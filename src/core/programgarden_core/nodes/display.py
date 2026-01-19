"""
ProgramGarden Core - Display Node

명시적 chart_type 기반 시각화 노드
- chart_type별 필수/선택 필드 정의
- 자동 감지 없음, 모든 필드 명시적 지정
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING, Union
from pydantic import Field, model_validator

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class DisplayNode(BaseNode):
    """
    명시적 chart_type 기반 시각화 노드
    
    차트 타입별 필수 필드:
    - table: data
    - line: data, x_field, y_field
    - multi_line: data, x_field, y_field, series_key
    - candlestick: data, date_field, open_field, high_field, low_field, close_field
    - bar: data, x_field, y_field
    - summary: data (raw JSON 표시)
    
    중첩 데이터 평탄화는 pluck() 함수 사용:
    {{ pluck(nodes.rsiCondition.values, 'time_series') }}
    """

    type: Literal["DisplayNode"] = "DisplayNode"
    category: NodeCategory = NodeCategory.ANALYSIS
    description: str = "i18n:nodes.DisplayNode.description"

    # ========================================
    # 공통 필드
    # ========================================
    chart_type: Literal[
        "table", "line", "multi_line", "candlestick", "bar", "summary"
    ] = Field(
        default="summary",
        description="차트 타입",
    )
    
    title: Optional[str] = Field(
        default=None,
        description="차트 제목",
    )
    
    data: Optional[str] = Field(
        default=None,
        description="데이터 바인딩 (예: {{ nodes.rsiCondition.time_series }})",
    )
    
    # ========================================
    # line / multi_line / bar 공통
    # ========================================
    x_field: Optional[str] = Field(
        default=None,
        description="X축 필드명 (예: date)",
    )
    
    y_field: Optional[str] = Field(
        default=None,
        description="Y축 필드명 (예: rsi)",
    )
    
    # ========================================
    # multi_line 전용
    # ========================================
    series_key: Optional[str] = Field(
        default=None,
        description="시리즈 구분 키 (multi_line용, 예: symbol)",
    )
    
    limit: Optional[int] = Field(
        default=10,
        description="최대 표시 개수",
        ge=1,
        le=100,
    )
    
    sort_by: Optional[str] = Field(
        default=None,
        description="정렬 기준 필드",
    )
    
    sort_order: Optional[Literal["asc", "desc"]] = Field(
        default="desc",
        description="정렬 순서",
    )
    
    # ========================================
    # candlestick 전용
    # ========================================
    date_field: Optional[str] = Field(
        default=None,
        description="날짜 필드명 (candlestick용)",
    )
    
    open_field: Optional[str] = Field(
        default=None,
        description="시가 필드명 (candlestick용)",
    )
    
    high_field: Optional[str] = Field(
        default=None,
        description="고가 필드명 (candlestick용)",
    )
    
    low_field: Optional[str] = Field(
        default=None,
        description="저가 필드명 (candlestick용)",
    )
    
    close_field: Optional[str] = Field(
        default=None,
        description="종가 필드명 (candlestick용)",
    )
    
    volume_field: Optional[str] = Field(
        default=None,
        description="거래량 필드명 (candlestick용, 선택)",
    )
    
    # ========================================
    # 시그널 마커 (line, multi_line, candlestick)
    # ========================================
    signal_field: Optional[str] = Field(
        default=None,
        description="시그널 필드명 (예: signal). buy/sell 값이 있으면 마커 표시",
    )
    
    side_field: Optional[str] = Field(
        default=None,
        description="포지션 방향 필드명 (예: side). long/short 구분. 미지정시 long으로 간주",
    )
    
    # ========================================
    # table 전용
    # ========================================
    columns: Optional[List[str]] = Field(
        default=None,
        description="표시할 컬럼 목록 (미지정시 전체)",
    )

    # ========================================
    # 포트 정의
    # ========================================
    _inputs: List[InputPort] = [
        InputPort(
            name="data",
            type="any",
            description="i18n:ports.data",
            required=False,  # data 필드로 바인딩할 수도 있음
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="rendered",
            type="signal",
            description="렌더링 완료 신호",
        ),
    ]

    @model_validator(mode="after")
    def validate_chart_type_fields(self):
        """chart_type에 따른 필수 필드 검증"""
        chart_type = self.chart_type
        errors = []
        
        # data는 모든 타입에서 필수 (바인딩 또는 엣지로)
        # data 필드가 없어도 엣지로 연결될 수 있으므로 여기선 검증하지 않음
        
        if chart_type == "line":
            if not self.x_field:
                errors.append("x_field")
            if not self.y_field:
                errors.append("y_field")
                
        elif chart_type == "multi_line":
            if not self.x_field:
                errors.append("x_field")
            if not self.y_field:
                errors.append("y_field")
            if not self.series_key:
                errors.append("series_key")
                
        elif chart_type == "candlestick":
            if not self.date_field:
                errors.append("date_field")
            if not self.open_field:
                errors.append("open_field")
            if not self.high_field:
                errors.append("high_field")
            if not self.low_field:
                errors.append("low_field")
            if not self.close_field:
                errors.append("close_field")
                
        elif chart_type == "bar":
            if not self.x_field:
                errors.append("x_field")
            if not self.y_field:
                errors.append("y_field")
        
        # table과 summary는 data만 있으면 됨
        
        if errors:
            raise ValueError(
                f"chart_type '{chart_type}'에 필수 필드 누락: {', '.join(errors)}"
            )
        
        return self

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode, UIComponent
        )
        return {
            "chart_type": FieldSchema(
                name="chart_type",
                type=FieldType.ENUM,
                description="차트 타입",
                enum_values=["table", "line", "multi_line", "candlestick", "bar", "summary"],
                default="summary",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.SELECT,
            ),
            "title": FieldSchema(
                name="title",
                type=FieldType.STRING,
                description="차트 제목",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
            ),
            "data": FieldSchema(
                name="data",
                type=FieldType.STRING,
                description="데이터 바인딩",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                ui_component=UIComponent.BINDING_INPUT,
                example_binding="{{ nodes.condition.values }}",
                bindable_sources=[
                    "ConditionNode.values",
                    "HistoricalDataNode.values",
                    "BacktestEngineNode.equity_curve",
                    "BacktestEngineNode.summary",
                    "RealAccountNode.positions",
                    "RealMarketDataNode.data",
                ],
            ),
            "x_field": FieldSchema(
                name="x_field",
                type=FieldType.STRING,
                description="X축 필드명",
                placeholder="date",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["line", "multi_line", "bar"]},
                group="field_mapping",
            ),
            "y_field": FieldSchema(
                name="y_field",
                type=FieldType.STRING,
                description="Y축 필드명",
                placeholder="rsi",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["line", "multi_line", "bar"]},
                group="field_mapping",
            ),
            "series_key": FieldSchema(
                name="series_key",
                type=FieldType.STRING,
                description="시리즈 구분 키 (심볼별 라인)",
                placeholder="symbol",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["multi_line"]},
                group="field_mapping",
            ),
            "limit": FieldSchema(
                name="limit",
                type=FieldType.INTEGER,
                description="최대 표시 개수",
                default=10,
                min_value=1,
                max_value=100,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.NUMBER_INPUT,
                depends_on={"chart_type": ["multi_line", "table"]},
            ),
            "sort_by": FieldSchema(
                name="sort_by",
                type=FieldType.STRING,
                description="정렬 기준 필드",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["multi_line", "table"]},
            ),
            "sort_order": FieldSchema(
                name="sort_order",
                type=FieldType.ENUM,
                description="정렬 순서",
                enum_values=["asc", "desc"],
                default="desc",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.SELECT,
                depends_on={"chart_type": ["multi_line", "table"]},
            ),
            "date_field": FieldSchema(
                name="date_field",
                type=FieldType.STRING,
                description="날짜 필드명",
                placeholder="date",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["candlestick"]},
                group="field_mapping",
            ),
            "open_field": FieldSchema(
                name="open_field",
                type=FieldType.STRING,
                description="시가 필드명",
                placeholder="open",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["candlestick"]},
                group="field_mapping",
            ),
            "high_field": FieldSchema(
                name="high_field",
                type=FieldType.STRING,
                description="고가 필드명",
                placeholder="high",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["candlestick"]},
                group="field_mapping",
            ),
            "low_field": FieldSchema(
                name="low_field",
                type=FieldType.STRING,
                description="저가 필드명",
                placeholder="low",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["candlestick"]},
                group="field_mapping",
            ),
            "close_field": FieldSchema(
                name="close_field",
                type=FieldType.STRING,
                description="종가 필드명",
                placeholder="close",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["candlestick"]},
                group="field_mapping",
            ),
            "volume_field": FieldSchema(
                name="volume_field",
                type=FieldType.STRING,
                description="거래량 필드명 (선택)",
                placeholder="volume",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["candlestick"]},
                group="field_mapping",
            ),
            "columns": FieldSchema(
                name="columns",
                type=FieldType.ARRAY,
                description="표시할 컬럼 목록",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.MULTI_SELECT,
                depends_on={"chart_type": ["table"]},
            ),
            "signal_field": FieldSchema(
                name="signal_field",
                type=FieldType.STRING,
                description="시그널 필드명 (buy/sell 마커 표시)",
                placeholder="signal",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["line", "multi_line", "candlestick"]},
                group="field_mapping",
            ),
            "side_field": FieldSchema(
                name="side_field",
                type=FieldType.STRING,
                description="포지션 방향 필드명 (long/short 구분)",
                placeholder="side",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.TEXT_INPUT,
                depends_on={"chart_type": ["line", "multi_line", "candlestick"]},
                group="field_mapping",
            ),
        }
