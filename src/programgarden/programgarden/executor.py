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
    ) -> Dict[str, Any]:
        """
        Execute node

        Returns:
            Dictionary of output port values
        """
        raise NotImplementedError


class GenericNodeExecutor(NodeExecutorBase):
    """
    범용 노드 실행기 (커뮤니티 노드 및 execute() 메서드가 있는 노드용)
    
    NodeRegistry에 등록된 노드 클래스의 execute() 메서드를 호출합니다.
    credential_id가 있으면 자동으로 credential 값을 노드 필드에 주입합니다.
    
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
    ) -> Dict[str, Any]:
        from programgarden_core.registry import NodeTypeRegistry
        
        registry = NodeTypeRegistry()
        node_class = registry.get(node_type)
        
        if not node_class:
            context.log("error", f"Node class not found in registry: {node_type}", node_id)
            return {"error": f"Unknown node type: {node_type}"}
        
        # credential_id가 있으면 credential 값을 config에 주입
        credential_id = config.get("credential_id")
        if credential_id:
            config = self._inject_credentials(credential_id, config, context, node_id)
        
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
    ) -> Dict[str, Any]:
        context.log("info", "Workflow started", node_id)
        return {"start": True}


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
    
    거래소 + 종목코드 구조를 처리합니다.
    BrokerNode 연결 시 broker 정보를 가져오고, product 불일치 시 경고합니다.
    BrokerNode 미연결 시에도 동작하며, 기본값(ls, overseas_stock)을 사용합니다.
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        from programgarden_core.models.exchange import (
            exchange_registry, 
            ProductType, 
            SymbolEntry
        )
        
        symbols_raw = config.get("symbols", [])
        config_product = config.get("product")  # WatchlistNode 자체 설정
        
        # BrokerNode로부터 broker 정보 가져오기 (선택)
        broker_output = context.find_parent_output(node_id, "BrokerNode")
        
        if broker_output:
            broker = broker_output.get("company", "ls")
            broker_product = broker_output.get("product", "overseas_stock")
            
            # WatchlistNode에 product가 설정되어 있고, BrokerNode와 다르면 경고
            if config_product and config_product != broker_product:
                context.log(
                    "warning", 
                    f"Product mismatch: WatchlistNode({config_product}) vs BrokerNode({broker_product}). "
                    f"Using WatchlistNode's product setting.",
                    node_id
                )
                product = config_product
            else:
                product = config_product or broker_product
        else:
            # BrokerNode 미연결: WatchlistNode 자체 설정 또는 기본값 사용
            broker = "ls"
            product = config_product or "overseas_stock"
            context.log("info", f"No BrokerNode connected. Using defaults: broker={broker}, product={product}", node_id)
        
        product_type = ProductType(product)
        
        # symbols 처리: [{exchange, symbol}, ...] 형태
        processed_symbols = []
        for entry in symbols_raw:
            if isinstance(entry, dict):
                exchange = entry.get("exchange", "")
                symbol = entry.get("symbol", "")
                
                if exchange and symbol:
                    # 거래소 이름 → API 코드 변환
                    exchange_code = exchange_registry.name_to_code(broker, product_type, exchange)
                    if exchange_code is None:
                        context.log("warning", f"Unknown exchange: {exchange}, using as-is", node_id)
                        exchange_code = exchange
                    
                    processed_symbols.append({
                        "exchange": exchange,           # 원본 이름 유지 (사용자 표시용)
                        "exchange_code": exchange_code, # API 코드
                        "symbol": symbol,
                    })
            elif isinstance(entry, str):
                # 문자열만 있는 경우: 기본 거래소 사용
                default_exchange = exchange_registry.get_default_exchange(broker, product_type)
                exchange_code = exchange_registry.name_to_code(broker, product_type, default_exchange) if default_exchange else ""
                
                processed_symbols.append({
                    "exchange": default_exchange or "",
                    "exchange_code": exchange_code or "",
                    "symbol": entry,
                })
        
        context.log("info", f"Watchlist: {len(processed_symbols)} symbols, product={product}, broker={broker}", node_id)
        
        return {
            "symbols": processed_symbols,
            "product": product,
            "broker": broker,
        }


class BrokerNodeExecutor(NodeExecutorBase):
    """BrokerNode executor"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
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
        
        # Fallback to environment variables (product별 자동 선택)
        if not appkey or not appsecret:
            appkey, appsecret = self._get_env_credentials(product, paper_trading)
            if appkey and appsecret:
                context.log("info", f"Credentials loaded from environment variables (product={product}, paper_trading={paper_trading})", node_id)
        
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
        Credential Store에서 값을 가져와 config에 주입 (GenericNodeExecutor와 동일 패턴)
        """
        try:
            from programgarden_core.registry import get_credential_store
            store = get_credential_store()
            cred = store.get(credential_id)
            
            if cred and cred.data:
                config = config.copy()
                injected_keys = []
                
                for key, value in cred.data.items():
                    # config에 없거나 None인 경우만 주입
                    if config.get(key) is None:
                        config[key] = value
                        injected_keys.append(key)
                
                if injected_keys:
                    context.log("debug", f"Credentials injected from '{credential_id}': {', '.join(injected_keys)}", node_id)
            else:
                context.log("warning", f"Credential '{credential_id}' not found in store", node_id)
                
        except ImportError:
            context.log("debug", "CredentialStore not available", node_id)
        except Exception as e:
            context.log("warning", f"Failed to inject credentials: {e}", node_id)
        
        return config
        
        # Fallback to environment variables (product별 자동 선택)
        if not appkey or not appsecret:
            appkey, appsecret = self._get_env_credentials(product, paper_trading)
            if appkey and appsecret:
                context.log("info", f"Credentials loaded from environment variables (product={product}, paper_trading={paper_trading})", node_id)
        
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
            }
        }

    def _get_env_credentials(self, product: str, paper_trading: bool) -> tuple:
        """
        Product별 환경변수에서 credential 로드
        
        로컬 개발용 환경변수 맵핑:
        - overseas_stock: APPKEY, APPSECRET (모의투자 미지원)
        - overseas_futures (실전): APPKEY_FUTURE, APPSECRET_FUTURE
        - overseas_futures (모의): APPKEY_FUTURE_FAKE, APPSECRET_FUTURE_FAKE
        
        프로덕션에서는 credential_id를 통해 DB에서 로드합니다.
        """
        import os
        
        if product == "overseas_futures":
            if paper_trading:
                appkey = os.getenv("APPKEY_FUTURE_FAKE")
                appsecret = os.getenv("APPSECRET_FUTURE_FAKE")
            else:
                appkey = os.getenv("APPKEY_FUTURE")
                appsecret = os.getenv("APPSECRET_FUTURE")
        else:
            # overseas_stock (기본)
            appkey = os.getenv("APPKEY")
            appsecret = os.getenv("APPSECRET")
        
        return appkey, appsecret


class AccountNodeExecutor(NodeExecutorBase):
    """
    AccountNode executor - 계좌 잔고 1회 조회 (REST API)
    
    RealAccountNode와 달리 WebSocket 연결 없이 REST API로 1회만 조회합니다.
    """

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        # BrokerNode에서 설정된 provider/product 정보 가져오기
        broker_connection = context.get_output("broker", "connection") or {}
        provider = broker_connection.get("provider", "ls-sec.co.kr")
        product = broker_connection.get("product", "overseas_stock")
        
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
            from programgarden_finance import LS
            
            ls = LS.get_instance()
            
            if not ls.is_logged_in():
                login_result = ls.login(
                    appkey=appkey,
                    appsecretkey=appsecret,
                    paper_trading=paper_trading,
                )
                if not login_result:
                    context.log("error", "LS login failed", node_id)
                    return self._empty_result("Login failed")
                context.log("info", f"LS logged in (paper_trading={paper_trading})", node_id)
            
            # 상품별 REST API 호출
            if product == "overseas_stock":
                return await self._ls_overseas_stock(ls, node_id, context)
            elif product == "domestic_stock":
                return await self._ls_domestic_stock(ls, node_id, context)
            elif product == "overseas_futureoption":
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
                    BalTpCode="1",       # 1: 합산, 2: 건별
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
                    "entry_price": float(item.AvrPrc) if item.AvrPrc else 0.0,
                    "current_price": float(item.NowPrc) if item.NowPrc else 0.0,
                    "pnl_amount": float(item.AbrdFutsEvalPnlAmt) if item.AbrdFutsEvalPnlAmt else 0.0,
                    "pnl_rate": float(item.ErnRat) if hasattr(item, 'ErnRat') and item.ErnRat else 0.0,
                    "currency": "USD",  # 해외선물은 대부분 USD
                }
            
            held_symbols = list(positions.keys())
            
            # block1 = 계좌 요약 정보
            balance_info = {"cash": 0.0, "total_value": 0.0}
            if response.block1:
                b1 = response.block1
                balance_info = {
                    "deposit": float(b1.Dps) if hasattr(b1, 'Dps') and b1.Dps else 0.0,
                    "orderable_amount": float(b1.OrdAbleAmt) if hasattr(b1, 'OrdAbleAmt') and b1.OrdAbleAmt else 0.0,
                    "total_pnl": float(b1.TotEvalPnlAmt) if hasattr(b1, 'TotEvalPnlAmt') and b1.TotEvalPnlAmt else 0.0,
                    "margin": float(b1.TotMgn) if hasattr(b1, 'TotMgn') and b1.TotMgn else 0.0,
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
    ) -> Dict[str, Any]:
        import sys
        # 옵션 확인
        stay_connected = config.get("stay_connected", True)
        sync_interval_sec = config.get("sync_interval_sec", 60)
        
        
        # BrokerNode에서 설정된 provider/product 정보 가져오기
        broker_connection = context.get_output("broker", "connection") or {}
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
            from programgarden_finance import LS
            from programgarden_finance.ls.models import SetupOptions
            
            ls = LS.get_instance()
            
            if not ls.is_logged_in():
                login_result = ls.login(
                    appkey=appkey,
                    appsecretkey=appsecret,
                    paper_trading=paper_trading,
                )
                if not login_result:
                    context.log("error", "LS login failed", node_id)
                    return self._empty_result("Login failed")
                context.log("info", f"LS logged in (paper_trading={paper_trading})", node_id)
            
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
        try:
            # 실시간 연결 클라이언트 가져오기 (tracker 생성 전에 필요)
            real_client = ls.overseas_stock().real()
            if not await real_client.is_connected():
                await real_client.connect()
            
            # StockAccountTracker 생성 (동기 함수)
            tracker = ls.overseas_stock().accno().account_tracker(
                real_client=real_client,
                refresh_interval=sync_interval_sec,
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
            
            # 포지션 변경 콜백 등록 (이벤트 발생용)
            def on_position_change(positions: Dict):
                # 컨텍스트에 최신 데이터 저장
                context.set_output(node_id, "positions", positions)
                
                # 디버깅용 print
                from datetime import datetime
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 해외주식 포지션 업데이트:")
                for sym, pos in positions.items():
                    if hasattr(pos, 'pnl_rate'):
                        print(f"  {sym}: 현재가=${pos.current_price:.2f}, 수익률={pos.pnl_rate:.2f}%")
                
                # 이벤트 큐에 추가 (비동기)
                asyncio.create_task(context.emit_event(
                    event_type="realtime_update",
                    source_node_id=node_id,
                    data={"positions": positions},
                    trigger_nodes=config.get("_trigger_on_update_nodes", []),
                ))
            
            tracker.on_position_change(on_position_change)
            
            # Tracker 시작
            await tracker.start()
            
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
            
            # 초기 데이터 반환
            result = self._get_stock_tracker_data(tracker)
            print(f"\n{'='*60}")
            print(f"[RealAccountNode] 해외주식 실시간 계좌 데이터")
            print(f"{'='*60}")
            print(f"보유 종목: {result.get('symbols', [])}")
            print(f"잔고: {result.get('balance', {})}")
            for sym, pos in result.get('positions', {}).items():
                print(f"  - {sym}: 수량={pos.get('qty')}, 평단가=${pos.get('avg_price'):.2f}, 현재가=${pos.get('current_price'):.2f}, 수익률={pos.get('pnl_rate'):.2f}%")
            print(f"{'='*60}\n")
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
        try:
            # 각 클라이언트 준비
            accno = ls.overseas_futureoption().accno()
            market = ls.overseas_futureoption().market()
            real = ls.overseas_futureoption().real()
            
            # 실시간 WebSocket 연결
            if not await real.is_connected():
                await real.connect()
            
            # FuturesAccountTracker 생성
            tracker = accno.account_tracker(
                market_client=market,
                real_client=real,
                refresh_interval=sync_interval_sec,
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
            
            # 포지션 변경 콜백 (실시간 이벤트)
            def on_position_change(positions):
                context.set_output(node_id, "positions", positions)
                
                # 디버깅용 print
                from datetime import datetime
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 해외선물 포지션 업데이트:")
                for sym, pos in positions.items():
                    direction = '롱' if getattr(pos, 'is_long', True) else '숏'
                    pnl = getattr(pos, 'pnl_amount', 0)
                    print(f"  {sym} ({direction}): 현재가=${getattr(pos, 'current_price', 0):.2f}, 손익=${pnl:.2f}")
                
                asyncio.create_task(context.emit_event(
                    event_type="realtime_update",
                    source_node_id=node_id,
                    data={"positions": positions},
                    trigger_nodes=config.get("_trigger_on_update_nodes", []),
                ))
            
            # 잔고 변경 콜백
            def on_balance_change(balance):
                context.set_output(node_id, "balance", balance)
                asyncio.create_task(context.emit_event(
                    event_type="balance_update",
                    source_node_id=node_id,
                    data={"balance": balance},
                    trigger_nodes=[],
                ))
            
            tracker.on_position_change(on_position_change)
            tracker.on_balance_change(on_balance_change)
            
            # Tracker 시작
            await tracker.start()
            
            # stay_connected에 따라 등록
            if stay_connected:
                context.register_persistent(node_id, tracker)
                context.log("info", f"FuturesAccountTracker started (stay_connected=True, sync_interval={sync_interval_sec}s)", node_id)
            else:
                context.register_cleanup_on_flow_end(node_id, tracker)
                context.log("info", f"FuturesAccountTracker started (stay_connected=False, will cleanup after flow)", node_id)
            
            # 초기 데이터 반환
            result = self._get_futures_tracker_data(tracker)
            print(f"\n{'='*60}")
            print(f"[RealAccountNode] 해외선물 실시간 계좌 데이터")
            print(f"{'='*60}")
            print(f"보유 종목: {result.get('symbols', [])}")
            print(f"잔고: {result.get('balance', {})}")
            for sym, pos in result.get('positions', {}).items():
                direction = '롱' if pos.get('is_long') else '숏'
                print(f"  - {sym} ({direction}): 수량={pos.get('qty')}, 진입가=${pos.get('entry_price'):.2f}, 현재가=${pos.get('current_price'):.2f}, 손익=${pos.get('pnl_amount'):.2f}")
            print(f"미체결: {list(result.get('open_orders', {}).keys())}")
            print(f"{'='*60}\n")
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
                "name": getattr(pos, 'name', symbol),
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
        raw_balance = tracker.get_balances()
        if hasattr(raw_balance, 'model_dump'):
            balance = {k: float(v) if isinstance(v, (int, float)) or hasattr(v, '__float__') else str(v) 
                      for k, v in raw_balance.model_dump().items() if v is not None}
        elif isinstance(raw_balance, dict):
            balance = raw_balance
        else:
            balance = {"cash": 0.0, "total_value": 0.0}
        
        return {
            "symbols": symbols,
            "held_symbols": symbols,
            "positions": positions,
            "balance": balance,
        }

    def _get_futures_tracker_data(self, tracker) -> Dict[str, Any]:
        """해외선물 Tracker에서 현재 데이터 추출"""
        positions = {}
        for symbol, pos in tracker.get_positions().items():
            positions[symbol] = {
                "symbol": symbol,
                "name": getattr(pos, 'symbol', symbol),
                "is_long": getattr(pos, 'is_long', True),
                "qty": int(getattr(pos, 'quantity', 0)),
                "entry_price": float(getattr(pos, 'entry_price', 0)),
                "current_price": float(getattr(pos, 'current_price', 0)),
                "pnl_amount": float(getattr(pos, 'pnl_amount', 0)),
                "pnl_rate": float(getattr(pos, 'realtime_pnl', {}).get('pnl_rate', 0)) if hasattr(pos, 'realtime_pnl') else 0,
                "currency": "USD",
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
                open_orders[order_no] = {
                    "order_no": order_no,
                    "symbol": getattr(order, 'symbol', ''),
                    "is_long": getattr(order, 'is_long', True),
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
    """RealMarketDataNode executor - 실시간 시세"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        import random
        from programgarden_core.exceptions import ValidationError
        
        # ========================================
        # BrokerNode와 WatchlistNode product 정합성 검증
        # ========================================
        broker_output = context.find_parent_output(node_id, "BrokerNode")
        watchlist_output = context.find_parent_output(node_id, "WatchlistNode")
        
        broker_product = None
        watchlist_product = None
        
        if broker_output:
            # BrokerNode 출력에서 product 가져오기
            broker_product = broker_output.get("product")
            if not broker_product:
                # connection 내부에 있을 수도 있음
                conn = broker_output.get("connection", {})
                broker_product = conn.get("product")
        
        if watchlist_output:
            watchlist_product = watchlist_output.get("product")
        
        # 둘 다 있고 product가 불일치하면 에러
        if broker_product and watchlist_product and broker_product != watchlist_product:
            error_msg = (
                f"Product mismatch: BrokerNode({broker_product}) ↔ WatchlistNode({watchlist_product}). "
                f"Cannot subscribe to realtime data with mismatched products. "
                f"Please ensure BrokerNode and WatchlistNode use the same product type."
            )
            context.log("error", error_msg, node_id)
            raise ValidationError(error_msg, node_id=node_id)
        
        # BrokerNode는 있는데 WatchlistNode가 없거나, 또는 symbols가 없으면 경고
        if broker_product and not watchlist_output:
            context.log("warning", f"No WatchlistNode found. BrokerNode product: {broker_product}", node_id)
        
        # 입력에서 symbols 가져오기
        symbols_raw = context.get_output("_input_" + node_id, "symbols") or []
        if not symbols_raw:
            symbols_raw = context.get_output("account", "held_symbols") or []
        
        if not symbols_raw:
            context.log("warning", "No symbols to subscribe. Check WatchlistNode or AccountNode connection.", node_id)
            return {"price": {}, "volume": {}, "bid": {}, "ask": {}, "error": "no_symbols"}
        
        # symbols 정규화: dict 형태 [{exchange, symbol}] → 문자열 리스트
        symbols = []
        for entry in symbols_raw:
            if isinstance(entry, dict):
                # WatchlistNode 출력 형식: {exchange, symbol}
                symbols.append(entry.get("symbol", ""))
            elif isinstance(entry, str):
                symbols.append(entry)
        
        # TODO: 실제 구현에서는 WebSocket 시세 수신
        # 현재는 약간의 변동을 주는 목업 데이터
        prices = {}
        base_prices = {"NVDA": 875.30, "AAPL": 192.30, "TSLA": 248.90}
        
        for symbol in symbols:
            if not symbol:
                continue
            base = base_prices.get(symbol, 100.0)
            # ±0.5% 랜덤 변동
            variation = base * random.uniform(-0.005, 0.005)
            prices[symbol] = round(base + variation, 2)
        
        context.log("info", f"Market data received: {symbols}", node_id)
        return {"price": prices, "volume": {}, "bid": {}, "ask": {}}


class CustomPnLNodeExecutor(NodeExecutorBase):
    """CustomPnLNode executor - 커스텀 수익률 계산 (고급 사용자용)"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
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
    """DisplayNode executor - 테이블/차트 표시"""

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

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        from datetime import datetime
        
        # 입력 데이터 가져오기 (다양한 소스 지원)
        # 1. _input_{node_id}에서 모든 포트의 데이터 수집
        input_namespace = f"_input_{node_id}"
        all_inputs = context.get_all_outputs(input_namespace) if hasattr(context, 'get_all_outputs') else {}
        
        # 디버깅: 입력 데이터 확인
        print(f"\n🔍 DisplayNode '{node_id}' 입력 데이터:")
        print(f"   - all_inputs keys: {list(all_inputs.keys())}")
        for k, v in all_inputs.items():
            v_type = type(v).__name__
            v_preview = str(v)[:100] if v else "None"
            print(f"   - {k} ({v_type}): {v_preview}...")
        
        context.log("debug", f"DisplayNode inputs from {input_namespace}: {list(all_inputs.keys())}", node_id)
        
        # === 여러 백테스트 노드에서 데이터 수집 ===
        metrics_list = []  # 성과 지표 배열 (radar/table용)
        trades_list = []   # 거래 내역 배열 (bar chart 집계용)
        
        if all_inputs:
            for key, value in all_inputs.items():
                if isinstance(value, dict):
                    # metrics/summary 형식인지 확인 (total_return, sharpe_ratio 등의 키 보유)
                    if any(k in value for k in ["total_return", "sharpe_ratio", "max_drawdown"]):
                        # 소스 노드에서 strategy_name 조회
                        source_node = key.split(".")[0] if "." in key else key
                        # strategy_name이 이미 있으면 사용, 없으면 소스 노드 이름
                        strategy_name = value.get("strategy_name") or source_node
                        metrics_with_name = {**value, "strategy_name": strategy_name}
                        metrics_list.append(metrics_with_name)
                elif isinstance(value, list) and len(value) > 0:
                    # trades 배열인지 확인
                    first = value[0]
                    if isinstance(first, dict) and "symbol" in first and "action" in first:
                        trades_list.extend(value)
        
        # 개별 포트에서도 시도 (data, summary, positions 등)
        input_data = (
            context.get_output(input_namespace, "data") or
            context.get_output(input_namespace, "summary") or
            context.get_output(input_namespace, "positions") or
            context.get_output(input_namespace, "input")
        )
        
        
        # 2. equity_curve 데이터 (라인 차트용)
        equity_data = context.get_output(input_namespace, "equity_curve")
        
        # 3. backtestEngine에서 직접 조회 (fallback)
        if not equity_data:
            equity_data = context.get_output("backtestEngine", "equity_curve")
        
        # 4. data 포트에 equity_curve 리스트가 들어온 경우 처리
        if not equity_data and isinstance(input_data, list) and len(input_data) > 0:
            # equity_curve 형식인지 확인 (date와 value 키가 있는 dict 리스트)
            first_item = input_data[0] if input_data else {}
            if isinstance(first_item, dict) and "date" in first_item and "value" in first_item:
                equity_data = input_data
        
        
        # 5. account.positions (실시간 PnL)
        positions_data = context.get_output("account", "positions") or {}
        
        # 6. all_inputs에서 첫 번째 데이터 가져오기 (fallback)
        first_input = None
        if all_inputs:
            first_input = next(iter(all_inputs.values()), None)
        
        # 우선순위: input_data > equity_data > all_inputs > positions
        data = input_data or first_input or positions_data or {}
        
        context.log("debug", f"DisplayNode data resolved: type={type(data).__name__}, equity_data={equity_data is not None}", node_id)
        
        # balance 정보도 가져오기
        balance = context.get_output("account", "balance") or {}
        
        chart_type = config.get("chart_type", "table")
        title = config.get("title", "")
        options = config.get("options", {})
        
        if chart_type == "table" and data:
            # 테이블 출력
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{title} [{now}]")
            
            # 데이터 형태에 따른 분기 처리
            # 1. dict of dicts: {symbol: {field: value, ...}} - 포지션 형태
            # 2. list of dicts: [{field: value}, ...] - 일반 테이블
            # 3. flat dict: {field: value} - 단순 메트릭
            
            is_positions_format = (
                isinstance(data, dict) and 
                data and 
                all(isinstance(v, dict) for v in data.values())
            )
            
            is_list_format = isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict)
            is_flat_dict = isinstance(data, dict) and data and not is_positions_format
            
            if is_positions_format:
                # 포지션 형태 (원래 로직)
                print("=" * 100)
                print(f"{'Symbol':<10} {'Name':<15} {'Qty':>10} {'Avg Price':>12} {'Cur Price':>12} {'PnL Rate':>10} {'PnL Amount':>14}")
                print("-" * 100)
                
                # 정렬
                sort_by = options.get("sort_by", "symbol")
                sort_order = options.get("sort_order", "asc")
                sorted_data = sorted(
                    data.values(),
                    key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by, 0), (int, float)) else str(x.get(sort_by, "")),
                    reverse=(sort_order == "desc"),
                )
                
                for row in sorted_data:
                    pnl_rate = row.get("pnl_rate", 0)
                    pnl_amount = row.get("pnl_amount", 0)
                    pnl_sign = "+" if pnl_rate >= 0 else ""
                    pnl_color = "\033[92m" if pnl_rate >= 0 else "\033[91m"  # Green/Red
                    reset = "\033[0m"
                    
                    currency = row.get("currency", "USD")
                    currency_symbol = "$" if currency == "USD" else currency + " "
                    
                    # qty가 float인 경우 (소수점 주식)
                    qty = row.get("qty", 0)
                    qty_str = f"{qty:>10.4f}" if isinstance(qty, float) and qty != int(qty) else f"{int(qty):>10}"
                    
                    # name 축약 (15자 이내)
                    name = row.get("name", row.get("symbol", ""))[:15]
                    
                    print(
                        f"{row.get('symbol', ''):<10} "
                        f"{name:<15} "
                        f"{qty_str} "
                        f"{currency_symbol}{row.get('avg_price', 0):>10.4f} "
                        f"{currency_symbol}{row.get('current_price', 0):>10.4f} "
                        f"{pnl_color}{pnl_sign}{pnl_rate:>8.2f}%{reset} "
                        f"{pnl_color}{pnl_sign}{currency_symbol}{pnl_amount:>12.2f}{reset}"
                    )
                
                print("-" * 100)
                total_pnl = sum(r.get("pnl_amount", 0) for r in data.values())
                total_sign = "+" if total_pnl >= 0 else ""
                total_color = "\033[92m" if total_pnl >= 0 else "\033[91m"
                print(f"{'Total':<10} {'':<15} {'':<10} {'':<12} {'':<12} {'':<10} {total_color}{total_sign}${total_pnl:>12.2f}\033[0m")
                
                # balance 정보 표시
                if balance:
                    print("-" * 100)
                    if "total_pnl_rate" in balance:
                        total_rate = balance.get("total_pnl_rate", 0)
                        rate_color = "\033[92m" if total_rate >= 0 else "\033[91m"
                        rate_sign = "+" if total_rate >= 0 else ""
                        print(f"총 수익률: {rate_color}{rate_sign}{total_rate:.2f}%\033[0m")
                    if "total_eval_krw" in balance:
                        print(f"총 평가금액(원화): ₩{balance.get('total_eval_krw', 0):,.0f}")
                    if "total_pnl_krw" in balance:
                        pnl_krw = balance.get("total_pnl_krw", 0)
                        krw_color = "\033[92m" if pnl_krw >= 0 else "\033[91m"
                        krw_sign = "+" if pnl_krw >= 0 else ""
                        print(f"총 평가손익(원화): {krw_color}{krw_sign}₩{pnl_krw:,.0f}\033[0m")
            
            elif is_list_format:
                # 리스트 형태 테이블 (백테스트 summary 리스트 등)
                print("=" * 80)
                if data:
                    columns = list(data[0].keys())
                    header = " | ".join(f"{col:<15}" for col in columns[:6])  # 최대 6컬럼
                    print(header)
                    print("-" * 80)
                    for row in data[:20]:  # 최대 20행
                        values = " | ".join(
                            f"{self._format_value(row.get(col)):<15}" for col in columns[:6]
                        )
                        print(values)
            
            elif is_flat_dict:
                # 단순 key-value 형태 (메트릭)
                print("=" * 50)
                sort_by = options.get("sort_by")
                items = list(data.items())
                if sort_by and sort_by in data:
                    # sort_by 키를 기준으로 정렬하지 않고 그냥 표시
                    pass
                for key, value in items:
                    formatted = self._format_value(value)
                    print(f"  {key:<25}: {formatted}")
            
            print("=" * 80 if not is_positions_format else "=" * 100)
        
        context.log("info", f"Display rendered: {chart_type}", node_id)
        
        # 프론트엔드로 전달할 데이터 구성
        output_data = {
            "rendered": True,
            "chart_type": chart_type,
            "title": title,
            "options": options,
        }
        
        # 차트 타입별 데이터 포맷팅
        if chart_type == "line":
            # 라인 차트용 데이터 (equity_curve 등)
            chart_data = None
            if equity_data:
                chart_data = equity_data
            elif isinstance(data, dict) and "equity_curve" in data:
                chart_data = data["equity_curve"]
            elif isinstance(data, list):
                chart_data = data
            else:
                chart_data = data
            
            output_data["chart_data"] = chart_data
            
            # 콘솔에 간단한 라인 차트 요약 출력
            if chart_data and isinstance(chart_data, list) and len(chart_data) > 0:
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n{title} [{now}]")
                print("=" * 80)
                
                # 시작/끝 값
                first = chart_data[0] if chart_data else {}
                last = chart_data[-1] if chart_data else {}
                
                start_value = first.get("value", 0)
                end_value = last.get("value", 0)
                start_date = first.get("date", "N/A")
                end_date = last.get("date", "N/A")
                
                # 수익률 계산
                if start_value > 0:
                    total_return = (end_value - start_value) / start_value * 100
                else:
                    total_return = 0
                
                return_sign = "+" if total_return >= 0 else ""
                return_color = "\033[92m" if total_return >= 0 else "\033[91m"
                reset = "\033[0m"
                
                print(f"📊 데이터 포인트: {len(chart_data)}일")
                print(f"📅 기간: {start_date} ~ {end_date}")
                print(f"💵 시작 자산: ${start_value:,.2f}")
                print(f"💵 최종 자산: ${end_value:,.2f}")
                print(f"📈 총 수익률: {return_color}{return_sign}{total_return:.2f}%{reset}")
                
                # 자산 최고/최저점 (equity curve)
                values = [d.get("value", 0) for d in chart_data]
                max_val = max(values)
                min_val = min(values)
                print(f"📈 자산 최고점: ${max_val:,.2f}")
                print(f"📉 자산 최저점: ${min_val:,.2f}")
                
                # MDD
                peak = values[0]
                max_dd = 0
                for v in values:
                    if v > peak:
                        peak = v
                    dd = (peak - v) / peak * 100 if peak > 0 else 0
                    if dd > max_dd:
                        max_dd = dd
                print(f"⚠️  최대 낙폭: {max_dd:.2f}%")
                print("=" * 80)
        elif chart_type == "radar":
            # Radar 차트용 데이터 (metrics_list 사용)
            if metrics_list:
                output_data["data"] = metrics_list
                context.log("info", f"Radar chart: {len(metrics_list)} strategies", node_id)
            elif isinstance(data, list):
                output_data["data"] = data
            elif isinstance(data, dict):
                # 단일 metrics 객체인 경우 배열로 감싸기
                output_data["data"] = [data]
            else:
                output_data["data"] = []
        elif chart_type == "bar":
            # Bar 차트용 데이터
            # trades 데이터 결정 (trades_list 또는 data)
            trades_to_process = trades_list if trades_list else []
            
            # data가 trades 형식인지 확인
            if not trades_to_process and isinstance(data, list) and len(data) > 0:
                first = data[0] if data else {}
                if isinstance(first, dict) and "symbol" in first and "action" in first:
                    trades_to_process = data
            
            if trades_to_process:
                # 종목별 투자 비중 및 손익 계산
                symbol_stats = {}
                for trade in trades_to_process:
                    symbol = trade.get("symbol", "unknown")
                    action = trade.get("action", "")
                    price = trade.get("price", 0)
                    qty = trade.get("qty", 0)
                    cost = trade.get("cost", price * qty)
                    
                    if symbol not in symbol_stats:
                        symbol_stats[symbol] = {"buy_cost": 0, "sell_revenue": 0, "buy_qty": 0, "sell_qty": 0}
                    
                    if action == "buy":
                        symbol_stats[symbol]["buy_cost"] += cost
                        symbol_stats[symbol]["buy_qty"] += qty
                    elif action == "sell":
                        symbol_stats[symbol]["sell_revenue"] += price * qty
                        symbol_stats[symbol]["sell_qty"] += qty
                
                # 종목별 기여도 계산
                bar_data = []
                has_sells = any(s["sell_qty"] > 0 for s in symbol_stats.values())
                
                for symbol, stats in symbol_stats.items():
                    if has_sells and stats["sell_qty"] > 0:
                        # 매도가 있는 경우: 실현 손익
                        avg_buy = stats["buy_cost"] / stats["buy_qty"] if stats["buy_qty"] > 0 else 0
                        profit = stats["sell_revenue"] - (avg_buy * stats["sell_qty"])
                        bar_data.append({"name": symbol, "value": round(profit, 2)})
                    else:
                        # 매도가 없는 경우 (Buy & Hold): 투자 금액 표시
                        bar_data.append({"name": symbol, "value": round(stats["buy_cost"], 2)})
                
                # 값 순으로 정렬
                bar_data.sort(key=lambda x: x["value"], reverse=True)
                output_data["data"] = bar_data
                
                label = "실현 손익" if has_sells else "투자 금액"
                context.log("info", f"Bar chart ({label}): {len(bar_data)} symbols from {len(trades_to_process)} trades", node_id)
            elif isinstance(data, list) and len(data) > 0:
                # 일반 배열 데이터
                output_data["data"] = data
            elif isinstance(data, dict):
                output_data["data"] = [{"name": k, "value": v} for k, v in data.items() if isinstance(v, (int, float))]
            else:
                output_data["data"] = []
        else:
            # 테이블용 데이터 - 구조화된 객체 배열로 전달
            if metrics_list:
                # 여러 전략의 metrics를 테이블로 표시
                output_data["table_data"] = metrics_list
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                # 이미 객체 배열인 경우 그대로 사용
                output_data["table_data"] = data
            elif isinstance(data, dict):
                # 단일 dict → 객체 배열로 감싸기
                output_data["table_data"] = [data]
            else:
                output_data["table_data"] = [data] if data else []
        
        # Notify listeners for inline display visualization
        # Prepare chart data for frontend
        frontend_chart_data = None
        if chart_type == "line":
            frontend_chart_data = output_data.get("chart_data")
        elif chart_type in ("radar", "bar"):
            frontend_chart_data = output_data.get("data")
        elif chart_type == "table":
            frontend_chart_data = output_data.get("table_data")
        elif chart_type == "candlestick":
            # OHLC data
            frontend_chart_data = equity_data or data
        elif chart_type in ("scatter", "heatmap"):
            frontend_chart_data = data
        
        # ========================================
        # Fallback: 차트 데이터가 없으면 raw data를 JSON으로 표시
        # ========================================
        if frontend_chart_data is None or (isinstance(frontend_chart_data, (list, dict)) and not frontend_chart_data):
            # 원본 데이터가 있으면 raw로 출력
            raw_data = data or all_inputs or {}
            if raw_data:
                context.log("info", f"DisplayNode: chart_type '{chart_type}'에 맞는 데이터 없음, raw JSON으로 표시", node_id)
                
                # 콘솔에 raw JSON 출력
                import json
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n📋 {title or 'Raw Output'} [{now}]")
                print("=" * 60)
                try:
                    # Pydantic 모델이나 특수 객체 처리
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
                    
                    serialized = serialize(raw_data)
                    print(json.dumps(serialized, indent=2, ensure_ascii=False, default=str))
                except Exception as e:
                    print(f"(직렬화 실패: {e})")
                    print(str(raw_data)[:500])
                print("=" * 60 + "\n")
                
                # 프론트엔드로 raw 데이터 전송 (테이블 형식으로)
                frontend_chart_data = raw_data
                chart_type = "raw"  # 프론트엔드에서 JSON viewer로 처리
                output_data["chart_type"] = "raw"
                output_data["raw_data"] = raw_data
        
        if frontend_chart_data is not None:
            await context.notify_display_data(
                node_id=node_id,
                chart_type=chart_type,
                title=title,
                data=frontend_chart_data,
                x_label=config.get("x_label"),
                y_label=config.get("y_label"),
                options=options,
            )
        
        return output_data


class ConditionNodeExecutor(NodeExecutorBase):
    """
    ConditionNode executor (plugin-based)
    
    두 가지 모드 지원:
    1. 실시간 모드: 단일 시점 price_data → result: bool
    2. 백테스트 모드: 시계열 ohlcv_data → signals: list
    
    입력 데이터 형태를 자동 감지하여 모드 결정.
    리소스 관리 시스템과 연동하여 배치 크기 및 속도를 조절합니다.
    플러그인은 PluginSandbox를 통해 타임아웃 보호됩니다.
    """

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
            # 입력 데이터 수집
            symbols = context.get_output(f"_input_{node_id}", "symbols") or []
            price_data = context.get_output(f"_input_{node_id}", "price_data") or {}
            
            # 시계열 데이터 확인 (HistoricalDataNode에서 온 경우)
            ohlcv_data = price_data
            if not ohlcv_data:
                ohlcv_data = context.get_output("historicalData", "ohlcv_data") or {}
            
            # fields 표현식 평가
            evaluated_fields = fields or config.get("fields", {}) or config.get("params", {})
            if evaluated_fields:
                expr_context = context.get_expression_context()
                evaluator = ExpressionEvaluator(expr_context)
                evaluated_fields = evaluator.evaluate_fields(evaluated_fields)
            
            # 시계열 모드 감지
            is_timeseries = self._is_timeseries_data(ohlcv_data)
            
            if is_timeseries:
                # 백테스트 모드: 시계열 전체에 대해 시그널 생성
                context.log("info", f"Condition running in backtest mode (timeseries)", node_id)
                return await self._execute_backtest_mode(
                    node_id, ohlcv_data, evaluated_fields, plugin, context, sandbox,
                    plugin_id=plugin_id,
                    batch_size=recommended_batch_size
                )
            else:
                # 실시간 모드: 단일 시점 평가
                context.log("info", f"Condition running in realtime mode", node_id)
                return await self._execute_realtime_mode(
                    node_id, symbols, price_data, evaluated_fields, plugin, context, sandbox,
                    plugin_id=plugin_id
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

    def _is_timeseries_data(self, data: Any) -> bool:
        """시계열 데이터인지 확인"""
        if not data:
            return False
        
        # {symbol: [{date, open, high, low, close, volume}, ...]} 형태인지 확인
        if isinstance(data, dict):
            first_value = next(iter(data.values()), None)
            if isinstance(first_value, list) and len(first_value) > 1:
                # 리스트가 2개 이상이고 date 필드가 있으면 시계열
                if isinstance(first_value[0], dict) and "date" in first_value[0]:
                    return True
        
        return False

    async def _execute_realtime_mode(
        self,
        node_id: str,
        symbols: List[str],
        price_data: Dict[str, Any],
        fields: Dict[str, Any],
        plugin: Optional[Callable],
        context: ExecutionContext,
        sandbox: "PluginSandbox",
        plugin_id: str = "Unknown",
    ) -> Dict[str, Any]:
        """실시간 모드: 단일 시점 평가 (샌드박스 적용)"""
        from programgarden.plugin import PluginSandbox, PluginTimeoutError
        
        passed_symbols = []
        failed_symbols = []
        values = {}

        if plugin:
            # 샌드박스에서 플러그인 실행
            try:
                if len(symbols) > sandbox._default_batch_size:
                    # 대량 종목은 배치 처리
                    result = await sandbox.execute_batched(
                        plugin_id=plugin_id,
                        plugin_callable=plugin,
                        symbols=symbols,
                        price_data=price_data,
                        fields=fields,
                    )
                else:
                    # 일반 실행
                    result = await sandbox.execute(
                        plugin_id=plugin_id,
                        plugin_callable=plugin,
                        kwargs={"symbols": symbols, "price_data": price_data, "fields": fields},
                    )
                
                passed_symbols = result.get("passed_symbols", [])
                failed_symbols = result.get("failed_symbols", [])
                values = result.get("values", {})
            except PluginTimeoutError as e:
                context.log("error", f"Plugin timeout: {e}", node_id)
                failed_symbols = symbols
            except Exception as e:
                context.log("error", f"Plugin error: {e}", node_id)
                failed_symbols = symbols
        else:
            # 플러그인 없으면 모두 통과
            passed_symbols = symbols
            for symbol in symbols:
                values[symbol] = {"result": True}

        context.log(
            "info",
            f"Condition evaluated: {len(passed_symbols)}/{len(symbols)} passed",
            node_id,
        )

        return {
            "result": len(passed_symbols) > 0,
            "passed_symbols": passed_symbols,
            "failed_symbols": failed_symbols,
            "values": values,
        }

    async def _execute_backtest_mode(
        self,
        node_id: str,
        ohlcv_data: Dict[str, List[Dict]],
        fields: Dict[str, Any],
        plugin: Optional[Callable],
        context: ExecutionContext,
        sandbox: "PluginSandbox",
        plugin_id: str = "Unknown",
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """
        백테스트 모드: 시계열 전체에 대해 시그널 생성 (샌드박스 적용)
        
        각 bar에 대해 플러그인을 호출하여 시그널 시계열 생성.
        플러그인은 해당 시점까지의 데이터만 받음 (미래 데이터 누출 방지).
        
        리소스 관리:
        - batch_size 단위로 처리 후 리소스 상태 체크
        - 리소스 부족 시 recommended_delay 적용
        """
        from programgarden.plugin import PluginTimeoutError
        
        signals = []
        all_values = {}
        
        # 첫 번째 종목의 날짜 리스트 기준
        if not ohlcv_data:
            return {"signals": [], "result": False}
        
        first_symbol = list(ohlcv_data.keys())[0]
        bars = ohlcv_data.get(first_symbol, [])
        symbols = list(ohlcv_data.keys())
        
        # 최소 데이터 포인트 (지표 계산에 필요)
        min_bars = fields.get("period", 14) + 5
        
        # 배치 처리
        batch_count = 0
        
        for i, bar in enumerate(bars):
            date = bar.get("date", "")
            
            # 충분한 데이터가 없으면 hold
            if i < min_bars:
                signals.append({
                    "date": date,
                    "signal": "hold",
                    "symbols": [],
                    "values": {},
                })
                continue
            
            # 배치 단위 리소스 체크 (batch_size마다)
            batch_count += 1
            if batch_count >= batch_size:
                batch_count = 0
                # 리소스 상태 확인 (권한 재획득 아님, 상태만 체크)
                if context.resource:
                    check = await context.check_resources_before_task(
                        task_type="ConditionNode",
                        weight=0.5,  # 배치 체크는 가벼움
                        timeout=5.0,
                    )
                    if check.get("can_proceed"):
                        # 권장 지연 적용
                        delay = check.get("recommended_delay", 0)
                        if delay > 0:
                            await asyncio.sleep(delay)
                        # 리소스 반환
                        await context.release_resources_after_task("ConditionNode", 0.5)
                    else:
                        # 리소스 부족 시 잠시 대기
                        context.log("debug", f"Resource throttle at bar {i}, waiting...", node_id)
                        await asyncio.sleep(0.5)
                        await context.release_resources_after_task("ConditionNode", 0.5)
            
            # 해당 시점까지의 데이터만 추출 (미래 데이터 누출 방지)
            context_data = {}
            for symbol, symbol_bars in ohlcv_data.items():
                context_data[symbol] = {
                    "prices": [b["close"] for b in symbol_bars[:i+1]],
                    "volumes": [b.get("volume", 0) for b in symbol_bars[:i+1]],
                    "current": symbol_bars[i] if i < len(symbol_bars) else {},
                }
            
            # 플러그인 호출 (샌드박스 적용)
            if plugin:
                try:
                    result = await sandbox.execute(
                        plugin_id=f"{plugin_id}:bar{i}",
                        plugin_callable=plugin,
                        kwargs={"symbols": symbols, "price_data": context_data, "fields": fields},
                        timeout=10.0,  # 개별 bar는 짧은 타임아웃
                    )
                    passed = result.get("passed_symbols", [])
                    values = result.get("values", {})
                    
                    # 시그널 결정
                    if passed:
                        signal_type = "buy"  # 조건 충족 = 매수 신호
                    else:
                        signal_type = "hold"
                    
                    signals.append({
                        "date": date,
                        "signal": signal_type,
                        "symbols": passed,
                        "values": values,
                    })
                    
                    # 값 저장
                    for symbol, val in values.items():
                        if symbol not in all_values:
                            all_values[symbol] = []
                        all_values[symbol].append({"date": date, **val})
                
                except PluginTimeoutError:
                    context.log("warning", f"Plugin timeout at {date}", node_id)
                    signals.append({"date": date, "signal": "hold", "symbols": [], "values": {}})
                except Exception as e:
                    context.log("warning", f"Plugin error at {date}: {e}", node_id)
                    signals.append({"date": date, "signal": "hold", "symbols": [], "values": {}})
            else:
                # 플러그인 없으면 데모용 신호 생성
                import random
                signal_type = random.choices(["buy", "hold", "sell"], weights=[0.1, 0.8, 0.1])[0]
                signals.append({
                    "date": date,
                    "signal": signal_type,
                    "symbols": symbols if signal_type == "buy" else [],
                    "values": {},
                })
        
        context.log(
            "info",
            f"Generated {len(signals)} signals, {sum(1 for s in signals if s['signal'] == 'buy')} buy signals",
            node_id,
        )
        
        return {
            "signals": signals,
            "result": any(s["signal"] == "buy" for s in signals),
            "values_timeseries": all_values,
        }


class HistoricalDataNodeExecutor(NodeExecutorBase):
    """
    HistoricalDataNode executor - 과거 OHLCV 데이터 조회
    
    LS Finance Chart API를 사용하여 과거 차트 데이터를 조회합니다.
    - 해외주식: g3103 (일/주/월봉)
    - 해외선물: o3108 (일봉), o3103 (분봉)
    """

    # 거래소 코드 매핑 (해외주식)
    EXCHANGE_CODES = {
        "NASDAQ": "82",
        "NYSE": "81",
        "AMEX": "83",
        # 기본값으로 NASDAQ 사용
    }

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """과거 데이터 조회"""
        
        # 입력 symbols 가져오기
        input_symbols = context.get_output(f"_input_{node_id}", "symbols")
        symbols = input_symbols or config.get("symbols", [])
        
        # positions 데이터 가져오기 (market_code 포함)
        positions = context.get_output(f"_input_{node_id}", "positions")
        if not positions:
            positions = context.get_output("account", "positions") or {}
        
        if not symbols:
            context.log("warning", "No symbols provided", node_id)
            return {"ohlcv_data": {}, "symbols": []}
        
        # 기간 설정
        start_date = config.get("start_date", "")
        end_date = config.get("end_date", "")
        interval = config.get("interval", "1d")  # 1d, 1w, 1m, 1min 등
        
        # dynamic: 표현식 처리
        if start_date.startswith("dynamic:"):
            start_date = self._resolve_dynamic_date(start_date)
        if end_date.startswith("dynamic:"):
            end_date = self._resolve_dynamic_date(end_date)
        
        # 날짜 형식 변환: YYYY-MM-DD → YYYYMMDD (finance 패키지 요구사항)
        start_date = self._normalize_date_format(start_date)
        end_date = self._normalize_date_format(end_date)
        
        # BrokerNode에서 product 정보 가져오기
        broker_connection = context.get_output("broker", "connection") or {}
        product = broker_connection.get("product", "overseas_stock")
        
        context.log(
            "info", 
            f"Fetching historical data: {len(symbols)} symbols, {start_date}~{end_date}, {interval}", 
            node_id
        )
        
        # product별 분기
        if product == "overseas_stock":
            ohlcv_data = await self._fetch_overseas_stock(symbols, start_date, end_date, interval, context, node_id, positions)
        elif product == "overseas_futureoption":
            ohlcv_data = await self._fetch_overseas_futures(symbols, start_date, end_date, interval, context, node_id)
        else:
            context.log("warning", f"Unsupported product: {product}, using demo data", node_id)
            ohlcv_data = self._generate_demo_data(symbols, start_date, end_date)
        
        return {
            "ohlcv_data": ohlcv_data,
            "symbols": list(ohlcv_data.keys()),
            "period": f"{start_date}~{end_date}",
            "interval": interval,
        }

    def _resolve_dynamic_date(self, expr: str) -> str:
        """dynamic: 표현식 해석"""
        from datetime import datetime, timedelta
        
        today = datetime.now()
        
        if "today()" in expr:
            return today.strftime("%Y%m%d")
        elif "months_ago(" in expr:
            # dynamic:months_ago(3)
            import re
            match = re.search(r'months_ago\((\d+)\)', expr)
            if match:
                months = int(match.group(1))
                result = today - timedelta(days=months * 30)
                return result.strftime("%Y%m%d")
        elif "days_ago(" in expr:
            import re
            match = re.search(r'days_ago\((\d+)\)', expr)
            if match:
                days = int(match.group(1))
                result = today - timedelta(days=days)
                return result.strftime("%Y%m%d")
        
        return expr.replace("dynamic:", "")

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
    ) -> Dict[str, List[Dict[str, Any]]]:
        """해외주식 차트 데이터 조회 (g3103)"""
        
        credential = context.get_credential()
        if not credential:
            context.log("warning", "No credential, using demo data", node_id)
            return self._generate_demo_data(symbols, start_date, end_date)
        
        try:
            from programgarden_finance import LS
            from programgarden_finance.ls.overseas_stock.chart.g3103.blocks import G3103InBlock
            
            ls = LS.get_instance()
            
            if not ls.is_logged_in():
                ls.login(
                    appkey=credential.get("appkey"),
                    appsecretkey=credential.get("appsecret"),
                    paper_trading=credential.get("paper_trading", False),
                )
            
            api = ls.overseas_stock()
            
            # interval → gubun 변환
            gubun_map = {"1d": "2", "1w": "3", "1M": "4"}
            gubun = gubun_map.get(interval, "2")
            
            ohlcv_data = {}
            
            for symbol in symbols:
                try:
                    # positions에서 market_code 가져오기 (LS증권 거래소 코드: 81=NYSE, 82=NASDAQ, 83=AMEX 등)
                    exchcd = "82"  # 기본값 NASDAQ
                    if positions and symbol in positions:
                        pos_market_code = positions[symbol].get("market_code", "")
                        if pos_market_code:
                            exchcd = pos_market_code
                    
                    keysymbol = f"{exchcd}{symbol}"
                    
                    # end_date는 이미 YYYYMMDD 형식으로 정규화됨
                    body = G3103InBlock(
                        keysymbol=keysymbol,
                        exchcd=exchcd,
                        symbol=symbol,
                        gubun=gubun,
                        date=end_date,
                    )
                    
                    # chart()는 메서드, req_async() 사용
                    result = await api.chart().g3103(body=body).req_async()
                    
                    if result.block1:
                        bars = []
                        for item in result.block1:
                            bars.append({
                                "date": item.chedate,
                                "open": float(item.open) if item.open else 0,
                                "high": float(item.high) if item.high else 0,
                                "low": float(item.low) if item.low else 0,
                                "close": float(item.price) if item.price else 0,
                                "volume": int(item.volume) if item.volume else 0,
                            })
                        # 날짜순 정렬 (오래된 것부터)
                        bars.sort(key=lambda x: x["date"])
                        ohlcv_data[symbol] = bars
                        context.log("debug", f"Fetched {len(bars)} bars for {symbol}", node_id)
                    else:
                        context.log("warning", f"No data for {symbol}", node_id)
                        ohlcv_data[symbol] = []
                        
                except Exception as e:
                    context.log("warning", f"Error fetching {symbol}: {e}", node_id)
                    ohlcv_data[symbol] = []
            
            return ohlcv_data
            
        except ImportError as e:
            context.log("warning", f"Finance package not available: {e}, using demo data", node_id)
            return self._generate_demo_data(symbols, start_date, end_date)
        except Exception as e:
            context.log("error", f"Error fetching data: {e}", node_id)
            return self._generate_demo_data(symbols, start_date, end_date)

    async def _fetch_overseas_futures(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        interval: str,
        context: ExecutionContext,
        node_id: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        해외선물 차트 데이터 조회 (o3108 일봉 / o3103 분봉)
        
        - 일봉/주봉/월봉: o3108
        - 분봉 (30초, 1분, 30분 등): o3103
        """
        credential = context.get_credential()
        if not credential:
            context.log("warning", "No credential, using demo data for futures", node_id)
            return self._generate_demo_data(symbols, start_date, end_date)
        
        try:
            from programgarden_finance import LS
            
            ls = LS.get_instance()
            
            if not ls.is_logged_in():
                ls.login(
                    appkey=credential.get("appkey"),
                    appsecretkey=credential.get("appsecret"),
                    paper_trading=credential.get("paper_trading", False),
                )
            
            api = ls.overseas_futureoption()
            ohlcv_data = {}
            
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
                    
                    ohlcv_data[symbol] = bars
                    context.log("debug", f"Fetched {len(bars)} bars for {symbol}", node_id)
                    
                except Exception as e:
                    context.log("warning", f"Error fetching futures {symbol}: {e}", node_id)
                    ohlcv_data[symbol] = []
            
            return ohlcv_data
            
        except ImportError as e:
            context.log("warning", f"Finance package not available: {e}, using demo data", node_id)
            return self._generate_demo_data(symbols, start_date, end_date)
        except Exception as e:
            context.log("error", f"Error fetching futures data: {e}", node_id)
            return self._generate_demo_data(symbols, start_date, end_date)

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

    def _generate_demo_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """데모용 OHLCV 데이터 생성"""
        from datetime import datetime, timedelta
        import random
        
        ohlcv_data = {}
        
        for symbol in symbols:
            base_price = random.uniform(100, 500)
            bars = []
            
            # 시작일부터 90일치 데이터 생성
            try:
                start = datetime.strptime(start_date.replace("-", ""), "%Y%m%d")
            except:
                start = datetime.now() - timedelta(days=90)
            
            for i in range(90):
                date = start + timedelta(days=i)
                change = random.uniform(-0.03, 0.035)
                base_price *= (1 + change)
                
                bars.append({
                    "date": date.strftime("%Y%m%d"),
                    "open": round(base_price * 0.99, 2),
                    "high": round(base_price * 1.02, 2),
                    "low": round(base_price * 0.98, 2),
                    "close": round(base_price, 2),
                    "volume": random.randint(1000000, 10000000),
                })
            
            ohlcv_data[symbol] = bars
        
        return ohlcv_data


class BacktestEngineNodeExecutor(NodeExecutorBase):
    """
    BacktestEngineNode executor - 백테스트 시뮬레이션 엔진
    
    입력:
    - ohlcv_data: 종목별 OHLCV 데이터
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
            # 입력 데이터 가져오기
            ohlcv_data = context.get_output(f"_input_{node_id}", "ohlcv_data")
            if not ohlcv_data:
                ohlcv_data = context.get_output("historicalData", "ohlcv_data") or {}
            
            signals = context.get_output(f"_input_{node_id}", "signals")
            if not signals:
                # ConditionNode에서 온 시그널
                signals = context.get_output(f"_input_{node_id}", "entry_signal") or []
            
            # 설정
            initial_capital = config.get("initial_capital", 10000)
            commission_rate = config.get("commission_rate", 0.001)
            slippage = config.get("slippage", 0.0005)
            
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
            )
            
            # 성과 지표 계산
            metrics = self._calculate_metrics(result["equity_curve"], initial_capital)
            
            context.log(
                "info", 
                f"Backtest complete: return={metrics['total_return']:.2f}%, trades={len(result['trades'])}", 
                node_id
            )
            
            return {
                "equity_curve": result["equity_curve"],
                "trades": result["trades"],
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

    def _run_simulation(
        self,
        ohlcv_data: Dict[str, List[Dict]],
        signals: List[Dict],
        initial_capital: float,
        commission_rate: float,
        slippage: float,
    ) -> Dict[str, Any]:
        """백테스트 시뮬레이션 실행"""
        
        equity_curve = []
        trades = []
        
        cash = initial_capital
        positions = {}  # {symbol: {"qty": 10, "avg_price": 100}}
        
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
        # signals가 bool, None, 빈 리스트 등일 때 처리
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
                        positions[symbol] = {"qty": qty, "avg_price": price}
                        
                        trades.append({
                            "date": date,
                            "symbol": symbol,
                            "action": "buy",
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
                    price = prices.get(symbol, 0)
                    
                    if action == "buy" and price > 0 and cash > 0:
                        # 매수: 자본의 10%씩
                        amount = cash * 0.1
                        qty = amount / (price * (1 + slippage))
                        cost = qty * price * (1 + commission_rate)
                        
                        if cost <= cash:
                            cash -= cost
                            if symbol not in positions:
                                positions[symbol] = {"qty": 0, "avg_price": 0}
                            
                            # 평균 단가 계산
                            old_qty = positions[symbol]["qty"]
                            old_avg = positions[symbol]["avg_price"]
                            new_qty = old_qty + qty
                            new_avg = (old_qty * old_avg + qty * price) / new_qty if new_qty > 0 else price
                            
                            positions[symbol] = {"qty": new_qty, "avg_price": new_avg}
                            
                            trades.append({
                                "date": date,
                                "symbol": symbol,
                                "action": "buy",
                                "price": price,
                                "qty": qty,
                                "cost": cost,
                            })
                    
                    elif action == "sell" and symbol in positions and positions[symbol]["qty"] > 0:
                        # 매도: 전량 매도
                        qty = positions[symbol]["qty"]
                        proceeds = qty * price * (1 - commission_rate)
                        pnl = proceeds - qty * positions[symbol]["avg_price"]
                        
                        cash += proceeds
                        positions[symbol] = {"qty": 0, "avg_price": 0}
                        
                        trades.append({
                            "date": date,
                            "symbol": symbol,
                            "action": "sell",
                            "price": price,
                            "qty": qty,
                            "proceeds": proceeds,
                            "pnl": pnl,
                        })
            
            # 포트폴리오 가치 계산
            portfolio_value = cash
            for symbol, pos in positions.items():
                if pos["qty"] > 0:
                    price = prices.get(symbol, pos["avg_price"])
                    portfolio_value += pos["qty"] * price
            
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
            "ScheduleNode": ScheduleNodeExecutor(),
            "WatchlistNode": WatchlistNodeExecutor(),
            "BrokerNode": BrokerNodeExecutor(),
            "AccountNode": AccountNodeExecutor(),  # 1회성 REST API 조회
            "RealAccountNode": RealAccountNodeExecutor(),  # 실시간 WebSocket
            "RealMarketDataNode": RealMarketDataNodeExecutor(),
            "CustomPnLNode": CustomPnLNodeExecutor(),
            "DisplayNode": DisplayNodeExecutor(),
            "ConditionNode": ConditionNodeExecutor(),
            # Backtest nodes
            "HistoricalDataNode": HistoricalDataNodeExecutor(),
            "BacktestEngineNode": BacktestEngineNodeExecutor(),
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
        workflow_credentials = definition.get("credentials", {})
        
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

        # Add plugin fields for ConditionNode
        if node_type == "ConditionNode":
            return await executor.execute(
                node_id=node_id,
                node_type=node_type,
                config=config,
                context=context,
                plugin=plugin,
                fields=fields,
            )

        return await executor.execute(
            node_id=node_id,
            node_type=node_type,
            config=config,
            context=context,
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
            if node.node_type in ("RealAccountNode", "RealMarketDataNode"):
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
        """Find nodes that should be triggered on realtime update"""
        trigger_nodes = []
        for edge in self.workflow.edges:
            if edge.from_node_id == source_node_id:
                # Check if edge has trigger: "on_update" attribute
                # (This would be set in the DSL edge definition)
                if hasattr(edge, 'trigger') and edge.trigger == "on_update":
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
                
            elif event.type == "schedule_tick":
                self.stats["flow_executions"] += 1
                await self._execute_main_flow()
        
        logger.info("Event loop ended")

    async def _handle_realtime_update(self, event: WorkflowEvent) -> None:
        """
        Handle realtime update event
        
        Re-executes nodes specified in trigger_nodes (from edge trigger: "on_update")
        """
        if not event.trigger_nodes:
            return
        
        logger.debug(f"Realtime update from {event.source_node_id}, triggering: {event.trigger_nodes}")
        
        for node_id in event.trigger_nodes:
            if not self.context.is_running:
                break
            
            node = self.workflow.nodes.get(node_id)
            if not node:
                continue
            
            # Re-execute the triggered node
            try:
                outputs = await self.executor.execute_node(
                    node_id=node_id,
                    node_type=node.node_type,
                    config=node.config,
                    context=self.context,
                    plugin=node.plugin,
                    fields=node.fields,
                )
                
                for port_name, value in outputs.items():
                    self.context.set_output(node_id, port_name, value)
                    
            except Exception as e:
                self.context.log("error", f"Error in triggered node {node_id}: {e}", node_id)
                self.stats["errors_count"] += 1

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
        }
