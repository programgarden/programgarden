"""
ProgramGarden Core - Broker Nodes

상품별 브로커 연결 노드:
- OverseasStockBrokerNode: 해외주식 전용 브로커
- OverseasFuturesBrokerNode: 해외선물 전용 브로커
- KoreaStockBrokerNode: 국내주식 전용 브로커
"""

from typing import Optional, List, Literal, Dict, TYPE_CHECKING, ClassVar, Any
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ProductScope,
    BrokerProvider,
)


class BaseBrokerNode(BaseNode):
    """
    브로커 노드 공통 베이스 클래스

    모든 브로커 노드의 공통 속성:
    - provider: 증권사 (현재 LS증권만 지원)
    - credential_id: 인증정보 참조
    - connection 출력 포트
    """

    category: NodeCategory = NodeCategory.INFRA

    provider: str = Field(
        default="ls-sec.co.kr", description="Broker provider"
    )
    credential_id: Optional[str] = Field(
        default=None, description="Reference to stored credentials"
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
            # Executor 가 DAG 전파용으로 주입하는 불투명 핸들. 일반 노드는
            # 참조할 필요가 없고 broker 의존 노드 (Market/Account/Order)
            # 가 자동 소비. 값 shape 은 내부 전용.
            example={"_opaque": True, "provider": "ls-sec.co.kr"},
        )
    ]


class OverseasStockBrokerNode(BaseBrokerNode):
    """
    해외주식 전용 브로커 연결 노드

    LS증권 OpenAPI를 통해 해외주식 거래를 위한 브로커 연결을 생성합니다.

    Note:
    - 해외주식은 모의투자 미지원 (LS증권 제한)
    - credential_types: broker_ls_overseas_stock
    """

    type: Literal["OverseasStockBrokerNode"] = "OverseasStockBrokerNode"
    description: str = "i18n:nodes.OverseasStockBrokerNode.description"

    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Every workflow that reads overseas stock market data, account state, or places orders",
            "As the only broker when the entire workflow is scoped to overseas_stock product",
        ],
        "when_not_to_use": [
            "Overseas futures workflows — use OverseasFuturesBrokerNode (separate credential type and TR set)",
            "Korean domestic stocks — use KoreaStockBrokerNode",
            "Non-trading workflows (pure HTTP fetch, file read) — skip broker entirely",
        ],
        "typical_scenarios": [
            "Start → OverseasStockBrokerNode → OverseasStockAccountNode → TableDisplayNode",
            "Start → OverseasStockBrokerNode → OverseasStockHistoricalDataNode → ConditionNode → NewOrderNode",
            "Start → OverseasStockBrokerNode → WatchlistNode → OverseasStockMarketDataNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Creates and caches the LS-Sec session so every downstream overseas_stock node shares the same login",
        "`connection` output is auto-injected into every overseas_stock node by the executor — no manual binding required",
        "credential_types=['broker_ls_overseas_stock'] ensures only the correct credential is selected",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Setting `paper_trading: true` on OverseasStockBrokerNode",
            "reason": "LS-Sec does not offer paper trading for overseas stocks; the broker node rejects the session with an explicit error and downstream nodes crash on None connection.",
            "alternative": "Always set `paper_trading: false` (or omit it and rely on the explicit-false default in new workflows).",
        },
        {
            "pattern": "Wiring a single broker across overseas_stock and overseas_futures nodes",
            "reason": "Product scope is a hard separator — overseas_futures nodes ignore stock-broker connections and the executor's auto-inject picks the wrong credential.",
            "alternative": "Add OverseasFuturesBrokerNode in parallel; each product scope's nodes pick up its matching broker automatically.",
        },
        {
            "pattern": "Omitting OverseasStockBrokerNode when using overseas_stock nodes",
            "reason": "Market / account / historical / order nodes all fail at runtime with 'credential not set' because there is no broker to source the LS session from.",
            "alternative": "Always include the broker node in the DAG root path.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Broker → Account balance",
            "description": "Simplest broker-rooted workflow — opens the LS session and reads the overseas stock account state.",
            "workflow_snippet": {
                "id": "broker-stock-account",
                "name": "Broker + account",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "Broker emits a connection handle that the executor auto-injects into AccountNode; AccountNode returns held_symbols / balance / positions.",
        },
        {
            "title": "Broker → Historical → Condition → Order",
            "description": "Full trading path: broker session feeds historical data, a condition plugin decides, then the order node fires when the condition passes.",
            "workflow_snippet": {
                "id": "broker-stock-trade",
                "name": "Broker + RSI + order",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                    {
                        "id": "historical",
                        "type": "OverseasStockHistoricalDataNode",
                        "symbol": "{{ item }}",
                        "period": "1d",
                        "start_date": "20260301",
                        "end_date": "20260401",
                    },
                    {
                        "id": "rsi",
                        "type": "ConditionNode",
                        "plugin": "RSI",
                        "items": {
                            "from": "{{ item.time_series }}",
                            "extract": {
                                "symbol": "{{ item.symbol }}",
                                "exchange": "{{ item.exchange }}",
                                "date": "{{ row.date }}",
                                "close": "{{ row.close }}",
                            },
                        },
                        "fields": {"period": 14, "threshold": 30, "direction": "below"},
                    },
                    {"id": "order", "type": "OverseasStockNewOrderNode", "symbol": "AAPL", "exchange": "NASDAQ", "side": "buy", "quantity": 1, "price": 150.0},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "historical"},
                    {"from": "historical", "to": "rsi"},
                    {"from": "rsi", "to": "order"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Broker session is reused across historical, rsi, and order nodes; order fires when the RSI plugin's `passed` output is true.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No data inputs. Only `credential_id` (points at credentials[].credential_id) and `paper_trading` (must be false for overseas_stock).",
        "output_consumption": "The `connection` output is an opaque handle consumed by the executor's auto-inject logic. Downstream overseas_stock nodes do NOT bind `{{ nodes.broker.connection }}` manually — the executor handles it.",
        "common_combinations": [
            "OverseasStockBrokerNode → OverseasStockAccountNode",
            "OverseasStockBrokerNode → WatchlistNode → OverseasStockHistoricalDataNode → ConditionNode → OverseasStockNewOrderNode",
            "OverseasStockBrokerNode → OverseasStockRealMarketDataNode → ThrottleNode → AIAgentNode",
        ],
        "pitfalls": [
            "paper_trading must be false — overseas_stock has no LS-Sec paper trading channel",
            "One workflow can have only one OverseasStockBrokerNode; duplicates compete for credential injection",
            "Credential type must be `broker_ls_overseas_stock` exactly; `broker_ls_overseas_futureoption` will not match",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode,
        )
        return {
            "provider": FieldSchema(
                name="provider",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockBrokerNode.provider",
                default="ls-sec.co.kr",
                enum_values=["ls-sec.co.kr"],
                enum_labels={"ls-sec.co.kr": "i18n:enums.broker_provider.ls-sec.co.kr"},
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example="ls-sec.co.kr",
            ),
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.OverseasStockBrokerNode.credential_id",
                default=None,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_CREDENTIAL_SELECT,
                credential_types=["broker_ls_overseas_stock"],
                example="cred_stock",
                help_text="Use the credential id provided in user message <credentials_context> block (verbatim). Do NOT invent.",
            ),
        }


class OverseasFuturesBrokerNode(BaseBrokerNode):
    """
    해외선물 전용 브로커 연결 노드

    LS증권 OpenAPI를 통해 해외선물 거래를 위한 브로커 연결을 생성합니다.

    Note:
    - 해외선물은 모의투자 지원
    - credential_types: broker_ls_overseas_futures
    """

    type: Literal["OverseasFuturesBrokerNode"] = "OverseasFuturesBrokerNode"
    description: str = "i18n:nodes.OverseasFuturesBrokerNode.description"
    paper_trading: bool = Field(default=False, description="모의투자 모드")

    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Every overseas futures workflow — CME ES / NQ, SGX Nikkei, HKEX HSI mini, etc.",
            "The only broker for paper-traded futures strategies (paper_trading=True)",
        ],
        "when_not_to_use": [
            "Overseas stock workflows — use OverseasStockBrokerNode (separate TR set, separate credential)",
            "Korean futures (KOSPI200, KRX) — not currently supported; only overseas exchanges ship here",
        ],
        "typical_scenarios": [
            "Start → OverseasFuturesBrokerNode (paper_trading=True) → OverseasFuturesMarketDataNode → chart",
            "Start → OverseasFuturesBrokerNode → OverseasFuturesAccountNode → PortfolioNode",
            "Start → OverseasFuturesBrokerNode → OverseasFuturesRealMarketDataNode → ThrottleNode → strategy",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Only broker that natively supports LS-Sec paper trading (set paper_trading=True)",
        "Auto-injects the connection into every overseas_futures node in the same workflow",
        "credential_types=['broker_ls_overseas_futures'] keeps the selector scoped",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using OverseasFuturesBrokerNode for overseas stock workflows",
            "reason": "The product_scope is futures — stock-scoped nodes (OverseasStockMarketDataNode etc.) ignore this broker's connection.",
            "alternative": "Use OverseasStockBrokerNode for stocks and OverseasFuturesBrokerNode for futures; both can coexist in the same workflow.",
        },
        {
            "pattern": "Defaulting to paper_trading=False for demo / backtest workflows",
            "reason": "Real orders hit the live exchange — paper mode exists precisely so demo workflows stay sandboxed.",
            "alternative": "Set paper_trading=True for any workflow not intended to send live orders.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Paper-traded ES futures account balance",
            "description": "Connect to LS-Sec paper futures account and fetch open positions.",
            "workflow_snippet": {
                "id": "broker-futures-paper",
                "name": "Paper futures + account",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "fut_cred", "paper_trading": True},
                    {"id": "account", "type": "OverseasFuturesAccountNode"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                ],
                "credentials": [
                    {"credential_id": "fut_cred", "type": "broker_ls_overseas_futureoption", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Broker opens a paper-trading session; account returns positions / balance sourced from the paper environment.",
        },
        {
            "title": "Realtime ES ticks throttled into a dashboard",
            "description": "Futures broker emits connection for the realtime market data node; ThrottleNode compresses ticks before the chart.",
            "workflow_snippet": {
                "id": "broker-futures-realtime",
                "name": "Futures realtime + throttle",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "fut_cred", "paper_trading": True},
                    {"id": "realtime", "type": "OverseasFuturesRealMarketDataNode", "symbols": [{"symbol": "ESZ24", "exchange": "CME"}]},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "latest", "interval_sec": 5.0},
                    {"id": "chart", "type": "LineChartNode", "title": "ES price", "data": "{{ nodes.throttle.data }}", "x_field": "timestamp", "y_field": "price"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "realtime"},
                    {"from": "realtime", "to": "throttle"},
                    {"from": "throttle", "to": "chart"},
                ],
                "credentials": [
                    {"credential_id": "fut_cred", "type": "broker_ls_overseas_futureoption", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Realtime node streams ticks through the broker connection; ThrottleNode emits one tick per 5s; chart renders live.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "credential_id (broker_ls_overseas_futures) plus paper_trading boolean. No runtime data inputs.",
        "output_consumption": "Auto-injected into every overseas_futures scoped node. Do not manually bind `{{ nodes.broker.connection }}`.",
        "common_combinations": [
            "OverseasFuturesBrokerNode → OverseasFuturesAccountNode → PortfolioNode",
            "OverseasFuturesBrokerNode → OverseasFuturesRealMarketDataNode → ThrottleNode → strategy",
            "OverseasFuturesBrokerNode → OverseasFuturesHistoricalDataNode → ConditionNode → OverseasFuturesNewOrderNode",
        ],
        "pitfalls": [
            "Credential type must be `broker_ls_overseas_futureoption`",
            "paper_trading=True is not a full sandbox — some TRs still hit the real datafeed; always double-check order nodes before production",
            "Each workflow holds exactly one futures broker; if you also trade stocks, add OverseasStockBrokerNode in parallel",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode,
        )
        return {
            "provider": FieldSchema(
                name="provider",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasFuturesBrokerNode.provider",
                default="ls-sec.co.kr",
                enum_values=["ls-sec.co.kr"],
                enum_labels={"ls-sec.co.kr": "i18n:enums.broker_provider.ls-sec.co.kr"},
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example="ls-sec.co.kr",
            ),
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.OverseasFuturesBrokerNode.credential_id",
                default=None,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_CREDENTIAL_SELECT,
                credential_types=["broker_ls_overseas_futures"],
                example="cred_futures",
                help_text="Use the credential id provided in user message <credentials_context> block (verbatim). Do NOT invent.",
            ),
            "paper_trading": FieldSchema(
                name="paper_trading",
                type=FieldType.BOOLEAN,
                description="i18n:fields.OverseasFuturesBrokerNode.paper_trading",
                default=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example=True,
                help_text="Set true for paper trading mode. Overseas futures only allow paper trading in the test suite.",
            ),
        }


class KoreaStockBrokerNode(BaseBrokerNode):
    """
    국내주식 전용 브로커 연결 노드

    LS증권 OpenAPI를 통해 국내주식 거래를 위한 브로커 연결을 생성합니다.

    Note:
    - 국내주식은 실전투자 전용 (모의투자 미지원)
    - credential_types: broker_ls_korea_stock
    """

    type: Literal["KoreaStockBrokerNode"] = "KoreaStockBrokerNode"
    description: str = "i18n:nodes.KoreaStockBrokerNode.description"

    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Every KRX-listed (KOSPI / KOSDAQ / NXT) stock workflow",
            "Korean account queries (balance, positions, open orders) and fill events",
        ],
        "when_not_to_use": [
            "Overseas stocks — use OverseasStockBrokerNode",
            "Overseas futures — use OverseasFuturesBrokerNode",
            "Korean futures or ELW products — not currently shipped",
        ],
        "typical_scenarios": [
            "Start → KoreaStockBrokerNode → KoreaStockAccountNode → TableDisplayNode",
            "Start → KoreaStockBrokerNode → KoreaStockMarketDataNode → condition → KoreaStockNewOrderNode",
            "Start → KoreaStockBrokerNode → KoreaStockRealMarketDataNode → throttle → strategy",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Dedicated credential type `broker_ls_korea_stock` keeps KRX credentials isolated from overseas ones",
        "Auto-injects connection into every korea_stock scoped node",
        "Executes the Korean-specific workflow P&L tracker (KRW-denominated) when account nodes are wired",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Setting any paper_trading field on KoreaStockBrokerNode",
            "reason": "KRX workflow routes do not support LS-Sec paper trading — the node does not even expose the field, which is intentional. Any `paper_trading: true` injected externally will be rejected.",
            "alternative": "Treat every Korean stock workflow as live; use small quantities during development and rely on `dry_run=True` in ExecutionContext for sandbox runs.",
        },
        {
            "pattern": "Mixing an overseas broker credential into a korea_stock workflow",
            "reason": "The auto-inject match is by product_scope — a mismatched credential type is silently ignored and korea_stock nodes fail with 'credential not set'.",
            "alternative": "Always source `credential_id` from a `broker_ls_korea_stock` credential entry.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "KRX account balance",
            "description": "Connect to the Korean stock account and list positions.",
            "workflow_snippet": {
                "id": "broker-korea-account",
                "name": "Korea stock + account",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "kr_cred"},
                    {"id": "account", "type": "KoreaStockAccountNode"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                ],
                "credentials": [
                    {"credential_id": "kr_cred", "type": "broker_ls_korea_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "AccountNode returns positions / balance in KRW; downstream display shows holdings.",
        },
        {
            "title": "KRX historical + condition",
            "description": "Fetch Korean historical data and run the RSI plugin — reads only, no orders.",
            "workflow_snippet": {
                "id": "broker-korea-historical-condition",
                "name": "Korea historical + RSI",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "kr_cred"},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "005930", "exchange": "KOSPI"}]},
                    {
                        "id": "historical",
                        "type": "KoreaStockHistoricalDataNode",
                        "symbol": "{{ item }}",
                        "period": "1d",
                        "start_date": "20260301",
                        "end_date": "20260401",
                    },
                    {
                        "id": "rsi",
                        "type": "ConditionNode",
                        "plugin": "RSI",
                        "items": {
                            "from": "{{ item.time_series }}",
                            "extract": {
                                "symbol": "{{ item.symbol }}",
                                "exchange": "{{ item.exchange }}",
                                "date": "{{ row.date }}",
                                "close": "{{ row.close }}",
                            },
                        },
                        "fields": {"period": 14, "threshold": 30, "direction": "below"},
                    },
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "historical"},
                    {"from": "historical", "to": "rsi"},
                ],
                "credentials": [
                    {"credential_id": "kr_cred", "type": "broker_ls_korea_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Historical feeds daily bars for Samsung (005930 KOSPI); RSI plugin evaluates oversold signals.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "credential_id only (broker_ls_korea_stock). No paper_trading toggle — live-only.",
        "output_consumption": "Auto-injected into korea_stock scoped nodes; manual binding not needed.",
        "common_combinations": [
            "KoreaStockBrokerNode → KoreaStockAccountNode → TableDisplayNode",
            "KoreaStockBrokerNode → KoreaStockHistoricalDataNode → ConditionNode",
            "KoreaStockBrokerNode → KoreaStockRealMarketDataNode → ThrottleNode → strategy",
        ],
        "pitfalls": [
            "Credential type must be `broker_ls_korea_stock` — overseas credentials will not match even though the fields are identical",
            "Every live order counts — always gate order nodes behind IfNode or ConditionNode when experimenting",
            "Use `dry_run=True` in ExecutionContext for sandbox runs (paper trading is not available at the LS-Sec level)",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode,
        )
        return {
            "provider": FieldSchema(
                name="provider",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockBrokerNode.provider",
                default="ls-sec.co.kr",
                enum_values=["ls-sec.co.kr"],
                enum_labels={"ls-sec.co.kr": "i18n:enums.broker_provider.ls-sec.co.kr"},
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
            ),
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.KoreaStockBrokerNode.credential_id",
                default=None,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_CREDENTIAL_SELECT,
                credential_types=["broker_ls_korea_stock"],
            ),
        }
