"""
ProgramGarden - WorkflowExecutor

Workflow execution engine
- validate() → compile() → execute() lifecycle
- Stateful long-running execution support
- Graceful Restart support
- Event-based realtime updates
"""

from typing import Optional, Dict, Any, List, Callable, Awaitable, Set, Tuple
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
    RestartEvent,
    NotificationCategory,
    NotificationSeverity,
)
from programgarden_core.retry_executor import RetryExecutor
from programgarden_core.nodes.base import BaseMessagingNode

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

    def _inject_credentials(
        self,
        credential_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """Credential 값을 config에 주입 (공용 메서드)."""
        cred_data = context.get_workflow_credential(credential_id)

        if cred_data:
            config = config.copy()
            injected_keys = []

            for key, value in cred_data.items():
                if config.get(key) is None and value:
                    config[key] = value
                    injected_keys.append(key)

            if injected_keys:
                context.log(
                    "debug",
                    f"Credentials injected from '{credential_id}': {', '.join(injected_keys)}",
                    node_id
                )
        else:
            context.log("warning", f"Credential '{credential_id}' not found", node_id)

        return config


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


class LSClientManager:
    """Product별 LS 클라이언트 관리 (토큰 충돌 방지)
    
    해외주식과 해외선물은 서로 다른 appkey를 사용하므로
    각각 독립된 LS 인스턴스로 관리합니다.
    
    - overseas_stock: LS 인스턴스 #1
    - overseas_futures: LS 인스턴스 #2
    
    인스턴스는 프로세스 종료까지 유지됩니다 (WebSocket 연결 재활용).
    """
    _instances: Dict[str, Any] = {}  # {product: LS}
    _credentials: Dict[str, tuple] = {}  # {product: (appkey, appsecret, paper_trading)}
    
    @classmethod
    def get_or_create(
        cls,
        product: str,
        appkey: str,
        appsecret: str,
        paper_trading: bool,
        context: "ExecutionContext",
        node_id: str,
    ) -> tuple:
        """Product별 LS 인스턴스 반환 (없으면 생성 및 로그인)
        
        Returns:
            (ls_instance, success: bool, error_message: str | None)
        """
        from programgarden_finance import LS
        
        # 이미 해당 product의 인스턴스가 있고 로그인된 경우
        if product in cls._instances:
            ls = cls._instances[product]
            stored = cls._credentials.get(product)
            
            # 같은 credential이면 재사용
            if stored and stored == (appkey, appsecret, paper_trading):
                if ls.is_logged_in():
                    return ls, True, None
        
        # 새 인스턴스 생성 (싱글톤 우회)
        ls = object.__new__(LS)
        ls.__init__()
        
        # 로그인
        login_result = ls.login(
            appkey=appkey,
            appsecretkey=appsecret,
            paper_trading=paper_trading,
        )
        
        if not login_result:
            context.log("error", f"LS login failed for {product}", node_id)
            return ls, False, "Login failed"
        
        # 저장
        cls._instances[product] = ls
        cls._credentials[product] = (appkey, appsecret, paper_trading)
        
        context.log("info", f"LS logged in for {product} (paper_trading={paper_trading})", node_id)
        return ls, True, None
    
    @classmethod
    def get(cls, product: str) -> Optional[Any]:
        """저장된 인스턴스 조회 (없으면 None)"""
        return cls._instances.get(product)
    
    @classmethod
    def reset(cls) -> None:
        """모든 인스턴스 초기화 (테스트용)"""
        cls._instances.clear()
        cls._credentials.clear()


def ensure_ls_login(
    appkey: str,
    appsecret: str,
    paper_trading: bool,
    context: "ExecutionContext",
    node_id: str,
    product: str,
    caller_name: str = "",
) -> tuple:
    """
    Product별 LS증권 로그인 보장 헬퍼 함수
    
    LSClientManager를 사용하여 product별 독립 인스턴스를 관리합니다.
    overseas_stock과 overseas_futures가 동시에 실행되어도 토큰 충돌이 없습니다.
    
    Args:
        appkey: LS증권 appkey
        appsecret: LS증권 appsecret
        paper_trading: 모의투자 여부
        context: 실행 컨텍스트
        node_id: 노드 ID
        product: 상품 유형 (overseas_stock, overseas_futures)
        caller_name: 호출자 이름 (로깅용)
        
    Returns:
        (ls_instance, success: bool, error_message: str | None)
    """
    return LSClientManager.get_or_create(
        product=product,
        appkey=appkey,
        appsecret=appsecret,
        paper_trading=paper_trading,
        context=context,
        node_id=node_id,
    )


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
        **kwargs,
    ) -> Dict[str, Any]:
        from programgarden_core.registry import NodeTypeRegistry, DynamicNodeRegistry

        registry = NodeTypeRegistry()
        node_class = registry.get(node_type)

        # 동적 노드 레지스트리에서 fallback 조회
        if not node_class:
            dynamic_registry = DynamicNodeRegistry()
            node_class = dynamic_registry.get_node_class(node_type)

            if not node_class:
                # 스키마는 있지만 클래스가 주입되지 않은 경우
                if dynamic_registry.get_schema(node_type):
                    context.log(
                        "error",
                        f"동적 노드 클래스가 주입되지 않음: {node_type}. "
                        "inject_node_classes()를 먼저 호출하세요.",
                        node_id
                    )
                    return {
                        "error": f"동적 노드 클래스가 주입되지 않음: {node_type}. "
                                 "inject_node_classes()를 먼저 호출하세요."
                    }
                # 스키마도 없는 경우
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

        # dry_run 가드: Messaging/Notification 노드는 no-op 반환
        if context.is_dry_run:
            try:
                from programgarden_core.nodes.base import NodeCategory
                node_category = getattr(node_instance, "category", None)
                if node_category == NodeCategory.MESSAGING:
                    context.log(
                        "info",
                        f"[dry_run] {node_type} skipped (messaging node)",
                        node_id,
                    )
                    return {"status": "simulated", "dry_run": True}
            except Exception:
                # NodeCategory import 실패는 무시 — dry_run 가드가 동작 안 할 뿐
                pass

        # execute() 메서드 호출
        if hasattr(node_instance, "execute"):
            try:
                # resilience 설정이 있고 retry가 활성화된 노드는 RetryExecutor로 래핑
                has_resilience = (
                    hasattr(node_instance, 'resilience')
                    and hasattr(node_instance, 'is_retryable_error')
                    and node_instance.resilience.retry.enabled
                )
                if has_resilience:
                    retry_executor = RetryExecutor()
                    result = await retry_executor.execute_with_retry(
                        node=node_instance,
                        execute_fn=lambda: node_instance.execute(context),
                        context=context,
                    )
                else:
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


class SplitNodeExecutor(NodeExecutorBase):
    """
    SplitNode executor

    Splits an input array into individual items for item-based execution.
    The actual iteration logic is handled in WorkflowJob._execute_main_flow.

    This executor provides:
    - item: Current item from the array
    - index: Current index (0-based)
    - total: Total number of items

    Note: The execution engine calls this executor once per item in the array.
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        # Get array from config or input port
        input_array = config.get("array", [])

        # If array binding expression, resolve from context
        if isinstance(input_array, str) and "{{" in input_array:
            expr_context = context.get_expression_context()
            evaluator = ExpressionEvaluator(expr_context)
            try:
                input_array = evaluator.evaluate(input_array) or []
            except Exception as e:
                context.log("warning", f"Array expression evaluation failed: {e}", node_id)
                input_array = []

        # Also check input port (upstream node output)
        if not input_array:
            input_data = context.get_output(f"_input_{node_id}", "input")
            if isinstance(input_data, list):
                input_array = input_data
            elif isinstance(input_data, dict):
                # Check for array fields in input
                for key in ["array", "symbols", "values", "data", "items"]:
                    if key in input_data and isinstance(input_data[key], list):
                        input_array = input_data[key]
                        break

        if not isinstance(input_array, list):
            input_array = [input_array] if input_array else []

        # Get current item context (set by _execute_main_flow during iteration)
        split_context = context.get_node_state(node_id, "_split_context") or {
            "item": input_array[0] if input_array else None,
            "index": 0,
            "total": len(input_array),
        }

        context.log(
            "debug",
            f"SplitNode: item {split_context['index']+1}/{split_context['total']}",
            node_id,
        )

        return {
            "item": split_context["item"],
            "index": split_context["index"],
            "total": split_context["total"],
            # Also expose array for inspection
            "_array": input_array,
        }


class AggregateNodeExecutor(NodeExecutorBase):
    """
    AggregateNode executor

    Collects individual results from SplitNode branches and aggregates them.

    Modes:
    - collect: Collect all items into an array
    - filter: Filter items where filter_field is truthy
    - sum/avg/min/max: Aggregate numeric value_field
    - count: Count items (or items where filter_field is truthy)
    - first/last: Return first/last item

    Note: The collected items are stored in context by _execute_main_flow.
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        mode = config.get("mode", "collect")
        filter_field = config.get("filter_field", "passed")
        value_field = config.get("value_field", "value")

        # Get collected items (set by _execute_main_flow)
        collected_items = context.get_node_state(node_id, "_collected_items") or []

        context.log(
            "debug",
            f"AggregateNode: {len(collected_items)} items, mode={mode}",
            node_id,
        )

        result_array = []
        result_value = None
        result_count = 0

        if mode == "collect":
            # Collect all items
            result_array = collected_items
            result_count = len(collected_items)

        elif mode == "filter":
            # Filter by field value
            for item in collected_items:
                if isinstance(item, dict) and item.get(filter_field):
                    result_array.append(item)
            result_count = len(result_array)

        elif mode in ("sum", "avg", "min", "max"):
            # Aggregate numeric values
            values = []
            for item in collected_items:
                if isinstance(item, dict):
                    val = item.get(value_field)
                elif isinstance(item, (int, float)):
                    val = item
                else:
                    val = None

                if val is not None and isinstance(val, (int, float)):
                    values.append(val)

            if values:
                if mode == "sum":
                    result_value = sum(values)
                elif mode == "avg":
                    result_value = sum(values) / len(values)
                elif mode == "min":
                    result_value = min(values)
                elif mode == "max":
                    result_value = max(values)

            result_count = len(values)
            result_array = collected_items

        elif mode == "count":
            # Count items (optionally filtered)
            if filter_field:
                result_count = sum(
                    1 for item in collected_items
                    if isinstance(item, dict) and item.get(filter_field)
                )
            else:
                result_count = len(collected_items)
            result_array = collected_items

        elif mode == "first":
            # Return first item
            if collected_items:
                result_array = [collected_items[0]]
                result_value = collected_items[0]
            result_count = 1 if collected_items else 0

        elif mode == "last":
            # Return last item
            if collected_items:
                result_array = [collected_items[-1]]
                result_value = collected_items[-1]
            result_count = 1 if collected_items else 0

        return {
            "array": result_array,
            "value": result_value,
            "count": result_count,
        }


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
        count = config.get("count", 1000)  # 최대 반복 횟수 (M-6: 기본값 축소)
        max_duration_hours = config.get("max_duration_hours", 24.0)
        
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
            import time as _time
            cnt = 0
            start_mono = _time.monotonic()
            max_duration_sec = max_duration_hours * 3600
            try:
                # second_at_beginning=True로 초 단위 cron도 지원
                try:
                    itr = croniter(cron_expr, datetime.now(tz), second_at_beginning=True)
                except TypeError:
                    itr = croniter(cron_expr, datetime.now(tz))

                while cnt < count and context.is_running:
                    # dry_run: 루프 진입 즉시 1회 emit 후 종료
                    if context.is_dry_run:
                        cnt += 1
                        context.log(
                            "info",
                            f"[dry_run] Schedule tick #{cnt} (single cycle), exiting scheduler",
                            node_id,
                        )
                        await context.emit_event(
                            event_type="schedule_tick",
                            source_node_id=node_id,
                            data={
                                "cron": cron_expr,
                                "count": cnt,
                                "triggered_at": datetime.now(tz).isoformat(),
                                "dry_run": True,
                            },
                        )
                        break
                    # M-6: max_duration_hours 초과 시 스케줄 종료
                    if (_time.monotonic() - start_mono) >= max_duration_sec:
                        context.log(
                            "warning",
                            f"Schedule max_duration_hours={max_duration_hours}h 초과 - "
                            f"스케줄 자동 종료 (총 {cnt}회 실행)",
                            node_id,
                        )
                        break
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

                    # SCHEDULE_STARTED notification
                    try:
                        await context.send_notification(
                            category=NotificationCategory.SCHEDULE_STARTED,
                            severity=NotificationSeverity.INFO,
                            title=f"Schedule cycle #{cnt}",
                            message=f"Cron: {cron_expr}",
                            node_id=node_id,
                            node_type="ScheduleNode",
                            data={"cycle_number": cnt},
                        )
                    except Exception:
                        pass

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


class ExclusionListNodeExecutor(NodeExecutorBase):
    """
    ExclusionListNode executor - 거래 제외 종목 관리

    수동 입력(symbols) + 동적 입력(dynamic_symbols)을 합산하여 제외 목록을 생성합니다.
    input_symbols가 연결되면 차집합(필터링) 결과도 출력합니다.

    출력:
    - excluded: 최종 제외 종목 목록 [{exchange, symbol, reason}, ...]
    - filtered: input_symbols에서 제외 종목을 뺀 결과
    - count: 제외 종목 수
    - reasons: 종목별 제외 사유 맵 {"AAPL": "과열 우려", ...}
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        default_reason = config.get("default_reason", "")

        # 1. 수동 입력 종목 (각 항목에 reason 포함 가능)
        manual_symbols = config.get("symbols") or []

        # 2. 동적 입력 종목
        dynamic_symbols = config.get("dynamic_symbols") or []

        # 3. 합산 (중복 제거: exchange+symbol 키 기준) + reason 매핑
        from programgarden_core.models import normalize_symbol

        excluded_map: Dict[str, Dict[str, str]] = {}  # key: symbol -> {exchange, symbol, reason}
        reasons: Dict[str, str] = {}

        # 수동 입력 처리 (reason 우선)
        for entry in manual_symbols:
            if isinstance(entry, dict):
                symbol = entry.get("symbol", "")
                if not symbol:
                    continue
                exchange = entry.get("exchange", "")
                reason = entry.get("reason", "") or default_reason
                if not exchange:
                    norm = normalize_symbol(symbol)
                    exchange = norm.get("exchange", "") if isinstance(norm, dict) else ""
                excluded_map[symbol] = {"exchange": exchange, "symbol": symbol}
                if reason:
                    reasons[symbol] = reason
            elif isinstance(entry, str) and entry:
                norm = normalize_symbol(entry)
                exchange = norm.get("exchange", "") if isinstance(norm, dict) else ""
                excluded_map[entry] = {"exchange": exchange, "symbol": entry}
                if default_reason:
                    reasons[entry] = default_reason

        # 동적 입력 처리 (수동 입력에서 이미 있는 종목은 덮어쓰지 않음)
        for entry in dynamic_symbols:
            if isinstance(entry, dict):
                symbol = entry.get("symbol", "")
                if not symbol:
                    continue
                if symbol not in excluded_map:
                    exchange = entry.get("exchange", "")
                    if not exchange:
                        norm = normalize_symbol(symbol)
                        exchange = norm.get("exchange", "") if isinstance(norm, dict) else ""
                    excluded_map[symbol] = {"exchange": exchange, "symbol": symbol}
                    reason = entry.get("reason", "") or default_reason
                    if reason:
                        reasons[symbol] = reason
            elif isinstance(entry, str) and entry:
                if entry not in excluded_map:
                    norm = normalize_symbol(entry)
                    exchange = norm.get("exchange", "") if isinstance(norm, dict) else ""
                    excluded_map[entry] = {"exchange": exchange, "symbol": entry}
                    if default_reason:
                        reasons[entry] = default_reason

        all_excluded = list(excluded_map.values())

        # 4. input_symbols가 있으면 차집합 계산
        input_symbols = config.get("input_symbols")
        filtered = []
        if input_symbols:
            excluded_set = set(excluded_map.keys())
            for item in input_symbols:
                if isinstance(item, dict):
                    symbol = item.get("symbol", "")
                    if symbol and symbol not in excluded_set:
                        filtered.append(item)
                elif isinstance(item, str) and item not in excluded_set:
                    filtered.append({"exchange": "", "symbol": item})

        context.log(
            "info",
            f"ExclusionList: {len(all_excluded)} excluded"
            + (f", {len(filtered)} filtered" if input_symbols else ""),
            node_id,
        )

        return {
            "excluded": all_excluded,
            "filtered": filtered,
            "count": len(all_excluded),
            "reasons": reasons,
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
        # node_type으로 기본값 결정 (KoreaStockSymbolQueryNode → korea_stock)
        if "KoreaStock" in node_type:
            default_product_type = "korea_stock"
        elif "Futures" in node_type:
            default_product_type = "overseas_futures"
        else:
            default_product_type = "overseas_stock"
        product_type = config.get("product_type", default_product_type)
        
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
        elif product_type == "korea_stock":
            return await self._execute_korea_stock_master(
                node_id, config, context, appkey, appsecret, max_results
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
        
        ls, success, error = ensure_ls_login(appkey, appsecret, False, context, node_id, "overseas_stock")
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

    async def _execute_korea_stock_master(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        appkey: str,
        appsecret: str,
        max_results: int,
    ) -> Dict[str, Any]:
        """국내주식 종목마스터 조회 (t9945)

        KOSPI(gubun=1) + KOSDAQ(gubun=2) 두 번 호출하여 전체 종목 반환.
        """
        from programgarden_finance.ls.korea_stock.market.t9945.blocks import T9945InBlock

        ls, success, error = ensure_ls_login(appkey, appsecret, False, context, node_id, "korea_stock")
        if not success:
            return {"symbols": [], "count": 0, "error": error}

        api = ls.korea_stock()

        # stock_exchange / market 필터: "KOSPI", "KOSDAQ", "" (전체)
        # 노드 필드명은 "market"이지만 하위 호환으로 "stock_exchange"도 지원
        stock_exchange = config.get("market", config.get("stock_exchange", ""))

        all_symbols = []

        # KOSPI + KOSDAQ 조회 (stock_exchange 필터에 따라)
        gubun_list = []
        if not stock_exchange or stock_exchange.upper() == "KOSPI":
            gubun_list.append(("1", "KOSPI"))
        if not stock_exchange or stock_exchange.upper() == "KOSDAQ":
            gubun_list.append(("2", "KOSDAQ"))

        try:
            for gubun, market_name in gubun_list:
                body = T9945InBlock(gubun=gubun)
                response = api.market().t9945(body=body).req()

                if response and response.block:
                    for item in response.block:
                        shcode = getattr(item, 'shcode', '')
                        hname = getattr(item, 'hname', '')
                        etfchk = getattr(item, 'etfchk', '')

                        all_symbols.append({
                            "exchange": "KRX",
                            "market": market_name,
                            "symbol": shcode,
                            "name": hname,
                            "is_etf": etfchk == "1",
                            "product": "korea_stock",
                        })

                    context.log("debug", f"t9945 {market_name}: {len(response.block)} symbols", node_id)

            # max_results 적용
            if max_results and len(all_symbols) > max_results:
                all_symbols = all_symbols[:max_results]

            context.log("info", f"Korea stock master: {len(all_symbols)} symbols", node_id)

            return {
                "symbols": all_symbols,
                "count": len(all_symbols),
                "product": "korea_stock",
            }

        except Exception as e:
            context.log("error", f"Korea stock master query failed: {e}", node_id)
            return {"symbols": [], "count": 0, "error": str(e)}

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
        
        ls, success, error = ensure_ls_login(appkey, appsecret, paper_trading, context, node_id, "overseas_futures")
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
    """BrokerNode executor

    계좌 수익률 자동 추적:
    - 리스너에 on_workflow_pnl_update가 구현되어 있으면 자동으로 AccountTracker 시작
    - 틱마다 워크플로우/계좌 수익률 계산 후 리스너에 전달 (서버에서 쓰로틀링 권장)
    - overseas_stock: StockAccountTracker 사용
    - overseas_futures: FuturesAccountTracker 사용
    """
    
    # 활성화된 트래커 저장 (Job 종료 시 정리용)
    _active_trackers: Dict[str, Any] = {}

    async def cleanup_fill_subscriptions(self, job_id: str) -> None:
        """BrokerNode가 등록한 fill subscription 콜백 정리

        Args:
            job_id: 해당 job의 fill_subscription만 정리
        """
        keys_to_remove = []
        for key, info in self._active_trackers.items():
            if not key.startswith(job_id):
                continue
            if info.get("type") != "fill_subscription":
                continue
            real = info.get("real")
            if real:
                # SDK 콜백 해제
                for tr_name, remove_method in [
                    ("AS0", "on_remove_as0_message"),
                    ("AS1", "on_remove_as1_message"),
                    ("TC2", "on_remove_tc2_message"),
                    ("TC3", "on_remove_tc3_message"),
                ]:
                    if hasattr(real, tr_name):
                        try:
                            getattr(getattr(real, tr_name)(), remove_method)()
                        except (RuntimeError, AttributeError):
                            pass
                        except Exception as e:
                            logger.warning(f"Failed to cleanup fill subscription {key}/{tr_name}: {e}")
            keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._active_trackers[key]
            logger.debug(f"Cleaned up fill subscription: {key}")

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
        # node_type에 따라 product 기본값 결정
        if "Futures" in node_type:
            default_product = "overseas_futures"
        elif "KoreaStock" in node_type:
            default_product = "korea_stock"
        else:
            default_product = "overseas_stock"
        product = config.get("product", default_product)
        # 국내주식은 실전투자 전용 (paper_trading 필드 없음)
        if product == "korea_stock":
            paper_trading = False
        else:
            # Default matches Pydantic BrokerNode.paper_trading default (False).
            # overseas_stock has no paper channel → default True would fail-closed
            # with "모의투자 미지원" on every unset workflow.
            paper_trading = config.get("paper_trading", False)

        # ========================================
        # 모의투자 지원 여부 검증
        # - overseas_stock: 모의투자 미지원 (LS증권) → 에러 반환 (자동 실전 전환 금지)
        # - overseas_futures: 모의투자 지원
        # - korea_stock: 실전투자 전용 (위에서 False 강제)
        # ========================================
        if product == "overseas_stock" and paper_trading:
            context.log(
                "error",
                "overseas_stock은 모의투자를 지원하지 않습니다 (LS증권 제한). "
                "paper_trading=False로 설정하거나, 해외선물(overseas_futures)을 사용하세요.",
                node_id,
            )
            return {
                "connection": None,
                "error": "overseas_stock does not support paper_trading. Set paper_trading=False to use real mode.",
            }
        
        # ========================================
        # Credential 자동 주입 (GenericNodeExecutor와 동일 패턴)
        # credential_id가 있으면 appkey, appsecret이 config에 주입됨
        # ========================================
        credential_id = config.get("credential_id")
        context.log("debug", f"BrokerNode credential_id={credential_id}", node_id)
        if credential_id:
            config = self._inject_credentials(credential_id, config, context, node_id)
            context.log("debug", f"After inject_credentials: appkey={bool(config.get('appkey'))}, appsecret={bool(config.get('appsecret'))}", node_id)

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

        if appkey and appsecret:
            context.log("info", f"Broker connected: {provider} ({product}, paper_trading={paper_trading})", node_id)
        else:
            context.log("warning", f"Broker initialized without credentials: {provider} ({product}, paper_trading={paper_trading})", node_id)
        
        # ========================================
        # 워크플로우 포지션 추적기 초기화 (리스너 자동 감지)
        # on_workflow_pnl_update를 구현한 리스너가 있으면 자동 시작
        # dry_run 모드에서는 주문/실시간 콜백이 모두 skip 되어 추적 대상이 없으므로
        # SQLite 파일 생성 자체를 건너뛴다.
        # ========================================
        if not context.is_dry_run:
            context.init_workflow_position_tracker(
                broker_node_id=node_id,
                product=product,
                provider=provider,
                paper_trading=paper_trading,
            )

            # ========================================
            # 위험관리 추적기 초기화 (노드/플러그인 risk feature 수집)
            # risk_features를 선언한 노드/플러그인이 있으면 RiskTracker 자동 시작
            # ========================================
            risk_features = self._collect_risk_features(context)
            if risk_features:
                context.init_risk_tracker(
                    features=risk_features,
                    product=product,
                    provider=provider,
                    paper_trading=paper_trading,
                )

        # ========================================
        # Fallback: 체결내역 조회로 시장가 주문 가격 복구
        # 연결 끊김 등으로 실시간 체결 이벤트를 놓친 경우 대비
        # ========================================
        if appkey and appsecret:
            asyncio.create_task(
                self._sync_fill_prices_from_history(
                    node_id=node_id,
                    product=product,
                    appkey=appkey,
                    appsecret=appsecret,
                    paper_trading=paper_trading,
                    context=context,
                )
            )
        
        # ========================================
        # 계좌 수익률 자동 추적 (리스너 자동 감지)
        # on_workflow_pnl_update를 구현한 리스너가 있으면 자동 시작
        # ========================================
        has_workflow_listener = self._has_workflow_pnl_listener(context)

        if appkey and appsecret and has_workflow_listener:
            context.log("info", "WorkflowPnL listener detected - starting account tracking", node_id)
            asyncio.create_task(
                self._start_account_tracking(
                    node_id=node_id,
                    product=product,
                    provider=provider,
                    appkey=appkey,
                    appsecret=appsecret,
                    paper_trading=paper_trading,
                    context=context,
                )
            )
        
        # ========================================
        # 워크플로우 체결 이벤트 자동 구독 (FIFO 포지션 추적용)
        # on_workflow_pnl_update 리스너가 있으면 체결/정정/취소 이벤트 구독
        # 
        # await로 실행하여 WebSocket 연결이 완료된 후 다음 노드 진행
        # 이렇게 해야 주문 시점에 체결 이벤트를 수신할 수 있음
        # ========================================
        if appkey and appsecret and has_workflow_listener:
            context.log("info", "Starting workflow fill event subscription for FIFO tracking", node_id)
            await self._subscribe_workflow_fill_events(
                node_id=node_id,
                product=product,
                appkey=appkey,
                appsecret=appsecret,
                paper_trading=paper_trading,
                context=context,
            )
        
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

    def _collect_risk_features(self, context: ExecutionContext) -> set:
        """워크플로우 내 노드/플러그인의 risk feature 요구사항 수집"""
        features = set()
        valid = {"hwm", "window", "events", "state"}

        # workflow_nodes에서 노드 클래스의 _risk_features 수집
        if hasattr(context, '_reverse_adj') and hasattr(context, '_outputs'):
            # DAG 내 모든 노드의 resolved 정보 접근
            workflow_nodes = getattr(context, '_workflow_nodes_map', None)
            if workflow_nodes:
                for node_id, resolved_node in workflow_nodes.items():
                    node_cls = getattr(resolved_node, 'node_class', None) or getattr(resolved_node, '_node_class', None)
                    if node_cls:
                        features.update(getattr(node_cls, '_risk_features', set()))

                    # 플러그인의 risk_features
                    plugin_name = getattr(resolved_node, 'plugin', None)
                    if not plugin_name and hasattr(resolved_node, 'config'):
                        plugin_name = resolved_node.config.get('plugin') if isinstance(resolved_node.config, dict) else None
                    if plugin_name:
                        features.update(self._get_plugin_risk_features(plugin_name))

        # context에 workflow_nodes_map이 없으면 workflow_nodes dict에서 시도
        if not features:
            wf_nodes = getattr(context, '_workflow_nodes_dict', None)
            if wf_nodes and isinstance(wf_nodes, dict):
                for node_def in wf_nodes.values():
                    node_type = node_def.get("type", "") if isinstance(node_def, dict) else getattr(node_def, "type", "")
                    node_cls = self._resolve_node_class_for_risk(node_type)
                    if node_cls:
                        features.update(getattr(node_cls, '_risk_features', set()))

                    plugin_name = node_def.get("plugin") if isinstance(node_def, dict) else getattr(node_def, "plugin", None)
                    if plugin_name:
                        features.update(self._get_plugin_risk_features(plugin_name))

        return features & valid

    def _get_plugin_risk_features(self, plugin_name: str) -> set:
        """플러그인 모듈에서 risk_features 속성 조회

        1) registry.get_plugin_module() 우선 사용
        2) 등록된 plugin callable의 __module__ 역추적 (Dynamic 플러그인 지원)
        3) hardcoded fallback (하위 호환)
        """
        try:
            from programgarden_core.registry import PluginRegistry
            registry = PluginRegistry()
            plugin_module = registry.get_plugin_module(plugin_name) if hasattr(registry, 'get_plugin_module') else None
            if plugin_module:
                return set(getattr(plugin_module, 'risk_features', set()))

            # callable의 __module__ 로 모듈 역추적 (일반화된 동적 플러그인 지원)
            plugin_callable = registry.get(plugin_name) if hasattr(registry, 'get') else None
            if plugin_callable:
                module_name = getattr(plugin_callable, '__module__', None)
                if module_name:
                    import sys
                    mod = sys.modules.get(module_name)
                    if mod is not None:
                        features = getattr(mod, 'risk_features', None)
                        if features:
                            return set(features)

            # 직접 import 시도 (하위 호환 fallback)
            import importlib
            module_map = {
                "TrailingStop": "programgarden_community.plugins.trailing_stop",
            }
            mod_path = module_map.get(plugin_name)
            if mod_path:
                mod = importlib.import_module(mod_path)
                return set(getattr(mod, 'risk_features', set()))
        except Exception:
            pass
        return set()

    def _resolve_node_class_for_risk(self, node_type: str):
        """노드 타입에서 클래스 resolve (risk feature 수집용)"""
        try:
            from programgarden_core.registry import NodeRegistry
            registry = NodeRegistry()
            return registry.get(node_type) if hasattr(registry, 'get') else None
        except Exception:
            return None

    def _has_workflow_pnl_listener(self, context: ExecutionContext) -> bool:
        """리스너 중 on_workflow_pnl_update를 실제로 오버라이드한 게 있는지 확인"""
        from programgarden_core.bases import BaseExecutionListener

        logger.debug(f"[_has_workflow_pnl_listener] Checking {len(context._listeners)} listeners")
        for listener in context._listeners:
            listener_class = type(listener)
            if 'on_workflow_pnl_update' in listener_class.__dict__:
                return True
            for cls in listener_class.__mro__:
                if cls is BaseExecutionListener:
                    break
                if 'on_workflow_pnl_update' in cls.__dict__:
                    return True
        return False
    
    async def _subscribe_workflow_fill_events(
        self,
        node_id: str,
        product: str,
        appkey: str,
        appsecret: str,
        paper_trading: bool,
        context: ExecutionContext,
    ) -> None:
        """워크플로우 체결 이벤트 구독 (FIFO 포지션 추적용)
        
        체결('11'), 정정완료('12'), 취소완료('13') 이벤트를 수신하여
        WorkflowPositionTracker에 기록합니다.
        
        Note: ensure_ls_login()을 사용하여 RealMarketDataNode와 동일한
        LS 인스턴스를 공유합니다. 이로써 하나의 WebSocket 연결에서
        GSC(시세)와 AS0/AS1(주문) 이벤트를 모두 수신합니다.
        """
        try:
            from datetime import datetime
            
            # ensure_ls_login으로 동일한 LS 인스턴스 사용 (RealMarketDataNode와 공유)
            ls, success, error = ensure_ls_login(appkey, appsecret, paper_trading, context, node_id, product)
            
            if not success:
                context.log("error", f"Failed to login for fill event subscription (node={node_id}): {error}", node_id)
                return
            
            context.log("info", f"Using shared LS instance for fill event subscription (product={product})", node_id)
            
            if product == "overseas_stock":
                await self._subscribe_overseas_stock_fill_events(ls, node_id, context)
            elif product == "overseas_futures":
                await self._subscribe_overseas_futures_fill_events(ls, node_id, context)
            elif product == "korea_stock":
                await self._subscribe_korea_stock_fill_events(ls, node_id, context)
            else:
                context.log("warning", f"Unknown product type for fill subscription: {product}", node_id)
                
        except Exception as e:
            context.log("error", f"Failed to subscribe fill events: {e}", node_id)
    
    async def _subscribe_overseas_stock_fill_events(
        self,
        ls,
        node_id: str,
        context: ExecutionContext,
    ) -> None:
        """해외주식 체결 이벤트 구독
        
        AS0~AS4 이벤트 구조:
        - AS0: 주문 접수 (01: 신규, 03: 취소접수)
        - AS1: 주문 체결 (sExecQty > 0 일 때 체결)
        - AS0/AS1: 정정완료(12), 취소완료(13), 거부(14)
        
        _add_real_order()가 한번 호출되면 AS0~AS4 전부 자동 등록되지만,
        콜백은 TR별로 따로 등록해야 함.
        """
        from datetime import datetime
        
        real = ls.overseas_stock().real()
        await real.connect()
        
        # 이벤트 루프 캡처
        loop = asyncio.get_running_loop()
        
        def on_as0_event(resp):
            """AS0: 주문 접수/정정완료/취소완료 이벤트 처리"""
            try:
                if context.is_shutdown:
                    return
                body = getattr(resp, 'body', resp)
                ord_type_code = getattr(body, 'sOrdxctPtnCode', '')
                
                logger.info(f"📡 AS0 event: type={ord_type_code}")
                
                # 필요한 필드 추출
                order_no = str(getattr(body, 'sOrdNo', ''))
                order_date = getattr(body, 'sOrdDt', datetime.now().strftime('%Y%m%d'))
                
                if ord_type_code == '12':  # 정정완료
                    quantity = int(getattr(body, 'sOrdQty', 0))
                    price = float(getattr(body, 'sOrdPrc', 0))
                    new_qty = int(getattr(body, 'sOrgOrdMdfyQty', 0)) or quantity
                    new_price = price
                    asyncio.run_coroutine_threadsafe(
                        context.modify_workflow_order(
                            order_no=order_no,
                            order_date=order_date,
                            new_quantity=new_qty if new_qty > 0 else None,
                            new_price=new_price if new_price > 0 else None,
                        ),
                        loop
                    )
                    logger.debug(f"📌 Workflow order modified: {order_no}")
                
                elif ord_type_code == '13':  # 취소완료
                    asyncio.run_coroutine_threadsafe(
                        context.cancel_workflow_order(
                            order_no=order_no,
                            order_date=order_date,
                        ),
                        loop
                    )
                    logger.debug(f"📌 Workflow order cancelled: {order_no}")
                    
            except Exception as e:
                logger.warning(f"Error processing AS0 event: {e}")
        
        def on_as1_event(resp):
            """AS1: 주문 체결 이벤트 처리"""
            try:
                if context.is_shutdown:
                    return
                body = getattr(resp, 'body', resp)
                
                # AS1 체결 전용 필드
                exec_qty = int(getattr(body, 'sExecQty', 0))
                exec_price = float(getattr(body, 'sExecPrc', 0))
                
                if exec_qty <= 0:
                    # 체결 수량이 0이면 체결 이벤트가 아님
                    return
                
                logger.info(f"📡 AS1 fill event: qty={exec_qty}, price={exec_price}")
                
                # 필요한 필드 추출
                order_no = str(getattr(body, 'sOrdNo', ''))
                order_date = datetime.now().strftime('%Y%m%d')  # AS1에는 sOrdDt 없음
                symbol = getattr(body, 'sShtnIsuNo', getattr(body, 'sIsuNo', ''))
                market_code = getattr(body, 'sOrdMktCode', '82')
                side_code = getattr(body, 'sOrdPtnCode', '')  # 01: 매도, 02: 매수
                fill_time = getattr(body, 'proctm', datetime.now().strftime('%H%M%S000'))
                
                # 시장코드 → 거래소 변환
                exchange_map = {'81': 'NYSE', '82': 'NASDAQ', '83': 'AMEX'}
                exchange = exchange_map.get(market_code, 'NASDAQ')
                
                # 매매구분 (AS1: sOrdPtnCode 또는 sBnsTp)
                bns_tp = getattr(body, 'sBnsTp', '')  # 1: 매도, 2: 매수
                if bns_tp:
                    side = 'buy' if bns_tp == '2' else 'sell'
                else:
                    side = 'buy' if side_code == '02' else 'sell'
                
                async def record_and_refresh():
                    """체결 기록 후 AccountTracker refresh"""
                    await context.record_workflow_fill(
                        order_no=order_no,
                        order_date=order_date,
                        symbol=symbol,
                        exchange=exchange,
                        side=side,
                        quantity=exec_qty,
                        price=exec_price,
                        fill_time=fill_time,
                        commda_code='40',  # OPEN API
                    )
                    
                    # AccountTracker refresh로 PnL 이벤트 강제 트리거
                    tracker_key = f"{context.job_id}_{node_id}"
                    tracker_info = self._active_trackers.get(tracker_key)
                    if tracker_info and "tracker" in tracker_info:
                        tracker = tracker_info["tracker"]
                        if hasattr(tracker, 'refresh_now'):
                            await tracker.refresh_now()
                            logger.debug(f"📊 AccountTracker refreshed after fill")
                
                asyncio.run_coroutine_threadsafe(record_and_refresh(), loop)
                logger.info(f"📌 Workflow fill recorded: {symbol} {side} {exec_qty}@{exec_price}")
                    
            except Exception as e:
                logger.warning(f"Error processing AS1 event: {e}")
        
        # AS0 구독 등록 (접수/정정완료/취소완료)
        real.AS0().on_as0_message(on_as0_event)
        
        # AS1 구독 등록 (체결)
        real.AS1().on_as1_message(on_as1_event)
        
        # 활성 구독 저장 (나중에 정리용)
        sub_key = f"{context.job_id}_{node_id}_fill_sub"
        self._active_trackers[sub_key] = {
            "ls": ls,
            "real": real,
            "type": "fill_subscription",
        }
        
        context.log("info", f"Workflow fill event subscription started (AS0+AS1)", node_id)
    
    async def _subscribe_overseas_futures_fill_events(
        self,
        ls,
        node_id: str,
        context: ExecutionContext,
    ) -> None:
        """해외선물 체결 이벤트 구독

        TC1: 주문접수 (HO01=ACK, HO04=Pending)
        TC2: 주문응답 (HO02=확인, HO03=거부)
        TC3: 주문체결 (CH01=체결) ← 실제 체결 이벤트
        """
        from datetime import datetime

        real = ls.overseas_futureoption().real()
        await real.connect()

        # 이벤트 루프 캡처
        loop = asyncio.get_running_loop()

        def on_tc2_event(resp):
            """TC2 이벤트 처리 (주문 확인/정정/취소)

            TC2 필드명:
            - svc_id: HO02=주문확인, HO03=주문거부
            - ordr_no: 주문번호
            - ordr_dt: 주문일자
            - is_cd: 종목코드
            - s_b_ccd: 매매구분 (1=매수, 2=매도)
            - ordr_ccd: 주문구분 (1=신규, 2=정정, 3=취소)
            - ordr_q: 주문수량
            - ordr_prc: 주문가격
            """
            try:
                if context.is_shutdown:
                    return
                body = getattr(resp, 'body', resp)
                header = getattr(resp, 'header', None)
                # TC2에서는 svc_id가 body에 있음
                svc_id = getattr(body, 'svc_id', '') or (getattr(header, 'svc_id', '') if header else '')

                order_no = str(getattr(body, 'ordr_no', ''))
                order_date = getattr(body, 'ordr_dt', datetime.now().strftime('%Y%m%d'))
                symbol = getattr(body, 'is_cd', '')
                side_code = getattr(body, 's_b_ccd', '')  # 매매구분
                quantity = int(getattr(body, 'ordr_q', 0) or getattr(body, 'cnfr_q', 0) or 0)
                price = float(getattr(body, 'ordr_prc', 0) or 0)
                ordr_ccd = getattr(body, 'ordr_ccd', '')  # 1=신규, 2=정정, 3=취소

                # 매매구분
                side = 'buy' if side_code == '1' else 'sell'

                logger.debug(f"[TC2] svc_id={svc_id}, ordr_ccd={ordr_ccd}, order_no={order_no}, symbol={symbol}")

                if svc_id == 'HO02':  # 주문 확인
                    if ordr_ccd == '2':  # 정정 완료
                        asyncio.run_coroutine_threadsafe(
                            context.modify_workflow_order(
                                order_no=order_no,
                                order_date=order_date,
                                new_quantity=quantity if quantity > 0 else None,
                                new_price=price if price > 0 else None,
                            ),
                            loop
                        )
                    elif ordr_ccd == '3':  # 취소 완료
                        asyncio.run_coroutine_threadsafe(
                            context.cancel_workflow_order(
                                order_no=order_no,
                                order_date=order_date,
                            ),
                            loop
                        )

            except Exception as e:
                logger.warning(f"Error processing TC2 event: {e}")

        def on_tc3_event(resp):
            """TC3 이벤트 처리 (체결 통보) - 실제 체결 이벤트

            TC3 필드명:
            - svc_id: CH01=체결
            - ordr_no: 주문번호
            - ordr_dt: 주문일자
            - is_cd: 종목코드
            - s_b_ccd: 매매구분 (1=매수, 2=매도)
            - ccls_q: 체결수량
            - ccls_prc: 체결가격
            - ccls_tm: 체결시간
            """
            try:
                if context.is_shutdown:
                    return
                body = getattr(resp, 'body', resp)
                header = getattr(resp, 'header', None)
                # TC3에서는 svc_id가 body에 있음
                svc_id = getattr(body, 'svc_id', '') or (getattr(header, 'svc_id', '') if header else '')

                order_no = str(getattr(body, 'ordr_no', ''))
                order_date = getattr(body, 'ordr_dt', datetime.now().strftime('%Y%m%d'))
                symbol = getattr(body, 'is_cd', '')
                side_code = getattr(body, 's_b_ccd', '')  # 매매구분
                # TC3에서는 ccls_q, ccls_prc가 체결수량/체결가격
                quantity = int(getattr(body, 'ccls_q', 0) or 0)
                price_str = str(getattr(body, 'ccls_prc', '0') or '0')
                price = float(price_str.strip()) if price_str.strip() else 0.0
                fill_time = getattr(body, 'ccls_tm', datetime.now().strftime('%H%M%S000'))

                # 매매구분
                side = 'buy' if side_code == '1' else 'sell'

                logger.info(f"[TC3] 체결: svc_id={svc_id}, order_no={order_no}, symbol={symbol}, side={side}, qty={quantity}, price={price}")

                if svc_id == 'CH01':  # 체결 통보
                    if price > 0 and quantity > 0:
                        asyncio.run_coroutine_threadsafe(
                            context.record_workflow_fill(
                                order_no=order_no,
                                order_date=order_date,
                                symbol=symbol,
                                exchange='FUTURES',
                                side=side,
                                quantity=quantity,
                                price=price,
                                fill_time=fill_time,
                                commda_code='40',
                            ),
                            loop
                        )

            except Exception as e:
                logger.warning(f"Error processing TC3 event: {e}")

        # TC2 + TC3 구독 등록
        real.TC2().on_tc2_message(on_tc2_event)
        real.TC3().on_tc3_message(on_tc3_event)

        # 활성 구독 저장
        sub_key = f"{context.job_id}_{node_id}_fill_sub"
        self._active_trackers[sub_key] = {
            "ls": ls,
            "real": real,
            "type": "fill_subscription",
        }

        context.log("info", f"Workflow fill event subscription started (TC2+TC3)", node_id)

    async def _subscribe_korea_stock_fill_events(
        self,
        ls,
        node_id: str,
        context: ExecutionContext,
    ) -> None:
        """국내주식 체결 이벤트 구독

        SC1 이벤트 구독 (SC1 등록 시 SC0~SC4 전체 활성화).
        ordxctptncode 값으로 분기:
        - '11': 체결 → record_workflow_fill()
        - '12': 정정확인 → modify_workflow_order()
        - '13': 취소확인 → cancel_workflow_order()
        """
        from datetime import datetime

        real = ls.korea_stock().real()
        await real.connect()

        # 이벤트 루프 캡처
        loop = asyncio.get_running_loop()

        def on_sc1_event(resp):
            """SC1: 주문체결/정정/취소 이벤트 처리"""
            try:
                if context.is_shutdown:
                    return
                body = getattr(resp, 'body', resp)
                if not body:
                    return

                ord_type_code = getattr(body, 'ordxctptncode', '')

                if ord_type_code == '11':  # 체결
                    exec_qty = int(getattr(body, 'execqty', '0') or '0')
                    exec_price = float(getattr(body, 'execprc', '0') or '0')

                    if exec_qty <= 0 or exec_price <= 0:
                        return

                    logger.info(f"[SC1] 국내주식 체결: qty={exec_qty}, price={exec_price}")

                    order_no = str(getattr(body, 'ordno', ''))
                    order_date = datetime.now().strftime('%Y%m%d')
                    # shtnIsuno: 'A005930' → '005930' (A 접두사 제거)
                    raw_symbol = getattr(body, 'shtnIsuno', '')
                    symbol = raw_symbol.lstrip('A') if raw_symbol.startswith('A') else raw_symbol
                    bns_tp = getattr(body, 'bnstp', '')  # 1:매도, 2:매수
                    side = 'buy' if bns_tp == '2' else 'sell'
                    fill_time = getattr(body, 'exectime', datetime.now().strftime('%H%M%S000'))

                    async def record_and_refresh():
                        """체결 기록 후 AccountTracker refresh"""
                        await context.record_workflow_fill(
                            order_no=order_no,
                            order_date=order_date,
                            symbol=symbol,
                            exchange='KRX',
                            side=side,
                            quantity=exec_qty,
                            price=exec_price,
                            fill_time=fill_time,
                            commda_code='40',
                        )

                        # AccountTracker refresh로 PnL 이벤트 강제 트리거
                        tracker_key = f"{context.job_id}_{node_id}"
                        tracker_info = self._active_trackers.get(tracker_key)
                        if tracker_info and "tracker" in tracker_info:
                            tracker = tracker_info["tracker"]
                            if hasattr(tracker, 'refresh_now'):
                                await tracker.refresh_now()
                                logger.debug(f"KoreaStockAccountTracker refreshed after fill")

                    asyncio.run_coroutine_threadsafe(record_and_refresh(), loop)
                    logger.info(f"Workflow fill recorded: {symbol} {side} {exec_qty}@{exec_price}")

                elif ord_type_code == '12':  # 정정확인
                    order_no = str(getattr(body, 'ordno', ''))
                    order_date = datetime.now().strftime('%Y%m%d')
                    new_qty = int(getattr(body, 'mdfycnfqty', '0') or '0')
                    new_price = float(getattr(body, 'mdfycnfprc', '0') or '0')
                    asyncio.run_coroutine_threadsafe(
                        context.modify_workflow_order(
                            order_no=order_no,
                            order_date=order_date,
                            new_quantity=new_qty if new_qty > 0 else None,
                            new_price=new_price if new_price > 0 else None,
                        ),
                        loop
                    )
                    logger.debug(f"Workflow order modified (korea_stock): {order_no}")

                elif ord_type_code == '13':  # 취소확인
                    order_no = str(getattr(body, 'ordno', ''))
                    order_date = datetime.now().strftime('%Y%m%d')
                    asyncio.run_coroutine_threadsafe(
                        context.cancel_workflow_order(
                            order_no=order_no,
                            order_date=order_date,
                        ),
                        loop
                    )
                    logger.debug(f"Workflow order cancelled (korea_stock): {order_no}")

            except Exception as e:
                logger.warning(f"Error processing SC1 event: {e}")

        # SC1 구독 등록 (SC0~SC4 전체 활성화)
        real.SC1().on_sc1_message(on_sc1_event)

        # 활성 구독 저장
        sub_key = f"{context.job_id}_{node_id}_fill_sub"
        self._active_trackers[sub_key] = {
            "ls": ls,
            "real": real,
            "type": "fill_subscription",
        }

        context.log("info", f"Workflow fill event subscription started (SC1, korea_stock)", node_id)

    async def _sync_fill_prices_from_history(
        self,
        node_id: str,
        product: str,
        appkey: str,
        appsecret: str,
        paper_trading: bool,
        context: ExecutionContext,
    ) -> None:
        """체결내역 조회로 시장가 주문 가격 복구 (Fallback)
        
        연결 끊김 등으로 실시간 체결 이벤트를 놓친 경우,
        체결내역 API를 조회하여 가격이 0인 주문의 실제 체결 가격을 업데이트합니다.
        """
        try:
            # 가격이 0인 주문이 있는지 확인
            orders_without_price = context.get_workflow_orders_without_fill_price()
            if not orders_without_price:
                return
            
            context.log("info", f"Found {len(orders_without_price)} orders without fill price - syncing from history", node_id)
            
            from programgarden_finance import LS
            
            ls, success, error = ensure_ls_login(appkey, appsecret, paper_trading, context, node_id, product)
            if not success:
                context.log("warning", f"Failed to login for fill price sync: {error}", node_id)
                return
            
            if product == "overseas_stock":
                await self._sync_overseas_stock_fill_prices(ls, orders_without_price, context, node_id)
            elif product == "overseas_futures":
                await self._sync_overseas_futures_fill_prices(ls, orders_without_price, context, node_id)
            elif product == "korea_stock":
                # 국내주식 체결가격 복구는 향후 구현 (t0425 미체결 조회 활용)
                context.log("debug", f"korea_stock fill price sync not yet implemented", node_id)

        except Exception as e:
            context.log("warning", f"Failed to sync fill prices from history: {e}", node_id)
    
    async def _sync_overseas_stock_fill_prices(
        self,
        ls,
        orders: list,
        context: ExecutionContext,
        node_id: str,
    ) -> None:
        """해외주식 체결내역에서 FIFO 포지션 동기화
        
        연결 끊김 등으로 실시간 체결 이벤트를 놓친 경우,
        체결내역 API를 조회하여 FIFO 포지션을 생성합니다.
        """
        try:
            from programgarden_finance import COSAQ00102

            
            # 오늘 날짜 기준 체결내역 조회 (COSAQ00102 = 주문체결내역조회)
            today = datetime.now().strftime("%Y%m%d")
            
            response = ls.overseas_stock().accno().cosaq00102(
                body=COSAQ00102.COSAQ00102InBlock1(
                    RecCnt=1,
                    QryTpCode="1",  # 계좌별
                    BkseqTpCode="1",  # 역순
                    OrdMktCode="00",  # 전체 시장
                    BnsTpCode="0",  # 전체 (매수/매도)
                    IsuNo="",  # 전체 종목
                    SrtOrdNo=999999999,  # 역순 시작
                    OrdDt=today,  # 오늘 날짜
                    ExecYn="1",  # 체결만 조회
                    CrcyCode="000",  # 전체 통화
                    ThdayBnsAppYn="0",
                    LoanBalHldYn="0",
                ),
            )
            result = await response.req_async()
            
            if not result or not result.block3:
                context.log("debug", "No fill history found for today", node_id)
                return
            
            # 시장코드 → 거래소 매핑
            market_to_exchange = {'81': 'NYSE', '82': 'NASDAQ', '83': 'AMEX'}
            
            # 체결내역에서 상세 정보 추출 (block3 = 주문/체결 상세)
            fill_history = []
            for item in result.block3:
                order_no = str(getattr(item, 'OrdNo', 0))
                fill_price = float(getattr(item, 'OvrsExecPrc', 0))
                fill_qty = int(getattr(item, 'ExecQty', 0))
                symbol = str(getattr(item, 'ShtnIsuNo', getattr(item, 'IsuNo', '')))
                market_code = str(getattr(item, 'OrdMktCode', '82'))
                side_code = str(getattr(item, 'BnsTpCode', ''))  # 1=매도, 2=매수
                fill_time = str(getattr(item, 'ExecTime', ''))
                
                # 시장코드 → 거래소
                exchange = market_to_exchange.get(market_code, 'NASDAQ')
                # 매매구분
                side = 'sell' if side_code == '1' else 'buy'
                
                if order_no and fill_price > 0 and fill_qty > 0 and symbol:
                    fill_history.append({
                        "order_no": order_no,
                        "order_date": today,
                        "symbol": symbol,
                        "exchange": exchange,
                        "side": side,
                        "quantity": fill_qty,
                        "price": fill_price,
                        "fill_time": fill_time,
                    })
            
            if fill_history:
                # 1. 가격 업데이트 (기존 로직)
                simple_history = [{"order_no": f["order_no"], "order_date": f["order_date"], "fill_price": f["price"]} for f in fill_history]
                updated = context.sync_workflow_fill_prices_from_history(simple_history)
                if updated > 0:
                    context.log("info", f"Synced {updated} order fill prices from stock history", node_id)
                
                # 2. FIFO 포지션 생성 (새 로직)
                processed = context.sync_workflow_fills_from_history(fill_history)
                if processed > 0:
                    context.log("info", f"Created {processed} FIFO positions from stock fill history", node_id)
                    
        except Exception as e:
            context.log("warning", f"Failed to sync stock fills: {e}", node_id)
    
    async def _sync_overseas_futures_fill_prices(
        self,
        ls,
        orders: list,
        context: ExecutionContext,
        node_id: str,
    ) -> None:
        """해외선물 체결내역에서 가격 동기화"""
        try:
            from programgarden_finance import CIDBQ01800
            
            # 오늘 날짜 기준 체결내역 조회
            today = datetime.now().strftime("%Y%m%d")
            
            response = ls.overseas_futureoption().accno().해외선물체결내역조회(
                body=CIDBQ01800.CIDBQ01800InBlock(
                    QryDt=today,
                )
            )
            result = await response.req_async()
            
            if not result or not hasattr(result, 'block1') or not result.block1:
                return
            
            # 체결내역에서 주문번호별 가격 추출
            fill_history = []
            for item in result.block1:
                fill_history.append({
                    "order_no": str(getattr(item, 'OrdNo', '')),
                    "order_date": today,
                    "fill_price": float(getattr(item, 'ExecPrc', 0)),
                })
            
            if fill_history:
                updated = context.sync_workflow_fill_prices_from_history(fill_history)
                if updated > 0:
                    context.log("info", f"Synced {updated} order fill prices from futures history", node_id)
                    
        except Exception as e:
            context.log("warning", f"Failed to sync futures fill prices: {e}", node_id)
    
    async def _start_account_tracking(
        self,
        node_id: str,
        product: str,
        provider: str,
        appkey: str,
        appsecret: str,
        paper_trading: bool,
        context: ExecutionContext,
    ) -> None:
        """계좌 추적기 시작 및 수익률 콜백 등록"""
        try:
            from programgarden_finance import LS
            
            # LS 클라이언트 생성 (별도 인스턴스)
            ls = LS()
            login_success = ls.login(
                appkey=appkey,
                appsecretkey=appsecret,
                paper_trading=paper_trading,
            )
            
            if not login_success:
                context.log("error", f"Failed to login for account tracking (node={node_id})", node_id)
                return
            
            if product == "overseas_stock":
                await self._start_overseas_stock_tracker(
                    ls, node_id, product, provider, context,
                )
            elif product == "overseas_futures":
                await self._start_overseas_futures_tracker(
                    ls, node_id, product, provider, context,
                )
            elif product == "korea_stock":
                await self._start_korea_stock_tracker(
                    ls, node_id, product, provider, context,
                )
            else:
                context.log("warning", f"Unknown product type for tracking: {product}", node_id)
                
        except Exception as e:
            context.log("error", f"Failed to start account tracking: {e}", node_id)
    
    async def _start_overseas_stock_tracker(
        self,
        ls,
        node_id: str,
        product: str,
        provider: str,
        context: ExecutionContext,
    ) -> None:
        """해외주식 계좌 추적기 시작"""
        accno = ls.overseas_stock().accno()
        real = ls.overseas_stock().real()
        await real.connect()

        tracker = accno.account_tracker(real_client=real)

        # 수익률 콜백 등록
        def on_pnl_change(pnl_info):
            # tracker에서 현재 positions 조회 (AccountPnLInfo에는 positions가 없음)
            current_prices = {}
            account_positions = {}

            positions = tracker.get_positions()  # Dict[symbol, StockPositionItem]
            if positions:
                for symbol, pos_item in positions.items():
                    # StockPositionItem에서 현재가 추출
                    if hasattr(pos_item, 'current_price') and pos_item.current_price:
                        current_prices[symbol] = float(pos_item.current_price)
                    # 전체 포지션 정보도 전달
                    account_positions[symbol] = {
                        "symbol": symbol,
                        "quantity": int(pos_item.quantity) if hasattr(pos_item, 'quantity') else 0,
                        "buy_price": float(pos_item.buy_price) if hasattr(pos_item, 'buy_price') else 0,
                        "current_price": float(pos_item.current_price) if hasattr(pos_item, 'current_price') else 0,
                        "pnl_rate": float(pos_item.pnl_rate) if hasattr(pos_item, 'pnl_rate') else 0,
                        "product": product,  # 상품 유형 (overseas_stock)
                    }

            asyncio.create_task(
                context.notify_workflow_pnl(
                    broker_node_id=node_id,
                    product=product,
                    provider=provider,
                    current_prices=current_prices,
                    account_positions=account_positions if account_positions else None,
                    currency=pnl_info.currency if hasattr(pnl_info, 'currency') else "USD",
                )
            )

        tracker.on_account_pnl_change(on_pnl_change)
        await tracker.start()
        
        # 활성 트래커 저장 (나중에 정리용)
        tracker_key = f"{context.job_id}_{node_id}"
        self._active_trackers[tracker_key] = {
            "tracker": tracker,
            "ls": ls,
            "real": real,
        }
        
        context.log("info", f"StockAccountTracker started for {node_id}", node_id)
    
    async def _start_overseas_futures_tracker(
        self,
        ls,
        node_id: str,
        product: str,
        provider: str,
        context: ExecutionContext,
    ) -> None:
        """해외선물 계좌 추적기 시작"""
        accno = ls.overseas_futureoption().accno()
        market = ls.overseas_futureoption().market()
        real = ls.overseas_futureoption().real()
        await real.connect()

        tracker = accno.account_tracker(
            market_client=market,
            real_client=real,
        )

        # 수익률 콜백 등록
        def on_pnl_change(pnl_info):
            # tracker에서 현재 positions 조회
            current_prices = {}
            account_positions = {}

            positions = tracker.get_positions()  # Dict[symbol, FuturesPositionItem]
            if positions:
                for symbol, pos_item in positions.items():
                    if hasattr(pos_item, 'current_price') and pos_item.current_price:
                        current_prices[symbol] = float(pos_item.current_price)
                    account_positions[symbol] = {
                        "symbol": symbol,
                        "quantity": int(pos_item.quantity) if hasattr(pos_item, 'quantity') else 0,
                        "buy_price": float(pos_item.entry_price) if hasattr(pos_item, 'entry_price') else 0,
                        "current_price": float(pos_item.current_price) if hasattr(pos_item, 'current_price') else 0,
                        "pnl_rate": float(pos_item.pnl_rate) if hasattr(pos_item, 'pnl_rate') else 0,
                        "side": pos_item.side if hasattr(pos_item, 'side') else "long",
                        "product": product,  # 상품 유형 (overseas_futures)
                    }

            asyncio.create_task(
                context.notify_workflow_pnl(
                    broker_node_id=node_id,
                    product=product,
                    provider=provider,
                    current_prices=current_prices,
                    account_positions=account_positions if account_positions else None,
                    currency=pnl_info.currency if hasattr(pnl_info, 'currency') else "USD",
                )
            )

        tracker.on_account_pnl_change(on_pnl_change)
        await tracker.start()
        
        tracker_key = f"{context.job_id}_{node_id}"
        self._active_trackers[tracker_key] = {
            "tracker": tracker,
            "ls": ls,
            "real": real,
            "market": market,
        }
        
        context.log("info", f"FuturesAccountTracker started for {node_id}", node_id)

    async def _start_korea_stock_tracker(
        self,
        ls,
        node_id: str,
        product: str,
        provider: str,
        context: ExecutionContext,
    ) -> None:
        """국내주식 계좌 추적기 시작"""
        accno = ls.korea_stock().accno()
        real = ls.korea_stock().real()
        await real.connect()

        tracker = accno.account_tracker(real_client=real)

        # 수익률 콜백 등록
        def on_pnl_change(pnl_info):
            # tracker에서 현재 positions 조회
            current_prices = {}
            account_positions = {}

            positions = tracker.get_positions()  # Dict[symbol, KrStockPositionItem]
            if positions:
                for symbol, pos_item in positions.items():
                    if pos_item.current_price:
                        current_prices[symbol] = float(pos_item.current_price)
                    account_positions[symbol] = {
                        "symbol": symbol,
                        "quantity": pos_item.quantity,
                        "buy_price": float(pos_item.buy_price),
                        "current_price": float(pos_item.current_price),
                        "pnl_rate": pos_item.pnl_rate,
                        "product": product,
                    }

            asyncio.create_task(
                context.notify_workflow_pnl(
                    broker_node_id=node_id,
                    product=product,
                    provider=provider,
                    current_prices=current_prices,
                    account_positions=account_positions if account_positions else None,
                    currency="KRW",
                )
            )

        tracker.on_account_pnl_change(on_pnl_change)
        await tracker.start()

        # 활성 트래커 저장 (나중에 정리용)
        tracker_key = f"{context.job_id}_{node_id}"
        self._active_trackers[tracker_key] = {
            "tracker": tracker,
            "ls": ls,
            "real": real,
        }

        context.log("info", f"KoreaStockAccountTracker started for {node_id}", node_id)

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

    Connection 획득:
    - product_scope + broker_provider 매칭으로 BrokerNode에서 자동 주입 (Phase 5)
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        # config에서 connection 확인 (자동 주입 또는 명시적 바인딩)
        broker_connection = config.get("connection")
        
        # connection 없으면 에러 - 자동 주입 또는 명시적 바인딩 필요
        if not broker_connection:
            context.log("error", "AccountNode: connection이 자동 주입되지 않았습니다. 매칭되는 BrokerNode가 워크플로우에 있는지 확인하세요.", node_id)
            return self._empty_result("Missing connection - no matching BrokerNode found in workflow")
        
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
                product=product,
                caller_name=f"AccountNode({product})"
            )
            if not success:
                return self._empty_result(error)
            
            # 상품별 REST API 호출
            if product == "overseas_stock":
                return await self._ls_overseas_stock(ls, node_id, context)
            elif product == "korea_stock":
                return await self._ls_korea_stock(ls, node_id, context)
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

        
        today = datetime.now().strftime("%Y%m%d")
        cosoq00201 = ls.overseas_stock().accno().cosoq00201(
            COSOQ00201.COSOQ00201InBlock1(
                RecCnt=1,
                BaseDt=today,
                CrcyCode="ALL",
                AstkBalTpCode="00",
            ),
        )
        
        response = await cosoq00201.req_async()
        
        if response.error_msg:
            context.log("error", f"API error: {response.error_msg}", node_id)
            return self._empty_result(response.error_msg)
        
        # block4 = 종목별 잔고 상세 (리스트 형태로 반환)
        positions = []
        for item in response.block4 or []:
            symbol = item.ShtnIsuNo.strip()
            if not symbol:
                continue

            positions.append({
                "symbol": symbol,
                "name": item.JpnMktHanglIsuNm.strip() if item.JpnMktHanglIsuNm else symbol,
                "qty": item.AstkBalQty,
                "quantity": item.AstkBalQty,  # NewOrderNode 호환
                "direction": "long",  # 주식은 보유=매수(long)
                "close_side": "sell",  # 청산=매도
                "avg_price": item.FcstckUprc,
                "current_price": item.OvrsScrtsCurpri,
                "pnl_rate": item.PnlRat,
                "pnl_amount": item.FcurrEvalPnlAmt,
                "currency": item.CrcyCode,
                "market": item.MktTpNm.strip() if item.MktTpNm else "",
                "exchange": item.MktTpNm.strip() if item.MktTpNm else "NASDAQ",  # NewOrderNode 호환
                "eval_amount": item.FcurrEvalAmt,
                "purchase_amount": item.FcurrBuyAmt,
            })

        held_symbols = [p["symbol"] for p in positions]
        
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
        
        # 2. COSOQ02701: 외화예수금/주문가능금액 조회 (graceful degradation)
        try:
            from programgarden_finance import COSOQ02701

            cosoq02701 = ls.overseas_stock().accno().cosoq02701(
                COSOQ02701.COSOQ02701InBlock1(RecCnt=1, CrcyCode="USD"),
            )
            cash_response = await cosoq02701.req_async()

            if not cash_response.error_msg:
                # block3: 국가별 외화 정보 (USD 기준)
                for item in cash_response.block3 or []:
                    if item.CrcyCode.strip() == "USD":
                        balance_info["orderable_amount"] = float(item.FcurrOrdAbleAmt) if item.FcurrOrdAbleAmt else 0.0
                        balance_info["foreign_cash"] = float(item.FcurrDps) if item.FcurrDps else 0.0
                        balance_info["exchange_rate"] = float(item.BaseXchrat) if item.BaseXchrat else 0.0
                        break

                # block4: 원화 출금/증거금
                if cash_response.block4:
                    balance_info["withdrawable_krw"] = float(cash_response.block4.MnyoutAbleAmt) if cash_response.block4.MnyoutAbleAmt else 0.0
                    balance_info["overseas_margin"] = float(cash_response.block4.OvrsMgn) if cash_response.block4.OvrsMgn else 0.0
            else:
                context.log("warning", f"COSOQ02701 조회 실패 (무시): {cash_response.error_msg}", node_id)
        except Exception as e:
            context.log("warning", f"COSOQ02701 조회 실패 (무시): {e}", node_id)

        context.log("info", f"AccountNode: {len(positions)} positions fetched", node_id)
        return {
            "positions": positions,
            "balance": balance_info,
        }

    async def _ls_korea_stock(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        LS증권 국내주식 잔고 조회

        - CSPAQ12300: 종목별 잔고내역 (보유종목, 평가손익)
        - CSPAQ22200: 예수금/주문가능금액
        """
        try:
            from programgarden_finance.ls.korea_stock.accno.CSPAQ12300.blocks import CSPAQ12300InBlock1
            from programgarden_finance.ls.korea_stock.accno.CSPAQ22200.blocks import CSPAQ22200InBlock1

            # 1. CSPAQ12300: 종목별 잔고내역
            response = await ls.korea_stock().accno().cspaq12300(
                body=CSPAQ12300InBlock1()
            ).req_async()

            positions = []
            balance_info = {
                "orderable_amount": 0.0,
                "deposit": 0.0,
                "total_eval": 0.0,
                "purchase_amount": 0.0,
                "eval_pnl": 0.0,
                "pnl_rate": 0.0,
            }

            if response.error_msg:
                context.log("warning", f"CSPAQ12300 조회 실패: {response.error_msg}", node_id)
            else:
                # block2: 잔고 요약
                if response.block2:
                    b2 = response.block2
                    balance_info["orderable_amount"] = float(b2.MnyOrdAbleAmt) if b2.MnyOrdAbleAmt else 0.0
                    balance_info["total_eval"] = float(b2.BalEvalAmt) if b2.BalEvalAmt else 0.0
                    balance_info["purchase_amount"] = float(b2.PchsAmt) if b2.PchsAmt else 0.0
                    balance_info["eval_pnl"] = float(b2.EvalPnl) if b2.EvalPnl else 0.0
                    balance_info["pnl_rate"] = float(b2.PnlRat) if b2.PnlRat else 0.0
                    balance_info["deposit"] = float(b2.Dps) if b2.Dps else 0.0

                # block3: 종목별 잔고 리스트
                for item in (response.block3 or []):
                    symbol = (item.IsuNo or "").strip()
                    # IsuNo가 A로 시작하면 앞자리 제거 (A005930 → 005930)
                    if symbol.startswith("A"):
                        symbol = symbol[1:]
                    if not symbol:
                        continue

                    qty = int(item.BalQty) if item.BalQty else 0
                    if qty <= 0:
                        continue

                    current_price = float(item.NowPrc) if item.NowPrc else 0.0
                    positions.append({
                        "symbol": symbol,
                        "exchange": "KRX",
                        "name": (item.IsuNm or "").strip(),
                        "quantity": qty,
                        "price": current_price,
                        "avg_price": float(item.AvrUprc) if item.AvrUprc else 0.0,
                        "current_price": current_price,
                        "pnl_amount": float(item.EvalPnl) if item.EvalPnl else 0.0,
                        "pnl_rate": float(item.PnlRat) if item.PnlRat else 0.0,
                        "sellable_qty": int(item.SellAbleQty) if item.SellAbleQty else 0,
                        "eval_amount": float(item.BalEvalAmt) if item.BalEvalAmt else 0.0,
                        "product": "korea_stock",
                    })

            # 2. CSPAQ22200: 예수금/주문가능금액
            try:
                cash_response = await ls.korea_stock().accno().cspaq22200(
                    body=CSPAQ22200InBlock1()
                ).req_async()

                if not cash_response.error_msg and cash_response.block2:
                    b2 = cash_response.block2
                    balance_info["orderable_amount"] = float(b2.MnyOrdAbleAmt) if b2.MnyOrdAbleAmt else balance_info["orderable_amount"]
                    balance_info["deposit"] = float(b2.Dps) if b2.Dps else balance_info["deposit"]
                    balance_info["d2_deposit"] = float(b2.D2Dps) if b2.D2Dps else 0.0
                    balance_info["margin_cash"] = float(b2.MgnMny) if b2.MgnMny else 0.0
                elif cash_response.error_msg:
                    context.log("warning", f"CSPAQ22200 조회 실패 (무시): {cash_response.error_msg}", node_id)
            except Exception as e:
                context.log("warning", f"CSPAQ22200 조회 실패 (무시): {e}", node_id)

            context.log("info", f"AccountNode (korea_stock): {len(positions)} positions fetched", node_id)
            return {
                "positions": positions,
                "balance": balance_info,
            }

        except Exception as e:
            context.log("error", f"Failed to fetch korea_stock positions: {e}", node_id)
            return self._empty_result(str(e))

    async def _ls_overseas_futureoption(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        LS증권 해외선물옵션 잔고 조회

        - CIDBQ01500: 미결제(보유) 포지션 조회
        - CIDBQ05300: 예탁자산 조회 (통화별, CIDBQ03000 상위호환)
        """
        from datetime import datetime

        try:
            from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01500.blocks import CIDBQ01500InBlock1
            from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ05300.blocks import CIDBQ05300InBlock1

            today = datetime.now().strftime("%Y%m%d")

            # 1. CIDBQ01500: 보유 포지션 조회
            response = await ls.overseas_futureoption().accno().CIDBQ01500(
                body=CIDBQ01500InBlock1(
                    RecCnt=1,
                    AcntTpCode="1",      # 1: 위탁
                    QryDt=today,         # 조회일자
                    BalTpCode="2",       # 1: 합산, 2: 건별 (건별이 더 안정적)
                    FcmAcntNo=""
                )
            ).req_async()

            # 응답 코드 확인 (00707: 조회할 내역 없음 - 정상)
            if response.rsp_cd and response.rsp_cd not in ["00000", "00136", "00707"]:
                context.log("warning", f"CIDBQ01500 response: {response.rsp_cd} - {response.rsp_msg}", node_id)

            # block2 = 종목별 잔고 (list 형태로 변환, NewOrderNode 호환)
            positions = []
            held_symbols = []
            for item in (response.block2 or []):
                symbol = item.IsuCodeVal.strip() if item.IsuCodeVal else ""
                if not symbol:
                    continue

                # BnsTpCode: 1=매도(short), 2=매수(long)
                is_long = item.BnsTpCode == "2"
                position_side = "long" if is_long else "short"
                close_side = "sell" if is_long else "buy"
                quantity = int(item.BalQty) if item.BalQty else 0
                current_price = float(item.OvrsDrvtNowPrc) if item.OvrsDrvtNowPrc else 0.0

                positions.append({
                    "symbol": symbol,
                    "exchange": "HKEX",  # 해외선물 기본 거래소
                    "name": item.IsuNm.strip() if hasattr(item, 'IsuNm') and item.IsuNm else symbol,
                    "direction": position_side,  # long/short
                    "close_side": close_side,  # 청산 시 주문 방향: sell/buy
                    "quantity": quantity,  # NewOrderNode 호환
                    "price": current_price,  # NewOrderNode 호환
                    "entry_price": float(item.PchsPrc) if item.PchsPrc else 0.0,
                    "current_price": current_price,
                    "pnl_amount": float(item.AbrdFutsEvalPnlAmt) if item.AbrdFutsEvalPnlAmt else 0.0,
                    "currency": item.CrcyCodeVal.strip() if item.CrcyCodeVal else "USD",
                })
                held_symbols.append(symbol)

            # 2. CIDBQ05300: 예탁자산 조회 (CIDBQ03000 상위호환)
            balance_response = await ls.overseas_futureoption().accno().CIDBQ05300(
                body=CIDBQ05300InBlock1(
                    RecCnt=1,
                    OvrsAcntTpCode="1",
                    CrcyCode="ALL"
                )
            ).req_async()

            # block2: 통화별 예수금 정보
            balance_by_currency = {}
            total_orderable = 0.0
            for item in (balance_response.block2 or []):
                currency = item.CrcyCode.strip() if item.CrcyCode else "USD"
                orderable = float(item.AbrdFutsOrdAbleAmt) if item.AbrdFutsOrdAbleAmt else 0.0
                deposit = float(item.OvrsFutsDps) if item.OvrsFutsDps else 0.0

                balance_by_currency[currency] = {
                    "deposit": deposit,
                    "orderable_amount": orderable,
                    "withdrawable_amount": float(item.AbrdFutsWthdwAbleAmt) if item.AbrdFutsWthdwAbleAmt else 0.0,
                    "eval_pnl": float(item.AbrdFutsEvalPnlAmt) if item.AbrdFutsEvalPnlAmt else 0.0,
                }
                total_orderable += orderable

            # balance 정보 구성 (PositionSizingNode 호환)
            balance_info = {
                "by_currency": balance_by_currency,
                "total_orderable": total_orderable,
                # 하위 호환성: 첫 번째 통화 또는 USD 기준
                "orderable_amount": balance_by_currency.get("USD", {}).get("orderable_amount", 0.0) or total_orderable,
                "deposit": sum(b.get("deposit", 0) for b in balance_by_currency.values()),
            }

            # block3: 전체 요약 (증거금/마진콜율 등)
            if balance_response.block3:
                b3 = balance_response.block3
                balance_info["margin"] = float(b3.AbrdFutsCsgnMgn) if b3.AbrdFutsCsgnMgn else 0.0
                balance_info["maintenance_margin"] = float(b3.OvrsFutsMaintMgn) if b3.OvrsFutsMaintMgn else 0.0
                balance_info["margin_call_rate"] = float(b3.MgnclRat) if b3.MgnclRat else 0.0
                balance_info["total_eval"] = float(b3.AbrdFutsEvalDpstgTotAmt) if b3.AbrdFutsEvalDpstgTotAmt else 0.0
                balance_info["settlement_pnl"] = float(b3.AbrdFutsLqdtPnlAmt) if b3.AbrdFutsLqdtPnlAmt else 0.0

            context.log("info", f"AccountNode (futures): {len(positions)} positions, {len(balance_by_currency)} currencies", node_id)
            return {
                "positions": positions,
                "balance": balance_info,
            }
            
        except Exception as e:
            context.log("error", f"Failed to fetch futures positions: {e}", node_id)
            return self._empty_result(str(e))

    def _empty_result(self, error: str = "") -> Dict[str, Any]:
        """빈 결과 반환 (positions는 리스트 형태)"""
        result = {
            "positions": [],
            "balance": {"cash": 0.0, "total_value": 0.0},
        }
        if error:
            result["error"] = error
        return result


class OpenOrdersNodeExecutor(NodeExecutorBase):
    """
    미체결 주문 조회 Executor (REST API 1회성)

    지원 노드:
    - OverseasStockOpenOrdersNode: 해외주식 미체결 조회 (COSAQ00102)
    - OverseasFuturesOpenOrdersNode: 해외선물 미체결 조회 (CIDBQ02400)

    출력:
    - open_orders: 미체결 주문 리스트
    - count: 미체결 주문 수
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        # config에서 connection 확인 (자동 주입)
        broker_connection = config.get("connection")

        if not broker_connection:
            context.log("error", f"{node_type}: connection이 자동 주입되지 않았습니다.", node_id)
            return self._empty_result("Missing connection")

        if isinstance(broker_connection, dict):
            provider = broker_connection.get("provider", "ls-sec.co.kr")
            product = config.get("product_type") or broker_connection.get("product", "overseas_stock")
        else:
            context.log("error", f"{node_type}: connection 타입이 잘못되었습니다.", node_id)
            return self._empty_result("Invalid connection type")

        context.log("info", f"{node_type}: provider={provider}, product={product}", node_id)

        if provider == "ls-sec.co.kr":
            return await self._execute_ls(node_id, node_type, product, context)
        else:
            context.log("error", f"Unsupported provider: {provider}", node_id)
            return self._empty_result(f"Unsupported provider: {provider}")

    async def _execute_ls(
        self,
        node_id: str,
        node_type: str,
        product: str,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """LS증권 미체결 조회"""
        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not found", node_id)
            return self._empty_result("Missing credentials")

        appkey = credential.get("appkey")
        appsecret = credential.get("appsecret")
        paper_trading = credential.get("paper_trading", False)

        if not appkey or not appsecret:
            context.log("error", "appkey/appsecret not found", node_id)
            return self._empty_result("Missing appkey/appsecret")

        try:
            ls, success, error = ensure_ls_login(
                appkey, appsecret, paper_trading, context, node_id,
                product=product,
                caller_name=node_type
            )
            if not success:
                return self._empty_result(error)

            if product == "overseas_stock":
                return await self._ls_overseas_stock(ls, node_id, context)
            elif product in ("overseas_futures", "overseas_futureoption"):
                return await self._ls_overseas_futures(ls, node_id, context)
            elif product == "korea_stock":
                return await self._ls_korea_stock(ls, node_id, context)
            else:
                context.log("warning", f"Unsupported product: {product}", node_id)
                return self._empty_result(f"Unsupported product: {product}")

        except Exception as e:
            context.log("error", f"Unexpected error: {e}", node_id)
            return self._empty_result(str(e))

    async def _ls_korea_stock(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """국내주식 미체결 조회 (t0425)"""
        try:
            from programgarden_finance.ls.korea_stock.accno.t0425.blocks import T0425InBlock

            response = await ls.korea_stock().accno().t0425(
                body=T0425InBlock(
                    expcode="",      # 빈값: 전체 종목
                    chegb="2",       # 2: 미체결
                    medosu="0",      # 0: 전체
                    sortgb="1",      # 1: 주문번호 역순
                    cts_ordno="",
                )
            ).req_async()

            if response.error_msg:
                context.log("error", f"t0425 error: {response.error_msg}", node_id)
                return self._empty_result(response.error_msg)

            open_orders = []
            # T0425Response.block (T0425OutBlock1 리스트)
            for item in response.block or []:
                order_id = str(item.ordno) if item.ordno else ""
                if not order_id:
                    continue

                # 미체결잔량이 0이면 완료된 주문
                remaining = int(item.ordrem) if item.ordrem else 0
                if remaining <= 0:
                    continue

                side = "buy" if "매수" in (item.medosu or "") else "sell"

                open_orders.append({
                    "order_id": order_id,
                    "exchange": "KRX",
                    "symbol": (item.expcode or "").strip(),
                    "name": "",
                    "side": side,
                    "order_type": (item.hogagb or "").strip(),
                    "quantity": int(item.qty) if item.qty else 0,
                    "filled_quantity": int(item.cheqty) if item.cheqty else 0,
                    "remaining_quantity": remaining,
                    "price": float(item.price) if item.price else 0.0,
                    "order_time": (item.ordtime or "").strip(),
                })

            context.log("info", f"OpenOrdersNode (korea_stock): {len(open_orders)} open orders", node_id)
            return {
                "open_orders": open_orders,
                "count": len(open_orders),
            }

        except Exception as e:
            context.log("error", f"Korea stock open orders error: {e}", node_id)
            return self._empty_result(str(e))

    async def _ls_overseas_stock(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """해외주식 미체결 조회 (COSAQ00102)"""
        from datetime import datetime
        from programgarden_finance.ls.overseas_stock.accno.COSAQ00102.blocks import COSAQ00102InBlock1


        today = datetime.now().strftime("%Y%m%d")

        response = await ls.overseas_stock().accno().cosaq00102(
            COSAQ00102InBlock1(
                RecCnt=1,
                QryTpCode="1",      # 1: 역순
                BkseqTpCode="1",    # 1: 역순
                OrdMktCode="00",    # 00: 전체
                BnsTpCode="0",      # 0: 전체
                IsuNo="",           # 빈값: 전체 종목
                SrtOrdNo=999999999,
                OrdDt=today,
                ExecYn="2",         # 2: 미체결
                CrcyCode="000",     # 000: 전체 통화
                ThdayBnsAppYn="0",
                LoanBalHldYn="0"
            ),
        ).req_async()

        if response.error_msg:
            context.log("error", f"COSAQ00102 error: {response.error_msg}", node_id)
            return self._empty_result(response.error_msg)

        open_orders = []
        for item in response.block3 or []:
            order_id = str(item.OrdNo) if item.OrdNo else ""
            if not order_id:
                continue

            # BnsTpCode: 01=매도, 02=매수
            side = "buy" if item.BnsTpCode == "02" else "sell"

            open_orders.append({
                "order_id": order_id,
                "exchange": item.OrdMktCode or "",
                "symbol": item.ShtnIsuNo.strip() if item.ShtnIsuNo else (item.IsuNo.strip() if item.IsuNo else ""),
                "name": item.JpnMktHanglIsuNm.strip() if item.JpnMktHanglIsuNm else "",
                "side": side,
                "order_type": "limit",  # 해외주식은 대부분 지정가
                "quantity": int(item.OrdQty) if item.OrdQty else 0,
                "filled_quantity": int(item.ExecQty) if item.ExecQty else 0,
                "remaining_quantity": int(item.UnercQty) if item.UnercQty else 0,
                "price": float(item.OvrsOrdPrc) if item.OvrsOrdPrc else 0.0,
                "order_time": item.OrdTime if item.OrdTime else "",
            })

        context.log("info", f"OpenOrdersNode (stock): {len(open_orders)} open orders", node_id)
        return {
            "open_orders": open_orders,
            "count": len(open_orders),
        }

    async def _ls_overseas_futures(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """해외선물 미체결 조회 (CIDBQ02400)"""
        from datetime import datetime
        from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ02400.blocks import CIDBQ02400InBlock1


        today = datetime.now().strftime("%Y%m%d")

        response = await ls.overseas_futureoption().accno().CIDBQ02400(
            body=CIDBQ02400InBlock1(
                RecCnt=1,
                IsuCodeVal="",          # 빈값: 전체 종목
                QrySrtDt=today,
                QryEndDt=today,
                ThdayTpCode="0",        # 0: 전체
                OrdStatCode="2",        # 2: 미체결
                BnsTpCode="0",          # 0: 전체
                QryTpCode="2",          # 2: 역순
                OrdPtnCode="00",        # 00: 전체
                OvrsDrvtFnoTpCode="A"   # A: 전체
            )
        ).req_async()

        # 응답 코드 확인
        if response.rsp_cd and response.rsp_cd not in ["00000", "00136", "00707"]:
            context.log("warning", f"CIDBQ02400 response: {response.rsp_cd} - {response.rsp_msg}", node_id)

        open_orders = []
        for item in response.block2 or []:
            # 해외선물 주문번호는 OvrsFutsOrdNo
            order_id = str(item.OvrsFutsOrdNo) if hasattr(item, 'OvrsFutsOrdNo') and item.OvrsFutsOrdNo else ""
            if not order_id:
                continue

            # BnsTpCode: 1=매도, 2=매수
            side = "buy" if item.BnsTpCode == "2" else "sell"

            order_qty = int(item.OrdQty) if hasattr(item, 'OrdQty') and item.OrdQty else 0
            exec_qty = int(item.ExecQty) if hasattr(item, 'ExecQty') and item.ExecQty else 0
            unerc_qty = int(item.UnercQty) if hasattr(item, 'UnercQty') and item.UnercQty else 0

            open_orders.append({
                "order_id": order_id,
                "exchange": "HKEX",  # 해외선물 기본
                "symbol": item.IsuCodeVal.strip() if hasattr(item, 'IsuCodeVal') and item.IsuCodeVal else "",
                "name": item.IsuNm.strip() if hasattr(item, 'IsuNm') and item.IsuNm else "",
                "side": side,
                "order_type": "limit",
                "quantity": order_qty,
                "filled_quantity": exec_qty,
                "remaining_quantity": unerc_qty,
                "price": float(item.OvrsDrvtOrdPrc) if hasattr(item, 'OvrsDrvtOrdPrc') and item.OvrsDrvtOrdPrc else 0.0,
                "order_time": item.OrdSndDttm if hasattr(item, 'OrdSndDttm') else "",
            })

        context.log("info", f"OpenOrdersNode (futures): {len(open_orders)} open orders", node_id)
        return {
            "open_orders": open_orders,
            "count": len(open_orders),
        }

    def _empty_result(self, error: str = "") -> Dict[str, Any]:
        """빈 결과 반환"""
        result = {
            "open_orders": [],
            "count": 0,
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

        # dry_run: WebSocket 미개방, skip 반환
        if context.is_dry_run:
            context.log(
                "warning",
                f"[dry_run] {node_type} skipped (realtime WebSocket disabled)",
                node_id,
            )
            return {"status": "skipped_dry_run", "dry_run": True}

        # 옵션 확인
        stay_connected = config.get("stay_connected", True)
        sync_interval_sec = config.get("sync_interval_sec", 60)


        # config에서 connection 확인 (자동 주입 또는 명시적 바인딩)
        broker_connection = config.get("connection")

        # connection 없으면 에러 - 자동 주입 또는 명시적 바인딩 필요
        if not broker_connection:
            context.log("error", "RealAccountNode: connection이 자동 주입되지 않았습니다. 매칭되는 BrokerNode가 워크플로우에 있는지 확인하세요.", node_id)
            return {"error": "Missing connection - no matching BrokerNode found in workflow"}
        
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
                product=product,
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
        elif product == "korea_stock":
            return await self._ls_korea_stock_with_tracker(
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
                        await reconnect_handler.on_reconnect_success()
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
                if context.is_shutdown:
                    return
                # 포지션 데이터를 list 형태로 변환 (NewOrderNode 호환)
                serialized_positions = []
                for sym, pos in positions.items():
                    quantity = pos.quantity
                    current_price = float(pos.current_price)
                    serialized_positions.append({
                        "symbol": sym,
                        "exchange": getattr(pos, 'market_code', 'NASDAQ'),
                        "name": getattr(pos, 'symbol_name', sym),
                        "quantity": quantity,  # NewOrderNode 호환
                        "price": current_price,  # NewOrderNode 호환
                        "avg_price": float(pos.buy_price),
                        "current_price": current_price,
                        "pnl_rate": float(pos.pnl_rate) if pos.pnl_rate else 0,
                        "pnl_amount": float(pos.pnl_amount) if pos.pnl_amount else 0,
                        "currency": getattr(pos, 'currency_code', 'USD'),
                        "product": "overseas_stock",  # 상품 유형
                    })

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
            result = self._get_overseas_stock_tracker_data(tracker)
            
            # 데이터가 비어있는지 확인 (에러 없이 정상 케이스)
            positions_count = len(result.get('positions', []))
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
            for pos in result.get('positions', []):
                sym = pos.get('symbol', '')
                logger.debug(f"  - {sym}: 수량={pos.get('qty')}, 평단가=${pos.get('avg_price', 0):.2f}, 현재가=${pos.get('current_price', 0):.2f}, 수익률={pos.get('pnl_rate', 0):.2f}%")
            logger.debug(f"{'='*60}\n")

            context.log("info", f"Initial account data loaded: {len(result.get('positions', []))} positions", node_id)
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
                        await reconnect_handler.on_reconnect_success()
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
                if context.is_shutdown:
                    return
                # 포지션 데이터를 list 형태로 변환 (NewOrderNode 호환, position_data 컨벤션)
                serialized_positions = []
                for sym, pos in positions.items():
                    # realtime_pnl이 None이 아닌 경우만 안전하게 접근
                    realtime_pnl = getattr(pos, 'realtime_pnl', None)
                    pnl_rate = 0.0
                    if realtime_pnl is not None and hasattr(realtime_pnl, 'pnl_rate'):
                        pnl_rate = float(getattr(realtime_pnl, 'pnl_rate', 0) or 0)
                    elif hasattr(pos, 'pnl_rate') and pos.pnl_rate is not None:
                        pnl_rate = float(pos.pnl_rate)

                    is_long = getattr(pos, 'is_long', True)
                    quantity = int(getattr(pos, 'quantity', 0))
                    current_price = float(getattr(pos, 'current_price', 0))
                    serialized_positions.append({
                        "symbol": sym,
                        "exchange": getattr(pos, 'exchange_code', ''),
                        "name": getattr(pos, 'symbol_name', sym),
                        "direction": "long" if is_long else "short",
                        "close_side": "sell" if is_long else "buy",
                        "qty": quantity,
                        "quantity": quantity,  # NewOrderNode 호환
                        "price": current_price,  # NewOrderNode 호환
                        "entry_price": float(getattr(pos, 'entry_price', 0)),
                        "current_price": current_price,
                        "pnl_amount": float(getattr(pos, 'pnl_amount', 0) or 0),
                        "pnl_rate": pnl_rate,
                        "currency": getattr(pos, 'currency', 'USD'),
                        "product": "overseas_futures",  # 상품 유형
                    })
                
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
                if context.is_shutdown:
                    return
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
            result = self._get_overseas_futures_tracker_data(tracker)
            
            # 데이터가 비어있는지 확인 (에러 없이 정상 케이스)
            positions_count = len(result.get('positions', []))
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
            for pos in result.get('positions', []):
                sym = pos.get('symbol', '')
                direction = '롱' if pos.get('direction') == 'long' else '숏'
                logger.debug(f"  - {sym} ({direction}): 수량={pos.get('quantity')}, 진입가=${pos.get('entry_price', 0):.2f}, 현재가=${pos.get('current_price', 0):.2f}, 손익=${pos.get('pnl_amount', 0):.2f}")
            logger.debug(f"미체결: {list(result.get('open_orders', {}).keys())}")
            logger.debug(f"{'='*60}\n")

            context.log("info", f"Initial futures data loaded: {len(result.get('positions', []))} positions", node_id)
            return result
            
        except Exception as e:
            context.log("error", f"Futures tracker setup failed: {e}", node_id)
            raise

    async def _ls_korea_stock_with_tracker(
        self,
        ls,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        sync_interval_sec: int,
        stay_connected: bool = True,
    ) -> Dict[str, Any]:
        """국내주식 실시간 계좌 추적 (KrStockAccountTracker)"""
        from decimal import Decimal

        try:
            commission_rate = Decimal(str(config.get("commission_rate", 0.015))) / 100

            context.log("info", f"Korea stock commission rate: {float(commission_rate)*100:.3f}%", node_id)

            real_client = ls.korea_stock().real()
            if not await real_client.is_connected():
                await real_client.connect()

            tracker = ls.korea_stock().accno().account_tracker(
                real_client=real_client,
                refresh_interval=sync_interval_sec,
                commission_rate=commission_rate,
            )

            token_manager = ls._token_manager if hasattr(ls, '_token_manager') else None
            reconnect_handler = ReconnectHandler(token_manager)

            async def on_disconnect():
                can_retry = await reconnect_handler.handle_disconnect()
                if can_retry:
                    try:
                        if not await real_client.is_connected():
                            await real_client.connect()
                        await reconnect_handler.on_reconnect_success()
                        context.log("info", "Korea stock reconnected successfully", node_id)
                    except Exception as e:
                        context.log("error", f"Korea stock reconnect failed: {e}", node_id)
                        await on_disconnect()
                else:
                    context.fail(f"Max reconnect attempts exceeded for {node_id}")

            trigger_nodes = config.get("_trigger_on_update_nodes", [])
            loop = asyncio.get_running_loop()

            def on_position_change(positions: Dict):
                if context.is_shutdown:
                    return
                serialized_positions = []
                for sym, pos in positions.items():
                    quantity = pos.quantity
                    current_price = float(pos.current_price)
                    serialized_positions.append({
                        "symbol": sym,
                        "exchange": "KRX",
                        "name": getattr(pos, 'symbol_name', sym),
                        "quantity": quantity,
                        "price": current_price,
                        "avg_price": float(pos.buy_price),
                        "current_price": current_price,
                        "pnl_rate": float(pos.pnl_rate) if pos.pnl_rate else 0,
                        "pnl_amount": float(pos.pnl_amount) if pos.pnl_amount else 0,
                        "product": "korea_stock",
                    })

                context.set_output(node_id, "positions", serialized_positions)

                asyncio.run_coroutine_threadsafe(
                    context.notify_output_update(
                        node_id=node_id,
                        node_type="KoreaStockRealAccountNode",
                        outputs={"positions": serialized_positions},
                    ),
                    loop
                )

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
            await tracker.start()

            tracker_errors = tracker.get_last_errors()
            if tracker_errors:
                for error_key, error_msg in tracker_errors.items():
                    context.log("error", f"증권사 API 오류 ({error_key}): {error_msg}", node_id)
                error_summary = ", ".join(tracker_errors.values())
                raise RuntimeError(f"KoreaStockRealAccountNode 초기화 실패: {error_summary}")

            if stay_connected:
                context.register_persistent(node_id, tracker)
                context.log("info", f"KrStockAccountTracker started (stay_connected=True, sync_interval={sync_interval_sec}s)", node_id)
            else:
                context.register_cleanup_on_flow_end(node_id, tracker)
                context.log("info", f"KrStockAccountTracker started (stay_connected=False)", node_id)

            result = self._get_korea_stock_tracker_data(tracker)

            for key, value in result.items():
                context.set_output(node_id, key, value)

            asyncio.create_task(context.notify_output_update(
                node_id=node_id,
                node_type="KoreaStockRealAccountNode",
                outputs=result,
            ))

            context.log("info", f"Korea stock initial data: {len(result.get('positions', []))} positions", node_id)
            return result

        except Exception as e:
            context.log("error", f"Korea stock tracker setup failed: {e}", node_id)
            raise

    def _get_overseas_stock_tracker_data(self, tracker) -> Dict[str, Any]:
        """해외주식 Tracker에서 현재 데이터 추출 (리스트 형태로 반환)"""
        positions = []
        for symbol, pos in tracker.get_positions().items():
            positions.append({
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
            })

        symbols = [p["symbol"] for p in positions]
        
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
            "positions": positions,
            "balance": balance,
            "open_orders": open_orders,
        }

    def _get_overseas_futures_tracker_data(self, tracker) -> Dict[str, Any]:
        """해외선물 Tracker에서 현재 데이터 추출

        positions 출력 형식: list[dict]
        - POSITION_FIELDS 스키마와 일치
        - NewOrderNode orders 배열과 호환 (qty→quantity 매핑 필요)
        """
        positions = []
        symbols = []
        for symbol, pos in tracker.get_positions().items():
            # realtime_pnl이 None이 아닌 dict인 경우만 .get() 호출
            realtime_pnl = getattr(pos, 'realtime_pnl', None)
            pnl_rate = 0.0
            if realtime_pnl is not None and hasattr(realtime_pnl, 'pnl_rate'):
                pnl_rate = float(getattr(realtime_pnl, 'pnl_rate', 0) or 0)
            elif hasattr(pos, 'pnl_rate') and pos.pnl_rate is not None:
                pnl_rate = float(pos.pnl_rate)

            is_long = getattr(pos, 'is_long', True)
            quantity = int(getattr(pos, 'quantity', 0))
            current_price = float(getattr(pos, 'current_price', 0))

            positions.append({
                "symbol": symbol,
                "exchange": getattr(pos, 'exchange_code', ''),
                "name": getattr(pos, 'symbol_name', symbol),
                "direction": "long" if is_long else "short",
                "close_side": "sell" if is_long else "buy",
                "quantity": quantity,  # qty → quantity (NewOrderNode 호환)
                "price": current_price,  # current_price → price (NewOrderNode 호환)
                "entry_price": float(getattr(pos, 'entry_price', 0)),
                "current_price": current_price,
                "pnl_amount": float(getattr(pos, 'pnl_amount', 0) or 0),
                "pnl_rate": pnl_rate,
                "currency": getattr(pos, 'currency', 'USD'),
            })
            symbols.append(symbol)
        
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
                    "direction": "long" if is_long else "short",
                    "close_side": "sell" if is_long else "buy",
                    "order_price": float(getattr(order, 'order_price', 0)),
                    "order_qty": int(getattr(order, 'order_qty', 0)),
                    "remaining_qty": int(getattr(order, 'remaining_qty', 0)),
                }
        
        return {
            "positions": positions,
            "balance": balance,
            "open_orders": open_orders,
        }

    def _get_korea_stock_tracker_data(self, tracker) -> Dict[str, Any]:
        """국내주식 KrStockAccountTracker에서 현재 데이터 추출"""
        positions = []
        for symbol, pos in tracker.get_positions().items():
            positions.append({
                "symbol": symbol,
                "name": getattr(pos, 'symbol_name', symbol),
                "qty": pos.quantity,
                "avg_price": float(pos.buy_price),
                "current_price": float(pos.current_price),
                "pnl_rate": pos.pnl_rate,
                "pnl_amount": float(pos.pnl_amount),
                "currency": "KRW",
                "eval_amount": float(pos.eval_amount),
                "market_code": getattr(pos, 'market', ''),
            })

        # KrStockAccountTracker.get_balance() → KrStockBalanceInfo (단일 객체)
        raw_balance = tracker.get_balance()
        balance = {}
        if raw_balance:
            balance["KRW"] = {
                "deposit": float(raw_balance.deposit),
                "orderable_amount": float(raw_balance.orderable_amount),
                "d1_deposit": float(raw_balance.d1_deposit),
                "d2_deposit": float(raw_balance.d2_deposit),
            }
            balance["_summary"] = {
                "total_deposit": float(raw_balance.deposit),
            }
        else:
            balance = {"cash": 0.0, "total_value": 0.0}

        # open_orders 추출
        open_orders = {}
        if hasattr(tracker, 'get_open_orders'):
            for order_no, order in tracker.get_open_orders().items():
                open_orders[str(order_no)] = {
                    "order_no": order_no,
                    "symbol": getattr(order, 'symbol', ''),
                    "exchange": "KRX",
                    "order_type": getattr(order, 'order_type', ''),
                    "order_price": float(getattr(order, 'order_price', 0)),
                    "order_qty": int(getattr(order, 'order_qty', 0)),
                    "filled_qty": int(getattr(order, 'executed_qty', 0)),
                    "remaining_qty": int(getattr(order, 'remaining_qty', 0)),
                }

        return {
            "positions": positions,
            "balance": balance,
            "open_orders": open_orders,
        }

    def _get_tracker_data(self, tracker) -> Dict[str, Any]:
        """Tracker에서 현재 데이터 추출 (하위 호환용)"""
        # 타입에 따라 분기
        tracker_type = type(tracker).__name__
        if "Futures" in tracker_type:
            return self._get_overseas_futures_tracker_data(tracker)
        elif "KrStock" in tracker_type:
            return self._get_korea_stock_tracker_data(tracker)
        else:
            return self._get_overseas_stock_tracker_data(tracker)

    def _empty_result(self, error: str = "") -> Dict[str, Any]:
        """빈 결과 반환"""
        result = {
            "positions": [],
            "balance": {"cash": 0.0, "total_value": 0.0},
            "open_orders": {},
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

        # dry_run: WebSocket 미개방, skip 반환
        if context.is_dry_run:
            context.log(
                "warning",
                f"[dry_run] {node_type} skipped (realtime WebSocket disabled)",
                node_id,
            )
            return {"status": "skipped_dry_run", "dry_run": True}

        # ========================================
        # 1. BrokerNode connection 획득 (config 바인딩 필수)
        # ========================================
        broker_connection = config.get("connection")

        # connection 없으면 에러 - 자동 주입 또는 명시적 바인딩 필요
        if not broker_connection:
            error_msg = (
                f"RealMarketDataNode: connection이 자동 주입되지 않았습니다. "
                f"매칭되는 BrokerNode가 워크플로우에 있는지 확인하세요."
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
        elif broker_product == "korea_stock":
            return await self._execute_korea_stock(
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
        """해외주식 실시간 시세 (GSC)

        GSC(체결) TR만 구독합니다. GSH(호가)는 구독하지 않습니다.
        사유: LS증권 해외주식 API 제약으로 GSH의 개별 호가단계 잔량(offerrem2~10,
        bidrem2~10)이 항상 0이며, 총잔량만 1단계에 합산되어 제공됩니다.
        건수(offerno/bidno)도 항상 0입니다.
        개별 호가 잔량이 필요한 경우 REST API(g3106)를 사용하세요.
        (해외선물/국내주식 실시간 호가는 정상 제공됨)
        """
        import asyncio
        from datetime import datetime
        
        appkey = broker_connection.get("appkey", "")
        appsecret = broker_connection.get("appsecret", "")
        paper_trading = broker_connection.get("paper_trading", False)
        
        # 현재 이벤트 루프 캡처 (콜백에서 사용)
        loop = asyncio.get_running_loop()
        
        # LS 로그인
        ls, success, error = ensure_ls_login(appkey, appsecret, paper_trading, context, node_id, "overseas_stock")
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
        
        # M-11: OHLCV 데이터를 context.node_state에 저장 (클로저 메모리 관리)
        # cleanup_persistent_nodes에서 자동 정리됨
        context.set_node_state(node_id, "ohlcv_bars", {})

        # 트리거할 하위 노드 목록 (RealOrderEventNode 패턴)
        trigger_nodes = []

        def on_tick(resp):
            """GSC 틱 데이터 수신 콜백 - OHLCV 형식으로 누적"""
            try:
                if context.is_shutdown:
                    return
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
                    # M-11: context state에서 ohlcv_bars 조회/갱신
                    ohlcv_bars = context.get_node_state(node_id, "ohlcv_bars") or {}

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

                    context.set_node_state(node_id, "ohlcv_bars", ohlcv_bars)

                    # 콘솔 출력
                    logger.debug(f"\n{'='*60}")
                    logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] [{node_id}] GSC tick")
                    logger.debug(f"  symbol: {symbol}  price: ${price:,.2f}  volume: {volume:,}")
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
        ls, success, error = ensure_ls_login(appkey, appsecret, paper_trading, context, node_id, "overseas_futures")
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
                if context.is_shutdown:
                    return
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

    async def _execute_korea_stock(
        self,
        node_id: str,
        broker_connection: Dict[str, Any],
        symbols: List[str],
        symbols_with_exchange: List[Dict[str, str]],
        symbols_raw: List,
        stay_connected: bool,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """국내주식 실시간 시세 (S3_: KOSPI체결, K3_: KOSDAQ체결)"""
        import asyncio
        from datetime import datetime

        appkey = broker_connection.get("appkey", "")
        appsecret = broker_connection.get("appsecret", "")

        loop = asyncio.get_running_loop()

        ls, success, error = ensure_ls_login(appkey, appsecret, False, context, node_id, "korea_stock")
        if not success:
            from programgarden_core.exceptions import ConnectionError
            raise ConnectionError(f"LS login failed: {error}")

        real_client = ls.korea_stock().real()
        await real_client.connect()
        context.log("info", f"WebSocket connected for korea_stock", node_id)

        # OHLCV 데이터 저장
        context.set_node_state(node_id, "ohlcv_bars", {})
        trigger_nodes = []

        # S3_ (KOSPI체결) 구독
        s3 = real_client.S3_()

        def on_tick(resp):
            """S3_/K3_ 틱 데이터 수신 콜백"""
            try:
                if context.is_shutdown:
                    return
                body = resp.body if hasattr(resp, 'body') else None
                if body is None:
                    return

                symbol = getattr(body, 'shcode', '')
                price = int(getattr(body, 'price', 0) or 0)
                tick_open = int(getattr(body, 'open', 0) or 0)
                tick_high = int(getattr(body, 'high', 0) or 0)
                tick_low = int(getattr(body, 'low', 0) or 0)
                volume = int(getattr(body, 'volume', 0) or 0)
                date = datetime.now().strftime('%Y%m%d')

                if symbol and price > 0:
                    ohlcv_bars = context.get_node_state(node_id, "ohlcv_bars") or {}

                    if symbol not in ohlcv_bars or ohlcv_bars[symbol].get('date') != date:
                        ohlcv_bars[symbol] = {
                            "date": date,
                            "open": tick_open if tick_open > 0 else price,
                            "high": tick_high if tick_high > 0 else price,
                            "low": tick_low if tick_low > 0 else price,
                            "close": price,
                            "volume": volume,
                        }
                    else:
                        bar = ohlcv_bars[symbol]
                        if tick_high > 0:
                            bar["high"] = tick_high
                        if tick_low > 0:
                            bar["low"] = tick_low
                        bar["close"] = price
                        bar["volume"] = volume

                    context.set_node_state(node_id, "ohlcv_bars", ohlcv_bars)

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
                            node_type="KoreaStockRealMarketDataNode",
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
                context.log("warning", f"Korea stock tick parse error: {e}", node_id)

        s3.on_s3__message(on_tick)

        # K3_ (KOSDAQ체결)도 동일 콜백
        k3 = real_client.K3_()
        k3.on_k3__message(on_tick)

        # 종목 구독 (6자리 종목코드)
        subscribe_symbols = [s for s in symbols if s]
        s3.add_s3__symbols(symbols=subscribe_symbols)
        k3.add_k3__symbols(symbols=subscribe_symbols)
        context.log("info", f"Subscribed to S3_/K3_: {subscribe_symbols}", node_id)

        if not stay_connected:
            context.log("warning", f"stay_connected=False for realtime node", node_id)
            s3.remove_s3__symbols(symbols=subscribe_symbols)
            k3.remove_k3__symbols(symbols=subscribe_symbols)
            await real_client.close()
        else:
            context.register_persistent(node_id, real_client)
            context.set_node_state(node_id, "s3", s3)
            context.set_node_state(node_id, "k3", k3)
            context.set_node_state(node_id, "subscribe_symbols", subscribe_symbols)
            context.log("info", f"S3_/K3_ subscription active - waiting for ticks...", node_id)

        return {
            "symbols": symbols_raw,
            "ohlcv_data": {},
            "data": {},
        }

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
        for account_type in (
            "RealAccountNode",
            "OverseasStockRealAccountNode",
            "OverseasFuturesRealAccountNode",
            "AccountNode",
            "OverseasStockAccountNode",
            "OverseasFuturesAccountNode",
        ):
            account_output = context.find_parent_output(node_id, account_type)
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
        # dry_run: WebSocket 미개방, skip 반환
        if context.is_dry_run:
            context.log(
                "warning",
                f"[dry_run] {node_type} skipped (realtime WebSocket disabled)",
                node_id,
            )
            return {"status": "skipped_dry_run", "dry_run": True}

        # 옵션 확인
        stay_connected = config.get("stay_connected", True)

        # config에서 connection 확인 (자동 주입 또는 명시적 바인딩)
        broker_connection = config.get("connection")

        # connection 없으면 에러 - 자동 주입 또는 명시적 바인딩 필요
        if not broker_connection:
            context.log("error", "RealOrderEventNode: connection이 자동 주입되지 않았습니다. 매칭되는 BrokerNode가 워크플로우에 있는지 확인하세요.", node_id)
            return {"error": "Missing connection - no matching BrokerNode found in workflow"}
        
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
                product=product,
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
            elif product == "korea_stock":
                return await self._ls_korea_stock_order_event(
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
                    if context.is_shutdown:
                        return
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
                    
                    # 체결 이벤트('11')일 때 시장가 주문의 가격 업데이트
                    if ord_type_code == '11' and event_data['order_price'] > 0:
                        order_no_str = str(event_data['order_no'])
                        order_date = getattr(body, 'sOrdDt', datetime.now().strftime('%Y%m%d'))
                        context.update_workflow_order_fill_price(
                            order_no=order_no_str,
                            order_date=order_date,
                            fill_price=event_data['order_price'],
                        )
                    
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
                    if context.is_shutdown:
                        return
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
                    if context.is_shutdown:
                        return
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
                        
                        # 체결 시 시장가 주문의 가격 업데이트
                        fill_price = event_data.get('fill_price', 0)
                        if fill_price > 0:
                            order_no_str = str(event_data.get('order_no', ''))
                            order_date = event_data.get('order_date', datetime.now().strftime('%Y%m%d'))
                            context.update_workflow_order_fill_price(
                                order_no=order_no_str,
                                order_date=order_date,
                                fill_price=fill_price,
                            )
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
                        if context.is_shutdown:
                            return
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

    async def _ls_korea_stock_order_event(
        self,
        ls,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        stay_connected: bool,
        event_filter: str = "all",
    ) -> Dict[str, Any]:
        """국내주식 실시간 주문 이벤트 (SC0~SC4)

        SC0: 주문접수, SC1: 체결, SC2: 정정확인, SC3: 취소확인, SC4: 거부
        하나만 등록해도 전체 수신됨.
        """
        from datetime import datetime

        product = "korea_stock"

        try:
            loop = asyncio.get_running_loop()
            trigger_nodes = config.get("_trigger_on_update_nodes", [])

            def create_handler(_node_id: str, _event_filter: str, _trigger_nodes: list):
                def handler(resp):
                    if context.is_shutdown:
                        return
                    from datetime import datetime

                    header = getattr(resp, 'header', None)
                    tr_cd = getattr(header, 'tr_cd', 'SC0') if header else 'SC0'

                    if _event_filter != "all" and tr_cd != _event_filter:
                        return

                    body = getattr(resp, 'body', resp)

                    # SC0~SC4 공통 필드 추출
                    event_data = {
                        "timestamp": datetime.now().isoformat(),
                        "tr_cd": tr_cd,
                        "symbol": getattr(body, 'shtnIsuNo', getattr(body, 'IsuNo', '')),
                        "symbol_name": getattr(body, 'IsuNm', ''),
                        "order_no": getattr(body, 'OrdNo', 0),
                        "orig_order_no": getattr(body, 'OrgOrdNo', 0),
                        "side": getattr(body, 'BnsTpCode', ''),
                        "order_qty": int(getattr(body, 'OrdQty', 0)),
                        "order_price": float(getattr(body, 'OrdPrc', 0)),
                        "filled_qty": int(getattr(body, 'ExecQty', 0) or 0),
                        "filled_price": float(getattr(body, 'ExecPrc', 0) or 0),
                        "remain_qty": int(getattr(body, 'UnercQty', 0) or 0),
                        "order_time": getattr(body, 'OrdTime', ''),
                        "market_code": "KRX",
                    }

                    # TR별 포트/상태 결정
                    port_map = {
                        'SC0': ('accepted', '주문접수'),
                        'SC1': ('filled', '체결'),
                        'SC2': ('modified', '정정확인'),
                        'SC3': ('cancelled', '취소확인'),
                        'SC4': ('rejected', '거부'),
                    }

                    port, status_name = port_map.get(tr_cd, ('accepted', f'코드:{tr_cd}'))
                    event_data["status"] = status_name

                    # 체결 이벤트(SC1)일 때 가격 업데이트
                    if tr_cd == 'SC1' and event_data['filled_price'] > 0:
                        order_no_str = str(event_data['order_no'])
                        order_date = datetime.now().strftime('%Y%m%d')
                        context.update_workflow_order_fill_price(
                            order_no=order_no_str,
                            order_date=order_date,
                            fill_price=event_data['filled_price'],
                        )

                    context.set_output(_node_id, port, event_data)

                    side_name = "매수" if event_data['side'] == '2' else "매도"

                    logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] [{_node_id}] 국내주식 {status_name} ({side_name})")
                    logger.debug(f"  종목: {event_data['symbol']} ({event_data['symbol_name']})")

                    asyncio.run_coroutine_threadsafe(
                        context.notify_output_update(
                            node_id=_node_id,
                            node_type="KoreaStockRealOrderEventNode",
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

            handler = create_handler(node_id, event_filter, trigger_nodes)
            context.register_order_event_handler(product, "SC0", node_id, event_filter, handler)

            if not context.has_order_event_subscription(product):
                real_client = ls.korea_stock().real()
                if not await real_client.is_connected():
                    await real_client.connect()

                context.set_order_event_real_client(product, real_client)

                def master_callback(resp):
                    if context.is_shutdown:
                        return
                    handlers = context.get_order_event_handlers(product, "SC0")
                    for (handler_node_id, handler_filter, handler_func) in handlers:
                        try:
                            handler_func(resp)
                        except Exception as e:
                            context.log("error", f"Handler error for {handler_node_id}: {e}", handler_node_id)

                real_client.SC0().on_sc0_message(master_callback)
                context.log("info", f"Master order event callback registered for korea_stock", node_id)

            real_client = context.get_order_event_real_client(product)
            if stay_connected:
                context.register_persistent(node_id, real_client, metadata={"event_filter": event_filter})
                context.log("info", f"SC0~SC4 order event subscription started (filter={event_filter}, stay_connected=True)", node_id)
            else:
                context.register_cleanup_on_flow_end(node_id, real_client)
                context.log("info", f"SC0~SC4 order event subscription started (filter={event_filter}, stay_connected=False)", node_id)

            result = {
                "status": "subscribed",
                "product": "korea_stock",
                "event_type": "SC0~SC4",
                "event_filter": event_filter,
            }

            asyncio.create_task(context.notify_output_update(
                node_id=node_id,
                node_type="KoreaStockRealOrderEventNode",
                outputs=result,
            ))

            return result

        except Exception as e:
            context.log("error", f"Korea stock order event error: {e}", node_id)
            return {"error": str(e)}


class MarketStatusNodeExecutor(NodeExecutorBase):
    """MarketStatusNode executor — JIF 기반 실시간 시장 상태 추적.

    Broker credential type 무관(해외주식/해외선물/국내주식 중 아무 BrokerNode).
    broker의 기존 WSS 세션과 별도로 ``Common.real()`` 공용 WebSocket 세션을
    생성하여 JIF TR 하나를 구독합니다. token_manager 는 broker 로그인에서
    재사용하므로 중복 로그인 없음.

    stay_connected=True (기본): 구독 유지하며 콜백마다 context._market_status_cache
    + set_output 갱신. 워크플로우 종료 시 cleanup_jif_subscriptions 에서 해제.

    stay_connected=False: 최대 5초 기다리며 수신된 이벤트 반영한 snapshot 반환
    후 즉시 tr_type=4 해제. AI Agent Tool 일회성 조회용.
    """

    # {f"{job_id}::{node_id}": {"jif": RealJIF, "real": Real, "stay_connected": bool}}
    _active_subscriptions: Dict[str, Any] = {}

    # Canonical market list for the convenience boolean ports. Updated in
    # lock-step with the OutputPort definitions on ``MarketStatusNode``.
    _SOLO_MARKET_PORTS = (
        ("US", "us_is_open"),
        ("KOSPI", "kospi_is_open"),
        ("KOSDAQ", "kosdaq_is_open"),
        ("KRX_FUTURES", "krx_futures_is_open"),
    )

    _COMBO_MARKET_PORTS = (
        ("hk_is_open", "HK_AM", "HK_PM"),
        ("cn_is_open", "CN_AM", "CN_PM"),
        ("jp_is_open", "JP_AM", "JP_PM"),
    )

    async def cleanup_jif_subscriptions(self, job_id: str) -> None:
        """Unsubscribe every active JIF stream registered for the given job.

        Mirrors ``BrokerNodeExecutor.cleanup_fill_subscriptions`` so the
        executor's shutdown sequence can wipe market-status subscriptions
        without touching unrelated real-time feeds.
        """

        keys_to_remove = []
        for key, info in self._active_subscriptions.items():
            if not key.startswith(f"{job_id}::"):
                continue
            jif = info.get("jif")
            real = info.get("real")
            if jif is not None:
                try:
                    jif.on_remove_jif_message()
                except (RuntimeError, AttributeError):
                    pass
                except Exception as e:
                    logger.warning(f"JIF unsubscribe failed for {key}: {e}")
            if real is not None:
                try:
                    await real.close()
                except Exception as e:
                    logger.warning(f"Common.real close failed for {key}: {e}")
            keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._active_subscriptions[key]
            logger.debug(f"Cleaned up JIF subscription: {key}")

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        import asyncio
        from datetime import datetime

        from programgarden_core.exceptions import ConnectionError, ValidationError

        # dry_run skip — WebSocket 불가
        if context.is_dry_run:
            context.log(
                "warning",
                f"[dry_run] MarketStatusNode skipped (realtime WebSocket disabled)",
                node_id,
            )
            return {"status": "skipped_dry_run", "dry_run": True}

        # 1. broker_connection 획득
        # MarketStatusNode 는 product_scope=ALL 이므로 auto-injection 에서 제외.
        # 여기서 직접 find_parent_output(...) 로 아무 BrokerNode 나 수용.
        broker_connection = config.get("connection")
        if not broker_connection:
            for broker_type in (
                "OverseasStockBrokerNode",
                "KoreaStockBrokerNode",
                "OverseasFuturesBrokerNode",
            ):
                candidates = context.find_parent_outputs(node_id, broker_type)
                if candidates:
                    _bnode_id, _dist, outputs = candidates[0]
                    broker_connection = outputs.get("connection")
                    if broker_connection:
                        context.log(
                            "debug",
                            f"MarketStatusNode: broker_connection resolved from "
                            f"{broker_type}/{_bnode_id} (distance={_dist})",
                            node_id,
                        )
                        break

        if not broker_connection:
            raise ConnectionError(
                "MarketStatusNode: BrokerNode 연결이 필요합니다. "
                "OverseasStockBrokerNode / OverseasFuturesBrokerNode / "
                "KoreaStockBrokerNode 중 아무거나 상위에 배치하세요."
            )

        # 2. LS 로그인 (broker 와 동일 instance 재사용)
        appkey = broker_connection.get("appkey", "")
        appsecret = broker_connection.get("appsecret", "")
        paper_trading = bool(broker_connection.get("paper_trading", False))
        broker_product = broker_connection.get("product", "overseas_stock")

        ls, success, error = ensure_ls_login(
            appkey, appsecret, paper_trading, context, node_id, broker_product,
            caller_name="MarketStatusNode",
        )
        if not success:
            raise ConnectionError(f"MarketStatusNode LS login failed: {error}")

        # 3. Common.real() — broker WSS 와 독립된 공용 세션
        from programgarden_finance.ls.common import Common

        common = Common(token_manager=ls.token_manager)
        real = common.real()
        await real.connect()
        context.log(
            "info",
            f"JIF WebSocket connected via Common.real (paper_trading={paper_trading})",
            node_id,
        )

        # 4. 구독 설정
        markets_filter = config.get("markets", []) or []
        stay_connected = bool(config.get("stay_connected", True))
        include_extended = bool(config.get("include_extended_hours", False))
        trigger_nodes = config.get("_trigger_on_update_nodes", [])

        jif = real.JIF()
        loop = asyncio.get_running_loop()

        # Track subscription for cleanup (registered even for stay_connected=False
        # so that an error between subscribe and unsubscribe still gets cleaned up)
        sub_key = f"{context.job_id}::{node_id}"
        MarketStatusNodeExecutor._active_subscriptions[sub_key] = {
            "jif": jif,
            "real": real,
            "stay_connected": stay_connected,
        }

        def _is_open(market: str) -> bool:
            flag = context.is_market_open(market, include_extended=include_extended)
            return bool(flag) if flag is not None else False

        def _compute_conv_booleans() -> Dict[str, bool]:
            conv: Dict[str, bool] = {}
            for market, port_name in self._SOLO_MARKET_PORTS:
                conv[port_name] = _is_open(market)
            for port_name, am_key, pm_key in self._COMBO_MARKET_PORTS:
                conv[port_name] = bool(_is_open(am_key) or _is_open(pm_key))
            return conv

        def on_jif_message(resp):
            """JIFRealResponse 수신 콜백 — cache/output/notification 일괄 갱신."""

            try:
                if context.is_shutdown:
                    return
                body = getattr(resp, "body", None)
                if body is None:
                    # ACK payload (rsp_cd only). Ignore.
                    return

                jangubun = str(getattr(body, "jangubun", "") or "")
                jstatus = str(getattr(body, "jstatus", "") or "")
                if not jangubun:
                    return

                # Canonical market key + open-state derivations (core 레이어)
                from programgarden_core.nodes.market_status import (
                    JANGUBUN_TO_MARKET,
                    is_extended_open,
                    is_regular_open,
                )
                from programgarden_finance.ls.common.real.JIF.constants import (
                    resolve_jstatus,
                )

                market = JANGUBUN_TO_MARKET.get(jangubun, jangubun)

                # markets 필터 (설정됐으면 구독 자체가 서버측 제약은 아니므로
                # 여기서 클라이언트 필터링 적용)
                if markets_filter and market not in markets_filter:
                    return

                status_info = resolve_jstatus(jstatus)
                reg_open = is_regular_open(jstatus)
                ext_open = is_extended_open(jstatus)

                new_status = {
                    "market": market,
                    "jangubun": jangubun,
                    "jstatus": jstatus,
                    "jstatus_label": status_info["label"],
                    "is_regular_open": reg_open,
                    "is_extended_open": ext_open,
                    "is_open": ext_open if include_extended else reg_open,
                    "updated_at": datetime.now().isoformat(),
                }

                # 이전 상태 조회 (transition 감지용)
                prev_status = context.get_market_status(market)
                prev_jstatus = prev_status.get("jstatus") if prev_status else None
                prev_label = prev_status.get("jstatus_label") if prev_status else None
                is_transition = prev_jstatus is not None and prev_jstatus != jstatus

                # Cache update
                context.update_market_status(market, new_status)

                # Output update — 바인딩 리졸버가 이 값을 읽음
                all_statuses = list(context.get_all_market_statuses().values())
                outputs = {
                    "statuses": all_statuses,
                    "event": {
                        "market": market,
                        "jstatus": jstatus,
                        "jstatus_label": status_info["label"],
                        "prev_jstatus": prev_jstatus,
                        "prev_jstatus_label": prev_label,
                        "transitioned_at": new_status["updated_at"],
                    },
                    **_compute_conv_booleans(),
                }

                for port_name, port_value in outputs.items():
                    context.set_output(node_id, port_name, port_value)

                # SSE broadcast
                asyncio.run_coroutine_threadsafe(
                    context.notify_output_update(
                        node_id=node_id,
                        node_type="MarketStatusNode",
                        outputs=outputs,
                    ),
                    loop,
                )

                # 전이 notification (prev != new)
                if is_transition:
                    asyncio.run_coroutine_threadsafe(
                        context.send_notification(
                            category=NotificationCategory.SCHEDULE_STARTED,
                            severity=NotificationSeverity.INFO,
                            title=f"Market status change: {market}",
                            message=(
                                f"{market}: {prev_label or prev_jstatus} → "
                                f"{status_info['label']} "
                                f"(jstatus {prev_jstatus} → {jstatus})"
                            ),
                            node_id=node_id,
                            node_type="MarketStatusNode",
                            data={
                                "market": market,
                                "jangubun": jangubun,
                                "prev_jstatus": prev_jstatus,
                                "jstatus": jstatus,
                                "jstatus_label": status_info["label"],
                                "is_regular_open": reg_open,
                                "is_extended_open": ext_open,
                            },
                        ),
                        loop,
                    )

                # Trigger downstream nodes
                if trigger_nodes:
                    asyncio.run_coroutine_threadsafe(
                        context.emit_event(
                            event_type="market_status",
                            source_node_id=node_id,
                            data=outputs,
                            trigger_nodes=trigger_nodes,
                        ),
                        loop,
                    )
            except Exception as e:
                context.log("warning", f"JIF message parse error: {e}", node_id)

        jif.on_jif_message(on_jif_message)
        context.log(
            "info",
            f"JIF subscription started "
            f"(markets={markets_filter or 'all 12'}, "
            f"stay_connected={stay_connected}, "
            f"include_extended_hours={include_extended})",
            node_id,
        )

        # One-shot 모드: 5초 대기 → 수신된 이벤트 반영 후 해제
        if not stay_connected:
            wait_timeout = 5.0
            check_interval = 0.1
            deadline = loop.time() + wait_timeout
            while loop.time() < deadline:
                if context.get_all_market_statuses():
                    break
                await asyncio.sleep(check_interval)

            try:
                jif.on_remove_jif_message()
            except Exception:
                pass
            MarketStatusNodeExecutor._active_subscriptions.pop(sub_key, None)
            try:
                await real.close()
            except Exception:
                pass

        # 초기/최종 output (stay_connected=True 에서는 현재까지 수신된 snapshot,
        # False 에서는 해제 직전 snapshot 을 그대로 반환)
        initial_statuses = list(context.get_all_market_statuses().values())
        initial_outputs: Dict[str, Any] = {
            "statuses": initial_statuses,
            "event": None,
            **_compute_conv_booleans(),
        }
        for port_name, port_value in initial_outputs.items():
            context.set_output(node_id, port_name, port_value)

        return initial_outputs


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
        
        # node_type별 chart_type 자동 매핑 (TableDisplayNode 등 개별 노드 지원)
        _NODE_TYPE_TO_CHART = {
            "TableDisplayNode": "table",
            "LineChartNode": "line",
            "MultiLineChartNode": "multi_line",
            "CandlestickChartNode": "candlestick",
            "BarChartNode": "bar",
            "SummaryDisplayNode": "summary",
        }
        chart_type = config.get("chart_type") or _NODE_TYPE_TO_CHART.get(node_type, "summary")
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
        # Display 노드 클래스에서 data_schema 가져오기
        _data_schema = None
        try:
            from programgarden_core.registry.node_registry import NodeTypeRegistry
            _node_class = NodeTypeRegistry().get(node_type)
            if _node_class:
                _data_schema = getattr(_node_class, '_display_data_schema', None)
        except Exception:
            pass

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
            data_schema=_data_schema,
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

    items { from, extract } 방식:
    - from: 반복할 배열 지정 (예: {{ nodes.historical.value.time_series }})
    - extract: 각 행에서 추출할 필드 정의 (row 키워드로 현재 행 접근)

    예시:
    "items": {
      "from": "{{ nodes.historical.value.time_series }}",
      "extract": {
        "symbol": "{{ nodes.split.item.symbol }}",
        "exchange": "{{ nodes.split.item.exchange }}",
        "date": "{{ row.date }}",
        "close": "{{ row.close }}"
      }
    }

    출력 형식:
    - passed_symbols: [{exchange, symbol}, ...] (거래소 정보 포함)
    - failed_symbols: [{exchange, symbol}, ...]
    - symbol_results: [{symbol, exchange, rsi, price, ...}, ...]
    - values: [{symbol, exchange, time_series: [...], ...}, ...]
    """

    def _process_items_with_extract(
        self,
        items_config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> List[Dict[str, Any]]:
        """
        items { from, extract }를 플랫 배열로 변환

        Args:
            items_config: {"from": "{{ expr }}", "extract": {"symbol": "{{ expr }}", ...}}
            context: 실행 컨텍스트
            node_id: 노드 ID

        Returns:
            평탄화된 데이터 배열 [{symbol, exchange, date, close, ...}, ...]
        """
        expr_context = context.get_expression_context()
        evaluator = ExpressionEvaluator(expr_context)

        # from 배열 평가
        from_expr = items_config.get("from")
        if not from_expr:
            context.log("error", f"items.from is required", node_id)
            return []

        from_data = evaluator.evaluate(from_expr) if isinstance(from_expr, str) else from_expr

        if not isinstance(from_data, list):
            from_data = [from_data] if from_data else []

        if not from_data:
            context.log("warning", f"items.from evaluated to empty array: {from_expr}", node_id)
            return []

        extract = items_config.get("extract", {})
        if not extract:
            context.log("error", f"items.extract is required", node_id)
            return []

        result = []

        # 외부 바인딩 값 미리 평가 (row 미포함 표현식)
        external_values = {}
        for target_field, source_expr in extract.items():
            if isinstance(source_expr, str) and "{{" in source_expr and "row." not in source_expr:
                try:
                    external_values[target_field] = evaluator.evaluate(source_expr)
                except Exception as e:
                    context.log("warning", f"External binding evaluation failed for {target_field}: {e}", node_id)
                    external_values[target_field] = source_expr

        # 기본 컨텍스트 dict (row 제외)
        base_dict = expr_context.to_dict()

        # 각 row 처리
        for row in from_data:
            record = {}

            # row 컨텍스트 추가: 기본 dict에 row 추가
            row_ctx = ExpressionContext()
            row_ctx.variables = {**base_dict, "row": row}
            row_evaluator = ExpressionEvaluator(row_ctx)

            for target_field, source_expr in extract.items():
                if target_field in external_values:
                    # 외부 바인딩 (캐시된 값 사용)
                    record[target_field] = external_values[target_field]
                elif isinstance(source_expr, str) and "{{" in source_expr:
                    # row 포함 표현식 평가
                    try:
                        record[target_field] = row_evaluator.evaluate(source_expr)
                    except Exception as e:
                        context.log("debug", f"Row expression failed for {target_field}: {e}", node_id)
                        record[target_field] = None
                else:
                    # 리터럴 값
                    record[target_field] = source_expr

            result.append(record)

        context.log("debug", f"items processed: {len(from_data)} rows -> {len(result)} records", node_id)
        return result

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
        **kwargs,
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
            
            # === 표현식 평가 (items 제외 - items는 _process_items_with_extract에서 처리) ===
            context.log("debug", f"ConditionNode '{node_id}' 실행: plugin={plugin_id}, is_positions_based={is_positions_based}", node_id)

            # items를 제외한 나머지 필드만 평가 (items는 _process_items_with_extract에서 별도 처리)
            items_orig = config.get("items")
            config_without_items = {k: v for k, v in config.items() if k != "items"}
            config = evaluate_all_bindings(config_without_items, context, node_id)
            if items_orig is not None:
                config["items"] = items_orig
            
            # === positions 기반 플러그인 처리 (ProfitTarget, StopLoss) ===
            if is_positions_based:
                positions = config.get("positions", [])
                context.log("debug", f"positions 평가 후: {type(positions).__name__}, {len(positions) if isinstance(positions, (list, dict)) else 0} items", node_id)

                if not positions or not isinstance(positions, list):
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
                            "symbols": [p.get("symbol") for p in positions if isinstance(p, dict)],
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
            
            # === items { from, extract } 기반 플러그인 처리 (RSI, MACD 등) ===
            items_config = config.get("items")
            context.log("debug", f"items config present: {items_config is not None}", node_id)

            if not items_config:
                context.log("error",
                    f"ConditionNode '{node_id}': items가 설정되지 않았습니다. "
                    f"items {{ from, extract }} 형태로 추가하세요.",
                    node_id
                )
                return {
                    "result": False,
                    "passed_symbols": [],
                    "failed_symbols": [],
                    "values": [],
                    "error": "missing_items",
                    "error_message": "items가 설정되지 않았습니다. items { from, extract } 형태로 추가하세요.",
                }

            # === 플러그인 required_fields 검증 ===
            if plugin_schema and hasattr(plugin_schema, 'required_fields'):
                required_fields = plugin_schema.required_fields or []
                extract = items_config.get("extract", {})
                missing = [f for f in required_fields if f not in extract]
                if missing:
                    context.log("error",
                        f"ConditionNode '{node_id}': extract에 필수 필드 누락: {missing}. "
                        f"플러그인 {plugin_id}는 {required_fields} 필드가 필요합니다.",
                        node_id
                    )
                    return {
                        "result": False,
                        "passed_symbols": [],
                        "failed_symbols": [],
                        "values": [],
                        "error": "missing_required_fields",
                        "error_message": f"extract에 필수 필드 누락: {missing}",
                    }

            # items 처리 (from 배열을 순회하며 extract 적용)
            data = self._process_items_with_extract(items_config, context, node_id)

            if not data:
                context.log("error",
                    f"ConditionNode '{node_id}': items 처리 결과가 비어있습니다.",
                    node_id
                )
                return {
                    "result": False,
                    "passed_symbols": [],
                    "failed_symbols": [],
                    "values": [],
                    "error": "empty_items_result",
                    "error_message": "items 처리 결과가 비어있습니다. from 배열을 확인하세요.",
                }

            # symbols 자동 추출 (data에서)
            symbols = []
            seen = set()
            for item in data:
                if isinstance(item, dict):
                    sym = item.get("symbol", "")
                    if sym and sym not in seen:
                        seen.add(sym)
                        symbols.append({
                            "symbol": sym,
                            "exchange": item.get("exchange", "NASDAQ")
                        })
            context.log("debug", f"symbols 자동 추출: {len(symbols)}개, data: {len(data)} rows", node_id)

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

            # 플러그인 실행 (새 형식: 필드 매핑 불필요 - extract에서 이미 정규화됨)
            context.log("info", f"Condition running with {len(data)} data rows", node_id)

            # 필드 매핑은 기본값 사용 (items extract에서 이미 정규화된 필드명 사용)
            field_mapping = {
                "close_field": "close",
                "open_field": "open",
                "high_field": "high",
                "low_field": "low",
                "volume_field": "volume",
                "date_field": "date",
                "symbol_field": "symbol",
                "exchange_field": "exchange",
            }

            return await self._execute_condition_plugin(
                node_id, normalized_symbols, data, evaluated_fields,
                plugin, context, sandbox,
                plugin_id=plugin_id,
                field_mapping=field_mapping,
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

            # context는 시그니처에 있는 플러그인에만 전달 (trailing_stop 등)
            import inspect
            try:
                sig = inspect.signature(plugin)
                if "context" in sig.parameters:
                    plugin_kwargs["context"] = context
            except (ValueError, TypeError):
                pass

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

        # SIGNAL_TRIGGERED notification (변화가 있을 때만: passed_symbols 존재)
        if passed_symbols:
            passed_names = [s.get("symbol", "?") for s in passed_symbols[:5]]
            extra = f" +{len(passed_symbols) - 5} more" if len(passed_symbols) > 5 else ""
            title = f"{plugin_id} signal: {', '.join(passed_names)}{extra}"
            msg = f"{len(passed_symbols)}/{len(normalized_symbols)} symbols passed"

            output_fields = {}
            try:
                from programgarden_core.registry import PluginRegistry
                _schema = PluginRegistry().get_schema(plugin_id)
                if _schema and hasattr(_schema, 'output_fields'):
                    output_fields = _schema.output_fields
            except Exception:
                pass

            await context.send_notification(
                category=NotificationCategory.SIGNAL_TRIGGERED,
                severity=NotificationSeverity.INFO,
                title=title,
                message=msg,
                node_id=node_id,
                node_type="ConditionNode",
                data={
                    "plugin": plugin_id,
                    "plugin_output_fields": output_fields,
                    "symbol_results": symbol_results,
                    "passed_count": len(passed_symbols),
                    "failed_count": len(failed_symbols),
                    "total_count": len(normalized_symbols),
                },
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


class IfNodeExecutor(NodeExecutorBase):
    """
    IfNode executor - 조건 분기

    left op right를 평가하여 true/false 포트로 흐름 분기.
    - true 포트: 조건 충족 시 upstream 데이터 pass-through
    - false 포트: 조건 미충족 시 upstream 데이터 pass-through
    - result 포트: 조건 평가 결과 (boolean)
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        config = evaluate_all_bindings(config, context, node_id)

        left = config.get("left")
        operator = config.get("operator", "==")
        right = config.get("right")

        result = self._evaluate(left, operator, right)
        context.log(
            "info",
            f"IfNode: {left!r} {operator} {right!r} → {result}",
            node_id,
        )

        # upstream에서 전달된 데이터 (pass-through)
        passthrough = kwargs.get("input_data") or {}

        return {
            "true": passthrough if result else None,
            "false": passthrough if not result else None,
            "result": result,
            "_if_branch": "true" if result else "false",
        }

    @staticmethod
    def _evaluate(left: Any, operator: str, right: Any) -> bool:
        """비교 연산 수행"""
        try:
            if operator == "==":           return left == right
            if operator == "!=":           return left != right
            if operator == ">":            return float(left) > float(right)
            if operator == ">=":           return float(left) >= float(right)
            if operator == "<":            return float(left) < float(right)
            if operator == "<=":           return float(left) <= float(right)
            if operator == "in":           return left in right
            if operator == "not_in":       return left not in right
            if operator == "contains":     return right in left
            if operator == "not_contains": return right not in left
            if operator == "is_empty":     return not left
            if operator == "is_not_empty": return bool(left)
        except (TypeError, ValueError):
            return False
        return False


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

        # 입력 symbols 가져오기 (포트 또는 config에서 명시적 입력 필수)
        input_symbols = context.get_output(f"_input_{node_id}", "symbols")
        config_symbols = config.get("symbols")
        symbols = input_symbols or config_symbols

        if not symbols:
            error_msg = "symbols 필드가 필수입니다. 종목을 직접 입력하거나 WatchlistNode를 연결하세요."
            context.log("error", error_msg, node_id)
            return {"error": error_msg, "values": []}

        # config에서 명시적 connection 확인
        broker_connection = config.get("connection")
        
        if not broker_connection:
            context.log("error", "connection이 자동 주입되지 않았습니다. 매칭되는 BrokerNode가 워크플로우에 있는지 확인하세요.", node_id)
            return {"error": "Missing connection - no matching BrokerNode found in workflow", "values": []}
        
        product = broker_connection.get("product", "overseas_stock")
        
        context.log(
            "info", 
            f"Fetching current market data: {len(symbols)} symbols, product={product}", 
            node_id
        )
        
        # product별 분기 (overseas_futures와 overseas_futureoption은 동일)
        if product == "overseas_stock":
            result = await self._fetch_overseas_stock(symbols, context, node_id)
        elif product in ("overseas_futureoption", "overseas_futures"):
            result = await self._fetch_overseas_futures(symbols, context, node_id)
        elif product == "korea_stock":
            result = await self._fetch_korea_stock(symbols, context, node_id)
        else:
            context.log("error", f"Unsupported product for MarketDataNode: {product}", node_id)
            result = self._empty_result(f"i18n:errors.UNSUPPORTED_PRODUCT|product={product}")

        return result

    async def _fetch_overseas_stock(
        self,
        symbols: List[Dict[str, str]],
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
                product="overseas_stock",
                caller_name="MarketDataNode(overseas_stock)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_result(f"i18n:errors.LS_LOGIN_FAILED|error={error}")
            
            api = ls.overseas_stock()
            
            values = []
            
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
                        from datetime import datetime
                        
                        # values 배열에 단일 항목 추가
                        values.append({
                            "symbol": symbol,
                            "exchange": exchange,
                            "price": float(out_block.price or 0),
                            "change": float(out_block.diff or 0),
                            "change_pct": float(out_block.rate or 0),
                            "volume": int(out_block.volume or 0),
                            "open": float(out_block.open or 0),
                            "high": float(out_block.high or 0),
                            "low": float(out_block.low or 0),
                            "close": float(out_block.price or 0),
                            "per": float(out_block.perv or 0) if hasattr(out_block, 'perv') else 0.0,
                            "eps": float(out_block.epsv or 0) if hasattr(out_block, 'epsv') else 0.0,
                        })
                        
                        context.log("debug", f"Fetched {exchange}:{symbol}: price={out_block.price}", node_id)
                    else:
                        context.log("warning", f"No data for {exchange}:{symbol}", node_id)
                        
                except Exception as e:
                    context.log("warning", f"Failed to fetch {exchange}:{symbol}: {e}", node_id)
                    continue
            
            return {"values": values}
            
        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_result(f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Market data fetch error: {e}", node_id)
            return self._empty_result(f"i18n:errors.MARKET_DATA_FETCH_ERROR|error={e}")

    async def _fetch_overseas_futures(
        self,
        symbols: List[Dict[str, str]],
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
                product="overseas_futures",
                caller_name="MarketDataNode(overseas_futureoption)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_result(f"i18n:errors.LS_LOGIN_FAILED|error={error}")
            
            api = ls.overseas_futureoption()
            
            values = []
            
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
                        from datetime import datetime
                        
                        # values 배열에 단일 항목 추가
                        values.append({
                            "symbol": symbol,
                            "exchange": exchange,
                            "symbol_name": out_block.SymbolNm or symbol,
                            "price": float(out_block.TrdP or 0),
                            "change": float(out_block.YdiffP or 0),
                            "change_pct": float(out_block.Diff or 0),
                            "volume": int(out_block.TotQ or 0),
                            "open": float(out_block.OpenP or 0),
                            "high": float(out_block.HighP or 0),
                            "low": float(out_block.LowP or 0),
                            "close": float(out_block.TrdP or 0),  # 현재가 = 종가
                        })
                        
                        context.log("debug", f"Fetched {exchange}:{symbol}: price={out_block.TrdP}", node_id)
                    else:
                        context.log("warning", f"No data for {exchange}:{symbol}", node_id)
                        
                except Exception as e:
                    context.log("warning", f"Failed to fetch {exchange}:{symbol}: {e}", node_id)
                    continue
            
            return {"values": values}
            
        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_result(f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Market data fetch error: {e}", node_id)
            return self._empty_result(f"i18n:errors.MARKET_DATA_FETCH_ERROR|error={e}")

    async def _fetch_korea_stock(
        self,
        symbols: List[Dict[str, str]],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """국내주식 현재가 조회 (t1102) - 당일 데이터만 반환"""

        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not set. Check BrokerNode credential_id.", node_id)
            return self._empty_result("i18n:errors.CREDENTIAL_NOT_SET")

        try:
            from programgarden_finance.ls.korea_stock.market.t1102.blocks import T1102InBlock

            ls, success, error = ensure_ls_login(
                credential.get("appkey"),
                credential.get("appsecret"),
                False,  # 국내주식은 실전 전용
                context, node_id,
                product="korea_stock",
                caller_name="MarketDataNode(korea_stock)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_result(f"i18n:errors.LS_LOGIN_FAILED|error={error}")

            api = ls.korea_stock()

            values = []

            for symbol_entry in symbols:
                try:
                    symbol = symbol_entry.get("symbol", "")
                    if not symbol:
                        continue

                    # t1102 현재가 조회 (6자리 종목코드)
                    body = T1102InBlock(shcode=symbol)

                    response = api.market().t1102(body=body).req()

                    if response and response.block:
                        blk = response.block

                        # sign: 1=상한/2=상승 → 양수, 4=하한/5=하락 → 음수
                        change_val = int(blk.change or 0)
                        if blk.sign in ("4", "5"):
                            change_val = -change_val

                        values.append({
                            "symbol": symbol,
                            "exchange": "KRX",
                            "name": str(blk.hname or ""),
                            "price": int(blk.price or 0),
                            "change": change_val,
                            "change_pct": float(blk.diff or 0),
                            "volume": int(blk.volume or 0),
                            "open": int(blk.open or 0),
                            "high": int(blk.high or 0),
                            "low": int(blk.low or 0),
                            "close": int(blk.price or 0),
                            "per": float(blk.per or 0),
                            "pbr": float(blk.pbrx or 0),
                        })

                        context.log("debug", f"Fetched KRX:{symbol}: price={blk.price}", node_id)
                    else:
                        context.log("warning", f"No data for KRX:{symbol}", node_id)

                except Exception as e:
                    context.log("warning", f"Failed to fetch KRX:{symbol}: {e}", node_id)
                    continue

            return {"values": values}

        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_result(f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Market data fetch error: {e}", node_id)
            return self._empty_result(f"i18n:errors.MARKET_DATA_FETCH_ERROR|error={e}")

    def _empty_result(self, error_msg: str = "") -> Dict[str, Any]:
        """빈 결과 반환 (에러 시)"""
        result = {"values": []}
        if error_msg:
            result["error"] = error_msg
        return result


class FundamentalNodeExecutor(NodeExecutorBase):
    """
    FundamentalNode executor - 해외주식 종목정보(펀더멘털) 조회

    LS Finance Market API g3104를 사용하여 종목정보를 조회합니다.
    PER, EPS, 시가총액, 발행주식수, 52주 고/저가, 업종 등
    """

    # 거래소 코드 매핑 (g3104용)
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
        """종목정보(펀더멘털) 조회"""

        # symbols 획득: input port → config.symbols → config.symbol (단일→배열 변환)
        input_symbols = context.get_output(f"_input_{node_id}", "symbols")
        config_symbols = config.get("symbols")
        symbols = input_symbols or config_symbols

        # Item-based execution: symbol (단수) → symbols (복수) 변환
        if not symbols:
            config_symbol = config.get("symbol")
            if isinstance(config_symbol, dict) and "symbol" in config_symbol:
                symbols = [config_symbol]

        if not symbols:
            error_msg = "symbols 필드가 필수입니다. 종목을 직접 입력하거나 WatchlistNode를 연결하세요."
            context.log("error", error_msg, node_id)
            return {"error": error_msg, "values": []}

        broker_connection = config.get("connection")

        if not broker_connection:
            context.log("error", "connection이 자동 주입되지 않았습니다. 매칭되는 BrokerNode가 워크플로우에 있는지 확인하세요.", node_id)
            return {"error": "Missing connection - no matching BrokerNode found in workflow", "values": []}

        context.log(
            "info",
            f"Fetching fundamental data: {len(symbols)} symbols",
            node_id
        )

        product = broker_connection.get("product", "overseas_stock")

        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not set. Check BrokerNode credential_id.", node_id)
            return self._empty_result("i18n:errors.CREDENTIAL_NOT_SET")

        if product == "korea_stock":
            return await self._fetch_korea_stock(symbols, credential, context, node_id)

        try:
            from programgarden_finance.ls.overseas_stock.market.g3104.blocks import G3104InBlock

            ls, success, error = ensure_ls_login(
                credential.get("appkey"),
                credential.get("appsecret"),
                credential.get("paper_trading", False),
                context, node_id,
                product="overseas_stock",
                caller_name="FundamentalNode(overseas_stock)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_result(f"i18n:errors.LS_LOGIN_FAILED|error={error}")

            api = ls.overseas_stock()

            values = []

            for symbol_entry in symbols:
                try:
                    exchange = symbol_entry.get("exchange", "NASDAQ")
                    symbol = symbol_entry.get("symbol", "")
                    if not symbol:
                        continue

                    exchange_code = self.EXCHANGE_CODES.get(exchange.upper(), "82")
                    keysymbol = f"{exchange_code}{symbol}"

                    body = G3104InBlock(
                        keysymbol=keysymbol,
                        exchcd=exchange_code,
                        symbol=symbol,
                    )

                    response = api.market().g3104(body=body).req()

                    if response and response.block:
                        blk = response.block

                        # 등락률 계산 (전일종가 대비)
                        pcls = float(blk.pcls or 0)
                        clos = float(blk.clos or 0)
                        change_percent = ((clos - pcls) / pcls * 100) if pcls else 0.0

                        values.append({
                            "exchange": exchange,
                            "symbol": symbol,
                            "name": str(blk.engname or ""),
                            "industry": str(blk.induname or ""),
                            "nation": str(blk.nation_name or ""),
                            "exchange_name": str(blk.exchange_name or ""),
                            "current_price": clos,
                            "volume": int(blk.volume or 0),
                            "change_percent": round(change_percent, 2),
                            "per": float(blk.perv or 0),
                            "eps": float(blk.epsv or 0),
                            "market_cap": int(blk.shareprc or 0),
                            "shares_outstanding": int(blk.share or 0),
                            "high_52w": float(blk.high52p or 0),
                            "low_52w": float(blk.low52p or 0),
                            "exchange_rate": float(blk.exrate or 0),
                        })

                        context.log("debug", f"Fetched fundamental {exchange}:{symbol}: PER={blk.perv}, EPS={blk.epsv}", node_id)
                    else:
                        context.log("warning", f"No data for {exchange}:{symbol}", node_id)

                except Exception as e:
                    context.log("warning", f"Failed to fetch {exchange}:{symbol}: {e}", node_id)
                    continue

            return {"values": values}

        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_result(f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Fundamental data fetch error: {e}", node_id)
            return self._empty_result(f"i18n:errors.FUNDAMENTAL_DATA_FETCH_ERROR|error={e}")

    async def _fetch_korea_stock(
        self,
        symbols: List[Dict[str, str]],
        credential: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """국내주식 펀더멘털 조회 (t1102) - PER, PBR, 시가총액, 52주 고저가 등"""

        try:
            from programgarden_finance.ls.korea_stock.market.t1102.blocks import T1102InBlock

            ls, success, error = ensure_ls_login(
                credential.get("appkey"),
                credential.get("appsecret"),
                False,  # 국내주식은 실전 전용
                context, node_id,
                product="korea_stock",
                caller_name="FundamentalNode(korea_stock)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_result(f"i18n:errors.LS_LOGIN_FAILED|error={error}")

            api = ls.korea_stock()

            values = []

            for symbol_entry in symbols:
                try:
                    symbol = symbol_entry.get("symbol", "")
                    if not symbol:
                        continue

                    body = T1102InBlock(shcode=symbol)
                    response = api.market().t1102(body=body).req()

                    if response and response.block:
                        blk = response.block

                        values.append({
                            "exchange": "KRX",
                            "symbol": symbol,
                            "name": str(blk.hname or ""),
                            "current_price": int(blk.price or 0),
                            "volume": int(blk.volume or 0),
                            "change_percent": float(blk.diff or 0),
                            "per": float(blk.per or 0),
                            "pbr": float(blk.pbrx or 0),
                            "market_cap": int(blk.total or 0),  # 억원
                            "shares_outstanding": int(blk.listing or 0),  # 천 단위
                            "high_52w": int(blk.high52w or 0),
                            "low_52w": int(blk.low52w or 0),
                            "eps": float(blk.bfeps or 0),  # 전분기 EPS
                        })

                        context.log("debug", f"Fetched fundamental KRX:{symbol}: PER={blk.per}, PBR={blk.pbrx}", node_id)
                    else:
                        context.log("warning", f"No data for KRX:{symbol}", node_id)

                except Exception as e:
                    context.log("warning", f"Failed to fetch KRX:{symbol}: {e}", node_id)
                    continue

            return {"values": values}

        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_result(f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Fundamental data fetch error: {e}", node_id)
            return self._empty_result(f"i18n:errors.FUNDAMENTAL_DATA_FETCH_ERROR|error={e}")

    def _empty_result(self, error_msg: str = "") -> Dict[str, Any]:
        """빈 결과 반환 (에러 시)"""
        result = {"values": []}
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

        # symbol 획득 (config 필드 우선, input port 폴백)
        # Item-based execution: symbol (단수) - 노드 스키마와 일치
        config_symbol = config.get("symbol")  # 단일 객체 {exchange, symbol}
        input_symbol = context.get_output(f"_input_{node_id}", "symbol")

        # 방어: LLM Tool 호출 시 JSON 문자열로 전달되는 경우 dict 변환
        import json as _json
        if isinstance(config_symbol, str):
            try:
                _parsed = _json.loads(config_symbol)
                if isinstance(_parsed, dict):
                    config_symbol = _parsed
            except (ValueError, _json.JSONDecodeError):
                pass
        if isinstance(input_symbol, str):
            try:
                _parsed = _json.loads(input_symbol)
                if isinstance(_parsed, dict):
                    input_symbol = _parsed
            except (ValueError, _json.JSONDecodeError):
                pass

        # 우선순위: config.symbol > input.symbol
        if config_symbol:
            symbols_raw = [config_symbol] if isinstance(config_symbol, dict) else []
            context.log("debug", f"Using config.symbol: {config_symbol}", node_id)
        elif input_symbol:
            symbols_raw = [input_symbol] if isinstance(input_symbol, dict) else []
            context.log("debug", f"Using input port symbol: {input_symbol}", node_id)
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
        
        # positions 데이터 가져오기 (market_code 참조용)
        positions_raw = context.get_output(f"_input_{node_id}", "positions")
        if not positions_raw:
            positions_raw = context.get_output("account", "positions") or []

        # 리스트에서 symbol → market_code 매핑 추출
        if isinstance(positions_raw, list):
            for pos in positions_raw:
                if isinstance(pos, dict) and pos.get("symbol"):
                    sym = pos["symbol"]
                    mc = pos.get("market_code", pos.get("exchange_code", ""))
                    if mc and sym not in symbol_exchange_map:
                        symbol_exchange_map[sym] = mc
        
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
        
        # config에서 connection 확인 (자동 주입 또는 명시적 바인딩)
        broker_connection = config.get("connection")

        # connection 없으면 기본값 사용 (HistoricalDataNode는 선택적)
        product = broker_connection.get("product", "overseas_stock") if broker_connection else "overseas_stock"
        if not broker_connection:
            context.log("warning", "connection이 자동 주입되지 않았습니다. 기본값(overseas_stock) 사용.", node_id)
        
        context.log(
            "info", 
            f"Fetching historical data: {len(symbols)} symbols, {start_date}~{end_date}, {interval}, product={product}", 
            node_id
        )
        
        # product별 분기 (overseas_futures와 overseas_futureoption은 동일)
        if product == "overseas_stock":
            ohlcv_data = await self._fetch_overseas_stock(symbols, start_date, end_date, interval, context, node_id, None, symbol_exchange_map, symbols_raw)
        elif product in ("overseas_futureoption", "overseas_futures"):
            ohlcv_data = await self._fetch_overseas_futures(symbols, start_date, end_date, interval, context, node_id, symbols_raw)
        elif product == "korea_stock":
            ohlcv_data = await self._fetch_korea_stock(symbols, start_date, end_date, interval, context, node_id, symbols_raw)
        else:
            context.log("error", f"Unsupported product for HistoricalDataNode: {product}", node_id)
            ohlcv_data = self._empty_historical_result(symbols_raw, f"i18n:errors.UNSUPPORTED_PRODUCT|product={product}")
        
        # 출력: value (단수, Item-based execution) + values (복수, 호환성)
        # Item-based execution: 단일 symbol → 단일 value
        single_value = ohlcv_data[0] if ohlcv_data and len(ohlcv_data) == 1 else None

        # 디버그 로그
        context.log("info", f"HistoricalData output: value={single_value is not None}, ohlcv_count={len(ohlcv_data) if ohlcv_data else 0}", node_id)
        if single_value:
            ts_count = len(single_value.get("time_series", [])) if isinstance(single_value, dict) else 0
            context.log("debug", f"HistoricalData value: symbol={single_value.get('symbol')}, time_series_count={ts_count}", node_id)

        return {
            "value": single_value,  # 단일 {symbol, exchange, time_series: [...]}  - 노드 스키마와 일치
            "values": ohlcv_data,  # [{symbol, exchange, time_series: [...]}, ...] - 호환성
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
                product="overseas_stock",
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

            # positions(list[dict])에서 symbol → market_code 매핑 구성
            position_market_code: Dict[str, str] = {}
            if positions:
                iterator = positions.values() if isinstance(positions, dict) else positions
                for pos in iterator:
                    if isinstance(pos, dict):
                        sym = pos.get("symbol")
                        mc = pos.get("market_code") or ""
                        if sym and mc:
                            position_market_code[sym] = mc

            result_list = []  # [{symbol, exchange, time_series: [...]}, ...]

            for symbol in symbols:
                try:
                    # positions에서 market_code 가져오기 (LS증권 거래소 코드: 81=NYSE/AMEX, 82=NASDAQ)
                    exchcd = position_market_code.get(symbol) or "82"  # 기본값 NASDAQ
                    
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
                product="overseas_futures",
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

        # API 응답 메시지 확인 (만기 종료 월물 등)
        rsp_msg = getattr(result, 'rsp_msg', '')
        if rsp_msg and '해당자료가 없습니다' in rsp_msg:
            context.log("warning", f"선물 {symbol} 조회 실패: {rsp_msg} (만기 종료된 월물이거나 조회 기간에 데이터가 없습니다)", node_id)
            return []

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

        # API 응답 메시지 확인 (만기 종료 월물 등)
        rsp_msg = getattr(result, 'rsp_msg', '')
        if rsp_msg and '해당자료가 없습니다' in rsp_msg:
            context.log("warning", f"선물 {symbol} 분봉 조회 실패: {rsp_msg} (만기 종료된 월물이거나 데이터가 없습니다)", node_id)
            return []

        bars = []
        if result.block1:
            for item in result.block1:
                # o3103은 date + time 별도 필드 (예: date=20260130, time=001500)
                date_str = getattr(item, 'date', '') or ''
                time_str = getattr(item, 'time', '') or ''
                datetime_str = f"{date_str}{time_str}" if date_str and time_str else date_str
                bars.append({
                    "date": datetime_str,  # 분봉: YYYYMMDDHHMMSS 형식
                    "open": float(item.open) if hasattr(item, 'open') and item.open else 0,
                    "high": float(item.high) if hasattr(item, 'high') and item.high else 0,
                    "low": float(item.low) if hasattr(item, 'low') and item.low else 0,
                    "close": float(item.close) if hasattr(item, 'close') and item.close else 0,
                    "volume": int(item.volume) if hasattr(item, 'volume') and item.volume else 0,
                })
        
        # 시간순 정렬 (오래된 것부터)
        bars.sort(key=lambda x: x["date"])
        return bars

    async def _fetch_korea_stock(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        interval: str,
        context: ExecutionContext,
        node_id: str,
        symbols_raw: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """국내주식 차트 데이터 조회 (t8451 일주월년)

        반환: [{symbol, exchange, time_series: [{date, open, high, low, close, volume}, ...]}, ...]
        """

        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not set for HistoricalDataNode", node_id)
            return self._empty_historical_result(symbols_raw or symbols, "i18n:errors.CREDENTIAL_NOT_SET")

        try:
            from programgarden_finance.ls.korea_stock.chart.t8451.blocks import T8451InBlock

            ls, success, error = ensure_ls_login(
                credential.get("appkey"),
                credential.get("appsecret"),
                False,  # 국내주식은 실전 전용
                context, node_id,
                product="korea_stock",
                caller_name="HistoricalDataNode(korea_stock)"
            )
            if not success:
                context.log("error", f"LS login failed: {error}", node_id)
                return self._empty_historical_result(symbols_raw or symbols, f"i18n:errors.LS_LOGIN_FAILED|error={error}")

            api = ls.korea_stock()

            # interval → gubun 변환 (t8451: 2=일, 3=주, 4=월, 5=년)
            gubun_map = {"1d": "2", "1w": "3", "1M": "4", "1Y": "5"}
            gubun = gubun_map.get(interval, "2")

            result_list = []

            for symbol in symbols:
                try:
                    body = T8451InBlock(
                        shcode=symbol,
                        gubun=gubun,
                        qrycnt=500,
                        sdate=start_date,
                        edate=end_date or "99999999",
                        sujung="Y",  # 수정주가 적용
                    )

                    response = api.chart().t8451(body=body).req()

                    time_series = []
                    if response and response.block1:
                        for bar in response.block1:
                            time_series.append({
                                "date": str(bar.date),
                                "open": int(bar.open or 0),
                                "high": int(bar.high or 0),
                                "low": int(bar.low or 0),
                                "close": int(bar.close or 0),
                                "volume": int(bar.jdiff_vol or 0),
                            })

                    # 시간순 정렬 (오래된 것부터)
                    time_series.sort(key=lambda x: x["date"])

                    # symbols_raw에서 exchange 정보 추출
                    exchange = "KRX"

                    result_list.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "time_series": time_series,
                    })

                    context.log("debug", f"Fetched KRX:{symbol}: {len(time_series)} bars", node_id)

                except Exception as e:
                    context.log("warning", f"Failed to fetch KRX:{symbol}: {e}", node_id)
                    result_list.append({
                        "symbol": symbol,
                        "exchange": "KRX",
                        "time_series": [],
                        "_error": str(e),
                    })

            return result_list

        except ImportError as e:
            context.log("error", f"Finance package not available: {e}", node_id)
            return self._empty_historical_result(symbols_raw or symbols, f"i18n:errors.FINANCE_PACKAGE_NOT_AVAILABLE|error={e}")
        except Exception as e:
            context.log("error", f"Historical data fetch error: {e}", node_id)
            return self._empty_historical_result(symbols_raw or symbols, f"i18n:errors.HISTORICAL_DATA_FETCH_ERROR|error={e}")

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

    items { from, extract } 방식:
    - from: 반복할 배열 지정 (예: {{ nodes.historical.value.time_series }})
    - extract: 각 행에서 추출할 필드 정의 (row 키워드로 현재 행 접근)

    예시:
    "items": {
      "from": "{{ nodes.historical.value.time_series }}",
      "extract": {
        "symbol": "{{ nodes.split.item.symbol }}",
        "exchange": "{{ nodes.split.item.exchange }}",
        "date": "{{ row.date }}",
        "open": "{{ row.open }}",
        "high": "{{ row.high }}",
        "low": "{{ row.low }}",
        "close": "{{ row.close }}",
        "volume": "{{ row.volume }}",
        "signal": "{{ nodes.condition.result.signal }}"
      }
    }

    출력:
    - equity_curve: 일별 포트폴리오 가치
    - trades: 거래 내역
    - metrics: 성과 지표

    리소스 관리:
    - 메모리/CPU 집약적 작업 (weight=3.0)
    - 리소스 부족 시 실행 대기 또는 거부
    """

    def _process_items_with_extract(
        self,
        items_config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> List[Dict[str, Any]]:
        """
        items { from, extract }를 플랫 배열로 변환 (ConditionNodeExecutor와 동일 로직)
        """
        expr_context = context.get_expression_context()
        evaluator = ExpressionEvaluator(expr_context)

        from_expr = items_config.get("from")
        if not from_expr:
            context.log("error", f"items.from is required", node_id)
            return []

        from_data = evaluator.evaluate(from_expr) if isinstance(from_expr, str) else from_expr

        if not isinstance(from_data, list):
            from_data = [from_data] if from_data else []

        if not from_data:
            context.log("warning", f"items.from evaluated to empty array", node_id)
            return []

        extract = items_config.get("extract", {})
        if not extract:
            context.log("error", f"items.extract is required", node_id)
            return []

        result = []

        # 외부 바인딩 값 미리 평가
        external_values = {}
        for target_field, source_expr in extract.items():
            if isinstance(source_expr, str) and "{{" in source_expr and "row." not in source_expr:
                try:
                    external_values[target_field] = evaluator.evaluate(source_expr)
                except Exception as e:
                    context.log("warning", f"External binding evaluation failed for {target_field}: {e}", node_id)
                    external_values[target_field] = source_expr

        # 각 row 처리
        for row in from_data:
            record = {}
            row_context = {**expr_context, "row": row}
            row_evaluator = ExpressionEvaluator(row_context)

            for target_field, source_expr in extract.items():
                if target_field in external_values:
                    record[target_field] = external_values[target_field]
                elif isinstance(source_expr, str) and "{{" in source_expr:
                    try:
                        record[target_field] = row_evaluator.evaluate(source_expr)
                    except Exception:
                        record[target_field] = None
                else:
                    record[target_field] = source_expr

            result.append(record)

        context.log("debug", f"items processed: {len(from_data)} rows -> {len(result)} records", node_id)
        return result

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
            # === items { from, extract } 방식으로 입력 데이터 가져오기 ===
            items_config = config.get("items")

            if items_config:
                # 새 방식: items { from, extract }
                flat_data = self._process_items_with_extract(items_config, context, node_id)

                if not flat_data:
                    context.log("error",
                        f"BacktestEngineNode '{node_id}': items 처리 결과가 비어있습니다.",
                        node_id
                    )
                    return {
                        "equity_curve": [],
                        "trades": [],
                        "metrics": {},
                        "summary": {"error": "items 처리 결과가 비어있습니다."},
                    }

                # items extract에서 이미 정규화된 필드명 사용
                close_field = "close"
                date_field = "date"
                symbol_field = "symbol"
                signal_field = "signal"
                side_field = "side"

                # signals는 flat_data에 포함됨 (extract에서 signal 필드 추출)
                signals = [row for row in flat_data if row.get(signal_field)]
            else:
                # 레거시 방식: 직접 data 바인딩 (하위 호환성)
                flat_data = config.get("data")
                if not flat_data:
                    flat_data = context.get_output(f"_input_{node_id}", "data")
                if not flat_data:
                    flat_data = context.get_output(f"_input_{node_id}", "ohlcv_data")
                if not flat_data:
                    flat_data = context.get_output("historicalData", "ohlcv_data") or []

                close_field = config.get("close_field", "close")
                date_field = config.get("date_field", "date")
                symbol_field = config.get("symbol_field", "symbol")
                signal_field = config.get("signal_field", "signal")
                side_field = config.get("side_field", "side")

                signals = config.get("signals") or context.get_output(f"_input_{node_id}", "signals")
                if not signals:
                    signals = context.get_output(f"_input_{node_id}", "entry_signal") or []

                # values 형식 지원
                values = context.get_output(f"_input_{node_id}", "values")
                if values and isinstance(values, list):
                    extracted_signals = self._extract_signals_from_values(values, signal_field, side_field)
                    if extracted_signals:
                        signals = extracted_signals

            # 플랫 배열 → 종목별 딕셔너리로 변환
            ohlcv_data = self._convert_flat_to_symbol_dict(flat_data, symbol_field, date_field, close_field)
            
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


class PositionSizingNodeExecutor(NodeExecutorBase):
    """
    PositionSizingNode executor - 포지션 크기 계산

    지원하는 포지션 사이징 방법:
    1. fixed_percent: 계좌의 일정 비율을 종목 수로 균등 분할
    2. fixed_amount: 종목당 고정 금액 투자
    3. fixed_quantity: 종목당 고정 수량 지정
    4. kelly: 켈리 공식 기반 최적 투자 비율 (조정 가능)
    5. atr_based: ATR 기반 리스크 관리형 사이징

    입력:
    - symbols: 투자할 종목 리스트 [{symbol, exchange, price?, ...}, ...]
    - balance: 예수금/매수가능금액 정보
    - price_data: 시세 데이터 (가격 조회용)

    출력:
    - orders: 주문 배열 [{symbol, exchange, quantity, price, ...}, ...]
    - symbols: 입력 종목 리스트 그대로 전달
    - total_amount: 총 투자 예정 금액
    - method: 사용된 사이징 방법
    - config: 사이징 설정 정보
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """포지션 사이징 실행"""
        
        # 바인딩 평가
        evaluated = evaluate_all_bindings(config, context, node_id)
        
        # 필수 입력 추출
        symbols_input = evaluated.get("symbols", [])
        balance_data = evaluated.get("balance", {})
        # price_data, prices, market_data 순서로 확인 (하위 호환성)
        price_data = evaluated.get("price_data") or evaluated.get("prices") or evaluated.get("market_data") or {}
        
        # 설정 추출
        method = evaluated.get("method", "fixed_percent")
        max_percent = float(evaluated.get("max_percent", 10.0))
        fixed_amount = evaluated.get("fixed_amount")
        fixed_quantity = int(evaluated.get("fixed_quantity", 1))
        kelly_fraction = float(evaluated.get("kelly_fraction", 0.25))
        atr_risk_percent = float(evaluated.get("atr_risk_percent", 1.0))
        
        # 종목 리스트 정규화
        symbols = self._normalize_symbols(symbols_input)
        
        if not symbols:
            context.log("warning", "No symbols provided for position sizing", node_id)
            return self._empty_result()
        
        # 예수금 추출 (해외주식/해외선물 공통)
        available_balance = self._extract_balance(balance_data)

        # fixed_quantity 메서드는 balance 없이도 동작 (테스트용)
        if available_balance <= 0 and method != "fixed_quantity":
            context.log("warning", f"No available balance: {available_balance}", node_id)
            return self._empty_result()
        
        context.log(
            "info",
            f"Position sizing: method={method}, symbols={len(symbols)}, balance={available_balance:,.0f}",
            node_id
        )
        
        # 방법별 수량 계산
        if method == "fixed_percent":
            result = self._calc_fixed_percent(
                symbols, available_balance, max_percent, price_data, context, node_id
            )
        elif method == "fixed_amount":
            result = self._calc_fixed_amount(
                symbols, fixed_amount, price_data, context, node_id
            )
        elif method == "fixed_quantity":
            result = self._calc_fixed_quantity(
                symbols, fixed_quantity, price_data, context, node_id
            )
        elif method == "kelly":
            result = self._calc_kelly(
                symbols, available_balance, max_percent, kelly_fraction, 
                price_data, context, node_id
            )
        elif method == "atr_based":
            result = self._calc_atr_based(
                symbols, available_balance, max_percent, atr_risk_percent,
                price_data, context, node_id
            )
        else:
            context.log("error", f"Unknown sizing method: {method}", node_id)
            return self._empty_result()
        
        # 결과에 원본 symbols 추가
        result["symbols"] = symbols_input
        
        return result

    def _normalize_symbols(self, symbols_input: Any) -> List[Dict[str, Any]]:
        """
        종목 입력을 정규화
        
        지원 형식:
        - List[str]: ["AAPL", "NVDA"]
        - List[dict]: [{"symbol": "AAPL", "exchange": "NASDAQ"}, ...]
        - Dict: {"AAPL": {...}, "NVDA": {...}}
        """
        if not symbols_input:
            return []
        
        if isinstance(symbols_input, dict):
            # {"AAPL": {...}, "NVDA": {...}} 형식
            return [
                {"symbol": k, **v} if isinstance(v, dict) else {"symbol": k}
                for k, v in symbols_input.items()
            ]
        
        if isinstance(symbols_input, list):
            result = []
            for item in symbols_input:
                if isinstance(item, str):
                    result.append({"symbol": item})
                elif isinstance(item, dict):
                    result.append(item)
            return result
        
        return []

    def _extract_balance(self, balance_data: Any) -> float:
        """
        예수금 데이터에서 매수가능금액 추출
        
        지원 형식:
        - float/int: 직접 금액
        - dict: {fcurr_ord_able_amt, balance, available, ...}
        - list: [{fcurr_ord_able_amt, ...}, ...]
        """
        if isinstance(balance_data, (int, float)):
            return float(balance_data)
        
        if isinstance(balance_data, dict):
            # 예수금 필드 (해외주식/해외선물 공통)
            for key in ["orderable_amount", "total_orderable", "fcurr_ord_able_amt", "ord_able_amt", "available", "balance", "cash_krw", "cash_usd"]:
                if key in balance_data and balance_data[key]:
                    try:
                        return float(balance_data[key])
                    except (ValueError, TypeError):
                        continue
        
        if isinstance(balance_data, list) and balance_data:
            # 첫 번째 항목에서 추출
            return self._extract_balance(balance_data[0])
        
        return 0.0

    def _get_price(
        self, 
        symbol: str, 
        symbol_data: Dict[str, Any],
        price_data: Any,
        context: ExecutionContext,
        node_id: str,
    ) -> Optional[float]:
        """
        종목의 현재가 추출
        
        우선순위:
        1. symbol_data에 price 포함
        2. price_data에서 조회
        """
        # 1. symbol_data에서 직접
        for key in ["price", "current_price", "close", "last"]:
            if key in symbol_data:
                try:
                    return float(symbol_data[key])
                except (ValueError, TypeError):
                    continue
        
        # 2. price_data에서 조회
        if price_data:
            if isinstance(price_data, dict):
                # {symbol: price} 또는 {symbol: {price: ...}}
                if symbol in price_data:
                    val = price_data[symbol]
                    if isinstance(val, (int, float)):
                        return float(val)
                    elif isinstance(val, dict):
                        for key in ["price", "current_price", "close", "last"]:
                            if key in val:
                                try:
                                    return float(val[key])
                                except (ValueError, TypeError):
                                    continue
            elif isinstance(price_data, list):
                # [{symbol: "AAPL", price: 150}, ...]
                for item in price_data:
                    if isinstance(item, dict) and item.get("symbol") == symbol:
                        for key in ["price", "current_price", "close", "last"]:
                            if key in item:
                                try:
                                    return float(item[key])
                                except (ValueError, TypeError):
                                    continue
        
        return None

    def _calc_fixed_percent(
        self,
        symbols: List[Dict[str, Any]],
        balance: float,
        max_percent: float,
        price_data: Any,
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        고정 비율 방식

        계좌의 max_percent%를 종목 수로 균등 분할
        예: balance=10000, max_percent=10, symbols=2개
            → 종목당 500 (10000 * 10% / 2)
        """
        num_symbols = len(symbols)
        total_invest = balance * (max_percent / 100.0)
        per_symbol_amount = total_invest / num_symbols

        orders = []
        total_amount = 0.0

        for sym_data in symbols:
            symbol = sym_data.get("symbol", "")
            exchange = sym_data.get("exchange", "")
            if not symbol:
                continue

            price = self._get_price(symbol, sym_data, price_data, context, node_id)

            if price and price > 0:
                qty = int(per_symbol_amount / price)
                if qty > 0:
                    orders.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "quantity": qty,
                        "price": price,
                        "allocation": round(max_percent / num_symbols, 2),
                    })
                    total_amount += qty * price
            else:
                context.log(
                    "warning",
                    f"No price for {symbol}, skipping position sizing",
                    node_id
                )

        context.log(
            "info",
            f"[fixed_percent] Allocated {len(orders)} symbols, "
            f"total_amount={total_amount:,.0f}, per_symbol={per_symbol_amount:,.0f}",
            node_id
        )

        return {
            "orders": orders,
            "total_amount": round(total_amount, 2),
            "method": "fixed_percent",
            "config": {
                "max_percent": max_percent,
                "per_symbol_amount": round(per_symbol_amount, 2),
            }
        }

    def _calc_fixed_amount(
        self,
        symbols: List[Dict[str, Any]],
        fixed_amount: Optional[float],
        price_data: Any,
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        고정 금액 방식

        각 종목에 fixed_amount 만큼 투자
        예: fixed_amount=1000, AAPL 가격=150
            → AAPL 수량 = 6주 (1000 / 150)
        """
        if not fixed_amount or fixed_amount <= 0:
            context.log("error", "fixed_amount is required for fixed_amount method", node_id)
            return self._empty_result()

        orders = []
        total_amount = 0.0

        for sym_data in symbols:
            symbol = sym_data.get("symbol", "")
            exchange = sym_data.get("exchange", "")
            if not symbol:
                continue

            price = self._get_price(symbol, sym_data, price_data, context, node_id)

            if price and price > 0:
                qty = int(fixed_amount / price)
                if qty > 0:
                    actual_invest = qty * price
                    orders.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "quantity": qty,
                        "price": price,
                        "allocation": round(actual_invest / fixed_amount * 100, 2),
                    })
                    total_amount += actual_invest
            else:
                context.log(
                    "warning",
                    f"No price for {symbol}, skipping position sizing",
                    node_id
                )

        context.log(
            "info",
            f"[fixed_amount] Allocated {len(orders)} symbols, "
            f"total_amount={total_amount:,.0f}, per_symbol={fixed_amount:,.0f}",
            node_id
        )

        return {
            "orders": orders,
            "total_amount": round(total_amount, 2),
            "method": "fixed_amount",
            "config": {
                "fixed_amount": fixed_amount,
            }
        }

    def _calc_fixed_quantity(
        self,
        symbols: List[Dict[str, Any]],
        fixed_quantity: int,
        price_data: Any,
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        고정 수량 방식

        각 종목에 지정된 수량을 할당
        예: fixed_quantity=1 → 모든 종목에 1계약씩
        """
        orders = []
        total_amount = 0.0

        for sym_data in symbols:
            symbol = sym_data.get("symbol", "")
            exchange = sym_data.get("exchange", "")
            if not symbol:
                continue

            price = self._get_price(symbol, sym_data, price_data, context, node_id)
            if not price or price <= 0:
                context.log(
                    "warning",
                    f"No price for {symbol}, skipping position sizing",
                    node_id
                )
                continue

            qty = fixed_quantity
            invest = qty * price

            orders.append({
                "symbol": symbol,
                "exchange": exchange,
                "quantity": qty,
                "price": price,
            })
            total_amount += invest

            context.log(
                "debug",
                f"[fixed_quantity] {symbol}: price={price:.2f}, qty={qty}, invest={invest:.0f}",
                node_id
            )

        context.log(
            "info",
            f"[fixed_quantity] Allocated {len(orders)} symbols, "
            f"total_amount={total_amount:,.0f}, fixed_quantity={fixed_quantity}",
            node_id
        )

        return {
            "orders": orders,
            "total_amount": round(total_amount, 2),
            "method": "fixed_quantity",
            "config": {
                "fixed_quantity": fixed_quantity,
            }
        }

    def _calc_kelly(
        self,
        symbols: List[Dict[str, Any]],
        balance: float,
        max_percent: float,
        kelly_fraction: float,
        price_data: Any,
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        켈리 공식 방식

        켈리 비율: f* = (p * b - q) / b
        - p: 승률, q: 패률 (1-p), b: 손익비

        symbol_data에 win_rate, profit_ratio 포함 필요
        없으면 기본값 사용 (win_rate=0.5, profit_ratio=1.5)

        kelly_fraction으로 보수적 조정 (0.25 = 1/4 켈리)
        max_percent로 상한선 제한
        """
        orders = []
        total_amount = 0.0

        for sym_data in symbols:
            symbol = sym_data.get("symbol", "")
            exchange = sym_data.get("exchange", "")
            if not symbol:
                continue

            # 승률/손익비 추출 (없으면 기본값)
            win_rate = float(sym_data.get("win_rate", 0.5))
            profit_ratio = float(sym_data.get("profit_ratio", 1.5))  # 이익/손실 비율

            # 켈리 비율 계산
            # f* = (p * b - q) / b = (win_rate * profit_ratio - (1 - win_rate)) / profit_ratio
            q = 1 - win_rate
            kelly_full = (win_rate * profit_ratio - q) / profit_ratio if profit_ratio > 0 else 0

            # 음수면 베팅하지 않음
            if kelly_full <= 0:
                context.log(
                    "info",
                    f"[kelly] {symbol}: negative kelly ({kelly_full:.2%}), skip",
                    node_id
                )
                continue

            # kelly_fraction 적용 및 max_percent 상한 제한
            kelly_adjusted = kelly_full * kelly_fraction
            final_percent = min(kelly_adjusted * 100, max_percent)

            invest_amount = balance * (final_percent / 100.0)
            price = self._get_price(symbol, sym_data, price_data, context, node_id)

            if price and price > 0:
                qty = int(invest_amount / price)
                if qty > 0:
                    orders.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "quantity": qty,
                        "price": price,
                        "allocation": round(final_percent, 2),
                    })
                    total_amount += qty * price

                    context.log(
                        "debug",
                        f"[kelly] {symbol}: win_rate={win_rate:.0%}, "
                        f"profit_ratio={profit_ratio:.1f}, kelly_full={kelly_full:.2%}, "
                        f"adjusted={final_percent:.2f}%, qty={qty}",
                        node_id
                    )
            else:
                context.log(
                    "warning",
                    f"No price for {symbol}, skipping position sizing",
                    node_id
                )

        context.log(
            "info",
            f"[kelly] Allocated {len(orders)} symbols, "
            f"total_amount={total_amount:,.0f}, kelly_fraction={kelly_fraction}",
            node_id
        )

        return {
            "orders": orders,
            "total_amount": round(total_amount, 2),
            "method": "kelly",
            "config": {
                "kelly_fraction": kelly_fraction,
                "max_percent": max_percent,
            }
        }

    def _calc_atr_based(
        self,
        symbols: List[Dict[str, Any]],
        balance: float,
        max_percent: float,
        atr_risk_percent: float,
        price_data: Any,
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        ATR 기반 리스크 관리 방식
        
        수량 = (계좌 × 리스크%) / ATR
        
        예: balance=10000, atr_risk_percent=1%, ATR=5
            → 수량 = (10000 × 0.01) / 5 = 20주
            → ATR만큼 가격이 하락해도 계좌의 1%만 손실
        
        symbol_data 또는 price_data에 atr 포함 필요
        없으면 가격의 2%를 ATR로 추정
        
        max_percent로 상한선 제한
        """
        orders = []
        total_amount = 0.0

        risk_amount = balance * (atr_risk_percent / 100.0)

        for sym_data in symbols:
            symbol = sym_data.get("symbol", "")
            exchange = sym_data.get("exchange", "")
            if not symbol:
                continue

            price = self._get_price(symbol, sym_data, price_data, context, node_id)
            if not price or price <= 0:
                context.log(
                    "warning",
                    f"No price for {symbol}, skipping position sizing",
                    node_id
                )
                continue

            # ATR 추출 (없으면 가격의 2%로 추정)
            atr = self._get_atr(symbol, sym_data, price_data)
            if atr is None or atr <= 0:
                atr = price * 0.02  # 기본값: 가격의 2%
                context.log(
                    "debug",
                    f"[atr_based] {symbol}: No ATR, using estimated {atr:.2f} (2% of price)",
                    node_id
                )

            # ATR 기반 수량 계산
            qty_by_atr = int(risk_amount / atr) if atr > 0 else 0
            invest_by_atr = qty_by_atr * price

            # max_percent 상한 적용
            max_invest = balance * (max_percent / 100.0)
            if invest_by_atr > max_invest:
                qty_by_atr = int(max_invest / price)
                invest_by_atr = qty_by_atr * price

            if qty_by_atr > 0:
                alloc_pct = round(invest_by_atr / balance * 100, 2)
                orders.append({
                    "symbol": symbol,
                    "exchange": exchange,
                    "quantity": qty_by_atr,
                    "price": price,
                    "allocation": alloc_pct,
                    "atr": round(atr, 4),
                })
                total_amount += invest_by_atr

                context.log(
                    "debug",
                    f"[atr_based] {symbol}: price={price:.2f}, atr={atr:.2f}, "
                    f"risk_amount={risk_amount:.0f}, qty={qty_by_atr}, "
                    f"invest={invest_by_atr:.0f}",
                    node_id
                )

        context.log(
            "info",
            f"[atr_based] Allocated {len(orders)} symbols, "
            f"total_amount={total_amount:,.0f}, risk_per_trade={risk_amount:,.0f}",
            node_id
        )

        return {
            "orders": orders,
            "total_amount": round(total_amount, 2),
            "method": "atr_based",
            "config": {
                "atr_risk_percent": atr_risk_percent,
                "max_percent": max_percent,
                "risk_amount": round(risk_amount, 2),
            }
        }

    def _get_atr(
        self,
        symbol: str,
        symbol_data: Dict[str, Any],
        price_data: Any,
    ) -> Optional[float]:
        """종목의 ATR 추출"""
        # 1. symbol_data에서 직접
        if "atr" in symbol_data:
            try:
                return float(symbol_data["atr"])
            except (ValueError, TypeError):
                pass
        
        # 2. price_data에서 조회
        if price_data:
            if isinstance(price_data, dict) and symbol in price_data:
                val = price_data[symbol]
                if isinstance(val, dict) and "atr" in val:
                    try:
                        return float(val["atr"])
                    except (ValueError, TypeError):
                        pass
            elif isinstance(price_data, list):
                for item in price_data:
                    if isinstance(item, dict) and item.get("symbol") == symbol and "atr" in item:
                        try:
                            return float(item["atr"])
                        except (ValueError, TypeError):
                            pass
        
        return None

    def _empty_result(self) -> Dict[str, Any]:
        """빈 결과 반환"""
        return {
            "orders": [],
            "total_amount": 0.0,
            "symbols": [],
            "method": None,
            "config": {},
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


class NewOrderNodeExecutor(NodeExecutorBase):
    """
    신규 주문 Executor (단일 종목)

    지원 노드:
    - OverseasStockNewOrderNode: 해외주식 신규주문 (COSAT00301)
    - OverseasFuturesNewOrderNode: 해외선물 신규주문 (CIDBT00100)

    입력 (order 객체):
    - order: {symbol, exchange, quantity, price}

    출력:
    - order_result: 주문 결과
    - order_id: 주문번호
    """

    # 해외주식 시장 코드 매핑
    STOCK_MARKET_CODES = {
        "NYSE": "81",
        "NASDAQ": "82",
        "AMEX": "83",
        "81": "81",
        "82": "82",
        "83": "83",
    }

    # 해외주식 호가 유형 코드 매핑
    STOCK_PRICE_TYPE_CODES = {
        "limit": "00",
        "market": "03",
        "LOO": "M1",
        "LOC": "M2",
        "MOO": "M3",
        "MOC": "M4",
    }

    # 해외선물 주문 유형 코드 매핑
    FUTURES_ORDER_TYPE_CODES = {
        "market": "1",
        "limit": "2",
    }

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """신규 주문 실행"""

        # dry_run: LS API 미호출, 모의 응답 반환
        if context.is_dry_run:
            import uuid
            order_id = f"DRYRUN-{uuid.uuid4()}"
            context.log(
                "info",
                f"[dry_run] {node_type} simulated order → {order_id}",
                node_id,
            )
            return {
                "order_id": order_id,
                "status": "simulated",
                "dry_run": True,
                "requested": config,
            }

        # M-10: Risk halt 체크 - critical risk event로 주문 중단
        if context.is_risk_halted:
            context.log(
                "warning",
                f"{node_type}: 위험 이벤트로 인해 주문이 중단되었습니다 (risk_halt=True)",
                node_id,
            )
            return self._error_result("Order halted by risk event")

        # === 1. Connection 확인 ===
        broker_connection = config.get("connection")
        if not broker_connection:
            context.log("error", f"{node_type}: connection이 자동 주입되지 않았습니다. 매칭되는 BrokerNode를 확인하세요.", node_id)
            return self._error_result("Missing connection - no matching BrokerNode found")

        if not isinstance(broker_connection, dict):
            context.log("error", f"{node_type}: connection 타입 오류: {type(broker_connection)}", node_id)
            return self._error_result("Invalid connection type")

        # 노드 타입에서 상품 결정
        if "KoreaStock" in node_type:
            product = "korea_stock"
        elif node_type.startswith("Stock"):
            product = "overseas_stock"
        elif node_type.startswith("Futures"):
            product = "overseas_futures"
        else:
            product = broker_connection.get("product", "overseas_stock")

        paper_trading = broker_connection.get("paper_trading", False) if product != "korea_stock" else False

        # === 2. 바인딩 표현식 평가 ===
        config = evaluate_all_bindings(config, context, node_id)

        # === 3. 주문 정보 추출 (order 단일 객체) ===
        order = config.get("order")
        side = config.get("side", "buy")
        order_type = config.get("order_type", "limit")

        # order 정규화
        normalized_order = self._normalize_order(order, config)

        if not normalized_order:
            context.log("warning", f"{node_type}: 주문할 종목이 없습니다", node_id)
            return self._empty_result()

        context.log(
            "info",
            f"{node_type}: {normalized_order['symbol']}, side={side}, type={order_type}, qty={normalized_order['quantity']}",
            node_id
        )

        # === 3.3. 제외 종목 안전장치: ExclusionListNode 출력 확인 ===
        if not config.get("ignore_exclusion", False):
            symbol = normalized_order["symbol"]
            is_excluded, reason = self._check_exclusion_list(symbol, context)
            if is_excluded:
                context.log(
                    "warning",
                    f"제외 종목 주문 차단: {symbol}" + (f" (사유: {reason})" if reason else ""),
                    node_id,
                )
                return self._order_result(
                    False, symbol, normalized_order["exchange"], side,
                    normalized_order["quantity"], normalized_order["price"],
                    f"Blocked by exclusion list" + (f": {reason}" if reason else ""),
                )

        # === 3.5. Drawdown 보호: risk_tracker가 활성화되어 있으면 체크 ===
        risk_tracker = context.risk_tracker
        if risk_tracker and side == "buy":
            # drawdown_threshold_pct: 사용자 설정 가능, 기본 10%
            drawdown_threshold = config.get("drawdown_threshold_pct", 10.0)
            symbol = normalized_order["symbol"]
            if risk_tracker.check_drawdown_threshold(symbol, drawdown_threshold):
                context.log(
                    "warning",
                    f"{node_type}: {symbol} drawdown이 {drawdown_threshold}%를 초과하여 매수 주문을 차단합니다.",
                    node_id,
                )
                return self._order_result(
                    False, symbol, normalized_order["exchange"], side,
                    normalized_order["quantity"], normalized_order["price"],
                    f"Drawdown exceeds {drawdown_threshold}% threshold"
                )

        # === 4. LS 로그인 ===
        credential = context.get_credential()
        if not credential:
            context.log("error", f"{node_type}: Credential not found", node_id)
            return self._error_result("Missing credentials")

        appkey = credential.get("appkey")
        appsecret = credential.get("appsecret")

        if not appkey or not appsecret:
            context.log("error", f"{node_type}: appkey/appsecret not found", node_id)
            return self._error_result("Missing appkey/appsecret")

        try:
            ls, success, error = ensure_ls_login(
                appkey, appsecret, paper_trading, context, node_id,
                product=product,
                caller_name=f"{node_type}"
            )
            if not success:
                return self._error_result(error)

            # === 5. 상품별 주문 실행 ===
            if product == "overseas_stock":
                return await self._execute_overseas_stock(
                    ls, normalized_order, side, order_type, config, context, node_id
                )
            elif product in ("overseas_futures", "overseas_futureoption"):
                return await self._execute_overseas_futures(
                    ls, normalized_order, side, order_type, config, context, node_id
                )
            elif product == "korea_stock":
                return await self._execute_korea_stock(
                    ls, normalized_order, side, order_type, config, context, node_id
                )
            else:
                context.log("error", f"{node_type}: Unsupported product: {product}", node_id)
                return self._error_result(f"Unsupported product: {product}")

        except Exception as e:
            context.log("error", f"{node_type}: Unexpected error: {e}", node_id)
            return self._error_result(str(e))

    def _normalize_order(
        self,
        order_raw: Any,
        config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        order 객체를 정규화 (단일 종목)

        입력: {symbol, exchange, quantity, price}
        출력: {symbol, exchange, quantity, price} (검증된 객체) 또는 None
        """
        if not order_raw:
            return None

        if not isinstance(order_raw, dict):
            return None

        symbol = order_raw.get("symbol", "")
        if not symbol:
            return None

        exchange = order_raw.get("exchange", "NASDAQ")
        try:
            quantity = int(float(order_raw.get("quantity", 0)))
        except (ValueError, TypeError):
            quantity = 0
        try:
            price = float(order_raw.get("price", 0.0))
        except (ValueError, TypeError):
            price = 0.0

        # quantity가 없으면 None
        if quantity <= 0:
            return None

        # price 필드 자동 탐색 (MarketDataNode 바인딩 시)
        if price <= 0:
            for field in ["last_price", "close", "current_price"]:
                if field in order_raw and order_raw[field]:
                    try:
                        price = float(order_raw[field])
                        break
                    except (ValueError, TypeError):
                        pass

        return {
            "symbol": symbol,
            "exchange": exchange,
            "quantity": int(quantity),
            "price": float(price) if price else 0.0,
        }

    async def _execute_overseas_stock(
        self,
        ls,
        order: Dict[str, Any],
        side: str,
        order_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """해외주식 신규주문 실행 (COSAT00301) - 단일 종목

        해외주식 주문 규칙:
        - 매수: 지정가(00)만 가능 → 시장가 요청 시 현재가로 지정가 변환
        - 매도: 시장가(03), 지정가(00) 둘 다 가능
        """
        from programgarden_finance.ls.overseas_stock.order.COSAT00301.blocks import COSAT00301InBlock1

        from datetime import datetime as dt

        symbol = order["symbol"]
        exchange = order["exchange"]
        qty = order["quantity"]
        price = order["price"]

        # 주문유형코드: 01=매도, 02=매수
        ord_ptn_code = "01" if side == "sell" else "02"

        # 호가유형코드
        price_type = config.get("price_type", order_type)
        ordprc_ptn_code = self.STOCK_PRICE_TYPE_CODES.get(price_type, "00")

        # 해외주식 매수는 지정가만 가능 - 시장가 요청 시 지정가로 변환
        is_buy = (side == "buy")
        if is_buy and ordprc_ptn_code == "03":
            context.log("warning", "주문 타입 자동 변환: 해외주식 매수는 시장가 불가 → 현재가 기준 지정가 주문으로 전환", node_id)
            ordprc_ptn_code = "00"

        ord_mkt_code = self.STOCK_MARKET_CODES.get(exchange, "82")

        # 매수 지정가 주문인데 가격이 없으면 현재가 조회
        if is_buy and ordprc_ptn_code == "00" and price <= 0:
            try:
                current_price = await self._get_current_price(ls, symbol, ord_mkt_code, context, node_id)
                if current_price and current_price > 0:
                    price = current_price
                    context.log("info", f"현재가 조회: {symbol} = ${price}", node_id)
                else:
                    context.log("warning", f"현재가 조회 실패: {symbol}", node_id)
                    return self._order_result(False, symbol, exchange, side, qty, 0, "현재가 조회 실패")
            except Exception as e:
                context.log("warning", f"현재가 조회 예외: {symbol} - {e}", node_id)
                return self._order_result(False, symbol, exchange, side, qty, 0, str(e))

        # 매도 시장가 주문은 가격 0
        if side == "sell" and ordprc_ptn_code == "03":
            price = 0.0

        try:
            order_api = ls.overseas_stock().주문().cosat00301(
                COSAT00301InBlock1(
                    RecCnt=1,
                    OrdPtnCode=ord_ptn_code,
                    OrdMktCode=ord_mkt_code,
                    IsuNo=symbol,
                    OrdQty=qty,
                    OvrsOrdPrc=price,
                    OrdprcPtnCode=ordprc_ptn_code,
                ),
            )

            response = await order_api.req_async()

            # 디버그: 응답 전체 출력
            context.log("debug", f"COSAT00301 response: rsp_cd={response.rsp_cd}, rsp_msg={response.rsp_msg}", node_id)

            if response.error_msg:
                context.log("warning", f"Order failed: {symbol} - {response.error_msg}", node_id)
                return self._order_result(False, symbol, exchange, side, qty, price, response.error_msg)

            order_no = ""
            if response.block2:
                order_no = str(response.block2.OrdNo) if response.block2.OrdNo else ""

            # 주문번호가 없으면 경고 (장 마감, 서버 오류 등)
            if not order_no:
                msg = response.rsp_msg or "주문번호 없음"
                context.log("warning", f"Order submitted but no OrderNo returned: {symbol} - {msg}", node_id)
                return self._order_result(False, symbol, exchange, side, qty, price, f"Empty OrderNo: {msg}")

            context.log("info", f"Order submitted: {symbol} {side} {qty}@{price} → order_id={order_no}", node_id)

            # Record workflow order for FIFO tracking (OrderNo가 있는 경우만)
            context.record_workflow_order(
                order_no=order_no,
                order_date=dt.now().strftime("%Y%m%d"),
                symbol=symbol,
                exchange=exchange,
                side=side,
                quantity=qty,
                price=price,
                node_id=node_id,
            )

            return self._order_result(True, symbol, exchange, side, qty, price, None, order_no)

        except Exception as e:
            context.log("warning", f"Order exception: {symbol} - {e}", node_id)
            return self._order_result(False, symbol, exchange, side, qty, price, str(e))

        return {
            "order_result": {
                "success": success_count > 0,
                "total": len(orders),
                "success_count": success_count,
                "fail_count": fail_count,
                "side": side,
                "order_type": order_type,
                "product": "overseas_stock",
            },
            "order_ids": order_ids,
            "submitted_orders": submitted_orders,
        }

    async def _get_current_price(
        self,
        ls,
        symbol: str,
        market_code: str,
        context: "ExecutionContext",
        node_id: str,
    ) -> Optional[float]:
        """해외주식 현재가 조회 (g3101)
        
        Args:
            ls: LS 클라이언트
            symbol: 종목코드
            market_code: 시장코드 (81=NYSE, 82=NASDAQ)
            context: 실행 컨텍스트
            node_id: 노드 ID
            
        Returns:
            현재가 (조회 실패 시 None)
        """
        try:
            from programgarden_finance import g3101

            
            # 미해석 표현식 가드 (auto-iterate 미발동 시 {{ item.xxx }} 그대로 넘어옴)
            if "{{" in symbol or not symbol or len(symbol) > 10:
                context.log("debug", f"_get_current_price: invalid symbol '{symbol}', skipping g3101", node_id)
                return None

            keysymbol = f"{market_code}{symbol}"

            result = ls.overseas_stock().market().현재가조회(
                g3101.G3101InBlock(
                    delaygb="R",
                    keysymbol=keysymbol,
                    exchcd=market_code,
                    symbol=symbol,
                ),
            )
            
            response = await result.req_async()
            
            if response.error_msg:
                context.log("debug", f"현재가 조회 실패: {symbol} - {response.error_msg}", node_id)
                return None
            
            if response.block and response.block.price:
                return float(response.block.price)
            
            return None
            
        except Exception as e:
            context.log("debug", f"현재가 조회 예외: {symbol} - {e}", node_id)
            return None

    async def _sync_fills_after_market_order(
        self,
        ls,
        submitted_orders: list,
        context: ExecutionContext,
        node_id: str,
    ) -> None:
        """시장가 주문 후 체결내역 동기화 (FIFO 포지션 생성)
        
        시장가 주문은 즉시 체결되므로, 잠시 대기 후 체결내역을 조회하여
        FIFO 포지션을 생성합니다.
        """
        try:
            # 체결 처리 대기 (5초) - AccountTracker와의 Rate Limit 충돌 방지
            await asyncio.sleep(5)
            
            from programgarden_finance import COSAQ00102

            from datetime import datetime
            
            today = datetime.now().strftime("%Y%m%d")
            
            context.log("debug", f"Querying fill history for {len(submitted_orders)} orders", node_id)
            
            # 체결내역 조회 (COSAQ00102 = 주문체결내역조회)
            # 참고: run_cosaq00102.py example
            response = ls.overseas_stock().accno().cosaq00102(
                body=COSAQ00102.COSAQ00102InBlock1(
                    RecCnt=1,
                    QryTpCode="1",  # 계좌별
                    BkseqTpCode="1",  # 역순
                    OrdMktCode="00",  # 전체 시장
                    BnsTpCode="0",  # 전체 (매수/매도)
                    IsuNo="",  # 전체 종목
                    SrtOrdNo=999999999,  # 역순 시작
                    OrdDt=today,  # 오늘 날짜
                    ExecYn="1",  # 체결만 조회
                    CrcyCode="000",  # 전체 통화
                    ThdayBnsAppYn="0",
                    LoanBalHldYn="0",
                ),
            )
            result = await response.req_async()
            
            context.log("debug", f"Fill history query result: block3={len(result.block3) if result and result.block3 else 0} items", node_id)
            
            if not result or not result.block3:
                context.log("debug", "No fill history found after market order", node_id)
                return
            
            # 주문번호 → 주문정보 매핑
            order_info_map = {
                order.get("order_id"): order
                for order in submitted_orders
                if order.get("status") == "submitted" and order.get("order_id")
            }
            
            # 시장코드 → 거래소 매핑
            market_to_exchange = {'81': 'NYSE', '82': 'NASDAQ', '83': 'AMEX'}
            
            fill_history = []
            for item in result.block3:
                # COSAQ00102OutBlock3 필드명 사용
                order_no = str(getattr(item, 'OrdNo', 0))
                
                # 방금 제출한 주문인지 확인
                if order_no not in order_info_map:
                    continue
                
                order_info = order_info_map[order_no]
                fill_price = float(getattr(item, 'OvrsExecPrc', 0) or getattr(item, 'OvrsOrdPrc', 0))
                fill_qty = int(getattr(item, 'ExecQty', 0))
                symbol = order_info.get("symbol", "")
                exchange = order_info.get("exchange", "NASDAQ")
                side = order_info.get("side", "buy")
                fill_time = str(getattr(item, 'ExecTime', '') or getattr(item, 'OrdTime', ''))
                
                if fill_price > 0 and fill_qty > 0 and symbol:
                    fill_history.append({
                        "order_no": order_no,
                        "order_date": today,
                        "symbol": symbol,
                        "exchange": exchange,
                        "side": side,
                        "quantity": fill_qty,
                        "price": fill_price,
                        "fill_time": fill_time,
                    })
                    context.log("debug", f"Found fill: {symbol} {side} {fill_qty}@{fill_price}", node_id)
            
            if fill_history:
                # FIFO 포지션 생성
                processed = context.sync_workflow_fills_from_history(fill_history)
                if processed > 0:
                    context.log("info", f"Created {processed} FIFO positions from market order fills", node_id)
                else:
                    context.log("debug", "No new FIFO positions created (already processed)", node_id)
            else:
                context.log("debug", "No fills found for submitted orders", node_id)
                
        except Exception as e:
            context.log("warning", f"Failed to sync fills after market order: {e}", node_id)

    async def _execute_overseas_futures(
        self,
        ls,
        order: Dict[str, Any],
        side: str,
        order_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """해외선물 신규주문 실행 (CIDBT00100) - 단일 종목"""
        from programgarden_finance.ls.overseas_futureoption.order.CIDBT00100.blocks import CIDBT00100InBlock1

        from datetime import datetime as dt

        symbol = order["symbol"]
        exchange = order["exchange"]
        qty = order["quantity"]
        price = order["price"]

        # 매매구분코드: 1=매도, 2=매수
        bns_tp_code = "1" if side == "sell" else "2"

        # 주문유형코드: 1=시장가, 2=지정가
        abrd_futs_ord_ptn_code = self.FUTURES_ORDER_TYPE_CODES.get(order_type, "2")

        # 공통 설정
        expiry_month = config.get("expiry_month", "")
        today = dt.now().strftime("%Y%m%d")

        # 시장가 주문은 가격 0으로 전송
        if abrd_futs_ord_ptn_code == "1":  # 시장가
            price = 0.0

        try:
            order_api = ls.overseas_futureoption().order().CIDBT00100(
                CIDBT00100InBlock1(
                    RecCnt=1,
                    OrdDt=today,
                    IsuCodeVal=symbol,
                    FutsOrdTpCode="1",  # 1=신규
                    BnsTpCode=bns_tp_code,
                    AbrdFutsOrdPtnCode=abrd_futs_ord_ptn_code,
                    CrcyCode="",
                    OvrsDrvtOrdPrc=price,
                    CndiOrdPrc=0.0,
                    OrdQty=qty,
                    PrdtCode="000000",
                    DueYymm=expiry_month,
                    ExchCode=exchange,
                ),
            )

            response = await order_api.req_async()

            # 디버그: 응답 전체 출력
            context.log("debug", f"CIDBT00100 response: rsp_cd={response.rsp_cd}, rsp_msg={response.rsp_msg}", node_id)

            if response.error_msg:
                context.log("warning", f"Order failed: {symbol} - {response.error_msg}", node_id)
                return self._order_result(False, symbol, exchange, side, qty, price, response.error_msg)

            order_no = ""
            if response.block2:
                # 해외선물 주문번호 필드: OvrsFutsOrdNo
                order_no = str(response.block2.OvrsFutsOrdNo) if hasattr(response.block2, "OvrsFutsOrdNo") and response.block2.OvrsFutsOrdNo else ""

            # 주문번호가 없으면 경고 + 기록 거부
            if not order_no:
                msg = response.rsp_msg or "주문번호 없음"
                context.log("warning", f"Futures order submitted but no OrderNo returned: {symbol} - {msg}", node_id)
                return self._order_result(False, symbol, exchange, side, qty, price, f"Empty OrderNo: {msg}")

            context.log("info", f"Futures order submitted: {symbol} {side} {qty}@{price} → order_id={order_no}", node_id)

            # Record workflow order for FIFO tracking (OrderNo가 있는 경우만)
            context.record_workflow_order(
                order_no=order_no,
                order_date=dt.now().strftime("%Y%m%d"),
                symbol=symbol,
                exchange=exchange,
                side=side,
                quantity=qty,
                price=price,
                node_id=node_id,
            )

            return self._order_result(True, symbol, exchange, side, qty, price, None, order_no)

        except Exception as e:
            context.log("warning", f"Futures order exception: {symbol} - {e}", node_id)
            return self._order_result(False, symbol, exchange, side, qty, price, str(e))

    def _check_exclusion_list(
        self,
        symbol: str,
        context: ExecutionContext,
    ) -> tuple:
        """같은 워크플로우 내 ExclusionListNode의 excluded 출력 확인

        Returns:
            (is_excluded: bool, reason: str)
        """
        for nid, ntype in context._node_types.items():
            if ntype == "ExclusionListNode":
                outputs = context.get_all_outputs(nid)
                if not outputs:
                    continue
                excluded = outputs.get("excluded", [])
                excluded_symbols = {s["symbol"] for s in excluded if isinstance(s, dict) and s.get("symbol")}
                if symbol in excluded_symbols:
                    reason = outputs.get("reasons", {}).get(symbol, "")
                    return True, reason
        return False, ""

    async def _execute_korea_stock(
        self,
        ls,
        order: Dict[str, Any],
        side: str,
        order_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """국내주식 신규주문 실행 (CSPAT00601)

        국내주식 주문 규칙:
        - BnsTpCode: 1=매도, 2=매수
        - OrdprcPtnCode: 00=지정가, 03=시장가
        - 가격은 KRW 정수
        """
        from programgarden_finance.ls.korea_stock.order.CSPAT00601.blocks import CSPAT00601InBlock1

        symbol = order["symbol"]
        qty = order["quantity"]
        price = order["price"]

        # 매매구분: 1=매도, 2=매수
        bns_tp_code = "1" if side == "sell" else "2"

        # 호가유형코드
        korea_price_type_map = {
            "limit": "00",
            "market": "03",
        }
        ordprc_ptn_code = korea_price_type_map.get(order_type, "00")

        # 시장가 주문 시 가격 0
        ord_prc = 0.0 if ordprc_ptn_code == "03" else float(price)

        try:
            body = CSPAT00601InBlock1(
                IsuNo=symbol,
                OrdQty=qty,
                OrdPrc=ord_prc,
                BnsTpCode=bns_tp_code,
                OrdprcPtnCode=ordprc_ptn_code,
            )

            order_api = ls.korea_stock().order().cspat00601(body=body)
            response = await order_api.req_async()

            if response.error_msg:
                context.log("warning", f"Korea stock order failed: {response.error_msg}", node_id)
                return self._order_result(
                    False, symbol, "KRX", side, qty, price,
                    response.error_msg
                )

            order_no = ""
            if response.block2:
                order_no = str(response.block2.OrdNo) if response.block2.OrdNo else ""

            context.log(
                "info",
                f"Korea stock order: {side} {symbol} qty={qty} price={ord_prc} → OrdNo={order_no}",
                node_id
            )

            result = self._order_result(
                True, symbol, "KRX", side, qty, price
            )
            result["order_result"]["order_id"] = order_no
            result["order_result"]["product"] = "korea_stock"
            return result

        except Exception as e:
            context.log("warning", f"Korea stock order exception: {e}", node_id)
            return self._order_result(
                False, symbol, "KRX", side, qty, price, str(e)
            )

    def _order_result(
        self,
        success: bool,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        price: float,
        error: Optional[str] = None,
        order_id: str = "",
    ) -> Dict[str, Any]:
        """단일 주문 결과 반환"""
        return {
            "order_result": {
                "success": success,
                "symbol": symbol,
                "exchange": exchange,
                "side": side,
                "quantity": quantity,
                "price": price,
                "status": "submitted" if success else "failed",
                "error": error,
            },
            "order_id": order_id,
        }

    def _empty_result(self) -> Dict[str, Any]:
        """빈 결과 반환"""
        return {
            "order_result": {
                "success": False,
                "error": "No order to submit",
            },
            "order_id": "",
        }

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """에러 결과 반환"""
        return {
            "order_result": {
                "success": False,
                "error": error_msg,
            },
            "order_id": "",
        }


class ModifyOrderNodeExecutor(NodeExecutorBase):
    """
    주문 정정 Executor

    지원 노드:
    - OverseasStockModifyOrderNode: 해외주식 정정주문 (COSAT00311)
    - OverseasFuturesModifyOrderNode: 해외선물 정정주문 (CIDBT00200)

    입력:
    - original_order_id: 원주문번호 (필수)
    - symbol: 종목코드
    - exchange: 거래소
    - new_quantity: 정정할 수량 (선택)
    - new_price: 정정할 가격 (선택)
    """

    # 해외주식 시장 코드 매핑
    STOCK_MARKET_CODES = {
        "NYSE": "81",
        "NASDAQ": "82",
        "AMEX": "83",
    }

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """주문 정정 실행"""

        # dry_run: LS API 미호출, 모의 응답 반환
        if context.is_dry_run:
            import uuid
            order_id = f"DRYRUN-{uuid.uuid4()}"
            context.log(
                "info",
                f"[dry_run] {node_type} simulated modify → {order_id}",
                node_id,
            )
            return {
                "order_id": order_id,
                "status": "simulated",
                "dry_run": True,
                "requested": config,
            }

        # M-10: Risk halt 체크
        if context.is_risk_halted:
            context.log("warning", f"{node_type}: 위험 이벤트로 인해 주문 정정이 중단되었습니다", node_id)
            return self._error_result("Order modify halted by risk event")

        # === 1. Connection 확인 ===
        broker_connection = config.get("connection")
        if not broker_connection:
            context.log("error", f"{node_type}: connection이 자동 주입되지 않았습니다. 매칭되는 BrokerNode를 확인하세요.", node_id)
            return self._error_result("Missing connection - no matching BrokerNode found")

        if not isinstance(broker_connection, dict):
            context.log("error", f"{node_type}: connection 타입 오류: {type(broker_connection)}", node_id)
            return self._error_result("Invalid connection type")

        # 노드 타입에서 상품 결정
        if "KoreaStock" in node_type:
            product = "korea_stock"
        elif node_type.startswith("Stock"):
            product = "overseas_stock"
        elif node_type.startswith("Futures"):
            product = "overseas_futures"
        else:
            product = broker_connection.get("product", "overseas_stock")
        paper_trading = broker_connection.get("paper_trading", False) if product != "korea_stock" else False

        # === 2. 바인딩 표현식 평가 ===
        config = evaluate_all_bindings(config, context, node_id)

        # === 3. 정정 정보 추출 ===
        original_order_id = config.get("original_order_id")
        symbol = config.get("symbol", "")
        exchange = config.get("exchange", "KRX" if product == "korea_stock" else "NASDAQ")
        new_quantity = config.get("new_quantity")
        new_price = config.get("new_price")
        side = config.get("side", "buy")
        
        if not original_order_id:
            context.log("error", f"{node_type}: original_order_id가 필수입니다", node_id)
            return self._error_result("Missing original_order_id")
        
        if not symbol:
            context.log("error", f"{node_type}: symbol이 필수입니다", node_id)
            return self._error_result("Missing symbol")
        
        context.log(
            "info", 
            f"{node_type}: symbol={symbol}, original_order={original_order_id}",
            node_id
        )
        
        # === 4. LS 로그인 ===
        credential = context.get_credential()
        if not credential:
            context.log("error", f"{node_type}: Credential not found", node_id)
            return self._error_result("Missing credentials")
        
        appkey = credential.get("appkey")
        appsecret = credential.get("appsecret")
        
        if not appkey or not appsecret:
            context.log("error", f"{node_type}: appkey/appsecret not found", node_id)
            return self._error_result("Missing appkey/appsecret")
        
        try:
            ls, success, error = ensure_ls_login(
                appkey, appsecret, paper_trading, context, node_id,
                product=product,
                caller_name=node_type
            )
            if not success:
                return self._error_result(error)
            
            # === 5. 상품별 정정 실행 ===
            if product == "overseas_stock":
                return await self._modify_overseas_stock(
                    ls, original_order_id, symbol, exchange, new_quantity, new_price, side, config, context, node_id
                )
            elif product in ("overseas_futures", "overseas_futureoption"):
                return await self._modify_overseas_futures(
                    ls, original_order_id, symbol, exchange, new_quantity, new_price, side, config, context, node_id
                )
            elif product == "korea_stock":
                return await self._modify_korea_stock(
                    ls, original_order_id, symbol, new_quantity, new_price, config, context, node_id
                )
            else:
                context.log("error", f"{node_type}: Unsupported product: {product}", node_id)
                return self._error_result(f"Unsupported product: {product}")
                
        except Exception as e:
            context.log("error", f"{node_type}: Unexpected error: {e}", node_id)
            return self._error_result(str(e))

    async def _modify_overseas_stock(
        self,
        ls,
        original_order_id: str,
        symbol: str,
        exchange: str,
        new_quantity: Optional[int],
        new_price: Optional[float],
        side: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """해외주식 정정주문 실행 (COSAT00311)"""
        from programgarden_finance.ls.overseas_stock.order.COSAT00311.blocks import COSAT00311InBlock1

        
        # 시장 코드 결정
        ord_mkt_code = self.STOCK_MARKET_CODES.get(exchange, "82")
        
        # 호가유형코드 (지정가)
        ordprc_ptn_code = config.get("price_type_code", "00")
        
        try:
            order_api = ls.overseas_stock().주문().cosat00311(
                COSAT00311InBlock1(
                    RecCnt=1,
                    OrdPtnCode="07",  # 정정주문
                    OrgOrdNo=int(original_order_id),
                    OrdMktCode=ord_mkt_code,
                    IsuNo=symbol,
                    OrdQty=new_quantity or 0,
                    OvrsOrdPrc=new_price or 0.0,
                    OrdprcPtnCode=ordprc_ptn_code,
                ),
            )
            
            response = await order_api.req_async()
            
            if response.error_msg:
                context.log("warning", f"Modify order failed: {response.error_msg}", node_id)
                return {
                    "modify_result": {
                        "success": False,
                        "error": response.error_msg,
                        "original_order_id": original_order_id,
                        "product": "overseas_stock",
                    },
                    "modified_order": None,
                }
            
            new_order_no = ""
            if response.block2:
                new_order_no = str(response.block2.OrdNo) if response.block2.OrdNo else ""
            
            context.log(
                "info",
                f"Order modified: {symbol} original={original_order_id} → new={new_order_no}",
                node_id
            )
            
            return {
                "modify_result": {
                    "success": True,
                    "original_order_id": original_order_id,
                    "new_order_id": new_order_no,
                    "product": "overseas_stock",
                },
                "modified_order": {
                    "symbol": symbol,
                    "exchange": exchange,
                    "original_order_id": original_order_id,
                    "new_order_id": new_order_no,
                    "new_quantity": new_quantity,
                    "new_price": new_price,
                    "status": "modified",
                },
            }
            
        except Exception as e:
            context.log("warning", f"Modify order exception: {e}", node_id)
            return {
                "modify_result": {
                    "success": False,
                    "error": str(e),
                    "original_order_id": original_order_id,
                    "product": "overseas_stock",
                },
                "modified_order": None,
            }

    async def _modify_overseas_futures(
        self,
        ls,
        original_order_id: str,
        symbol: str,
        exchange: str,
        new_quantity: Optional[int],
        new_price: Optional[float],
        side: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """해외선물 정정주문 실행 (CIDBT00900)"""
        from programgarden_finance.ls.overseas_futureoption.order.CIDBT00900.blocks import CIDBT00900InBlock1

        from datetime import datetime
        
        # 매매구분코드: 1=매도, 2=매수
        bns_tp_code = "1" if side == "sell" else "2"
        
        today = datetime.now().strftime("%Y%m%d")
        expiry_month = config.get("expiry_month", "")
        exchange_code = config.get("exchange_code", exchange)
        
        try:
            order_api = ls.overseas_futureoption().order().CIDBT00900(
                CIDBT00900InBlock1(
                    RecCnt=1,
                    OrdDt=today,
                    OvrsFutsOrgOrdNo=str(original_order_id),
                    IsuCodeVal=symbol,
                    FutsOrdTpCode="2",  # 정정
                    BnsTpCode=bns_tp_code,
                    FutsOrdPtnCode="2",  # 지정가
                    CrcyCodeVal="",
                    OvrsDrvtOrdPrc=new_price or 0.0,
                    CndiOrdPrc=0.0,
                    OrdQty=new_quantity or 0,
                    OvrsDrvtPrdtCode="000000",
                    DueYymm=expiry_month,
                    ExchCode=exchange_code,
                ),
            )
            
            response = await order_api.req_async()
            
            if response.error_msg:
                context.log("warning", f"Modify futures order failed: {response.error_msg}", node_id)
                return {
                    "modify_result": {
                        "success": False,
                        "error": response.error_msg,
                        "original_order_id": original_order_id,
                        "product": "overseas_futures",
                    },
                    "modified_order": None,
                }
            
            new_order_no = ""
            if response.block2:
                # 해외선물 정정 주문번호 필드: OvrsFutsOrdNo
                new_order_no = str(response.block2.OvrsFutsOrdNo) if hasattr(response.block2, "OvrsFutsOrdNo") and response.block2.OvrsFutsOrdNo else ""

            context.log(
                "info",
                f"Futures order modified: {symbol} original={original_order_id} → new={new_order_no}",
                node_id
            )
            
            return {
                "modify_result": {
                    "success": True,
                    "original_order_id": original_order_id,
                    "new_order_id": new_order_no,
                    "product": "overseas_futures",
                },
                "modified_order": {
                    "symbol": symbol,
                    "exchange": exchange_code,
                    "expiry_month": expiry_month,
                    "original_order_id": original_order_id,
                    "new_order_id": new_order_no,
                    "new_quantity": new_quantity,
                    "new_price": new_price,
                    "status": "modified",
                },
            }
            
        except Exception as e:
            context.log("warning", f"Modify futures order exception: {e}", node_id)
            return {
                "modify_result": {
                    "success": False,
                    "error": str(e),
                    "original_order_id": original_order_id,
                    "product": "overseas_futures",
                },
                "modified_order": None,
            }

    async def _modify_korea_stock(
        self,
        ls,
        original_order_id: str,
        symbol: str,
        new_quantity: Optional[int],
        new_price: Optional[float],
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """국내주식 정정주문 실행 (CSPAT00701)"""
        from programgarden_finance.ls.korea_stock.order.CSPAT00701.blocks import CSPAT00701InBlock1

        # 호가유형코드 (기본: 지정가)
        ordprc_ptn_code = config.get("price_type_code", "00")

        try:
            body = CSPAT00701InBlock1(
                OrgOrdNo=int(original_order_id),
                IsuNo=symbol,
                OrdQty=new_quantity or 0,
                OrdprcPtnCode=ordprc_ptn_code,
                OrdPrc=float(new_price) if new_price else 0.0,
            )

            order_api = ls.korea_stock().order().cspat00701(body=body)
            response = await order_api.req_async()

            if response.error_msg:
                context.log("warning", f"Korea stock modify order failed: {response.error_msg}", node_id)
                return {
                    "modify_result": {
                        "success": False,
                        "error": response.error_msg,
                        "original_order_id": original_order_id,
                        "product": "korea_stock",
                    },
                    "modified_order": None,
                }

            new_order_no = ""
            if response.block2:
                new_order_no = str(response.block2.OrdNo) if response.block2.OrdNo else ""

            context.log(
                "info",
                f"Korea stock order modified: {symbol} original={original_order_id} → new={new_order_no}",
                node_id
            )

            return {
                "modify_result": {
                    "success": True,
                    "original_order_id": original_order_id,
                    "new_order_id": new_order_no,
                    "product": "korea_stock",
                },
                "modified_order": {
                    "symbol": symbol,
                    "exchange": "KRX",
                    "original_order_id": original_order_id,
                    "new_order_id": new_order_no,
                    "new_quantity": new_quantity,
                    "new_price": new_price,
                    "status": "modified",
                },
            }

        except Exception as e:
            context.log("warning", f"Korea stock modify order exception: {e}", node_id)
            return {
                "modify_result": {
                    "success": False,
                    "error": str(e),
                    "original_order_id": original_order_id,
                    "product": "korea_stock",
                },
                "modified_order": None,
            }

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """에러 결과 반환"""
        return {
            "modify_result": {
                "success": False,
                "error": error_msg,
            },
            "modified_order": None,
        }


class CancelOrderNodeExecutor(NodeExecutorBase):
    """
    주문 취소 Executor

    지원 노드:
    - OverseasStockCancelOrderNode: 해외주식 취소주문 (COSAT00303)
    - OverseasFuturesCancelOrderNode: 해외선물 취소주문 (CIDBT00300)

    입력:
    - original_order_id: 취소할 주문번호 (필수)
    - symbol: 종목코드
    - exchange: 거래소
    """

    # 해외주식 시장 코드 매핑
    STOCK_MARKET_CODES = {
        "NYSE": "81",
        "NASDAQ": "82",
        "AMEX": "83",
    }

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """주문 취소 실행"""

        # dry_run: LS API 미호출, 모의 응답 반환
        if context.is_dry_run:
            import uuid
            order_id = f"DRYRUN-{uuid.uuid4()}"
            context.log(
                "info",
                f"[dry_run] {node_type} simulated cancel → {order_id}",
                node_id,
            )
            return {
                "order_id": order_id,
                "status": "simulated",
                "dry_run": True,
                "requested": config,
            }

        # === 1. Connection 확인 ===
        broker_connection = config.get("connection")
        if not broker_connection:
            context.log("error", f"{node_type}: connection이 자동 주입되지 않았습니다. 매칭되는 BrokerNode를 확인하세요.", node_id)
            return self._error_result("Missing connection - no matching BrokerNode found")

        if not isinstance(broker_connection, dict):
            context.log("error", f"{node_type}: connection 타입 오류: {type(broker_connection)}", node_id)
            return self._error_result("Invalid connection type")

        # 노드 타입에서 상품 결정
        if "KoreaStock" in node_type:
            product = "korea_stock"
        elif node_type.startswith("Stock"):
            product = "overseas_stock"
        elif node_type.startswith("Futures"):
            product = "overseas_futures"
        else:
            product = broker_connection.get("product", "overseas_stock")
        paper_trading = broker_connection.get("paper_trading", False) if product != "korea_stock" else False

        # === 2. 바인딩 표현식 평가 ===
        config = evaluate_all_bindings(config, context, node_id)

        # === 3. 취소 정보 추출 ===
        order_id = config.get("original_order_id")
        symbol = config.get("symbol", "")
        exchange = config.get("exchange", "KRX" if product == "korea_stock" else "NASDAQ")
        
        if not order_id:
            context.log("error", f"{node_type}: original_order_id가 필수입니다", node_id)
            return self._error_result("Missing order_id")
        
        if not symbol:
            context.log("error", f"{node_type}: symbol이 필수입니다", node_id)
            return self._error_result("Missing symbol")
        
        context.log(
            "info", 
            f"{node_type}: symbol={symbol}, order_id={order_id}",
            node_id
        )
        
        # === 4. LS 로그인 ===
        credential = context.get_credential()
        if not credential:
            context.log("error", f"{node_type}: Credential not found", node_id)
            return self._error_result("Missing credentials")
        
        appkey = credential.get("appkey")
        appsecret = credential.get("appsecret")
        
        if not appkey or not appsecret:
            context.log("error", f"{node_type}: appkey/appsecret not found", node_id)
            return self._error_result("Missing appkey/appsecret")
        
        try:
            ls, success, error = ensure_ls_login(
                appkey, appsecret, paper_trading, context, node_id,
                product=product,
                caller_name=node_type
            )
            if not success:
                return self._error_result(error)
            
            # === 5. 상품별 취소 실행 ===
            if product == "overseas_stock":
                return await self._cancel_overseas_stock(
                    ls, order_id, symbol, exchange, config, context, node_id
                )
            elif product in ("overseas_futures", "overseas_futureoption"):
                return await self._cancel_overseas_futures(
                    ls, order_id, symbol, exchange, config, context, node_id
                )
            elif product == "korea_stock":
                return await self._cancel_korea_stock(
                    ls, order_id, symbol, config, context, node_id
                )
            else:
                context.log("error", f"{node_type}: Unsupported product: {product}", node_id)
                return self._error_result(f"Unsupported product: {product}")
                
        except Exception as e:
            context.log("error", f"{node_type}: Unexpected error: {e}", node_id)
            return self._error_result(str(e))

    async def _cancel_overseas_stock(
        self,
        ls,
        order_id: str,
        symbol: str,
        exchange: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """해외주식 취소주문 실행 (COSAT00301)"""
        from programgarden_finance.ls.overseas_stock.order.COSAT00301.blocks import COSAT00301InBlock1


        # 시장 코드 결정
        ord_mkt_code = self.STOCK_MARKET_CODES.get(exchange, "82")

        try:
            order_api = ls.overseas_stock().주문().cosat00301(
                COSAT00301InBlock1(
                    RecCnt=1,
                    OrdPtnCode="08",  # 취소
                    OrgOrdNo=int(order_id),
                    OrdMktCode=ord_mkt_code,
                    IsuNo=symbol,
                    OrdQty=0,  # 취소 시 수량 0
                    OvrsOrdPrc=0.0,  # 취소 시 가격 0
                    OrdprcPtnCode="00",
                ),
            )
            
            response = await order_api.req_async()
            
            if response.error_msg:
                context.log("warning", f"Cancel order failed: {response.error_msg}", node_id)
                return {
                    "cancel_result": {
                        "success": False,
                        "error": response.error_msg,
                        "order_id": order_id,
                        "product": "overseas_stock",
                    },
                    "cancelled_order": None,
                }
            
            context.log(
                "info",
                f"Order cancelled: {symbol} order_id={order_id}",
                node_id
            )
            
            return {
                "cancel_result": {
                    "success": True,
                    "order_id": order_id,
                    "product": "overseas_stock",
                },
                "cancelled_order": {
                    "symbol": symbol,
                    "exchange": exchange,
                    "order_id": order_id,
                    "status": "cancelled",
                },
            }
            
        except Exception as e:
            context.log("warning", f"Cancel order exception: {e}", node_id)
            return {
                "cancel_result": {
                    "success": False,
                    "error": str(e),
                    "order_id": order_id,
                    "product": "overseas_stock",
                },
                "cancelled_order": None,
            }

    async def _cancel_overseas_futures(
        self,
        ls,
        order_id: str,
        symbol: str,
        exchange: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """해외선물 취소주문 실행 (CIDBT01000)"""
        from programgarden_finance.ls.overseas_futureoption.order.CIDBT01000.blocks import CIDBT01000InBlock1

        from datetime import datetime

        today = datetime.now().strftime("%Y%m%d")
        # 해외선물 취소 시 ExchCode는 공백 사용
        exchange_code = " "
        
        try:
            order_api = ls.overseas_futureoption().order().CIDBT01000(
                CIDBT01000InBlock1(
                    RecCnt=1,
                    OrdDt=today,
                    IsuCodeVal=symbol,
                    OvrsFutsOrgOrdNo=str(order_id),
                    FutsOrdTpCode="3",  # 취소
                    PrdtTpCode=" ",
                    ExchCode=exchange_code or " ",
                ),
            )
            
            response = await order_api.req_async()
            
            if response.error_msg:
                context.log("warning", f"Cancel futures order failed: {response.error_msg}", node_id)
                return {
                    "cancel_result": {
                        "success": False,
                        "error": response.error_msg,
                        "order_id": order_id,
                        "product": "overseas_futures",
                    },
                    "cancelled_order": None,
                }
            
            context.log(
                "info",
                f"Futures order cancelled: {symbol} order_id={order_id}",
                node_id
            )
            
            return {
                "cancel_result": {
                    "success": True,
                    "order_id": order_id,
                    "product": "overseas_futures",
                },
                "cancelled_order": {
                    "symbol": symbol,
                    "exchange": exchange_code,
                    "order_id": order_id,
                    "status": "cancelled",
                },
            }
            
        except Exception as e:
            context.log("warning", f"Cancel futures order exception: {e}", node_id)
            return {
                "cancel_result": {
                    "success": False,
                    "error": str(e),
                    "order_id": order_id,
                    "product": "overseas_futures",
                },
                "cancelled_order": None,
            }

    async def _cancel_korea_stock(
        self,
        ls,
        order_id: str,
        symbol: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """국내주식 취소주문 실행 (CSPAT00801)"""
        from programgarden_finance.ls.korea_stock.order.CSPAT00801.blocks import CSPAT00801InBlock1

        # 취소 수량: config에서 지정하거나, 미지정 시 원주문 잔량 사용
        cancel_qty = config.get("quantity", 0) or config.get("cancel_quantity", 0)
        if not cancel_qty:
            context.log("warning", f"cancel_quantity not specified, using original order remaining qty from order info", node_id)
            # 미체결 잔량 정보가 없으면 기본 1 (API에서 잔량 초과 시 에러 반환)
            cancel_qty = config.get("remaining_quantity", 1)

        try:
            body = CSPAT00801InBlock1(
                OrgOrdNo=int(order_id),
                IsuNo=symbol,
                OrdQty=int(cancel_qty),
            )

            order_api = ls.korea_stock().order().cspat00801(body=body)
            response = await order_api.req_async()

            if response.error_msg:
                context.log("warning", f"Korea stock cancel order failed: {response.error_msg}", node_id)
                return {
                    "cancel_result": {
                        "success": False,
                        "error": response.error_msg,
                        "order_id": order_id,
                        "product": "korea_stock",
                    },
                    "cancelled_order": None,
                }

            context.log(
                "info",
                f"Korea stock order cancelled: {symbol} order_id={order_id}",
                node_id
            )

            return {
                "cancel_result": {
                    "success": True,
                    "order_id": order_id,
                    "product": "korea_stock",
                },
                "cancelled_order": {
                    "symbol": symbol,
                    "exchange": "KRX",
                    "order_id": order_id,
                    "status": "cancelled",
                },
            }

        except Exception as e:
            context.log("warning", f"Korea stock cancel order exception: {e}", node_id)
            return {
                "cancel_result": {
                    "success": False,
                    "error": str(e),
                    "order_id": order_id,
                    "product": "korea_stock",
                },
                "cancelled_order": None,
            }

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """에러 결과 반환"""
        return {
            "cancel_result": {
                "success": False,
                "error": error_msg,
            },
            "cancelled_order": None,
        }


class LLMModelNodeExecutor(NodeExecutorBase):
    """LLMModelNode executor - BrokerNode 패턴 동일.

    credential에서 API 키와 provider 정보를 주입하고,
    litellm 형식의 connection dict를 출력한다.
    """

    # credential_type → provider 매핑
    _CREDENTIAL_TYPE_TO_PROVIDER = {
        "llm_openai": "openai",
        "llm_anthropic": "anthropic",
        "llm_deepseek": "deepseek",
        "llm_google": "gemini",
    }

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        # Credential 주입
        credential_id = config.get("credential_id")
        if credential_id:
            config = self._inject_credentials(credential_id, config, context, node_id)

            # credential_type에서 provider 자동 결정
            cred_ref = next(
                (c for c in context._workflow_credentials
                 if c.get("credential_id") == credential_id),
                None,
            )
            if cred_ref:
                cred_type = cred_ref.get("type") or cred_ref.get("credential_type", "")
                auto_provider = self._CREDENTIAL_TYPE_TO_PROVIDER.get(cred_type)
                if auto_provider:
                    config["provider"] = auto_provider

        provider = config.get("provider", "openai")
        model = config.get("model", "gpt-4o")

        context.log(
            "info",
            f"LLM model connected: {model} (provider={provider})",
            node_id,
        )

        # API 키를 secrets에 저장 (connection 출력에 평문 노출 방지)
        api_key = config.get("api_key")
        if api_key:
            context.set_secret(f"llm_api_key_{node_id}", api_key)

        return {
            "connection": {
                "provider": provider,
                "model": model,
                "api_key": None,  # secrets에 별도 저장됨
                "_llm_node_id": node_id,  # secrets 조회용
                "base_url": config.get("base_url"),
                "organization": config.get("organization"),
                "api_version": config.get("api_version"),
                "temperature": config.get("temperature", 0.7),
                "max_tokens": config.get("max_tokens", 1000),
                "seed": config.get("seed"),
                "streaming": config.get("streaming", False),
            }
        }


class AIAgentToolExecutor:
    """AI Agent의 Tool 호출 엔진.

    tool 엣지로 연결된 기존 노드를 GenericNodeExecutor를 통해 실행합니다.
    동일한 ExecutionContext를 공유하여 credential/connection 자동 주입이 작동합니다.
    """

    def __init__(
        self,
        context: ExecutionContext,
        workflow: "ResolvedWorkflow",
        generic_executor: GenericNodeExecutor,
        executors: Optional[Dict[str, "NodeExecutorBase"]] = None,
    ) -> None:
        self.context = context
        self.workflow = workflow
        self.generic_executor = generic_executor
        self._executors = executors or {}
        # tool 노드별 기본 config 캐시 (as_tool_schema에서 사용)
        self._tool_configs: Dict[str, Dict[str, Any]] = {}
        self._tool_schemas: Dict[str, Dict[str, Any]] = {}

    def register_tools(self, agent_node_id: str) -> List[Dict[str, Any]]:
        """tool 엣지로 연결된 노드들을 Tool로 등록하고 OpenAI function calling 형식 반환.

        Returns:
            List of tool definitions in OpenAI function calling format:
            [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]
        """
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        tool_node_ids = self.workflow.get_tool_node_ids(agent_node_id)
        tools = []

        for tool_node_id in tool_node_ids:
            node = self.workflow.nodes.get(tool_node_id)
            if not node:
                continue

            node_class = registry.get(node.node_type)
            if not node_class:
                continue

            if not node_class.is_tool_enabled():
                self.context.log(
                    "warning",
                    f"Node {node.node_type} is not tool-enabled, skipping",
                    agent_node_id,
                )
                continue

            # as_tool_schema()로 Tool 정보 추출
            tool_schema = node_class.as_tool_schema()
            tool_name = tool_schema["tool_name"]

            # 기본 config 캐시 (LLM args와 병합 시 사용)
            self._tool_configs[tool_name] = {
                "node_id": tool_node_id,
                "node_type": node.node_type,
                "config": node.config.copy(),
            }
            self._tool_schemas[tool_name] = tool_schema

            # LLM이 넘길 수 있는 파라미터만 추출 (credential_id 등 제외)
            llm_params = {}
            excluded_keys = {"credential_id", "connection", "_source_node_id"}
            for param_name, param_info in tool_schema.get("parameters", {}).items():
                if param_name in excluded_keys:
                    continue
                json_type = self._to_json_type(param_info.get("type", "string"))
                p = {"type": json_type}
                if "description" in param_info:
                    p["description"] = param_info["description"]
                if "enum" in param_info:
                    p["enum"] = param_info["enum"]

                # object 타입: 내부 properties 스키마 생성 (LLM이 올바른 구조를 전달할 수 있도록)
                if json_type == "object" and "object_schema" in param_info:
                    props = {}
                    required_fields = []
                    for field_def in param_info["object_schema"]:
                        fname = field_def.get("name", "")
                        ftype = field_def.get("type", "STRING").lower()
                        fp = {"type": "string" if ftype == "string" else ftype}
                        if "label" in field_def:
                            fp["description"] = field_def["label"]
                        props[fname] = fp
                        if field_def.get("required", False):
                            required_fields.append(fname)
                    if props:
                        p["properties"] = props
                        if required_fields:
                            p["required"] = required_fields
                # example 포함 (LLM에게 형식 힌트 제공)
                if "example" in param_info:
                    p["description"] = (
                        p.get("description", "") +
                        f" (예: {param_info['example']})"
                    ).strip()

                llm_params[param_name] = p

            # OpenAI function calling 형식
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_schema.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": llm_params,
                    },
                },
            })

        self.context.log(
            "info",
            f"Registered {len(tools)} tools for AIAgentNode '{agent_node_id}': "
            f"{[t['function']['name'] for t in tools]}",
            agent_node_id,
        )

        return tools

    async def call_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        agent_node_id: str,
    ) -> Dict[str, Any]:
        """tool 엣지로 연결된 노드를 Tool로 호출.

        Args:
            tool_name: Tool 이름 (as_tool_schema의 tool_name)
            args: LLM이 넘긴 인자
            agent_node_id: 호출하는 AIAgentNode ID

        Returns:
            노드 실행 결과 dict
        """
        tool_info = self._tool_configs.get(tool_name)
        if not tool_info:
            return {"error": f"Unknown tool: {tool_name}"}

        tool_node_id = tool_info["node_id"]
        tool_node_type = tool_info["node_type"]
        tool_config = tool_info["config"].copy()

        # LLM args 전처리: JSON 문자열 → dict 자동 변환
        # (LLM이 object 타입 파라미터를 JSON 문자열로 보내는 경우 처리)
        import json as _json
        processed_args = {}
        for k, v in args.items():
            if isinstance(v, str) and v.startswith("{"):
                try:
                    processed_args[k] = _json.loads(v)
                except (ValueError, _json.JSONDecodeError):
                    processed_args[k] = v
            else:
                processed_args[k] = v

        # 노드의 고정 config + LLM이 넘긴 args 병합
        tool_config.update(processed_args)

        # Broker connection 자동 주입 (product_scope 매칭)
        node = self.workflow.nodes.get(tool_node_id)
        if node:
            tool_config = self._auto_inject_connection(tool_node_id, node, tool_config)

        # 전용 executor가 있으면 우선 사용, 없으면 GenericNodeExecutor 사용
        executor = self._executors.get(tool_node_type, self.generic_executor)
        result = await executor.execute(
            node_id=tool_node_id,
            node_type=tool_node_type,
            config=tool_config,
            context=self.context,
        )

        return result

    def _auto_inject_connection(
        self,
        node_id: str,
        node: "ResolvedNode",
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Tool 노드에 Broker connection 자동 주입."""
        if node.product_scope == "all":
            return config

        for other_id, other_node in self.workflow.nodes.items():
            if other_node.product_scope == "all":
                continue
            if other_node.product_scope != node.product_scope:
                continue
            if (node.broker_provider != "all"
                    and other_node.broker_provider != "all"
                    and other_node.broker_provider != node.broker_provider):
                continue

            other_outputs = self.context.get_all_outputs(other_id)
            if "connection" in other_outputs:
                config = config.copy()
                config["connection"] = other_outputs["connection"]
                self.context.log(
                    "debug",
                    f"Tool auto-injected connection from {other_id} "
                    f"(scope={node.product_scope})",
                    node_id,
                )
                break

        return config

    @staticmethod
    def _to_json_type(field_type: str) -> str:
        """FieldType을 JSON Schema 타입으로 변환."""
        mapping = {
            "string": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
            "enum": "string",
            "json": "object",
            "array": "array",
            "credential": "string",
        }
        return mapping.get(field_type, "string")


class AIAgentNodeExecutor(NodeExecutorBase):
    """AIAgentNode executor - ReAct/Function Calling 루프 + Output Parser.

    실행 흐름:
    1. ai_model 엣지에서 LLM connection 주입
    2. tool 엣지에서 Tool 목록 수집 (as_tool_schema)
    3. 프롬프트 조립 (system + user + output 지시)
    4. LLM 호출 → Tool 호출 필요? → Tool 실행 → 결과로 LLM 재호출 (루프)
    5. 최종 응답 Output Parser (text/json/structured)
    6. response 포트 출력
    """

    # Tool 결과 compact 설정
    _MAX_TOOL_RESULT_CHARS = 4000  # LLM에 전달할 최대 문자수 (~1000 tokens)
    _ARRAY_SUMMARY_THRESHOLD = 10  # 배열 아이템이 이 수 이상이면 다운샘플링
    _M4_BUCKET_COUNT = 8  # M4 다운샘플링 버킷 수
    _TOPN_COUNT = 5  # 순위형 데이터 상위/하위 N개

    # OHLCV 시계열 감지용 키 세트
    _OHLCV_KEYS = {"open", "high", "low", "close"}
    # 순위형(포지션/종목) 감지용 키 세트
    _RANKING_KEYS = {"symbol", "pnl", "pnl_rate", "quantity", "qty"}

    @staticmethod
    def _detect_array_type(arr: list) -> str:
        """배열의 데이터 타입을 감지하여 최적 전략을 선택.

        Returns:
            "timeseries" - OHLCV 캔들 등 시계열 → M4
            "ranking"    - 포지션/종목 등 순위형 → Top-N
            "primitive"  - 단순 값 배열 → 균등 샘플링
        """
        if not arr or not isinstance(arr[0], dict):
            return "primitive"

        keys = set(arr[0].keys())
        keys_lower = {k.lower() for k in keys}

        # OHLCV 시계열: open/high/low/close 중 3개 이상 존재
        if len(keys_lower & AIAgentNodeExecutor._OHLCV_KEYS) >= 3:
            return "timeseries"

        # 순위형: symbol + 숫자 필드(pnl, quantity 등) 존재
        if "symbol" in keys_lower and len(keys_lower & AIAgentNodeExecutor._RANKING_KEYS) >= 2:
            return "ranking"

        # 기본: dict 배열이지만 특정 패턴 없음 → M4로 처리 (범용)
        return "timeseries"

    @staticmethod
    def _compact_tool_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """Tool 결과를 LLM 컨텍스트용으로 적응형 다운샘플링.

        데이터 타입을 자동 감지하여 최적 전략을 선택:
        - 시계열(OHLCV 캔들) → M4 (버킷별 first/min/max/last 보존)
        - 순위형(포지션/종목) → Top-N (정렬 기준으로 상위+하위)
        - 단순 배열 → 균등 샘플링

        원본은 response 출력 포트 + AIToolCallEvent로 별도 전달 (손실 없음).
        """
        import json as _json

        threshold = AIAgentNodeExecutor._ARRAY_SUMMARY_THRESHOLD
        max_chars = AIAgentNodeExecutor._MAX_TOOL_RESULT_CHARS
        bucket_count = AIAgentNodeExecutor._M4_BUCKET_COUNT
        topn = AIAgentNodeExecutor._TOPN_COUNT

        def _stats_for_dict_array(arr: list) -> dict:
            """dict 배열에서 숫자 필드 통계 추출."""
            if not arr or not isinstance(arr[0], dict):
                return {}
            numeric_keys = [
                k for k, v in arr[0].items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            stats = {}
            for nk in numeric_keys[:5]:
                values = [item.get(nk) for item in arr if isinstance(item.get(nk), (int, float))]
                if values:
                    stats[nk] = {
                        "min": round(min(values), 4),
                        "max": round(max(values), 4),
                        "avg": round(sum(values) / len(values), 4),
                    }
            return stats

        def _downsample_timeseries(arr: list, key: str) -> dict:
            """M4 알고리즘: 시계열 데이터 다운샘플링 (OHLCV에 최적).

            버킷별 first/min/max/last 인덱스를 선택하여
            캔들의 high/low가 손실 없이 보존됨. O(n).
            """
            count = len(arr)
            summary: dict = {"_compacted": True, "method": "m4", "field": key, "count": count}

            numeric_keys = [
                k for k, v in arr[0].items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]

            if count <= bucket_count * 4:
                summary["samples"] = arr
            else:
                bucket_size = count / bucket_count
                selected: set = {0, count - 1}

                for b in range(bucket_count):
                    start = int(b * bucket_size)
                    end = min(int((b + 1) * bucket_size), count)
                    if start >= end:
                        continue
                    selected.add(start)
                    selected.add(end - 1)
                    if numeric_keys:
                        ref = numeric_keys[0]
                        selected.add(min(range(start, end), key=lambda i: arr[i].get(ref, 0)))
                        selected.add(max(range(start, end), key=lambda i: arr[i].get(ref, 0)))

                summary["samples"] = [arr[i] for i in sorted(selected)]

            stats = _stats_for_dict_array(arr)
            if stats:
                summary["stats"] = stats
            return summary

        def _downsample_ranking(arr: list, key: str) -> dict:
            """Top-N: 순위형 데이터 다운샘플링 (포지션/종목 목록).

            정렬 가능한 숫자 필드(pnl, pnl_rate 등) 기준으로
            상위 N개 + 하위 N개를 선택. 중간은 통계로 요약.
            """
            count = len(arr)
            summary: dict = {"_compacted": True, "method": "topn", "field": key, "count": count}

            # 정렬 기준: pnl_rate > pnl > 첫 번째 숫자 필드
            sort_key = None
            for candidate in ("pnl_rate", "pnl", "quantity", "qty"):
                if candidate in arr[0] and isinstance(arr[0][candidate], (int, float)):
                    sort_key = candidate
                    break
            if sort_key is None:
                numeric_keys = [
                    k for k, v in arr[0].items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                ]
                sort_key = numeric_keys[0] if numeric_keys else None

            if sort_key and count > topn * 2:
                sorted_arr = sorted(arr, key=lambda x: x.get(sort_key, 0), reverse=True)
                summary["sort_key"] = sort_key
                summary["top"] = sorted_arr[:topn]
                summary["bottom"] = sorted_arr[-topn:]
            else:
                summary["samples"] = arr

            stats = _stats_for_dict_array(arr)
            if stats:
                summary["stats"] = stats
            return summary

        def _downsample_primitive(arr: list, key: str) -> dict:
            """균등 샘플링: 단순 값 배열."""
            count = len(arr)
            summary: dict = {"_compacted": True, "method": "uniform", "field": key, "count": count}
            sample_count = min(bucket_count * 2, count)
            step = count / sample_count
            summary["samples"] = [arr[int(i * step)] for i in range(sample_count)]
            return summary

        def _downsample_array(arr: list, key: str) -> dict:
            """데이터 타입 감지 후 최적 전략 선택."""
            dtype = AIAgentNodeExecutor._detect_array_type(arr)
            if dtype == "timeseries":
                return _downsample_timeseries(arr, key)
            elif dtype == "ranking":
                return _downsample_ranking(arr, key)
            else:
                return _downsample_primitive(arr, key)

        def _compact_value(val, key=""):
            if isinstance(val, list) and len(val) >= threshold:
                return _downsample_array(val, key)
            if isinstance(val, dict):
                return {k: _compact_value(v, k) for k, v in val.items()}
            return val

        compacted = _compact_value(result)

        # 최종 문자수 가드레일 (3단계 폴백)
        serialized = _json.dumps(compacted, ensure_ascii=False, default=str)
        if len(serialized) > max_chars:
            # 2단계: samples/top/bottom을 절반으로 축소
            def _shrink_samples(obj):
                if isinstance(obj, dict):
                    if obj.get("_compacted"):
                        for field in ("samples", "top", "bottom"):
                            if field in obj and isinstance(obj[field], list) and len(obj[field]) > 3:
                                s = obj[field]
                                keep = max(2, len(s) // 2)
                                step = max(1, (len(s) - 1) / (keep - 1))
                                obj[field] = [s[int(i * step)] for i in range(keep)]
                        return obj
                    return {k: _shrink_samples(v) for k, v in obj.items()}
                return obj

            compacted = _shrink_samples(compacted)
            serialized = _json.dumps(compacted, ensure_ascii=False, default=str)

            # 3단계: stats + first/last만 남김
            if len(serialized) > max_chars:
                def _stats_only(obj):
                    if isinstance(obj, dict):
                        if obj.get("_compacted"):
                            minimal = {"_compacted": True, "count": obj.get("count", 0)}
                            if "stats" in obj:
                                minimal["stats"] = obj["stats"]
                            for field in ("samples", "top"):
                                if field in obj and obj[field]:
                                    minimal["first"] = obj[field][0]
                                    break
                            for field in ("samples", "bottom"):
                                if field in obj and obj[field]:
                                    minimal["last"] = obj[field][-1]
                                    break
                            return minimal
                        return {k: _stats_only(v) for k, v in obj.items()}
                    return obj

                compacted = _stats_only(compacted)
                serialized = _json.dumps(compacted, ensure_ascii=False, default=str)

            # 최종 안전장치: 위 3단계로도 줄지 않으면 직접 truncation
            if len(serialized) > max_chars:
                compacted = {"_truncated": True, "preview": serialized[:max_chars]}

        return compacted

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        import json as json_module
        from programgarden.providers import LLMProvider

        # === 1. ai_model 엣지에서 LLM connection 주입 ===
        workflow = kwargs.get("workflow")
        if not workflow:
            context.log("error", "AIAgentNode requires workflow context", node_id)
            return {"error": "Workflow context not provided"}

        ai_model_node_id = workflow.get_ai_model_node_id(node_id)
        if not ai_model_node_id:
            context.log("error", "No LLMModelNode connected via ai_model edge", node_id)
            return {"error": "No LLM model connected. Connect a LLMModelNode via ai_model edge."}

        # LLMModelNode의 출력에서 connection 가져오기
        llm_connection = context.get_output(ai_model_node_id, "connection")
        if not llm_connection:
            # LLMModelNode가 아직 실행되지 않았으면 직접 실행
            llm_node = workflow.nodes.get(ai_model_node_id)
            if llm_node:
                llm_executor = LLMModelNodeExecutor()
                llm_result = await llm_executor.execute(
                    node_id=ai_model_node_id,
                    node_type=llm_node.node_type,
                    config=llm_node.config.copy(),
                    context=context,
                )
                context.set_output(ai_model_node_id, "connection", llm_result.get("connection"))
                llm_connection = llm_result.get("connection")

        if not llm_connection:
            context.log("error", "Failed to get LLM connection", node_id)
            return {"error": "Failed to get LLM connection from LLMModelNode."}

        # secrets에서 API 키 복원 (H-8: 평문 노출 방지)
        llm_node_ref = llm_connection.get("_llm_node_id", ai_model_node_id)
        api_key_from_secret = context.get_secret(f"llm_api_key_{llm_node_ref}")
        if api_key_from_secret and not llm_connection.get("api_key"):
            llm_connection = {**llm_connection, "api_key": api_key_from_secret}

        # LLMProvider 생성
        provider = LLMProvider.from_connection(llm_connection)

        # === 2. Tool 등록 ===
        generic_executor = GenericNodeExecutor()
        # kwargs에서 전용 executor 맵 가져오기 (WorkflowExecutor.execute_node에서 전달)
        all_executors = kwargs.get("_executors", {})
        tool_executor = AIAgentToolExecutor(
            context=context,
            workflow=workflow,
            generic_executor=generic_executor,
            executors=all_executors,
        )
        tools = tool_executor.register_tools(node_id)

        # === 3. 프리셋 적용 + 프롬프트 조립 ===
        preset_id = config.get("preset")
        if preset_id and preset_id != "custom":
            from programgarden_core.presets import PresetLoader
            config = PresetLoader.apply_preset(preset_id, config)
            context.log("info", f"Applied preset '{preset_id}'", node_id)

        system_prompt = config.get("system_prompt", "")
        user_prompt = config.get("user_prompt", "")
        output_format = config.get("output_format", "text")
        output_schema = config.get("output_schema")

        # 표현식 평가 (user_prompt에 {{ }} 바인딩)
        if "{{" in user_prompt:
            expr_context = context.get_expression_context()
            evaluator = ExpressionEvaluator(expr_context)
            try:
                user_prompt = evaluator.evaluate(user_prompt)
                if not isinstance(user_prompt, str):
                    user_prompt = json_module.dumps(user_prompt, ensure_ascii=False, default=str)
            except Exception as e:
                context.log("warning", f"User prompt expression evaluation failed: {e}", node_id)

        # Output 형식 지시 추가
        output_instruction = self._build_output_instruction(output_format, output_schema)

        messages = []
        if system_prompt or output_instruction:
            full_system = system_prompt
            if output_instruction:
                full_system = f"{full_system}\n{output_instruction}" if full_system else output_instruction
            messages.append({"role": "system", "content": full_system})
        messages.append({"role": "user", "content": user_prompt})

        # === 4. ReAct/Function Calling 루프 ===
        max_tool_calls = config.get("max_tool_calls", 10)
        tool_error_strategy = config.get("tool_error_strategy", "retry_with_context")
        max_total_tokens = config.get("max_total_tokens", 100000)
        tool_call_count = 0
        accumulated_tokens = 0  # 누적 토큰 카운터
        streaming = llm_connection.get("streaming", False)

        selected_tools = tools

        context.log("info", f"AIAgent starting (model={llm_connection.get('model')}, tools={len(selected_tools)})", node_id)

        while True:
            # LLM 호출
            try:
                if streaming:
                    async def on_token(token: str):
                        from programgarden_core.bases.listener import LLMStreamEvent
                        from datetime import datetime
                        await context.notify_llm_stream(LLMStreamEvent(
                            job_id=context.job_id or "",
                            node_id=node_id,
                            token=token,
                            is_final=False,
                            timestamp=datetime.utcnow(),
                        ))

                    llm_response = await provider.chat_stream(
                        messages=messages,
                        on_token=on_token,
                        tools=selected_tools if selected_tools else None,
                    )

                    # 스트리밍 완료 이벤트
                    from programgarden_core.bases.listener import LLMStreamEvent
                    from datetime import datetime
                    await context.notify_llm_stream(LLMStreamEvent(
                        job_id=context.job_id or "",
                        node_id=node_id,
                        token="",
                        is_final=True,
                        timestamp=datetime.utcnow(),
                    ))
                else:
                    llm_response = await provider.chat(
                        messages=messages,
                        tools=selected_tools if selected_tools else None,
                    )
            except Exception as e:
                context.log("error", f"LLM call failed: {e}", node_id)
                return {"error": f"LLM call failed: {e}"}

            # 토큰 사용량 이벤트
            from programgarden_core.bases.listener import TokenUsageEvent
            from datetime import datetime
            accumulated_tokens += llm_response.total_tokens
            await context.notify_token_usage(TokenUsageEvent(
                job_id=context.job_id or "",
                node_id=node_id,
                model=llm_response.model,
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                total_tokens=llm_response.total_tokens,
                cost_usd=llm_response.cost_usd,
                accumulated_tokens=accumulated_tokens,
                timestamp=datetime.utcnow(),
            ))

            # 토큰 상한선 체크 (0=무제한)
            if max_total_tokens > 0 and accumulated_tokens >= max_total_tokens:
                context.log(
                    "warning",
                    f"Token limit reached: {accumulated_tokens:,}/{max_total_tokens:,} tokens. "
                    f"Stopping tool loop and returning current response.",
                    node_id,
                )
                break

            # Tool 호출 체크
            if not llm_response.tool_calls:
                # Tool 호출 없음 → 최종 응답
                break

            # Tool 호출 처리
            # assistant 메시지 (tool_calls 포함) 추가
            assistant_msg = {"role": "assistant", "content": llm_response.content or ""}
            assistant_msg["tool_calls"] = llm_response.tool_calls
            messages.append(assistant_msg)

            for tc in llm_response.tool_calls:
                if tool_call_count >= max_tool_calls:
                    context.log(
                        "warning",
                        f"Max tool calls ({max_tool_calls}) reached, stopping",
                        node_id,
                    )
                    # 강제 중단: LLM에 알림
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": f"[시스템] 최대 Tool 호출 횟수({max_tool_calls})에 도달했습니다. 현재까지의 정보로 최종 답변을 작성하세요.",
                    })
                    continue

                func = tc.get("function", {})
                tool_name = func.get("name", "")
                tool_args_str = func.get("arguments", "{}")

                try:
                    tool_args = json_module.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                except json_module.JSONDecodeError:
                    tool_args = {}

                context.log("info", f"Tool call: {tool_name}({tool_args})", node_id)

                # Tool 노드 ID 조회
                tool_info = tool_executor._tool_configs.get(tool_name, {})
                tool_node_id = tool_info.get("node_id", "")

                # Tool 실행
                import time as _time
                tool_start = _time.monotonic()

                try:
                    tool_result = await tool_executor.call_tool(
                        tool_name=tool_name,
                        args=tool_args,
                        agent_node_id=node_id,
                    )
                    tool_call_count += 1
                    tool_duration = (_time.monotonic() - tool_start) * 1000

                    # AIToolCallEvent 발행 (완료)
                    from programgarden_core.bases.listener import AIToolCallEvent
                    await context.notify_ai_tool_call(AIToolCallEvent(
                        job_id=context.job_id or "",
                        node_id=node_id,
                        tool_name=tool_name,
                        tool_node_id=tool_node_id,
                        tool_input=tool_args,
                        tool_output=tool_result,
                        duration_ms=tool_duration,
                        timestamp=datetime.utcnow(),
                    ))

                    # Tool 결과를 메시지에 추가 (LLM에는 compact 버전 전달)
                    compacted = self._compact_tool_result(tool_result) if isinstance(tool_result, dict) else tool_result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": json_module.dumps(compacted, ensure_ascii=False, default=str),
                    })

                except Exception as e:
                    context.log("warning", f"Tool '{tool_name}' failed: {e}", node_id)
                    tool_duration = (_time.monotonic() - tool_start) * 1000

                    # AIToolCallEvent 발행 (실패)
                    from programgarden_core.bases.listener import AIToolCallEvent
                    await context.notify_ai_tool_call(AIToolCallEvent(
                        job_id=context.job_id or "",
                        node_id=node_id,
                        tool_name=tool_name,
                        tool_node_id=tool_node_id,
                        tool_input=tool_args,
                        tool_output={"error": str(e)},
                        duration_ms=tool_duration,
                        timestamp=datetime.utcnow(),
                    ))

                    if tool_error_strategy == "abort":
                        return {"error": f"Tool '{tool_name}' failed: {e}"}
                    elif tool_error_strategy == "skip":
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", ""),
                            "content": json_module.dumps({"error": str(e), "status": "skipped"}, ensure_ascii=False),
                        })
                    else:  # retry_with_context
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", ""),
                            "content": json_module.dumps(
                                {"error": str(e), "hint": "이 도구 호출이 실패했습니다. 다른 방법을 시도하거나, 현재 정보로 답변하세요."},
                                ensure_ascii=False,
                            ),
                        })

        # === 5. Output Parser ===
        raw_response = llm_response.content or ""
        parsed = self._parse_output(raw_response, output_format, output_schema, context, node_id)

        context.log(
            "info",
            f"AIAgent completed (tool_calls={tool_call_count}, "
            f"accumulated_tokens={accumulated_tokens:,}, "
            f"last_call_tokens={llm_response.total_tokens}, cost=${llm_response.cost_usd:.4f})",
            node_id,
        )

        return {"response": parsed}

    def _build_output_instruction(
        self,
        output_format: str,
        output_schema: Optional[Dict[str, Any]],
    ) -> str:
        """output_format에 따라 시스템 프롬프트에 추가할 출력 형식 지시."""
        import json as json_module

        if output_format == "text":
            return ""

        if output_format == "json":
            return (
                "\n\n[출력 규칙] 반드시 유효한 JSON 객체로만 응답하세요. "
                "설명 텍스트 없이 JSON만 출력합니다."
            )

        if output_format == "structured" and output_schema:
            schema_desc_lines = []
            for key, schema in output_schema.items():
                if isinstance(schema, str):
                    schema_desc_lines.append(f"- {key}: {schema}")
                elif isinstance(schema, dict):
                    desc = schema.get("description", "")
                    stype = schema.get("type", "string")
                    enum_vals = schema.get("enum")
                    line = f"- {key} ({stype}): {desc}"
                    if enum_vals:
                        line += f" [가능한 값: {', '.join(str(v) for v in enum_vals)}]"
                    schema_desc_lines.append(line)

            return (
                f"\n\n[출력 규칙] 반드시 다음 JSON 스키마에 맞춰 응답하세요:\n"
                f"{json_module.dumps(output_schema, ensure_ascii=False, indent=2)}\n\n"
                f"각 필드 설명:\n"
                f"{chr(10).join(schema_desc_lines)}\n\n"
                f"JSON 외의 텍스트는 출력하지 마세요."
            )

        return ""

    def _parse_output(
        self,
        raw_response: str,
        output_format: str,
        output_schema: Optional[Dict[str, Any]],
        context: ExecutionContext,
        node_id: str,
    ) -> Any:
        """LLM 응답을 output_format에 따라 파싱."""
        import json as json_module

        if output_format == "text":
            return raw_response

        if output_format in ("json", "structured"):
            # JSON 추출 (```json ... ``` 블록 또는 raw JSON)
            text = raw_response.strip()
            if "```json" in text:
                start = text.index("```json") + len("```json")
                closing = text.find("```", start)
                text = text[start:closing].strip() if closing != -1 else text[start:].strip()
            elif "```" in text:
                start = text.index("```") + 3
                closing = text.find("```", start)
                text = text[start:closing].strip() if closing != -1 else text[start:].strip()

            try:
                parsed = json_module.loads(text)

                # structured 모드: output_schema 검증
                if output_format == "structured" and output_schema:
                    validated = self._validate_structured(parsed, output_schema, context, node_id)
                    return validated

                return parsed
            except json_module.JSONDecodeError:
                context.log(
                    "warning",
                    f"JSON parse failed for output_format='{output_format}', "
                    "returning raw text",
                    node_id,
                )
                return raw_response

        return raw_response

    def _validate_structured(
        self,
        parsed: Any,
        output_schema: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Any:
        """structured 모드에서 output_schema로 Pydantic 검증."""
        from pydantic import create_model

        if not isinstance(parsed, dict):
            return parsed

        try:
            # output_schema → 동적 Pydantic 모델 생성
            fields = {}
            for key, schema in output_schema.items():
                if isinstance(schema, str):
                    type_map = {
                        "string": str, "number": float, "integer": int,
                        "boolean": bool, "array": list, "object": dict,
                    }
                    fields[key] = (type_map.get(schema, str), ...)
                elif isinstance(schema, dict):
                    base_type = schema.get("type", "string")
                    if "enum" in schema:
                        from typing import Literal as PyLiteral
                        fields[key] = (PyLiteral[tuple(schema["enum"])], ...)
                    else:
                        type_map = {
                            "string": str, "number": float, "integer": int,
                            "boolean": bool, "array": list, "object": dict,
                        }
                        fields[key] = (type_map.get(base_type, str), ...)

            DynamicModel = create_model("AIAgentOutput", **fields)
            validated = DynamicModel(**parsed)
            return validated.model_dump()
        except Exception as e:
            context.log("error", f"Structured validation failed: {e}. output_schema와 LLM 응답이 일치하지 않습니다.", node_id)
            return parsed


class SQLiteNodeExecutor(NodeExecutorBase):
    """
    SQLiteNode executor

    로컬 SQLite 데이터베이스 조작:
    - execute_query 모드: 직접 SQL 쿼리 실행
    - simple 모드: GUI 기반 CRUD 조작 (select, insert, update, delete, upsert)
    
    DB 파일은 {workspace}/programgarden_data/ 폴더에 자동 생성됩니다.
    """
    
    def __init__(self):
        self._connections: Dict[str, Any] = {}  # db_path -> connection 캐시
    
    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        import aiosqlite
        import os
        from programgarden.database.query_builder import SQLQueryBuilder
        
        db_name = config.get("db_name", "default.db")
        operation = config.get("operation", "simple")

        # dry_run 모드에서는 SELECT만 허용. INSERT/UPDATE/DELETE/UPSERT는
        # 시뮬레이션 응답으로 대체하여 디스크 쓰기를 차단한다.
        if getattr(context, "is_dry_run", False):
            if operation == "execute_query":
                query_text = (config.get("query") or "").strip()
                if not query_text.upper().startswith("SELECT"):
                    context.log(
                        "warning",
                        f"SQLiteNode: dry_run 모드 — 쓰기 쿼리 무시됨 ({query_text[:40]}...)",
                        node_id,
                    )
                    return {"rows": [], "affected_count": 0, "last_insert_id": None}
            else:
                action = (config.get("action") or "select").lower()
                if action != "select":
                    context.log(
                        "warning",
                        f"SQLiteNode: dry_run 모드 — {action.upper()} 작업 무시됨",
                        node_id,
                    )
                    return {"rows": [], "affected_count": 0, "last_insert_id": None}

        db_path = context._resolve_db_path(db_name)
        context.log("debug", f"SQLite DB path: {db_path}", node_id)

        try:
            async with aiosqlite.connect(db_path) as db:
                # Row를 dict로 변환하도록 설정
                db.row_factory = aiosqlite.Row
                
                if operation == "execute_query":
                    return await self._execute_query_mode(db, config, context, node_id)
                else:
                    return await self._execute_simple_mode(db, config, context, node_id)
                    
        except Exception as e:
            context.log("error", f"SQLite execution error: {e}", node_id)
            return {
                "rows": [],
                "affected_count": 0,
                "last_insert_id": None,
                "error": str(e),
            }
    
    async def _execute_query_mode(
        self,
        db,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """execute_query 모드: 직접 SQL 쿼리 실행"""
        query = config.get("query", "")
        parameters = config.get("parameters") or {}
        
        if not query:
            context.log("warning", "Empty query provided", node_id)
            return {
                "rows": [],
                "affected_count": 0,
                "last_insert_id": None,
            }
        
        context.log("debug", f"Executing SQL: {query[:100]}...", node_id)
        
        # SELECT 쿼리인지 확인
        is_select = query.strip().upper().startswith("SELECT")
        
        async with db.execute(query, parameters) as cursor:
            if is_select:
                rows = await cursor.fetchall()
                # Row 객체를 dict로 변환
                result_rows = [dict(row) for row in rows]
                context.log("info", f"Query returned {len(result_rows)} rows", node_id)
                return {
                    "rows": result_rows,
                    "affected_count": len(result_rows),
                    "last_insert_id": None,
                }
            else:
                await db.commit()
                affected = cursor.rowcount
                last_id = cursor.lastrowid
                context.log("info", f"Query affected {affected} rows, last_insert_id={last_id}", node_id)
                return {
                    "rows": [],
                    "affected_count": affected,
                    "last_insert_id": last_id,
                }
    
    async def _execute_simple_mode(
        self,
        db,
        config: Dict[str, Any],
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, Any]:
        """simple 모드: GUI 기반 CRUD 조작"""
        from programgarden.database.query_builder import SQLQueryBuilder
        
        table = config.get("table", "")
        action = config.get("action", "select")
        columns = config.get("columns") or []
        where_clause = config.get("where_clause", "")
        values = config.get("values") or {}
        on_conflict = config.get("on_conflict", "")
        
        # 입력 데이터 포트에서 values 대체 가능
        input_data = config.get("data")
        if input_data and isinstance(input_data, dict):
            values = {**values, **input_data}
        
        if not table:
            context.log("warning", "Table name is required for simple mode", node_id)
            return {
                "rows": [],
                "affected_count": 0,
                "last_insert_id": None,
            }
        
        try:
            if action == "select":
                query = SQLQueryBuilder.build_select(table, columns or None, where_clause or None)
                params = SQLQueryBuilder.extract_params_from_where(where_clause, values)
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    result_rows = [dict(row) for row in rows]
                    context.log("info", f"SELECT {table}: {len(result_rows)} rows", node_id)
                    return {
                        "rows": result_rows,
                        "affected_count": len(result_rows),
                        "last_insert_id": None,
                    }
            
            elif action == "insert":
                cols = columns if columns else list(values.keys())
                query = SQLQueryBuilder.build_insert(table, cols)
                
                async with db.execute(query, values) as cursor:
                    await db.commit()
                    context.log("info", f"INSERT {table}: 1 row, last_id={cursor.lastrowid}", node_id)
                    return {
                        "rows": [],
                        "affected_count": 1,
                        "last_insert_id": cursor.lastrowid,
                    }
            
            elif action == "update":
                cols = list(values.keys())
                query = SQLQueryBuilder.build_update(table, cols, where_clause or None)
                params = {**values, **SQLQueryBuilder.extract_params_from_where(where_clause, values)}
                
                async with db.execute(query, params) as cursor:
                    await db.commit()
                    context.log("info", f"UPDATE {table}: {cursor.rowcount} rows affected", node_id)
                    return {
                        "rows": [],
                        "affected_count": cursor.rowcount,
                        "last_insert_id": None,
                    }
            
            elif action == "delete":
                query = SQLQueryBuilder.build_delete(table, where_clause or None)
                params = SQLQueryBuilder.extract_params_from_where(where_clause, values)
                
                async with db.execute(query, params) as cursor:
                    await db.commit()
                    context.log("info", f"DELETE {table}: {cursor.rowcount} rows affected", node_id)
                    return {
                        "rows": [],
                        "affected_count": cursor.rowcount,
                        "last_insert_id": None,
                    }
            
            elif action == "upsert":
                if not on_conflict:
                    context.log("warning", "on_conflict column is required for upsert", node_id)
                    return {
                        "rows": [],
                        "affected_count": 0,
                        "last_insert_id": None,
                    }
                
                cols = columns if columns else list(values.keys())
                query = SQLQueryBuilder.build_upsert(table, cols, on_conflict)
                
                async with db.execute(query, values) as cursor:
                    await db.commit()
                    context.log("info", f"UPSERT {table}: last_id={cursor.lastrowid}", node_id)
                    return {
                        "rows": [],
                        "affected_count": cursor.rowcount,
                        "last_insert_id": cursor.lastrowid,
                    }
            
            else:
                context.log("warning", f"Unknown action: {action}", node_id)
                return {
                    "rows": [],
                    "affected_count": 0,
                    "last_insert_id": None,
                }
                
        except Exception as e:
            context.log("error", f"Simple mode error ({action}): {e}", node_id)
            return {
                "rows": [],
                "affected_count": 0,
                "last_insert_id": None,
                "error": str(e),
            }


class WorkflowExecutor:
    """
    Workflow execution engine

    Stateful long-running execution:
    - 24-hour continuous execution support
    - Position/balance state persistence
    - Graceful Restart support
    - Dynamic node injection support (Dynamic_ prefix nodes)
    """

    def __init__(self):
        self.resolver = WorkflowResolver()
        self._jobs: Dict[str, "WorkflowJob"] = {}
        self._executors: Dict[str, NodeExecutorBase] = self._init_executors()
        # 동적 노드 레지스트리 (지연 임포트로 순환 참조 방지)
        self._dynamic_registry = None

    def _get_dynamic_registry(self):
        """DynamicNodeRegistry 싱글톤 반환 (지연 로딩)"""
        if self._dynamic_registry is None:
            from programgarden_core.registry import DynamicNodeRegistry
            self._dynamic_registry = DynamicNodeRegistry()
        return self._dynamic_registry

    def _init_executors(self) -> Dict[str, NodeExecutorBase]:
        """Initialize per-node-type executors"""
        return {
            "StartNode": StartNodeExecutor(),
            "ThrottleNode": ThrottleNodeExecutor(),
            "SplitNode": SplitNodeExecutor(),
            "AggregateNode": AggregateNodeExecutor(),
            "ScheduleNode": ScheduleNodeExecutor(),
            "WatchlistNode": WatchlistNodeExecutor(),
            "SymbolQueryNode": SymbolQueryNodeExecutor(),
            "OverseasStockSymbolQueryNode": SymbolQueryNodeExecutor(),
            "OverseasFuturesSymbolQueryNode": SymbolQueryNodeExecutor(),
            "SymbolFilterNode": SymbolFilterNodeExecutor(),
            "ExclusionListNode": ExclusionListNodeExecutor(),
            "MarketUniverseNode": MarketUniverseNodeExecutor(),
            "ScreenerNode": ScreenerNodeExecutor(),
            "BrokerNode": BrokerNodeExecutor(),
            "OverseasStockBrokerNode": BrokerNodeExecutor(),
            "OverseasFuturesBrokerNode": BrokerNodeExecutor(),
            "AccountNode": AccountNodeExecutor(),  # 1회성 REST API 조회
            "OverseasStockAccountNode": AccountNodeExecutor(),
            "OverseasFuturesAccountNode": AccountNodeExecutor(),
            "OverseasStockOpenOrdersNode": OpenOrdersNodeExecutor(),  # 미체결 조회
            "OverseasFuturesOpenOrdersNode": OpenOrdersNodeExecutor(),
            "RealAccountNode": RealAccountNodeExecutor(),  # 실시간 WebSocket
            "OverseasStockRealAccountNode": RealAccountNodeExecutor(),
            "OverseasFuturesRealAccountNode": RealAccountNodeExecutor(),
            "MarketDataNode": MarketDataNodeExecutor(),  # REST API 현재가 조회
            "OverseasStockMarketDataNode": MarketDataNodeExecutor(),
            "OverseasFuturesMarketDataNode": MarketDataNodeExecutor(),
            "OverseasStockFundamentalNode": FundamentalNodeExecutor(),  # 종목정보(펀더멘털) 조회
            "RealMarketDataNode": RealMarketDataNodeExecutor(),
            "OverseasStockRealMarketDataNode": RealMarketDataNodeExecutor(),
            "OverseasFuturesRealMarketDataNode": RealMarketDataNodeExecutor(),
            "RealOrderEventNode": RealOrderEventNodeExecutor(),  # 실시간 주문 이벤트
            "OverseasStockRealOrderEventNode": RealOrderEventNodeExecutor(),
            "OverseasFuturesRealOrderEventNode": RealOrderEventNodeExecutor(),
            "DisplayNode": DisplayNodeExecutor(),
            "TableDisplayNode": DisplayNodeExecutor(),
            "LineChartNode": DisplayNodeExecutor(),
            "MultiLineChartNode": DisplayNodeExecutor(),
            "CandlestickChartNode": DisplayNodeExecutor(),
            "BarChartNode": DisplayNodeExecutor(),
            "SummaryDisplayNode": DisplayNodeExecutor(),
            "ConditionNode": ConditionNodeExecutor(),
            "LogicNode": LogicNodeExecutor(),  # 조건 조합
            "IfNode": IfNodeExecutor(),  # 조건 분기
            # Backtest nodes
            "HistoricalDataNode": HistoricalDataNodeExecutor(),
            "OverseasStockHistoricalDataNode": HistoricalDataNodeExecutor(),
            "OverseasFuturesHistoricalDataNode": HistoricalDataNodeExecutor(),
            "BacktestEngineNode": BacktestEngineNodeExecutor(),
            "BenchmarkCompareNode": BenchmarkCompareNodeExecutor(),
            # Portfolio node
            "PortfolioNode": PortfolioNodeExecutor(),
            # Position sizing node
            "PositionSizingNode": PositionSizingNodeExecutor(),
            # 해외주식 주문
            "OverseasStockNewOrderNode": NewOrderNodeExecutor(),
            "OverseasStockModifyOrderNode": ModifyOrderNodeExecutor(),
            "OverseasStockCancelOrderNode": CancelOrderNodeExecutor(),
            # 해외선물 주문
            "OverseasFuturesNewOrderNode": NewOrderNodeExecutor(),
            "OverseasFuturesModifyOrderNode": ModifyOrderNodeExecutor(),
            "OverseasFuturesCancelOrderNode": CancelOrderNodeExecutor(),
            # 국내주식
            "KoreaStockBrokerNode": BrokerNodeExecutor(),
            "KoreaStockAccountNode": AccountNodeExecutor(),
            "KoreaStockOpenOrdersNode": OpenOrdersNodeExecutor(),
            "KoreaStockMarketDataNode": MarketDataNodeExecutor(),
            "KoreaStockFundamentalNode": FundamentalNodeExecutor(),
            "KoreaStockHistoricalDataNode": HistoricalDataNodeExecutor(),
            "KoreaStockSymbolQueryNode": SymbolQueryNodeExecutor(),
            "KoreaStockNewOrderNode": NewOrderNodeExecutor(),
            "KoreaStockModifyOrderNode": ModifyOrderNodeExecutor(),
            "KoreaStockCancelOrderNode": CancelOrderNodeExecutor(),
            "KoreaStockRealMarketDataNode": RealMarketDataNodeExecutor(),
            "KoreaStockRealAccountNode": RealAccountNodeExecutor(),
            "KoreaStockRealOrderEventNode": RealOrderEventNodeExecutor(),
            # Data nodes
            "SQLiteNode": SQLiteNodeExecutor(),
            # External market data nodes (credential 불필요, 외부 API)
            "CurrencyRateNode": GenericNodeExecutor(),
            # Market Status (JIF, broker credential type 무관)
            "MarketStatusNode": MarketStatusNodeExecutor(),
            # AI nodes
            "LLMModelNode": LLMModelNodeExecutor(),
            "AIAgentNode": AIAgentNodeExecutor(),
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
        storage_dir: Optional[str] = None,
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
            storage_dir: DB/파일 저장 디렉토리. None = /app/data 기본값 (로컬에서 권한 없으면 ./app/data 로 폴백)
        """
        # Dynamic_ 노드 자동 로드 (definition에 dynamic_nodes가 있으면)
        dynamic_nodes = definition.get("dynamic_nodes")
        if dynamic_nodes:
            loaded = self.load_dynamic_nodes(dynamic_nodes)
            logger.info(f"Dynamic nodes auto-loaded from definition: {loaded}")

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

        # Job ID 중복 체크
        if job_id in self._jobs:
            from programgarden_core.exceptions import DuplicateJobIdError

            raise DuplicateJobIdError(
                message=f"job_id '{job_id}'가 이미 사용 중입니다.",
                job_id=job_id,
                details={"existing_job_status": self._jobs[job_id].status},
            )

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
            storage_dir=storage_dir,
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
        
        # Set workflow job reference for start datetime access
        context.set_workflow_job(job)

        # Checkpoint: 워크플로우 해시 저장 (복구 시 변경 감지용)
        from programgarden.database.checkpoint_manager import CheckpointManager as _CM
        job._workflow_json_hash = _CM.compute_workflow_hash(definition)

        self._jobs[job_id] = job

        # Start execution
        await job.start()

        return job

    async def restore(
        self,
        definition: Dict[str, Any],
        job_id: str,
        context_params: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        listeners: Optional[List[ExecutionListener]] = None,
        resource_limits: Optional["ResourceLimits"] = None,
        storage_dir: Optional[str] = None,
    ) -> "WorkflowJob":
        """체크포인트에서 워크플로우 복원.

        Args:
            definition: 워크플로우 정의 (원본과 동일해야 함)
            job_id: 복원할 Job ID (checkpoint가 존재해야 함)
            context_params: 런타임 파라미터
            secrets: 민감 자격증명
            listeners: ExecutionListener 목록
            resource_limits: 리소스 제한
            storage_dir: DB 저장 디렉토리

        Returns:
            복원된 WorkflowJob

        Raises:
            ValueError: checkpoint가 없거나, 만료되었거나, 워크플로우가 변경된 경우
        """
        from programgarden.database.checkpoint_manager import CheckpointManager
        from datetime import timezone as _tz

        # 1. Compile
        resolved, validation = self.compile(definition, context_params)
        if not validation.is_valid:
            raise ValueError(f"Workflow validation failed: {validation.errors}")

        # 2. DB에서 checkpoint 로드
        workflow_id = resolved.workflow_id
        from programgarden.tools.job_tools import _resolve_data_dir
        db_dir = _resolve_data_dir(storage_dir)
        db_path = str(db_dir / f"{workflow_id}_workflow.db")

        mgr = CheckpointManager(db_path)
        checkpoint = mgr.load_checkpoint(job_id)

        # 3. 유효성 검증
        is_valid, reason = self._validate_checkpoint(checkpoint, definition)
        if not is_valid:
            # 복구 실패 알림
            await self._emit_restore_failure(job_id, reason, storage_dir, listeners)
            raise ValueError(f"Checkpoint 복구 불가: {reason}")

        # 4. 워크플로우 inputs/credentials 추출
        workflow_inputs = definition.get("inputs", {})
        workflow_credentials = definition.get("credentials", [])

        # 5. ResourceContext (execute()와 동일)
        resource_context = None
        try:
            from programgarden.resource import ResourceContext
            from programgarden_core.models.resource import ResourceLimits as RL

            effective_limits = resource_limits
            if effective_limits is None:
                workflow_limits = definition.get("resource_limits")
                if workflow_limits:
                    if isinstance(workflow_limits, dict):
                        effective_limits = RL(**workflow_limits)
                    else:
                        effective_limits = workflow_limits

            resource_context = await ResourceContext.create(
                limits=effective_limits,
                auto_detect=(effective_limits is None),
            )
            await resource_context.start()
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to initialize ResourceContext: {e}")

        # 6. ExecutionContext 생성
        context = ExecutionContext(
            job_id=job_id,
            workflow_id=workflow_id,
            context_params=context_params or checkpoint.get("context_params") or {},
            secrets=secrets,
            workflow_inputs=workflow_inputs,
            workflow_credentials=workflow_credentials,
            resource_context=resource_context,
            workflow_edges=resolved.edges,
            workflow_nodes=resolved.nodes,
            storage_dir=storage_dir,
        )

        if listeners:
            context.set_listeners(listeners)

        # 7. Checkpoint outputs 복원
        for node_id, ports in checkpoint.get("node_outputs", {}).items():
            for port_name, value in ports.items():
                context.set_output(node_id, port_name, value)

        # 8. WorkflowJob 생성 + 상태 복원
        job = WorkflowJob(
            job_id=job_id,
            workflow=resolved,
            context=context,
            executor=self,
        )

        # stats/workflow_start_datetime/risk_halt 복원
        if checkpoint.get("stats"):
            job.stats.update(checkpoint["stats"])
        if checkpoint.get("workflow_start_datetime"):
            try:
                wsd = datetime.fromisoformat(checkpoint["workflow_start_datetime"])
                job.workflow_start_datetime = wsd
            except (ValueError, TypeError):
                pass
        if checkpoint.get("risk_halt"):
            context._risk_halt = True

        context.set_workflow_job(job)

        # 9. 복구 모드 설정
        job._restore_mode = True
        job._restore_checkpoint = checkpoint
        job._completed_node_ids = set(checkpoint.get("completed_nodes", []))

        # 10. Job 등록 + 시작
        self._jobs[job_id] = job
        await job.start()

        return job

    def _validate_checkpoint(
        self,
        checkpoint: Optional[Dict[str, Any]],
        definition: Dict[str, Any],
    ) -> tuple:
        """체크포인트 유효성 검증.

        Returns:
            (is_valid: bool, reason: str)
        """
        from programgarden.database.checkpoint_manager import CheckpointManager
        from datetime import timezone as _tz

        # 존재 여부
        if checkpoint is None:
            return False, "checkpoint_not_found"

        # 나이 검증 (10분 = 600초)
        created_at = checkpoint.get("created_at")
        if created_at:
            try:
                cp_time = datetime.fromisoformat(created_at)
                if cp_time.tzinfo is None:
                    cp_time = cp_time.replace(tzinfo=_tz.utc)
                age = (datetime.now(_tz.utc) - cp_time).total_seconds()
                if age > 600:
                    return False, f"checkpoint_expired (age={age:.0f}s > 600s)"
            except (ValueError, TypeError):
                pass

        # 워크플로우 변경 감지
        stored_hash = checkpoint.get("workflow_json_hash")
        if stored_hash:
            current_hash = CheckpointManager.compute_workflow_hash(definition)
            if stored_hash != current_hash:
                return False, "workflow_changed"

        return True, ""

    async def _emit_restore_failure(
        self,
        job_id: str,
        reason: str,
        storage_dir: Optional[str],
        listeners: Optional[List[ExecutionListener]],
    ) -> None:
        """복구 실패 시 RestartEvent 발행 + 로깅."""
        logger.critical(f"Checkpoint 복구 실패: job={job_id}, reason={reason}")

        if listeners:
            event = RestartEvent(
                job_id=job_id,
                restart_reason="restore_failed",
                checkpoint_age_sec=0.0,
                workflow_type="unknown",
                skipped_nodes=[],
                data_gap_warning=f"복구 실패: {reason}",
            )
            for listener in listeners:
                try:
                    if hasattr(listener, 'on_restart'):
                        await listener.on_restart(event)
                except Exception as e:
                    logger.warning(f"Listener error on_restart: {e}")

    async def execute_node(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        plugin: Optional[Callable] = None,
        fields: Optional[Dict[str, Any]] = None,
        workflow: Optional["ResolvedWorkflow"] = None,
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
            workflow=workflow,
            _executors=self._executors,
        )

    def get_job(self, job_id: str) -> Optional["WorkflowJob"]:
        """Get Job"""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List["WorkflowJob"]:
        """List all Jobs"""
        return list(self._jobs.values())

    def remove_job(self, job_id: str) -> bool:
        """Remove a completed/stopped/cancelled/failed job from the executor."""
        job = self._jobs.get(job_id)
        if job and job.status in ("completed", "stopped", "cancelled", "failed", "force_stopped"):
            del self._jobs[job_id]
            return True
        return False

    async def emergency_stop_all(self) -> Dict[str, Any]:
        """긴급 전체 정지 (Kill Switch).

        실행 중인 모든 Job을 즉시 중단합니다.

        Returns:
            {"stopped_jobs": [...], "total_pending_orders": N}
        """
        logger.warning("EMERGENCY STOP ALL triggered")
        results = []
        active_jobs = [
            j for j in self._jobs.values()
            if j.status in ("running", "pending", "stopping")
        ]
        for job in active_jobs:
            try:
                result = await job.force_stop()
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to force_stop job {job.job_id}: {e}")
                results.append({"job_id": job.job_id, "error": str(e)})

        total_pending = sum(
            len(r.get("pending_orders", [])) for r in results
        )
        return {
            "stopped_jobs": results,
            "total_pending_orders": total_pending,
        }

    # ─────────────────────────────────────────────────
    # Dynamic Node API (Lazy Loading 지원)
    # ─────────────────────────────────────────────────

    def register_dynamic_schemas(self, schemas: List[Dict[str, Any]]) -> None:
        """
        동적 노드 스키마 등록 (UI 표시용)

        사용자가 DB에서 로드한 스키마를 등록합니다.
        이 시점에는 클래스 없이 스키마만 저장됩니다.

        Args:
            schemas: 스키마 딕셔너리 목록
                [{"node_type": "Dynamic_MyRSI", "category": "condition", ...}, ...]

        Raises:
            ValueError: Dynamic_ prefix가 없는 경우

        Example:
            executor = WorkflowExecutor()
            schemas = db.get_all_dynamic_node_schemas()
            executor.register_dynamic_schemas(schemas)
        """
        from programgarden_core.registry import DynamicNodeSchema
        registry = self._get_dynamic_registry()
        for schema_dict in schemas:
            schema = DynamicNodeSchema(**schema_dict)
            registry.register_schema(schema)

    def get_required_dynamic_types(self, workflow: Dict[str, Any]) -> List[str]:
        """
        워크플로우에서 사용되는 동적 노드 타입 목록 반환

        사용자는 이 목록을 받아서 해당 타입들의 .py 파일만
        Cloud Storage에서 다운로드하면 됩니다.

        Args:
            workflow: 워크플로우 정의 (JSON dict)

        Returns:
            동적 노드 타입명 목록 (예: ["Dynamic_MyRSI", "Dynamic_MyMACD"])

        Example:
            required = executor.get_required_dynamic_types(workflow)
            for node_type in required:
                code = await cloud.download(f"nodes/{node_type}.py")
                # ... 동적 import 후 inject_node_classes() 호출
        """
        from programgarden_core.registry import DYNAMIC_NODE_PREFIX
        dynamic_types = []
        for node in workflow.get("nodes", []):
            node_type = node.get("type", "")
            if node_type.startswith(DYNAMIC_NODE_PREFIX):
                if node_type not in dynamic_types:
                    dynamic_types.append(node_type)
        return dynamic_types

    def inject_node_classes(self, node_classes: Dict[str, type]) -> None:
        """
        동적 노드 클래스 주입

        사용자가 Cloud Storage에서 다운로드 → 동적 import한 클래스들을 주입합니다.

        검증 항목:
        1. 스키마 등록 여부
        2. BaseNode 상속 여부
        3. execute() 메서드 존재 여부
        4. 스키마와 클래스의 출력 포트 일치 여부

        Args:
            node_classes: {node_type: node_class} 딕셔너리
                {"Dynamic_MyRSI": MyRSINode, "Dynamic_MyMACD": MyMACDNode}

        Raises:
            ValueError: 스키마 미등록, 포트 불일치
            TypeError: BaseNode 미상속, execute() 미구현

        Example:
            executor.inject_node_classes({
                "Dynamic_MyRSI": MyRSINode,
                "Dynamic_MyMACD": MyMACDNode,
            })
        """
        registry = self._get_dynamic_registry()
        registry.inject_node_classes(node_classes)

    def clear_injected_classes(self) -> None:
        """
        주입된 클래스 초기화 (실행 후 메모리 정리)

        스키마는 유지되고 클래스만 제거됩니다.
        워크플로우 실행 후 메모리 정리 용도로 사용합니다.

        Example:
            result = await executor.execute(workflow)
            executor.clear_injected_classes()  # 메모리 정리
        """
        registry = self._get_dynamic_registry()
        registry.clear_injected_classes()

    def load_dynamic_nodes(self, dynamic_nodes: List[Dict[str, Any]]) -> int:
        """
        동적 노드 코드 문자열로부터 스키마 등록 + 클래스 주입을 한 번에 처리

        서버에서 받은 dynamic_nodes payload를 직접 전달하면
        내부에서 exec() → BaseNode 서브클래스 추출 → 스키마 등록 + 클래스 주입.

        register_dynamic_schemas() + inject_node_classes()의 편의 메서드.

        Args:
            dynamic_nodes: 동적 노드 payload 목록
                [{
                    "dynamic_type": "Dynamic_MyRSI",
                    "dynamic_node_code": "import ...\nclass MyRSINode(BaseNode):\n  ...",
                    "category": "condition",
                    "inputs": [...],
                    "outputs": [...],
                    "config_schema": {...},
                }]

        Returns:
            성공적으로 로드된 노드 수

        Raises:
            ValueError: dynamic_type 또는 dynamic_node_code가 없는 경우

        Example:
            executor = WorkflowExecutor()
            loaded = executor.load_dynamic_nodes(payload["dynamic_nodes"])
            print(f"{loaded}개 동적 노드 로드 완료")
            job = await executor.execute(workflow)
            executor.clear_injected_classes()
        """
        if not dynamic_nodes:
            return 0

        from programgarden_core.nodes.base import BaseNode

        schemas = []
        classes = {}

        for dn in dynamic_nodes:
            dynamic_type = dn.get("dynamic_type")
            code = dn.get("dynamic_node_code")

            if not dynamic_type or not code:
                raise ValueError(
                    f"dynamic_type과 dynamic_node_code는 필수: "
                    f"dynamic_type={dynamic_type!r}"
                )

            # exec()로 코드 실행 → namespace에서 클래스 추출
            namespace: Dict[str, Any] = {}
            exec(code, namespace)

            # BaseNode 서브클래스 중 type이 일치하는 클래스 탐색
            # Pydantic 모델에서 type은 클래스 속성이 아니라 model_fields의 default 값임
            node_class = None
            for obj in namespace.values():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseNode)
                    and obj is not BaseNode
                ):
                    # model_fields에서 type 기본값 확인 (Pydantic v2)
                    type_field = obj.model_fields.get("type")
                    node_type_val = type_field.default if type_field else None
                    if node_type_val == dynamic_type:
                        node_class = obj
                        break

            if node_class is None:
                raise ValueError(
                    f"코드에서 type='{dynamic_type}'인 "
                    f"BaseNode 서브클래스를 찾을 수 없음"
                )

            schemas.append({
                "node_type": dynamic_type,
                "category": dn.get("category", "data"),
                "inputs": dn.get("inputs", []),
                "outputs": dn.get("outputs", []),
                "config_schema": dn.get("config_schema", {}),
                "version": dn.get("version", "1.0.0"),
            })
            classes[dynamic_type] = node_class

        if schemas:
            self.register_dynamic_schemas(schemas)
            self.inject_node_classes(classes)

        return len(classes)

    def list_dynamic_node_types(self) -> List[str]:
        """
        등록된 동적 노드 타입 목록 반환

        Returns:
            노드 타입명 목록 (예: ["Dynamic_MyRSI", "Dynamic_MyMACD"])
        """
        registry = self._get_dynamic_registry()
        return registry.list_schema_types()

    def is_dynamic_node_ready(self, node_type: str) -> bool:
        """
        동적 노드가 실행 준비 완료되었는지 확인

        스키마 등록 + 클래스 주입 여부 확인.

        Args:
            node_type: 노드 타입명 (예: Dynamic_MyRSI)

        Returns:
            실행 준비 완료 여부
        """
        registry = self._get_dynamic_registry()
        return (
            registry.is_schema_registered(node_type)
            and registry.is_class_injected(node_type)
        )


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
        
        # Workflow start datetime (fixed, UTC) for PnL tracking
        from datetime import timezone
        self.workflow_start_datetime: datetime = datetime.now(timezone.utc)

        # Statistics
        self.stats: Dict[str, Any] = {
            "conditions_evaluated": 0,
            "orders_placed": 0,
            "orders_filled": 0,
            "errors_count": 0,
            "flow_executions": 0,
            "realtime_updates": 0,
            "last_error": None,
            "last_error_detail": None,
        }

        # Execution task
        self._task: Optional[asyncio.Task] = None

        # Checkpoint support
        self._checkpoint_mgr = None  # CheckpointManager (lazy init)
        self._checkpoint_task: Optional[asyncio.Task] = None  # 실시간 주기 저장 태스크
        self._completed_node_ids: Set[str] = set()  # 완료된 노드 ID 집합

        # Per-node diagnostic cache for get_state() (in-memory only, not persisted to checkpoint)
        self._node_states: Dict[str, NodeState] = {}        # node_id -> latest NodeState
        self._node_errors: Dict[str, str] = {}              # node_id -> last error message
        self._node_durations: Dict[str, float] = {}         # node_id -> last duration_ms
        self._node_error_timestamps: Dict[str, str] = {}    # node_id -> ISO timestamp of last failure
        self._restore_mode: bool = False
        self._restore_checkpoint: Optional[Dict[str, Any]] = None
        self._workflow_json_hash: Optional[str] = None  # 워크플로우 정의 해시

        # Precompute node categories for optimization
        self._has_schedule_node = self._check_has_schedule_node()
        self._stay_connected_nodes = self._find_stay_connected_nodes()

        # Per-node state cache listener — mirrors every NodeStateEvent into
        # _node_states/_node_errors/_node_durations so get_state() surfaces
        # accurate per-node diagnostics without scraping logs.
        from programgarden_core.bases import BaseExecutionListener

        class _NodeStateCacheListener(BaseExecutionListener):
            """Internal listener that updates WorkflowJob's per-node diagnostic cache."""

            def __init__(inner_self, job: "WorkflowJob") -> None:
                super().__init__()
                inner_self._job = job

            async def on_node_state_change(inner_self, event) -> None:
                ts = (
                    event.timestamp.isoformat()
                    if event.error and event.timestamp is not None
                    else None
                )
                inner_self._job._record_node_state(
                    event.node_id,
                    event.state,
                    error=event.error,
                    duration_ms=event.duration_ms,
                    error_timestamp=ts,
                )

        self._node_state_cache_listener = _NodeStateCacheListener(self)
        self.context.add_listener(self._node_state_cache_listener)

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
            if node.node_type in (
                "RealAccountNode", "RealMarketDataNode", "RealOrderEventNode",
                "OverseasStockRealAccountNode", "OverseasFuturesRealAccountNode",
                "OverseasStockRealMarketDataNode", "OverseasFuturesRealMarketDataNode",
                "OverseasStockRealOrderEventNode", "OverseasFuturesRealOrderEventNode",
            ):
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

        # WORKFLOW_STARTED notification
        try:
            wf_type = "realtime" if getattr(self, "_has_realtime", False) else "oneshot"
            await self.context.send_notification(
                category=NotificationCategory.WORKFLOW_STARTED,
                severity=NotificationSeverity.INFO,
                title="Workflow started",
                message=f"Job {self.job_id} started",
                data={"workflow_type": wf_type},
            )
        except Exception as e:
            logger.debug(f"WORKFLOW_STARTED notification failed: {e}")

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
            if self._restore_mode and self._restore_checkpoint:
                checkpoint = self._restore_checkpoint
                from datetime import timezone as _tz

                # 복구 알림
                age_sec = (
                    datetime.now(_tz.utc) - datetime.fromisoformat(checkpoint["created_at"])
                ).total_seconds() if checkpoint.get("created_at") else 0.0

                skipped = checkpoint.get("completed_nodes", [])
                data_gap_msg = None
                if age_sec > 10:
                    data_gap_msg = f"체크포인트 이후 {age_sec:.0f}초 동안의 데이터가 누락될 수 있습니다"

                restart_event = RestartEvent(
                    job_id=self.job_id,
                    restart_reason="checkpoint_restore",
                    checkpoint_age_sec=age_sec,
                    workflow_type=checkpoint.get("workflow_type", "oneshot"),
                    skipped_nodes=skipped,
                    data_gap_warning=data_gap_msg,
                )
                await self.context.notify_restart(restart_event)

                if checkpoint.get("workflow_type") == "oneshot":
                    await self._execute_main_flow(skip_nodes=set(skipped))
                else:
                    # 실시간: Main Flow 전체 재실행
                    await self._execute_main_flow()
                self._restore_mode = False
                self._restore_checkpoint = None
            else:
                await self._execute_main_flow()
            self.stats["flow_executions"] += 1
            await self.context.notify_job_state("cycle_completed", self.stats)

            # Phase 1.5: Cleanup stay_connected=False nodes
            await self.context.cleanup_flow_end_nodes()

            # Phase 2: Event loop if stay_connected OR schedule nodes exist
            has_event_sources = (
                bool(self._stay_connected_nodes) or
                self._has_schedule_node or
                bool(self.context._persistent_tasks)  # Any persistent background tasks
            )
            # dry_run: skip event loop. ScheduleNode/realtime executors emit a
            # single dry_run cycle and exit; staying in the event loop would
            # block forever waiting for ticks that never arrive. Persistent
            # tasks are cleaned up in the finally block below.
            if has_event_sources and self.context.is_running and not self.context.is_dry_run:
                logger.info(
                    f"Entering event loop "
                    f"(stay_connected: {self._stay_connected_nodes}, "
                    f"schedule: {self._has_schedule_node}, "
                    f"persistent_tasks: {len(self.context._persistent_tasks)})"
                )
                # 실시간 checkpoint 주기 저장 시작
                self._start_checkpoint_loop()
                await self._event_loop()
            elif has_event_sources and self.context.is_dry_run:
                logger.info(
                    f"[dry_run] Skipping event loop "
                    f"(schedule: {self._has_schedule_node}, "
                    f"persistent_tasks: {len(self.context._persistent_tasks)})"
                )

            # Phase 3: Mark completed if no failures
            if not self.context.is_failed:
                self.status = "completed"
            else:
                self.status = "failed"

            self.completed_at = datetime.utcnow()

            # 정상 완료 → checkpoint 삭제
            self._delete_checkpoint()
            await self._stop_checkpoint_loop()

            # 🆕 Job 완료 알림
            await self.context.notify_job_state(self.status, self.stats)

            # WORKFLOW_COMPLETED / FAILED notification
            try:
                if self.status == "completed":
                    duration = (self.completed_at - self.started_at).total_seconds() if self.started_at else 0
                    await self.context.send_notification(
                        category=NotificationCategory.WORKFLOW_COMPLETED,
                        severity=NotificationSeverity.INFO,
                        title="Workflow completed",
                        message=f"Job {self.job_id} completed successfully",
                        data={"duration_sec": round(duration, 1), "executed_nodes": self.stats.get("flow_executions", 0)},
                    )
                elif self.status == "failed":
                    await self.context.send_notification(
                        category=NotificationCategory.WORKFLOW_FAILED,
                        severity=NotificationSeverity.CRITICAL,
                        title="Workflow failed",
                        message=f"Job {self.job_id} failed",
                        data={"error": str(self.stats.get("last_error", "Unknown error"))},
                    )
            except Exception:
                pass

        except asyncio.CancelledError:
            self.status = "cancelled"
            logger.info(f"Job {self.job_id} cancelled")
            print(f"⚠️ Job {self.job_id} cancelled")
            await self.context.notify_job_state("cancelled", self.stats)
        except Exception as e:
            self.status = "failed"
            self.stats["errors_count"] += 1
            error_msg = str(e)
            # Preserve _run_node's last_error if already set (more specific node-level info).
            if not self.stats.get("last_error"):
                self.stats["last_error"] = error_msg
                self.stats["last_error_detail"] = {
                    "node_id": None,
                    "node_type": None,
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            self.context.log("error", error_msg)
            logger.exception(f"Job {self.job_id} failed: {e}")
            print(f"❌ Job {self.job_id} failed: {e}")
            import traceback
            traceback.print_exc()
            await self.context.notify_job_state("failed", self.stats)

            # WORKFLOW_FAILED notification
            try:
                await self.context.send_notification(
                    category=NotificationCategory.WORKFLOW_FAILED,
                    severity=NotificationSeverity.CRITICAL,
                    title="Workflow failed",
                    message=f"Job {self.job_id} failed: {e}",
                    data={"error": str(e)},
                )
            except Exception:
                pass
        finally:
            # Cleanup broker fill subscriptions (SDK 콜백 해제)
            await self._cleanup_broker_fill_subscriptions()
            # Cleanup MarketStatusNode JIF subscriptions
            await self._cleanup_jif_subscriptions()
            # Cleanup persistent nodes (shutdown flag 설정 + 구독 해제 + WebSocket close)
            await self.context.cleanup_persistent_nodes()
            # Cleanup listeners
            await self.context.cleanup_listeners()

    async def _execute_main_flow(self, skip_nodes: Optional[Set[str]] = None) -> None:
        """Execute all nodes in topological order with state notifications

        Supports item-based execution with SplitNode/AggregateNode:
        - SplitNode: Triggers repeated execution of downstream nodes for each item
        - AggregateNode: Collects results from SplitNode branches

        Args:
            skip_nodes: 복구 모드에서 이미 완료된 노드 ID 집합 (스킵)
        """
        skip_nodes = skip_nodes or set()
        print(f"🔄 Executing main flow: {self.workflow.execution_order}")

        # === Item-based execution setup ===
        # Find Split/Aggregate pairs and their branch nodes
        split_aggregate_pairs = self._find_split_aggregate_pairs()
        branch_nodes = set()  # Nodes that are part of a Split→Aggregate branch
        for split_id, agg_id in split_aggregate_pairs.items():
            branch = self._get_branch_nodes(split_id, agg_id)
            branch_nodes.update(branch)

        # Track which SplitNodes have been processed
        processed_splits: Dict[str, bool] = {}

        # IfNode: 비활성 브랜치 스킵 집합 (IfNode 실행 후 동적 갱신)
        if_skipped_nodes: Set[str] = set()

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

            # === Checkpoint restore: 이미 완료된 노드 스킵 ===
            if node_id in skip_nodes:
                print(f"  ⏭ Skipping restored node: {node_id} ({node.node_type})")
                self._completed_node_ids.add(node_id)
                await self.context.notify_node_state(
                    node_id=node_id,
                    node_type=node.node_type,
                    state=NodeState.COMPLETED,
                )
                continue

            # === Item-based execution: Skip branch nodes (handled by SplitNode) ===
            if node_id in branch_nodes and node.node_type not in ("SplitNode", "AggregateNode"):
                print(f"  ⏭ Skipping branch node: {node_id} (handled by SplitNode)")
                continue

            # === Item-based execution: Handle SplitNode specially ===
            if node.node_type == "SplitNode" and node_id not in processed_splits:
                await self._execute_split_branch(node_id, node, split_aggregate_pairs, branch_nodes)
                processed_splits[node_id] = True
                continue

            # === Item-based execution: Skip AggregateNode (already executed by SplitNode) ===
            if node.node_type == "AggregateNode" and node_id in split_aggregate_pairs.values():
                print(f"  ⏭ Skipping AggregateNode: {node_id} (already executed by SplitNode)")
                continue

            # === IfNode: 비활성 브랜치 스킵 ===
            if node_id in if_skipped_nodes:
                print(f"  ⏭ Skipping node: {node_id} (IfNode branch not taken)")
                await self.context.notify_node_state(
                    node_id=node_id,
                    node_type=node.node_type,
                    state=NodeState.SKIPPED,
                )
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

            # Auto-inject connection from matching BrokerNode (Phase 5)
            config = self._auto_inject_connection(node_id, node, config)

            # Connect inputs (get values from edges) + 🆕 엣지 알림
            for edge in self.workflow.edges:
                if edge.to_node_id == node_id:
                    # 엣지는 실행 순서만 표현, 데이터는 전체 출력을 전달
                    # get_all_outputs로 소스 노드의 모든 출력 가져오기
                    all_outputs = self.context.get_all_outputs(edge.from_node_id)
                    
                    # 단일 값 (하위 호환): 첫 번째 출력
                    single_value = self.context.get_output(edge.from_node_id, None)
                    
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
                # === 자동 iterate 체크 ===
                # 입력 데이터가 배열이고, 노드가 단일 아이템을 기대하면 자동으로 각 아이템마다 실행
                input_data = None
                for edge in self.workflow.edges:
                    if edge.to_node_id == node_id:
                        # symbols 포트 우선 확인 (WatchlistNode 출력)
                        input_data = self.context.get_output(edge.from_node_id, "symbols")

                        # symbols가 문자열 배열이면 (merge 후) value 포트로 폴백
                        # - WatchlistNode symbols: [{exchange, symbol}, ...] → dict 배열 → 그대로 사용
                        # - HistoricalDataNode merged symbols: ["TSLA"] → string 배열 → value 포트로 전환
                        if (isinstance(input_data, list) and input_data
                                and not isinstance(input_data[0], dict)):
                            value_data = self.context.get_output(edge.from_node_id, "value")
                            if value_data is not None:
                                if isinstance(value_data, list):
                                    input_data = value_data
                                elif isinstance(value_data, dict):
                                    input_data = [value_data]

                        if input_data is None:
                            # 기본 출력 확인
                            input_data = self.context.get_output(edge.from_node_id, None)
                        break

                should_iterate, port_name, items = self._should_auto_iterate(node.node_type, input_data)

                if should_iterate and node_id not in branch_nodes:
                    # 자동 iterate 실행 (SplitNode 브랜치가 아닌 경우에만)
                    outputs = await self._execute_with_auto_iterate(
                        node_id=node_id,
                        node=node,
                        config=config,
                        items=items,
                        port_name=port_name,
                    )
                else:
                    # 일반 실행
                    outputs = await self.executor.execute_node(
                        node_id=node_id,
                        node_type=node.node_type,
                        config=config,
                        context=self.context,
                        plugin=node.plugin,
                        fields=node.fields,
                        workflow=self.workflow,
                    )

                # IfNode: 스킵 노드 계산 후 내부 키 제거
                if node.node_type == "IfNode" and outputs:
                    taken = outputs.pop("_if_branch", "true")
                    new_skips = self._compute_if_skip_nodes(node_id, taken)
                    if_skipped_nodes.update(new_skips)
                    if new_skips:
                        print(f"  🔀 IfNode {node_id}: branch={taken}, skipping {new_skips}")

                # Store outputs
                for out_port_name, value in outputs.items():
                    self.context.set_output(node_id, out_port_name, value)

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

                # Checkpoint: 노드 완료 추적 + 일회성 워크플로우 노드 완료마다 저장
                self._completed_node_ids.add(node_id)
                if not self._stay_connected_nodes:
                    await self._save_checkpoint()

            except Exception as e:
                # 🆕 노드 실패 알림 — listener (_NodeStateCacheListener) 가 자동으로
                # _node_states / _node_errors / _node_durations 에 캐시함
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                error_msg = str(e)
                error_ts = datetime.utcnow().isoformat()
                await self.context.notify_node_state(
                    node_id=node_id,
                    node_type=node.node_type,
                    state=NodeState.FAILED,
                    error=error_msg,
                    duration_ms=duration_ms,
                )
                self.stats["errors_count"] += 1
                self.stats["last_error"] = f"{node_id}: {error_msg}"
                self.stats["last_error_detail"] = {
                    "node_id": node_id,
                    "node_type": node.node_type,
                    "error": error_msg,
                    "timestamp": error_ts,
                }
                self.context.log("error", f"Node {node_id} failed: {e}", node_id)
                raise

    # === Item-based Execution Helpers (자동 반복 실행) ===

    # 자동 반복 실행에서 제외할 노드 타입 (배열을 그대로 처리하는 노드)
    NO_AUTO_ITERATE_NODE_TYPES = {
        "SplitNode", "AggregateNode",  # 명시적 반복 제어 노드
        "StartNode", "ThrottleNode", "IfNode",  # 인프라 노드
        "TableDisplayNode", "LineChartNode", "MultiLineChartNode",  # 디스플레이 노드 (배열 표시)
        "CandlestickChartNode", "BarChartNode", "SummaryDisplayNode",
        "WatchlistNode", "MarketUniverseNode", "ScreenerNode",  # 배열 생성 노드
        "ExclusionListNode",  # 제외 종목 관리 노드 (배열 생성)
        "SymbolFilterNode",  # 집합 연산 노드 (배열 입력/출력)
        "OverseasStockAccountNode", "OverseasFuturesAccountNode",  # 계좌 노드
        "OverseasStockRealAccountNode", "OverseasFuturesRealAccountNode",
        "SQLiteNode", "HTTPRequestNode",  # 데이터 노드
        "BacktestEngineNode", "BenchmarkCompareNode",  # 분석 노드
    }

    def _should_auto_iterate(self, node_type: str, input_data: Any) -> tuple:
        """
        이전 노드 출력이 배열이면 자동 반복 실행

        조건:
        1. 입력 데이터가 배열 (1개 이상)
        2. 노드가 NO_AUTO_ITERATE_NODE_TYPES에 포함되지 않음
        3. SplitNode 브랜치 내부가 아님

        Returns:
            (should_iterate: bool, input_port_name: str, items: list)
        """
        # 자동 반복 제외 노드 타입
        if node_type in self.NO_AUTO_ITERATE_NODE_TYPES:
            return False, "", []

        # 입력이 배열이 아니거나 비어있으면 iterate 불필요
        if not isinstance(input_data, list) or len(input_data) < 1:
            return False, "", []

        # 배열 입력이면 자동 반복 실행
        return True, "item", input_data

    async def _execute_with_auto_iterate(
        self,
        node_id: str,
        node: "ResolvedNode",
        config: Dict[str, Any],
        items: list,
        port_name: str,
    ) -> Dict[str, Any]:
        """
        배열 입력을 자동으로 iterate하며 노드 실행

        각 아이템마다 노드를 실행하고 결과를 배열로 수집합니다.
        {{ item }}, {{ index }}, {{ total }} 표현식을 지원합니다.

        Args:
            node_id: 노드 ID
            node: ResolvedNode 인스턴스
            config: 노드 설정 ({{ item.xxx }} 표현식 포함 가능)
            items: iterate할 아이템 배열
            port_name: 사용되지 않음 (호환성 유지)

        Returns:
            병합된 출력 (배열 필드는 배열로, 단일 필드는 마지막 값)
        """
        from programgarden_core.bases.listener import NodeState

        all_results = []
        total = len(items)

        print(f"  🔄 Auto-iterate: {node_id} ({node.node_type}) - {total} items")

        for idx, current_item in enumerate(items):
            # === item, index, total을 ExecutionContext에 설정 ===
            self.context.set_iteration_context(current_item, idx, total)

            # config 내 표현식 평가 ({{ item.xxx }}, {{ index }} 등)
            item_config = self._resolve_config_expressions(config)

            # 진행 상황 로그
            item_label = current_item.get("symbol", str(current_item)) if isinstance(current_item, dict) else str(current_item)
            print(f"    [{idx+1}/{total}] Processing: {item_label}")
            self.context.log("debug", f"Auto-iterate [{idx+1}/{total}]: {item_label}", node_id)

            try:
                outputs = await self.executor.execute_node(
                    node_id=node_id,
                    node_type=node.node_type,
                    config=item_config,
                    context=self.context,
                    plugin=node.plugin,
                    fields=node.fields,
                    workflow=self.workflow,
                )
                all_results.append(outputs)
            except Exception as e:
                self.context.log("warning", f"Auto-iterate [{idx+1}/{total}] failed: {e}", node_id)
                # continue_on_error: 기본적으로 계속 진행
                all_results.append({"error": str(e), "item": current_item})

        # === 반복 종료 후 컨텍스트 정리 ===
        self.context.clear_iteration_context()

        # 결과 병합: 배열 필드는 병합, 단일 필드는 마지막 값
        merged = self._merge_iterate_results(all_results)
        print(f"  ✅ Auto-iterate complete: {len(all_results)} results merged")

        return merged

    def _merge_iterate_results(self, results: list) -> Dict[str, Any]:
        """
        자동 iterate 결과 병합

        - 배열 필드 (value, values, items 등): 모든 결과를 하나의 배열로 병합
        - 단일 필드: 마지막 값 사용
        """
        if not results:
            return {}

        merged = {}
        array_fields = {"value", "values", "items", "data", "result", "results", "passed_symbols", "failed_symbols"}

        for key in results[0].keys():
            if key in array_fields:
                # 배열 필드: 모든 결과 수집
                merged[key] = []
                for r in results:
                    val = r.get(key)
                    if val is not None:
                        if isinstance(val, list):
                            merged[key].extend(val)
                        else:
                            merged[key].append(val)
            else:
                # 단일 필드: 마지막 유효 값
                for r in reversed(results):
                    if key in r and r[key] is not None:
                        merged[key] = r[key]
                        break

        return merged

    def _compute_if_skip_nodes(self, if_node_id: str, taken_branch: str) -> Set[str]:
        """IfNode 실행 결과에 따라 스킵할 노드 집합 계산 (캐스케이딩)

        비활성 브랜치(from_port)의 하위 노드를 BFS로 탐색하고,
        다른 활성 경로가 없는 노드만 스킵합니다.

        Args:
            if_node_id: IfNode ID
            taken_branch: 선택된 브랜치 ("true" or "false")

        Returns:
            스킵할 노드 ID 집합
        """
        skipped_port = "false" if taken_branch == "true" else "true"

        # 1. 비활성 브랜치의 직접 하위 노드 찾기
        initial_skip = set()
        for edge in self.workflow.edges:
            if (edge.from_node_id == if_node_id
                    and edge.is_dag_edge
                    and edge.from_port == skipped_port):
                initial_skip.add(edge.to_node_id)

        # 2. BFS로 캐스케이딩 스킵 전파
        skip_nodes: Set[str] = set()
        queue = list(initial_skip)

        while queue:
            current = queue.pop(0)
            if current in skip_nodes:
                continue

            # 이 노드의 모든 incoming main edge 확인
            incoming = [e for e in self.workflow.edges
                        if e.to_node_id == current and e.is_dag_edge]

            all_inactive = True
            for edge in incoming:
                if edge.from_node_id == if_node_id:
                    # IfNode에서 오는 edge: 활성 브랜치면 스킵 안 함
                    if edge.from_port == taken_branch or edge.from_port is None:
                        all_inactive = False
                        break
                elif edge.from_node_id not in skip_nodes:
                    # 다른 활성 노드에서 오는 edge가 있으면 스킵 안 함
                    all_inactive = False
                    break

            if all_inactive:
                skip_nodes.add(current)
                # 하위 노드도 확인 대상에 추가
                for edge in self.workflow.edges:
                    if edge.from_node_id == current and edge.is_dag_edge:
                        queue.append(edge.to_node_id)

        return skip_nodes

    def _find_split_aggregate_pairs(self) -> Dict[str, str]:
        """Find pairs of SplitNode → AggregateNode in the workflow

        Returns:
            Dict mapping SplitNode ID to its paired AggregateNode ID
        """
        pairs: Dict[str, str] = {}
        split_nodes = []
        aggregate_nodes = []

        # Find all Split and Aggregate nodes
        for node_id, node in self.workflow.nodes.items():
            if node.node_type == "SplitNode":
                split_nodes.append(node_id)
            elif node.node_type == "AggregateNode":
                aggregate_nodes.append(node_id)

        # Match pairs based on graph reachability
        for split_id in split_nodes:
            # Find the nearest AggregateNode reachable from this SplitNode
            for agg_id in aggregate_nodes:
                if self._is_reachable(split_id, agg_id):
                    pairs[split_id] = agg_id
                    break

        return pairs

    def _is_reachable(self, from_id: str, to_id: str) -> bool:
        """Check if to_id is reachable from from_id via edges"""
        visited = set()
        queue = [from_id]

        while queue:
            current = queue.pop(0)
            if current == to_id:
                return True
            if current in visited:
                continue
            visited.add(current)

            for edge in self.workflow.edges:
                if edge.from_node_id == current:
                    queue.append(edge.to_node_id)

        return False

    def _get_branch_nodes(self, split_id: str, aggregate_id: str) -> Set[str]:
        """Get all nodes between SplitNode and AggregateNode (exclusive)

        Args:
            split_id: SplitNode ID
            aggregate_id: AggregateNode ID

        Returns:
            Set of node IDs in the branch (excluding Split and Aggregate themselves)
        """
        branch = set()
        visited = set()
        queue = []

        # Start from nodes directly connected to SplitNode
        for edge in self.workflow.edges:
            if edge.from_node_id == split_id:
                queue.append(edge.to_node_id)

        while queue:
            current = queue.pop(0)
            if current == aggregate_id or current in visited:
                continue
            visited.add(current)
            branch.add(current)

            for edge in self.workflow.edges:
                if edge.from_node_id == current:
                    queue.append(edge.to_node_id)

        return branch

    async def _execute_split_branch(
        self,
        split_id: str,
        split_node: "ResolvedNode",
        split_aggregate_pairs: Dict[str, str],
        branch_nodes: Set[str],
    ) -> None:
        """Execute a SplitNode and its branch for each item in the input array

        Args:
            split_id: SplitNode ID
            split_node: SplitNode instance
            split_aggregate_pairs: Dict of Split→Aggregate pairs
            branch_nodes: Set of all branch node IDs
        """
        from programgarden_core.bases.listener import NodeState

        print(f"  🔀 Executing SplitNode branch: {split_id}")

        # Get paired AggregateNode
        aggregate_id = split_aggregate_pairs.get(split_id)
        if not aggregate_id:
            self.context.log("warning", f"SplitNode {split_id} has no paired AggregateNode", split_id)
            return

        # Get branch nodes for this Split→Aggregate pair
        branch = self._get_branch_nodes(split_id, aggregate_id)

        # Sort branch nodes by execution order
        branch_order = [n for n in self.workflow.execution_order if n in branch]

        # === Execute SplitNode to get input array ===
        start_time = datetime.utcnow()
        await self.context.notify_node_state(
            node_id=split_id,
            node_type="SplitNode",
            state=NodeState.RUNNING,
        )

        # Get input array from upstream node
        input_array = []
        for edge in self.workflow.edges:
            if edge.to_node_id == split_id:
                upstream_outputs = self.context.get_all_outputs(edge.from_node_id)
                # Look for array in outputs
                for key in ["symbols", "values", "array", "data", "items"]:
                    if key in upstream_outputs and isinstance(upstream_outputs[key], list):
                        input_array = upstream_outputs[key]
                        break
                if not input_array and upstream_outputs:
                    # Check if single output is a list
                    first_val = next(iter(upstream_outputs.values()), None)
                    if isinstance(first_val, list):
                        input_array = first_val
                break

        if not input_array:
            self.context.log("info", f"SplitNode {split_id}: empty array, skipping branch", split_id)
            await self.context.notify_node_state(
                node_id=split_id,
                node_type="SplitNode",
                state=NodeState.COMPLETED,
                outputs={"item": None, "index": 0, "total": 0},
            )
            return

        # Get SplitNode config
        config = dict(split_node.config)
        parallel = config.get("parallel", False)
        delay_ms = config.get("delay_ms", 0)
        continue_on_error = config.get("continue_on_error", True)

        total = len(input_array)
        collected_results: List[Any] = []
        errors: List[str] = []

        print(f"    📦 SplitNode: {total} items, parallel={parallel}, delay_ms={delay_ms}")

        # === Execute branch for each item ===
        if parallel:
            # Parallel execution
            async def execute_item(idx: int, item: Any) -> Any:
                return await self._execute_branch_for_item(
                    split_id=split_id,
                    branch_order=branch_order,
                    item=item,
                    index=idx,
                    total=total,
                )

            tasks = [execute_item(i, item) for i, item in enumerate(input_array)]
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    collected_results.append(result)
                except Exception as e:
                    if continue_on_error:
                        errors.append(str(e))
                        collected_results.append(None)
                    else:
                        raise
        else:
            # Sequential execution
            for idx, item in enumerate(input_array):
                try:
                    result = await self._execute_branch_for_item(
                        split_id=split_id,
                        branch_order=branch_order,
                        item=item,
                        index=idx,
                        total=total,
                    )
                    collected_results.append(result)
                except Exception as e:
                    if continue_on_error:
                        errors.append(str(e))
                        collected_results.append(None)
                    else:
                        raise

                # Apply delay between items (except last)
                if delay_ms > 0 and idx < total - 1:
                    await asyncio.sleep(delay_ms / 1000)

        # === Store results for AggregateNode ===
        self.context.set_node_state(aggregate_id, "_collected_items", collected_results)

        # Mark SplitNode as completed
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        await self.context.notify_node_state(
            node_id=split_id,
            node_type="SplitNode",
            state=NodeState.COMPLETED,
            outputs={"item": input_array[-1] if input_array else None, "index": total - 1, "total": total},
            duration_ms=duration_ms,
        )

        if errors:
            self.context.log("warning", f"SplitNode {split_id}: {len(errors)} errors occurred", split_id)

        # === Execute AggregateNode ===
        await self._execute_aggregate_node(aggregate_id)

    async def _execute_branch_for_item(
        self,
        split_id: str,
        branch_order: List[str],
        item: Any,
        index: int,
        total: int,
    ) -> Any:
        """Execute branch nodes for a single item

        Args:
            split_id: SplitNode ID
            branch_order: Ordered list of branch node IDs
            item: Current item from the array
            index: Current index (0-based)
            total: Total number of items

        Returns:
            Result from the last node in the branch (or the item if no branch)
        """
        # Set split context for SplitNodeExecutor
        self.context.set_node_state(split_id, "_split_context", {
            "item": item,
            "index": index,
            "total": total,
        })

        # Store SplitNode outputs
        self.context.set_output(split_id, "item", item)
        self.context.set_output(split_id, "index", index)
        self.context.set_output(split_id, "total", total)

        result = item

        # Execute each branch node
        for node_id in branch_order:
            node = self.workflow.nodes.get(node_id)
            if not node:
                continue

            # Prepare config
            config = dict(node.config)
            config = self._resolve_config_expressions(config)
            config = self._auto_inject_connection(node_id, node, config)

            # Connect inputs from upstream
            for edge in self.workflow.edges:
                if edge.to_node_id == node_id:
                    all_outputs = self.context.get_all_outputs(edge.from_node_id)
                    for port_name, port_value in all_outputs.items():
                        self.context.set_output(f"_input_{node_id}", port_name, port_value)

            # Execute node
            outputs = await self.executor.execute_node(
                node_id=node_id,
                node_type=node.node_type,
                config=config,
                context=self.context,
                plugin=node.plugin,
                fields=node.fields,
                workflow=self.workflow,
            )

            # Store outputs
            for port_name, value in outputs.items():
                self.context.set_output(node_id, port_name, value)

            # Track last result
            if outputs:
                result = outputs.get("result") or outputs.get("value") or next(iter(outputs.values()), item)

        return result

    async def _execute_aggregate_node(self, aggregate_id: str) -> None:
        """Execute an AggregateNode with collected results

        Args:
            aggregate_id: AggregateNode ID
        """
        from programgarden_core.bases.listener import NodeState

        node = self.workflow.nodes.get(aggregate_id)
        if not node:
            return

        print(f"  🔗 Executing AggregateNode: {aggregate_id}")

        start_time = datetime.utcnow()
        await self.context.notify_node_state(
            node_id=aggregate_id,
            node_type="AggregateNode",
            state=NodeState.RUNNING,
        )

        config = dict(node.config)
        config = self._resolve_config_expressions(config)

        try:
            outputs = await self.executor.execute_node(
                node_id=aggregate_id,
                node_type="AggregateNode",
                config=config,
                context=self.context,
                plugin=node.plugin,
                fields=node.fields,
                workflow=self.workflow,
            )

            # Store outputs
            for port_name, value in outputs.items():
                self.context.set_output(aggregate_id, port_name, value)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self.context.notify_node_state(
                node_id=aggregate_id,
                node_type="AggregateNode",
                state=NodeState.COMPLETED,
                outputs=outputs,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self.context.notify_node_state(
                node_id=aggregate_id,
                node_type="AggregateNode",
                state=NodeState.FAILED,
                error=str(e),
                duration_ms=duration_ms,
            )
            raise

    def _find_trigger_nodes(self, source_node_id: str) -> List[str]:
        """Find nodes that should be triggered on realtime update
        
        - edge에 trigger: "on_update" 속성이 있으면 트리거
        - 소스가 RealAccountNode/RealMarketDataNode면 연결된 모든 노드 자동 트리거
        """
        trigger_nodes = []
        source_node = self.workflow.nodes.get(source_node_id)
        
        # 실시간 노드는 하위 노드를 자동 트리거
        auto_trigger_types = {
            "RealAccountNode", "RealMarketDataNode", "RealOrderEventNode",
            "OverseasStockRealAccountNode", "OverseasFuturesRealAccountNode",
            "OverseasStockRealMarketDataNode", "OverseasFuturesRealMarketDataNode",
            "OverseasStockRealOrderEventNode", "OverseasFuturesRealOrderEventNode",
        }
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

    def _auto_inject_connection(
        self,
        node_id: str,
        node: "ResolvedNode",
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        product_scope에 맞는 BrokerNode의 connection 출력을 자동 주입.

        Phase 5: product_scope + broker_provider 매칭으로 BrokerNode의
        connection 출력을 자동으로 config에 주입합니다.

        동작:
        1. product_scope가 ALL인 범용 노드 → 주입 불필요 (스킵)
        2. 매칭되는 BrokerNode의 connection 출력 → 자동 주입

        Args:
            node_id: 현재 노드 ID
            node: ResolvedNode (product_scope 포함)
            config: 노드 config (표현식 이미 resolve됨)

        Returns:
            connection이 주입된 config
        """
        # 1. 범용 노드(product_scope=ALL)는 connection 불필요
        if node.product_scope == "all":
            return config

        # 3. 매칭되는 BrokerNode의 connection 출력 검색
        #    product_scope + broker_provider 둘 다 매칭되어야 주입
        for other_id, other_node in self.workflow.nodes.items():
            # product_scope 매칭
            if other_node.product_scope == "all":
                continue
            if other_node.product_scope != node.product_scope:
                continue

            # broker_provider 매칭 (ALL은 모든 것과 호환)
            if (node.broker_provider != "all"
                    and other_node.broker_provider != "all"
                    and other_node.broker_provider != node.broker_provider):
                continue

            # BrokerNode 여부 확인: connection 출력이 있는 노드
            other_outputs = self.context.get_all_outputs(other_id)
            if "connection" in other_outputs:
                config = config.copy()
                config["connection"] = other_outputs["connection"]
                self.context.log(
                    "debug",
                    f"Auto-injected connection from {other_id} "
                    f"(product_scope={node.product_scope}, "
                    f"broker_provider={node.broker_provider})",
                    node_id,
                )
                return config

        # 매칭 실패 시 원본 반환 (노드 executor에서 에러 처리)
        return config

    def _resolve_config_expressions(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Config 내의 {{ }} 표현식을 resolve.

        예: "{{ input.total_capital }}" → 100000

        지원 표현식:
        - {{ input.xxx }}: 워크플로우 inputs 파라미터
        - {{ nodeId.port }}: 이전 노드 출력값
        - {{ context.xxx }}: 실행 컨텍스트 값

        Note: items 키는 제외 (ConditionNode의 _process_items_with_extract에서 별도 처리).
              items 내부에 {{ row.xxx }} 같은 지연 평가 표현식이 있어 여기서 평가하면 실패함.
        """
        from programgarden_core.expression import ExpressionEvaluator

        # items는 별도 처리 대상이므로 항상 제외
        items_orig = config.get("items")
        config_copy = {k: v for k, v in config.items() if k != "items"}

        # iteration context 없으면 {{ item }} 표현식도 지연 (auto-iterate 전)
        deferred = {}
        if self.context._iteration_item is None:
            for k in list(config_copy.keys()):
                v = config_copy[k]
                if isinstance(v, str) and "{{ item" in v:
                    deferred[k] = config_copy.pop(k)

        try:
            expr_context = self.context.get_expression_context()
            evaluator = ExpressionEvaluator(expr_context)
            resolved = evaluator.evaluate_fields(config_copy)
        except Exception as e:
            self.context.log("warning", f"Expression resolve failed: {e}")
            resolved = config_copy

        # 지연 평가 필드 복원
        resolved.update(deferred)
        if items_orig is not None:
            resolved["items"] = items_orig

        return resolved

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
                await self.context.notify_job_state("cycle_completed", self.stats)

            elif event.type == "order_event":
                # 주문 이벤트도 실시간 업데이트와 동일하게 처리
                self.stats["realtime_updates"] += 1
                await self._handle_realtime_update(event)
                await self.context.notify_job_state("cycle_completed", self.stats)

            elif event.type == "market_data":
                # RealMarketDataNode에서 발생하는 시세 이벤트 → DisplayNode 트리거
                try:
                    self.stats["realtime_updates"] += 1
                    await self._handle_realtime_update(event)
                    await self.context.notify_job_state("cycle_completed", self.stats)
                except Exception as e:
                    logger.warning(f"market_data event handling error: {e}")

            elif event.type == "schedule_tick":
                self.stats["flow_executions"] += 1
                await self._execute_main_flow()
                await self.context.notify_job_state("cycle_completed", self.stats)
        
        logger.info("Event loop ended")

    async def _apply_rate_limit_guard(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        노드의 rate limit을 체크하고, 제한에 걸리면 스킵/에러 결과를 반환.

        우선순위:
        1. 사용자 config의 rate_limit_interval (명시 설정이면 우선)
        2. 노드 클래스의 _rate_limit ClassVar (기본 보호)
        3. 둘 다 없으면 None (제한 없음)

        Returns:
            None: rate limit 통과 (실행 진행)
            Dict: rate limit 적용됨 (_skipped=True 또는 에러)
        """
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        node_class = registry.get(node_type)
        if not node_class:
            return None

        # _rate_limit ClassVar에서 기본값 읽기
        class_rate_limit = getattr(node_class, '_rate_limit', None)
        if not class_rate_limit:
            return None

        # 사용자 config 오버라이드 (rate_limit_interval이 명시되어 있으면 우선)
        # AIAgentNode는 cooldown_sec 필드를 사용하므로 fallback으로 읽음
        user_interval = config.get("rate_limit_interval")
        if user_interval is None:
            user_interval = config.get("cooldown_sec")
        user_action = config.get("rate_limit_action")

        min_interval_sec = float(user_interval) if user_interval is not None else class_rate_limit.min_interval_sec
        max_concurrent = class_rate_limit.max_concurrent
        on_throttle = user_action if user_action else class_rate_limit.on_throttle

        if min_interval_sec <= 0 and max_concurrent <= 0:
            return None

        # node_state에서 실행 상태 관리
        rate_limit_state_key = "_rate_limit_state"
        rate_limit_state = self.context.get_node_state(node_id, rate_limit_state_key) or {}

        # 1. 동시 실행 제한 체크
        if max_concurrent > 0:
            current_executing_count = rate_limit_state.get("executing_count", 0)
            if current_executing_count >= max_concurrent:
                if on_throttle == "error":
                    raise RuntimeError(
                        f"Node '{node_id}' ({node_type}) rate limit exceeded: "
                        f"max_concurrent={max_concurrent}"
                    )
                self.context.log(
                    "info",
                    f"Rate limit: {node_id} already executing ({current_executing_count}/{max_concurrent}), skipping",
                    node_id,
                )
                return {"_skipped": True, "reason": "rate_limit_concurrent"}

        # 2. 최소 실행 간격 체크
        if min_interval_sec > 0 and rate_limit_state.get("last_executed_at"):
            last_executed_at = rate_limit_state["last_executed_at"]
            if isinstance(last_executed_at, str):
                last_executed_at = datetime.fromisoformat(last_executed_at)
            elapsed_seconds = (datetime.now() - last_executed_at).total_seconds()
            if elapsed_seconds < min_interval_sec:
                remaining_seconds = round(min_interval_sec - elapsed_seconds)
                if on_throttle == "error":
                    raise RuntimeError(
                        f"Node '{node_id}' ({node_type}) rate limit: "
                        f"{remaining_seconds}s remaining (min_interval={min_interval_sec}s)"
                    )
                # M-14: 누적 스킵 카운트 추적
                skip_count_key = "_rate_limit_skip_count"
                current_skip_count = rate_limit_state.get(skip_count_key, 0) + 1
                rate_limit_state[skip_count_key] = current_skip_count
                self.context.set_node_state(node_id, rate_limit_state_key, rate_limit_state)

                self.context.log(
                    "warning",
                    f"Rate limit: {node_id} cooldown 스킵 ({remaining_seconds}s 남음, "
                    f"누적 스킵: {current_skip_count}회)",
                    node_id,
                )
                return {
                    "_skipped": True,
                    "reason": "rate_limit_interval",
                    "remaining_sec": remaining_seconds,
                    "skipped_count": current_skip_count,
                }

        # 통과: 실행 시작 마킹
        rate_limit_state["executing_count"] = rate_limit_state.get("executing_count", 0) + 1
        rate_limit_state["last_executed_at"] = datetime.now().isoformat()
        self.context.set_node_state(node_id, rate_limit_state_key, rate_limit_state)

        return None

    def _release_rate_limit_guard(self, node_id: str) -> None:
        """
        노드 실행 완료 후 rate limit 상태에서 executing_count를 감소.
        """
        rate_limit_state_key = "_rate_limit_state"
        rate_limit_state = self.context.get_node_state(node_id, rate_limit_state_key) or {}
        current_count = rate_limit_state.get("executing_count", 0)
        rate_limit_state["executing_count"] = max(0, current_count - 1)
        self.context.set_node_state(node_id, rate_limit_state_key, rate_limit_state)

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
            if node.node_type in (
                "RealAccountNode", "RealMarketDataNode", "RealOrderEventNode",
                "OverseasStockRealAccountNode", "OverseasFuturesRealAccountNode",
                "OverseasStockRealMarketDataNode", "OverseasFuturesRealMarketDataNode",
                "OverseasStockRealOrderEventNode", "OverseasFuturesRealOrderEventNode",
            ):
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

                # Auto-inject connection from matching BrokerNode (Phase 5)
                config_with_source = self._auto_inject_connection(node_id, node, config_with_source)

                # Rate limit guard: 실행 간격/동시 실행 제한 체크
                rate_limit_result = await self._apply_rate_limit_guard(
                    node_id=node_id,
                    node_type=node.node_type,
                    config=config_with_source,
                )
                if rate_limit_result:
                    # rate limit에 걸린 경우: 출력 저장 후 하위 노드 실행 중단
                    for port_name, value in rate_limit_result.items():
                        self.context.set_output(node_id, port_name, value)
                    await self.context.notify_node_state(
                        node_id=node_id,
                        node_type=node.node_type,
                        state=NodeState.SKIPPED,
                        outputs=rate_limit_result,
                    )
                    break

                try:
                    outputs = await self.executor.execute_node(
                        node_id=node_id,
                        node_type=node.node_type,
                        config=config_with_source,
                        context=self.context,
                        plugin=node.plugin,
                        fields=node.fields,
                        workflow=self.workflow,
                    )
                finally:
                    self._release_rate_limit_guard(node_id)

                # ThrottleNode에서 _throttled=True 반환 시 하위 노드 실행 중단 (M-8)
                if outputs.get("_throttled"):
                    self.context.log(
                        "warning",
                        f"ThrottleNode 제한: 노드 '{node_id}' 스로틀링으로 인해 "
                        f"다운스트림 노드 체인 실행이 중단됩니다.",
                        node_id,
                    )
                    for port_name, value in outputs.items():
                        self.context.set_output(node_id, port_name, value)
                    await self.context.notify_node_state(
                        node_id=node_id,
                        node_type=node.node_type,
                        state=NodeState.SKIPPED,
                        outputs=outputs,
                    )
                    break  # 체인 실행 중단

                for port_name, value in outputs.items():
                    self.context.set_output(node_id, port_name, value)

                # 노드 실행 완료 알림 (UI 업데이트용)
                await self.context.notify_node_state(
                    node_id=node_id,
                    node_type=node.node_type,
                    state=NodeState.COMPLETED,
                    outputs=outputs,
                )

            except Exception as e:
                self._release_rate_limit_guard(node_id)
                error_msg = str(e)
                error_ts = datetime.utcnow().isoformat()
                self._record_node_state(
                    node_id,
                    NodeState.FAILED,
                    error=error_msg,
                    error_timestamp=error_ts,
                )
                self.context.log("error", f"Error in triggered node {node_id}: {e}", node_id)
                self.stats["errors_count"] += 1
                self.stats["last_error"] = f"{node_id}: {error_msg}"
                self.stats["last_error_detail"] = {
                    "node_id": node_id,
                    "node_type": node.node_type if node else None,
                    "error": error_msg,
                    "timestamp": error_ts,
                }
    
    def _find_downstream_nodes(self, start_nodes: List[str]) -> List[str]:
        """
        Find all downstream nodes from start_nodes in topological order.
        
        Returns nodes that need to be re-executed when realtime update occurs.
        Uses DFS to follow one path completely before moving to the next.
        """
        # DFS로 하위 노드 찾기
        downstream = set(start_nodes)
        stack = list(start_nodes)
        
        while stack:
            current = stack.pop()  # DFS: LIFO
            for edge in self.workflow.edges:
                if edge.from_node_id == current and edge.to_node_id not in downstream:
                    downstream.add(edge.to_node_id)
                    stack.append(edge.to_node_id)
        
        # 토폴로지 순서대로 정렬 (workflow.execution_order 기준)
        ordered = [n for n in self.workflow.execution_order if n in downstream]
        return ordered

    async def pause(self) -> None:
        """Pause execution"""
        self.status = "paused"
        self.context.pause()
        await self._save_checkpoint()

    async def resume(self) -> None:
        """Resume execution"""
        self.status = "running"
        self.context.resume()

    async def _cleanup_broker_fill_subscriptions(self) -> None:
        """BrokerNode의 fill subscription SDK 콜백 정리"""
        try:
            broker_executor = BrokerNodeExecutor()
            await broker_executor.cleanup_fill_subscriptions(self.job_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup broker fill subscriptions: {e}")

    async def _cleanup_jif_subscriptions(self) -> None:
        """MarketStatusNode의 JIF 구독 SDK 콜백 정리."""
        try:
            ms_executor = MarketStatusNodeExecutor()
            await ms_executor.cleanup_jif_subscriptions(self.job_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup JIF subscriptions: {e}")

    async def stop(self) -> None:
        """Stop execution gracefully"""
        logger.info(f"Stopping job {self.job_id}")
        self.status = "stopping"

        # Checkpoint 저장 (cleanup 전에)
        await self._save_checkpoint()
        await self._stop_checkpoint_loop()

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
        
        # Cleanup RiskTracker flush
        if self.context.risk_tracker:
            try:
                await self.context.risk_tracker.stop_flush_loop()
            except Exception as e:
                logger.warning(f"Failed to stop risk tracker: {e}")

        # Cleanup ResourceContext
        if self.context.resource:
            try:
                await self.context.resource.stop()
                logger.debug(f"ResourceContext stopped for job {self.job_id}")
            except Exception as e:
                logger.warning(f"Failed to stop ResourceContext: {e}")

        # Cleanup listeners
        await self.context.cleanup_listeners()

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
        await self._cleanup_broker_fill_subscriptions()
        await self._cleanup_jif_subscriptions()
        await self.context.cleanup_persistent_nodes()
        await self.context.cleanup_flow_end_nodes()

        # Cleanup RiskTracker flush
        if self.context.risk_tracker:
            try:
                await self.context.risk_tracker.stop_flush_loop()
            except Exception as e:
                logger.warning(f"Failed to stop risk tracker: {e}")

        # Cleanup ResourceContext
        if self.context.resource:
            try:
                await self.context.resource.stop()
            except Exception as e:
                logger.warning(f"Failed to stop ResourceContext: {e}")

        # Cleanup listeners
        await self.context.cleanup_listeners()

    async def force_stop(self) -> Dict[str, Any]:
        """긴급 정지 (Kill Switch).

        모든 실행을 즉시 중단하고 미체결 주문 정보를 반환합니다.
        cancel()과 달리 미체결 주문 목록을 수집하여 반환합니다.

        Returns:
            {"stopped": True, "pending_orders": [...], "warning": "..."}
        """
        logger.warning(f"FORCE STOP (Kill Switch) triggered for job {self.job_id}")

        # RISK_HALT notification
        try:
            await self.context.send_notification(
                category=NotificationCategory.RISK_HALT,
                severity=NotificationSeverity.CRITICAL,
                title="Kill Switch activated",
                message=f"Job {self.job_id} force stopped",
                data={"reason": "Kill Switch activated", "halted_at": datetime.utcnow().isoformat() + "Z"},
            )
        except Exception:
            pass  # force_stop 중 notification 실패는 무시
        self.status = "force_stopped"
        self.context.stop()

        # Task 즉시 취소
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # 미체결 주문 정보 수집
        pending_orders = []
        try:
            tracker = self.context._workflow_position_tracker
            if tracker:
                pending_orders = tracker.get_pending_orders()
        except Exception as e:
            logger.warning(f"Failed to get pending orders: {e}")

        # 모든 리소스 정리
        await self._cleanup_broker_fill_subscriptions()
        await self._cleanup_jif_subscriptions()
        await self.context.cleanup_persistent_nodes()
        await self.context.cleanup_flow_end_nodes()

        if self.context.risk_tracker:
            try:
                await self.context.risk_tracker.flush_to_db()
                await self.context.risk_tracker.stop_flush_loop()
            except Exception:
                pass

        if self.context.resource:
            try:
                await self.context.resource.stop()
            except Exception:
                pass

        await self.context.cleanup_listeners()
        self.completed_at = datetime.now()

        warning_msg = ""
        if pending_orders:
            warning_msg = (
                f"미체결 주문 {len(pending_orders)}건이 LS증권 서버에 남아있을 수 있습니다. "
                f"HTS/MTS에서 직접 확인하세요."
            )
            logger.warning(warning_msg)

        return {
            "stopped": True,
            "job_id": self.job_id,
            "pending_orders": pending_orders,
            "warning": warning_msg,
        }

    def _record_node_state(
        self,
        node_id: str,
        state: NodeState,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error_timestamp: Optional[str] = None,
    ) -> None:
        """Update local per-node diagnostic cache used by get_state().

        Mirrors the most recent NodeState event so get_state() can surface
        accurate node-level state/error/duration without relying on listener
        replay or scraping logs.
        """
        self._node_states[node_id] = state
        if error is not None:
            self._node_errors[node_id] = error
            if error_timestamp is not None:
                self._node_error_timestamps[node_id] = error_timestamp
        if duration_ms is not None:
            self._node_durations[node_id] = duration_ms

    def get_state(self) -> Dict[str, Any]:
        """Get state snapshot.

        Returns a diagnostic payload that surfaces per-node state, errors,
        and duration sourced from `_node_states` / `_node_errors` /
        `_node_durations` caches (populated by `_NodeStateCacheListener` on
        every `notify_node_state` event). All workflow nodes appear in
        `nodes` (default `state="pending"` for not-yet-executed nodes), so
        callers can rely on key presence regardless of execution progress.
        """
        # Per-node state: every workflow node, defaulting to "pending"
        nodes_state: Dict[str, Dict[str, Any]] = {}
        for node_id, node in self.workflow.nodes.items():
            cached_state = self._node_states.get(node_id, NodeState.PENDING)
            entry: Dict[str, Any] = {
                "state": cached_state.value,
                "node_type": node.node_type,
                "outputs": self.context.get_all_outputs(node_id),
            }
            if node_id in self._node_errors:
                entry["error"] = self._node_errors[node_id]
            if node_id in self._node_durations:
                entry["duration_ms"] = self._node_durations[node_id]
            nodes_state[node_id] = entry

        # Aggregated structured errors — primary debugging surface for
        # external callers (chatbot sandbox, dry_run validators). Always
        # present, even when empty, so callers can rely on the key.
        errors: List[Dict[str, Any]] = []
        cached_node_ids: Set[str] = set()         # node IDs already covered by _node_errors cache
        cached_messages: Set[str] = set()         # raw exception strings cached (for top-level log dedup)
        seen_log_keys: Set[Tuple[str, str]] = set()  # dedup on (node_id, log_message)

        # 1) Per-node cached failures (highest fidelity — direct from FAILED state)
        for node_id, err_msg in self._node_errors.items():
            cached_node_ids.add(node_id)
            cached_messages.add(err_msg)
            node = self.workflow.nodes.get(node_id)
            errors.append({
                "node_id": node_id,
                "node_type": node.node_type if node else None,
                "error": err_msg,
                "timestamp": self._node_error_timestamps.get(node_id),
                "level": "error",
            })

        # 2) Log-derived errors (covers top-level and event-loop paths whose
        #    failure does not pass through notify_node_state). Skip logs for
        #    node_ids already in the cache — cache version is authoritative
        #    (raw exception message; log adds "Node X failed: " prefix and
        #    would otherwise produce a near-duplicate entry). Also skip
        #    top-level except logs (no node_id) whose raw message is already
        #    represented by a cached failure — they are zero-information
        #    duplicates of the same exception bubbling up to the job boundary.
        for log in self.context.get_logs(level="error", limit=200):
            log_node_id = log.get("node_id") or ""
            if log_node_id and log_node_id in cached_node_ids:
                continue
            msg = log.get("message", "")
            if not log_node_id and msg in cached_messages:
                continue
            log_key = (log_node_id, msg)
            if log_key in seen_log_keys:
                continue
            seen_log_keys.add(log_key)
            node = self.workflow.nodes.get(log_node_id) if log_node_id else None
            errors.append({
                "node_id": log_node_id or None,
                "node_type": node.node_type if node else None,
                "error": msg,
                "timestamp": log.get("timestamp"),
                "level": log.get("level", "error"),
            })

        # Sort by timestamp ascending so callers reading errors[0] always
        # land on the earliest (typically root-cause) failure. Entries
        # without a timestamp fall to the end while preserving relative order.
        errors.sort(key=lambda x: (x["timestamp"] is None, x["timestamp"] or ""))

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
            "errors": errors,
        }

    # ============================================================
    # Checkpoint (Graceful Restart)
    # ============================================================

    def _get_checkpoint_mgr(self):
        """CheckpointManager 싱글톤 반환 (지연 로딩)."""
        if self._checkpoint_mgr is None:
            from programgarden.database.checkpoint_manager import CheckpointManager
            db_filename = f"{self.workflow.workflow_id}_workflow.db"
            db_path = self.context._resolve_db_path(db_filename)
            self._checkpoint_mgr = CheckpointManager(db_path)
        return self._checkpoint_mgr

    async def _save_checkpoint(self) -> None:
        """현재 상태를 DB에 저장."""
        try:
            mgr = self._get_checkpoint_mgr()

            node_outputs = {}
            for node_id, ports in self.context._outputs.items():
                node_outputs[node_id] = {
                    port: output.value for port, output in ports.items()
                }

            mgr.save_checkpoint(
                job_id=self.job_id,
                workflow_id=self.workflow.workflow_id,
                status=self.status,
                workflow_type="realtime" if self._stay_connected_nodes else "oneshot",
                completed_nodes=list(self._completed_node_ids),
                stats=self.stats,
                node_outputs=node_outputs,
                workflow_json_hash=self._workflow_json_hash,
                workflow_start_datetime=self.workflow_start_datetime.isoformat() if self.workflow_start_datetime else None,
                risk_halt=getattr(self.context, '_risk_halt', False),
                context_params=self.context.context_params,
            )
        except Exception as e:
            logger.warning(f"Checkpoint 저장 실패: {e}")

    def _delete_checkpoint(self) -> None:
        """체크포인트 삭제 (정상 완료 시)."""
        try:
            mgr = self._get_checkpoint_mgr()
            mgr.delete_checkpoint(self.job_id)
        except Exception as e:
            logger.warning(f"Checkpoint 삭제 실패: {e}")

    async def _checkpoint_loop(self) -> None:
        """실시간 워크플로우: 30초 주기 체크포인트 저장."""
        try:
            while True:
                await asyncio.sleep(30)
                await self._save_checkpoint()
        except asyncio.CancelledError:
            pass

    def _start_checkpoint_loop(self) -> None:
        """실시간 워크플로우에서 checkpoint 주기 저장 시작."""
        if self._checkpoint_task is not None:
            return
        self._checkpoint_task = asyncio.ensure_future(self._checkpoint_loop())
        logger.debug("Checkpoint loop 시작 (30초 주기)")

    async def _stop_checkpoint_loop(self) -> None:
        """checkpoint 주기 저장 중단."""
        if self._checkpoint_task and not self._checkpoint_task.done():
            self._checkpoint_task.cancel()
            try:
                await self._checkpoint_task
            except asyncio.CancelledError:
                pass
        self._checkpoint_task = None
