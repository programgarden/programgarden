"""
ProgramGarden Core - Portfolio Node

포트폴리오 관리 노드:
- PortfolioNode: 멀티 전략 자본 관리, 리밸런싱 (백테스트 + 실거래 공용)
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
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
        ),
        OutputPort(
            name="combined_metrics",
            type="performance_summary",
            description="i18n:ports.combined_metrics",
        ),
        OutputPort(
            name="allocation_weights",
            type="dict",
            description="i18n:ports.allocation_weights",
        ),
        # 실거래용 출력
        OutputPort(
            name="rebalance_orders",
            type="order_list",
            description="i18n:ports.rebalance_orders",
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
        ),
    ]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 필드 스키마 (클라이언트 UI용)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 자본 배분 설정 ===
            "total_capital": FieldSchema(
                name="total_capital",
                type=FieldType.NUMBER,
                description="i18n:fields.PortfolioNode.total_capital",
                default=100000.0,
                required=False,
                min_value=0,
                bindable=True,
                expression_enabled=True,
                group="basic",
                disabled_when="has_incoming_portfolio_edge",
                override_source="parent_portfolio.allocation * parent_portfolio.total_capital",
                ui_hint="inherited_when_child",
                category=FieldCategory.PARAMETERS,
            ),
            "allocation_method": FieldSchema(
                name="allocation_method",
                type=FieldType.ENUM,
                description="i18n:fields.PortfolioNode.allocation_method",
                default="equal",
                enum_values=["equal", "custom", "risk_parity", "momentum"],
                required=True,
                bindable=False,
                group="allocation",
                category=FieldCategory.PARAMETERS,
            ),
            "custom_allocations": FieldSchema(
                name="custom_allocations",
                type=FieldType.OBJECT,
                description="i18n:fields.PortfolioNode.custom_allocations",
                required=False,
                bindable=False,
                group="allocation",
                ui_component="key_value_editor",
                ui_hint="show_when_allocation_method_is_custom",
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 리밸런싱 및 자본 관리 부가 설정 ===
            "rebalance_rule": FieldSchema(
                name="rebalance_rule",
                type=FieldType.ENUM,
                description="i18n:fields.PortfolioNode.rebalance_rule",
                default="none",
                enum_values=["none", "periodic", "drift", "both"],
                required=True,
                bindable=False,
                group="rebalancing",
                category=FieldCategory.SETTINGS,
            ),
            "rebalance_frequency": FieldSchema(
                name="rebalance_frequency",
                type=FieldType.ENUM,
                description="i18n:fields.PortfolioNode.rebalance_frequency",
                enum_values=["daily", "weekly", "monthly", "quarterly"],
                required=False,
                bindable=False,
                group="rebalancing",
                ui_hint="show_when_rebalance_rule_is_periodic_or_both",
                category=FieldCategory.SETTINGS,
            ),
            "drift_threshold": FieldSchema(
                name="drift_threshold",
                type=FieldType.NUMBER,
                description="i18n:fields.PortfolioNode.drift_threshold",
                default=5.0,
                min_value=0.1,
                max_value=50.0,
                required=False,
                bindable=True,
                expression_enabled=True,
                group="rebalancing",
                ui_hint="show_when_rebalance_rule_is_drift_or_both",
                category=FieldCategory.SETTINGS,
            ),
            "capital_sharing": FieldSchema(
                name="capital_sharing",
                type=FieldType.BOOLEAN,
                description="i18n:fields.PortfolioNode.capital_sharing",
                default=True,
                required=False,
                bindable=False,
                group="capital",
                category=FieldCategory.SETTINGS,
            ),
            "reserve_percent": FieldSchema(
                name="reserve_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.PortfolioNode.reserve_percent",
                default=0.0,
                min_value=0,
                max_value=100,
                required=False,
                bindable=True,
                expression_enabled=True,
                group="capital",
                category=FieldCategory.SETTINGS,
            ),
        }
