"""
ProgramGarden Core - Symbol Nodes

Symbol source/filter nodes:
- WatchlistNode: User-defined watchlist
- MarketUniverseNode: Market universe (NASDAQ100, S&P500, etc.)
- ScreenerNode: Conditional symbol screening
- SymbolFilterNode: Symbol list filter/intersection/difference
- SymbolQueryNode: 전체종목조회 - All tradable symbols from broker API (g3190 for stock, o3101 for futures)
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
)
from programgarden_core.models.exchange import SymbolEntry, ProductType


class SymbolQueryNode(BaseNode):
    """
    전체종목조회 노드 (Symbol Query Node)

    Queries all tradable symbols from broker API.
    - overseas_stock: Uses g3190 API (마스터상장종목조회)
    - overseas_futures: Uses o3101 API (해외선물마스터조회)
    
    Returns a list of all symbols available for trading on the selected exchange.
    """

    type: Literal["SymbolQueryNode"] = "SymbolQueryNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.SymbolQueryNode.description"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

    # 상품 유형 선택 (해외주식/해외선물)
    product_type: str = Field(
        default="overseas_stock",
        description="Product type: overseas_stock or overseas_futures",
    )

    # 거래소 선택 (해외주식)
    stock_exchange: Optional[str] = Field(
        default=None,
        description="Exchange for overseas_stock: NYSE(81), NASDAQ(82), AMEX(83), etc.",
    )
    
    # 국가 선택 (해외주식) - g3190 natcode
    country: str = Field(
        default="US",
        description="Country code for overseas_stock (US, HK, JP, CN, etc.)",
    )
    
    # 거래소 구분 (해외선물) - o3101 gubun
    futures_exchange: Optional[str] = Field(
        default=None,
        description="Exchange for overseas_futures: 1(all), 2(CME), 3(SGX), etc.",
    )
    
    # 월물 필터 (해외선물)
    futures_contract_month: Optional[str] = Field(
        default=None,
        description="Contract month filter for overseas_futures: F, 2026F, front, next",
    )
    
    # 최대 조회 건수
    max_results: int = Field(
        default=500,
        description="Maximum number of symbols to retrieve per request",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
            required=True,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols"),
        OutputPort(name="count", type="integer", description="Total symbol count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                description="증권사 연결 정보입니다. BrokerNode를 먼저 추가하고, 그 노드의 connection 출력을 연결하세요.",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
                ui_component=UIComponent.BINDING_INPUT,
            ),
            # === PARAMETERS: 상품 유형 선택 ===
            "product_type": FieldSchema(
                name="product_type",
                type=FieldType.ENUM,
                description="상품 유형을 선택하세요. 해외주식 또는 해외선물.",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={"overseas_stock": "해외주식", "overseas_futures": "해외선물"},
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="overseas_stock",
                expected_type="str",
                ui_component=UIComponent.SELECT,
            ),
            # === PARAMETERS: 해외주식 설정 (overseas_stock 선택시만 표시) ===
            "country": FieldSchema(
                name="country",
                type=FieldType.ENUM,
                description="국가 코드. US: 미국, HK: 홍콩, JP: 일본, CN: 중국",
                default="US",
                enum_values=["US", "HK", "JP", "CN", "VN", "ID"],
                enum_labels={"US": "미국", "HK": "홍콩", "JP": "일본", "CN": "중국", "VN": "베트남", "ID": "인도네시아"},
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="US",
                expected_type="str",
                visible_when={"product_type": "overseas_stock"},
                ui_component=UIComponent.SELECT,
            ),
            "stock_exchange": FieldSchema(
                name="stock_exchange",
                type=FieldType.ENUM,
                description="거래소 구분. NYSE/AMEX: 81, NASDAQ: 82, 전체: 빈값",
                enum_values=["", "81", "82"],
                enum_labels={"": "전체", "81": "NYSE/AMEX", "82": "NASDAQ"},
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="82",
                expected_type="str",
                visible_when={"product_type": "overseas_stock"},
                ui_component=UIComponent.SELECT,
            ),
            # === PARAMETERS: 해외선물 설정 (overseas_futures 선택시만 표시) ===
            "futures_exchange": FieldSchema(
                name="futures_exchange",
                type=FieldType.ENUM,
                description="거래소 구분. 1: 전체, 2: CME, 3: SGX, 4: EUREX, 5: ICE, 6: HKEX, 7: OSE",
                enum_values=["1", "2", "3", "4", "5", "6", "7"],
                enum_labels={"1": "전체", "2": "CME", "3": "SGX", "4": "EUREX", "5": "ICE", "6": "HKEX", "7": "OSE"},
                default="1",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="1",
                expected_type="str",
                visible_when={"product_type": "overseas_futures"},
                ui_component=UIComponent.SELECT,
            ),
            "futures_contract_month": FieldSchema(
                name="futures_contract_month",
                type=FieldType.STRING,
                description="월물 필터. 예: 'F' (1월), '2026F' (2026년 1월), 'front' (근월물), 'next' (차월물). 월물코드: F=1월, G=2월, H=3월, J=4월, K=5월, M=6월, N=7월, Q=8월, U=9월, V=10월, X=11월, Z=12월",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="front",
                expected_type="str",
                placeholder="front, next, F, 2026F",
                visible_when={"product_type": "overseas_futures"},
                ui_component=UIComponent.TEXT_INPUT,
            ),
            # === SETTINGS: 부가 설정 ===
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 조회 건수. 연속 조회로 전체 데이터를 가져옵니다.",
                default=500,
                min_value=100,
                max_value=10000,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=500,
                expected_type="int",
                ui_component=UIComponent.NUMBER_INPUT,
            ),
        }


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
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols")
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
        return {
            # === PARAMETERS: 핵심 설정 ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="관심종목 목록입니다. 각 항목에 거래소(exchange)와 종목코드(symbol)를 입력하세요.",
                required=True,
                array_item_type=FieldType.OBJECT,
                bindable=False,
                expression_enabled=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SYMBOL_EDITOR,
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "TSLA"}],
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
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols"),
        OutputPort(name="count", type="integer", description="종목 수"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
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
                bindable=False,
                example="NASDAQ100",
                expected_type="str",
                ui_component=UIComponent.SELECT,
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
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols"),
        OutputPort(name="count", type="integer", description="결과 종목 수"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
        return {
            "market_cap_min": FieldSchema(
                name="market_cap_min",
                type=FieldType.NUMBER,
                description="최소 시가총액을 입력하세요 (달러 단위). 예: 100억 달러 = 10000000000. 유동성 낮은 소형주를 제외하려면 설정하세요.",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example=10000000000,
                placeholder="예: 10000000000 (100억 달러)",
                expected_type="float",
                ui_component=UIComponent.NUMBER_INPUT,
            ),
            "market_cap_max": FieldSchema(
                name="market_cap_max",
                type=FieldType.NUMBER,
                description="최대 시가총액을 입력하세요. 중소형주만 찾으려면 설정하세요.",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example=50000000000,
                expected_type="float",
                ui_component=UIComponent.NUMBER_INPUT,
            ),
            "volume_min": FieldSchema(
                name="volume_min",
                type=FieldType.INTEGER,
                description="최소 평균 거래량 (주 단위). 예: 100만주 = 1000000. 거래량이 적은 종목은 주문 체결이 어려울 수 있습니다.",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example=1000000,
                placeholder="예: 1000000 (100만주)",
                expected_type="int",
                ui_component=UIComponent.NUMBER_INPUT,
            ),
            "sector": FieldSchema(
                name="sector",
                type=FieldType.ENUM,
                description="특정 섹터만 찾으려면 선택하세요. 비워두면 전체 섹터.",
                required=False,
                enum_values=["", "Technology", "Healthcare", "Financial Services", "Consumer Cyclical", "Communication Services", "Industrials", "Consumer Defensive", "Energy", "Utilities", "Real Estate", "Basic Materials"],
                enum_labels={"": "전체", "Technology": "기술", "Healthcare": "헬스케어", "Financial Services": "금융", "Consumer Cyclical": "경기소비재", "Communication Services": "커뮤니케이션", "Industrials": "산업재", "Consumer Defensive": "필수소비재", "Energy": "에너지", "Utilities": "유틸리티", "Real Estate": "부동산", "Basic Materials": "소재"},
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="Technology",
                expected_type="str",
                ui_component=UIComponent.SELECT,
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.ENUM,
                description="특정 거래소 종목만 찾으려면 선택하세요. 비워두면 전체 거래소.",
                required=False,
                enum_values=["", "NASDAQ", "NYSE", "AMEX"],
                enum_labels={"": "전체", "NASDAQ": "나스닥", "NYSE": "뉴욕증권거래소", "AMEX": "아멕스"},
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="NASDAQ",
                expected_type="str",
                ui_component=UIComponent.SELECT,
            ),
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 몇 개 종목을 가져올지 설정하세요. 시가총액 큰 순으로 정렬됩니다.",
                default=100,
                min_value=1,
                max_value=500,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=100,
                expected_type="int",
                ui_component=UIComponent.NUMBER_INPUT,
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
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols"),
        OutputPort(name="count", type="integer", description="결과 종목 수"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
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
                bindable=False,
                example="difference",
                expected_type="str",
                ui_component=UIComponent.SELECT,
            ),
            "input_a": FieldSchema(
                name="input_a",
                type=FieldType.ARRAY,
                description="첫 번째 종목 리스트입니다. WatchlistNode나 다른 노드의 symbols 출력을 연결하세요.",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=["WatchlistNode.symbols", "MarketUniverseNode.symbols", "ScreenerNode.symbols", "AccountNode.held_symbols"],
                expected_type="list[dict]",
                ui_component=UIComponent.BINDING_INPUT,
            ),
            "input_b": FieldSchema(
                name="input_b",
                type=FieldType.ARRAY,
                description="두 번째 종목 리스트입니다. 비교할 대상을 연결하세요. 예: 보유종목(AccountNode.held_symbols)",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.account.held_symbols }}",
                bindable_sources=["WatchlistNode.symbols", "AccountNode.held_symbols", "ConditionNode.passed_symbols"],
                expected_type="list[dict]",
                ui_component=UIComponent.BINDING_INPUT,
            ),
        }