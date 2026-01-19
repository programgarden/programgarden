"""
ProgramGarden - WorkflowExecutor

Workflow execution engine
- validate() → compile() → execute() lifecycle
- Stateful long-running execution support
- Graceful Restart support
- Event-based realtime updates
"""

from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime
import asyncio
import uuid
import logging

from programgarden.resolver import WorkflowResolver, ResolvedWorkflow, ValidationResult
from programgarden.context import ExecutionContext, WorkflowEvent
from programgarden.reconnect_handler import ReconnectHandler
from programgarden_core.expression import ExpressionEvaluator, ExpressionContext
from programgarden_core.bases.listener import (
    ExecutionListener,
    NodeState,
    EdgeState,
)

logger = logging.getLogger("programgarden.executor")


class NodeExecutorBase:
    """Node executor base class"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,  # plugin, fields 등 추가 매개변수 허용
    ) -> Dict[str, Any]:
        """
        Execute node

        Returns:
            Dictionary of output port values
        """
        raise NotImplementedError


def resolve_port_bindings(
    config: Dict[str, Any],
    context: ExecutionContext,
    node_id: str,
    port_names: List[str],
) -> Dict[str, Any]:
    """
    포트 바인딩 표현식을 평가하여 config를 업데이트
    
    config에 {{ nodes.xxx.yyy }} 표현식이 있으면 평가하여 실제 데이터로 교체합니다.
    
    Args:
        config: 노드 config (포트 바인딩 표현식 포함 가능)
        context: 실행 컨텍스트
        node_id: 현재 노드 ID
        port_names: 포트 바인딩을 확인할 필드 이름 목록
        
    Returns:
        평가된 config (표현식이 실제 데이터로 교체됨)
    """
    config = config.copy()  # 원본 보호
    
    for port_name in port_names:
        binding_expr = config.get(port_name)
        
        if binding_expr and isinstance(binding_expr, str) and "{{" in binding_expr:
            # {{ nodes.xxx.yyy }} 표현식 평가
            expr_context = context.get_expression_context()
            evaluator = ExpressionEvaluator(expr_context)
            try:
                result = evaluator.evaluate(binding_expr)
                if result is not None:
                    config[port_name] = result
                    context.log("debug", f"Port binding resolved: {port_name} = {type(result).__name__}", node_id)
            except Exception as e:
                context.log("warning", f"Port binding evaluation failed for {port_name}: {e}", node_id)
    
    return config


def ensure_ls_login(
    appkey: str,
    appsecret: str,
    paper_trading: bool,
    context: "ExecutionContext",
    node_id: str,
    caller_name: str = "",
) -> tuple:
    """
    LS증권 로그인 보장 헬퍼 함수
    
    싱글톤 LS 클라이언트의 appkey 또는 paper_trading이 변경되면 재로그인합니다.
    
    Args:
        appkey: LS증권 appkey
        appsecret: LS증권 appsecret
        paper_trading: 모의투자 여부
        context: 실행 컨텍스트
        node_id: 노드 ID
        caller_name: 호출자 이름 (로깅용)
        
    Returns:
        (ls_instance, success: bool, error_message: str | None)
    """
    from programgarden_finance import LS
    
    ls = LS.get_instance()
    
    # 현재 로그인된 appkey와 paper_trading 확인
    current_appkey = ls.token_manager.appkey if ls.token_manager else None
    current_paper_trading = ls.token_manager.paper_trading if ls.token_manager else None
    
    # appkey 또는 paper_trading 모드가 다르면 재로그인 필요
    needs_relogin = (
        not ls.is_logged_in() or 
        (current_appkey and current_appkey != appkey) or
        (current_paper_trading is not None and current_paper_trading != paper_trading)
    )
    
    if needs_relogin:
        if current_appkey and current_appkey != appkey:
            context.log("info", f"AppKey changed, re-logging in{f' for {caller_name}' if caller_name else ''}", node_id)
        elif current_paper_trading is not None and current_paper_trading != paper_trading:
            context.log("info", f"Trading mode changed ({current_paper_trading} → {paper_trading}), re-logging in{f' for {caller_name}' if caller_name else ''}", node_id)
        
        login_result = ls.login(
            appkey=appkey,
            appsecretkey=appsecret,
            paper_trading=paper_trading,
        )
        
        if not login_result:
            context.log("error", "LS login failed", node_id)
            return ls, False, "Login failed"
        
        context.log("info", f"LS logged in (paper_trading={paper_trading}){f' for {caller_name}' if caller_name else ''}", node_id)
    
    return ls, True, None


def evaluate_all_bindings(
    config: Dict[str, Any],
    context: "ExecutionContext",
    node_id: str,
) -> Dict[str, Any]:
    """
    config 내 모든 {{ }} 표현식을 재귀적으로 평가
    
    - dict, list 내부도 재귀 탐색
    - 평가 실패 시 원본 유지 + 경고 로그
    
    Args:
        config: 노드 config
        context: 실행 컨텍스트
        node_id: 노드 ID
        
    Returns:
        표현식이 평가된 config
    """
    config = config.copy()
    expr_context = context.get_expression_context()
    evaluator = ExpressionEvaluator(expr_context)
    
    def evaluate_value(value: Any) -> Any:
        if isinstance(value, str) and "{{" in value:
            try:
                result = evaluator.evaluate(value)
                context.log("debug", f"Expression evaluated: {value} -> {type(result).__name__}", node_id)
                return result
            except Exception as e:
                context.log("warning", f"Expression evaluation failed: {value} - {e}", node_id)
                return value
        elif isinstance(value, dict):
            return {k: evaluate_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [evaluate_value(v) for v in value]
        return value
    
    return {k: evaluate_value(v) for k, v in config.items()}


class GenericNodeExecutor(NodeExecutorBase):
    """
    범용 노드 실행기 (커뮤니티 노드 및 execute() 메서드가 있는 노드용)
    
    NodeRegistry에 등록된 노드 클래스의 execute() 메서드를 호출합니다.
    credential_id가 있으면 자동으로 credential 값을 노드 필드에 주입합니다.
    포트 바인딩({{ nodes.xxx.yyy }})이 있으면 자동으로 표현식을 평가합니다.
    
    이를 통해 노드 개발자는:
    1. 필드만 선언하면 됨 (bot_token: Optional[str] = None)
    2. execute()에서 self.bot_token으로 바로 사용
    3. _credential_keys, resolve_credentials() 호출 불필요
    
    Example:
        class TelegramNode(BaseNotificationNode):
            bot_token: Optional[str] = None  # credential에서 자동 주입
            chat_id: Optional[str] = None
            
            async def execute(self, context):
                # self.bot_token에 이미 값이 있음!
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        plugin: Optional[Any] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from programgarden_core.registry import NodeTypeRegistry
        
        registry = NodeTypeRegistry()
        node_class = registry.get(node_type)
        
        if not node_class:
            context.log("error", f"Node class not found in registry: {node_type}", node_id)
            return {"error": f"Unknown node type: {node_type}"}
        
        # plugin과 fields가 별도로 전달되면 config에 추가 (PluginNode용)
        # 빈 딕셔너리 {}는 무시 - config에 이미 있는 fields를 덮어쓰지 않음
        if plugin is not None:
            config["plugin"] = plugin.id if hasattr(plugin, "id") else str(plugin)
        if fields:  # truthy check: None, {}, [] 모두 무시
            config["fields"] = fields
        
        # 모든 config 값에서 {{ }} 표현식 평가
        config = evaluate_all_bindings(config, context, node_id)
        
        # credential_id가 있으면 credential 값을 config에 주입
        credential_id = config.get("credential_id")
        if credential_id:
            config = self._inject_credentials(credential_id, config, context, node_id)
        
        # fields 내부 표현식도 평가 (플러그인 노드용 - Dict 타입만)
        # MarketDataNode 등은 fields가 List[str]이므로 건드리지 않음
        fields = config.get("fields")
        if fields and isinstance(fields, dict):
            expr_context = context.get_expression_context()
            evaluator = ExpressionEvaluator(expr_context)
            config["fields"] = evaluator.evaluate_fields(fields)
        
        # 노드 인스턴스 생성 (config의 값들이 Pydantic 필드에 매핑됨)
        try:
            node_instance = node_class(id=node_id, **config)
        except Exception as e:
            context.log("error", f"Failed to create node instance: {e}", node_id)
            return {"error": str(e)}
        
        # execute() 메서드 호출
        if hasattr(node_instance, "execute"):
            try:
                result = await node_instance.execute(context)
                return result if isinstance(result, dict) else {"result": result}
            except Exception as e:
                context.log("error", f"Node execution failed: {e}", node_id)
                return {"error": str(e)}
        else:
            context.log("warning", f"Node {node_type} has no execute() method", node_id)
            return {"executed": True}
    
    def _inject_credentials(
        self,
        credential_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        Credential 값을 config에 주입
        
        우선순위:
        1. 워크플로우 JSON의 credentials 섹션 (data 값이 있으면)
        2. CredentialStore (외부 저장소)
        
        규칙:
        - credential의 키명 = 노드의 필드명 (예: token, header_name)
        - config에 해당 키가 없거나 None이면 credential 값으로 채움
        - 이미 값이 있으면 (직접 설정) 유지 (우선순위: 직접 설정 > credential)
        
        Example:
            credentials = {"openai-api": {"type": "http_bearer", "data": {"token": "sk-xxx"}}}
            config = {"credential_id": "openai-api", "url": "..."}
            
            → config = {"credential_id": "openai-api", "url": "...", "token": "sk-xxx"}
        """
        cred_data = context.get_workflow_credential(credential_id)
        
        if cred_data:
            config = config.copy()  # 원본 보호
            injected_keys = []
            
            for key, value in cred_data.items():
                # config에 없거나 None인 경우만 주입
                if config.get(key) is None and value:
                    config[key] = value
                    injected_keys.append(key)
            
            if injected_keys:
                # 민감 정보 로깅 방지: 키 이름만 로깅
                context.log(
                    "debug", 
                    f"Credentials injected from '{credential_id}': {', '.join(injected_keys)}", 
                    node_id
                )
        else:
            context.log("warning", f"Credential '{credential_id}' not found", node_id)
        
        return config


class StartNodeExecutor(NodeExecutorBase):
    """StartNode executor"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        context.log("info", "Workflow started", node_id)
        return {"start": True}


class ThrottleNodeExecutor(NodeExecutorBase):
    """
    ThrottleNode executor
    
    Controls data flow frequency from realtime nodes to prevent excessive
    execution of downstream nodes and API rate limiting.
    
    Modes:
    - skip: Ignore incoming data during cooldown
    - latest: Keep only the latest data during cooldown, execute when cooldown ends
    
    State is persisted in context.node_state to track:
    - last_passed_at: When data last passed through
    - skipped_count: Cumulative count of skipped executions
    - pending_data: Latest data waiting to be processed (latest mode only)
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        from programgarden_core.bases.listener import NodeState
        
        mode = config.get("mode", "latest")
        interval_sec = config.get("interval_sec", 5.0)
        pass_first = config.get("pass_first", True)
        
        # State key for this node
        state_key = "_throttle_state"
        throttle_state = context.get_node_state(node_id, state_key) or {
            "last_passed_at": None,
            "skipped_count": 0,
            "pending_data": None,
        }
        
        now = datetime.now()
        last_passed = throttle_state.get("last_passed_at")
        
        # Collect input data from upstream nodes
        input_data = self._collect_input_data(node_id, config, context)
        
        # First execution with pass_first=True
        if last_passed is None:
            if pass_first:
                return await self._pass_through(
                    node_id, node_type, context, input_data, throttle_state, state_key
                )
            else:
                # No data to pass yet, just store and wait
                throttle_state["pending_data"] = input_data
                throttle_state["last_passed_at"] = now
                context.set_node_state(node_id, state_key, throttle_state)
                context.log("debug", f"First data stored, waiting for interval ({interval_sec}s)", node_id)
                return {
                    "_throttled": True,
                    "_throttle_stats": {
                        "countdown_sec": interval_sec,
                        "skipped_count": 0,
                        "mode": mode,
                    }
                }
        
        # Cooldown check
        if isinstance(last_passed, str):
            last_passed = datetime.fromisoformat(last_passed)
        
        elapsed = (now - last_passed).total_seconds()
        remaining = interval_sec - elapsed
        
        if remaining > 0:
            # Still in cooldown
            throttle_state["skipped_count"] = throttle_state.get("skipped_count", 0) + 1
            
            if mode == "latest":
                # Keep the latest data
                throttle_state["pending_data"] = input_data
            
            # Save state
            context.set_node_state(node_id, state_key, throttle_state)
            
            # SSE notification for throttling state
            await context.notify_node_state(
                node_id=node_id,
                node_type=node_type,
                state=NodeState.THROTTLING,
                outputs={
                    "_throttle_stats": {
                        "countdown_sec": round(remaining, 1),
                        "skipped_count": throttle_state["skipped_count"],
                        "mode": mode,
                    }
                },
            )
            
            context.log(
                "debug", 
                f"Throttled ({mode}): {remaining:.1f}s remaining, skipped: {throttle_state['skipped_count']}", 
                node_id
            )
            
            # Return throttled result - downstream nodes should not execute
            return {
                "_throttled": True,
                "_throttle_stats": {
                    "countdown_sec": round(remaining, 1),
                    "skipped_count": throttle_state["skipped_count"],
                    "mode": mode,
                }
            }
        
        # Cooldown finished - pass through
        # In latest mode, use pending data if available
        if mode == "latest" and throttle_state.get("pending_data"):
            input_data = throttle_state["pending_data"]
            context.log("debug", "Using pending data (latest mode)", node_id)
        
        return await self._pass_through(
            node_id, node_type, context, input_data, throttle_state, state_key
        )
    
    async def _pass_through(
        self,
        node_id: str,
        node_type: str,
        context: ExecutionContext,
        input_data: Dict[str, Any],
        throttle_state: Dict[str, Any],
        state_key: str,
    ) -> Dict[str, Any]:
        """Process data pass-through"""
        from programgarden_core.bases.listener import NodeState
        
        now = datetime.now()
        throttle_state["last_passed_at"] = now.isoformat()
        throttle_state["pending_data"] = None
        # Keep skipped_count for cumulative stats
        
        context.set_node_state(node_id, state_key, throttle_state)
        
        # Pass input data as output (transparent proxy)
        outputs = dict(input_data) if input_data else {}
        outputs["_throttle_stats"] = {
            "skipped_count": throttle_state.get("skipped_count", 0),
            "last_passed_at": now.isoformat(),
            "passed": True,
        }
        
        # SSE notification for pass-through
        await context.notify_node_state(
            node_id=node_id,
            node_type=node_type,
            state=NodeState.COMPLETED,
            outputs=outputs,
        )
        
        context.log(
            "info", 
            f"Data passed through (total skipped: {throttle_state.get('skipped_count', 0)})", 
            node_id
        )
        
        return outputs
    
    def _collect_input_data(
        self, 
        node_id: str, 
        config: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Collect all data from upstream nodes"""
        input_data = {}
        
        # Check if we have realtime data from event
        if "_realtime_data" in config:
            input_data.update(config["_realtime_data"])
        
        # Get workflow edges to find upstream nodes
        workflow_edges = getattr(context, '_workflow_edges', None)
        if workflow_edges:
            for edge in workflow_edges:
                to_node = edge.get("to") or edge.get("to_node_id")
                if to_node == node_id:
                    from_node = edge.get("from") or edge.get("from_node_id")
                    if from_node:
                        all_outputs = context.get_all_outputs(from_node)
                        if all_outputs:
                            # Filter out internal fields
                            for key, value in all_outputs.items():
                                if not key.startswith("_"):
                                    input_data[key] = value
        
        return input_data


class ScheduleNodeExecutor(NodeExecutorBase):
    """
    ScheduleNode executor
    
    Cron 표현식에 따라 주기적으로 schedule_tick 이벤트를 발생시킵니다.
    - 첫 실행 시 즉시 trigger 반환 (초기 플로우 실행용)
    - 백그라운드에서 cron 스케줄에 따라 schedule_tick 이벤트 발생
    - stay_connected 노드들은 스케줄 사이에도 살아있음
    
    Based on programgarden_legacy/programgarden/system_executor.py
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from croniter import croniter
        
        # 이미 스케줄러가 실행 중이면 재등록하지 않음 (schedule_tick 이벤트로 인한 재실행 시)
        if node_id in context._persistent_tasks:
            context.log("debug", f"Scheduler already running for {node_id}, skip", node_id)
            return {"trigger": True}
        
        cron_expr = config.get("cron", "*/5 * * * *")
        tz_name = config.get("timezone", "America/New_York")
        enabled = config.get("enabled", True)
        count = config.get("count", 9999999)  # 최대 반복 횟수
        
        if not enabled:
            context.log("info", f"Schedule disabled: {cron_expr}", node_id)
            return {"trigger": False}
        
        # 타임존 설정
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            context.log("warning", f"Invalid timezone '{tz_name}', using UTC", node_id)
            tz = ZoneInfo("UTC")
        
        # cron 표현식 유효성 검사
        try:
            # croniter 6.x는 second_at_beginning 지원
            try:
                valid = croniter.is_valid(cron_expr, second_at_beginning=True)
            except TypeError:
                valid = croniter.is_valid(cron_expr)
            
            if not valid:
                context.log("error", f"Invalid cron expression: {cron_expr}", node_id)
                return {"trigger": False, "error": f"Invalid cron: {cron_expr}"}
        except Exception as e:
            context.log("error", f"Cron validation error: {e}", node_id)
            return {"trigger": False, "error": str(e)}
        
        context.log("info", f"Schedule started: {cron_expr} ({tz_name})", node_id)
        
        # 백그라운드 스케줄러 태스크
        async def scheduler_task():
            cnt = 0
            try:
                # second_at_beginning=True로 초 단위 cron도 지원
                try:
                    itr = croniter(cron_expr, datetime.now(tz), second_at_beginning=True)
                except TypeError:
                    itr = croniter(cron_expr, datetime.now(tz))
                
                while cnt < count and context.is_running:
                    # 다음 실행 시간 계산
                    next_dt = itr.get_next(datetime)
                    now = datetime.now(tz)
                    delay = (next_dt - now).total_seconds()
                    
                    if delay < 0:
                        delay = 0
                    
                    context.log(
                        "debug", 
                        f"Next schedule in {delay:.1f}s ({next_dt.isoformat()})", 
                        node_id
                    )
                    
                    # 대기 (1초 단위로 나눠서 is_running 체크)
                    while delay > 0 and context.is_running:
                        sleep_time = min(delay, 1.0)
                        await asyncio.sleep(sleep_time)
                        delay -= sleep_time
                    
                    if not context.is_running:
                        break
                    
                    # 스케줄 시간 도달 - 이벤트 발생
                    cnt += 1
                    context.log("info", f"Schedule tick #{cnt}: {cron_expr}", node_id)
                    
                    await context.emit_event(
                        event_type="schedule_tick",
                        source_node_id=node_id,
                        data={
                            "cron": cron_expr,
                            "count": cnt,
                            "triggered_at": datetime.now(tz).isoformat(),
                        },
                    )
                
                context.log("info", f"Schedule ended (total {cnt} executions)", node_id)
                
            except asyncio.CancelledError:
                context.log("debug", f"Scheduler cancelled after {cnt} executions", node_id)
            except Exception as e:
                context.log("error", f"Scheduler error: {e}", node_id)
        
        # 백그라운드 태스크 등록
        task = asyncio.create_task(scheduler_task())
        context.register_persistent_task(node_id, task)
        
        # 초기 트리거 반환 (첫 플로우 실행용)
        return {"trigger": True}


class WatchlistNodeExecutor(NodeExecutorBase):
    """
    WatchlistNode executor
    
    사용자 정의 관심종목 리스트를 처리합니다.
    단순히 [{exchange, symbol}] 형태로 정규화하여 출력합니다.
    
    connection, product는 필요 없음 - 후속 노드(RealMarketDataNode 등)에서 처리.
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        symbols_raw = config.get("symbols", [])
        
        # symbols 처리: [{exchange, symbol}, ...] 형태로 정규화
        processed_symbols = []
        for entry in symbols_raw:
            if isinstance(entry, dict):
                exchange = entry.get("exchange", "")
                symbol = entry.get("symbol", "")
                
                if symbol:
                    processed_symbols.append({
                        "exchange": exchange,
                        "symbol": symbol,
                    })
            elif isinstance(entry, str):
                # 문자열만 있는 경우: 거래소 없이 심볼만
                processed_symbols.append({
                    "exchange": "",
                    "symbol": entry,
                })
        
        context.log("info", f"Watchlist: {len(processed_symbols)} symbols", node_id)
        
        return {
            "symbols": processed_symbols,
        }


class SymbolFilterNodeExecutor(NodeExecutorBase):
    """
    SymbolFilterNode executor - 종목 비교/필터
    
    두 종목 리스트 간 집합 연산:
    - difference: A - B (차집합) - 중복 매수 방지에 활용
    - intersection: A ∩ B (교집합) - 복합 조건 충족 종목
    - union: A ∪ B (합집합) - 여러 소스 통합
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        operation = config.get("operation", "difference")
        input_a = config.get("input_a") or []  # None 대응
        input_b = config.get("input_b") or []  # None 대응
        
        # 종목 코드만 추출하여 집합으로 변환
        def extract_symbols(symbol_list: List) -> set:
            if not symbol_list:
                return set()
            result = set()
            for item in symbol_list:
                if isinstance(item, dict):
                    symbol = item.get("symbol", "")
                    if symbol:
                        result.add(symbol)
                elif isinstance(item, str):
                    result.add(item)
            return result
        
        # 원본 종목 정보 유지를 위한 매핑
        def build_symbol_map(symbol_list: List) -> Dict[str, Dict]:
            if not symbol_list:
                return {}
            from programgarden_core.models import normalize_symbol
            result = {}
            for item in symbol_list:
                if isinstance(item, dict):
                    symbol = item.get("symbol", "")
                    if symbol and symbol not in result:
                        # exchange가 없으면 추정
                        if item.get("exchange"):
                            result[symbol] = item
                        else:
                            result[symbol] = normalize_symbol(symbol)
                elif isinstance(item, str):
                    if item not in result:
                        result[item] = normalize_symbol(item)
            return result
        
        set_a = extract_symbols(input_a)
        set_b = extract_symbols(input_b)
        map_a = build_symbol_map(input_a)
        map_b = build_symbol_map(input_b)
        
        # 집합 연산 수행
        if operation == "difference":
            result_symbols = set_a - set_b
            source_map = map_a
        elif operation == "intersection":
            result_symbols = set_a & set_b
            source_map = map_a
        elif operation == "union":
            result_symbols = set_a | set_b
            source_map = {**map_b, **map_a}  # A가 우선
        else:
            context.log("warning", f"Unknown operation: {operation}, using difference", node_id)
            result_symbols = set_a - set_b
            source_map = map_a
        
        # 결과를 원본 형식으로 복원
        output_symbols = []
        for symbol in result_symbols:
            if symbol in source_map:
                output_symbols.append(source_map[symbol])
            else:
                output_symbols.append({"symbol": symbol, "exchange": ""})
        
        context.log("info", f"SymbolFilter ({operation}): {len(set_a)} - {len(set_b)} = {len(output_symbols)} symbols", node_id)
        
        return {
            "symbols": output_symbols,
            "count": len(output_symbols),
        }


class MarketUniverseNodeExecutor(NodeExecutorBase):
    """
    MarketUniverseNode executor - 대표지수 종목
    
    ⚠️ 해외주식(overseas_stock) 전용 노드입니다. 해외선물은 지원하지 않습니다.
    
    pytickersymbols 라이브러리를 활용하여 미국 대표지수 구성종목을 조회합니다.
    Broker 연결 없이 독립적으로 실행됩니다.
    
    지원 인덱스 (LS증권 거래 가능 거래소):
    - NASDAQ 100 (~101개)
    - S&P 500 (~503개)
    - S&P 100
    - DOW JONES (다우존스 30)
    
    Note: pytickersymbols는 유럽/아시아 인덱스도 지원하지만,
          LS증권에서 거래 가능한 미국 인덱스만 권장합니다.
    """
    
    # 인덱스별 심볼 캐시 (앱 실행 중 재사용)
    _cache: Dict[str, List[Dict[str, str]]] = {}
    _cache_time: Dict[str, float] = {}
    CACHE_TTL = 3600 * 24  # 24시간 캐시
    
    # 사용자 입력 → pytickersymbols 인덱스명 매핑 (미국 인덱스)
    INDEX_MAPPING = {
        "NASDAQ100": "NASDAQ 100",
        "NASDAQ 100": "NASDAQ 100",
        "SP500": "S&P 500",
        "S&P500": "S&P 500",
        "S&P 500": "S&P 500",
        "SP100": "S&P 100",
        "S&P100": "S&P 100",
        "S&P 100": "S&P 100",
        "DOW30": "DOW JONES",
        "DOW JONES": "DOW JONES",
        "DOWJONES": "DOW JONES",
    }
    
    # 인덱스별 기본 거래소 매핑
    INDEX_EXCHANGE_MAPPING = {
        "NASDAQ 100": "NASDAQ",
        "S&P 500": "",  # 혼합 (NYSE, NASDAQ)
        "S&P 100": "",
        "DOW JONES": "",
    }
    
    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        import time
        
        universe = config.get("universe", "NASDAQ100")
        
        # 사용자 입력을 pytickersymbols 인덱스명으로 변환
        pts_index = self.INDEX_MAPPING.get(universe, universe)
        
        # 캐시 확인
        now = time.time()
        if pts_index in self._cache:
            cache_age = now - self._cache_time.get(pts_index, 0)
            if cache_age < self.CACHE_TTL:
                symbols = self._cache[pts_index]
                context.log("info", f"MarketUniverse ({pts_index}): {len(symbols)} symbols (cached)", node_id)
                return {"symbols": symbols, "count": len(symbols)}
        
        # pytickersymbols로 조회 (동기 라이브러리이므로 to_thread 사용)
        try:
            symbols = await self._fetch_index_constituents(pts_index, context, node_id)
            
            # 캐시 저장
            self._cache[pts_index] = symbols
            self._cache_time[pts_index] = now
            
            context.log("info", f"MarketUniverse ({pts_index}): {len(symbols)} symbols", node_id)
            return {"symbols": symbols, "count": len(symbols)}
            
        except Exception as e:
            context.log("error", f"MarketUniverse fetch failed: {e}", node_id)
            return {"symbols": [], "count": 0, "error": str(e)}
    
    async def _fetch_index_constituents(
        self,
        index_name: str,
        context: ExecutionContext,
        node_id: str,
    ) -> List[Dict[str, str]]:
        """pytickersymbols를 사용하여 인덱스 구성종목 조회"""
        import asyncio
        
        def _sync_fetch():
            """동기 함수 - pytickersymbols는 동기 라이브러리"""
            from pytickersymbols import PyTickerSymbols
            
            pts = PyTickerSymbols()
            available_indices = pts.get_all_indices()
            
            if index_name not in available_indices:
                raise ValueError(
                    f"Unknown index: {index_name}. "
                    f"Available indices: {', '.join(available_indices)}"
                )
            
            stocks = list(pts.get_stocks_by_index(index_name))
            
            # 기본 거래소 결정
            default_exchange = self.INDEX_EXCHANGE_MAPPING.get(index_name, "")
            
            symbols = []
            for stock in stocks:
                symbol = stock.get("symbol", "")
                if not symbol:
                    continue
                
                # 거래소 정보 추출 (있으면 사용, 없으면 기본값)
                exchange = default_exchange
                stock_symbols = stock.get("symbols", [])
                for sym_info in stock_symbols:
                    if sym_info.get("yahoo"):
                        # yahoo 심볼에서 거래소 힌트 추출 가능
                        yahoo_sym = sym_info.get("yahoo", "")
                        if "." in yahoo_sym:
                            # 예: "7203.T" → 도쿄 거래소
                            suffix = yahoo_sym.split(".")[-1]
                            exchange_hints = {
                                "T": "TSE",  # Tokyo
                                "L": "LSE",  # London
                                "PA": "EPA",  # Paris
                                "DE": "FRA",  # Frankfurt
                                "F": "FRA",
                            }
                            exchange = exchange_hints.get(suffix, exchange)
                        break
                
                symbols.append({
                    "exchange": exchange,
                    "symbol": symbol,
                    "name": stock.get("name", ""),
                })
            
            return symbols
        
        # 동기 호출을 thread pool에서 실행하여 이벤트 루프 블로킹 방지
        result = await asyncio.to_thread(_sync_fetch)
        return result


class ScreenerNodeExecutor(NodeExecutorBase):
    """
    ScreenerNode executor - 조건으로 종목찾기
    
    Yahoo Finance API를 활용하여 시가총액, 거래량 등 조건으로 종목을 검색합니다.
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        market_cap_min = config.get("market_cap_min")
        market_cap_max = config.get("market_cap_max")
        volume_min = config.get("volume_min")
        sector = config.get("sector")
        exchange = config.get("exchange")
        max_results = config.get("max_results", 100)
        
        # 입력으로 받은 종목 리스트 (선택사항)
        input_symbols = config.get("symbols", [])
        
        try:
            if input_symbols:
                # 입력 종목에서 필터링
                symbols = await self._filter_symbols(
                    input_symbols, market_cap_min, market_cap_max, 
                    volume_min, sector, exchange, max_results, context, node_id
                )
            else:
                # 전체 시장에서 검색
                symbols = await self._search_market(
                    market_cap_min, market_cap_max,
                    volume_min, sector, exchange, max_results, context, node_id
                )
            
            context.log("info", f"Screener: {len(symbols)} symbols matched", node_id)
            return {"symbols": symbols, "count": len(symbols)}
            
        except Exception as e:
            context.log("error", f"Screener failed: {e}", node_id)
            return {"symbols": [], "count": 0, "error": str(e)}
    
    async def _filter_symbols(
        self,
        symbols: List[Dict],
        market_cap_min: Optional[float],
        market_cap_max: Optional[float],
        volume_min: Optional[int],
        sector: Optional[str],
        exchange: Optional[str],
        max_results: int,
        context: ExecutionContext,
        node_id: str,
    ) -> List[Dict[str, str]]:
        """입력 종목 리스트에서 조건 필터링"""
        import asyncio
        
        tickers = [s.get("symbol", s) if isinstance(s, dict) else s for s in symbols]
        
        # yfinance 동기 호출을 thread pool에서 실행 (이벤트 루프 블로킹 방지)
        def _sync_filter():
            import yfinance as yf
            filtered = []
            
            for ticker in tickers[:max_results * 2]:  # 여유분 확보
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    # 필터 조건 확인
                    mcap = info.get("marketCap", 0)
                    vol = info.get("averageVolume", 0)
                    stock_sector = info.get("sector", "")
                    stock_exchange = info.get("exchange", "")
                    
                    # 거래소 매핑 (yfinance 코드 → 표준 이름)
                    ex_map = {"NMS": "NASDAQ", "NGM": "NASDAQ", "NYQ": "NYSE", "ASE": "AMEX", "NCM": "NASDAQ"}
                    mapped_exchange = ex_map.get(stock_exchange, stock_exchange)
                    
                    if market_cap_min and mcap < market_cap_min:
                        continue
                    if market_cap_max and mcap > market_cap_max:
                        continue
                    if volume_min and vol < volume_min:
                        continue
                    # sector 정규화 비교 (대소문자, 띄어쓰기 무시)
                    if sector:
                        normalized_input = sector.lower().replace(" ", "").replace("-", "").replace("_", "")
                        normalized_stock = stock_sector.lower().replace(" ", "").replace("-", "").replace("_", "")
                        if normalized_input != normalized_stock:
                            continue
                    # exchange 필터 (매핑된 값으로 비교)
                    if exchange and exchange.upper() not in mapped_exchange.upper():
                        continue
                    
                    filtered.append({
                        "exchange": mapped_exchange,
                        "symbol": ticker,
                        "market_cap": mcap,
                        "volume": vol,
                        "sector": stock_sector,
                    })
                    
                    if len(filtered) >= max_results:
                        break
                        
                except Exception as e:
                    # 동기 함수에서는 context 사용 불가, 그냥 skip
                    continue
            
            # 시가총액 내림차순 정렬
            filtered.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
            return filtered[:max_results]
        
        # thread pool에서 실행하여 이벤트 루프 블로킹 방지
        result = await asyncio.to_thread(_sync_filter)
        return result
    
    async def _search_market(
        self,
        market_cap_min: Optional[float],
        market_cap_max: Optional[float],
        volume_min: Optional[int],
        sector: Optional[str],
        exchange: Optional[str],
        max_results: int,
        context: ExecutionContext,
        node_id: str,
    ) -> List[Dict[str, str]]:
        """전체 시장에서 조건 검색 (S&P500 기반)"""
        # 기본적으로 S&P500에서 필터링
        universe_executor = MarketUniverseNodeExecutor()
        universe_result = await universe_executor.execute(
            node_id=f"{node_id}_universe",
            node_type="MarketUniverseNode",
            config={"universe": "SP500"},
            context=context,
        )
        
        input_symbols = universe_result.get("symbols", [])
        
        return await self._filter_symbols(
            input_symbols, market_cap_min, market_cap_max,
            volume_min, sector, exchange, max_results, context, node_id
        )


class SymbolQueryNodeExecutor(NodeExecutorBase):
    """
    SymbolQueryNode executor - 전체종목조회
    
    해외주식: g3190 API (마스터상장종목조회)
    해외선물: o3101 API (해외선물마스터조회)
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        from programgarden_core.models.exchange import ProductType
        
        # product_type 필드에서 상품 유형 확인 (UI에서 선택)
        product_type = config.get("product_type", "overseas_stock")
        
        # connection에서 paper_trading 확인 (fallback)
        connection = config.get("connection", {})
        paper_trading = connection.get("paper_trading", False)
        
        # BrokerNode가 set_secret()으로 저장한 credential 가져오기
        cred = context.get_credential("credential_id")
        if cred:
            appkey = cred.get("appkey", "")
            appsecret = cred.get("appsecret", "")
            paper_trading = cred.get("paper_trading", paper_trading)
        else:
            appkey = ""
            appsecret = ""
        
        if not appkey or not appsecret:
            context.log("error", "SymbolQueryNode requires valid connection with appkey/appsecret", node_id)
            return {"symbols": [], "count": 0, "error": "Missing credentials"}
        
        max_results = config.get("max_results", 500)
        
        # product_type 필드 기준으로 API 분기
        if product_type == "overseas_futures":
            return await self._execute_futures_master(
                node_id, config, context, appkey, appsecret, paper_trading, max_results
            )
        else:
            return await self._execute_stock_master(
                node_id, config, context, appkey, appsecret, max_results
            )
    
    async def _execute_stock_master(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        appkey: str,
        appsecret: str,
        max_results: int,
    ) -> Dict[str, Any]:
        """해외주식 종목마스터 조회 (g3190)"""
        from programgarden_finance import LS, g3190
        
        ls, success, error = ensure_ls_login(appkey, appsecret, False, context, node_id)
        if not success:
            return {"symbols": [], "count": 0, "error": error}
        
        country = config.get("country", "US")
        stock_exchange = config.get("stock_exchange", "")  # 빈값이면 전체
        
        # UI 스키마(81/82) → g3190 API exgubun(1/2) 변환
        # Note: AMEX는 NYSE와 함께 exgubun="1"로 조회됨 (83 옵션 제거)
        exgubun_mapping = {
            "": "",      # 전체
            "81": "1",   # NYSE/AMEX → 1
            "82": "2",   # NASDAQ → 2
        }
        exgubun = exgubun_mapping.get(stock_exchange, stock_exchange)
        # 1자리 코드가 직접 입력된 경우도 지원 (하위 호환)
        if stock_exchange in ("1", "2", "3"):
            exgubun = stock_exchange
        
        # g3190 호출
        all_symbols = []
        cts_value = ""
        read_count = min(max_results, 500)
        
        try:
            while True:
                query = ls.overseas_stock().시세().마스터상장종목조회(
                    g3190.G3190InBlock(
                        delaygb="R",
                        natcode=country,
                        exgubun=exgubun or "2",  # 2: NASDAQ (기본값)
                        readcnt=read_count,
                        cts_value=cts_value
                    )
                )
                
                result = await query.req_async()
                
                if result and hasattr(result, 'block1') and result.block1:
                    for item in result.block1:
                        # 거래소 코드 → 이름 매핑
                        exchcd = getattr(item, 'exchcd', '')
                        exchange_name = self._stock_exchcd_to_name(exchcd)
                        
                        all_symbols.append({
                            "exchange": exchange_name,
                            "exchange_code": exchcd,
                            "symbol": getattr(item, 'symbol', ''),
                            "name": getattr(item, 'korname', '') or getattr(item, 'engname', ''),
                            "isin": getattr(item, 'isin', ''),
                        })
                    
                    # 연속 조회
                    if hasattr(result, 'block') and result.block:
                        cts_value = getattr(result.block, 'cts_value', '')
                    
                    if not cts_value or len(all_symbols) >= max_results:
                        break
                else:
                    break
                    
        except Exception as e:
            context.log("error", f"g3190 API error: {str(e)}", node_id)
            return {"symbols": [], "count": 0, "error": str(e)}
        
        context.log("info", f"전체종목조회 (해외주식): {len(all_symbols)}개 종목 from {country}", node_id)
        
        return {
            "symbols": all_symbols[:max_results],
            "count": len(all_symbols[:max_results]),
            "country": country,
            "product": "overseas_stock",
        }
    
    async def _execute_futures_master(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        appkey: str,
        appsecret: str,
        paper_trading: bool,
        max_results: int,
    ) -> Dict[str, Any]:
        """해외선물 종목마스터 조회 (o3101)"""
        from programgarden_finance import LS, o3101
        
        ls, success, error = ensure_ls_login(appkey, appsecret, paper_trading, context, node_id)
        if not success:
            return {"symbols": [], "count": 0, "error": error}
        
        futures_exchange = config.get("futures_exchange", "1")  # 1: 전체
        futures_contract_month = config.get("futures_contract_month", "")  # 월물 필터
        
        all_symbols = []
        
        try:
            query = ls.overseas_futureoption().market().해외선물마스터조회(
                body=o3101.O3101InBlock(gubun=futures_exchange)
            )
            
            result = await query.req_async()
            
            if result and hasattr(result, 'block') and result.block:
                for item in result.block:
                    # 거래소 코드 → 이름 매핑
                    exchcd = getattr(item, 'ExchCd', '')
                    exchange_name = getattr(item, 'ExchNm', '') or self._futures_exchcd_to_name(exchcd)
                    contract_month = f"{getattr(item, 'LstngYr', '')}{getattr(item, 'LstngM', '')}"
                    
                    all_symbols.append({
                        "exchange": exchange_name,
                        "exchange_code": exchcd,
                        "symbol": getattr(item, 'Symbol', ''),
                        "name": getattr(item, 'SymbolNm', ''),
                        "base_product": getattr(item, 'BscGdsCd', ''),
                        "base_product_name": getattr(item, 'BscGdsNm', ''),
                        "currency": getattr(item, 'CrncyCd', ''),
                        "contract_month": contract_month,
                    })
            
            # 월물 필터링 적용
            if futures_contract_month:
                all_symbols = self._filter_by_contract_month(all_symbols, futures_contract_month)
                    
        except Exception as e:
            context.log("error", f"o3101 API error: {str(e)}", node_id)
            return {"symbols": [], "count": 0, "error": str(e)}
        
        context.log("info", f"전체종목조회 (해외선물): {len(all_symbols)}개 종목, 거래소={futures_exchange}, 월물필터={futures_contract_month or 'none'}", node_id)
        
        return {
            "symbols": all_symbols[:max_results],
            "count": len(all_symbols[:max_results]),
            "futures_exchange": futures_exchange,
            "futures_contract_month": futures_contract_month or None,
            "product": "overseas_futures",
        }
    
    def _stock_exchcd_to_name(self, exchcd: str) -> str:
        """해외주식 거래소 코드 → 이름"""
        # Note: AMEX 종목도 exchcd=81로 반환됨 (NYSE/AMEX 통합)
        mapping = {
            "81": "NYSE/AMEX",
            "82": "NASDAQ",
            "84": "SEHK",  # 홍콩
            "85": "TSE",   # 일본
            "86": "SSE",   # 상해
            "87": "SZSE",  # 심천
        }
        return mapping.get(exchcd, exchcd)
    
    def _futures_exchcd_to_name(self, exchcd: str) -> str:
        """해외선물 거래소 코드 → 이름"""
        mapping = {
            "CME": "CME",
            "COMEX": "COMEX",
            "NYMEX": "NYMEX",
            "CBOT": "CBOT",
            "SGX": "SGX",
            "HKEX": "HKEX",
            "OSE": "OSE",
            "EUREX": "EUREX",
            "ICE": "ICE",
        }
        return mapping.get(exchcd, exchcd)
    
    def _filter_by_contract_month(
        self, symbols: List[Dict[str, Any]], month_filter: str
    ) -> List[Dict[str, Any]]:
        """
        월물 필터링
        
        Args:
            symbols: 종목 리스트
            month_filter: 월물 필터
                - "F", "G", ... "Z": 특정 월만 (모든 연도)
                - "2026F": 특정 연도+월
                - "front": 근월물 (가장 가까운 만기)
                - "next": 차월물 (두 번째로 가까운 만기)
        
        Returns:
            필터링된 종목 리스트
        """
        if not month_filter or not symbols:
            return symbols
        
        month_filter = month_filter.strip().upper()
        
        # front/next: 월물 정렬 후 선택
        if month_filter in ("FRONT", "NEXT"):
            # base_product별로 그룹화
            by_product: Dict[str, List[Dict]] = {}
            for sym in symbols:
                bp = sym.get("base_product", "")
                if bp not in by_product:
                    by_product[bp] = []
                by_product[bp].append(sym)
            
            result = []
            for bp, items in by_product.items():
                # contract_month 기준 정렬 (예: 2026F < 2026G < 2026H)
                sorted_items = sorted(items, key=lambda x: x.get("contract_month", ""))
                if month_filter == "FRONT" and sorted_items:
                    result.append(sorted_items[0])
                elif month_filter == "NEXT" and len(sorted_items) > 1:
                    result.append(sorted_items[1])
            return result
        
        # 월 코드만 (예: "F", "G")
        if len(month_filter) == 1:
            return [s for s in symbols if s.get("contract_month", "").endswith(month_filter)]
        
        # 연도+월 코드 (예: "2026F")
        return [s for s in symbols if s.get("contract_month", "") == month_filter]


class BrokerNodeExecutor(NodeExecutorBase):
    """BrokerNode executor"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        import os
        
        provider = config.get("provider", "ls-sec.co.kr")
        company = config.get("company", "ls")
        product = config.get("product", "overseas_stock")
        paper_trading = config.get("paper_trading", True)
        
        # ========================================
        # 모의투자 지원 여부 검증
        # - overseas_stock: 모의투자 미지원 (LS증권)
        # - overseas_futures: 모의투자 지원
        # ========================================
        if product == "overseas_stock" and paper_trading:
            context.log("warning", "overseas_stock does not support paper_trading (LS Securities), forcing real mode", node_id)
            paper_trading = False
        
        # ========================================
        # Credential 자동 주입 (GenericNodeExecutor와 동일 패턴)
        # credential_id가 있으면 appkey, appsecret이 config에 주입됨
        # ========================================
        credential_id = config.get("credential_id")
        if credential_id:
            config = self._inject_credentials(credential_id, config, context, node_id)
        
        appkey = config.get("appkey")
        appsecret = config.get("appsecret")
        
        # credential에서 paper_trading 설정 오버라이드
        if "paper_trading" in config and credential_id:
            paper_trading = config.get("paper_trading", paper_trading)
        
        if appkey and appsecret:
            context.set_secret("credential_id", {
                "appkey": appkey,
                "appsecret": appsecret,
                "paper_trading": paper_trading,
            })
            context.log("info", f"Broker credentials stored (paper_trading={paper_trading})", node_id)
        else:
            context.log("warning", "No credentials found - some features may not work", node_id)
        
        # provider 매핑 (company -> provider)
        if company == "ls":
            provider = "ls-sec.co.kr"
        
        context.log("info", f"Broker connected: {provider} ({product}, paper_trading={paper_trading})", node_id)
        return {
            "connected": True,
            "connection": {
                "provider": provider,
                "product": product,
                "paper_trading": paper_trading,
                "appkey": appkey,
                "appsecret": appsecret,
            }
        }
    
    def _inject_credentials(
        self,
        credential_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        Credential 값을 config에 주입
        
        워크플로우 JSON의 credentials 섹션에서 값을 가져와 config에 주입합니다.
        (프로덕션 환경: 서버가 암호화된 credentials를 복호화하여 JSON에 포함)
        
        규칙:
        - credential의 키명 = 노드의 필드명 (예: appkey, appsecret)
        - config에 해당 키가 없거나 None이면 credential 값으로 채움
        """
        cred_data = context.get_workflow_credential(credential_id)
        
        if cred_data:
            config = config.copy()  # 원본 보호
            injected_keys = []
            
            for key, value in cred_data.items():
                # config에 없거나 None인 경우만 주입
                if config.get(key) is None and value:
                    config[key] = value
                    injected_keys.append(key)
            
            if injected_keys:
                # 민감 정보 로깅 방지: 키 이름만 로깅
                context.log(
                    "debug", 
                    f"Credentials injected from '{credential_id}': {', '.join(injected_keys)}", 
                    node_id
                )
        else:
            context.log("warning", f"Credential '{credential_id}' not found in workflow credentials", node_id)
        
        return config


class AccountNodeExecutor(NodeExecutorBase):
    """
    AccountNode executor - 계좌 잔고 1회 조회 (REST API)
    
    RealAccountNode와 달리 WebSocket 연결 없이 REST API로 1회만 조회합니다.
    
    Connection 획득 방법:
    1. config에서 명시적으로 지정된 connection (바인딩 표현식 지원)
    2. input 포트로 연결된 BrokerNode의 connection
    
    예시:
      - 바인딩: "connection": "{{ nodes.broker_2.connection }}"
      - 엣지 연결: BrokerNode → AccountNode
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        # config에서 명시적 connection 확인 (바인딩 표현식 해석됨)
        # 예: "connection": "{{ nodes.broker_2.connection }}"
        broker_connection = config.get("connection")
        
        # connection 없으면 에러 - 명시적 바인딩 필수
        if not broker_connection:
            context.log("error", "AccountNode: connection 필드가 필수입니다. connection: \"{{ nodes.broker.connection }}\"를 설정하세요.", node_id)
            return self._empty_result("Missing connection field - set connection: \"{{ nodes.broker.connection }}\"")
        
        # connection 정보 추출
        if isinstance(broker_connection, dict):
            provider = broker_connection.get("provider", "ls-sec.co.kr")
            # config의 product_type 우선, connection.product fallback (하위 호환)
            product = config.get("product_type") or broker_connection.get("product", "overseas_stock")
        else:
            context.log("error", f"AccountNode: connection 타입이 잘못되었습니다: {type(broker_connection)}", node_id)
            return self._empty_result("Invalid connection type")
        
        context.log("info", f"AccountNode: provider={provider}, product={product} (REST 1회 조회)", node_id)
        
        # 브로커별 분기 처리
        if provider == "ls-sec.co.kr":
            return await self._execute_ls(node_id, product, context)
        else:
            context.log("error", f"Unsupported provider: {provider}", node_id)
            return self._empty_result(f"Unsupported provider: {provider}")

    async def _execute_ls(
        self,
        node_id: str,
        product: str,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """LS증권 계좌 조회 (REST API)"""
        # secrets에서 인증 정보 가져오기
        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not found in secrets", node_id)
            return self._empty_result("Missing credentials")
        
        appkey = credential.get("appkey")
        appsecret = credential.get("appsecret")
        paper_trading = credential.get("paper_trading", False)
        
        if not appkey or not appsecret:
            context.log("error", "appkey/appsecret not found in credential", node_id)
            return self._empty_result("Missing appkey/appsecret")
        
        try:
            ls, success, error = ensure_ls_login(
                appkey, appsecret, paper_trading, context, node_id,
                caller_name=f"AccountNode({product})"
            )
            if not success:
                return self._empty_result(error)
            
            # 상품별 REST API 호출
            if product == "overseas_stock":
                return await self._ls_overseas_stock(ls, node_id, context)
            elif product == "domestic_stock":
                return await self._ls_domestic_stock(ls, node_id, context)
            elif product in ("overseas_futures", "overseas_futureoption"):
                # overseas_futures와 overseas_futureoption은 같은 API 사용
                return await self._ls_overseas_futureoption(ls, node_id, context)
            else:
                context.log("warning", f"Unsupported LS product: {product}, using overseas_stock", node_id)
                return await self._ls_overseas_stock(ls, node_id, context)
                
        except ImportError as e:
            context.log("error", f"finance package not available: {e}", node_id)
            return self._empty_result(f"finance package error: {e}")
        except Exception as e:
            context.log("error", f"Unexpected error: {e}", node_id)
            return self._empty_result(str(e))

    async def _ls_overseas_stock(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """LS증권 해외주식 잔고 조회"""
        from datetime import datetime
        from programgarden_finance import COSOQ00201
        from programgarden_finance.ls.models import SetupOptions
        
        today = datetime.now().strftime("%Y%m%d")
        cosoq00201 = ls.overseas_stock().accno().cosoq00201(
            COSOQ00201.COSOQ00201InBlock1(
                RecCnt=1,
                BaseDt=today,
                CrcyCode="ALL",
                AstkBalTpCode="00",
            ),
            options=SetupOptions(on_rate_limit="wait"),
        )
        
        response = await cosoq00201.req_async()
        
        if response.error_msg:
            context.log("error", f"API error: {response.error_msg}", node_id)
            return self._empty_result(response.error_msg)
        
        # block4 = 종목별 잔고 상세
        positions = {}
        for item in response.block4 or []:
            symbol = item.ShtnIsuNo.strip()
            if not symbol:
                continue
            
            positions[symbol] = {
                "symbol": symbol,
                "name": item.JpnMktHanglIsuNm.strip() if item.JpnMktHanglIsuNm else symbol,
                "qty": item.AstkBalQty,
                "avg_price": item.FcstckUprc,
                "current_price": item.OvrsScrtsCurpri,
                "pnl_rate": item.PnlRat,
                "pnl_amount": item.FcurrEvalPnlAmt,
                "currency": item.CrcyCode,
                "market": item.MktTpNm.strip() if item.MktTpNm else "",
                "eval_amount": item.FcurrEvalAmt,
                "purchase_amount": item.FcurrBuyAmt,
            }
        
        held_symbols = list(positions.keys())
        
        # block2 = 전체 평가 요약
        balance_info = {"cash": 0.0, "total_value": 0.0}
        if response.block2:
            balance_info = {
                "total_pnl_rate": response.block2.ErnRat,
                "cash_krw": response.block2.WonDpsBalAmt,
                "stock_eval_krw": response.block2.StkConvEvalAmt,
                "total_eval_krw": response.block2.WonEvalSumAmt,
                "total_pnl_krw": response.block2.ConvEvalPnlAmt,
            }
        
        context.log("info", f"AccountNode: {len(held_symbols)} positions fetched", node_id)
        return {
            "held_symbols": held_symbols,
            "positions": positions,
            "balance": balance_info,
        }

    async def _ls_domestic_stock(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """LS증권 국내주식 잔고 조회 (TODO: 구현 필요)"""
        context.log("warning", "LS domestic_stock not yet implemented, returning empty", node_id)
        return self._empty_result("domestic_stock not implemented")

    async def _ls_overseas_futureoption(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        LS증권 해외선물옵션 잔고 조회 (CIDBQ01500)
        
        미결제(보유) 잔고를 조회합니다.
        """
        from datetime import datetime
        
        try:
            from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01500.blocks import CIDBQ01500InBlock1
            
            today = datetime.now().strftime("%Y%m%d")
            
            response = await ls.overseas_futureoption().accno().CIDBQ01500(
                body=CIDBQ01500InBlock1(
                    RecCnt=1,
                    AcntTpCode="1",      # 1: 위탁
                    QryDt=today,         # 조회일자
                    BalTpCode="2",       # 1: 합산, 2: 건별 (건별이 더 안정적)
                    FcmAcntNo=""
                )
            ).req_async()
            
            # 응답 코드 확인
            if response.rsp_cd and response.rsp_cd not in ["00000", "00136"]:
                context.log("warning", f"CIDBQ01500 response: {response.rsp_cd} - {response.rsp_msg}", node_id)
            
            # block2 = 종목별 잔고
            positions = {}
            for item in (response.block2 or []):
                symbol = item.IsuCodeVal.strip() if item.IsuCodeVal else ""
                if not symbol:
                    continue
                
                # BnsTpCode: 1=매도, 2=매수
                is_long = item.BnsTpCode == "2"
                
                positions[symbol] = {
                    "symbol": symbol,
                    "name": item.IsuNm.strip() if hasattr(item, 'IsuNm') and item.IsuNm else symbol,
                    "is_long": is_long,
                    "qty": int(item.BalQty) if item.BalQty else 0,
                    "entry_price": float(item.PchsPrc) if item.PchsPrc else 0.0,
                    "current_price": float(item.OvrsDrvtNowPrc) if item.OvrsDrvtNowPrc else 0.0,
                    "pnl_amount": float(item.AbrdFutsEvalPnlAmt) if item.AbrdFutsEvalPnlAmt else 0.0,
                    "currency": item.CrcyCodeVal.strip() if item.CrcyCodeVal else "USD",
                }
            
            held_symbols = list(positions.keys())
            
            # block2의 첫 번째 항목에서 계좌 요약 정보 가져오기 (CIDBQ01500 구조상 block2에 있음)
            balance_info = {"cash": 0.0, "total_value": 0.0}
            if response.block2 and len(response.block2) > 0:
                b2 = response.block2[0]
                balance_info = {
                    "deposit": float(b2.Dps) if b2.Dps else 0.0,
                    "orderable_amount": float(b2.OrdAbleAmt) if b2.OrdAbleAmt else 0.0,
                    "withdrawable_amount": float(b2.WthdwAbleAmt) if b2.WthdwAbleAmt else 0.0,
                    "margin": float(b2.CsgnMgn) if b2.CsgnMgn else 0.0,
                    "maintenance_margin": float(b2.MaintMgn) if b2.MaintMgn else 0.0,
                }
            
            context.log("info", f"AccountNode (futures): {len(held_symbols)} positions fetched", node_id)
            return {
                "held_symbols": held_symbols,
                "symbols": held_symbols,
                "positions": positions,
                "balance": balance_info,
            }
            
        except Exception as e:
            context.log("error", f"Failed to fetch futures positions: {e}", node_id)
            return self._empty_result(str(e))

    def _empty_result(self, error: str = "") -> Dict[str, Any]:
        """빈 결과 반환"""
        result = {
            "held_symbols": [],
            "positions": {},
            "balance": {"cash": 0.0, "total_value": 0.0},
        }
        if error:
            result["error"] = error
        return result


class RealAccountNodeExecutor(NodeExecutorBase):
    """
    RealAccountNode executor - 실시간 계좌 정보 (브로커별 분기 처리)
    
    stay_connected 옵션에 따라:
    - True: WebSocket 연결 유지, 플로우 끝나도 계속 살아있음 (이벤트 루프 진입)
    - False: WebSocket 연결, 플로우 끝나면 cleanup (연결 종료)
    
    1회성 REST API 조회가 필요하면 AccountNode를 사용하세요.
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        import sys
        # 옵션 확인
        stay_connected = config.get("stay_connected", True)
        sync_interval_sec = config.get("sync_interval_sec", 60)
        
        
        # config에서 명시적 connection 확인 (바인딩 표현식 해석됨)
        # 예: "connection": "{{ nodes.broker_2.connection }}"
        broker_connection = config.get("connection")
        
        # connection 없으면 에러 - 명시적 바인딩 필수
        if not broker_connection:
            context.log("error", "RealAccountNode: connection 필드가 필수입니다. connection: \"{{ nodes.broker.connection }}\"를 설정하세요.", node_id)
            return {"error": "Missing connection field - set connection: \"{{ nodes.broker.connection }}\""}
        
        provider = broker_connection.get("provider", "ls-sec.co.kr")
        product = broker_connection.get("product", "overseas_stock")
        
        context.log("info", f"RealAccount: provider={provider}, product={product}, stay_connected={stay_connected}", node_id)
        
        # 이미 persistent tracker가 있으면 재사용 (stay_connected=True인 경우)
        if stay_connected and context.has_persistent(node_id):
            tracker = context.get_persistent(node_id)
            context.log("info", "Reusing existing tracker", node_id)
            return self._get_tracker_data(tracker)
        
        # ========================================
        # 브로커별 분기 처리
        # ========================================
        if provider == "ls-sec.co.kr":
            return await self._execute_ls(node_id, product, config, context, stay_connected, sync_interval_sec)
        else:
            context.log("error", f"Unsupported provider: {provider}", node_id)
            return self._empty_result(f"Unsupported provider: {provider}")

    async def _execute_ls(
        self,
        node_id: str,
        product: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        stay_connected: bool,
        sync_interval_sec: int,
    ) -> Dict[str, Any]:
        """LS증권 실시간 계좌 조회 (WebSocket)"""
        from datetime import datetime
        
        
        # secrets에서 인증 정보 가져오기
        credential = context.get_credential()
        
        if not credential:
            context.log("error", "Credential not found in secrets", node_id)
            return self._empty_result("Missing credentials")
        
        appkey = credential.get("appkey")
        appsecret = credential.get("appsecret")
        paper_trading = credential.get("paper_trading", False)
        
        
        if not appkey or not appsecret:
            context.log("error", "appkey/appsecret not found in credential", node_id)
            return self._empty_result("Missing appkey/appsecret")
        
        try:
            ls, success, error = ensure_ls_login(
                appkey, appsecret, paper_trading, context, node_id,
                caller_name=f"RealAccountNode({product})"
            )
            if not success:
                return self._empty_result(error)
            
            # ========================================
            # 항상 WebSocket + Tracker 사용 (진짜 "Real")
            # stay_connected에 따라 cleanup 대상 여부만 결정
            # ========================================
            return await self._ls_with_tracker(
                ls, node_id, product, config, context, 
                sync_interval_sec, stay_connected
            )
                
        except ImportError as e:
            context.log("error", f"finance package not available: {e}", node_id)
            return self._empty_result(f"finance package error: {e}")
        except RuntimeError:
            # API 에러 등으로 플로우 중단이 필요한 경우 - 상위로 전파
            raise
        except Exception as e:
            context.log("error", f"Unexpected error: {e}", node_id)
            return self._empty_result(str(e))

    async def _ls_with_tracker(
        self,
        ls,
        node_id: str,
        product: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        sync_interval_sec: int,
        stay_connected: bool = True,
    ) -> Dict[str, Any]:
        """
        LS증권 StockAccountTracker를 사용한 실시간 계좌 추적
        
        - WebSocket으로 틱마다 수익률 계산
        - REST API로 주기적 데이터 동기화
        - 연결 끊김 시 토큰 확인 후 재연결
        
        stay_connected:
        - True: persistent로 등록 (플로우 끝나도 유지)
        - False: cleanup_on_flow_end로 등록 (플로우 끝나면 종료)
        """
        
        # Product별 분기 처리
        if product == "overseas_stock":
            return await self._ls_stock_with_tracker(
                ls, node_id, config, context, sync_interval_sec, stay_connected
            )
        elif product == "overseas_futures":
            return await self._ls_futureoption_with_tracker(
                ls, node_id, config, context, sync_interval_sec, stay_connected
            )
        else:
            context.log("warning", f"Unsupported product for RealAccountNode: {product}", node_id)
            raise ValueError(f"RealAccountNode does not support product '{product}' yet. Use AccountNode for REST API query.")

    async def _ls_stock_with_tracker(
        self,
        ls,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        sync_interval_sec: int,
        stay_connected: bool = True,
    ) -> Dict[str, Any]:
        """해외주식 실시간 계좌 추적 (StockAccountTracker)"""
        from decimal import Decimal
        
        try:
            # 수수료/세금 설정 읽기 (% → 비율 변환)
            commission_rate = Decimal(str(config.get("commission_rate", 0.25))) / 100
            tax_rate = Decimal(str(config.get("tax_rate", 0.0))) / 100
            
            context.log("info", f"Commission rate: {float(commission_rate)*100:.2f}%, Tax rate: {float(tax_rate)*100:.2f}%", node_id)
            
            # 실시간 연결 클라이언트 가져오기 (tracker 생성 전에 필요)
            real_client = ls.overseas_stock().real()
            if not await real_client.is_connected():
                await real_client.connect()
            
            # StockAccountTracker 생성 (수수료/세금 적용)
            tracker = ls.overseas_stock().accno().account_tracker(
                real_client=real_client,
                refresh_interval=sync_interval_sec,
                commission_rates={"DEFAULT": commission_rate},
                tax_rates={"DEFAULT": tax_rate},
            )
            
            # ReconnectHandler 설정 (토큰 갱신 포함)
            token_manager = ls._token_manager if hasattr(ls, '_token_manager') else None
            reconnect_handler = ReconnectHandler(token_manager)
            
            # 연결 끊김 콜백 등록
            async def on_disconnect():
                can_retry = await reconnect_handler.handle_disconnect()
                if can_retry:
                    try:
                        # 토큰 갱신은 ReconnectHandler가 처리했으므로 재연결만
                        if not await real_client.is_connected():
                            await real_client.connect()
                        reconnect_handler.reset()
                        context.log("info", "Reconnected successfully", node_id)
                    except Exception as e:
                        context.log("error", f"Reconnect failed: {e}", node_id)
                        await on_disconnect()  # 재귀 재시도
                else:
                    context.fail(f"Max reconnect attempts exceeded for {node_id}")
            
            # 트리거할 하위 노드 목록 (클로저로 캡처)
            trigger_nodes = config.get("_trigger_on_update_nodes", [])
            logger.debug(f"[RealAccountNode] 트리거 대상 노드: {trigger_nodes}")
            
            # 현재 이벤트 루프 캡처 (콜백에서 사용)
            loop = asyncio.get_running_loop()
            
            # 포지션 변경 콜백 등록 (이벤트 발생용)
            def on_position_change(positions: Dict):
                # 포지션 데이터를 직렬화 가능한 형태로 변환
                serialized_positions = {}
                for sym, pos in positions.items():
                    serialized_positions[sym] = {
                        "symbol": sym,
                        "name": getattr(pos, 'symbol_name', sym),
                        "qty": pos.quantity,
                        "avg_price": float(pos.buy_price),
                        "current_price": float(pos.current_price),
                        "pnl_rate": float(pos.pnl_rate) if pos.pnl_rate else 0,
                        "pnl_amount": float(pos.pnl_amount) if pos.pnl_amount else 0,
                        "currency": getattr(pos, 'currency_code', 'USD'),
                    }
                
                # 컨텍스트에 최신 데이터 저장
                context.set_output(node_id, "positions", serialized_positions)
                
                # 🆕 SSE로 output 업데이트 브로드캐스트 (스레드 안전하게)
                asyncio.run_coroutine_threadsafe(
                    context.notify_output_update(
                        node_id=node_id,
                        node_type="RealAccountNode",
                        outputs={"positions": serialized_positions},
                    ),
                    loop
                )
                
                # 디버깅용 logger
                from datetime import datetime
                logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 해외주식 포지션 업데이트:")
                for sym, pos in positions.items():
                    if hasattr(pos, 'pnl_rate'):
                        logger.debug(f"  {sym}: 현재가=${pos.current_price:.2f}, 수익률={pos.pnl_rate:.2f}%")
                logger.debug(f"  → 트리거할 노드: {trigger_nodes}")
                
                # 이벤트 큐에 추가 (스레드 안전하게)
                asyncio.run_coroutine_threadsafe(
                    context.emit_event(
                        event_type="realtime_update",
                        source_node_id=node_id,
                        data={"positions": serialized_positions},
                        trigger_nodes=trigger_nodes,
                    ),
                    loop
                )
            
            tracker.on_position_change(on_position_change)
            
            # Tracker 시작
            await tracker.start()
            
            # 🆕 서버 에러 확인 - 에러 시 플로우 중단
            tracker_errors = tracker.get_last_errors()
            if tracker_errors:
                for error_key, error_msg in tracker_errors.items():
                    context.log("error", f"⚠️ 증권사 API 오류 ({error_key}): {error_msg}", node_id)
                
                # 에러 발생 시 플로우 중단 (빈 데이터로 진행하면 잘못된 의사결정 위험)
                error_summary = ", ".join(tracker_errors.values())
                raise RuntimeError(f"RealAccountNode 초기화 실패: {error_summary}")
            
            # ========================================
            # stay_connected에 따라 등록 방식 결정
            # ========================================
            if stay_connected:
                # Persistent로 등록 (플로우 끝나도 유지, Job 종료 시 cleanup)
                context.register_persistent(node_id, tracker)
                context.log("info", f"StockAccountTracker started (stay_connected=True, sync_interval={sync_interval_sec}s)", node_id)
            else:
                # 플로우 끝나면 cleanup 대상으로 등록
                context.register_cleanup_on_flow_end(node_id, tracker)
                context.log("info", f"StockAccountTracker started (stay_connected=False, will cleanup after flow)", node_id)
            
            # 초기 데이터 반환 (여기까지 도달했다면 에러 없이 정상)
            result = self._get_stock_tracker_data(tracker)
            
            # 데이터가 비어있는지 확인 (에러 없이 정상 케이스)
            positions_count = len(result.get('positions', {}))
            if positions_count == 0:
                context.log("info", "ℹ️ 해외주식 보유종목이 없습니다. (잔고가 없거나 장 마감 시간일 수 있음)", node_id)
            
            # SSE로 즉시 전송되도록 context.set_output 호출
            for key, value in result.items():
                context.set_output(node_id, key, value)
            
            # 🆕 초기 데이터도 SSE로 브로드캐스트
            asyncio.create_task(context.notify_output_update(
                node_id=node_id,
                node_type="RealAccountNode",
                outputs=result,
            ))
            
            logger.debug(f"\n{'='*60}")
            logger.debug(f"[RealAccountNode] 해외주식 실시간 계좌 데이터")
            logger.debug(f"{'='*60}")
            logger.debug(f"보유 종목: {result.get('symbols', [])}")
            logger.debug(f"잔고: {result.get('balance', {})}")
            for sym, pos in result.get('positions', {}).items():
                logger.debug(f"  - {sym}: 수량={pos.get('qty')}, 평단가=${pos.get('avg_price'):.2f}, 현재가=${pos.get('current_price'):.2f}, 수익률={pos.get('pnl_rate'):.2f}%")
            logger.debug(f"{'='*60}\n")
            
            context.log("info", f"Initial account data loaded: {len(result.get('positions', {}))} positions", node_id)
            return result
            
        except Exception as e:
            context.log("error", f"Stock tracker setup failed: {e}", node_id)
            raise

    async def _ls_futureoption_with_tracker(
        self,
        ls,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        sync_interval_sec: int,
        stay_connected: bool = True,
    ) -> Dict[str, Any]:
        """
        해외선물 실시간 계좌 추적 (FuturesAccountTracker)
        
        - OVC WebSocket으로 실시간 시세 수신
        - TC1/TC2/TC3 WebSocket으로 주문 이벤트 수신
        - CIDBQ01500 등으로 주기적 잔고 동기화
        """
        from decimal import Decimal
        
        try:
            # 해외선물 수수료 설정 읽기 (계약당 고정 금액, USD)
            futures_fee_per_contract = Decimal(str(config.get("futures_fee_per_contract", 7.5)))
            
            context.log("info", f"Futures fee per contract: ${float(futures_fee_per_contract):.2f} (one-way)", node_id)
            
            # 각 클라이언트 준비
            accno = ls.overseas_futureoption().accno()
            market = ls.overseas_futureoption().market()
            real = ls.overseas_futureoption().real()
            
            # 실시간 WebSocket 연결
            if not await real.is_connected():
                await real.connect()
            
            # FuturesAccountTracker 생성 (계약당 수수료 적용)
            tracker = accno.account_tracker(
                market_client=market,
                real_client=real,
                refresh_interval=sync_interval_sec,
                commission_rate=futures_fee_per_contract,  # 계약당 수수료
            )
            
            # ReconnectHandler 설정
            token_manager = ls._token_manager if hasattr(ls, '_token_manager') else None
            reconnect_handler = ReconnectHandler(token_manager)
            
            # 연결 끊김 콜백
            async def on_disconnect():
                can_retry = await reconnect_handler.handle_disconnect()
                if can_retry:
                    try:
                        if not await real.is_connected():
                            await real.connect()
                        reconnect_handler.reset()
                        context.log("info", "Futures WebSocket reconnected successfully", node_id)
                    except Exception as e:
                        context.log("error", f"Futures reconnect failed: {e}", node_id)
                        await on_disconnect()
                else:
                    context.fail(f"Max reconnect attempts exceeded for {node_id}")
            
            # 트리거할 하위 노드 목록 (클로저로 캡처)
            trigger_nodes = config.get("_trigger_on_update_nodes", [])
            logger.debug(f"[RealAccountNode/Futures] 트리거 대상 노드: {trigger_nodes}")
            
            # 현재 이벤트 루프 캡처 (콜백에서 사용)
            loop = asyncio.get_running_loop()
            
            # 포지션 변경 콜백 (실시간 이벤트)
            def on_position_change(positions):
                # 포지션 데이터를 직렬화 가능한 형태로 변환
                serialized_positions = {}
                for sym, pos in positions.items():
                    # realtime_pnl이 None이 아닌 경우만 안전하게 접근
                    realtime_pnl = getattr(pos, 'realtime_pnl', None)
                    pnl_rate = 0.0
                    if realtime_pnl is not None and hasattr(realtime_pnl, 'pnl_rate'):
                        pnl_rate = float(getattr(realtime_pnl, 'pnl_rate', 0) or 0)
                    elif hasattr(pos, 'pnl_rate') and pos.pnl_rate is not None:
                        pnl_rate = float(pos.pnl_rate)
                    
                    is_long = getattr(pos, 'is_long', True)
                    serialized_positions[sym] = {
                        "symbol": sym,
                        "exchange": getattr(pos, 'exchange_code', ''),
                        "name": getattr(pos, 'symbol_name', sym),
                        "is_long": is_long,
                        "direction": "LONG" if is_long else "SHORT",
                        "qty": int(getattr(pos, 'quantity', 0)),
                        "entry_price": float(getattr(pos, 'entry_price', 0)),
                        "current_price": float(getattr(pos, 'current_price', 0)),
                        "pnl_amount": float(getattr(pos, 'pnl_amount', 0) or 0),
                        "pnl_rate": pnl_rate,
                        "currency": getattr(pos, 'currency', 'USD'),
                    }
                
                # 컨텍스트에 최신 데이터 저장
                context.set_output(node_id, "positions", serialized_positions)
                
                # 🆕 SSE로 output 업데이트 브로드캐스트 (스레드 안전하게)
                asyncio.run_coroutine_threadsafe(
                    context.notify_output_update(
                        node_id=node_id,
                        node_type="RealAccountNode",
                        outputs={"positions": serialized_positions},
                    ),
                    loop
                )
                
                # 디버깅용 logger
                from datetime import datetime
                logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 해외선물 포지션 업데이트:")
                for sym, pos in positions.items():
                    direction = 'LONG' if getattr(pos, 'is_long', True) else 'SHORT'
                    exchange = getattr(pos, 'exchange_code', '')
                    pnl = getattr(pos, 'pnl_amount', 0)
                    logger.debug(f"  {sym}@{exchange} ({direction}): 현재가=${getattr(pos, 'current_price', 0):.2f}, 손익=${pnl:.2f}")
                logger.debug(f"  → 트리거할 노드: {trigger_nodes}")
                
                # 이벤트 큐에 추가 (스레드 안전하게)
                asyncio.run_coroutine_threadsafe(
                    context.emit_event(
                        event_type="realtime_update",
                        source_node_id=node_id,
                        data={"positions": serialized_positions},
                        trigger_nodes=trigger_nodes,
                    ),
                    loop
                )
            
            # 잔고 변경 콜백
            def on_balance_change(balance):
                context.set_output(node_id, "balance", balance)
                asyncio.run_coroutine_threadsafe(
                    context.emit_event(
                        event_type="balance_update",
                        source_node_id=node_id,
                        data={"balance": balance},
                        trigger_nodes=[],
                    ),
                    loop
                )
            
            tracker.on_position_change(on_position_change)
            tracker.on_balance_change(on_balance_change)
            
            # Tracker 시작
            await tracker.start()
            
            # 🆕 서버 에러 확인 - 에러 시 플로우 중단
            tracker_errors = tracker.get_last_errors()
            if tracker_errors:
                for error_key, error_msg in tracker_errors.items():
                    context.log("error", f"⚠️ 증권사 API 오류 ({error_key}): {error_msg}", node_id)
                
                # 에러 발생 시 플로우 중단 (빈 데이터로 진행하면 잘못된 의사결정 위험)
                error_summary = ", ".join(tracker_errors.values())
                raise RuntimeError(f"RealAccountNode 초기화 실패: {error_summary}")
            
            # stay_connected에 따라 등록
            if stay_connected:
                context.register_persistent(node_id, tracker)
                context.log("info", f"FuturesAccountTracker started (stay_connected=True, sync_interval={sync_interval_sec}s)", node_id)
            else:
                context.register_cleanup_on_flow_end(node_id, tracker)
                context.log("info", f"FuturesAccountTracker started (stay_connected=False, will cleanup after flow)", node_id)
            
            # 초기 데이터 반환 (여기까지 도달했다면 에러 없이 정상)
            result = self._get_futures_tracker_data(tracker)
            
            # 데이터가 비어있는지 확인 (에러 없이 정상 케이스)
            positions_count = len(result.get('positions', {}))
            if positions_count == 0:
                context.log("info", "ℹ️ 해외선물 보유종목이 없습니다. (포지션이 없거나 장 마감 시간일 수 있음)", node_id)
            
            # SSE로 즉시 전송되도록 context.set_output 호출
            for key, value in result.items():
                context.set_output(node_id, key, value)
            
            # 🆕 초기 데이터도 SSE로 브로드캐스트
            asyncio.create_task(context.notify_output_update(
                node_id=node_id,
                node_type="RealAccountNode",
                outputs=result,
            ))
            
            logger.debug(f"\n{'='*60}")
            logger.debug(f"[RealAccountNode] 해외선물 실시간 계좌 데이터")
            logger.debug(f"{'='*60}")
            logger.debug(f"보유 종목: {result.get('symbols', [])}")
            logger.debug(f"잔고: {result.get('balance', {})}")
            for sym, pos in result.get('positions', {}).items():
                direction = '롱' if pos.get('is_long') else '숏'
                logger.debug(f"  - {sym} ({direction}): 수량={pos.get('qty')}, 진입가=${pos.get('entry_price'):.2f}, 현재가=${pos.get('current_price'):.2f}, 손익=${pos.get('pnl_amount'):.2f}")
            logger.debug(f"미체결: {list(result.get('open_orders', {}).keys())}")
            logger.debug(f"{'='*60}\n")
            
            context.log("info", f"Initial futures data loaded: {len(result.get('positions', {}))} positions", node_id)
            return result
            
        except Exception as e:
            context.log("error", f"Futures tracker setup failed: {e}", node_id)
            raise

    def _get_stock_tracker_data(self, tracker) -> Dict[str, Any]:
        """해외주식 Tracker에서 현재 데이터 추출"""
        positions = {}
        for symbol, pos in tracker.get_positions().items():
            positions[symbol] = {
                "symbol": symbol,
                "name": getattr(pos, 'name', getattr(pos, 'symbol_name', symbol)),
                "qty": pos.quantity,
                "avg_price": float(pos.buy_price),
                "current_price": float(pos.current_price),
                "pnl_rate": float(pos.pnl_rate) if pos.pnl_rate else 0,
                "pnl_amount": float(pos.pnl_amount) if pos.pnl_amount else 0,
                "currency": getattr(pos, 'currency_code', 'USD'),
                "eval_amount": float(pos.eval_amount) if pos.eval_amount else 0,
                "market_code": getattr(pos, 'market_code', ''),
            }
        
        symbols = list(positions.keys())
        
        # balance를 JSON 직렬화 가능한 형태로 변환
        # get_balances()는 Dict[str, StockBalanceInfo]를 반환 (통화별)
        raw_balances = tracker.get_balances()
        balance = {}
        
        if isinstance(raw_balances, dict):
            # 통화별 잔고 변환
            for currency, bal_info in raw_balances.items():
                if hasattr(bal_info, 'model_dump'):
                    # Pydantic 모델
                    bal_dict = bal_info.model_dump()
                    balance[currency] = {
                        k: float(v) if hasattr(v, '__float__') else str(v)
                        for k, v in bal_dict.items() 
                        if v is not None and k != 'last_updated'
                    }
                elif hasattr(bal_info, '__dict__'):
                    # dataclass 또는 일반 객체
                    balance[currency] = {
                        "deposit": float(getattr(bal_info, 'deposit', 0)),
                        "orderable_amount": float(getattr(bal_info, 'orderable_amount', 0)),
                        "eval_amount": float(getattr(bal_info, 'eval_amount', 0)),
                        "pnl_amount": float(getattr(bal_info, 'pnl_amount', 0)),
                        "pnl_rate": float(getattr(bal_info, 'pnl_rate', 0)),
                    }
                else:
                    balance[currency] = bal_info
            
            # 총 잔고 요약 추가 (USD 기준 또는 첫 번째 통화)
            if balance:
                primary = balance.get('USD') or next(iter(balance.values()), {})
                balance['_summary'] = {
                    "total_deposit": sum(b.get('deposit', 0) for b in balance.values() if isinstance(b, dict) and 'deposit' in b),
                    "total_eval_amount": sum(b.get('eval_amount', 0) for b in balance.values() if isinstance(b, dict) and 'eval_amount' in b),
                    "total_pnl_amount": sum(b.get('pnl_amount', 0) for b in balance.values() if isinstance(b, dict) and 'pnl_amount' in b),
                }
        else:
            balance = {"cash": 0.0, "total_value": 0.0}
        
        # open_orders 추출
        open_orders = {}
        if hasattr(tracker, 'get_open_orders'):
            for order_no, order in tracker.get_open_orders().items():
                open_orders[order_no] = {
                    "order_no": order_no,
                    "symbol": getattr(order, 'symbol', ''),
                    "exchange": getattr(order, 'exchange_code', getattr(order, 'market_code', '')),
                    "order_type": getattr(order, 'order_type', ''),
                    "order_price": float(getattr(order, 'order_price', 0)),
                    "order_qty": int(getattr(order, 'order_qty', 0)),
                    "filled_qty": int(getattr(order, 'filled_qty', 0)),
                    "remaining_qty": int(getattr(order, 'remaining_qty', getattr(order, 'order_qty', 0)) or 0),
                }
        
        return {
            "symbols": symbols,
            "held_symbols": symbols,
            "positions": positions,
            "balance": balance,
            "open_orders": open_orders,
        }

    def _get_futures_tracker_data(self, tracker) -> Dict[str, Any]:
        """해외선물 Tracker에서 현재 데이터 추출"""
        positions = {}
        for symbol, pos in tracker.get_positions().items():
            # realtime_pnl이 None이 아닌 dict인 경우만 .get() 호출
            realtime_pnl = getattr(pos, 'realtime_pnl', None)
            pnl_rate = 0.0
            if realtime_pnl is not None and hasattr(realtime_pnl, 'pnl_rate'):
                pnl_rate = float(getattr(realtime_pnl, 'pnl_rate', 0) or 0)
            elif hasattr(pos, 'pnl_rate') and pos.pnl_rate is not None:
                pnl_rate = float(pos.pnl_rate)
            
            is_long = getattr(pos, 'is_long', True)
            positions[symbol] = {
                "symbol": symbol,
                "exchange": getattr(pos, 'exchange_code', ''),
                "name": getattr(pos, 'symbol_name', symbol),
                "is_long": is_long,
                "direction": "LONG" if is_long else "SHORT",
                "qty": int(getattr(pos, 'quantity', 0)),
                "entry_price": float(getattr(pos, 'entry_price', 0)),
                "current_price": float(getattr(pos, 'current_price', 0)),
                "pnl_amount": float(getattr(pos, 'pnl_amount', 0) or 0),
                "pnl_rate": pnl_rate,
                "currency": getattr(pos, 'currency', 'USD'),
            }
        
        symbols = list(positions.keys())
        
        # balance 추출
        raw_balance = tracker.get_balance()
        if hasattr(raw_balance, 'model_dump'):
            balance = {k: float(v) if isinstance(v, (int, float)) or hasattr(v, '__float__') else str(v) 
                      for k, v in raw_balance.model_dump().items() if v is not None}
        elif hasattr(raw_balance, '__dict__'):
            balance = {
                "deposit": float(getattr(raw_balance, 'deposit', 0)),
                "orderable_amount": float(getattr(raw_balance, 'orderable_amount', 0)),
                "margin": float(getattr(raw_balance, 'total_margin', 0)),
                "pnl_amount": float(getattr(raw_balance, 'pnl_amount', 0)),
            }
        elif isinstance(raw_balance, dict):
            balance = raw_balance
        else:
            balance = {"deposit": 0.0, "orderable_amount": 0.0}
        
        # open_orders 추출
        open_orders = {}
        if hasattr(tracker, 'get_open_orders'):
            for order_no, order in tracker.get_open_orders().items():
                is_long = getattr(order, 'is_long', True)
                open_orders[order_no] = {
                    "order_no": order_no,
                    "symbol": getattr(order, 'symbol', ''),
                    "exchange": getattr(order, 'exchange_code', ''),
                    "is_long": is_long,
                    "direction": "LONG" if is_long else "SHORT",
                    "order_price": float(getattr(order, 'order_price', 0)),
                    "order_qty": int(getattr(order, 'order_qty', 0)),
                    "remaining_qty": int(getattr(order, 'remaining_qty', 0)),
                }
        
        return {
            "symbols": symbols,
            "held_symbols": symbols,
            "positions": positions,
            "balance": balance,
            "open_orders": open_orders,
        }

    def _get_tracker_data(self, tracker) -> Dict[str, Any]:
        """Tracker에서 현재 데이터 추출 (하위 호환용)"""
        # 타입에 따라 분기
        tracker_type = type(tracker).__name__
        if "Futures" in tracker_type:
            return self._get_futures_tracker_data(tracker)
        else:
            return self._get_stock_tracker_data(tracker)

    def _empty_result(self, error: str = "") -> Dict[str, Any]:
        """빈 결과 반환"""
        result = {
            "symbols": [],
            "held_symbols": [],  # 별칭
            "positions": {},
            "balance": {"cash": 0.0, "total_value": 0.0},
        }
        if error:
            result["error"] = error
        return result


class RealMarketDataNodeExecutor(NodeExecutorBase):
    """RealMarketDataNode executor - 실시간 시세 (WebSocket)"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        from programgarden_core.exceptions import ValidationError, ConnectionError
        
        # ========================================
        # 1. BrokerNode connection 획득 (config 바인딩 필수)
        # ========================================
        broker_connection = config.get("connection")
        
        # connection 없으면 에러 - 명시적 바인딩 필수
        if not broker_connection:
            error_msg = (
                f"RealMarketDataNode: connection 필드가 필수입니다. "
                f"connection: \"{{{{ nodes.broker.connection }}}}\"를 설정하세요."
            )
            context.log("error", error_msg, node_id)
            raise ConnectionError(error_msg)
        
        broker_product = broker_connection.get("product", "overseas_stock")
        
        # ========================================
        # 2. Symbols 획득 (필드 우선, WatchlistNode 폴백)
        # ========================================
        watchlist_output = context.find_parent_output(node_id, "WatchlistNode")
        symbols_raw = self._resolve_symbols(node_id, config, context, watchlist_output)
        
        if not symbols_raw:
            error_msg = (
                f"RealMarketDataNode requires symbols to subscribe. "
                f"Either set 'symbols' field directly or connect WatchlistNode/AccountNode. "
                f"Node '{node_id}' has no symbols configured."
            )
            context.log("error", error_msg, node_id)
            raise ValidationError(error_msg, node_id=node_id)
        
        # symbols 정규화: dict 형태 [{exchange, symbol}] → 문자열 리스트
        symbols = []
        symbols_with_exchange = []  # 거래소 코드 포함 형식
        for entry in symbols_raw:
            if isinstance(entry, dict):
                symbol = entry.get("symbol", "")
                exchange = entry.get("exchange", "")
                symbols.append(symbol)
                symbols_with_exchange.append({"symbol": symbol, "exchange": exchange})
            elif isinstance(entry, str):
                symbols.append(entry)
                symbols_with_exchange.append({"symbol": entry, "exchange": ""})
        
        # ========================================
        # 3. stay_connected 설정
        # ========================================
        stay_connected = config.get("stay_connected", True)
        
        # ========================================
        # 4. 상품별 실시간 WebSocket 연결
        # ========================================
        if broker_product == "overseas_stock":
            return await self._execute_stock(
                node_id, broker_connection, symbols, symbols_with_exchange, 
                symbols_raw, stay_connected, context
            )
        elif broker_product == "overseas_futures":
            return await self._execute_futures(
                node_id, broker_connection, symbols, symbols_with_exchange,
                symbols_raw, stay_connected, context
            )
        else:
            raise ValidationError(f"Unsupported product: {broker_product}", node_id=node_id)
    
    async def _execute_stock(
        self,
        node_id: str,
        broker_connection: Dict[str, Any],
        symbols: List[str],
        symbols_with_exchange: List[Dict[str, str]],
        symbols_raw: List,
        stay_connected: bool,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """해외주식 실시간 시세 (GSC)"""
        import asyncio
        from datetime import datetime
        
        appkey = broker_connection.get("appkey", "")
        appsecret = broker_connection.get("appsecret", "")
        paper_trading = broker_connection.get("paper_trading", False)
        
        # 현재 이벤트 루프 캡처 (콜백에서 사용)
        loop = asyncio.get_running_loop()
        
        # LS 로그인
        ls, success, error = ensure_ls_login(appkey, appsecret, paper_trading, context, node_id, "RealMarketDataNode")
        if not success:
            from programgarden_core.exceptions import ConnectionError
            raise ConnectionError(f"LS login failed: {error}")
        
        # 실시간 클라이언트 생성 및 연결
        real_client = ls.overseas_stock().real()
        await real_client.connect()
        context.log("info", f"WebSocket connected for overseas_stock (paper_trading={paper_trading})", node_id)
        
        # GSC 구독 설정
        gsc = real_client.GSC()
        
        # 거래소 코드 포함 심볼 생성: 81AAPL, 82TSLA 형식
        subscribe_symbols = []
        for entry in symbols_with_exchange:
            symbol = entry.get("symbol", "")
            exchange = entry.get("exchange", "")
            # 거래소 코드 매핑: NASDAQ=82, NYSE=81, AMEX=83
            exchange_code = self._get_stock_exchange_code(exchange)
            subscribe_symbols.append(f"{exchange_code}{symbol}")
        
        # 실시간 OHLCV 데이터 저장소 (콜백에서 틱마다 누적)
        # 형식: {symbol: {date, open, high, low, close, volume}}
        ohlcv_bars = {}
        
        # 트리거할 하위 노드 목록 (RealOrderEventNode 패턴)
        trigger_nodes = []
        
        def on_tick(resp):
            """GSC 틱 데이터 수신 콜백 - OHLCV 형식으로 누적"""
            try:
                body = resp.body if hasattr(resp, 'body') else None
                
                if body is None:
                    context.log("debug", f"GSC subscription confirmed: {resp.rsp_msg if hasattr(resp, 'rsp_msg') else ''}", node_id)
                    return
                
                # GSCRealResponseBody 필드 추출
                symbol = getattr(body, 'symbol', '')
                price = float(getattr(body, 'price', 0) or 0)
                tick_open = float(getattr(body, 'open', 0) or 0)
                tick_high = float(getattr(body, 'high', 0) or 0)
                tick_low = float(getattr(body, 'low', 0) or 0)
                volume = int(getattr(body, 'totq', 0) or 0)
                date = getattr(body, 'kordate', '') or datetime.now().strftime('%Y%m%d')
                
                if symbol and price > 0:
                    # OHLCV 바 업데이트 (당일 누적)
                    if symbol not in ohlcv_bars or ohlcv_bars[symbol].get('date') != date:
                        # 첫 틱 또는 새 날짜: 초기화
                        ohlcv_bars[symbol] = {
                            "date": date,
                            "open": tick_open if tick_open > 0 else price,
                            "high": tick_high if tick_high > 0 else price,
                            "low": tick_low if tick_low > 0 else price,
                            "close": price,
                            "volume": volume,
                        }
                    else:
                        # 이후 틱: 누적 (high/low는 틱에서 제공되므로 그대로 사용)
                        bar = ohlcv_bars[symbol]
                        if tick_high > 0:
                            bar["high"] = tick_high
                        if tick_low > 0:
                            bar["low"] = tick_low
                        bar["close"] = price
                        bar["volume"] = volume
                    
                    # 콘솔 출력
                    logger.debug(f"\n{'='*60}")
                    logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 [{node_id}] GSC 체결")
                    logger.debug(f"  종목: {symbol}  가격: ${price:,.2f}  거래량: {volume:,}")
                    logger.debug(f"  OHLCV: O={ohlcv_bars[symbol]['open']:.2f} H={ohlcv_bars[symbol]['high']:.2f} L={ohlcv_bars[symbol]['low']:.2f} C={price:.2f}")
                    logger.debug(f"{'='*60}\n")
                    
                    # OHLCV 데이터 형식으로 변환: {symbol: [bar]}
                    ohlcv_data = {s: [bar] for s, bar in ohlcv_bars.items()}
                    
                    # context에 업데이트
                    context.set_output(node_id, "ohlcv_data", ohlcv_data)
                    context.set_output(node_id, "data", ohlcv_data)
                    
                    output_data = {
                        "ohlcv_data": ohlcv_data,
                        "symbol": symbol,
                        "data": ohlcv_data,
                    }
                    
                    # SSE 브로드캐스트
                    asyncio.run_coroutine_threadsafe(
                        context.notify_output_update(
                            node_id=node_id,
                            node_type="RealMarketDataNode",
                            outputs=output_data,
                        ),
                        loop
                    )
                    
                    # 후속 노드 트리거
                    asyncio.run_coroutine_threadsafe(
                        context.emit_event(
                            event_type="market_data",
                            source_node_id=node_id,
                            data=output_data,
                            trigger_nodes=trigger_nodes,
                        ),
                        loop
                    )
            except Exception as e:
                context.log("warning", f"GSC parse error: {e}", node_id)
        
        gsc.on_gsc_message(on_tick)
        gsc.add_gsc_symbols(symbols=subscribe_symbols)
        context.log("info", f"Subscribed to GSC: {subscribe_symbols} (체결 시 실시간 업데이트)", node_id)
        
        # 타임아웃 없음 - 체결은 언제 올지 모름 (장 외 시간에는 오지 않음)
        # stay_connected=true면 구독 유지, false면 즉시 종료
        
        if not stay_connected:
            # stay_connected=False: 구독만 설정하고 즉시 종료 (1회성 조회 용도 아님)
            context.log("warning", f"stay_connected=False for realtime node - no data will be received", node_id)
            gsc.remove_gsc_symbols(symbols=subscribe_symbols)
            await real_client.close()
            context.log("info", f"WebSocket disconnected (stay_connected=False)", node_id)
        else:
            # 연결 유지: register_persistent로 WebSocket 연결 유지 (RealOrderEventNode 패턴)
            context.register_persistent(node_id, real_client)
            context.set_node_state(node_id, "gsc", gsc)
            context.set_node_state(node_id, "subscribe_symbols", subscribe_symbols)
            context.log("info", f"GSC subscription active - waiting for ticks...", node_id)
        
        # 초기 반환: 빈 OHLCV 데이터 (체결 시 콜백에서 업데이트)
        return {
            "symbols": symbols_raw,
            "ohlcv_data": {},
            "data": {},
        }
    
    async def _execute_futures(
        self,
        node_id: str,
        broker_connection: Dict[str, Any],
        symbols: List[str],
        symbols_with_exchange: List[Dict[str, str]],
        symbols_raw: List,
        stay_connected: bool,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """해외선물 실시간 시세 (OVC)"""
        import asyncio
        from datetime import datetime
        
        appkey = broker_connection.get("appkey", "")
        appsecret = broker_connection.get("appsecret", "")
        paper_trading = broker_connection.get("paper_trading", False)
        
        # 현재 이벤트 루프 캡처 (콜백에서 사용)
        loop = asyncio.get_running_loop()
        
        # LS 로그인
        ls, success, error = ensure_ls_login(appkey, appsecret, paper_trading, context, node_id, "RealMarketDataNode")
        if not success:
            from programgarden_core.exceptions import ConnectionError
            raise ConnectionError(f"LS login failed: {error}")
        
        # 실시간 클라이언트 생성 및 연결
        real_client = ls.overseas_futureoption().real()
        await real_client.connect()
        context.log("info", f"WebSocket connected for overseas_futures (paper_trading={paper_trading})", node_id)
        
        # OVC 구독 설정
        ovc = real_client.OVC()
        
        # 선물 심볼 형식: "ESU25   " (8자리 패딩)
        subscribe_symbols = []
        for entry in symbols_with_exchange:
            symbol = entry.get("symbol", "")
            # 8자리로 패딩
            padded_symbol = symbol.ljust(8)
            subscribe_symbols.append(padded_symbol)
        
        # 실시간 OHLCV 데이터 저장소 (콜백에서 틱마다 누적)
        ohlcv_bars = {}
        
        # 트리거할 하위 노드 목록
        trigger_nodes = []
        
        def on_tick(resp):
            """OVC 틱 데이터 수신 콜백 - OHLCV 형식으로 누적"""
            try:
                if not hasattr(resp, 'body') or resp.body is None:
                    context.log("debug", f"OVC subscription confirmed: {resp.rsp_msg if hasattr(resp, 'rsp_msg') else 'OK'}", node_id)
                    return
                
                body = resp.body
                symbol = getattr(body, 'symbol', '')
                symbol = symbol.strip() if symbol else ''
                
                # OVC 필드 추출
                curpr = getattr(body, 'curpr', '0')
                tick_open = getattr(body, 'open', '0')
                tick_high = getattr(body, 'high', '0')
                tick_low = getattr(body, 'low', '0')
                totq = getattr(body, 'totq', '0')
                date = getattr(body, 'kordate', '') or datetime.now().strftime('%Y%m%d')
                
                price = float(curpr) if curpr else 0.0
                tick_open_f = float(tick_open) if tick_open else 0.0
                tick_high_f = float(tick_high) if tick_high else 0.0
                tick_low_f = float(tick_low) if tick_low else 0.0
                volume = int(float(totq)) if totq else 0
                
                if symbol and price > 0:
                    # OHLCV 바 업데이트
                    if symbol not in ohlcv_bars or ohlcv_bars[symbol].get('date') != date:
                        ohlcv_bars[symbol] = {
                            "date": date,
                            "open": tick_open_f if tick_open_f > 0 else price,
                            "high": tick_high_f if tick_high_f > 0 else price,
                            "low": tick_low_f if tick_low_f > 0 else price,
                            "close": price,
                            "volume": volume,
                        }
                    else:
                        bar = ohlcv_bars[symbol]
                        if tick_high_f > 0:
                            bar["high"] = tick_high_f
                        if tick_low_f > 0:
                            bar["low"] = tick_low_f
                        bar["close"] = price
                        bar["volume"] = volume
                    
                    # 콘솔 출력
                    logger.debug(f"\n{'='*60}")
                    logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 [{node_id}] OVC 체결")
                    logger.debug(f"  종목: {symbol}  가격: {price:,.2f}  거래량: {volume:,}")
                    logger.debug(f"  OHLCV: O={ohlcv_bars[symbol]['open']:.2f} H={ohlcv_bars[symbol]['high']:.2f} L={ohlcv_bars[symbol]['low']:.2f} C={price:.2f}")
                    logger.debug(f"{'='*60}\n")
                    
                    # OHLCV 데이터 형식으로 변환
                    ohlcv_data = {s: [bar] for s, bar in ohlcv_bars.items()}
                    
                    context.set_output(node_id, "ohlcv_data", ohlcv_data)
                    context.set_output(node_id, "data", ohlcv_data)
                    
                    output_data = {
                        "ohlcv_data": ohlcv_data,
                        "symbol": symbol,
                        "data": ohlcv_data,
                    }
                    
                    asyncio.run_coroutine_threadsafe(
                        context.notify_output_update(
                            node_id=node_id,
                            node_type="RealMarketDataNode",
                            outputs=output_data,
                        ),
                        loop
                    )
                    
                    asyncio.run_coroutine_threadsafe(
                        context.emit_event(
                            event_type="market_data",
                            source_node_id=node_id,
                            data=output_data,
                            trigger_nodes=trigger_nodes,
                        ),
                        loop
                    )
            except Exception as e:
                context.log("warning", f"OVC parse error: {e}", node_id)
        
        ovc.on_ovc_message(on_tick)
        ovc.add_ovc_symbols(symbols=subscribe_symbols)
        context.log("info", f"Subscribed to OVC: {subscribe_symbols} (체결 시 실시간 업데이트)", node_id)
        
        # 타임아웃 없음 - 체결은 언제 올지 모름
        # stay_connected=true면 구독 유지, false면 즉시 종료
        
        if not stay_connected:
            # stay_connected=False: 구독만 설정하고 즉시 종료 (1회성 조회 용도 아님)
            context.log("warning", f"stay_connected=False for realtime node - no data will be received", node_id)
            ovc.remove_ovc_symbols(symbols=subscribe_symbols)
            await real_client.close()
            context.log("info", f"WebSocket disconnected (stay_connected=False)", node_id)
        else:
            # 연결 유지: register_persistent로 WebSocket 연결 유지 (RealOrderEventNode 패턴)
            context.register_persistent(node_id, real_client)
            context.set_node_state(node_id, "ovc", ovc)
            context.set_node_state(node_id, "subscribe_symbols", subscribe_symbols)
            context.log("info", f"OVC subscription active - waiting for ticks...", node_id)
        
        # 초기 반환: 빈 OHLCV 데이터
        return {
            "symbols": symbols_raw,
            "ohlcv_data": {},
            "data": {},
        }
    
    def _get_stock_exchange_code(self, exchange: str) -> str:
        """거래소명을 LS증권 거래소 코드로 변환"""
        exchange_map = {
            "NASDAQ": "82",
            "NYSE": "81",
            "AMEX": "83",
            "82": "82",
            "81": "81",
            "83": "83",
        }
        return exchange_map.get(exchange.upper(), "82")  # 기본값 NASDAQ
    
    def _resolve_symbols(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        watchlist_output: Optional[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """
        Symbols 획득 (필드 우선, 포트 폴백 패턴)
        
        1. 노드 config의 symbols 필드 확인
        2. WatchlistNode 출력에서 symbols 가져오기
        3. AccountNode/RealAccountNode의 held_symbols 가져오기
        """
        # 1. 필드에서 직접 설정된 경우
        if config.get("symbols"):
            return config["symbols"]
        
        # 2. Input 포트에서 받기 (context input)
        symbols_input = context.get_output(f"_input_{node_id}", "symbols")
        if symbols_input:
            return symbols_input
        
        # 3. WatchlistNode에서 받기
        if watchlist_output and watchlist_output.get("symbols"):
            return watchlist_output["symbols"]
        
        # 4. AccountNode/RealAccountNode에서 held_symbols 가져오기
        account_output = context.find_parent_output(node_id, "RealAccountNode")
        if account_output and account_output.get("held_symbols"):
            return account_output["held_symbols"]
        
        account_output = context.find_parent_output(node_id, "AccountNode")
        if account_output and account_output.get("held_symbols"):
            return account_output["held_symbols"]
        
        return []
    
    def _build_full_data(
        self,
        symbols_raw: List[Dict[str, str]],
        prices: Dict[str, float],
        volumes: Dict[str, int],
        bids: Dict[str, float],
        asks: Dict[str, float],
    ) -> Dict[str, Dict[str, Any]]:
        """
        종목별 전체 시세 데이터 구조 생성
        
        Returns:
            {
                "AAPL": {"symbol": "AAPL", "exchange": "NASDAQ", "price": 192.30, ...},
                "TSLA": {...},
            }
        """
        data = {}
        for entry in symbols_raw:
            if isinstance(entry, dict):
                symbol = entry.get("symbol", "")
                exchange = entry.get("exchange", "")
            else:
                symbol = entry
                exchange = ""
            
            if symbol:
                data[symbol] = {
                    "symbol": symbol,
                    "exchange": exchange,
                    "price": prices.get(symbol),
                    "volume": volumes.get(symbol),
                    "bid": bids.get(symbol),
                    "ask": asks.get(symbol),
                }
        return data


class RealOrderEventNodeExecutor(NodeExecutorBase):
    """
    RealOrderEventNode executor - 실시간 주문 이벤트 (체결/거부/취소)
    
    WebSocket을 통해 주문 체결, 거부, 취소 이벤트를 실시간으로 수신합니다.
    - 해외주식: AS0~AS4 (체결통보) - 하나만 등록해도 전체 수신
    - 해외선물: TC1~TC3 (주문접수/확인/체결) - 하나만 등록해도 전체 수신
    
    event_filter로 특정 TR만 output하도록 필터링 가능
    
    stay_connected 옵션에 따라:
    - True: WebSocket 연결 유지, 플로우 끝나도 계속 살아있음
    - False: WebSocket 연결, 플로우 끝나면 cleanup (연결 종료)
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        # 옵션 확인
        stay_connected = config.get("stay_connected", True)
        
        # config에서 명시적 connection 확인 (바인딩 표현식 해석됨)
        broker_connection = config.get("connection")
        
        # connection 없으면 에러 - 명시적 바인딩 필수
        if not broker_connection:
            context.log("error", "RealOrderEventNode: connection 필드가 필수입니다. connection: \"{{ nodes.broker.connection }}\"를 설정하세요.", node_id)
            return {"error": "Missing connection field - set connection: \"{{ nodes.broker.connection }}\""}
        
        provider = broker_connection.get("provider", "ls-sec.co.kr")
        broker_product = broker_connection.get("product", "overseas_stock")
        # config의 product_type 우선, connection.product fallback
        product = config.get("product_type") or broker_product
        
        # ========================================
        # ⚠️ Product 불일치 검증
        # ========================================
        if product != broker_product:
            error_msg = f"Product mismatch: 노드 product_type='{product}' vs 브로커 product='{broker_product}'. 브로커와 동일한 상품을 선택하세요."
            context.log("error", error_msg, node_id)
            return {"error": error_msg}
        
        # 이벤트 필터 가져오기 (product_type에 따라 다른 필드 사용)
        if product == "overseas_futures":
            event_filter = config.get("event_filter_futures", "all")
        else:
            event_filter = config.get("event_filter", "all")
        
        context.log("info", f"RealOrderEvent: provider={provider}, product={product}, event_filter={event_filter}, stay_connected={stay_connected}", node_id)
        
        # 🆕 기존 연결이 있고 event_filter가 변경된 경우 기존 연결 제거 후 재등록
        # persistent에 저장된 event_filter와 현재 event_filter 비교
        if stay_connected and context.has_persistent(node_id):
            existing_filter = context.get_persistent_metadata(node_id, "event_filter")
            if existing_filter == event_filter:
                context.log("info", f"Reusing existing RealOrderEvent subscription (filter={event_filter})", node_id)
                return {"status": "subscribed", "product": product, "event_filter": event_filter}
            else:
                # event_filter가 변경됨 - 기존 연결 제거
                context.log("info", f"event_filter changed ({existing_filter} -> {event_filter}), re-subscribing", node_id)
                await context.cleanup_persistent(node_id)
        
        # ========================================
        # 브로커별 분기 처리
        # ========================================
        if provider == "ls-sec.co.kr":
            return await self._execute_ls(node_id, product, config, context, stay_connected, event_filter)
        else:
            context.log("error", f"Unsupported provider: {provider}", node_id)
            return {"error": f"Unsupported provider: {provider}"}

    async def _execute_ls(
        self,
        node_id: str,
        product: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        stay_connected: bool,
        event_filter: str = "all",
    ) -> Dict[str, Any]:
        """LS증권 실시간 주문 이벤트 구독"""
        
        # secrets에서 인증 정보 가져오기
        credential = context.get_credential()
        
        if not credential:
            context.log("error", "Credential not found in secrets", node_id)
            return {"error": "Missing credentials"}
        
        appkey = credential.get("appkey")
        appsecret = credential.get("appsecret")
        paper_trading = credential.get("paper_trading", False)
        
        if not appkey or not appsecret:
            context.log("error", "appkey/appsecret not found in credential", node_id)
            return {"error": "Missing appkey/appsecret"}
        
        try:
            ls, success, error = ensure_ls_login(
                appkey, appsecret, paper_trading, context, node_id,
                caller_name=f"RealOrderEventNode({product})"
            )
            if not success:
                return {"error": error}
            
            # Product별 분기 처리
            if product == "overseas_stock":
                return await self._ls_stock_order_event(
                    ls, node_id, config, context, stay_connected, event_filter
                )
            elif product == "overseas_futures":
                return await self._ls_futures_order_event(
                    ls, node_id, config, context, stay_connected, event_filter
                )
            else:
                context.log("error", f"Unsupported product for RealOrderEventNode: {product}", node_id)
                return {"error": f"Unsupported product: {product}"}
                
        except ImportError as e:
            context.log("error", f"finance package not available: {e}", node_id)
            return {"error": f"finance package error: {e}"}
        except Exception as e:
            context.log("error", f"Unexpected error: {e}", node_id)
            return {"error": str(e)}

    async def _ls_stock_order_event(
        self,
        ls,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        stay_connected: bool,
        event_filter: str = "all",
    ) -> Dict[str, Any]:
        """해외주식 실시간 주문 체결 이벤트 (AS0~AS4)
        
        AS0~AS4 중 하나만 등록해도 전체 수신됨.
        여러 노드가 동시에 사용할 수 있도록 마스터 콜백 패턴 사용.
        """
        from datetime import datetime
        
        product = "overseas_stock"
        
        try:
            # 현재 이벤트 루프 캡처 (콜백에서 사용)
            loop = asyncio.get_running_loop()
            
            # 트리거할 하위 노드 목록
            trigger_nodes = config.get("_trigger_on_update_nodes", [])
            
            # ========================================
            # 노드별 핸들러 생성 및 등록
            # ========================================
            def create_handler(_node_id: str, _event_filter: str, _trigger_nodes: list):
                """특정 노드용 핸들러 생성 (클로저로 값 캡처)"""
                
                def handler(resp):
                    from datetime import datetime
                    
                    # header에서 tr_cd 확인하여 필터링
                    header = getattr(resp, 'header', None)
                    tr_cd = getattr(header, 'tr_cd', 'AS0') if header else 'AS0'
                    
                    # event_filter가 'all'이 아니면 해당 TR만 처리
                    if _event_filter != "all" and tr_cd != _event_filter:
                        return  # 필터링된 TR이 아니면 무시
                    
                    # body에서 필드 추출
                    body = getattr(resp, 'body', resp)
                    ord_type_code = getattr(body, 'sOrdxctPtnCode', '')
                    
                    event_data = {
                        "timestamp": datetime.now().isoformat(),
                        "tr_cd": tr_cd,
                        "event_code": ord_type_code,
                        "symbol": getattr(body, 'sShtnIsuNo', getattr(body, 'sIsuNo', '')),
                        "symbol_name": getattr(body, 'sIsuNm', ''),
                        "order_no": getattr(body, 'sOrdNo', 0),
                        "orig_order_no": getattr(body, 'sOrgOrdNo', 0),
                        "side": getattr(body, 'sOrdPtnCode', ''),
                        "order_qty": int(getattr(body, 'sOrdQty', 0)),
                        "order_price": float(getattr(body, 'sOrdPrc', 0)),
                        "remain_qty": int(getattr(body, 'sOrgOrdUnercQty', 0)),
                        "modified_qty": int(getattr(body, 'sOrgOrdMdfyQty', 0)),
                        "cancelled_qty": int(getattr(body, 'sOrgOrdCancQty', 0)),
                        "order_time": getattr(body, 'sOrdTime', ''),
                        "market_code": getattr(body, 'sOrdMktCode', ''),
                    }
                    
                    # 주문체결유형코드에 따라 포트 및 상태명 결정
                    port_map = {
                        '01': ('accepted', '신규접수'),
                        '02': ('accepted', '정정접수'),
                        '03': ('accepted', '취소접수'),
                        '11': ('filled', '체결'),
                        '12': ('modified', '정정완료'),
                        '13': ('cancelled', '취소완료'),
                        '14': ('rejected', '거부'),
                    }
                    
                    port, status_name = port_map.get(ord_type_code, ('accepted', f'코드:{ord_type_code}'))
                    event_data["status"] = status_name
                    
                    context.set_output(_node_id, port, event_data)
                    
                    side_name = "매수" if event_data['side'] == '02' else "매도"
                    
                    logger.debug(f"\n{'='*60}")
                    logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 📣 [{_node_id}] 해외주식 {status_name} ({side_name})")
                    logger.debug(f"  종목: {event_data['symbol']} ({event_data['symbol_name']})")
                    logger.debug(f"  주문번호: {event_data['order_no']}")
                    logger.debug(f"{'='*60}\n")
                    
                    asyncio.run_coroutine_threadsafe(
                        context.notify_output_update(
                            node_id=_node_id,
                            node_type="RealOrderEventNode",
                            outputs={port: event_data},
                        ),
                        loop
                    )
                    
                    asyncio.run_coroutine_threadsafe(
                        context.emit_event(
                            event_type="order_event",
                            source_node_id=_node_id,
                            data={port: event_data},
                            trigger_nodes=_trigger_nodes,
                        ),
                        loop
                    )
                
                return handler
            
            # 핸들러 등록 (AS0~AS4는 모두 같은 콜백으로 수신됨)
            handler = create_handler(node_id, event_filter, trigger_nodes)
            context.register_order_event_handler(product, "AS0", node_id, event_filter, handler)
            
            # ========================================
            # 마스터 콜백 설정 (첫 번째 노드만)
            # ========================================
            if not context.has_order_event_subscription(product):
                real_client = ls.overseas_stock().real()
                if not await real_client.is_connected():
                    await real_client.connect()
                
                context.set_order_event_real_client(product, real_client)
                
                # 마스터 콜백: 모든 등록된 핸들러에게 분배
                def master_callback(resp):
                    handlers = context.get_order_event_handlers(product, "AS0")
                    for (handler_node_id, handler_filter, handler_func) in handlers:
                        try:
                            handler_func(resp)
                        except Exception as e:
                            context.log("error", f"Handler error for {handler_node_id}: {e}", handler_node_id)
                
                real_client.AS0().on_as0_message(master_callback)
                context.log("info", f"Master order event callback registered for {product}", node_id)
            
            # ========================================
            # stay_connected에 따라 등록 방식 결정
            # ========================================
            real_client = context.get_order_event_real_client(product)
            if stay_connected:
                context.register_persistent(node_id, real_client, metadata={"event_filter": event_filter})
                context.log("info", f"AS0~AS4 order event subscription started (filter={event_filter}, stay_connected=True)", node_id)
            else:
                context.register_cleanup_on_flow_end(node_id, real_client)
                context.log("info", f"AS0~AS4 order event subscription started (filter={event_filter}, stay_connected=False)", node_id)
            
            result = {
                "status": "subscribed",
                "product": "overseas_stock",
                "event_type": "AS0~AS4",
                "event_filter": event_filter,
            }
            
            asyncio.create_task(context.notify_output_update(
                node_id=node_id,
                node_type="RealOrderEventNode",
                outputs=result,
            ))
            
            return result
            
        except Exception as e:
            context.log("error", f"AS0~AS4 subscription failed: {e}", node_id)
            return {"error": str(e)}

    async def _ls_futures_order_event(
        self,
        ls,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        stay_connected: bool,
        event_filter: str = "all",
    ) -> Dict[str, Any]:
        """해외선물 실시간 주문 이벤트 (TC1/TC2/TC3)
        
        TC1: 주문접수 (HO01=ACK, HO04=Pending)
        TC2: 주문응답 (HO02=확인, HO03=거부)
        TC3: 주문체결 (CH01=체결)
        
        TC1~TC3 중 하나만 등록해도 전체 수신됨.
        여러 노드가 동시에 사용할 수 있도록 마스터 콜백 패턴 사용:
        - 첫 번째 노드가 마스터 콜백 등록
        - 후속 노드들은 핸들러만 등록
        - 마스터 콜백이 모든 핸들러에게 이벤트 분배
        """
        from datetime import datetime
        
        product = "overseas_futures"
        
        try:
            # 현재 이벤트 루프 캡처 (콜백에서 사용)
            loop = asyncio.get_running_loop()
            
            # 트리거할 하위 노드 목록
            trigger_nodes = config.get("_trigger_on_update_nodes", [])
            
            # ========================================
            # 노드별 핸들러 생성 및 등록
            # ========================================
            def create_handler(tr_cd: str, _node_id: str, _event_filter: str, _trigger_nodes: list):
                """특정 노드용 핸들러 생성 (클로저로 값 캡처)"""
                
                def handler(resp):
                    from datetime import datetime
                    
                    # event_filter 체크
                    if _event_filter != "all" and _event_filter != tr_cd:
                        return
                    
                    body = getattr(resp, 'body', resp)
                    
                    if tr_cd == "TC1":
                        event_data = self._parse_tc1_data(body)
                        port, status_name = self._get_tc1_port_status(event_data)
                    elif tr_cd == "TC2":
                        event_data = self._parse_tc2_data(body)
                        port, status_name = self._get_tc2_port_status(event_data)
                    elif tr_cd == "TC3":
                        event_data = self._parse_tc3_data(body)
                        port, status_name = 'filled', '체결'
                    else:
                        return
                    
                    event_data["status"] = status_name
                    context.set_output(_node_id, port, event_data)
                    
                    # 콘솔 출력
                    side_name = "매수" if event_data.get('side') == '2' else "매도"
                    logger.debug(f"\n{'='*60}")
                    logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 📣 [{_node_id}] 해외선물 {status_name} ({side_name})")
                    logger.debug(f"  종목: {event_data.get('symbol', '')}")
                    logger.debug(f"  주문번호: {event_data.get('order_no', '')}")
                    logger.debug(f"{'='*60}\n")
                    
                    # SSE 브로드캐스트
                    asyncio.run_coroutine_threadsafe(
                        context.notify_output_update(
                            node_id=_node_id,
                            node_type="RealOrderEventNode",
                            outputs={port: event_data},
                        ),
                        loop
                    )
                    
                    # 이벤트 발행
                    asyncio.run_coroutine_threadsafe(
                        context.emit_event(
                            event_type="order_event",
                            source_node_id=_node_id,
                            data={port: event_data},
                            trigger_nodes=_trigger_nodes,
                        ),
                        loop
                    )
                
                return handler
            
            # 각 TR에 대해 핸들러 등록
            for tr_cd in ["TC1", "TC2", "TC3"]:
                handler = create_handler(tr_cd, node_id, event_filter, trigger_nodes)
                context.register_order_event_handler(product, tr_cd, node_id, event_filter, handler)
            
            # ========================================
            # 마스터 콜백 설정 (첫 번째 노드만)
            # ========================================
            if not context.has_order_event_subscription(product):
                # 실시간 WebSocket 클라이언트 연결
                real_client = ls.overseas_futureoption().real()
                if not await real_client.is_connected():
                    await real_client.connect()
                
                context.set_order_event_real_client(product, real_client)
                
                # 마스터 콜백: 모든 등록된 핸들러에게 분배
                def create_master_callback(tr_cd: str):
                    def master_callback(resp):
                        handlers = context.get_order_event_handlers(product, tr_cd)
                        for (handler_node_id, handler_filter, handler_func) in handlers:
                            try:
                                handler_func(resp)
                            except Exception as e:
                                context.log("error", f"Handler error for {handler_node_id}: {e}", handler_node_id)
                    return master_callback
                
                # TC1, TC2, TC3 마스터 콜백 등록
                real_client.TC1().on_tc1_message(create_master_callback("TC1"))
                real_client.TC2().on_tc2_message(create_master_callback("TC2"))
                real_client.TC3().on_tc3_message(create_master_callback("TC3"))
                
                context.log("info", f"Master order event callbacks registered for {product}", node_id)
            
            # ========================================
            # stay_connected에 따라 등록 방식 결정
            # ========================================
            real_client = context.get_order_event_real_client(product)
            if stay_connected:
                context.register_persistent(node_id, real_client, metadata={"event_filter": event_filter})
                context.log("info", f"TC1/TC2/TC3 order event subscription started (filter={event_filter}, stay_connected=True)", node_id)
            else:
                context.register_cleanup_on_flow_end(node_id, real_client)
                context.log("info", f"TC1/TC2/TC3 order event subscription started (filter={event_filter}, stay_connected=False)", node_id)
            
            result = {
                "status": "subscribed",
                "product": "overseas_futures",
                "event_type": "TC1/TC2/TC3",
                "event_filter": event_filter,
            }
            
            # 🆕 초기 상태 SSE 브로드캐스트 (UI 반짝임용)
            asyncio.create_task(context.notify_output_update(
                node_id=node_id,
                node_type="RealOrderEventNode",
                outputs=result,
            ))
            
            return result
            
        except Exception as e:
            context.log("error", f"TC1/TC2/TC3 subscription failed: {e}", node_id)
            return {"error": str(e)}
    
    def _parse_tc1_data(self, body) -> Dict[str, Any]:
        """TC1 응답 파싱"""
        from datetime import datetime
        return {
            "timestamp": datetime.now().isoformat(),
            "tr_cd": "TC1",
            "svc_id": getattr(body, 'svc_id', ''),
            "order_type": getattr(body, 'ordr_ccd', '1'),
            "symbol": getattr(body, 'is_cd', ''),
            "order_no": getattr(body, 'ordr_no', ''),
            "orig_order_no": getattr(body, 'orgn_ordr_no', ''),
            "side": getattr(body, 's_b_ccd', ''),
            "order_qty": int(getattr(body, 'ordr_q', 0) or 0),
            "order_price": float(getattr(body, 'ordr_prc', 0) or 0),
            "order_time": getattr(body, 'ordr_tm', ''),
        }
    
    def _get_tc1_port_status(self, event_data: Dict) -> tuple:
        """TC1 포트 및 상태명 결정"""
        svc_id = event_data.get("svc_id", "")
        if svc_id == 'HO01':
            return 'accepted', '주문접수'
        elif svc_id == 'HO04':
            return 'accepted', '주문대기'
        else:
            return 'accepted', f'TC1({svc_id})'
    
    def _parse_tc2_data(self, body) -> Dict[str, Any]:
        """TC2 응답 파싱"""
        from datetime import datetime
        return {
            "timestamp": datetime.now().isoformat(),
            "tr_cd": "TC2",
            "svc_id": getattr(body, 'svc_id', ''),
            "order_type": getattr(body, 'ordr_ccd', '1'),
            "symbol": getattr(body, 'is_cd', ''),
            "order_no": getattr(body, 'ordr_no', ''),
            "orig_order_no": getattr(body, 'orgn_ordr_no', ''),
            "side": getattr(body, 's_b_ccd', ''),
            "order_qty": int(getattr(body, 'ordr_q', 0) or 0),
            "order_price": float(getattr(body, 'ordr_prc', 0) or 0),
            "confirmed_qty": int(getattr(body, 'cnfr_q', 0) or 0),
            "order_time": getattr(body, 'ordr_tm', ''),
            "reject_code": getattr(body, 'rfsl_cd', ''),
            "reject_reason": getattr(body, 'text', ''),
        }
    
    def _get_tc2_port_status(self, event_data: Dict) -> tuple:
        """TC2 포트 및 상태명 결정"""
        svc_id = event_data.get("svc_id", "")
        ordr_ccd = event_data.get("order_type", "1")
        
        if svc_id == 'HO03':
            return 'rejected', '주문거부'
        elif svc_id == 'HO02':
            if ordr_ccd == '2':
                return 'modified', '정정완료'
            elif ordr_ccd == '3':
                return 'cancelled', '취소완료'
            else:
                return 'accepted', '주문확인'
        else:
            return 'accepted', f'TC2({svc_id})'
    
    def _parse_tc3_data(self, body) -> Dict[str, Any]:
        """TC3 응답 파싱"""
        from datetime import datetime
        return {
            "timestamp": datetime.now().isoformat(),
            "tr_cd": "TC3",
            "svc_id": getattr(body, 'svc_id', ''),
            "symbol": getattr(body, 'is_cd', ''),
            "order_no": getattr(body, 'ordr_no', ''),
            "orig_order_no": getattr(body, 'orgn_ordr_no', ''),
            "side": getattr(body, 's_b_ccd', ''),
            "filled_qty": int(getattr(body, 'ccls_q', 0) or 0),
            "filled_price": float(getattr(body, 'ccls_prc', 0) or 0),
            "fill_no": getattr(body, 'ccls_no', ''),
            "fill_time": getattr(body, 'ccls_tm', ''),
            "avg_price": float(getattr(body, 'avg_byng_uprc', 0) or 0),
            "pnl": float(getattr(body, 'clr_pl_amt', 0) or 0),
            "commission": float(getattr(body, 'ent_fee', 0) or 0),
            "currency": getattr(body, 'crncy_cd', 'USD'),
        }


class CustomPnLNodeExecutor(NodeExecutorBase):
    """CustomPnLNode executor - 커스텀 수익률 계산 (고급 사용자용)"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        # 입력 데이터 가져오기
        positions = context.get_output("account", "positions") or {}
        current_prices = context.get_output("realMarket", "price") or {}
        
        # 커스텀 설정
        custom_commission = config.get("commission_rate", 0.0025)  # 기본 0.25%
        include_commission = config.get("include_commission", True)
        
        position_pnl = {}
        total_pnl_amount = 0.0
        
        for symbol, pos in positions.items():
            current_price = current_prices.get(symbol, pos.get("current_price", 0))
            avg_price = pos.get("avg_price", 0)
            qty = pos.get("qty", 0)
            
            if avg_price > 0:
                pnl_rate = ((current_price - avg_price) / avg_price) * 100
                pnl_amount = (current_price - avg_price) * qty
                
                # 커스텀 수수료 적용
                if include_commission:
                    commission = (avg_price * qty + current_price * qty) * custom_commission
                    pnl_amount -= commission
            else:
                pnl_rate = 0.0
                pnl_amount = 0.0
            
            position_pnl[symbol] = {
                "symbol": symbol,
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
                "pnl_rate": round(pnl_rate, 2),
                "pnl_amount": round(pnl_amount, 2),
            }
            total_pnl_amount += pnl_amount
        
        context.log("info", f"Custom PnL calculated: {len(position_pnl)} positions", node_id)
        return {
            "position_pnl": position_pnl,
            "daily_pnl": round(total_pnl_amount, 2),
            "summary": {"total_positions": len(position_pnl), "total_pnl": total_pnl_amount},
        }


class DisplayNodeExecutor(NodeExecutorBase):
    """
    DisplayNode executor - 명시적 chart_type 기반 시각화
    
    chart_type별 필수 필드:
    - table: data
    - line: data, x_field, y_field
    - multi_line: data, x_field, y_field, series_key
    - candlestick: data, date_field, open_field, high_field, low_field, close_field
    - bar: data, x_field, y_field
    - summary: data (raw JSON 표시)
    """

    def _format_value(self, value) -> str:
        """값을 출력용 문자열로 포맷팅"""
        if value is None:
            return "-"
        if isinstance(value, float):
            if abs(value) >= 1000:
                return f"{value:,.2f}"
            elif abs(value) < 0.01:
                return f"{value:.6f}"
            else:
                return f"{value:.4f}"
        if isinstance(value, int):
            return f"{value:,}"
        if isinstance(value, (list, dict)):
            return str(value)[:15] + "..." if len(str(value)) > 15 else str(value)
        return str(value)[:20]

    def _get_data(self, config: Dict[str, Any], context: ExecutionContext, node_id: str) -> Any:
        """data 필드 또는 엣지에서 데이터 가져오기"""
        # 1. config의 data 필드가 바인딩 표현식인 경우 이미 평가됨
        data = config.get("data")
        if data is not None:
            return data
        
        # 2. 엣지로 연결된 입력 데이터
        input_namespace = f"_input_{node_id}"
        all_inputs = context.get_all_outputs(input_namespace) if hasattr(context, 'get_all_outputs') else {}
        
        # 실시간 데이터 우선
        realtime_data = config.get("_realtime_data")
        if realtime_data:
            all_inputs = {**all_inputs, **realtime_data}
        
        # 소스 노드에서 직접 조회
        source_node_id = config.get("_source_node_id")
        if source_node_id and not realtime_data:
            source_outputs = context.get_all_outputs(source_node_id)
            if source_outputs:
                all_inputs = source_outputs
        
        # data 포트 또는 첫 번째 입력
        return all_inputs.get("data") or (next(iter(all_inputs.values()), None) if all_inputs else None)

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        from datetime import datetime
        import json
        
        chart_type = config.get("chart_type", "summary")
        title = config.get("title", "")
        
        # 데이터 가져오기
        data = self._get_data(config, context, node_id)
        
        context.log("debug", f"DisplayNode '{node_id}': chart_type={chart_type}, data_type={type(data).__name__}", node_id)
        
        # 출력 데이터 구성
        output_data = {
            "rendered": True,
            "chart_type": chart_type,
            "title": title,
        }
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ========================================
        # chart_type별 처리
        # ========================================
        
        if chart_type == "summary":
            # Raw JSON 표시
            print(f"\n📋 {title or 'Data Summary'} [{now}]")
            print("=" * 60)
            try:
                def serialize(obj):
                    if hasattr(obj, 'model_dump'):
                        return obj.model_dump()
                    elif hasattr(obj, '__dict__'):
                        return {k: serialize(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
                    elif isinstance(obj, dict):
                        return {k: serialize(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [serialize(v) for v in obj]
                    return obj
                
                serialized = serialize(data)
                print(json.dumps(serialized, indent=2, ensure_ascii=False, default=str))
            except Exception as e:
                print(f"(직렬화 실패: {e})")
                print(str(data)[:500])
            print("=" * 60 + "\n")
            
            output_data["data"] = data
            
        elif chart_type == "table":
            # 테이블 표시
            columns = config.get("columns")
            limit = config.get("limit", 10)
            sort_by = config.get("sort_by")
            sort_order = config.get("sort_order", "desc")
            
            print(f"\n📊 {title or 'Table'} [{now}]")
            print("=" * 80)
            
            # 데이터 형식 판단
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                # 리스트 형태
                rows = data
                if sort_by and sort_by in (rows[0] if rows else {}):
                    rows = sorted(rows, key=lambda x: x.get(sort_by, 0), reverse=(sort_order == "desc"))
                rows = rows[:limit]
                
                cols = columns or list(rows[0].keys())[:8]
                header = " | ".join(f"{c:<12}" for c in cols)
                print(header)
                print("-" * 80)
                for row in rows:
                    values = " | ".join(f"{self._format_value(row.get(c)):<12}" for c in cols)
                    print(values)
                    
            elif isinstance(data, dict):
                # dict of dicts (symbol: {field: value}) 또는 flat dict
                if data and all(isinstance(v, dict) for v in data.values()):
                    # dict of dicts
                    items = list(data.items())
                    if sort_by:
                        items = sorted(items, key=lambda x: x[1].get(sort_by, 0), reverse=(sort_order == "desc"))
                    items = items[:limit]
                    
                    if items:
                        cols = columns or list(items[0][1].keys())[:6]
                        header = f"{'Key':<12} | " + " | ".join(f"{c:<12}" for c in cols)
                        print(header)
                        print("-" * 80)
                        for key, val in items:
                            values = f"{key:<12} | " + " | ".join(f"{self._format_value(val.get(c)):<12}" for c in cols)
                            print(values)
                else:
                    # flat dict
                    for k, v in list(data.items())[:limit]:
                        print(f"  {k:<25}: {self._format_value(v)}")
            
            print("=" * 80 + "\n")
            output_data["data"] = data
            
        elif chart_type == "line":
            # 단일 라인 차트
            x_field = config.get("x_field")
            y_field = config.get("y_field")
            signal_field = config.get("signal_field")
            side_field = config.get("side_field")
            
            if not x_field or not y_field:
                context.log("error", f"line 차트에 x_field, y_field 필수", node_id)
                return {"rendered": False, "error": "x_field, y_field 필수"}
            
            print(f"\n📈 {title or 'Line Chart'} [{now}]")
            print("=" * 60)
            
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                last = data[-1]
                print(f"📊 데이터 포인트: {len(data)}개")
                print(f"📅 X축 범위: {first.get(x_field)} ~ {last.get(x_field)}")
                print(f"📈 Y축({y_field}) 시작: {self._format_value(first.get(y_field))}")
                print(f"📈 Y축({y_field}) 끝: {self._format_value(last.get(y_field))}")
                
                # 최대/최소
                values = [d.get(y_field, 0) for d in data if d.get(y_field) is not None]
                if values:
                    print(f"📈 최대: {self._format_value(max(values))}")
                    print(f"📉 최소: {self._format_value(min(values))}")
                
                # 시그널 마커 표시
                if signal_field:
                    signals = self._extract_signals(data, x_field, signal_field, side_field)
                    if signals:
                        print(f"\n🎯 시그널 ({len(signals)}개):")
                        for sig in signals[:10]:  # 최대 10개만 표시
                            print(f"  {sig['marker']} {sig['x']} ({sig['signal']}/{sig['side']})")
                        if len(signals) > 10:
                            print(f"  ... 외 {len(signals) - 10}개")
            else:
                print("(데이터 없음)")
            
            print("=" * 60 + "\n")
            output_data["data"] = data
            output_data["x_field"] = x_field
            output_data["y_field"] = y_field
            if signal_field:
                output_data["signal_field"] = signal_field
            if side_field:
                output_data["side_field"] = side_field
            
        elif chart_type == "multi_line":
            # 멀티 라인 차트 (심볼별)
            x_field = config.get("x_field")
            y_field = config.get("y_field")
            series_key = config.get("series_key")
            limit = config.get("limit", 10)
            sort_by = config.get("sort_by")
            sort_order = config.get("sort_order", "desc")
            signal_field = config.get("signal_field")
            side_field = config.get("side_field")
            
            if not x_field or not y_field or not series_key:
                context.log("error", f"multi_line 차트에 x_field, y_field, series_key 필수", node_id)
                return {"rendered": False, "error": "x_field, y_field, series_key 필수"}
            
            print(f"\n📈 {title or 'Multi-Line Chart'} [{now}]")
            print("=" * 80)
            
            # data가 평탄화된 배열 형식인 경우 [{symbol, date, value, ...}, ...]
            if isinstance(data, list):
                # series_key로 그룹핑
                from collections import defaultdict
                grouped = defaultdict(list)
                for row in data:
                    if isinstance(row, dict):
                        key = row.get(series_key, "unknown")
                        grouped[key].append(row)
                
                series_items = list(grouped.items())
                
                # 정렬 (마지막 값 기준)
                if sort_by:
                    def get_last_value(item):
                        symbol, rows = item
                        if rows and len(rows) > 0:
                            return rows[-1].get(sort_by, 0)
                        return 0
                    series_items = sorted(series_items, key=get_last_value, reverse=(sort_order == "desc"))
                
                series_items = series_items[:limit]
                
                print(f"📊 시리즈 수: {len(series_items)}개 (limit: {limit})")
                print("-" * 80)
                print(f"{'Series':<12} | {'Points':<8} | {f'First {y_field}':<15} | {f'Last {y_field}':<15}")
                print("-" * 80)
                
                for symbol, rows in series_items:
                    if isinstance(rows, list) and len(rows) > 0:
                        first_val = rows[0].get(y_field, 0)
                        last_val = rows[-1].get(y_field, 0)
                        print(f"{symbol:<12} | {len(rows):<8} | {self._format_value(first_val):<15} | {self._format_value(last_val):<15}")
                
                # 시그널 마커 표시
                if signal_field:
                    signals = self._extract_signals(data, x_field, signal_field, side_field, series_key)
                    if signals:
                        print(f"\n🎯 시그널 ({len(signals)}개):")
                        for sig in signals[:15]:  # 최대 15개만 표시
                            series_info = f" [{sig.get('series', '')}]" if sig.get('series') else ""
                            print(f"  {sig['marker']} {sig['x']}{series_info} ({sig['signal']}/{sig['side']})")
                        if len(signals) > 15:
                            print(f"  ... 외 {len(signals) - 15}개")
            
            print("=" * 80 + "\n")
            output_data["data"] = data
            output_data["x_field"] = x_field
            output_data["y_field"] = y_field
            output_data["series_key"] = series_key
            if signal_field:
                output_data["signal_field"] = signal_field
            if side_field:
                output_data["side_field"] = side_field
            
        elif chart_type == "candlestick":
            # 캔들스틱 차트
            date_field = config.get("date_field")
            open_field = config.get("open_field")
            high_field = config.get("high_field")
            low_field = config.get("low_field")
            close_field = config.get("close_field")
            volume_field = config.get("volume_field")
            signal_field = config.get("signal_field")
            side_field = config.get("side_field")
            
            required = [date_field, open_field, high_field, low_field, close_field]
            if not all(required):
                context.log("error", f"candlestick 차트에 date_field, open_field, high_field, low_field, close_field 필수", node_id)
                return {"rendered": False, "error": "OHLC 필드 필수"}
            
            print(f"\n📊 {title or 'Candlestick Chart'} [{now}]")
            print("=" * 80)
            
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                last = data[-1]
                print(f"📊 캔들 수: {len(data)}개")
                print(f"📅 기간: {first.get(date_field)} ~ {last.get(date_field)}")
                print(f"💵 시작 종가: {self._format_value(first.get(close_field))}")
                print(f"💵 최종 종가: {self._format_value(last.get(close_field))}")
                
                # 수익률
                start_price = first.get(close_field, 0)
                end_price = last.get(close_field, 0)
                if start_price > 0:
                    pct_change = (end_price - start_price) / start_price * 100
                    sign = "+" if pct_change >= 0 else ""
                    color = "\033[92m" if pct_change >= 0 else "\033[91m"
                    print(f"📈 변동률: {color}{sign}{pct_change:.2f}%\033[0m")
                
                # 시그널 마커 표시
                if signal_field:
                    signals = self._extract_signals(data, date_field, signal_field, side_field)
                    if signals:
                        print(f"\n🎯 시그널 ({len(signals)}개):")
                        for sig in signals[:10]:  # 최대 10개만 표시
                            print(f"  {sig['marker']} {sig['x']} ({sig['signal']}/{sig['side']})")
                        if len(signals) > 10:
                            print(f"  ... 외 {len(signals) - 10}개")
            else:
                print("(데이터 없음)")
            
            print("=" * 80 + "\n")
            output_data["data"] = data
            output_data["date_field"] = date_field
            output_data["open_field"] = open_field
            output_data["high_field"] = high_field
            output_data["low_field"] = low_field
            output_data["close_field"] = close_field
            if volume_field:
                output_data["volume_field"] = volume_field
            if signal_field:
                output_data["signal_field"] = signal_field
            if side_field:
                output_data["side_field"] = side_field
            
        elif chart_type == "bar":
            # 바 차트
            x_field = config.get("x_field")
            y_field = config.get("y_field")
            
            if not x_field or not y_field:
                context.log("error", f"bar 차트에 x_field, y_field 필수", node_id)
                return {"rendered": False, "error": "x_field, y_field 필수"}
            
            print(f"\n📊 {title or 'Bar Chart'} [{now}]")
            print("=" * 60)
            
            if isinstance(data, list) and len(data) > 0:
                print(f"{'Bar':<20} | {y_field}")
                print("-" * 60)
                for item in data[:20]:
                    x_val = item.get(x_field, "")
                    y_val = item.get(y_field, 0)
                    print(f"{str(x_val):<20} | {self._format_value(y_val)}")
            elif isinstance(data, dict):
                print(f"{'Key':<20} | {'Value'}")
                print("-" * 60)
                for k, v in list(data.items())[:20]:
                    print(f"{str(k):<20} | {self._format_value(v)}")
            
            print("=" * 60 + "\n")
            output_data["data"] = data
            output_data["x_field"] = x_field
            output_data["y_field"] = y_field
        
        else:
            # 알 수 없는 chart_type
            context.log("warning", f"알 수 없는 chart_type: {chart_type}, summary로 처리", node_id)
            output_data["data"] = data
        
        # Notify listeners for frontend
        await context.notify_display_data(
            node_id=node_id,
            chart_type=chart_type,
            title=title,
            data=output_data.get("data"),
            x_label=config.get("x_field"),
            y_label=config.get("y_field"),
            options={
                "x_field": config.get("x_field"),
                "y_field": config.get("y_field"),
                "series_key": config.get("series_key"),
                "date_field": config.get("date_field"),
                "open_field": config.get("open_field"),
                "high_field": config.get("high_field"),
                "low_field": config.get("low_field"),
                "close_field": config.get("close_field"),
                "volume_field": config.get("volume_field"),
                "columns": config.get("columns"),
                "limit": config.get("limit"),
                "sort_by": config.get("sort_by"),
                "sort_order": config.get("sort_order"),
                "signal_field": config.get("signal_field"),
                "side_field": config.get("side_field"),
            },
        )
        
        context.log("info", f"Display rendered: {chart_type}", node_id)
        return output_data
    
    def _extract_signals(
        self,
        data: List[Dict[str, Any]],
        x_field: str,
        signal_field: str,
        side_field: Optional[str] = None,
        series_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        데이터에서 시그널 마커 정보 추출
        
        Returns:
            [{"x": "2025-01-15", "signal": "buy", "side": "long", "marker": "[B:L]", "series": "AAPL"}, ...]
        """
        signals = []
        
        # 시그널 마커 매핑
        SIGNAL_MARKERS = {
            ("buy", "long"): "[B:L]",      # 🟢 롱 진입
            ("sell", "long"): "[S:L]",     # 🔴 롱 청산
            ("sell", "short"): "[S:S]",    # 🔵 숏 진입
            ("buy", "short"): "[B:S]",     # 🟠 숏 청산
        }
        
        for row in data:
            if not isinstance(row, dict):
                continue
            
            signal_val = row.get(signal_field)
            if not signal_val:
                continue
            
            # signal 정규화
            signal = str(signal_val).lower()
            if signal not in ("buy", "sell"):
                continue
            
            # side 결정 (기본값: long)
            side = "long"
            if side_field:
                side_val = row.get(side_field)
                if side_val:
                    side = str(side_val).lower()
                    if side not in ("long", "short"):
                        side = "long"
            
            # 마커 결정
            marker = SIGNAL_MARKERS.get((signal, side), f"[{signal[0].upper()}:{side[0].upper()}]")
            
            sig_info = {
                "x": row.get(x_field, ""),
                "signal": signal,
                "side": side,
                "marker": marker,
            }
            
            # 시리즈 키가 있으면 추가
            if series_key:
                sig_info["series"] = row.get(series_key, "")
            
            signals.append(sig_info)
        
        return signals


class ConditionNodeExecutor(NodeExecutorBase):
    """
    ConditionNode executor (plugin-based)
    
    DisplayNode-like 패턴:
    - 입력: data (평탄화된 배열), field_mapping (필드 매핑)
    - 출력: passed_symbols, failed_symbols, values
    
    data 필드는 flatten() 표현식으로 시계열 데이터를 평탄화하여 전달:
    예: "data": "{{ flatten(nodes.historicaldata_1.values, 'time_series') }}"
    
    field_mapping으로 커스텀 필드명 매핑 가능:
    예: close_field="adj_close", date_field="trading_date"
    
    출력 형식:
    - passed_symbols: [{exchange, symbol}, ...] (거래소 정보 포함)
    - failed_symbols: [{exchange, symbol}, ...]
    - symbol_results: [{symbol, exchange, rsi, price, ...}, ...]
    - values: [{symbol, exchange, time_series: [...], ...}, ...]
    """

    def _resolve_port_binding(
        self,
        config: Dict[str, Any],
        port_name: str,
        context: ExecutionContext,
        node_id: str,
        default: Any = None,
    ) -> Any:
        """
        포트 바인딩 표현식을 평가하여 데이터 반환
        
        Args:
            config: 노드 config (price_data, symbols 등 바인딩 표현식 포함)
            port_name: 포트 이름 (price_data, symbols 등)
            context: 실행 컨텍스트
            node_id: 현재 노드 ID
            default: 기본값
            
        Returns:
            평가된 데이터 또는 기본값
        """
        binding_expr = config.get(port_name)
        
        if binding_expr and isinstance(binding_expr, str):
            # {{ nodes.xxx.yyy }} 표현식 평가
            expr_context = context.get_expression_context()
            evaluator = ExpressionEvaluator(expr_context)
            try:
                result = evaluator.evaluate(binding_expr)
                if result is not None:
                    context.log("debug", f"Port binding resolved: {port_name} = {type(result).__name__}", node_id)
                    return result
            except Exception as e:
                context.log("warning", f"Port binding evaluation failed for {port_name}: {e}", node_id)
        
        return default

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        plugin: Optional[Callable] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from programgarden.plugin import PluginSandbox, PluginTimeoutError
        from programgarden_core.models import get_plugin_hints
        
        # 플러그인 ID 추출
        plugin_id = config.get("plugin", "Unknown")
        
        # 플러그인 리소스 힌트 조회
        hints = get_plugin_hints(plugin_id)
        
        # === 리소스 체크 ===
        resource_check = await context.check_resources_before_task(
            task_type="ConditionNode",
            weight=hints.get_weight() if hasattr(hints, 'get_weight') else 1.0,
        )
        
        if not resource_check["can_proceed"]:
            context.log("warning", f"Resource limit reached: {resource_check['reason']}", node_id)
            # 리소스 부족 시 빈 결과 반환 (안전 모드)
            return {
                "result": False,
                "passed_symbols": [],
                "failed_symbols": [],
                "values": {},
                "error": "resource_limit",
            }
        
        # 권장 배치 크기 저장 (백테스트 모드에서 사용)
        recommended_batch_size = resource_check.get("recommended_batch_size", 10)
        
        # 샌드박스 생성
        sandbox = PluginSandbox(
            resource_context=context.resource,
            default_timeout=hints.max_execution_sec if hasattr(hints, 'max_execution_sec') else 30.0,
            default_batch_size=hints.max_symbols_per_call if hasattr(hints, 'max_symbols_per_call') else 100,
        )
        
        try:
            # === 플러그인 스키마에서 required_data 확인 ===
            # 먼저 community 플러그인 레지스트리 초기화 (자동 등록)
            try:
                import programgarden_community  # 플러그인 자동 등록 트리거
            except ImportError:
                pass  # community 패키지 없어도 동작
            
            from programgarden_core import PluginRegistry
            plugin_registry = PluginRegistry()
            plugin_schema = plugin_registry.get_schema(plugin_id)
            required_data = plugin_schema.required_data if plugin_schema else ["data"]
            
            # positions 기반 플러그인인지 확인 (ProfitTarget, StopLoss 등)
            is_positions_based = "positions" in required_data and "data" not in required_data
            
            # === 명시적 바인딩으로 데이터 가져오기 ===
            # 모든 config 값에서 {{ }} 표현식 평가
            original_data_expr = config.get("data")
            original_positions_expr = config.get("positions")
            print(f"\n🔍 ConditionNode '{node_id}' 바인딩 평가:")
            print(f"   - plugin: {plugin_id}, required_data: {required_data}")
            print(f"   - is_positions_based: {is_positions_based}")
            
            config = evaluate_all_bindings(config, context, node_id)
            
            # === positions 기반 플러그인 처리 (ProfitTarget, StopLoss) ===
            if is_positions_based:
                positions = config.get("positions", {})
                print(f"   - positions 평가 후: {type(positions).__name__}, {len(positions) if isinstance(positions, dict) else 0} items")
                
                if not positions:
                    context.log("error", 
                        f"ConditionNode '{node_id}': positions가 설정되지 않았습니다. "
                        f"config에 positions: {{{{ nodes.realAccount.positions }}}} 형태로 추가하세요.",
                        node_id
                    )
                    return {
                        "result": False,
                        "passed_symbols": [],
                        "failed_symbols": [],
                        "values": [],
                        "error": "missing_positions",
                        "error_message": "positions가 설정되지 않았습니다. 예: {{ nodes.realAccount.positions }}",
                    }
                
                # fields 표현식 평가
                evaluated_fields = fields or config.get("fields", {}) or config.get("params", {})
                if evaluated_fields:
                    expr_context = context.get_expression_context()
                    evaluator = ExpressionEvaluator(expr_context)
                    evaluated_fields = evaluator.evaluate_fields(evaluated_fields)
                
                # positions 기반 플러그인 직접 실행
                context.log("info", f"Condition (positions-based) running with {len(positions)} positions", node_id)
                
                if plugin:
                    try:
                        result = await sandbox.execute(
                            plugin_id=plugin_id,
                            plugin_callable=plugin,
                            kwargs={
                                "positions": positions,
                                "fields": evaluated_fields,
                            },
                        )
                        
                        context.log(
                            "info",
                            f"Condition evaluated: {len(result.get('passed_symbols', []))}/{len(positions)} passed",
                            node_id,
                        )
                        
                        return {
                            "symbols": list(positions.keys()),
                            "result": result.get("result", False),
                            "passed_symbols": result.get("passed_symbols", []),
                            "failed_symbols": result.get("failed_symbols", []),
                            "symbol_results": result.get("symbol_results", []),
                            "values": result.get("values", []),
                        }
                    except Exception as e:
                        context.log("error", f"Plugin error: {e}", node_id)
                        import traceback
                        context.log("debug", f"Plugin traceback: {traceback.format_exc()}", node_id)
                        return {
                            "result": False,
                            "passed_symbols": [],
                            "failed_symbols": [],
                            "values": [],
                            "error": str(e),
                        }
                else:
                    # 플러그인 없으면 모두 통과
                    passed_symbols = [{"symbol": s, "exchange": "UNKNOWN"} for s in positions.keys()]
                    return {
                        "symbols": list(positions.keys()),
                        "result": True,
                        "passed_symbols": passed_symbols,
                        "failed_symbols": [],
                        "symbol_results": [],
                        "values": [],
                    }
            
            # === 기존 data 기반 플러그인 처리 (RSI, MACD 등) ===
            print(f"   - data 원본: {original_data_expr}")
            
            # 필드 매핑 추출
            field_mapping = {
                "close_field": config.get("close_field", "close"),
                "open_field": config.get("open_field", "open"),
                "high_field": config.get("high_field", "high"),
                "low_field": config.get("low_field", "low"),
                "volume_field": config.get("volume_field", "volume"),
                "date_field": config.get("date_field", "date"),
                "symbol_field": config.get("symbol_field", "symbol"),
                "exchange_field": config.get("exchange_field", "exchange"),
            }
            
            # 필수 데이터 추출 (새 형식: data)
            data = config.get("data", [])
            position_data = config.get("position_data")
            held_symbols = config.get("held_symbols", [])
            symbols = config.get("symbols", [])
            
            # symbols가 비어있으면 data에서 자동 추출
            symbol_field = field_mapping["symbol_field"]
            exchange_field = field_mapping["exchange_field"]
            if not symbols and data and isinstance(data, list):
                # 플랫 배열에서 고유 종목 추출
                seen = set()
                for item in data:
                    if isinstance(item, dict):
                        sym = item.get(symbol_field, "")
                        if sym and sym not in seen:
                            seen.add(sym)
                            symbols.append({
                                "symbol": sym,
                                "exchange": item.get(exchange_field, "NASDAQ")
                            })
                print(f"   - symbols 자동 추출: {symbols}")
            
            print(f"   - data 평가 후: {type(data).__name__}, {len(data) if isinstance(data, list) else 0} rows")
            print(f"   - symbols: {symbols}")
            print(f"   - field_mapping: {field_mapping}")
            
            # data가 없으면 에러
            if not data:
                context.log("error", 
                    f"ConditionNode '{node_id}': data가 설정되지 않았습니다. "
                    f"config에 data: {{{{ flatten(nodes.historicaldata_1.values, 'time_series') }}}} 형태로 추가하세요.",
                    node_id
                )
                return {
                    "result": False,
                    "passed_symbols": [],
                    "failed_symbols": [],
                    "values": [],
                    "error": "missing_data",
                    "error_message": "data가 설정되지 않았습니다. 예: flatten(nodes.historicaldata_1.values, 'time_series')",
                }
            
            # fields 표현식 평가
            evaluated_fields = fields or config.get("fields", {}) or config.get("params", {})
            if evaluated_fields:
                expr_context = context.get_expression_context()
                evaluator = ExpressionEvaluator(expr_context)
                evaluated_fields = evaluator.evaluate_fields(evaluated_fields)
            
            # symbols 정규화 (거래소 정보 포함)
            from programgarden_core.models import symbols_to_dict_list, extract_symbol_codes
            normalized_symbols = symbols_to_dict_list(symbols)
            symbol_codes = extract_symbol_codes(symbols)  # 플러그인 호출용
            
            # 플러그인 실행 (새 형식)
            context.log("info", f"Condition running with {len(data)} data rows", node_id)
            
            return await self._execute_condition_plugin(
                node_id, normalized_symbols, data, evaluated_fields, 
                plugin, context, sandbox,
                plugin_id=plugin_id,
                field_mapping=field_mapping,
                held_symbols=held_symbols,
                position_data=position_data,
            )
        except PluginTimeoutError as e:
            context.log("error", f"Plugin timeout: {e}", node_id)
            return {
                "result": False,
                "passed_symbols": [],
                "failed_symbols": symbols if 'symbols' in locals() else [],
                "values": {},
                "error": "plugin_timeout",
            }
        finally:
            # 리소스 반환
            await context.release_resources_after_task(
                task_type="ConditionNode",
                weight=hints.get_weight() if hasattr(hints, 'get_weight') else 1.0,
            )

    async def _execute_condition_plugin(
        self,
        node_id: str,
        normalized_symbols: List[Dict[str, str]],  # [{exchange, symbol}, ...]
        data: List[Dict[str, Any]],  # 평탄화된 데이터 [{date, close, symbol, exchange, ...}, ...]
        fields: Dict[str, Any],  # 플러그인 파라미터 (period, threshold 등)
        plugin: Optional[Callable],
        context: ExecutionContext,
        sandbox: "PluginSandbox",
        plugin_id: str = "Unknown",
        field_mapping: Optional[Dict[str, str]] = None,
        held_symbols: Optional[List[str]] = None,
        position_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        조건 플러그인 실행 (새 형식: data + field_mapping)
        
        입력:
        - data: 평탄화된 배열 [{date, close, symbol, exchange, ...}, ...]
        - field_mapping: 필드 매핑 {close_field: "close", date_field: "date", ...}
        - fields: 플러그인 파라미터
        - normalized_symbols: 평가 대상 심볼 [{exchange, symbol}, ...]
        
        출력:
        - passed_symbols: [{exchange, symbol}, ...]
        - failed_symbols: [{exchange, symbol}, ...]
        - symbol_results: [{symbol, exchange, rsi, ...}, ...]
        - values: [{symbol, exchange, time_series: [...], ...}, ...]
        """
        from programgarden.plugin import PluginSandbox, PluginTimeoutError
        
        passed_symbols = []
        failed_symbols = []
        symbol_results = []
        values = []
        
        if field_mapping is None:
            field_mapping = {}
        
        if plugin:
            # 플러그인에 전달할 kwargs
            plugin_kwargs = {
                "data": data,  # 평탄화된 배열
                "fields": fields,  # 플러그인 파라미터
                "field_mapping": field_mapping,  # 필드 매핑
                "symbols": normalized_symbols,  # [{exchange, symbol}, ...]
            }
            
            # 추가 포트 데이터
            if held_symbols:
                plugin_kwargs["held_symbols"] = held_symbols
            if position_data:
                plugin_kwargs["position_data"] = position_data
            
            try:
                # 종목 수에 따라 배치 처리 결정
                symbol_codes = [s["symbol"] for s in normalized_symbols]
                
                if len(symbol_codes) > sandbox._default_batch_size:
                    # 대량 종목은 배치 처리
                    result = await sandbox.execute_batched(
                        plugin_id=plugin_id,
                        plugin_callable=plugin,
                        symbols=symbol_codes,
                        data=data,
                        fields=fields,
                        field_mapping=field_mapping,
                    )
                else:
                    # 일반 실행
                    result = await sandbox.execute(
                        plugin_id=plugin_id,
                        plugin_callable=plugin,
                        kwargs=plugin_kwargs,
                    )
                
                passed_symbols = result.get("passed_symbols", [])
                failed_symbols = result.get("failed_symbols", [])
                symbol_results = result.get("symbol_results", [])
                values = result.get("values", [])
                
            except PluginTimeoutError as e:
                context.log("error", f"Plugin timeout: {e}", node_id)
                failed_symbols = normalized_symbols
            except Exception as e:
                context.log("error", f"Plugin error: {e}", node_id)
                import traceback
                context.log("debug", f"Plugin traceback: {traceback.format_exc()}", node_id)
                failed_symbols = normalized_symbols
        else:
            # 플러그인 없으면 모두 통과
            passed_symbols = normalized_symbols
            for sym in normalized_symbols:
                symbol_results.append({
                    "symbol": sym["symbol"], 
                    "exchange": sym.get("exchange", "UNKNOWN"), 
                    "result": True
                })
        
        context.log(
            "info",
            f"Condition evaluated: {len(passed_symbols)}/{len(normalized_symbols)} passed",
            node_id,
        )
        
        return {
            "symbols": normalized_symbols,  # 입력 symbols (거래소 포함)
            "result": len(passed_symbols) > 0,
            "passed_symbols": passed_symbols,  # [{exchange, symbol}, ...]
            "failed_symbols": failed_symbols,  # [{exchange, symbol}, ...]
            "symbol_results": symbol_results,  # [{symbol, exchange, rsi, price, ...}, ...]
            "values": values,  # [{symbol, exchange, time_series: [...], ...}, ...]
        }


class LogicNodeExecutor(NodeExecutorBase):
    """
    LogicNode executor - 조건 조합
    
    여러 ConditionNode의 결과를 조합하여 최종 조건 판정.
    
    지원 연산자:
    - all: 모든 조건 만족 (AND)
    - any: 하나 이상 만족 (OR)
    - not: 모든 조건 불만족
    - xor: 정확히 하나만 만족
    - at_least: N개 이상 만족 (threshold 필요)
    - at_most: N개 이하 만족 (threshold 필요)
    - exactly: 정확히 N개 만족 (threshold 필요)
    - weighted: 가중치 합이 threshold 이상 (conditions 내 weight 사용)
    
    입력: conditions 필드 (각 조건의 is_condition_met, passed_symbols, weight 바인딩)
    출력: result (bool), passed_symbols (list)
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """조건 조합 실행"""
        
        # config에서 표현식 평가
        config = evaluate_all_bindings(config, context, node_id)
        
        operator = config.get("operator", "all")
        threshold = config.get("threshold")
        conditions = config.get("conditions", [])  # 조건 객체 목록
        
        # conditions 필수 검증
        if not conditions:
            context.log("error", "LogicNode requires at least one condition in 'conditions' field", node_id)
            return {"result": False, "passed_symbols": [], "details": [], "error": "conditions field is required"}
        
        context.log("info", f"LogicNode executing with operator='{operator}', conditions_count={len(conditions)}", node_id)
        
        # 각 조건 결과 수집
        condition_results: List[Dict[str, Any]] = []
        all_passed_symbols: List[List[str]] = []
        weights: Dict[int, float] = {}  # index -> weight
        
        for idx, cond in enumerate(conditions):
            # 조건 객체 검증
            if not isinstance(cond, dict):
                context.log("warning", f"Condition at index {idx} is not a dict, skipping", node_id)
                continue
            
            # is_condition_met 필수
            is_met = cond.get("is_condition_met")
            if is_met is None:
                context.log("warning", f"Condition at index {idx} missing 'is_condition_met', treating as False", node_id)
                is_met = False
            
            # passed_symbols 필수
            passed_symbols = cond.get("passed_symbols")
            if passed_symbols is None:
                passed_symbols = []
            if not isinstance(passed_symbols, list):
                passed_symbols = []
            
            # weight (optional, default 1.0)
            weight = cond.get("weight", 1.0)
            if not isinstance(weight, (int, float)):
                weight = 1.0
            weights[idx] = float(weight)
            
            condition_results.append({
                "index": idx,
                "result": bool(is_met),
                "passed_symbols": passed_symbols,
                "weight": weight,
            })
            all_passed_symbols.append(passed_symbols if isinstance(passed_symbols, list) else [])
        
        if not condition_results:
            context.log("warning", "No valid condition results to combine", node_id)
            return {"result": False, "passed_symbols": [], "details": []}
        
        # 연산자별 로직 실행
        final_result, final_passed_symbols = self._apply_operator(
            operator=operator,
            results=condition_results,
            all_passed_symbols=all_passed_symbols,
            threshold=threshold,
            weights=weights,
            context=context,
            node_id=node_id,
        )
        
        context.log(
            "info",
            f"LogicNode result: {final_result}, passed_symbols: {len(final_passed_symbols)}",
            node_id,
        )
        
        return {
            "result": final_result,
            "passed_symbols": final_passed_symbols,
            "details": condition_results,  # 각 조건 결과 디테일
        }

    def _apply_operator(
        self,
        operator: str,
        results: List[Dict[str, Any]],
        all_passed_symbols: List[List[str]],
        threshold: Optional[float],
        weights: Dict[int, float],
        context: ExecutionContext,
        node_id: str,
    ) -> tuple:
        """
        연산자 적용
        
        Args:
            weights: index -> weight 매핑 (conditions 내부 weight에서 추출)
        
        Returns:
            (final_result: bool, final_passed_symbols: List[str])
        """
        # 각 조건의 bool 결과 목록
        bool_results = [r["result"] for r in results]
        passed_count = sum(1 for r in bool_results if r)
        
        # 종목 코드 → 전체 정보 매핑 (거래소 정보 보존)
        # passed_symbols가 [{exchange, symbol}] 또는 ["AAPL"] 형식일 수 있음
        def build_symbol_map(symbols_list: List) -> Dict[str, Dict[str, str]]:
            """종목 리스트에서 code → {exchange, symbol} 매핑 생성"""
            result = {}
            for sym in symbols_list:
                if isinstance(sym, dict):
                    code = sym.get("symbol", "")
                    if code and code not in result:
                        result[code] = sym
                elif isinstance(sym, str) and sym:
                    if sym not in result:
                        # 레거시 형식: 거래소 추정
                        from programgarden_core.models import normalize_symbol
                        result[sym] = normalize_symbol(sym)
            return result
        
        # 모든 조건의 종목 매핑 통합
        all_symbol_maps = [build_symbol_map(s) for s in all_passed_symbols]
        combined_map: Dict[str, Dict[str, str]] = {}
        for m in all_symbol_maps:
            for code, info in m.items():
                if code not in combined_map:
                    combined_map[code] = info
        
        # 기본: 모든 조건이 공유하는 종목 (intersection)
        def intersection_symbols() -> List[Dict[str, str]]:
            if not all_passed_symbols:
                return []
            # 각 조건의 종목 코드 집합
            def extract_codes(symbols: List) -> set:
                codes = set()
                for s in symbols:
                    if isinstance(s, dict):
                        codes.add(s.get("symbol", ""))
                    elif isinstance(s, str):
                        codes.add(s)
                return codes
            
            sets = [extract_codes(s) for s in all_passed_symbols if s]
            if not sets:
                return []
            common = sets[0]
            for s in sets[1:]:
                common &= s
            # 코드를 {exchange, symbol} 형식으로 복원
            return [combined_map.get(code, {"exchange": "", "symbol": code}) for code in common if code]
        
        # union: 하나라도 포함된 종목
        def union_symbols() -> List[Dict[str, str]]:
            if not all_passed_symbols:
                return []
            codes = set()
            for s in all_passed_symbols:
                for sym in s:
                    if isinstance(sym, dict):
                        codes.add(sym.get("symbol", ""))
                    elif isinstance(sym, str):
                        codes.add(sym)
            # 코드를 {exchange, symbol} 형식으로 복원
            return [combined_map.get(code, {"exchange": "", "symbol": code}) for code in codes if code]
        
        # 연산자별 처리
        if operator == "all":
            # AND: 모든 조건 만족
            final_result = all(bool_results)
            final_passed = intersection_symbols() if final_result else []
            
        elif operator == "any":
            # OR: 하나 이상 만족
            final_result = any(bool_results)
            final_passed = union_symbols() if final_result else []
            
        elif operator == "not":
            # NOT: 모든 조건 불만족
            final_result = not any(bool_results)
            # not이면 passed_symbols는 빈 배열 (조건 불만족이 목표)
            final_passed = []
            
        elif operator == "xor":
            # XOR: 정확히 하나만 만족
            final_result = passed_count == 1
            if final_result:
                # 만족한 조건의 passed_symbols 반환
                for i, r in enumerate(bool_results):
                    if r:
                        final_passed = all_passed_symbols[i] if all_passed_symbols else []
                        break
                else:
                    final_passed = []
            else:
                final_passed = []
                
        elif operator == "at_least":
            # N개 이상 만족
            if threshold is None:
                context.log("warning", "at_least requires threshold, defaulting to 1", node_id)
                threshold = 1
            final_result = passed_count >= threshold
            final_passed = union_symbols() if final_result else []
            
        elif operator == "at_most":
            # N개 이하 만족
            if threshold is None:
                context.log("warning", "at_most requires threshold, defaulting to 1", node_id)
                threshold = 1
            final_result = passed_count <= threshold
            final_passed = union_symbols() if final_result else []
            
        elif operator == "exactly":
            # 정확히 N개 만족
            if threshold is None:
                context.log("warning", "exactly requires threshold, defaulting to 1", node_id)
                threshold = 1
            final_result = passed_count == threshold
            final_passed = union_symbols() if final_result else []
            
        elif operator == "weighted":
            # 가중치 합산
            if threshold is None:
                context.log("warning", "weighted requires threshold, defaulting to 0.5", node_id)
                threshold = 0.5
            
            total_weight = 0.0
            for i, r in enumerate(results):
                if r["result"]:
                    # weights에 index가 없으면 기본 1.0
                    w = weights.get(i, 1.0)
                    total_weight += w
            
            final_result = total_weight >= threshold
            final_passed = union_symbols() if final_result else []
            context.log("debug", f"Weighted sum: {total_weight} >= {threshold} = {final_result}", node_id)
            
        else:
            context.log("warning", f"Unknown operator: {operator}, defaulting to 'all'", node_id)
            final_result = all(bool_results)
            final_passed = intersection_symbols() if final_result else []
        
        return final_result, final_passed


class PerformanceConditionNodeExecutor(NodeExecutorBase):
    """
    PerformanceConditionNode executor - 성과 기반 조건 평가
    
    계좌 데이터, 백테스트 결과, 거래 내역에서 성과 지표를 계산하고
    조건 충족 여부를 평가합니다.
    
    지원 지표:
    - pnl_rate: 수익률 (%)
    - pnl_amount: 손익 금액
    - mdd: 최대 낙폭 (%)
    - win_rate: 승률 (%)
    - sharpe_ratio: 샤프 비율
    - profit_factor: 수익 팩터
    - avg_win: 평균 수익
    - avg_loss: 평균 손실
    - consecutive_wins: 연속 수익 횟수
    - consecutive_losses: 연속 손실 횟수
    - total_trades: 총 거래 횟수
    - daily_pnl: 일일 손익
    """

    # 연산자 매핑
    OPERATORS = {
        "gt": lambda a, b: a > b,
        "lt": lambda a, b: a < b,
        "gte": lambda a, b: a >= b,
        "lte": lambda a, b: a <= b,
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
    }

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """성과 기반 조건 평가"""
        
        # 설정 추출
        metric = config.get("metric", "pnl_rate")
        operator = config.get("operator", "gt")
        threshold = config.get("threshold", 0.0)
        symbol_filter = config.get("symbol_filter")
        time_period = config.get("time_period")  # TODO: 시간 기반 필터링 구현
        
        context.log(
            "info", 
            f"Evaluating performance: {metric} {operator} {threshold}", 
            node_id
        )
        
        # 입력 데이터 가져오기
        position_data = config.get("position_data") or {}
        balance_data = config.get("balance_data") or {}
        equity_curve = config.get("equity_curve") or []
        trade_history = config.get("trade_history") or []
        
        # 종목 필터 적용
        if symbol_filter and position_data:
            position_data = {
                k: v for k, v in position_data.items() 
                if k in symbol_filter
            }
        
        # 지표 계산
        metric_value = self._calculate_metric(
            metric=metric,
            position_data=position_data,
            balance_data=balance_data,
            equity_curve=equity_curve,
            trade_history=trade_history,
            context=context,
            node_id=node_id,
        )
        
        # 조건 평가
        compare_fn = self.OPERATORS.get(operator, lambda a, b: a > b)
        passed = compare_fn(metric_value, threshold)
        
        # 연산자 기호 매핑
        operator_symbols = {
            "gt": ">",
            "lt": "<",
            "gte": ">=",
            "lte": "<=",
            "eq": "==",
            "ne": "!=",
        }
        op_symbol = operator_symbols.get(operator, "?")
        
        context.log(
            "info", 
            f"Performance condition: {metric}={metric_value:.4f} {op_symbol} {threshold} => {'PASSED' if passed else 'FAILED'}", 
            node_id
        )
        
        # 결과 구성
        result = {
            "passed": passed,
            "metric": metric,
            "metric_value": metric_value,
            "operator": operator,
            "threshold": threshold,
            "comparison": f"{metric_value:.4f} {op_symbol} {threshold}",
        }
        
        details = {
            "metric": metric,
            "value": metric_value,
            "threshold": threshold,
            "operator": operator,
            "passed": passed,
            "symbol_filter": symbol_filter,
            "time_period": time_period,
            "input_summary": {
                "positions_count": len(position_data),
                "equity_points": len(equity_curve),
                "trades_count": len(trade_history),
            },
        }
        
        return {
            "result": result,
            "passed": passed,
            "metric_value": metric_value,
            "details": details,
        }

    def _calculate_metric(
        self,
        metric: str,
        position_data: Dict[str, Any],
        balance_data: Dict[str, Any],
        equity_curve: List[Dict[str, Any]],
        trade_history: List[Dict[str, Any]],
        context: ExecutionContext,
        node_id: str,
    ) -> float:
        """지표 계산"""
        
        if metric == "pnl_rate":
            # 수익률: 포지션 평균 수익률 또는 전체 자산 수익률
            if position_data:
                rates = [
                    p.get("pnl_rate", p.get("return_rate_percent", 0))
                    for p in position_data.values()
                    if isinstance(p, dict)
                ]
                return sum(rates) / len(rates) if rates else 0.0
            elif equity_curve and len(equity_curve) >= 2:
                first = equity_curve[0].get("equity", equity_curve[0].get("value", 0))
                last = equity_curve[-1].get("equity", equity_curve[-1].get("value", 0))
                return ((last - first) / first * 100) if first > 0 else 0.0
            return 0.0
            
        elif metric == "pnl_amount":
            # 손익 금액 합계
            if position_data:
                amounts = [
                    p.get("pnl_amount", p.get("profit", 0))
                    for p in position_data.values()
                    if isinstance(p, dict)
                ]
                return sum(amounts)
            elif trade_history:
                return sum(t.get("pnl", t.get("profit", 0)) for t in trade_history)
            return 0.0
            
        elif metric == "mdd":
            # 최대 낙폭 (%)
            if not equity_curve:
                return 0.0
            
            peak = 0.0
            max_drawdown = 0.0
            
            for point in equity_curve:
                value = point.get("equity", point.get("value", 0))
                if value > peak:
                    peak = value
                if peak > 0:
                    drawdown = (peak - value) / peak * 100
                    max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        elif metric == "win_rate":
            # 승률 (%)
            if not trade_history:
                return 0.0
            
            wins = sum(1 for t in trade_history if t.get("pnl", t.get("profit", 0)) > 0)
            total = len(trade_history)
            
            return (wins / total * 100) if total > 0 else 0.0
            
        elif metric == "sharpe_ratio":
            # 샤프 비율 (일일 수익률 기준, 무위험 이자율 0 가정)
            if len(equity_curve) < 2:
                return 0.0
            
            import math
            
            # 일일 수익률 계산
            returns = []
            for i in range(1, len(equity_curve)):
                prev = equity_curve[i-1].get("equity", equity_curve[i-1].get("value", 0))
                curr = equity_curve[i].get("equity", equity_curve[i].get("value", 0))
                if prev > 0:
                    returns.append((curr - prev) / prev)
            
            if not returns:
                return 0.0
            
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0001
            
            # 연간화 (252 거래일 가정)
            annualized_sharpe = (mean_return / std_dev) * math.sqrt(252)
            
            return annualized_sharpe
            
        elif metric == "profit_factor":
            # 수익 팩터 (총 수익 / 총 손실)
            if not trade_history:
                return 0.0
            
            total_profit = sum(
                t.get("pnl", t.get("profit", 0)) 
                for t in trade_history 
                if t.get("pnl", t.get("profit", 0)) > 0
            )
            total_loss = abs(sum(
                t.get("pnl", t.get("profit", 0)) 
                for t in trade_history 
                if t.get("pnl", t.get("profit", 0)) < 0
            ))
            
            return (total_profit / total_loss) if total_loss > 0 else float('inf')
            
        elif metric == "avg_win":
            # 평균 수익
            wins = [
                t.get("pnl", t.get("profit", 0)) 
                for t in trade_history 
                if t.get("pnl", t.get("profit", 0)) > 0
            ]
            return sum(wins) / len(wins) if wins else 0.0
            
        elif metric == "avg_loss":
            # 평균 손실 (절대값)
            losses = [
                abs(t.get("pnl", t.get("profit", 0)))
                for t in trade_history 
                if t.get("pnl", t.get("profit", 0)) < 0
            ]
            return sum(losses) / len(losses) if losses else 0.0
            
        elif metric == "consecutive_wins":
            # 현재 연속 수익 횟수
            if not trade_history:
                return 0
            
            count = 0
            for t in reversed(trade_history):
                if t.get("pnl", t.get("profit", 0)) > 0:
                    count += 1
                else:
                    break
            return float(count)
            
        elif metric == "consecutive_losses":
            # 현재 연속 손실 횟수
            if not trade_history:
                return 0
            
            count = 0
            for t in reversed(trade_history):
                if t.get("pnl", t.get("profit", 0)) < 0:
                    count += 1
                else:
                    break
            return float(count)
            
        elif metric == "total_trades":
            # 총 거래 횟수
            return float(len(trade_history))
            
        elif metric == "daily_pnl":
            # 오늘 손익 (가장 최근 equity 변화)
            if len(equity_curve) < 2:
                return 0.0
            
            prev = equity_curve[-2].get("equity", equity_curve[-2].get("value", 0))
            curr = equity_curve[-1].get("equity", equity_curve[-1].get("value", 0))
            
            return curr - prev
            
        else:
            context.log("warning", f"Unknown metric: {metric}, returning 0", node_id)
            return 0.0


class MarketDataNodeExecutor(NodeExecutorBase):
    """
    MarketDataNode executor - REST API 현재가 조회 (당일 데이터만)
    
    LS Finance Market API를 사용하여 현재 시세를 조회합니다.
    - 해외주식: g3101 (현재가)
    - 해외선물: o3101 (현재가)
    
    ⚠️ 과거 N일 일봉/주봉/월봉 데이터는 HistoricalDataNode를 사용하세요.
    """

    # 거래소 코드 매핑 (해외주식 g3101용)
    # 81: NYSE/AMEX, 82: NASDAQ
    EXCHANGE_CODES = {
        "NASDAQ": "82",
        "NYSE": "81",
        "AMEX": "81",
    }

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """현재가 조회"""
        
        # 🔍 디버그 로그
        print(f"🔍 MarketDataNode config keys: {list(config.keys())}", flush=True)
        print(f"🔍 MarketDataNode config.symbols: {config.get('symbols')}", flush=True)
        
        # 입력 symbols 가져오기 (포트 또는 config에서 명시적 입력 필수)
        input_symbols = context.get_output(f"_input_{node_id}", "symbols")
        config_symbols = config.get("symbols")
        symbols = input_symbols or config_symbols
        
        print(f"🔍 MarketDataNode input_symbols: {input_symbols}", flush=True)
        print(f"🔍 MarketDataNode final symbols: {symbols}", flush=True)
        
        if not symbols:
            error_msg = "symbols 필드가 필수입니다. 종목을 직접 입력하거나 WatchlistNode를 연결하세요."
            context.log("error", error_msg, node_id)
            return {"error": error_msg, "price": {}, "volume": {}, "ohlcv": {}, "symbols": []}
        
        # config에서 명시적 connection 확인
        broker_connection = config.get("connection")
        print(f"🔍 MarketDataNode connection: {broker_connection}", flush=True)
        
        if not broker_connection:
            context.log("error", "connection 필드가 필수입니다. connection: \"{{ nodes.broker.connection }}\"를 설정하세요.", node_id)
            return {"error": "connection 필드가 필수입니다", "price": {}, "volume": {}, "ohlcv": {}}
        
        product = broker_connection.get("product", "overseas_stock")
        
        # 조회할 필드 (현재가 조회 전용 - 과거 데이터는 HistoricalDataNode 사용)
        fields = config.get("fields", ["price", "volume", "ohlcv"])
        
        context.log(
            "info", 
            f"Fetching current market data: {len(symbols)} symbols, fields={fields}, product={product}", 
            node_id
        )
        
        # product별 분기 (overseas_futures와 overseas_futureoption은 동일)
        if product == "overseas_stock":
            result = await self._fetch_overseas_stock(symbols, fields, context, node_id)
        elif product in ("overseas_futureoption", "overseas_futures"):
            result = await self._fetch_overseas_futures(symbols, fields, context, node_id)
        else:
            context.log("error", f"Unsupported product for MarketDataNode: {product}", node_id)
            result = self._empty_result(f"i18n:errors.UNSUPPORTED_PRODUCT|product={product}")
        
        return result

    async def _fetch_overseas_stock(
        self,
        symbols: List[Dict[str, str]],
        fields: List[str],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """해외주식 현재가 조회 (g3101) - 당일 데이터만 반환"""
        
        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not set. Check BrokerNode credential_id.", node_id)
            return self._empty_result("i18n:errors.CREDENTIAL_NOT_SET")
        
        try:
            from programgarden_finance.ls.overseas_stock.market.g3101.blocks import G3101InBlock
            
            ls, success, error = ensure_ls_login(
                credential.get("appkey"),
                credential.get("appsecret"),
                credential.get("paper_trading", False),
                context, node_id,
                caller_name="MarketDataNode(overseas_stock)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_result(f"i18n:errors.LS_LOGIN_FAILED|error={error}")
            
            api = ls.overseas_stock()
            
            price_data = {}
            volume_data = {}
            ohlcv_data = {}
            
            for symbol_entry in symbols:
                try:
                    # 거래소와 심볼 추출
                    exchange = symbol_entry.get("exchange", "NASDAQ")
                    symbol = symbol_entry.get("symbol", "")
                    if not symbol:
                        continue
                    
                    # 거래소 코드 변환 (81: NYSE/AMEX, 82: NASDAQ)
                    exchange_code = self.EXCHANGE_CODES.get(exchange.upper(), "82")
                    
                    # KEY종목코드 생성 (거래소코드 + 심볼, 예: "82AAPL")
                    keysymbol = f"{exchange_code}{symbol}"
                    
                    # g3101 현재가 조회
                    body = G3101InBlock(
                        keysymbol=keysymbol,
                        exchcd=exchange_code,
                        symbol=symbol,
                    )
                    
                    response = api.market().g3101(body=body).req()
                    
                    if response and response.block:
                        out_block = response.block
                        
                        # price 필드
                        if "price" in fields:
                            price_data[symbol] = {
                                "price": float(out_block.price or 0),
                                "change": float(out_block.diff or 0),
                                "change_pct": float(out_block.rate or 0),
                                "timestamp": "",
                                "exchange": exchange,
                            }
                        
                        # volume 필드
                        if "volume" in fields:
                            volume_data[symbol] = {
                                "volume": int(out_block.volume or 0),
                                "value": float(out_block.amount or 0),
                                "exchange": exchange,
                            }
                        
                        # ohlcv 필드 (현재가 기준 단일 데이터)
                        if "ohlcv" in fields:
                            from datetime import datetime
                            ohlcv_data[symbol] = [{
                                "date": datetime.now().strftime("%Y%m%d"),
                                "open": float(out_block.open or 0),
                                "high": float(out_block.high or 0),
                                "low": float(out_block.low or 0),
                                "close": float(out_block.price or 0),
                                "volume": int(out_block.volume or 0),
                                "exchange": exchange,
                            }]
                        
                        context.log("debug", f"Fetched {exchange}:{symbol}: price={out_block.price}", node_id)
                    else:
                        context.log("warning", f"No data for {exchange}:{symbol}", node_id)
                        
                except Exception as e:
                    context.log("warning", f"Failed to fetch {exchange}:{symbol}: {e}", node_id)
                    continue
            
            return {
                "price": price_data,
                "volume": volume_data,
                "ohlcv": ohlcv_data,
                "symbols": list(price_data.keys()),
            }
            
        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_result(f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Market data fetch error: {e}", node_id)
            return self._empty_result(f"i18n:errors.MARKET_DATA_FETCH_ERROR|error={e}")

    async def _fetch_overseas_futures(
        self,
        symbols: List[Dict[str, str]],
        fields: List[str],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """해외선물 현재가 조회 (o3105) - 당일 데이터만 반환"""
        
        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not set. Check BrokerNode credential_id.", node_id)
            return self._empty_result("i18n:errors.CREDENTIAL_NOT_SET")
        
        try:
            from programgarden_finance.ls.overseas_futureoption.market.o3105.blocks import O3105InBlock
            
            ls, success, error = ensure_ls_login(
                credential.get("appkey"),
                credential.get("appsecret"),
                credential.get("paper_trading", False),
                context, node_id,
                caller_name="MarketDataNode(overseas_futureoption)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_result(f"i18n:errors.LS_LOGIN_FAILED|error={error}")
            
            api = ls.overseas_futureoption()
            
            price_data = {}
            volume_data = {}
            ohlcv_data = {}
            
            for symbol_entry in symbols:
                try:
                    # 해외선물은 exchange 대신 symbol만 사용 (예: "GCGF25", "CLH25")
                    exchange = symbol_entry.get("exchange", "CME")
                    symbol = symbol_entry.get("symbol", "")
                    if not symbol:
                        continue
                    
                    # o3105 현재가 조회 (종목심볼만 필요)
                    body = O3105InBlock(symbol=symbol)
                    
                    context.log("debug", f"Calling o3105 for symbol={symbol}", node_id)
                    response = api.market().o3105(body=body).req()
                    context.log("debug", f"o3105 response: {response}", node_id)
                    
                    if response and response.block:
                        out_block = response.block
                        
                        # price 필드
                        if "price" in fields:
                            price_data[symbol] = {
                                "price": float(out_block.TrdP or 0),
                                "change": float(out_block.YdiffP or 0),
                                "change_pct": float(out_block.Diff or 0),
                                "timestamp": out_block.RcvTm or "",
                                "exchange": exchange,
                                "symbol_name": out_block.SymbolNm or symbol,
                            }
                        
                        # volume 필드
                        if "volume" in fields:
                            volume_data[symbol] = {
                                "volume": int(out_block.TotQ or 0),
                                "value": float(out_block.TotAmt or 0),
                                "exchange": exchange,
                            }
                        
                        # ohlcv 필드 (현재가 기준 당일 데이터)
                        if "ohlcv" in fields:
                            from datetime import datetime
                            ohlcv_data[symbol] = [{
                                "date": out_block.KorDate or datetime.now().strftime("%Y%m%d"),
                                "open": float(out_block.OpenP or 0),
                                "high": float(out_block.HighP or 0),
                                "low": float(out_block.LowP or 0),
                                "close": float(out_block.TrdP or 0),  # 현재가 = 종가
                                "volume": int(out_block.TotQ or 0),
                                "exchange": exchange,
                            }]
                        
                        context.log("debug", f"Fetched {exchange}:{symbol}: price={out_block.TrdP}", node_id)
                    else:
                        context.log("warning", f"No data for {exchange}:{symbol}", node_id)
                        
                except Exception as e:
                    context.log("warning", f"Failed to fetch {exchange}:{symbol}: {e}", node_id)
                    continue
            
            return {
                "price": price_data,
                "volume": volume_data,
                "ohlcv": ohlcv_data,
                "symbols": list(price_data.keys()),
            }
            
        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_result(f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Market data fetch error: {e}", node_id)
            return self._empty_result(f"i18n:errors.MARKET_DATA_FETCH_ERROR|error={e}")

    def _empty_result(self, error_msg: str = "") -> Dict[str, Any]:
        """빈 결과 반환 (에러 시)"""
        result = {
            "price": {},
            "volume": {},
            "ohlcv": {},
            "symbols": [],
        }
        if error_msg:
            result["error"] = error_msg
        return result


class HistoricalDataNodeExecutor(NodeExecutorBase):
    """
    HistoricalDataNode executor - 과거 OHLCV 데이터 조회
    
    LS Finance Chart API를 사용하여 과거 차트 데이터를 조회합니다.
    - 해외주식: g3103 (일/주/월봉)
    - 해외선물: o3108 (일봉), o3103 (분봉)
    """

    # 거래소 코드 매핑 (해외주식)
    # Note: AMEX는 실제로 exchcd=81로 반환됨 (NYSE/AMEX 통합)
    EXCHANGE_CODES = {
        "NASDAQ": "82",
        "NYSE": "81",
        "AMEX": "81",  # AMEX도 81 사용 (NYSE/AMEX 통합)
    }

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """과거 데이터 조회"""
        
        # symbols 획득 (config 필드 우선, input port 폴백)
        # config.symbols: 직접 입력 또는 바인딩 표현식 (평가 후 값)
        config_symbols = config.get("symbols")
        input_symbols = context.get_output(f"_input_{node_id}", "symbols")
        
        # config가 있으면 config 사용, 없으면 input port 사용
        if config_symbols:
            symbols_raw = config_symbols
            context.log("debug", f"Using config.symbols: {len(symbols_raw) if symbols_raw else 0} items", node_id)
        elif input_symbols:
            symbols_raw = input_symbols
            context.log("debug", f"Using input port symbols: {len(symbols_raw) if symbols_raw else 0} items", node_id)
        else:
            symbols_raw = []
        
        # symbols 정규화: [{exchange, symbol}] → 문자열 리스트 + exchange 정보 보존
        symbols = []
        symbol_exchange_map = {}  # {symbol: exchange_code}
        for entry in symbols_raw:
            if isinstance(entry, dict):
                symbol = entry.get("symbol", "")
                exchange = entry.get("exchange", "")
                exchange_code = entry.get("exchange_code", exchange)  # WatchlistNode에서 변환된 코드
                if symbol:
                    symbols.append(symbol)
                    # 거래소 이름 → LS 코드 변환
                    if exchange_code in ("NASDAQ", "82"):
                        symbol_exchange_map[symbol] = "82"
                    elif exchange_code in ("NYSE", "AMEX", "81"):
                        symbol_exchange_map[symbol] = "81"
                    elif exchange_code in ("83",):
                        symbol_exchange_map[symbol] = "83"
                    else:
                        symbol_exchange_map[symbol] = exchange_code or "82"  # 기본값 NASDAQ
            elif isinstance(entry, str):
                symbols.append(entry)
                symbol_exchange_map[entry] = "82"  # 기본값 NASDAQ
        
        # positions 데이터 가져오기 (market_code 포함)
        positions = context.get_output(f"_input_{node_id}", "positions")
        if not positions:
            positions = context.get_output("account", "positions") or {}
        
        # symbol_exchange_map을 positions에 병합 (positions가 우선)
        for symbol in symbols:
            if symbol not in positions:
                positions[symbol] = {"market_code": symbol_exchange_map.get(symbol, "82")}
        
        if not symbols:
            context.log("warning", "No symbols provided", node_id)
            return {"ohlcv_data": {}, "symbols": []}
        
        # 기간 설정 ({{ today_yyyymmdd() }}, {{ days_ago_yyyymmdd(100) }} 바인딩 사용)
        start_date = config.get("start_date", "")
        end_date = config.get("end_date", "")
        interval = config.get("interval", "1d")  # 1d, 1w, 1m, 1min 등
        
        # 날짜 형식 변환: YYYY-MM-DD → YYYYMMDD (finance 패키지 요구사항)
        start_date = self._normalize_date_format(start_date)
        end_date = self._normalize_date_format(end_date)
        
        # config에서 명시적 connection 확인 (바인딩 표현식 해석됨)
        # 예: "connection": "{{ nodes.broker_2.connection }}"
        broker_connection = config.get("connection")
        
        # connection 없으면 기본값 사용 (HistoricalDataNode는 선택적)
        product = broker_connection.get("product", "overseas_stock") if broker_connection else "overseas_stock"
        if not broker_connection:
            context.log("warning", "connection 필드가 없습니다. 기본값(overseas_stock) 사용. connection: \"{{ nodes.broker.connection }}\"를 설정하면 정확한 product를 사용합니다.", node_id)
        
        context.log(
            "info", 
            f"Fetching historical data: {len(symbols)} symbols, {start_date}~{end_date}, {interval}, product={product}", 
            node_id
        )
        
        # product별 분기 (overseas_futures와 overseas_futureoption은 동일)
        if product == "overseas_stock":
            ohlcv_data = await self._fetch_overseas_stock(symbols, start_date, end_date, interval, context, node_id, positions, symbol_exchange_map, symbols_raw)
        elif product in ("overseas_futureoption", "overseas_futures"):
            ohlcv_data = await self._fetch_overseas_futures(symbols, start_date, end_date, interval, context, node_id, symbols_raw)
        else:
            context.log("error", f"Unsupported product for HistoricalDataNode: {product}", node_id)
            ohlcv_data = self._empty_historical_result(symbols_raw, f"i18n:errors.UNSUPPORTED_PRODUCT|product={product}")
        
        # 출력: values (time_series 포함 배열 형식)
        return {
            "values": ohlcv_data,  # [{symbol, exchange, time_series: [...]}, ...]
            "symbols": [item.get("symbol") for item in ohlcv_data if isinstance(item, dict)],
            "period": f"{start_date}~{end_date}",
            "interval": interval,
        }

    def _normalize_date_format(self, date_str: str) -> str:
        """
        날짜 형식을 finance 패키지 요구사항(YYYYMMDD)으로 정규화.
        
        지원 형식:
        - YYYY-MM-DD → YYYYMMDD
        - YYYY/MM/DD → YYYYMMDD
        - YYYYMMDD → YYYYMMDD (그대로)
        - 빈 문자열/None → 오늘 날짜
        """
        from datetime import datetime
        
        if not date_str or date_str.startswith("{{"):
            # 표현식이 resolve 안 됐거나 빈 값이면 오늘 날짜 사용
            return datetime.now().strftime("%Y%m%d")
        
        # 구분자 제거
        normalized = date_str.replace("-", "").replace("/", "").strip()
        
        # 8자리 숫자인지 검증
        if len(normalized) == 8 and normalized.isdigit():
            return normalized
        
        # 파싱 시도
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%Y%m%d")
            except ValueError:
                continue
        
        # 파싱 실패 시 오늘 날짜 반환
        return datetime.now().strftime("%Y%m%d")

    async def _fetch_overseas_stock(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        interval: str,
        context: ExecutionContext,
        node_id: str,
        positions: Dict[str, Any] = None,
        symbol_exchange_map: Dict[str, str] = None,
        symbols_raw: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """해외주식 차트 데이터 조회 (g3204)
        
        g3204 API 사용 (sdate, edate, qrycnt 지원):
        - g3103: date 기준 최근 30개만 반환 (제한적)
        - g3204: 시작일~종료일 범위, 최대 500개 조회 가능
        
        반환: [{symbol, exchange, time_series: [{date, open, high, low, close, volume}, ...]}, ...]
        """
        
        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not set for HistoricalDataNode", node_id)
            return self._empty_historical_result(symbols, "i18n:errors.CREDENTIAL_NOT_SET")
        
        try:
            from programgarden_finance.ls.overseas_stock.chart.g3204.blocks import G3204InBlock
            
            ls, success, error = ensure_ls_login(
                credential.get("appkey"),
                credential.get("appsecret"),
                credential.get("paper_trading", False),
                context, node_id,
                caller_name="HistoricalDataNode(overseas_stock)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_historical_result(symbols, f"i18n:errors.LS_LOGIN_FAILED|error={error}")
            
            api = ls.overseas_stock()
            
            # interval → gubun 변환 (g3204: 2=일, 3=주, 4=월, 5=년)
            gubun_map = {"1d": "2", "1w": "3", "1M": "4", "1Y": "5"}
            gubun = gubun_map.get(interval, "2")
            
            # 거래소 코드 매핑 (역변환용)
            exchcd_to_exchange = {"82": "NASDAQ", "81": "NYSE", "83": "AMEX"}
            
            # symbols_raw에서 exchange 정보 추출
            symbol_to_exchange = {}
            if symbols_raw:
                for entry in symbols_raw:
                    if isinstance(entry, dict):
                        sym = entry.get("symbol", "")
                        exch = entry.get("exchange", "NASDAQ")
                        symbol_to_exchange[sym] = exch
            
            result_list = []  # [{symbol, exchange, time_series: [...]}, ...]
            
            for symbol in symbols:
                try:
                    # positions에서 market_code 가져오기 (LS증권 거래소 코드: 81=NYSE/AMEX, 82=NASDAQ)
                    exchcd = "82"  # 기본값 NASDAQ
                    if positions and symbol in positions:
                        pos_market_code = positions[symbol].get("market_code", "")
                        if pos_market_code:
                            exchcd = pos_market_code
                    
                    # symbols_raw에서 exchange 정보 가져오기 (우선순위: symbols_raw > exchcd 변환)
                    exchange = symbol_to_exchange.get(symbol) or exchcd_to_exchange.get(exchcd, "NASDAQ")
                    
                    keysymbol = f"{exchcd}{symbol}"
                    
                    # g3204 API 사용 (sdate, edate, qrycnt 지원)
                    body = G3204InBlock(
                        sujung="Y",  # 수정주가 적용
                        delaygb="R",
                        comp_yn="N",
                        keysymbol=keysymbol,
                        exchcd=exchcd,
                        symbol=symbol,
                        gubun=gubun,
                        qrycnt=500,  # 최대 500개 조회
                        sdate=start_date,
                        edate=end_date,
                    )
                    
                    # chart()는 메서드, req_async() 사용
                    result = await api.chart().g3204(body=body).req_async()
                    
                    if result.block1:
                        bars = []
                        for item in result.block1:
                            bars.append({
                                "date": item.date,  # g3204는 date 필드 사용 (g3103은 chedate)
                                "open": float(item.open) if item.open else 0,
                                "high": float(item.high) if item.high else 0,
                                "low": float(item.low) if item.low else 0,
                                "close": float(item.close) if item.close else 0,
                                "volume": int(item.volume) if item.volume else 0,
                            })
                        # 날짜순 정렬 (오래된 것부터)
                        bars.sort(key=lambda x: x["date"])
                        result_list.append({
                            "symbol": symbol,
                            "exchange": exchange,
                            "time_series": bars,
                        })
                        context.log("debug", f"Fetched {len(bars)} bars for {symbol} ({start_date}~{end_date})", node_id)
                    else:
                        context.log("warning", f"No data for {symbol}", node_id)
                        result_list.append({
                            "symbol": symbol,
                            "exchange": exchange,
                            "time_series": [],
                        })
                        
                except Exception as e:
                    context.log("warning", f"Error fetching {symbol}: {e}", node_id)
                    # symbols_raw에서 exchange 정보 가져오기
                    exchange = symbol_to_exchange.get(symbol, "NASDAQ")
                    result_list.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "time_series": [],
                    })
            
            return result_list
            
        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_historical_result(symbols, f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Historical data fetch error: {e}", node_id)
            return self._empty_historical_result(symbols, f"i18n:errors.HISTORICAL_DATA_FETCH_ERROR|error={e}")

    async def _fetch_overseas_futures(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        interval: str,
        context: ExecutionContext,
        node_id: str,
        symbols_raw: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        해외선물 차트 데이터 조회 (o3108 일봉 / o3103 분봉)
        
        - 일봉/주봉/월봉: o3108
        - 분봉 (30초, 1분, 30분 등): o3103
        
        반환: [{symbol, exchange, time_series: [{date, open, high, low, close, volume}, ...]}, ...]
        """
        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not set for HistoricalDataNode(futures)", node_id)
            return self._empty_historical_result(symbols_raw or [], "i18n:errors.CREDENTIAL_NOT_SET")
        
        try:
            ls, success, error = ensure_ls_login(
                credential.get("appkey"),
                credential.get("appsecret"),
                credential.get("paper_trading", False),
                context, node_id,
                caller_name="HistoricalDataNode(overseas_futures)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_historical_result(symbols_raw or [], f"i18n:errors.LS_LOGIN_FAILED|error={error}")
            
            api = ls.overseas_futureoption()
            result_list = []
            
            # symbols_raw에서 exchange 정보 추출
            symbol_to_exchange = {}
            if symbols_raw:
                for entry in symbols_raw:
                    if isinstance(entry, dict):
                        sym = entry.get("symbol", "")
                        exch = entry.get("exchange", "CME")  # 선물 기본값 CME
                        symbol_to_exchange[sym] = exch
            
            # interval별 분기
            is_minute_data = interval in ["1min", "5min", "15min", "30min", "30s"]
            
            for symbol in symbols:
                try:
                    if is_minute_data:
                        # 분봉: o3103
                        bars = await self._fetch_futures_minute_chart(api, symbol, interval, context, node_id)
                    else:
                        # 일봉/주봉/월봉: o3108
                        bars = await self._fetch_futures_daily_chart(api, symbol, start_date, end_date, interval, context, node_id)
                    
                    exchange = symbol_to_exchange.get(symbol, "CME")
                    result_list.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "time_series": bars,
                    })
                    context.log("debug", f"Fetched {len(bars)} bars for {symbol}", node_id)
                    
                except Exception as e:
                    context.log("warning", f"Error fetching futures {symbol}: {e}", node_id)
                    exchange = symbol_to_exchange.get(symbol, "CME")
                    result_list.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "time_series": [],
                    })
            
            return result_list
            
        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_historical_result(symbols, f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Historical data fetch error: {e}", node_id)
            return self._empty_historical_result(symbols, f"i18n:errors.HISTORICAL_DATA_FETCH_ERROR|error={e}")

    async def _fetch_futures_daily_chart(
        self,
        api,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str,
        context: ExecutionContext,
        node_id: str,
    ) -> List[Dict[str, Any]]:
        """해외선물 일봉/주봉/월봉 조회 (o3108)"""
        from programgarden_finance.ls.overseas_futureoption.chart.o3108.blocks import O3108InBlock
        
        # interval → gubun 변환 (0=일, 1=주, 2=월)
        gubun_map = {"1d": "0", "1w": "1", "1M": "2"}
        gubun = gubun_map.get(interval, "0")
        
        body = O3108InBlock(
            shcode=symbol,
            gubun=gubun,
            qrycnt=200,     # 최대 조회 건수
            sdate=start_date,
            edate=end_date,
        )
        
        result = await api.chart().o3108(body=body).req_async()
        
        bars = []
        if result.block1:
            for item in result.block1:
                bars.append({
                    "date": item.date if hasattr(item, 'date') else "",
                    "open": float(item.open) if hasattr(item, 'open') and item.open else 0,
                    "high": float(item.high) if hasattr(item, 'high') and item.high else 0,
                    "low": float(item.low) if hasattr(item, 'low') and item.low else 0,
                    "close": float(item.close) if hasattr(item, 'close') and item.close else 0,
                    "volume": int(item.volume) if hasattr(item, 'volume') and item.volume else 0,
                })
        
        # 날짜순 정렬 (오래된 것부터)
        bars.sort(key=lambda x: x["date"])
        return bars

    async def _fetch_futures_minute_chart(
        self,
        api,
        symbol: str,
        interval: str,
        context: ExecutionContext,
        node_id: str,
    ) -> List[Dict[str, Any]]:
        """해외선물 분봉 조회 (o3103)"""
        from programgarden_finance.ls.overseas_futureoption.chart.o3103.blocks import O3103InBlock
        
        # interval → ncnt 변환 (0=30초, 1=1분, 5=5분, 30=30분)
        ncnt_map = {"30s": 0, "1min": 1, "5min": 5, "15min": 15, "30min": 30}
        ncnt = ncnt_map.get(interval, 1)
        
        body = O3103InBlock(
            shcode=symbol,
            ncnt=ncnt,
            readcnt=200,    # 최대 조회 건수
        )
        
        result = await api.chart().o3103(body=body).req_async()
        
        bars = []
        if result.block1:
            for item in result.block1:
                bars.append({
                    "date": item.chetime if hasattr(item, 'chetime') else "",  # 분봉은 시간 포함
                    "open": float(item.open) if hasattr(item, 'open') and item.open else 0,
                    "high": float(item.high) if hasattr(item, 'high') and item.high else 0,
                    "low": float(item.low) if hasattr(item, 'low') and item.low else 0,
                    "close": float(item.close) if hasattr(item, 'close') and item.close else 0,
                    "volume": int(item.volume) if hasattr(item, 'volume') and item.volume else 0,
                })
        
        # 시간순 정렬 (오래된 것부터)
        bars.sort(key=lambda x: x["date"])
        return bars

    def _empty_historical_result(self, symbols_raw: List, error_msg: str = "") -> List[Dict[str, Any]]:
        """빈 historical 결과 반환 (에러 시)
        
        반환 형식: [{symbol, exchange, time_series: [], _error: "..."}, ...]
        """
        result_list = []
        for s in symbols_raw:
            if isinstance(s, dict):
                result_list.append({
                    "symbol": s.get("symbol", ""),
                    "exchange": s.get("exchange", "NASDAQ"),
                    "time_series": [],
                    "_error": error_msg,
                })
            else:
                result_list.append({
                    "symbol": str(s),
                    "exchange": "NASDAQ",
                    "time_series": [],
                    "_error": error_msg,
                })
        return result_list


class BacktestEngineNodeExecutor(NodeExecutorBase):
    """
    BacktestEngineNode executor - 백테스트 시뮬레이션 엔진
    
    입력:
    - data: 종목별 OHLCV 데이터 (플랫 배열)
    - signals: 종목별 매매 시그널 시계열
    
    출력:
    - equity_curve: 일별 포트폴리오 가치
    - trades: 거래 내역
    - metrics: 성과 지표
    
    리소스 관리:
    - 메모리/CPU 집약적 작업 (weight=3.0)
    - 리소스 부족 시 실행 대기 또는 거부
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """백테스트 실행"""
        
        # === 리소스 체크 (백테스트는 무거운 작업) ===
        resource_check = await context.check_resources_before_task(
            task_type="BacktestEngineNode",
            weight=3.0,  # 무거운 작업
            timeout=60.0,  # 최대 1분 대기
        )
        
        if not resource_check["can_proceed"]:
            context.log("error", f"Cannot run backtest: {resource_check['reason']}", node_id)
            return {
                "equity_curve": [],
                "trades": [],
                "metrics": {},
                "summary": {"error": resource_check["reason"]},
            }
        
        try:
            # === 입력 데이터 가져오기 ===
            # 1. 우선 config에서 직접 바인딩된 data 사용 (expression 평가 후)
            flat_data = config.get("data")
            
            # 2. data가 없으면 _input_{node_id}에서 시도
            if not flat_data:
                flat_data = context.get_output(f"_input_{node_id}", "data")
            
            # 3. 레거시 호환: ohlcv_data 포트
            if not flat_data:
                flat_data = context.get_output(f"_input_{node_id}", "ohlcv_data")
            if not flat_data:
                flat_data = context.get_output("historicalData", "ohlcv_data") or []
            
            # 필드 매핑 설정
            close_field = config.get("close_field", "close")
            date_field = config.get("date_field", "date")
            symbol_field = config.get("symbol_field", "symbol")
            signal_field = config.get("signal_field", "signal")
            side_field = config.get("side_field", "side")
            
            # 플랫 배열 → 종목별 딕셔너리로 변환
            ohlcv_data = self._convert_flat_to_symbol_dict(flat_data, symbol_field, date_field, close_field)
            
            # signals 가져오기 (플랫 배열 또는 values 형식 지원)
            signals = config.get("signals") or context.get_output(f"_input_{node_id}", "signals")
            if not signals:
                # ConditionNode에서 온 시그널
                signals = context.get_output(f"_input_{node_id}", "entry_signal") or []
            
            # values 형식 지원: [{symbol, exchange, time_series: [{date, ..., signal}, ...]}, ...] → 플랫 배열로 변환
            values = context.get_output(f"_input_{node_id}", "values")
            if values and isinstance(values, list):
                # values에서 signal 필드가 있는 엔트리 추출
                extracted_signals = self._extract_signals_from_values(values, signal_field, side_field)
                if extracted_signals:
                    signals = extracted_signals
            
            # 설정
            initial_capital = config.get("initial_capital", 10000)
            commission_rate = config.get("commission_rate", 0.001)
            slippage = config.get("slippage", 0.0005)
            allow_short = config.get("allow_short", False)
            
            context.log(
                "info", 
                f"Running backtest: capital=${initial_capital}, commission={commission_rate*100}%", 
                node_id
            )
            
            # 시뮬레이션 실행
            result = self._run_simulation(
                ohlcv_data=ohlcv_data,
                signals=signals,
                initial_capital=initial_capital,
                commission_rate=commission_rate,
                slippage=slippage,
                allow_short=allow_short,
            )
            
            # 성과 지표 계산
            metrics = self._calculate_metrics(result["equity_curve"], initial_capital)
            
            context.log(
                "info", 
                f"Backtest complete: return={metrics['total_return']:.2f}%, trades={len(result['trades'])}", 
                node_id
            )
            
            # values 생성: equity_curve를 종목별 그룹화 형식으로도 제공
            backtest_values = []
            if result["equity_curve"]:
                # 포트폴리오 전체 time_series
                backtest_values.append({
                    "symbol": "_portfolio",
                    "exchange": "_portfolio",
                    "time_series": result["equity_curve"],
                })
                
                # 각 종목별 trade 정보를 values에 추가
                symbol_trades = {}
                for trade in result["trades"]:
                    symbol = trade.get("symbol", "_unknown")
                    if symbol not in symbol_trades:
                        symbol_trades[symbol] = []
                    symbol_trades[symbol].append({
                        "date": trade.get("date"),
                        "price": trade.get("price"),
                        "signal": trade.get("action"),
                        "qty": trade.get("qty"),
                    })
                
                for symbol, trades in symbol_trades.items():
                    backtest_values.append({
                        "symbol": symbol,
                        "exchange": "UNKNOWN",  # trade에서 exchange 정보가 없으면 UNKNOWN
                        "time_series": trades,
                    })
            
            return {
                "equity_curve": result["equity_curve"],
                "trades": result["trades"],
                "signals": signals if isinstance(signals, list) else [],  # 입력 signals 전달 (DisplayNode용)
                "values": backtest_values,  # 종목별 그룹화 형식: [{symbol, exchange, time_series: [...]}, ...]
                "metrics": metrics,
                "summary": {
                    **metrics,
                    "initial_capital": initial_capital,
                    "final_value": result["equity_curve"][-1]["value"] if result["equity_curve"] else initial_capital,
                    "trade_count": len(result["trades"]),
                },
            }
        finally:
            # 리소스 반환
            await context.release_resources_after_task(
                task_type="BacktestEngineNode",
                weight=3.0,
            )

    def _convert_flat_to_symbol_dict(
        self,
        flat_data: Any,
        symbol_field: str = "symbol",
        date_field: str = "date",
        close_field: str = "close",
    ) -> Dict[str, List[Dict]]:
        """
        플랫 배열을 종목별 딕셔너리로 변환
        
        입력: [{symbol: "AAPL", date: "20260101", close: 150, ...}, ...]
        출력: {"AAPL": [{date: "20260101", close: 150, ...}, ...]}
        """
        if not flat_data:
            return {}
        
        if not isinstance(flat_data, list):
            return {}
        
        result: Dict[str, List[Dict]] = {}
        
        for item in flat_data:
            if not isinstance(item, dict):
                continue
            
            symbol = item.get(symbol_field, "")
            if not symbol:
                continue
            
            if symbol not in result:
                result[symbol] = []
            
            # 필드 매핑 적용 (표준 필드명으로 변환)
            normalized = {
                "date": item.get(date_field, ""),
                "close": item.get(close_field, 0),
                "open": item.get("open", item.get(close_field, 0)),
                "high": item.get("high", item.get(close_field, 0)),
                "low": item.get("low", item.get(close_field, 0)),
                "volume": item.get("volume", 0),
            }
            result[symbol].append(normalized)
        
        # 날짜순 정렬
        for symbol in result:
            result[symbol].sort(key=lambda x: x.get("date", ""))
        
        return result

    def _extract_signals_from_values(
        self,
        values: List[Dict],
        signal_field: str = "signal",
        side_field: str = "side",
    ) -> List[Dict]:
        """
        values 형식에서 signal 필드가 있는 엔트리를 추출하여 플랫 배열로 변환
        
        입력: [{symbol: "AAPL", exchange: "NASDAQ", time_series: [{date, close, rsi, signal: "buy", side: "long"}, ...]}, ...]
        출력: [{date, symbol: "AAPL", signal: "buy", side: "long", action: "buy", price}, ...]
        """
        signals = []
        
        for item in values:
            if not isinstance(item, dict):
                continue
            
            symbol = item.get("symbol", "")
            time_series = item.get("time_series", [])
            
            if not isinstance(time_series, list):
                continue
            
            for bar in time_series:
                if not isinstance(bar, dict):
                    continue
                
                signal = bar.get(signal_field)
                side = bar.get(side_field, "long")  # 기본값: long
                if signal and signal in ("buy", "sell"):
                    signals.append({
                        "date": bar.get("date", ""),
                        "symbol": symbol,
                        "signal": signal,
                        "side": side,
                        "action": signal,
                        "price": bar.get("close", bar.get("price", 0)),
                    })
        
        # 날짜순 정렬
        signals.sort(key=lambda x: x.get("date", ""))
        return signals

    def _run_simulation(
        self,
        ohlcv_data: Dict[str, List[Dict]],
        signals: List[Dict],
        initial_capital: float,
        commission_rate: float,
        slippage: float,
        allow_short: bool = False,
    ) -> Dict[str, Any]:
        """백테스트 시뮬레이션 실행 (양방향 지원)"""
        
        equity_curve = []
        trades = []
        
        cash = initial_capital
        # 양방향 포지션 관리: {symbol: {long_qty, long_avg, short_qty, short_avg}}
        positions = {}
        
        # 모든 날짜 수집 (첫 번째 종목 기준)
        if not ohlcv_data:
            return {"equity_curve": [], "trades": []}
        
        first_symbol = list(ohlcv_data.keys())[0]
        dates = [bar["date"] for bar in ohlcv_data.get(first_symbol, [])]
        
        # 시그널을 날짜별로 인덱싱
        signal_by_date = {}
        if isinstance(signals, list):
            for sig in signals:
                date = sig.get("date", "")
                if date not in signal_by_date:
                    signal_by_date[date] = []
                signal_by_date[date].append(sig)
        
        # ========================================
        # Buy & Hold 전략: signals가 없거나 빈 리스트면 첫날 전종목 매수
        # ========================================
        use_buy_and_hold = (
            not signals or 
            not isinstance(signals, list) or 
            len(signals) == 0
        )
        buy_and_hold_executed = False
        
        # 날짜별 시뮬레이션
        for date in dates:
            # 현재가 조회
            prices = {}
            for symbol, bars in ohlcv_data.items():
                for bar in bars:
                    if bar["date"] == date:
                        prices[symbol] = bar["close"]
                        break
            
            # ========================================
            # Buy & Hold: 첫날 전종목 균등 매수
            # ========================================
            if use_buy_and_hold and not buy_and_hold_executed and prices:
                symbols = list(prices.keys())
                per_symbol = initial_capital / len(symbols)
                
                for symbol in symbols:
                    price = prices.get(symbol, 0)
                    if price > 0:
                        qty = per_symbol / (price * (1 + slippage))
                        cost = qty * price * (1 + commission_rate)
                        
                        cash -= cost
                        positions[symbol] = {
                            "long_qty": qty, "long_avg": price,
                            "short_qty": 0, "short_avg": 0,
                        }
                        
                        trades.append({
                            "date": date,
                            "symbol": symbol,
                            "action": "buy",
                            "side": "long",
                            "price": price,
                            "qty": qty,
                            "cost": cost,
                            "note": "buy_and_hold",
                        })
                
                buy_and_hold_executed = True
            
            # 시그널 처리 (Buy & Hold가 아닐 때)
            if not use_buy_and_hold:
                day_signals = signal_by_date.get(date, [])
                for sig in day_signals:
                    symbol = sig.get("symbol", "")
                    action = sig.get("signal", sig.get("action", "hold"))
                    side = sig.get("side", "long")
                    price = prices.get(symbol, 0)
                    
                    # 포지션 초기화
                    if symbol not in positions:
                        positions[symbol] = {
                            "long_qty": 0, "long_avg": 0,
                            "short_qty": 0, "short_avg": 0,
                        }
                    pos = positions[symbol]
                    
                    if action == "buy" and price > 0:
                        if side == "long":
                            # 롱 매수: cash → long_qty 증가
                            if cash > 0:
                                amount = cash * 0.1
                                qty = amount / (price * (1 + slippage))
                                cost = qty * price * (1 + commission_rate)
                                
                                if cost <= cash:
                                    cash -= cost
                                    old_qty = pos["long_qty"]
                                    old_avg = pos["long_avg"]
                                    new_qty = old_qty + qty
                                    new_avg = (old_qty * old_avg + qty * price) / new_qty if new_qty > 0 else price
                                    
                                    pos["long_qty"] = new_qty
                                    pos["long_avg"] = new_avg
                                    
                                    trades.append({
                                        "date": date,
                                        "symbol": symbol,
                                        "action": "buy",
                                        "side": "long",
                                        "price": price,
                                        "qty": qty,
                                        "cost": cost,
                                    })
                        
                        elif side == "short" and allow_short:
                            # 숗 커버: short_qty 감소 → cash (손익 정산)
                            if pos["short_qty"] > 0:
                                qty = pos["short_qty"]
                                # 숗 청산: (진입가 - 현재가) * 수량
                                pnl = (pos["short_avg"] - price) * qty
                                proceeds = qty * pos["short_avg"] + pnl - (qty * price * commission_rate)
                                
                                cash += proceeds
                                pos["short_qty"] = 0
                                pos["short_avg"] = 0
                                
                                trades.append({
                                    "date": date,
                                    "symbol": symbol,
                                    "action": "cover",
                                    "side": "short",
                                    "price": price,
                                    "qty": qty,
                                    "proceeds": proceeds,
                                    "pnl": pnl,
                                })
                    
                    elif action == "sell" and price > 0:
                        if side == "long":
                            # 롱 청산: long_qty 감소 → cash (손익 정산)
                            if pos["long_qty"] > 0:
                                qty = pos["long_qty"]
                                proceeds = qty * price * (1 - commission_rate)
                                pnl = proceeds - qty * pos["long_avg"]
                                
                                cash += proceeds
                                pos["long_qty"] = 0
                                pos["long_avg"] = 0
                                
                                trades.append({
                                    "date": date,
                                    "symbol": symbol,
                                    "action": "sell",
                                    "side": "long",
                                    "price": price,
                                    "qty": qty,
                                    "proceeds": proceeds,
                                    "pnl": pnl,
                                })
                        
                        elif side == "short" and allow_short:
                            # 숗 진입: cash → short_qty 증가
                            if cash > 0:
                                amount = cash * 0.1
                                qty = amount / (price * (1 + slippage))
                                # 숗 진입 시 증거금 차감 (단순화: 가격만큼 예치)
                                margin = qty * price * (1 + commission_rate)
                                
                                if margin <= cash:
                                    cash -= margin
                                    old_qty = pos["short_qty"]
                                    old_avg = pos["short_avg"]
                                    new_qty = old_qty + qty
                                    new_avg = (old_qty * old_avg + qty * price) / new_qty if new_qty > 0 else price
                                    
                                    pos["short_qty"] = new_qty
                                    pos["short_avg"] = new_avg
                                    
                                    trades.append({
                                        "date": date,
                                        "symbol": symbol,
                                        "action": "short",
                                        "side": "short",
                                        "price": price,
                                        "qty": qty,
                                        "margin": margin,
                                    })
            
            # 포트폴리오 가치 계산 (양방향)
            portfolio_value = cash
            for symbol, pos in positions.items():
                price = prices.get(symbol, 0)
                if pos.get("long_qty", 0) > 0:
                    portfolio_value += pos["long_qty"] * price
                if pos.get("short_qty", 0) > 0:
                    # 숗 포지션 가치: 증거금 + 미실현 손익
                    short_pnl = (pos["short_avg"] - price) * pos["short_qty"]
                    portfolio_value += pos["short_qty"] * pos["short_avg"] + short_pnl
            
            equity_curve.append({
                "date": date,
                "value": round(portfolio_value, 2),
                "cash": round(cash, 2),
            })
        
        return {"equity_curve": equity_curve, "trades": trades}

    def _calculate_metrics(
        self,
        equity_curve: List[Dict],
        initial_capital: float,
    ) -> Dict[str, Any]:
        """성과 지표 계산"""
        
        if not equity_curve:
            return {
                "total_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "win_rate": 0,
            }
        
        values = [e["value"] for e in equity_curve]
        final_value = values[-1]
        
        # 총 수익률
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        # 최대 낙폭 (MDD)
        peak = values[0]
        max_dd = 0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # 일간 수익률
        daily_returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                daily_returns.append((values[i] - values[i-1]) / values[i-1])
        
        # 샤프 비율 (연환산, 무위험수익률 0 가정)
        import math
        if daily_returns:
            avg_return = sum(daily_returns) / len(daily_returns)
            std_return = math.sqrt(sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns))
            sharpe = (avg_return / std_return) * math.sqrt(252) if std_return > 0 else 0
        else:
            sharpe = 0
        
        return {
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "final_value": round(final_value, 2),
        }


class PortfolioNodeExecutor(NodeExecutorBase):
    """
    PortfolioNode executor - 포트폴리오 관리 엔진
    
    백테스트 모드:
    - 여러 전략 결과(equity_curve) 합산
    - 리밸런싱 시뮬레이션
    - 통합 성과 지표 계산
    
    실거래 모드:
    - 실시간 자본 배분 관리
    - 리밸런싱 신호 생성
    
    입력:
    - strategy_results: 전략별 equity_curve (BacktestEngineNode 또는 PortfolioNode 출력)
    - account_state: 실시간 계좌 상태 (실거래용, 선택적)
    
    출력:
    - combined_equity: 통합 포트폴리오 equity curve
    - combined_metrics: 통합 성과 지표
    - allocation_weights: 현재 배분 비중
    - rebalance_signal: 리밸런싱 필요 여부
    - rebalance_orders: 리밸런싱 주문 목록 (실거래용)
    - allocated_capital: 하위 전략/포트폴리오에 배분할 자본
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """포트폴리오 실행"""
        
        # 설정 읽기
        total_capital = config.get("total_capital", 100000)
        allocation_method = config.get("allocation_method", "equal")
        custom_allocations = config.get("custom_allocations", {})
        rebalance_rule = config.get("rebalance_rule", "none")
        rebalance_frequency = config.get("rebalance_frequency")
        drift_threshold = config.get("drift_threshold", 5.0)
        capital_sharing = config.get("capital_sharing", True)
        reserve_percent = config.get("reserve_percent", 0.0)
        
        # 상위 포트폴리오에서 자본 배분을 받았는지 확인
        allocated_from_parent = context.get_output(f"_input_{node_id}", "allocated_capital")
        if allocated_from_parent:
            # 상위에서 배분받은 자본 사용 (total_capital 설정 무시)
            parent_allocation = allocated_from_parent.get(node_id, 0)
            if parent_allocation > 0:
                total_capital = parent_allocation
                context.log(
                    "info",
                    f"Using allocated capital from parent: ${total_capital:,.0f}",
                    node_id
                )
        
        # 전략 결과 수집 (여러 입력 연결)
        strategy_results = self._collect_strategy_results(node_id, context)
        
        if not strategy_results:
            context.log("warning", "No strategy results received", node_id)
            return self._empty_result(total_capital)
        
        context.log(
            "info",
            f"Portfolio combining {len(strategy_results)} strategies, "
            f"capital=${total_capital:,.0f}, method={allocation_method}",
            node_id
        )
        
        # 자본 배분 계산
        reserve_amount = total_capital * (reserve_percent / 100)
        investable_capital = total_capital - reserve_amount
        
        allocation_weights = self._calculate_allocations(
            strategy_results=strategy_results,
            method=allocation_method,
            custom_allocations=custom_allocations,
        )
        
        # 하위 전략에 배분할 자본 계산
        allocated_capital = {
            strategy_id: investable_capital * weight
            for strategy_id, weight in allocation_weights.items()
        }
        
        # 포트폴리오 합산 (백테스트 모드)
        combined_equity = self._combine_equity_curves(
            strategy_results=strategy_results,
            allocation_weights=allocation_weights,
            total_capital=investable_capital,
            capital_sharing=capital_sharing,
        )
        
        # 리밸런싱 체크
        rebalance_signal = False
        rebalance_orders = []
        
        if rebalance_rule != "none" and combined_equity:
            rebalance_signal, rebalance_info = self._check_rebalancing(
                strategy_results=strategy_results,
                target_weights=allocation_weights,
                rule=rebalance_rule,
                frequency=rebalance_frequency,
                drift_threshold=drift_threshold,
                combined_equity=combined_equity,
            )
            
            if rebalance_signal:
                context.log("info", f"Rebalancing triggered: {rebalance_info}", node_id)
                # 리밸런싱 시뮬레이션 (백테스트) 또는 주문 생성 (실거래)
                combined_equity = self._apply_rebalancing(
                    combined_equity=combined_equity,
                    target_weights=allocation_weights,
                    rebalance_info=rebalance_info,
                )
        
        # 성과 지표 계산
        combined_metrics = self._calculate_portfolio_metrics(
            equity_curve=combined_equity,
            initial_capital=total_capital,
            strategy_results=strategy_results,
        )
        
        context.log(
            "info",
            f"Portfolio result: return={combined_metrics.get('total_return', 0):.2f}%, "
            f"MDD={combined_metrics.get('max_drawdown', 0):.2f}%",
            node_id
        )
        
        return {
            "combined_equity": combined_equity,
            "combined_metrics": combined_metrics,
            "allocation_weights": allocation_weights,
            "rebalance_signal": rebalance_signal,
            "rebalance_orders": rebalance_orders,
            "allocated_capital": allocated_capital,
        }

    def _collect_strategy_results(
        self,
        node_id: str,
        context: ExecutionContext,
    ) -> Dict[str, Dict[str, Any]]:
        """여러 입력에서 전략 결과 수집"""
        results = {}
        
        # strategy_results 입력에서 수집
        strategy_data = context.get_output(f"_input_{node_id}", "strategy_results")
        if strategy_data:
            if isinstance(strategy_data, dict):
                results.update(strategy_data)
            elif isinstance(strategy_data, list):
                for i, item in enumerate(strategy_data):
                    if isinstance(item, dict):
                        strategy_id = item.get("strategy_id", f"strategy_{i}")
                        results[strategy_id] = item
        
        # 개별 equity_curve 연결도 확인
        for key in context._outputs.keys():
            if key.endswith(".equity_curve") or key.endswith(".combined_equity"):
                source_node = key.split(".")[0]
                if source_node != node_id:
                    equity_data = context.get_output(key.split(".")[0], key.split(".")[1])
                    if equity_data and source_node not in results:
                        results[source_node] = {"equity_curve": equity_data}
        
        return results

    def _calculate_allocations(
        self,
        strategy_results: Dict[str, Dict],
        method: str,
        custom_allocations: Dict[str, float],
    ) -> Dict[str, float]:
        """자본 배분 비율 계산"""
        strategy_ids = list(strategy_results.keys())
        
        if not strategy_ids:
            return {}
        
        if method == "equal":
            weight = 1.0 / len(strategy_ids)
            return {sid: weight for sid in strategy_ids}
        
        elif method == "custom":
            # 커스텀 배분 (합계가 1.0이 되도록 정규화)
            total = sum(custom_allocations.get(sid, 0) for sid in strategy_ids)
            if total > 0:
                return {
                    sid: custom_allocations.get(sid, 0) / total
                    for sid in strategy_ids
                }
            else:
                # 배분 설정이 없으면 균등 배분
                weight = 1.0 / len(strategy_ids)
                return {sid: weight for sid in strategy_ids}
        
        elif method == "risk_parity":
            # 리스크 패리티: 변동성 역비례 배분 (간단 버전)
            volatilities = {}
            for sid, data in strategy_results.items():
                equity_curve = data.get("equity_curve", [])
                vol = self._calculate_volatility(equity_curve)
                volatilities[sid] = vol if vol > 0 else 0.01
            
            inv_vol_sum = sum(1/v for v in volatilities.values())
            return {
                sid: (1/vol) / inv_vol_sum
                for sid, vol in volatilities.items()
            }
        
        elif method == "momentum":
            # 모멘텀 기반: 최근 수익률 비례 배분
            returns = {}
            for sid, data in strategy_results.items():
                equity_curve = data.get("equity_curve", [])
                ret = self._calculate_recent_return(equity_curve)
                returns[sid] = max(ret, 0.001)  # 최소값 설정
            
            total_return = sum(returns.values())
            return {
                sid: ret / total_return
                for sid, ret in returns.items()
            }
        
        # 기본: 균등 배분
        weight = 1.0 / len(strategy_ids)
        return {sid: weight for sid in strategy_ids}

    def _combine_equity_curves(
        self,
        strategy_results: Dict[str, Dict],
        allocation_weights: Dict[str, float],
        total_capital: float,
        capital_sharing: bool,
    ) -> List[Dict]:
        """전략별 equity curve를 합산하여 통합 포트폴리오 생성"""
        
        if not strategy_results:
            return []
        
        # 모든 날짜 수집
        all_dates = set()
        for data in strategy_results.values():
            equity_curve = data.get("equity_curve", [])
            for point in equity_curve:
                if "date" in point:
                    all_dates.add(point["date"])
        
        if not all_dates:
            return []
        
        sorted_dates = sorted(all_dates)
        
        # 전략별 equity를 날짜별로 인덱싱
        strategy_equity_by_date: Dict[str, Dict[str, float]] = {}
        for sid, data in strategy_results.items():
            equity_curve = data.get("equity_curve", [])
            strategy_equity_by_date[sid] = {
                point["date"]: point.get("value", 0)
                for point in equity_curve
                if "date" in point
            }
        
        # 통합 equity curve 생성
        combined = []
        
        for date in sorted_dates:
            portfolio_value = 0
            
            for sid, weight in allocation_weights.items():
                allocated = total_capital * weight
                
                equity_by_date = strategy_equity_by_date.get(sid, {})
                current_value = equity_by_date.get(date)
                
                if current_value is not None:
                    # 전략의 수익률을 배분 자본에 적용
                    strategy_equity = list(strategy_equity_by_date.get(sid, {}).values())
                    if strategy_equity:
                        initial = strategy_equity[0] if strategy_equity else allocated
                        if initial > 0:
                            return_rate = current_value / initial
                            portfolio_value += allocated * return_rate
                        else:
                            portfolio_value += allocated
                    else:
                        portfolio_value += allocated
                else:
                    # 해당 날짜 데이터 없으면 배분 자본 유지
                    portfolio_value += allocated
            
            combined.append({
                "date": date,
                "value": round(portfolio_value, 2),
            })
        
        return combined

    def _check_rebalancing(
        self,
        strategy_results: Dict[str, Dict],
        target_weights: Dict[str, float],
        rule: str,
        frequency: Optional[str],
        drift_threshold: float,
        combined_equity: List[Dict],
    ) -> tuple[bool, Dict[str, Any]]:
        """리밸런싱 필요 여부 체크"""
        
        if not combined_equity:
            return False, {}
        
        # 현재 비중 계산 (마지막 날짜 기준)
        current_weights = self._calculate_current_weights(strategy_results)
        
        rebalance_info = {
            "target_weights": target_weights,
            "current_weights": current_weights,
            "drift": {},
        }
        
        # 드리프트 체크
        if rule in ("drift", "both"):
            for sid, target in target_weights.items():
                current = current_weights.get(sid, 0)
                if target > 0:
                    drift_pct = abs(current - target) / target * 100
                    rebalance_info["drift"][sid] = drift_pct
                    
                    if drift_pct > drift_threshold:
                        rebalance_info["trigger"] = "drift"
                        rebalance_info["trigger_strategy"] = sid
                        return True, rebalance_info
        
        # 주기적 체크 (백테스트에서는 날짜 기반)
        if rule in ("periodic", "both") and frequency:
            # TODO: 날짜 기반 주기적 리밸런싱 체크
            # 실제 구현 시 combined_equity의 날짜와 frequency 비교
            pass
        
        return False, rebalance_info

    def _apply_rebalancing(
        self,
        combined_equity: List[Dict],
        target_weights: Dict[str, float],
        rebalance_info: Dict[str, Any],
    ) -> List[Dict]:
        """리밸런싱 시뮬레이션 적용"""
        # 현재는 단순히 equity curve 반환
        # 실제 구현 시 리밸런싱 비용 등 반영
        return combined_equity

    def _calculate_current_weights(
        self,
        strategy_results: Dict[str, Dict],
    ) -> Dict[str, float]:
        """현재 비중 계산"""
        total_value = 0
        current_values = {}
        
        for sid, data in strategy_results.items():
            equity_curve = data.get("equity_curve", [])
            if equity_curve:
                current_value = equity_curve[-1].get("value", 0)
                current_values[sid] = current_value
                total_value += current_value
        
        if total_value > 0:
            return {
                sid: val / total_value
                for sid, val in current_values.items()
            }
        
        return {sid: 0 for sid in strategy_results}

    def _calculate_volatility(self, equity_curve: List[Dict]) -> float:
        """변동성(표준편차) 계산"""
        if len(equity_curve) < 2:
            return 0.01
        
        values = [p.get("value", 0) for p in equity_curve]
        returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                returns.append((values[i] - values[i-1]) / values[i-1])
        
        if not returns:
            return 0.01
        
        import math
        avg = sum(returns) / len(returns)
        variance = sum((r - avg) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance)

    def _calculate_recent_return(
        self,
        equity_curve: List[Dict],
        lookback: int = 20,
    ) -> float:
        """최근 수익률 계산"""
        if len(equity_curve) < 2:
            return 0.0
        
        values = [p.get("value", 0) for p in equity_curve]
        start_idx = max(0, len(values) - lookback - 1)
        
        if values[start_idx] > 0:
            return (values[-1] - values[start_idx]) / values[start_idx]
        return 0.0

    def _calculate_portfolio_metrics(
        self,
        equity_curve: List[Dict],
        initial_capital: float,
        strategy_results: Dict[str, Dict],
    ) -> Dict[str, Any]:
        """포트폴리오 성과 지표 계산"""
        
        if not equity_curve:
            return {
                "total_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "strategy_count": len(strategy_results),
            }
        
        values = [e.get("value", 0) for e in equity_curve]
        final_value = values[-1] if values else initial_capital
        
        # 총 수익률
        total_return = (final_value - initial_capital) / initial_capital * 100 if initial_capital > 0 else 0
        
        # 최대 낙폭
        peak = values[0] if values else initial_capital
        max_dd = 0
        for v in values:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak * 100
                if dd > max_dd:
                    max_dd = dd
        
        # 샤프 비율
        import math
        daily_returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                daily_returns.append((values[i] - values[i-1]) / values[i-1])
        
        if daily_returns:
            avg_return = sum(daily_returns) / len(daily_returns)
            std_return = math.sqrt(sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns))
            sharpe = (avg_return / std_return) * math.sqrt(252) if std_return > 0 else 0
        else:
            sharpe = 0
        
        return {
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "final_value": round(final_value, 2),
            "initial_capital": initial_capital,
            "strategy_count": len(strategy_results),
        }

    def _empty_result(self, total_capital: float) -> Dict[str, Any]:
        """빈 결과 반환"""
        return {
            "combined_equity": [],
            "combined_metrics": {
                "total_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "final_value": total_capital,
                "initial_capital": total_capital,
                "strategy_count": 0,
            },
            "allocation_weights": {},
            "rebalance_signal": False,
            "rebalance_orders": [],
            "allocated_capital": {},
        }


class BenchmarkCompareNodeExecutor(NodeExecutorBase):
    """
    BenchmarkCompareNode executor - 벤치마크 비교 분석
    
    여러 백테스트 결과(equity_curve)를 비교 분석합니다.
    전략 vs 전략, 전략 vs Buy&Hold 등 다양한 비교를 지원합니다.
    
    입력:
    - strategies: BacktestEngineNode 출력 목록 (equity_curve, metrics 포함)
    
    출력:
    - combined_curve: 통합 차트 데이터 (날짜별 모든 전략 값)
    - comparison_metrics: 전략별 비교 지표 (return, sharpe, mdd, calmar)
    - ranking: ranking_metric 기준 순위
    - strategies_meta: 전략 메타 정보 (index, id, label)
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """벤치마크 비교 실행"""
        
        # 설정 읽기
        strategies_input = config.get("strategies", [])
        ranking_metric = config.get("ranking_metric", "sharpe")
        
        # 전략 결과 파싱
        parsed = self._parse_strategies(strategies_input, context, node_id)
        
        if not parsed["strategies"]:
            context.log("warning", "No strategy results to compare", node_id)
            return {
                "combined_curve": [],
                "comparison_metrics": [],
                "ranking": [],
                "strategies_meta": [],
            }
        
        context.log(
            "info",
            f"Comparing {len(parsed['strategies'])} strategies, ranking by {ranking_metric}",
            node_id
        )
        
        # 날짜 정렬 및 통합 차트 데이터 생성
        combined_curve = self._combine_curves(parsed["strategies"], parsed["meta"])
        
        # 비교 지표 계산
        comparison_metrics = self._calculate_comparison_metrics(parsed["strategies"], parsed["meta"])
        
        # 순위 결정
        ranking = self._rank_strategies(comparison_metrics, ranking_metric)
        
        return {
            "combined_curve": combined_curve,
            "comparison_metrics": comparison_metrics,
            "ranking": ranking,
            "strategies_meta": parsed["meta"],
        }

    def _parse_strategies(
        self,
        strategies_input: Any,
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        strategies 입력에서 equity_curve와 메타 정보 추출
        
        지원 형식:
        1. BacktestEngineNode 전체 출력: {equity_curve: [...], metrics: {...}, strategy_name: "..."}
        2. equity_curve 직접: [{date, value}, ...]
        3. 바인딩 배열: [{{ nodes.bt1 }}, {{ nodes.bt2 }}]
        4. 딕셔너리 내 바인딩: [{strategy_name: "...", equity_curve: "{{ nodes.bt1.equity_curve }}"}]
        """
        from programgarden_core.expression import ExpressionEvaluator
        
        result = {
            "strategies": [],  # [{equity_curve: [...], metrics: {...}}, ...]
            "meta": [],  # [{index, id, label}, ...]
        }
        
        if not strategies_input:
            return result
        
        # 표현식 평가기 준비
        expr_context = context.get_expression_context()
        evaluator = ExpressionEvaluator(expr_context)
        
        def evaluate_recursive(value: Any) -> Any:
            """딕셔너리/리스트 내부 표현식을 재귀적으로 평가"""
            if isinstance(value, str) and "{{" in value:
                try:
                    return evaluator.evaluate(value)
                except Exception as e:
                    context.log("warning", f"Expression evaluation failed: {value} - {e}", node_id)
                    return value
            elif isinstance(value, dict):
                return {k: evaluate_recursive(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [evaluate_recursive(v) for v in value]
            return value
        
        # 단일 객체를 배열로 변환
        if not isinstance(strategies_input, list):
            strategies_input = [strategies_input]
        
        for idx, item in enumerate(strategies_input):
            if not item:
                continue
            
            # 딕셔너리 내부의 표현식을 먼저 평가 (equity_curve: "{{ }}" 등)
            if isinstance(item, dict):
                item = evaluate_recursive(item)
            
            strategy_data = {}
            meta = {
                "index": idx,
                "id": f"strategy_{idx}",
                "label": f"Strategy {idx + 1}",
            }
            
            # BacktestEngineNode 전체 출력인 경우
            if isinstance(item, dict):
                if "equity_curve" in item:
                    strategy_data["equity_curve"] = item["equity_curve"]
                    strategy_data["metrics"] = item.get("metrics", item.get("summary", {}))
                    
                    # label 결정
                    if item.get("strategy_name"):
                        meta["label"] = item["strategy_name"]
                    
                    # id 결정 (바인딩 표현식에서 노드 ID 추출 시도)
                    if item.get("_source_node_id"):
                        meta["id"] = item["_source_node_id"]
                
                # equity_curve가 직접 전달된 경우 (배열 형식)
                elif isinstance(item.get("date"), str) or (
                    isinstance(item, list) and item and isinstance(item[0], dict) and "date" in item[0]
                ):
                    # 단일 포인트인 경우 배열로 변환
                    if "date" in item:
                        strategy_data["equity_curve"] = [item]
                    else:
                        strategy_data["equity_curve"] = item
                    strategy_data["metrics"] = {}
                
                # values 형식인 경우 (time_series 포함)
                elif "time_series" in item:
                    ts = item.get("time_series", [])
                    # time_series에서 value/equity 필드가 있는 경우 equity_curve로 변환
                    equity_curve = []
                    for point in ts:
                        if isinstance(point, dict):
                            date = point.get("date", "")
                            value = point.get("value", point.get("equity", point.get("close", 0)))
                            if date and value:
                                equity_curve.append({"date": date, "value": value})
                    
                    if equity_curve:
                        strategy_data["equity_curve"] = equity_curve
                        strategy_data["metrics"] = {}
                        
                        if item.get("symbol"):
                            meta["label"] = f"{item['symbol']} Strategy"
                            meta["id"] = item["symbol"]
            
            # 배열이 직접 전달된 경우 (equity_curve 배열)
            elif isinstance(item, list) and item and isinstance(item[0], dict):
                strategy_data["equity_curve"] = item
                strategy_data["metrics"] = {}
            
            if strategy_data.get("equity_curve"):
                result["strategies"].append(strategy_data)
                result["meta"].append(meta)
        
        return result

    def _combine_curves(
        self,
        strategies: List[Dict],
        meta: List[Dict],
    ) -> List[Dict]:
        """
        여러 equity_curve를 날짜별로 통합
        
        출력: [{date: "20260101", values: [10500, 10200, 10100]}, ...]
        """
        if not strategies:
            return []
        
        # 모든 날짜 수집 및 정렬
        all_dates = set()
        for s in strategies:
            for point in s.get("equity_curve", []):
                all_dates.add(point.get("date", ""))
        
        all_dates = sorted(all_dates)
        
        # 날짜별 값 수집
        combined = []
        for date in all_dates:
            if not date:
                continue
            
            values = []
            for s in strategies:
                # 해당 날짜의 값 찾기
                value = None
                for point in s.get("equity_curve", []):
                    if point.get("date") == date:
                        value = point.get("value", 0)
                        break
                
                # 값이 없으면 이전 값 사용 (forward fill)
                if value is None:
                    # 해당 날짜 이전의 가장 최근 값 찾기
                    for point in reversed(s.get("equity_curve", [])):
                        if point.get("date", "") <= date:
                            value = point.get("value", 0)
                            break
                
                values.append(value if value is not None else 0)
            
            combined.append({
                "date": date,
                "values": values,
            })
        
        return combined

    def _calculate_comparison_metrics(
        self,
        strategies: List[Dict],
        meta: List[Dict],
    ) -> List[Dict]:
        """
        각 전략의 비교 지표 계산
        
        출력: [{index, id, label, return, sharpe, mdd, calmar}, ...]
        """
        import math
        
        result = []
        
        for idx, (strategy, m) in enumerate(zip(strategies, meta)):
            equity_curve = strategy.get("equity_curve", [])
            metrics = strategy.get("metrics", {})
            
            # 기존 metrics가 있으면 사용
            total_return = metrics.get("total_return")
            sharpe = metrics.get("sharpe_ratio")
            mdd = metrics.get("max_drawdown")
            
            # 없으면 직접 계산
            if equity_curve and len(equity_curve) >= 2:
                values = [p.get("value", 0) for p in equity_curve]
                initial = values[0] if values[0] > 0 else 1
                final = values[-1]
                
                # 총 수익률
                if total_return is None:
                    total_return = (final - initial) / initial * 100
                
                # MDD
                if mdd is None:
                    peak = values[0]
                    max_dd = 0
                    for v in values:
                        if v > peak:
                            peak = v
                        if peak > 0:
                            dd = (peak - v) / peak * 100
                            if dd > max_dd:
                                max_dd = dd
                    mdd = max_dd
                
                # Sharpe
                if sharpe is None:
                    daily_returns = []
                    for i in range(1, len(values)):
                        if values[i-1] > 0:
                            daily_returns.append((values[i] - values[i-1]) / values[i-1])
                    
                    if daily_returns:
                        avg = sum(daily_returns) / len(daily_returns)
                        std = math.sqrt(sum((r - avg) ** 2 for r in daily_returns) / len(daily_returns))
                        sharpe = (avg / std) * math.sqrt(252) if std > 0 else 0
                    else:
                        sharpe = 0
            else:
                total_return = total_return or 0
                sharpe = sharpe or 0
                mdd = mdd or 0
            
            # Calmar 계산 (연환산 수익률 / MDD)
            # 간단히 total_return / mdd로 계산
            calmar = abs(total_return / mdd) if mdd and mdd > 0 else 0
            
            result.append({
                "index": m["index"],
                "id": m["id"],
                "label": m["label"],
                "return": round(total_return, 2) if total_return else 0,
                "sharpe": round(sharpe, 2) if sharpe else 0,
                "mdd": round(mdd, 2) if mdd else 0,
                "calmar": round(calmar, 2),
            })
        
        return result

    def _rank_strategies(
        self,
        metrics: List[Dict],
        ranking_metric: str,
    ) -> List[Dict]:
        """
        ranking_metric 기준으로 순위 결정
        
        출력: [{rank, index, id, label, <metric_value>}, ...]
        """
        if not metrics:
            return []
        
        # 정렬 기준 결정 (높을수록 좋은 지표)
        # MDD는 낮을수록 좋으므로 reverse=False
        reverse = ranking_metric != "mdd"
        
        sorted_metrics = sorted(
            metrics,
            key=lambda x: x.get(ranking_metric, 0) if ranking_metric != "mdd" else -x.get(ranking_metric, 0),
            reverse=reverse
        )
        
        result = []
        for rank, m in enumerate(sorted_metrics, 1):
            result.append({
                "rank": rank,
                "index": m["index"],
                "id": m["id"],
                "label": m["label"],
                ranking_metric: m.get(ranking_metric, 0),
            })
        
        return result


class WorkflowExecutor:
    """
    Workflow execution engine

    Stateful long-running execution:
    - 24-hour continuous execution support
    - Position/balance state persistence
    - Graceful Restart support
    """

    def __init__(self):
        self.resolver = WorkflowResolver()
        self._jobs: Dict[str, "WorkflowJob"] = {}
        self._executors: Dict[str, NodeExecutorBase] = self._init_executors()

    def _init_executors(self) -> Dict[str, NodeExecutorBase]:
        """Initialize per-node-type executors"""
        return {
            "StartNode": StartNodeExecutor(),
            "ThrottleNode": ThrottleNodeExecutor(),
            "ScheduleNode": ScheduleNodeExecutor(),
            "WatchlistNode": WatchlistNodeExecutor(),
            "SymbolQueryNode": SymbolQueryNodeExecutor(),
            "SymbolFilterNode": SymbolFilterNodeExecutor(),
            "MarketUniverseNode": MarketUniverseNodeExecutor(),
            "ScreenerNode": ScreenerNodeExecutor(),
            "BrokerNode": BrokerNodeExecutor(),
            "AccountNode": AccountNodeExecutor(),  # 1회성 REST API 조회
            "RealAccountNode": RealAccountNodeExecutor(),  # 실시간 WebSocket
            "MarketDataNode": MarketDataNodeExecutor(),  # REST API 현재가 조회
            "RealMarketDataNode": RealMarketDataNodeExecutor(),
            "RealOrderEventNode": RealOrderEventNodeExecutor(),  # 실시간 주문 이벤트
            "CustomPnLNode": CustomPnLNodeExecutor(),
            "DisplayNode": DisplayNodeExecutor(),
            "ConditionNode": ConditionNodeExecutor(),
            "LogicNode": LogicNodeExecutor(),  # 조건 조합
            "PerformanceConditionNode": PerformanceConditionNodeExecutor(),  # 성과 조건
            # Backtest nodes
            "HistoricalDataNode": HistoricalDataNodeExecutor(),
            "BacktestEngineNode": BacktestEngineNodeExecutor(),
            "BenchmarkCompareNode": BenchmarkCompareNodeExecutor(),
            # Portfolio node
            "PortfolioNode": PortfolioNodeExecutor(),
        }

    def validate(self, definition: Dict[str, Any]) -> ValidationResult:
        """
        Validate workflow

        Args:
            definition: Workflow definition (JSON dict)
        """
        return self.resolver.validate(definition)

    def compile(
        self,
        definition: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None,
    ) -> tuple[Optional[ResolvedWorkflow], ValidationResult]:
        """
        Compile workflow (convert to execution objects)

        Args:
            definition: Workflow definition
            context_params: Execution context parameters
        """
        return self.resolver.resolve(definition, context_params)

    async def execute(
        self,
        definition: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        listeners: Optional[List[ExecutionListener]] = None,
        resource_limits: Optional["ResourceLimits"] = None,
    ) -> "WorkflowJob":
        """
        Execute workflow

        Args:
            definition: Workflow definition
            context_params: Runtime parameters (symbols, dry_run, etc.)
            secrets: Sensitive credentials (appkey, appsecret, etc.) - never logged
            job_id: Job ID (auto-generated if not provided)
            listeners: List of ExecutionListener instances for state callbacks
            resource_limits: Resource limits (CPU, RAM, workers). None = auto-detect
        """
        # Compile
        resolved, validation = self.compile(definition, context_params)
        if not validation.is_valid:
            raise ValueError(f"Workflow validation failed: {validation.errors}")

        # Extract workflow inputs schema for expression evaluation
        workflow_inputs = definition.get("inputs", {})
        
        # Extract workflow credentials for credential_id resolution
        workflow_credentials = definition.get("credentials", [])
        
        # === Resource Context Setup ===
        # Priority: explicit resource_limits > workflow definition > auto-detect
        resource_context = None
        try:
            from programgarden.resource import ResourceContext
            from programgarden_core.models.resource import ResourceLimits as RL
            
            # Determine limits to use
            effective_limits = resource_limits
            if effective_limits is None:
                # Check workflow definition
                workflow_limits = definition.get("resource_limits")
                if workflow_limits:
                    if isinstance(workflow_limits, dict):
                        effective_limits = RL(**workflow_limits)
                    else:
                        effective_limits = workflow_limits
            
            # Create ResourceContext (auto-detect if no limits)
            resource_context = await ResourceContext.create(
                limits=effective_limits,
                auto_detect=(effective_limits is None),
            )
            await resource_context.start()
            logger.info(f"ResourceContext initialized (limits={effective_limits is not None})")
        except ImportError:
            logger.debug("Resource management not available (psutil not installed)")
        except Exception as e:
            logger.warning(f"Failed to initialize ResourceContext: {e}")

        # Create Job
        job_id = job_id or f"job-{uuid.uuid4().hex[:8]}"
        context = ExecutionContext(
            job_id=job_id,
            workflow_id=resolved.workflow_id,
            context_params=context_params or {},
            secrets=secrets,
            workflow_inputs=workflow_inputs,
            workflow_credentials=workflow_credentials,
            resource_context=resource_context,
            # DAG 탐색용 워크플로우 구조 정보
            workflow_edges=resolved.edges,
            workflow_nodes=resolved.nodes,
        )
        
        # Set listeners (Option A: inject at creation)
        if listeners:
            context.set_listeners(listeners)

        job = WorkflowJob(
            job_id=job_id,
            workflow=resolved,
            context=context,
            executor=self,
        )

        self._jobs[job_id] = job

        # Start execution
        await job.start()

        return job

    async def execute_node(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        plugin: Optional[Callable] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute single node"""
        executor = self._executors.get(node_type)

        # 전용 executor가 없으면 GenericNodeExecutor 사용 (커뮤니티 노드 등)
        if not executor:
            executor = GenericNodeExecutor()
            context.log("debug", f"Using GenericNodeExecutor for {node_type}", node_id)

        # 모든 노드에 plugin과 fields 전달 (GenericNodeExecutor에서 처리)
        return await executor.execute(
            node_id=node_id,
            node_type=node_type,
            config=config,
            context=context,
            plugin=plugin,
            fields=fields,
        )

    def get_job(self, job_id: str) -> Optional["WorkflowJob"]:
        """Get Job"""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List["WorkflowJob"]:
        """List all Jobs"""
        return list(self._jobs.values())


class WorkflowJob:
    """
    Workflow execution instance

    Stateful: Persists position/balance state
    
    Execution modes based on workflow structure:
    - No ScheduleNode, stay_connected=False: One-shot execution
    - No ScheduleNode, stay_connected=True: Continuous until stop()
    - With ScheduleNode, stay_connected=False: Repeat on schedule, disconnect between
    - With ScheduleNode, stay_connected=True: Repeat on schedule, realtime stays alive
    """

    def __init__(
        self,
        job_id: str,
        workflow: ResolvedWorkflow,
        context: ExecutionContext,
        executor: WorkflowExecutor,
    ):
        self.job_id = job_id
        self.workflow = workflow
        self.context = context
        self.executor = executor

        # State
        self.status = "pending"
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # Statistics
        self.stats = {
            "conditions_evaluated": 0,
            "orders_placed": 0,
            "orders_filled": 0,
            "errors_count": 0,
            "flow_executions": 0,
            "realtime_updates": 0,
        }

        # Execution task
        self._task: Optional[asyncio.Task] = None
        
        # Precompute node categories for optimization
        self._has_schedule_node = self._check_has_schedule_node()
        self._stay_connected_nodes = self._find_stay_connected_nodes()

    # === Listener Management ===

    def add_listener(self, listener: ExecutionListener) -> "WorkflowJob":
        """
        Add a listener (supports chaining).
        
        Example:
            job.add_listener(listener1).add_listener(listener2)
        
        Args:
            listener: ExecutionListener implementation
        
        Returns:
            self (for chaining)
        """
        self.context.add_listener(listener)
        return self

    def remove_listener(self, listener: ExecutionListener) -> "WorkflowJob":
        """
        Remove a listener (supports chaining).
        
        Args:
            listener: Listener to remove
        
        Returns:
            self (for chaining)
        """
        self.context.remove_listener(listener)
        return self

    def _check_has_schedule_node(self) -> bool:
        """Check if workflow has any ScheduleNode"""
        for node in self.workflow.nodes.values():
            if node.node_type == "ScheduleNode":
                return True
        return False

    def _find_stay_connected_nodes(self) -> List[str]:
        """Find all nodes with stay_connected=True or persistent nodes"""
        result = []
        for node_id, node in self.workflow.nodes.items():
            # 실시간 노드 (stay_connected 설정)
            if node.node_type in ("RealAccountNode", "RealMarketDataNode", "RealOrderEventNode"):
                if node.config.get("stay_connected", True):
                    result.append(node_id)
            # 영속 노드 (백그라운드 태스크를 등록하는 노드)
            elif node.node_type == "ScheduleNode":
                if node.config.get("enabled", True):
                    result.append(node_id)
        return result

    async def start(self) -> None:
        """Start execution"""
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.context.start()
        
        # 🆕 Job 시작 알림
        await self.context.notify_job_state("running", self.stats)

        # Async execution
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        """
        Workflow execution loop
        
        Flow:
        1. Execute main flow (all nodes in topological order)
        2. Cleanup stay_connected=False nodes (flow-end cleanup)
        3. If stay_connected=True nodes exist:
           - Enter event loop
           - Process realtime updates
           - Re-execute triggered nodes
        4. Cleanup on stop
        """
        try:
            # Phase 1: Execute main flow
            await self._execute_main_flow()
            self.stats["flow_executions"] += 1
            
            # Phase 1.5: Cleanup stay_connected=False nodes
            await self.context.cleanup_flow_end_nodes()
            
            # Phase 2: Event loop if stay_connected OR schedule nodes exist
            has_event_sources = (
                bool(self._stay_connected_nodes) or 
                self._has_schedule_node or
                bool(self.context._persistent_tasks)  # Any persistent background tasks
            )
            if has_event_sources and self.context.is_running:
                logger.info(
                    f"Entering event loop "
                    f"(stay_connected: {self._stay_connected_nodes}, "
                    f"schedule: {self._has_schedule_node}, "
                    f"persistent_tasks: {len(self.context._persistent_tasks)})"
                )
                await self._event_loop()
            
            # Phase 3: Mark completed if no failures
            if not self.context.is_failed:
                self.status = "completed"
            else:
                self.status = "failed"
            
            self.completed_at = datetime.utcnow()
            
            # 🆕 Job 완료 알림
            await self.context.notify_job_state(self.status, self.stats)

        except asyncio.CancelledError:
            self.status = "cancelled"
            logger.info(f"Job {self.job_id} cancelled")
            print(f"⚠️ Job {self.job_id} cancelled")
            await self.context.notify_job_state("cancelled", self.stats)
        except Exception as e:
            self.status = "failed"
            self.stats["errors_count"] += 1
            self.context.log("error", str(e))
            logger.exception(f"Job {self.job_id} failed: {e}")
            print(f"❌ Job {self.job_id} failed: {e}")
            import traceback
            traceback.print_exc()
            await self.context.notify_job_state("failed", self.stats)
        finally:
            # Cleanup persistent nodes
            await self.context.cleanup_persistent_nodes()

    async def _execute_main_flow(self) -> None:
        """Execute all nodes in topological order with state notifications"""
        print(f"🔄 Executing main flow: {self.workflow.execution_order}")
        
        # 🆕 실행 시작 전 모든 노드 상태를 pending으로 리셋 (UI 깜빡임 효과)
        for node_id in self.workflow.execution_order:
            node = self.workflow.nodes.get(node_id)
            if node:
                await self.context.notify_node_state(
                    node_id=node_id,
                    node_type=node.node_type,
                    state=NodeState.PENDING,
                )
        
        for node_id in self.workflow.execution_order:
            if not self.context.is_running:
                break

            # Wait if paused
            while self.context.is_paused:
                await asyncio.sleep(0.1)

            node = self.workflow.nodes.get(node_id)
            if not node:
                continue

            print(f"  ▶ Executing node: {node_id} ({node.node_type})")
            
            # 🆕 노드 실행 시작 알림
            start_time = datetime.utcnow()
            await self.context.notify_node_state(
                node_id=node_id,
                node_type=node.node_type,
                state=NodeState.RUNNING,
            )

            # Prepare node config with trigger info from edges
            config = dict(node.config)
            trigger_nodes = self._find_trigger_nodes(node_id)
            if trigger_nodes:
                config["_trigger_on_update_nodes"] = trigger_nodes
            
            # 🆕 상위 노드 ID를 config에 추가 (DisplayNode 등에서 사용)
            for edge in self.workflow.edges:
                if edge.to_node_id == node_id:
                    config["_source_node_id"] = edge.from_node_id
                    break  # 첫 번째 상위 노드만 사용
            
            # Resolve expressions in config ({{ input.xxx }}, {{ nodeId.port }})
            config = self._resolve_config_expressions(config)

            # Connect inputs (get values from edges) + 🆕 엣지 알림
            for edge in self.workflow.edges:
                if edge.to_node_id == node_id:
                    # 엣지는 실행 순서만 표현, 데이터는 전체 출력을 전달
                    # get_all_outputs로 소스 노드의 모든 출력 가져오기
                    all_outputs = self.context.get_all_outputs(edge.from_node_id)
                    
                    # 단일 값 (하위 호환): 첫 번째 출력
                    single_value = self.context.get_output(edge.from_node_id, None)
                    
                    print(f"    📦 Edge: {edge.from_node_id} → {node_id} = {len(all_outputs)} outputs", flush=True)
                    
                    if all_outputs:
                        from_port = "output"
                        input_port = "input"
                        
                        # 🆕 엣지 전송 시작 알림
                        await self.context.notify_edge_state(
                            from_node_id=edge.from_node_id,
                            from_port=from_port,
                            to_node_id=node_id,
                            to_port=input_port,
                            state=EdgeState.TRANSMITTING,
                            data=all_outputs,
                        )
                        
                        # 전체 출력을 각 포트별로 저장 (DisplayNode 등에서 개별 접근 가능)
                        for port_name, port_value in all_outputs.items():
                            self.context.set_output(
                                f"_input_{node_id}",
                                port_name,
                                port_value,
                            )
                        
                        # 단일 값도 "input" 포트에 저장 (하위 호환)
                        self.context.set_output(
                            f"_input_{node_id}",
                            input_port,
                            single_value if single_value is not None else all_outputs,
                        )
                        
                        # 🆕 엣지 전송 완료 알림
                        await self.context.notify_edge_state(
                            from_node_id=edge.from_node_id,
                            from_port=from_port,
                            to_node_id=node_id,
                            to_port=input_port,
                            state=EdgeState.TRANSMITTED,
                        )

            # Execute node
            try:
                outputs = await self.executor.execute_node(
                    node_id=node_id,
                    node_type=node.node_type,
                    config=config,
                    context=self.context,
                    plugin=node.plugin,
                    fields=node.fields,
                )

                # Store outputs
                for port_name, value in outputs.items():
                    self.context.set_output(node_id, port_name, value)
                
                # 🆕 노드 완료 알림
                # stay_connected 노드는 RUNNING 상태 유지 (계속 실시간 업데이트)
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                is_stay_connected = node_id in self._stay_connected_nodes
                
                await self.context.notify_node_state(
                    node_id=node_id,
                    node_type=node.node_type,
                    state=NodeState.RUNNING if is_stay_connected else NodeState.COMPLETED,
                    outputs=outputs,
                    duration_ms=duration_ms,
                )
                
            except Exception as e:
                # 🆕 노드 실패 알림
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                await self.context.notify_node_state(
                    node_id=node_id,
                    node_type=node.node_type,
                    state=NodeState.FAILED,
                    error=str(e),
                    duration_ms=duration_ms,
                )
                self.stats["errors_count"] += 1
                self.context.log("error", f"Node {node_id} failed: {e}", node_id)
                raise

    def _find_trigger_nodes(self, source_node_id: str) -> List[str]:
        """Find nodes that should be triggered on realtime update
        
        - edge에 trigger: "on_update" 속성이 있으면 트리거
        - 소스가 RealAccountNode/RealMarketDataNode면 연결된 모든 노드 자동 트리거
        """
        trigger_nodes = []
        source_node = self.workflow.nodes.get(source_node_id)
        
        # 실시간 노드는 하위 노드를 자동 트리거
        auto_trigger_types = {"RealAccountNode", "RealMarketDataNode", "RealOrderEventNode"}
        is_realtime_source = source_node and source_node.node_type in auto_trigger_types
        
        for edge in self.workflow.edges:
            if edge.from_node_id == source_node_id:
                # 1. edge에 trigger: "on_update" 속성이 있으면 트리거
                if hasattr(edge, 'trigger') and edge.trigger == "on_update":
                    trigger_nodes.append(edge.to_node_id)
                # 2. 실시간 노드는 연결된 모든 노드 자동 트리거
                elif is_realtime_source:
                    trigger_nodes.append(edge.to_node_id)
        return trigger_nodes

    def _resolve_config_expressions(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Config 내의 {{ }} 표현식을 resolve.
        
        예: "{{ input.total_capital }}" → 100000
        
        지원 표현식:
        - {{ input.xxx }}: 워크플로우 inputs 파라미터
        - {{ nodeId.port }}: 이전 노드 출력값
        - {{ context.xxx }}: 실행 컨텍스트 값
        """
        from programgarden_core.expression import ExpressionEvaluator
        
        try:
            expr_context = self.context.get_expression_context()
            evaluator = ExpressionEvaluator(expr_context)
            return evaluator.evaluate_fields(config)
        except Exception as e:
            # 표현식 평가 실패 시 원본 반환 (graceful degradation)
            self.context.log("warning", f"Expression resolve failed: {e}")
            return config

    async def _event_loop(self) -> None:
        """
        Event loop for realtime updates
        
        Waits for events and processes them:
        - realtime_update: Re-execute triggered nodes (e.g., risk check)
        - schedule_tick: Re-execute schedule branch
        """
        logger.info("Starting event loop")
        
        while self.context.is_running and not self.context.is_failed:
            # Wait for event with timeout (allows checking is_running periodically)
            event = await self.context.wait_for_event(timeout=1.0)
            
            if event is None:
                continue
            
            # Wait if paused
            while self.context.is_paused:
                await asyncio.sleep(0.1)
            
            if event.type == "realtime_update":
                self.stats["realtime_updates"] += 1
                await self._handle_realtime_update(event)
            
            elif event.type == "order_event":
                # 주문 이벤트도 실시간 업데이트와 동일하게 처리
                self.stats["realtime_updates"] += 1
                await self._handle_realtime_update(event)
            
            elif event.type == "market_data":
                # RealMarketDataNode에서 발생하는 시세 이벤트 → DisplayNode 트리거
                try:
                    self.stats["realtime_updates"] += 1
                    await self._handle_realtime_update(event)
                except Exception as e:
                    logger.warning(f"market_data event handling error: {e}")
                
            elif event.type == "schedule_tick":
                self.stats["flow_executions"] += 1
                await self._execute_main_flow()
        
        logger.info("Event loop ended")

    async def _handle_realtime_update(self, event: WorkflowEvent) -> None:
        """
        Handle realtime update event
        
        Re-executes nodes specified in trigger_nodes and their downstream nodes.
        Follows topological order to ensure proper data flow.
        """
        from datetime import datetime
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 실시간 업데이트 이벤트 수신: trigger_nodes={event.trigger_nodes}")
        
        # trigger_nodes가 비어있으면 source_node_id에서 연결된 하위 노드 찾기
        trigger_nodes = event.trigger_nodes
        if not trigger_nodes and event.source_node_id:
            trigger_nodes = self._find_trigger_nodes(event.source_node_id)
            print(f"  → 자동 탐색된 trigger_nodes: {trigger_nodes}")
        
        if not trigger_nodes:
            print(f"  ⚠️ 트리거할 노드 없음, 스킵")
            return
        
        logger.debug(f"Realtime update from {event.source_node_id}, triggering: {trigger_nodes}")
        print(f"  → {event.source_node_id}에서 트리거: {trigger_nodes}")
        
        # 🆕 트리거된 노드들 + 하위 노드들을 모두 찾아서 실행 순서대로 정렬
        nodes_to_execute = self._find_downstream_nodes(trigger_nodes)
        print(f"  → 실행할 노드 체인: {nodes_to_execute}")
        
        for node_id in nodes_to_execute:
            if not self.context.is_running:
                break
            
            node = self.workflow.nodes.get(node_id)
            if not node:
                continue
            
            # 실시간 노드는 이미 실행 중이므로 스킵 (무한 루프 방지)
            if node.node_type in ("RealAccountNode", "RealMarketDataNode", "RealOrderEventNode"):
                continue
            
            # Re-execute the triggered node
            try:
                print(f"    ▶ Re-executing: {node_id} ({node.node_type})")
                
                # 소스 노드 ID를 config에 추가하여 최신 데이터 참조 가능하게
                config_with_source = dict(node.config)
                config_with_source["_source_node_id"] = event.source_node_id
                
                # 🆕 이벤트 데이터를 직접 전달 (context.get_all_outputs보다 최신)
                # emit_event에서 전달된 데이터를 사용하면 타이밍 문제 해결
                if event.data:
                    config_with_source["_realtime_data"] = event.data
                
                # 🆕 입력 데이터 준비 (상위 노드 출력 연결)
                for edge in self.workflow.edges:
                    if edge.to_node_id == node_id:
                        all_outputs = self.context.get_all_outputs(edge.from_node_id)
                        if all_outputs:
                            for port_name, port_value in all_outputs.items():
                                self.context.set_output(
                                    f"_input_{node_id}",
                                    port_name,
                                    port_value,
                                )
                
                # Resolve expressions in config
                config_with_source = self._resolve_config_expressions(config_with_source)
                
                outputs = await self.executor.execute_node(
                    node_id=node_id,
                    node_type=node.node_type,
                    config=config_with_source,
                    context=self.context,
                    plugin=node.plugin,
                    fields=node.fields,
                )
                
                # 🆕 ThrottleNode에서 _throttled=True 반환 시 하위 노드 실행 중단
                if outputs.get("_throttled"):
                    print(f"    ⏸️ Throttled: {node_id} - stopping downstream execution")
                    # 출력은 저장하되 하위 노드 실행은 중단
                    for port_name, value in outputs.items():
                        self.context.set_output(node_id, port_name, value)
                    break  # 체인 실행 중단
                
                for port_name, value in outputs.items():
                    self.context.set_output(node_id, port_name, value)
                
                # 🆕 노드 실행 완료 알림 (UI 업데이트용)
                await self.context.notify_node_state(
                    node_id=node_id,
                    node_type=node.node_type,
                    state=NodeState.COMPLETED,
                    outputs=outputs,
                )
                    
            except Exception as e:
                self.context.log("error", f"Error in triggered node {node_id}: {e}", node_id)
                self.stats["errors_count"] += 1
    
    def _find_downstream_nodes(self, start_nodes: List[str]) -> List[str]:
        """
        Find all downstream nodes from start_nodes in topological order.
        
        Returns nodes that need to be re-executed when realtime update occurs.
        """
        # BFS로 하위 노드 찾기
        downstream = set(start_nodes)
        queue = list(start_nodes)
        
        while queue:
            current = queue.pop(0)
            for edge in self.workflow.edges:
                if edge.from_node_id == current and edge.to_node_id not in downstream:
                    downstream.add(edge.to_node_id)
                    queue.append(edge.to_node_id)
        
        # 토폴로지 순서대로 정렬 (workflow.execution_order 기준)
        ordered = [n for n in self.workflow.execution_order if n in downstream]
        return ordered

    async def pause(self) -> None:
        """Pause execution"""
        self.status = "paused"
        self.context.pause()

    async def resume(self) -> None:
        """Resume execution"""
        self.status = "running"
        self.context.resume()

    async def stop(self) -> None:
        """Stop execution gracefully"""
        logger.info(f"Stopping job {self.job_id}")
        self.status = "stopping"
        self.context.stop()
        
        # Wait for task to finish cleanup
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Job {self.job_id} stop timeout, cancelling")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        
        # Cleanup ResourceContext
        if self.context.resource:
            try:
                await self.context.resource.stop()
                logger.debug(f"ResourceContext stopped for job {self.job_id}")
            except Exception as e:
                logger.warning(f"Failed to stop ResourceContext: {e}")
        
        self.status = "stopped"
        self.completed_at = datetime.now()
        logger.info(f"Job {self.job_id} stopped")

    async def cancel(self) -> None:
        """Cancel execution immediately"""
        self.status = "cancelled"
        self.context.stop()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Cleanup
        await self.context.cleanup_persistent_nodes()
        
        # Cleanup ResourceContext
        if self.context.resource:
            try:
                await self.context.resource.stop()
            except Exception as e:
                logger.warning(f"Failed to stop ResourceContext: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get state snapshot"""
        # 노드별 상태 및 outputs 수집
        nodes_state = {}
        for node_id in self.context._outputs.keys():
            outputs = self.context.get_all_outputs(node_id)
            nodes_state[node_id] = {
                "state": "completed",
                "outputs": outputs,
            }
        
        return {
            "job_id": self.job_id,
            "workflow_id": self.workflow.workflow_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stats": self.stats,
            "has_schedule": self._has_schedule_node,
            "stay_connected_nodes": self._stay_connected_nodes,
            "logs": self.context.get_logs(limit=50),
            "nodes": nodes_state,
        }
