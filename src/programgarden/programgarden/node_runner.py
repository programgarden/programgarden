"""
NodeRunner - 워크플로우 없이 개별 노드를 단독 실행하는 경량 러너

브로커 로그인, credential 주입, connection 생성을 자동 처리합니다.

Usage:
    # 단순 노드
    runner = NodeRunner()
    result = await runner.run("HTTPRequestNode", url="https://api.example.com", method="GET")

    # 브로커 의존 노드
    runner = NodeRunner(credentials=[
        {"credential_id": "broker", "type": "broker_ls_overseas_stock",
         "data": {"appkey": "xxx", "appsecret": "yyy"}}
    ])
    result = await runner.run("OverseasStockMarketDataNode",
        credential_id="broker",
        symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        fields=["price", "volume"]
    )

    # async with 패턴 (리소스 자동 정리)
    async with NodeRunner(credentials=[...]) as runner:
        result = await runner.run("OverseasStockAccountNode", credential_id="broker")
"""

import uuid
import logging
from typing import Any, Dict, List, Optional

from programgarden.context import ExecutionContext
from programgarden.executor import WorkflowExecutor

logger = logging.getLogger(__name__)

# 실시간(WebSocket) 노드 타입 - 단독 실행 불가
_REALTIME_NODE_TYPES = frozenset({
    "RealAccountNode",
    "OverseasStockRealAccountNode",
    "OverseasFuturesRealAccountNode",
    "RealMarketDataNode",
    "OverseasStockRealMarketDataNode",
    "OverseasFuturesRealMarketDataNode",
    "RealOrderEventNode",
    "OverseasStockRealOrderEventNode",
    "OverseasFuturesRealOrderEventNode",
})

# BrokerNode 타입 - NodeRunner에서 직접 실행 대신 credential/connection 자동 처리
_BROKER_NODE_TYPES = frozenset({
    "BrokerNode",
    "OverseasStockBrokerNode",
    "OverseasFuturesBrokerNode",
})

# 브로커 의존 노드 - connection 자동 주입이 필요한 노드 타입
_BROKER_DEPENDENT_NODE_TYPES = frozenset({
    # Account
    "AccountNode", "OverseasStockAccountNode", "OverseasFuturesAccountNode",
    "OverseasStockOpenOrdersNode", "OverseasFuturesOpenOrdersNode",
    # Market Data
    "MarketDataNode", "OverseasStockMarketDataNode", "OverseasFuturesMarketDataNode",
    "OverseasStockFundamentalNode",
    # Historical Data
    "HistoricalDataNode", "OverseasStockHistoricalDataNode", "OverseasFuturesHistoricalDataNode",
    # Symbol Query
    "SymbolQueryNode", "OverseasStockSymbolQueryNode", "OverseasFuturesSymbolQueryNode",
    "SymbolFilterNode", "MarketUniverseNode", "ScreenerNode",
    # Order
    "OverseasStockNewOrderNode", "OverseasStockModifyOrderNode", "OverseasStockCancelOrderNode",
    "OverseasFuturesNewOrderNode", "OverseasFuturesModifyOrderNode", "OverseasFuturesCancelOrderNode",
})


class NodeRunner:
    """
    워크플로우 없이 개별 노드를 단독 실행하는 경량 러너.

    브로커 로그인, credential 주입, connection 생성을 자동 처리합니다.

    Args:
        credentials: Credential 목록 (워크플로우 JSON의 credentials와 동일 형식)
        context_params: 실행 컨텍스트 파라미터 (선택)
        raise_on_error: 노드 결과에 error가 있으면 RuntimeError 발생 (기본: True)
    """

    def __init__(
        self,
        credentials: Optional[List[Dict[str, Any]]] = None,
        context_params: Optional[Dict[str, Any]] = None,
        raise_on_error: bool = True,
    ):
        self._credentials = credentials or []
        self._context_params = context_params or {}
        self._raise_on_error = raise_on_error
        self._workflow_executor = WorkflowExecutor()
        # 브로커 로그인 완료 여부 (product별 추적)
        self._broker_logged_in: Dict[str, bool] = {}
        # 실행 컨텍스트 (브로커 세션 재사용을 위해 유지)
        self._context: Optional[ExecutionContext] = None

    def _get_or_create_context(self) -> ExecutionContext:
        """ExecutionContext를 생성하거나 기존 것을 재사용"""
        if self._context is None:
            self._context = ExecutionContext(
                job_id=f"noderunner-{uuid.uuid4().hex[:8]}",
                workflow_id="__standalone__",
                context_params=self._context_params,
                workflow_credentials=self._credentials,
            )
        return self._context

    def _parse_broker_credential(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """
        credential_id에 해당하는 브로커 credential을 찾아 파싱.

        Returns:
            {"appkey", "appsecret", "paper_trading", "product", "provider"} 또는 None
        """
        cred = next(
            (c for c in self._credentials if c.get("credential_id") == credential_id),
            None,
        )
        if not cred:
            return None

        cred_type = cred.get("type", "")
        if not cred_type.startswith("broker_ls_"):
            return None

        # broker_ls_overseas_stock → overseas_stock
        product = cred_type.replace("broker_ls_", "")
        data = cred.get("data", {})

        # list 형태의 data 처리
        if isinstance(data, list):
            parsed = {}
            for item in data:
                if isinstance(item, dict) and "key" in item:
                    parsed[item["key"]] = item.get("value")
            data = parsed

        paper_trading = data.get("paper_trading", False)

        # overseas_stock은 모의투자 미지원 (LS증권)
        if product == "overseas_stock" and paper_trading:
            logger.warning("overseas_stock does not support paper_trading, forcing real mode")
            paper_trading = False

        return {
            "appkey": data.get("appkey", ""),
            "appsecret": data.get("appsecret", ""),
            "paper_trading": paper_trading,
            "product": product,
            "provider": "ls-sec.co.kr",
        }

    async def _ensure_broker_setup(
        self,
        credential_id: str,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """
        브로커 credential을 파싱하고 LS 로그인 + context 설정을 수행.

        Returns:
            connection dict

        Raises:
            ValueError: credential을 찾을 수 없거나 브로커 타입이 아닌 경우
            RuntimeError: LS 로그인 실패
        """
        broker_info = self._parse_broker_credential(credential_id)
        if not broker_info:
            raise ValueError(
                f"Broker credential '{credential_id}' not found or not a broker type. "
                f"Expected type: 'broker_ls_overseas_stock' or 'broker_ls_overseas_futures'"
            )

        product = broker_info["product"]
        appkey = broker_info["appkey"]
        appsecret = broker_info["appsecret"]
        paper_trading = broker_info["paper_trading"]

        if not appkey or not appsecret:
            raise ValueError(f"appkey/appsecret not found in credential '{credential_id}'")

        # context에 secret 설정 (하위 노드 executor가 get_credential()로 접근)
        context.set_secret("credential_id", {
            "appkey": appkey,
            "appsecret": appsecret,
            "paper_trading": paper_trading,
        })

        # LS 로그인 (이미 로그인된 경우 LSClientManager가 재사용)
        if product not in self._broker_logged_in:
            from programgarden.executor import ensure_ls_login

            ls, success, error = ensure_ls_login(
                appkey=appkey,
                appsecret=appsecret,
                paper_trading=paper_trading,
                context=context,
                node_id="__noderunner__",
                product=product,
                caller_name="NodeRunner",
            )
            if not success:
                raise RuntimeError(f"LS login failed for {product}: {error}")
            self._broker_logged_in[product] = True
            logger.info(f"LS login success: {product} (paper_trading={paper_trading})")

        # connection dict 생성 (BrokerNodeExecutor 출력과 동일)
        connection = {
            "provider": broker_info["provider"],
            "product": product,
            "paper_trading": paper_trading,
            "appkey": appkey,
            "appsecret": appsecret,
        }

        return connection

    async def run(
        self,
        node_type: str,
        *,
        node_id: Optional[str] = None,
        credential_id: Optional[str] = None,
        **config,
    ) -> Dict[str, Any]:
        """
        노드 단독 실행.

        Args:
            node_type: 노드 타입명 (예: "OverseasStockMarketDataNode")
            node_id: 노드 ID (생략 시 자동 생성)
            credential_id: 사용할 credential ID (credentials에서 매칭)
            **config: 노드 설정 값 (키워드 인자로 전달)

        Returns:
            노드 실행 결과 (출력 포트 딕셔너리)

        Raises:
            ValueError: 알 수 없는 노드 타입, 실시간 노드, 브로커 노드 직접 실행
            RuntimeError: 실행 실패 (raise_on_error=True인 경우)
        """
        # 실시간 노드 차단
        if node_type in _REALTIME_NODE_TYPES:
            raise ValueError(
                f"'{node_type}'은 실시간(WebSocket) 노드로 단독 실행이 불가합니다. "
                "향후 NodeRunner.subscribe() API로 지원 예정입니다."
            )

        # BrokerNode 직접 실행 차단
        if node_type in _BROKER_NODE_TYPES:
            raise ValueError(
                f"'{node_type}'은 NodeRunner에서 직접 실행할 필요 없습니다. "
                "credential을 전달하면 브로커 로그인이 자동 처리됩니다."
            )

        node_id = node_id or f"{node_type.lower()}-{uuid.uuid4().hex[:6]}"
        context = self._get_or_create_context()

        # credential_id가 있으면 config에 추가
        if credential_id:
            config["credential_id"] = credential_id

        # 브로커 의존 노드면 자동 로그인 + connection 주입
        if node_type in _BROKER_DEPENDENT_NODE_TYPES and credential_id:
            connection = await self._ensure_broker_setup(credential_id, context)
            config["connection"] = connection

        # WorkflowExecutor.execute_node()으로 실행 위임
        result = await self._workflow_executor.execute_node(
            node_id=node_id,
            node_type=node_type,
            config=config,
            context=context,
        )

        # 에러 체크
        if self._raise_on_error and isinstance(result, dict) and "error" in result:
            raise RuntimeError(f"Node '{node_type}' execution failed: {result['error']}")

        return result

    def list_node_types(self) -> List[str]:
        """사용 가능한 노드 타입 목록 조회 (실시간/브로커 노드 제외)"""
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        all_types = registry.list_types()
        excluded = _REALTIME_NODE_TYPES | _BROKER_NODE_TYPES
        return [t for t in sorted(all_types) if t not in excluded]

    def get_node_schema(self, node_type: str) -> Optional[Dict[str, Any]]:
        """노드 스키마(config_schema) 조회"""
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        node_class = registry.get(node_type)
        if not node_class:
            return None

        schema = {}
        if hasattr(node_class, "config_schema"):
            schema = node_class.config_schema()
        elif hasattr(node_class, "model_json_schema"):
            schema = node_class.model_json_schema()
        return schema

    async def cleanup(self) -> None:
        """리소스 정리 (LS 세션 등)"""
        self._broker_logged_in.clear()
        self._context = None
        logger.debug("NodeRunner cleanup completed")

    async def __aenter__(self) -> "NodeRunner":
        return self

    async def __aexit__(self, *args) -> None:
        await self.cleanup()
