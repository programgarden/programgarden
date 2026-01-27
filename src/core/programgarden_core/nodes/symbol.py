"""
ProgramGarden Core - Symbol Nodes

Symbol source/filter nodes:
- WatchlistNode: User-defined watchlist
- MarketUniverseNode: Market universe (NASDAQ100, S&P500, etc.)
- ScreenerNode: Conditional symbol screening
- SymbolFilterNode: Symbol list filter/intersection/difference

SymbolQueryNode는 상품별 분리됨:
- symbol_stock.py → OverseasStockSymbolQueryNode
- symbol_futures.py → OverseasFuturesSymbolQueryNode
"""

from typing import Optional, List, Literal, Dict, Any, Union, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    SYMBOL_LIST_FIELDS,
)
from programgarden_core.models.exchange import SymbolEntry, ProductType


class WatchlistNode(BaseNode):
    """
    User-defined watchlist node

    Outputs a list of symbols with exchange information.
    Each symbol entry contains exchange name (NYSE, NASDAQ, CME, etc.) and symbol code.
    
    Note: This node only defines symbols. 
    Broker connection and product type are handled by downstream nodes (RealMarketDataNode, etc.)
    """

    type: Literal["WatchlistNode"] = "WatchlistNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.WatchlistNode.description"

    # Symbol entries: [{exchange: "NASDAQ", symbol: "AAPL"}, ...]
    symbols: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of symbol entries with exchange and symbol code",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS)
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 핵심 설정 ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="관심종목 목록입니다. 각 항목에 거래소(exchange)와 종목코드(symbol)를 입력하세요.",
                required=True,
                array_item_type=FieldType.OBJECT,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                ui_options={
                    "exchanges": [
                        {"value": "NASDAQ", "label": "NASDAQ"},
                        {"value": "NYSE", "label": "NYSE"},
                        {"value": "AMEX", "label": "AMEX"},
                        {"value": "CME", "label": "CME (시카고상업거래소)"},
                        {"value": "EUREX", "label": "EUREX (유럽선물거래소)"},
                        {"value": "SGX", "label": "SGX (싱가포르거래소)"},
                        {"value": "HKEX", "label": "HKEX (홍콩거래소)"},
                    ],
                },
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "TSLA"}],
                example_binding="{{ nodes.universe.symbols }}",
                bindable_sources=["MarketUniverseNode.symbols", "ScreenerNode.symbols"],
                expected_type="list[dict]",
            ),
        }


class MarketUniverseNode(BaseNode):
    """
    대표지수 종목 노드 (Market Universe Node)
    
    ⚠️ 해외주식(overseas_stock) 전용 노드입니다. 해외선물은 지원하지 않습니다.
    
    S&P500, NASDAQ100 등 미국 대표 지수의 구성 종목을 자동으로 가져옵니다.
    pytickersymbols 라이브러리를 활용하여 최신 인덱스 구성종목을 조회합니다.
    Broker 연결 없이 독립적으로 실행됩니다.
    
    지원 인덱스 (LS증권 거래 가능):
    - NASDAQ100: 나스닥 100 (~101개)
    - SP500: S&P 500 (~503개)
    - SP100: S&P 100
    - DOW30: 다우존스 30
    """

    type: Literal["MarketUniverseNode"] = "MarketUniverseNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.MarketUniverseNode.description"

    # 인덱스 선택
    universe: str = Field(
        default="NASDAQ100",
        description="대표 지수 선택 (NASDAQ100, SP500, DOW30 등). 해외주식 전용.",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="종목 수"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "universe": FieldSchema(
                name="universe",
                type=FieldType.ENUM,
                description="i18n:fields.MarketUniverseNode.universe",
                default="NASDAQ100",
                required=True,
                enum_values=["NASDAQ100", "SP500", "SP100", "DOW30"],
                enum_labels={"NASDAQ100": "나스닥 100", "SP500": "S&P 500", "SP100": "S&P 100", "DOW30": "다우존스 30"},
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="NASDAQ100",
                expected_type="str",
            ),
        }


class ScreenerNode(BaseNode):
    """
    조건으로 종목찾기 노드 (Screener Node)
    
    시가총액, 거래량, 섹터 등 조건을 설정하면
    해당 조건을 만족하는 종목만 골라냅니다.
    Yahoo Finance API를 활용합니다.
    """

    type: Literal["ScreenerNode"] = "ScreenerNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.ScreenerNode.description"

    # 입력 종목 리스트 (선택사항) - 바인딩 또는 직접 입력
    symbols: Optional[Union[List[Dict[str, str]], str]] = Field(
        default=None,
        description="필터링할 종목 리스트. 없으면 전체 시장에서 검색",
    )
    
    # 스크리닝 조건
    market_cap_min: Optional[float] = Field(
        default=None,
        description="최소 시가총액 (달러). 예: 10000000000 = 100억 달러",
    )
    market_cap_max: Optional[float] = Field(
        default=None,
        description="최대 시가총액 (달러)",
    )
    volume_min: Optional[int] = Field(
        default=None,
        description="최소 평균 거래량 (주). 예: 1000000 = 100만주",
    )
    sector: Optional[str] = Field(
        default=None,
        description="섹터 필터 (Technology, Healthcare, Finance 등)",
    )
    exchange: Optional[str] = Field(
        default=None,
        description="거래소 필터 (NASDAQ, NYSE, AMEX)",
    )
    max_results: int = Field(
        default=100, 
        description="최대 결과 수"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="symbols",
            type="symbol_list",
            description="필터링할 종목 리스트 (선택사항). 없으면 전체 시장에서 검색",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="결과 종목 수"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 입력 종목 리스트 (선택사항) ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="필터링할 종목 리스트입니다. 비워두면 전체 시장에서 검색합니다. 다른 노드의 symbols 출력을 연결하면 해당 종목들만 필터링합니다.",
                required=False,
                array_item_type=FieldType.OBJECT,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                ui_options={
                    "exchanges": [
                        {"value": "NASDAQ", "label": "NASDAQ"},
                        {"value": "NYSE", "label": "NYSE"},
                        {"value": "AMEX", "label": "AMEX"},
                        {"value": "CME", "label": "CME (시카고상업거래소)"},
                        {"value": "EUREX", "label": "EUREX (유럽선물거래소)"},
                        {"value": "SGX", "label": "SGX (싱가포르거래소)"},
                        {"value": "HKEX", "label": "HKEX (홍콩거래소)"},
                    ],
                },
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=["WatchlistNode.symbols", "MarketUniverseNode.symbols", "SymbolQueryNode.symbols"],
                expected_type="list[dict]",
            ),
            # === PARAMETERS: 시가총액 필터 ===
            "market_cap_min": FieldSchema(
                name="market_cap_min",
                type=FieldType.NUMBER,
                description="최소 시가총액을 입력하세요 (달러 단위). 예: 100억 달러 = 10000000000. 유동성 낮은 소형주를 제외하려면 설정하세요.",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=10000000000,
                placeholder="예: 10000000000 (100억 달러)",
                expected_type="float",
            ),
            "market_cap_max": FieldSchema(
                name="market_cap_max",
                type=FieldType.NUMBER,
                description="최대 시가총액을 입력하세요. 중소형주만 찾으려면 설정하세요.",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=50000000000,
                expected_type="float",
            ),
            # === PARAMETERS: 거래량 필터 ===
            "volume_min": FieldSchema(
                name="volume_min",
                type=FieldType.INTEGER,
                description="최소 평균 거래량 (주 단위). 예: 100만주 = 1000000. 거래량이 적은 종목은 주문 체결이 어려울 수 있습니다.",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=1000000,
                placeholder="예: 1000000 (100만주)",
                expected_type="int",
            ),
            # === PARAMETERS: 섹터/거래소 필터 ===
            "sector": FieldSchema(
                name="sector",
                type=FieldType.ENUM,
                description="특정 섹터만 찾으려면 선택하세요. 비워두면 전체 섹터.",
                required=False,
                enum_values=["", "Technology", "Healthcare", "Financial Services", "Consumer Cyclical", "Communication Services", "Industrials", "Consumer Defensive", "Energy", "Utilities", "Real Estate", "Basic Materials"],
                enum_labels={"": "전체", "Technology": "기술", "Healthcare": "헬스케어", "Financial Services": "금융", "Consumer Cyclical": "경기소비재", "Communication Services": "커뮤니케이션", "Industrials": "산업재", "Consumer Defensive": "필수소비재", "Energy": "에너지", "Utilities": "유틸리티", "Real Estate": "부동산", "Basic Materials": "소재"},
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="Technology",
                expected_type="str",
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.ENUM,
                description="특정 거래소 종목만 찾으려면 선택하세요. 비워두면 전체 거래소.",
                required=False,
                enum_values=["", "NASDAQ", "NYSE", "AMEX"],
                enum_labels={"": "전체", "NASDAQ": "나스닥", "NYSE": "뉴욕증권거래소", "AMEX": "아멕스"},
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="NASDAQ",
                expected_type="str",
            ),
            # === SETTINGS: 결과 제한 ===
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 몇 개 종목을 가져올지 설정하세요. 시가총액 큰 순으로 정렬됩니다.",
                default=100,
                min_value=1,
                max_value=500,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=100,
                expected_type="int",
            ),
        }


class SymbolFilterNode(BaseNode):
    """
    종목 비교/필터 노드 (Symbol Filter Node)
    
    두 종목 리스트를 비교하여 교집합, 합집합, 차집합을 계산합니다.
    
    사용 예시:
    - 관심종목 - 보유종목 = 신규 매수 대상 (중복 매수 방지)
    - RSI과매도 ∩ MACD골든크로스 = 강력 매수 신호
    """

    type: Literal["SymbolFilterNode"] = "SymbolFilterNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.SymbolFilterNode.description"

    # 집합 연산 종류
    operation: Literal["difference", "intersection", "union"] = Field(
        default="difference",
        description="집합 연산 종류",
    )
    
    # input_a, input_b는 바인딩으로 받음
    input_a: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="첫 번째 종목 리스트 (필수)",
    )
    input_b: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="두 번째 종목 리스트 (선택)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="input_a",
            type="symbol_list",
            description="첫 번째 종목 리스트 (예: 관심종목)",
            required=True,
        ),
        InputPort(
            name="input_b",
            type="symbol_list",
            description="두 번째 종목 리스트 (예: 보유종목)",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="결과 종목 수"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "operation": FieldSchema(
                name="operation",
                type=FieldType.ENUM,
                description="어떤 비교를 할지 선택하세요.",
                default="difference",
                required=True,
                enum_values=["difference", "intersection", "union"],
                enum_labels={"difference": "차집합 (A-B, 중복 매수 방지)", "intersection": "교집합 (A∩B)", "union": "합집합 (A∪B)"},
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="difference",
                expected_type="str",
            ),
            "input_a": FieldSchema(
                name="input_a",
                type=FieldType.ARRAY,
                description="첫 번째 종목 리스트입니다. WatchlistNode나 다른 노드의 symbols 출력을 연결하세요.",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=["WatchlistNode.symbols", "MarketUniverseNode.symbols", "ScreenerNode.symbols", "AccountNode.held_symbols"],
                expected_type="list[dict]",
            ),
            "input_b": FieldSchema(
                name="input_b",
                type=FieldType.ARRAY,
                description="두 번째 종목 리스트입니다. 비교할 대상을 연결하세요. 예: 보유종목(AccountNode.held_symbols)",
                required=False,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.account.held_symbols }}",
                bindable_sources=["WatchlistNode.symbols", "AccountNode.held_symbols", "ConditionNode.passed_symbols"],
                expected_type="list[dict]",
            ),
        }