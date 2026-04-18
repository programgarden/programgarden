"""
ProgramGarden Core - Portfolio Node

포트폴리오 관리 노드:
- PortfolioNode: 멀티 전략 자본 관리, 리밸런싱 (백테스트 + 실거래 공용)
"""

from typing import Optional, List, Literal, Dict, Any, Set, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ALLOCATED_CAPITAL_FIELDS,
    EQUITY_CURVE_FIELDS,
    ORDER_LIST_FIELDS,
    PERFORMANCE_METRICS_FIELDS,
)


class PortfolioNode(BaseNode):
    """
    포트폴리오 관리 노드

    멀티 전략 자본 배분 및 리밸런싱을 담당합니다.
    백테스트와 실거래 모두에서 사용 가능합니다.

    백테스트 모드:
    - 여러 전략 결과(equity_curve) 합산
    - 리밸런싱 시뮬레이션
    - 통합 성과 지표 계산

    실거래 모드:
    - 실시간 자본 배분 관리
    - 리밸런싱 신호 생성
    - 리밸런싱 주문 목록 출력

    계층적 연결:
    - PortfolioNode 간 연결 가능 (Portfolio of Portfolios)
    - 상위 포트폴리오에서 자본 배분 시 하위의 total_capital은 자동 계산됨
    """

    type: Literal["PortfolioNode"] = "PortfolioNode"
    category: NodeCategory = NodeCategory.RISK
    _risk_features: ClassVar[Set[str]] = {"hwm", "window"}
    description: str = "i18n:nodes.PortfolioNode.description"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 기본 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    total_capital: float = Field(
        default=100000.0,
        description="총 포트폴리오 자본금 (상위 포트폴리오에서 상속 시 자동 계산됨)",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 자본 배분 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    allocation_method: Literal["equal", "custom", "risk_parity", "momentum"] = Field(
        default="equal",
        description="자본 배분 방법 (equal: 균등, custom: 사용자 지정, risk_parity: 리스크 패리티, momentum: 모멘텀 기반)",
    )
    custom_allocations: Optional[Dict[str, float]] = Field(
        default=None,
        description="커스텀 배분 비율 (strategy_id: 비율, 합계=1.0). allocation_method='custom'일 때 사용",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 리밸런싱 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    rebalance_rule: Literal["none", "periodic", "drift", "both"] = Field(
        default="none",
        description="리밸런싱 규칙 (none: 없음, periodic: 주기적, drift: 드리프트 기반, both: 둘 다)",
    )
    rebalance_frequency: Optional[Literal["daily", "weekly", "monthly", "quarterly"]] = Field(
        default=None,
        description="주기적 리밸런싱 빈도 (rebalance_rule이 periodic 또는 both일 때)",
    )
    drift_threshold: Optional[float] = Field(
        default=None,
        description="드리프트 임계값 (%, rebalance_rule이 drift 또는 both일 때). 예: 5.0 → 목표 비중에서 ±5% 이탈 시 리밸런싱",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 자본 공유 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    capital_sharing: bool = Field(
        default=True,
        description="전략간 자본 공유 여부 (True: 유휴 자본 재배분 가능, False: 각 전략 자본 고정)",
    )
    reserve_percent: float = Field(
        default=0.0,
        description="현금 예비금 비율 (%). 예: 5.0 → 총 자본의 5%는 현금으로 유지",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 입출력 포트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _inputs: List[InputPort] = [
        # 백테스트용: 전략별 결과 (BacktestEngineNode 또는 PortfolioNode 출력)
        InputPort(
            name="strategy_results",
            type="portfolio_result",
            description="i18n:ports.strategy_results",
            multiple=True,
            min_connections=1,
        ),
        # 실거래용: 계좌 상태
        InputPort(
            name="account_state",
            type="account_data",
            description="i18n:ports.account_state",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        # 공통 출력
        OutputPort(
            name="combined_equity",
            type="portfolio_result",
            description="i18n:ports.combined_equity",
            fields=EQUITY_CURVE_FIELDS,
        ),
        OutputPort(
            name="combined_metrics",
            type="performance_summary",
            description="i18n:ports.combined_metrics",
            fields=PERFORMANCE_METRICS_FIELDS,
        ),
        OutputPort(
            name="allocation_weights",
            type="dict",
            description="i18n:ports.allocation_weights",
            fields=ALLOCATED_CAPITAL_FIELDS,
        ),
        # 실거래용 출력
        OutputPort(
            name="rebalance_orders",
            type="order_list",
            description="i18n:ports.rebalance_orders",
            fields=ORDER_LIST_FIELDS,
        ),
        OutputPort(
            name="rebalance_signal",
            type="bool",
            description="i18n:ports.rebalance_signal",
        ),
        # 하위 전략/포트폴리오에 전달할 자본 배분
        OutputPort(
            name="allocated_capital",
            type="dict",
            description="i18n:ports.allocated_capital",
            fields=ALLOCATED_CAPITAL_FIELDS,
        ),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Allocate capital across multiple strategies (equal / custom / risk_parity / momentum)",
            "Generate rebalancing signals on a periodic or drift-based schedule",
            "Compose portfolio of portfolios — each PortfolioNode can feed another PortfolioNode",
            "Track combined equity / metrics (Sharpe, MDD) across multiple BacktestEngineNode results",
        ],
        "when_not_to_use": [
            "Single-strategy workflows with no capital-split decision — PositionSizingNode alone is enough",
            "Per-trade position-management (stop-loss / trailing) — use ConditionNode with position plugins",
            "Pure order-routing without rebalancing — skip PortfolioNode",
        ],
        "typical_scenarios": [
            "2× BacktestEngineNode → PortfolioNode(equal) → combined_metrics / equity",
            "Strategy backtests + AccountNode → PortfolioNode(risk_parity, periodic monthly) → rebalance_orders",
            "PortfolioNode → PortfolioNode (parent) for tiered capital hierarchies",
        ],
    }
    _features: ClassVar[List[str]] = [
        "4 allocation methods: equal / custom (explicit weights) / risk_parity / momentum",
        "4 rebalance rules: none / periodic / drift / both (periodic + drift)",
        "Supports Portfolio of Portfolios — nested PortfolioNodes auto-inherit parent's allocated capital",
        "_risk_features={'hwm','window'} — Risk tracker auto-activates for HWM / drawdown monitoring",
        "capital_sharing + reserve_percent knobs govern idle-capital reallocation",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "allocation_method='custom' without `custom_allocations`",
            "reason": "Custom mode requires explicit weights that sum to 1.0 — leaving it empty silently falls back to equal weights, hiding the intent.",
            "alternative": "Always populate `custom_allocations: {strategy_1: 0.4, strategy_2: 0.6}` when method='custom', or pick 'equal' / 'risk_parity' for automatic weighting.",
        },
        {
            "pattern": "rebalance_rule='drift' without `drift_threshold`",
            "reason": "Drift mode needs a numeric threshold to detect when the real weights deviate too far from target; without it nothing triggers.",
            "alternative": "Set `drift_threshold: 5.0` (e.g. rebalance when any strategy drifts >5% from target).",
        },
        {
            "pattern": "Overriding `total_capital` on a child PortfolioNode connected to a parent",
            "reason": "When a parent PortfolioNode feeds allocated_capital downstream, child's total_capital is inherited automatically; manual overrides are ignored or cause inconsistency.",
            "alternative": "Leave `total_capital` at its default for child nodes and bind the parent's `allocated_capital.<strategy_id>` via edge.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Equal-weight backtest portfolio",
            "description": "Two BacktestEngineNode results feed PortfolioNode with equal weighting; combined metrics render downstream.",
            "workflow_snippet": {
                "id": "portfolio-equal-backtest",
                "name": "Equal-weight backtest portfolio",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {
                        "id": "historical",
                        "type": "OverseasStockHistoricalDataNode",
                        "symbol": {"symbol": "SPY", "exchange": "NYSE"},
                        "period": "1d",
                        "start_date": "20260101",
                        "end_date": "20260401",
                    },
                    {
                        "id": "rsi_strategy",
                        "type": "BacktestEngineNode",
                        "strategy": "RSI",
                        "data": "{{ nodes.historical.values }}",
                        "initial_capital": 50000,
                    },
                    {
                        "id": "macd_strategy",
                        "type": "BacktestEngineNode",
                        "strategy": "MACD",
                        "data": "{{ nodes.historical.values }}",
                        "initial_capital": 50000,
                    },
                    {"id": "portfolio", "type": "PortfolioNode", "total_capital": 100000, "allocation_method": "equal"},
                    {"id": "summary", "type": "SummaryDisplayNode", "title": "Combined metrics", "data": "{{ nodes.portfolio.combined_metrics }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "rsi_strategy"},
                    {"from": "historical", "to": "macd_strategy"},
                    {"from": "rsi_strategy", "to": "portfolio"},
                    {"from": "macd_strategy", "to": "portfolio"},
                    {"from": "portfolio", "to": "summary"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "combined_metrics contains aggregated Sharpe / MDD / CAGR across both strategies; equity curves merge 50/50.",
        },
        {
            "title": "Live portfolio with monthly rebalancing",
            "description": "Custom weights (60/40); monthly periodic rebalance generates rebalance_orders when allocation drifts.",
            "workflow_snippet": {
                "id": "portfolio-live-rebalance",
                "name": "Live portfolio with rebalance",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "cron", "type": "ScheduleNode", "cron": "0 9 1 * *", "timezone": "America/New_York"},
                    {
                        "id": "portfolio",
                        "type": "PortfolioNode",
                        "total_capital": 100000,
                        "allocation_method": "custom",
                        "custom_allocations": {"equities": 0.6, "bonds": 0.4},
                        "rebalance_rule": "periodic",
                        "rebalance_frequency": "monthly",
                        "capital_sharing": True,
                    },
                    {"id": "display", "type": "TableDisplayNode", "title": "Rebalance orders", "data": "{{ nodes.portfolio.rebalance_orders }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "start", "to": "cron"},
                    {"from": "cron", "to": "portfolio"},
                    {"from": "account", "to": "portfolio"},
                    {"from": "portfolio", "to": "display"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "On the 1st of each month at 09:00 ET, PortfolioNode emits rebalance_orders when the 60/40 split drifts; table renders the orders.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "`strategy_results` (multiple=True, min=1) from BacktestEngineNode or PortfolioNode. `account_state` optional for live mode. All allocation / rebalance settings are configuration, not bindings.",
        "output_consumption": "`combined_equity` + `combined_metrics` for backtest analytics; `rebalance_orders` + `rebalance_signal` for live rebalancing; `allocated_capital` for cascading to child portfolios; `allocation_weights` for transparency.",
        "common_combinations": [
            "BacktestEngineNode × N → PortfolioNode (equal) → SummaryDisplayNode",
            "PortfolioNode → PortfolioNode (parent→child with inherited total_capital)",
            "ScheduleNode + AccountNode → PortfolioNode (rebalance) → TableDisplayNode(rebalance_orders)",
        ],
        "pitfalls": [
            "`custom_allocations` must sum to 1.0 when method='custom'",
            "`drift_threshold` is required for rebalance_rule in {drift, both}",
            "Child PortfolioNodes should leave `total_capital` unset to inherit from parent",
            "_risk_features={'hwm','window'} activates the risk tracker automatically — expect DB writes when not in dry_run",
        ],
    }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 필드 스키마 (클라이언트 UI용)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 핵심 자본 배분 설정 ===
            "total_capital": FieldSchema(
                name="total_capital",
                type=FieldType.NUMBER,
                description="Total portfolio capital. When connected to parent PortfolioNode, this value is automatically calculated based on parent's allocation.",
                default=100000.0,
                required=False,
                min_value=0,
                expression_mode=ExpressionMode.BOTH,
                group="basic",
                disabled_when="has_incoming_portfolio_edge",
                override_source="parent_portfolio.allocation * parent_portfolio.total_capital",
                ui_hint="inherited_when_child",
                category=FieldCategory.PARAMETERS,
                example=100000.0,
                example_binding="{{ nodes.parentPortfolio.allocated_capital.strategy_1 }}",
                bindable_sources=[
                    "PortfolioNode.allocated_capital",
                    "AccountNode.balance.total",
                ],
                expected_type="float",
            ),
            "allocation_method": FieldSchema(
                name="allocation_method",
                type=FieldType.ENUM,
                description="Capital allocation method. equal: divide equally. custom: use custom_allocations. risk_parity: allocate inversely to volatility. momentum: allocate based on recent returns.",
                default="equal",
                enum_values=["equal", "custom", "risk_parity", "momentum"],
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="allocation",
                category=FieldCategory.PARAMETERS,
                example="equal",
                expected_type="str",
            ),
            "custom_allocations": FieldSchema(
                name="custom_allocations",
                type=FieldType.OBJECT,
                description="Custom allocation weights when allocation_method='custom'. Keys are strategy IDs, values are weights (sum should be 1.0).",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="allocation",
                ui_component=UIComponent.CUSTOM_KEY_VALUE_EDITOR,
                visible_when={"allocation_method": "custom"},
                category=FieldCategory.PARAMETERS,
                example={"momentum_strategy": 0.4, "mean_reversion": 0.3, "trend_following": 0.3},
                expected_type="dict[str, float]",
            ),
            # === SETTINGS: 리밸런싱 및 자본 관리 부가 설정 ===
            "rebalance_rule": FieldSchema(
                name="rebalance_rule",
                type=FieldType.ENUM,
                description="Rebalancing rule. none: no rebalancing. periodic: rebalance at fixed intervals. drift: rebalance when allocation drifts. both: combine periodic and drift.",
                default="none",
                enum_values=["none", "periodic", "drift", "both"],
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="rebalancing",
                category=FieldCategory.SETTINGS,
                example="periodic",
                expected_type="str",
            ),
            "rebalance_frequency": FieldSchema(
                name="rebalance_frequency",
                type=FieldType.ENUM,
                description="Rebalancing frequency when rebalance_rule is 'periodic' or 'both'.",
                enum_values=["daily", "weekly", "monthly", "quarterly"],
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="rebalancing",
                visible_when={"rebalance_rule": ["periodic", "both"]},
                category=FieldCategory.SETTINGS,
                example="monthly",
                expected_type="str",
            ),
            "drift_threshold": FieldSchema(
                name="drift_threshold",
                type=FieldType.NUMBER,
                description="Drift threshold percentage. Rebalance when allocation deviates by this percentage from target. e.g., 5.0 means ±5% drift triggers rebalancing.",
                default=5.0,
                min_value=0.1,
                max_value=50.0,
                required=False,
                expression_mode=ExpressionMode.BOTH,
                group="rebalancing",
                visible_when={"rebalance_rule": ["drift", "both"]},
                category=FieldCategory.SETTINGS,
                example=5.0,
                expected_type="float",
            ),
            "capital_sharing": FieldSchema(
                name="capital_sharing",
                type=FieldType.BOOLEAN,
                description="Allow capital sharing between strategies. When true, idle capital can be reallocated to other strategies.",
                default=True,
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="capital",
                category=FieldCategory.SETTINGS,
            ),
            "reserve_percent": FieldSchema(
                name="reserve_percent",
                type=FieldType.NUMBER,
                description="Cash reserve percentage. This portion of capital is kept as cash and not allocated to strategies. e.g., 5.0 means 5% cash reserve.",
                default=0.0,
                min_value=0,
                max_value=100,
                required=False,
                expression_mode=ExpressionMode.BOTH,
                group="capital",
                category=FieldCategory.SETTINGS,
                example=5.0,
                expected_type="float",
            ),
        }
