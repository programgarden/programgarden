"""
ProgramGarden Core - Display Nodes

차트/테이블/요약 시각화 노드 (6개)
- TableDisplayNode: 테이블/그리드 표시
- LineChartNode: 단일 라인 차트
- MultiLineChartNode: 다중 시리즈 라인 차트
- CandlestickChartNode: OHLCV 캔들스틱 차트
- BarChartNode: 막대 차트
- SummaryDisplayNode: JSON/요약 데이터 표시
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


# ── OutputPort.fields 상수 (Display 노드용) ──

TABLE_DISPLAY_FIELDS: List[Dict[str, Any]] = [
    {"name": "columns", "type": "dynamic", "description": "표시할 컬럼 (설정에 따라 결정)"},
]

LINE_CHART_FIELDS: List[Dict[str, Any]] = [
    {"name": "x", "type": "dynamic", "description": "X축 값 (x_field로 지정)"},
    {"name": "y", "type": "dynamic", "description": "Y축 값 (y_field로 지정)"},
    {"name": "signal", "type": "string", "description": "매매 시그널 (buy/sell)", "nullable": True},
    {"name": "side", "type": "string", "description": "포지션 방향 (long/short)", "nullable": True},
]

MULTI_LINE_CHART_FIELDS: List[Dict[str, Any]] = [
    {"name": "x", "type": "dynamic", "description": "X축 값 (x_field로 지정)"},
    {"name": "y", "type": "dynamic", "description": "Y축 값 (y_field로 지정)"},
    {"name": "series_key", "type": "dynamic", "description": "시리즈 구분 키 (series_key로 지정)"},
    {"name": "signal", "type": "string", "description": "매매 시그널 (buy/sell)", "nullable": True},
    {"name": "side", "type": "string", "description": "포지션 방향 (long/short)", "nullable": True},
]

CANDLESTICK_CHART_FIELDS: List[Dict[str, Any]] = [
    {"name": "date", "type": "dynamic", "description": "날짜 (date_field로 지정)"},
    {"name": "open", "type": "number", "description": "시가 (open_field로 지정)"},
    {"name": "high", "type": "number", "description": "고가 (high_field로 지정)"},
    {"name": "low", "type": "number", "description": "저가 (low_field로 지정)"},
    {"name": "close", "type": "number", "description": "종가 (close_field로 지정)"},
    {"name": "volume", "type": "number", "description": "거래량 (volume_field로 지정)", "nullable": True},
    {"name": "signal", "type": "string", "description": "매매 시그널 (buy/sell)", "nullable": True},
    {"name": "side", "type": "string", "description": "포지션 방향 (long/short)", "nullable": True},
]

BAR_CHART_FIELDS: List[Dict[str, Any]] = [
    {"name": "x", "type": "dynamic", "description": "X축 값 (x_field로 지정)"},
    {"name": "y", "type": "dynamic", "description": "Y축 값 (y_field로 지정)"},
]

SUMMARY_DISPLAY_FIELDS: List[Dict[str, Any]] = [
    {"name": "data", "type": "any", "description": "요약 데이터 (JSON 객체 또는 원시값)"},
]


# ── 공통 data_schema 필드 ──

_SIGNAL_FIELD = {
    "type": "string",
    "resolved_by": "signal_field",
    "nullable": True,
    "enum": ["buy", "sell"],
    "description": "i18n:display_schema.common.signal",
}

_SIDE_FIELD = {
    "type": "string",
    "resolved_by": "side_field",
    "nullable": True,
    "enum": ["long", "short"],
    "description": "i18n:display_schema.common.side",
}


class BaseDisplayNode(BaseNode):
    """Display 노드 공통 베이스"""

    category: NodeCategory = NodeCategory.DISPLAY

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = None

    title: Optional[str] = Field(
        default=None,
        description="차트 제목",
    )

    data: Optional[str] = Field(
        default=None,
        description="데이터 바인딩 (예: {{ nodes.condition.values }})",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="data",
            type="any",
            description="i18n:ports.data",
            required=False,
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

    @classmethod
    def _common_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """공통 필드 스키마 (title, data)"""
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            "title": FieldSchema(
                name="title",
                type=FieldType.STRING,
                description="차트 제목",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "data": FieldSchema(
                name="data",
                type=FieldType.STRING,
                description="데이터 바인딩",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
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
        }


class TableDisplayNode(BaseDisplayNode):
    """테이블/그리드 형태로 데이터를 표시"""

    type: Literal["TableDisplayNode"] = "TableDisplayNode"
    description: str = "i18n:nodes.TableDisplayNode.description"

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=TABLE_DISPLAY_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.table.description",
        "items": {
            "type": "object",
            "properties": {
                "columns": {
                    "type": "dynamic",
                    "resolved_by": "columns",
                    "description": "i18n:display_schema.table.columns",
                },
            },
            "required": [],
        },
        "options_fields": ["columns", "limit", "sort_by", "sort_order"],
    }

    columns: Optional[List[str]] = Field(
        default=None,
        description="표시할 컬럼 목록 (미지정시 전체)",
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

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "columns": FieldSchema(
                name="columns",
                type=FieldType.ARRAY,
                description="표시할 컬럼 목록",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_options={"multiple": True},
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
            ),
            "sort_by": FieldSchema(
                name="sort_by",
                type=FieldType.STRING,
                description="정렬 기준 필드",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "sort_order": FieldSchema(
                name="sort_order",
                type=FieldType.ENUM,
                description="정렬 순서",
                enum_values=["asc", "desc"],
                default="desc",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        })
        return schema


class LineChartNode(BaseDisplayNode):
    """시계열 라인 차트"""

    type: Literal["LineChartNode"] = "LineChartNode"
    description: str = "i18n:nodes.LineChartNode.description"

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=LINE_CHART_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.line.description",
        "items": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "dynamic",
                    "resolved_by": "x_field",
                    "description": "i18n:display_schema.line.x",
                    "example": "date",
                },
                "y": {
                    "type": "dynamic",
                    "resolved_by": "y_field",
                    "description": "i18n:display_schema.line.y",
                    "example": "rsi",
                },
                "signal": _SIGNAL_FIELD,
                "side": _SIDE_FIELD,
            },
            "required": ["x", "y"],
        },
    }

    x_field: Optional[str] = Field(
        default=None,
        description="X축 필드명 (예: date)",
    )

    y_field: Optional[str] = Field(
        default=None,
        description="Y축 필드명 (예: rsi)",
    )

    signal_field: Optional[str] = Field(
        default=None,
        description="시그널 필드명 (buy/sell 마커 표시)",
    )

    side_field: Optional[str] = Field(
        default=None,
        description="포지션 방향 필드명 (long/short 구분)",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "x_field": FieldSchema(
                name="x_field",
                type=FieldType.STRING,
                description="X축 필드명",
                placeholder="date",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "y_field": FieldSchema(
                name="y_field",
                type=FieldType.STRING,
                description="Y축 필드명",
                placeholder="rsi",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "signal_field": FieldSchema(
                name="signal_field",
                type=FieldType.STRING,
                description="시그널 필드명 (buy/sell 마커 표시)",
                placeholder="signal",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "side_field": FieldSchema(
                name="side_field",
                type=FieldType.STRING,
                description="포지션 방향 필드명 (long/short 구분)",
                placeholder="side",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
        })
        return schema


class MultiLineChartNode(BaseDisplayNode):
    """다중 시리즈 라인 차트"""

    type: Literal["MultiLineChartNode"] = "MultiLineChartNode"
    description: str = "i18n:nodes.MultiLineChartNode.description"

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=MULTI_LINE_CHART_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.multi_line.description",
        "items": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "dynamic",
                    "resolved_by": "x_field",
                    "description": "i18n:display_schema.line.x",
                    "example": "date",
                },
                "y": {
                    "type": "dynamic",
                    "resolved_by": "y_field",
                    "description": "i18n:display_schema.line.y",
                    "example": "rsi",
                },
                "series_key": {
                    "type": "dynamic",
                    "resolved_by": "series_key",
                    "description": "i18n:display_schema.multi_line.series_key",
                    "example": "symbol",
                },
                "signal": _SIGNAL_FIELD,
                "side": _SIDE_FIELD,
            },
            "required": ["x", "y", "series_key"],
        },
        "options_fields": ["limit", "sort_by", "sort_order"],
    }

    x_field: Optional[str] = Field(
        default=None,
        description="X축 필드명 (예: date)",
    )

    y_field: Optional[str] = Field(
        default=None,
        description="Y축 필드명 (예: rsi)",
    )

    series_key: Optional[str] = Field(
        default=None,
        description="시리즈 구분 키 (예: symbol)",
    )

    signal_field: Optional[str] = Field(
        default=None,
        description="시그널 필드명 (buy/sell 마커 표시)",
    )

    side_field: Optional[str] = Field(
        default=None,
        description="포지션 방향 필드명 (long/short 구분)",
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

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "x_field": FieldSchema(
                name="x_field",
                type=FieldType.STRING,
                description="X축 필드명",
                placeholder="date",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "y_field": FieldSchema(
                name="y_field",
                type=FieldType.STRING,
                description="Y축 필드명",
                placeholder="rsi",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "series_key": FieldSchema(
                name="series_key",
                type=FieldType.STRING,
                description="시리즈 구분 키 (심볼별 라인)",
                placeholder="symbol",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "signal_field": FieldSchema(
                name="signal_field",
                type=FieldType.STRING,
                description="시그널 필드명 (buy/sell 마커 표시)",
                placeholder="signal",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "side_field": FieldSchema(
                name="side_field",
                type=FieldType.STRING,
                description="포지션 방향 필드명 (long/short 구분)",
                placeholder="side",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
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
            ),
            "sort_by": FieldSchema(
                name="sort_by",
                type=FieldType.STRING,
                description="정렬 기준 필드",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "sort_order": FieldSchema(
                name="sort_order",
                type=FieldType.ENUM,
                description="정렬 순서",
                enum_values=["asc", "desc"],
                default="desc",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        })
        return schema


class CandlestickChartNode(BaseDisplayNode):
    """OHLCV 캔들스틱 차트"""

    type: Literal["CandlestickChartNode"] = "CandlestickChartNode"
    description: str = "i18n:nodes.CandlestickChartNode.description"

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=CANDLESTICK_CHART_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.candlestick.description",
        "items": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "dynamic",
                    "resolved_by": "date_field",
                    "description": "i18n:display_schema.candlestick.date",
                    "example": "date",
                },
                "open": {
                    "type": "number",
                    "resolved_by": "open_field",
                    "description": "i18n:display_schema.candlestick.open",
                    "example": "open",
                },
                "high": {
                    "type": "number",
                    "resolved_by": "high_field",
                    "description": "i18n:display_schema.candlestick.high",
                    "example": "high",
                },
                "low": {
                    "type": "number",
                    "resolved_by": "low_field",
                    "description": "i18n:display_schema.candlestick.low",
                    "example": "low",
                },
                "close": {
                    "type": "number",
                    "resolved_by": "close_field",
                    "description": "i18n:display_schema.candlestick.close",
                    "example": "close",
                },
                "volume": {
                    "type": "number",
                    "resolved_by": "volume_field",
                    "nullable": True,
                    "description": "i18n:display_schema.candlestick.volume",
                    "example": "volume",
                },
                "signal": _SIGNAL_FIELD,
                "side": _SIDE_FIELD,
            },
            "required": ["date", "open", "high", "low", "close"],
        },
    }

    date_field: Optional[str] = Field(
        default=None,
        description="날짜 필드명",
    )

    open_field: Optional[str] = Field(
        default=None,
        description="시가 필드명",
    )

    high_field: Optional[str] = Field(
        default=None,
        description="고가 필드명",
    )

    low_field: Optional[str] = Field(
        default=None,
        description="저가 필드명",
    )

    close_field: Optional[str] = Field(
        default=None,
        description="종가 필드명",
    )

    volume_field: Optional[str] = Field(
        default=None,
        description="거래량 필드명 (선택)",
    )

    signal_field: Optional[str] = Field(
        default=None,
        description="시그널 필드명 (buy/sell 마커 표시)",
    )

    side_field: Optional[str] = Field(
        default=None,
        description="포지션 방향 필드명 (long/short 구분)",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "date_field": FieldSchema(
                name="date_field",
                type=FieldType.STRING,
                description="날짜 필드명",
                placeholder="date",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "open_field": FieldSchema(
                name="open_field",
                type=FieldType.STRING,
                description="시가 필드명",
                placeholder="open",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "high_field": FieldSchema(
                name="high_field",
                type=FieldType.STRING,
                description="고가 필드명",
                placeholder="high",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "low_field": FieldSchema(
                name="low_field",
                type=FieldType.STRING,
                description="저가 필드명",
                placeholder="low",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "close_field": FieldSchema(
                name="close_field",
                type=FieldType.STRING,
                description="종가 필드명",
                placeholder="close",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "volume_field": FieldSchema(
                name="volume_field",
                type=FieldType.STRING,
                description="거래량 필드명 (선택)",
                placeholder="volume",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "signal_field": FieldSchema(
                name="signal_field",
                type=FieldType.STRING,
                description="시그널 필드명 (buy/sell 마커 표시)",
                placeholder="signal",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "side_field": FieldSchema(
                name="side_field",
                type=FieldType.STRING,
                description="포지션 방향 필드명 (long/short 구분)",
                placeholder="side",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
        })
        return schema


class BarChartNode(BaseDisplayNode):
    """막대 차트"""

    type: Literal["BarChartNode"] = "BarChartNode"
    description: str = "i18n:nodes.BarChartNode.description"

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=BAR_CHART_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.bar.description",
        "items": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "dynamic",
                    "resolved_by": "x_field",
                    "description": "i18n:display_schema.line.x",
                    "example": "category",
                },
                "y": {
                    "type": "dynamic",
                    "resolved_by": "y_field",
                    "description": "i18n:display_schema.line.y",
                    "example": "value",
                },
            },
            "required": ["x", "y"],
        },
    }

    x_field: Optional[str] = Field(
        default=None,
        description="X축 필드명",
    )

    y_field: Optional[str] = Field(
        default=None,
        description="Y축 필드명",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "x_field": FieldSchema(
                name="x_field",
                type=FieldType.STRING,
                description="X축 필드명",
                placeholder="category",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "y_field": FieldSchema(
                name="y_field",
                type=FieldType.STRING,
                description="Y축 필드명",
                placeholder="value",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
        })
        return schema


class SummaryDisplayNode(BaseDisplayNode):
    """JSON/요약 데이터 표시"""

    type: Literal["SummaryDisplayNode"] = "SummaryDisplayNode"
    description: str = "i18n:nodes.SummaryDisplayNode.description"

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=SUMMARY_DISPLAY_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "any",
        "description": "i18n:display_schema.summary.description",
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return cls._common_field_schema()
