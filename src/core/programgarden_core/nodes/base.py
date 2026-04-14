"""
ProgramGarden Core - 노드 베이스 클래스

모든 노드의 기반이 되는 BaseNode와 공통 타입 정의
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Literal, ClassVar, Set
from pydantic import BaseModel, ConfigDict, Field

from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
from programgarden_core.models.resilience import (
    ResilienceConfig,
    RetryableError,
    FallbackMode,
)
from programgarden_core.models.connection_rule import ConnectionRule, RateLimitConfig


class ProductScope(str, Enum):
    """노드가 지원하는 상품 범위"""
    STOCK = "overseas_stock"        # 해외주식 전용
    FUTURES = "overseas_futures"    # 해외선물 전용
    KOREA_STOCK = "korea_stock"    # 국내주식 전용
    ALL = "all"                     # 상품 무관 (범용)


class BrokerProvider(str, Enum):
    """지원 증권사"""
    LS = "ls-sec.co.kr"             # LS증권
    ALL = "all"                     # 증권사 무관 (범용)


class NodeCategory(str, Enum):
    """
    노드 카테고리 (11개 - 금융 도메인 기준)

    투자자가 직관적으로 이해할 수 있는 금융 용어 기반 분류
    """

    # 인프라: 워크플로우 시작점, 브로커 연결
    INFRA = "infra"

    # 계좌: 잔고, 포지션, 체결 내역 (실시간/REST)
    ACCOUNT = "account"

    # 시장: 시세, 종목 목록, 과거 데이터
    MARKET = "market"

    # 조건: 매매 조건 판단 (기술적 분석, 로직 조합)
    CONDITION = "condition"

    # 주문: 신규/정정/취소 주문, 포지션 사이징
    ORDER = "order"

    # 리스크: 리스크 관리, 포트폴리오 배분
    RISK = "risk"

    # 스케줄: 시간 기반 트리거, 거래시간 필터
    SCHEDULE = "schedule"

    # 데이터: 외부 DB/API 연동 (SQLite, Postgres, HTTP)
    DATA = "data"

    # 분석: 백테스트, 성과 계산
    ANALYSIS = "analysis"

    # 디스플레이: 차트, 테이블, 요약 시각화
    DISPLAY = "display"

    # 시스템: Job 제어, 서브플로우
    SYSTEM = "system"

    # 메시징: 텔레그램, 슬랙, 디스코드 등 알림
    MESSAGING = "messaging"

    # AI: AI 에이전트, LLM 모델 연결
    AI = "ai"


class Position(BaseModel):
    """클라이언트 UI용 노드 위치"""

    x: float = 0.0
    y: float = 0.0


class InputPort(BaseModel):
    """입력 포트 정의"""

    name: str
    type: str
    display_name: Optional[str] = None  # 사용자 표시용 이름 (i18n 키 또는 직접 값)
    description: Optional[str] = None
    required: bool = True
    multiple: bool = False  # 여러 엣지 연결 가능 여부
    min_connections: Optional[int] = None  # 최소 연결 수


class OutputPort(BaseModel):
    """출력 포트 정의"""

    name: str
    type: str
    display_name: Optional[str] = None  # 사용자 표시용 이름 (i18n 키 또는 직접 값)
    description: Optional[str] = None
    fields: Optional[List[Dict[str, Any]]] = None  # 구조화된 서브필드 정의
    # 출력 값의 shape 예시 — LLM 이 `nodes.X.{port}` 표현식 작성 시
    # 어떤 키/타입이 나오는지 즉시 파악하도록 노출. fields 만으로는 중첩
    # 구조나 array 여부를 시각화하기 어려운 한계 보완.
    example: Optional[Any] = None


# === OutputPort.fields 공통 상수 ===
SYMBOL_LIST_FIELDS: List[Dict[str, str]] = [
    {"name": "exchange", "type": "string", "description": "거래소 코드 (NASDAQ, NYSE, CME 등)"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
]

# ── 해외주식 REST AccountNode 전용 ──
OVERSEAS_STOCK_BALANCE_FIELDS: List[Dict[str, str]] = [
    {"name": "total_pnl_rate", "type": "number", "description": "수익률 (%)"},
    {"name": "cash_krw", "type": "number", "description": "원화예수금"},
    {"name": "stock_eval_krw", "type": "number", "description": "주식환산평가금액"},
    {"name": "total_eval_krw", "type": "number", "description": "원화평가합계"},
    {"name": "total_pnl_krw", "type": "number", "description": "환산평가손익"},
    {"name": "orderable_amount", "type": "number", "description": "외화주문가능금액 (USD)"},
    {"name": "foreign_cash", "type": "number", "description": "외화예수금 (USD)"},
    {"name": "exchange_rate", "type": "number", "description": "기준환율"},
]

# ── 해외선물 REST AccountNode 전용 ──
OVERSEAS_FUTURES_BALANCE_FIELDS: List[Dict[str, str]] = [
    {"name": "deposit", "type": "number", "description": "예수금"},
    {"name": "orderable_amount", "type": "number", "description": "주문가능금액"},
    {"name": "total_orderable", "type": "number", "description": "전체 주문가능금액 합산"},
    {"name": "margin", "type": "number", "description": "위탁증거금"},
    {"name": "maintenance_margin", "type": "number", "description": "유지증거금"},
    {"name": "margin_call_rate", "type": "number", "description": "마진콜율 (%)"},
    {"name": "total_eval", "type": "number", "description": "평가예탁총금액"},
    {"name": "settlement_pnl", "type": "number", "description": "청산손익"},
]

# ── 해외주식 RealAccountNode 전용 ──
OVERSEAS_STOCK_REAL_BALANCE_FIELDS: List[Dict[str, str]] = [
    {"name": "total", "type": "number", "description": "총 예수금"},
    {"name": "available", "type": "number", "description": "매수 가능 금액"},
    {"name": "currency", "type": "string", "description": "통화 코드 (USD 등)"},
]

# ── 해외선물 RealAccountNode 전용 ──
OVERSEAS_FUTURES_REAL_BALANCE_FIELDS: List[Dict[str, str]] = [
    {"name": "total", "type": "number", "description": "총 예수금"},
    {"name": "available", "type": "number", "description": "매수 가능 금액"},
    {"name": "currency", "type": "string", "description": "통화 코드 (USD 등)"},
]

# ── 국내주식 REST AccountNode 전용 ──
KOREA_STOCK_BALANCE_FIELDS: List[Dict[str, str]] = [
    {"name": "cash", "type": "number", "description": "예수금"},
    {"name": "total_eval", "type": "number", "description": "총평가금액"},
    {"name": "stock_eval", "type": "number", "description": "주식평가금액"},
    {"name": "total_pnl", "type": "number", "description": "평가손익합계"},
    {"name": "total_pnl_rate", "type": "number", "description": "수익률 (%)"},
    {"name": "orderable_amount", "type": "number", "description": "주문가능금액"},
]

# ── 국내주식 RealAccountNode 전용 ──
KOREA_STOCK_REAL_BALANCE_FIELDS: List[Dict[str, str]] = [
    {"name": "total", "type": "number", "description": "총 예수금"},
    {"name": "available", "type": "number", "description": "매수 가능 금액"},
]

# ── 국내주식 시세 전용 (t1102 기반) ──
KOREA_STOCK_PRICE_DATA_FIELDS: List[Dict[str, str]] = [
    {"name": "symbol", "type": "string", "description": "종목코드 (6자리)"},
    {"name": "name", "type": "string", "description": "종목명"},
    {"name": "current_price", "type": "number", "description": "현재가"},
    {"name": "volume", "type": "number", "description": "거래량"},
    {"name": "change_percent", "type": "number", "description": "등락률 (%)"},
    {"name": "open_price", "type": "number", "description": "시가"},
    {"name": "high_price", "type": "number", "description": "고가"},
    {"name": "low_price", "type": "number", "description": "저가"},
    {"name": "market_cap", "type": "number", "description": "시가총액 (억원)"},
]

# ── 국내주식 펀더멘털 전용 ──
KOREA_STOCK_FUNDAMENTAL_FIELDS: List[Dict[str, str]] = [
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "name", "type": "string", "description": "종목명"},
    {"name": "current_price", "type": "number", "description": "현재가"},
    {"name": "volume", "type": "number", "description": "거래량"},
    {"name": "change_percent", "type": "number", "description": "등락률 (%)"},
    {"name": "per", "type": "number", "description": "PER"},
    {"name": "eps", "type": "number", "description": "EPS"},
    {"name": "pbr", "type": "number", "description": "PBR"},
    {"name": "market_cap", "type": "number", "description": "시가총액 (억원)"},
    {"name": "shares_outstanding", "type": "number", "description": "상장주식수"},
    {"name": "high_52w", "type": "number", "description": "52주 최고가"},
    {"name": "low_52w", "type": "number", "description": "52주 최저가"},
    {"name": "industry", "type": "string", "description": "업종명"},
]

POSITION_FIELDS: List[Dict[str, str]] = [
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "quantity", "type": "number", "description": "보유 수량"},
    {"name": "avg_price", "type": "number", "description": "평균 매입가"},
    {"name": "current_price", "type": "number", "description": "현재가"},
    {"name": "pnl", "type": "number", "description": "평가 손익"},
    {"name": "pnl_percent", "type": "number", "description": "수익률 (%)"},
]

ORDER_RESULT_FIELDS: List[Dict[str, str]] = [
    {"name": "order_id", "type": "string", "description": "주문번호"},
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "side", "type": "string", "description": "매매구분 (buy/sell)"},
    {"name": "quantity", "type": "number", "description": "주문수량"},
    {"name": "price", "type": "number", "description": "주문가격"},
    {"name": "status", "type": "string", "description": "주문 상태"},
]

PRICE_DATA_FIELDS: List[Dict[str, str]] = [
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "current_price", "type": "number", "description": "현재가"},
    {"name": "volume", "type": "number", "description": "거래량"},
    {"name": "change_percent", "type": "number", "description": "등락률 (%)"},
    {"name": "per", "type": "number", "description": "PER (주가수익비율)"},
    {"name": "eps", "type": "number", "description": "EPS (주당순이익)"},
]

FUNDAMENTAL_DATA_FIELDS: List[Dict[str, str]] = [
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "name", "type": "string", "description": "영문 종목명"},
    {"name": "industry", "type": "string", "description": "업종명"},
    {"name": "nation", "type": "string", "description": "국가명"},
    {"name": "exchange_name", "type": "string", "description": "거래소명"},
    {"name": "current_price", "type": "number", "description": "현재가"},
    {"name": "volume", "type": "number", "description": "거래량"},
    {"name": "change_percent", "type": "number", "description": "등락률 (%)"},
    {"name": "per", "type": "number", "description": "PER (주가수익비율)"},
    {"name": "eps", "type": "number", "description": "EPS (주당순이익)"},
    {"name": "market_cap", "type": "number", "description": "시가총액"},
    {"name": "shares_outstanding", "type": "number", "description": "발행주식수"},
    {"name": "high_52w", "type": "number", "description": "52주 최고가"},
    {"name": "low_52w", "type": "number", "description": "52주 최저가"},
    {"name": "exchange_rate", "type": "number", "description": "환율"},
]

HISTORICAL_DATA_FIELDS: List[Dict[str, str]] = [
    {"name": "date", "type": "string", "description": "날짜 (YYYYMMDD)"},
    {"name": "open", "type": "number", "description": "시가"},
    {"name": "high", "type": "number", "description": "고가"},
    {"name": "low", "type": "number", "description": "저가"},
    {"name": "close", "type": "number", "description": "종가"},
    {"name": "volume", "type": "number", "description": "거래량"},
]

ORDER_LIST_FIELDS: List[Dict[str, str]] = [
    {"name": "order_id", "type": "string", "description": "주문번호"},
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "side", "type": "string", "description": "매매구분 (buy/sell)"},
    {"name": "order_type", "type": "string", "description": "주문유형 (market/limit)"},
    {"name": "quantity", "type": "number", "description": "주문수량"},
    {"name": "price", "type": "number", "description": "주문가격"},
    {"name": "status", "type": "string", "description": "주문 상태"},
]

OPEN_ORDER_FIELDS: List[Dict[str, str]] = [
    {"name": "order_id", "type": "string", "description": "주문번호"},
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "name", "type": "string", "description": "종목명"},
    {"name": "side", "type": "string", "description": "매매구분 (buy/sell)"},
    {"name": "order_type", "type": "string", "description": "주문유형 (market/limit)"},
    {"name": "quantity", "type": "number", "description": "주문수량"},
    {"name": "filled_quantity", "type": "number", "description": "체결수량"},
    {"name": "remaining_quantity", "type": "number", "description": "미체결수량"},
    {"name": "price", "type": "number", "description": "주문가격"},
    {"name": "order_time", "type": "string", "description": "주문시각"},
]

ORDER_EVENT_FIELDS: List[Dict[str, str]] = [
    {"name": "order_id", "type": "string", "description": "주문번호"},
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "side", "type": "string", "description": "매매구분"},
    {"name": "quantity", "type": "number", "description": "주문수량"},
    {"name": "filled_quantity", "type": "number", "description": "체결수량"},
    {"name": "price", "type": "number", "description": "주문가격"},
    {"name": "filled_price", "type": "number", "description": "체결가격"},
    {"name": "event_type", "type": "string", "description": "이벤트 유형"},
    {"name": "timestamp", "type": "string", "description": "이벤트 시각"},
]

OHLCV_DATA_FIELDS: List[Dict[str, str]] = [
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "open", "type": "number", "description": "시가"},
    {"name": "high", "type": "number", "description": "고가"},
    {"name": "low", "type": "number", "description": "저가"},
    {"name": "close", "type": "number", "description": "종가"},
    {"name": "volume", "type": "number", "description": "거래량"},
    {"name": "timestamp", "type": "string", "description": "캔들 시각"},
]

MARKET_DATA_FULL_FIELDS: List[Dict[str, str]] = [
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "current_price", "type": "number", "description": "현재가"},
    {"name": "bid_price", "type": "number", "description": "매수호가 (해외주식 실시간에서는 미제공)"},
    {"name": "ask_price", "type": "number", "description": "매도호가 (해외주식 실시간에서는 미제공)"},
    {"name": "volume", "type": "number", "description": "거래량"},
    {"name": "change_percent", "type": "number", "description": "등락률 (%)"},
    {"name": "timestamp", "type": "string", "description": "시세 시각"},
]

CONDITION_RESULT_FIELDS: List[Dict[str, str]] = [
    {"name": "passed", "type": "boolean", "description": "조건 충족 여부"},
    {"name": "value", "type": "number", "description": "계산된 지표 값"},
    {"name": "threshold", "type": "number", "description": "비교 기준값"},
    {"name": "direction", "type": "string", "description": "비교 방향 (above/below/cross)"},
]

EQUITY_CURVE_FIELDS: List[Dict[str, str]] = [
    {"name": "date", "type": "string", "description": "날짜"},
    {"name": "equity", "type": "number", "description": "자산 가치"},
    {"name": "drawdown", "type": "number", "description": "낙폭 (%)"},
    {"name": "returns", "type": "number", "description": "수익률"},
]

TRADE_FIELDS: List[Dict[str, str]] = [
    {"name": "date", "type": "string", "description": "거래일"},
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "side", "type": "string", "description": "매매구분"},
    {"name": "quantity", "type": "number", "description": "수량"},
    {"name": "price", "type": "number", "description": "가격"},
    {"name": "pnl", "type": "number", "description": "손익"},
]

PERFORMANCE_METRICS_FIELDS: List[Dict[str, str]] = [
    {"name": "total_return", "type": "number", "description": "총 수익률 (%)"},
    {"name": "annualized_return", "type": "number", "description": "연환산 수익률 (%)"},
    {"name": "max_drawdown", "type": "number", "description": "최대 낙폭 (%)"},
    {"name": "sharpe_ratio", "type": "number", "description": "샤프 비율"},
    {"name": "win_rate", "type": "number", "description": "승률 (%)"},
    {"name": "trade_count", "type": "integer", "description": "거래 횟수"},
]

QUANTITY_FIELDS: List[Dict[str, str]] = [
    {"name": "exchange", "type": "string", "description": "거래소 코드"},
    {"name": "symbol", "type": "string", "description": "종목코드"},
    {"name": "quantity", "type": "number", "description": "산출 수량"},
    {"name": "weight", "type": "number", "description": "비중 (%)"},
]

ALLOCATED_CAPITAL_FIELDS: List[Dict[str, str]] = [
    {"name": "strategy_id", "type": "string", "description": "전략 ID"},
    {"name": "allocated", "type": "number", "description": "배분 금액"},
    {"name": "weight", "type": "number", "description": "배분 비중 (%)"},
]


class BaseNode(BaseModel):
    """
    모든 노드의 베이스 클래스

    Attributes:
        id: 노드 고유 ID (워크플로우 내에서 유일)
        type: 노드 타입 (클래스명)
        category: 노드 카테고리
        position: 클라이언트 UI용 위치 (선택적)
        config: 노드별 설정
        description: 노드 설명
    """

    id: str = Field(..., description="노드 고유 ID")
    type: str = Field(..., description="노드 타입")
    category: NodeCategory = Field(..., description="노드 카테고리")
    position: Optional[Position] = Field(
        default=None, description="클라이언트 UI용 노드 위치"
    )
    config: Dict[str, Any] = Field(default_factory=dict, description="노드 설정")
    description: Optional[str] = Field(default=None, description="노드 설명")

    # 메타 정보 (서브클래스에서 오버라이드)
    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = []
    _field_schema: ClassVar[Dict[str, FieldSchema]] = {}
    _img_url: ClassVar[Optional[str]] = None  # 노드 아이콘 이미지 URL
    _product_scope: ClassVar[ProductScope] = ProductScope.ALL
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.ALL
    _connection_rules: ClassVar[List["ConnectionRule"]] = []
    _rate_limit: ClassVar[Optional["RateLimitConfig"]] = None
    _risk_features: ClassVar[Set[str]] = set()  # {"hwm","window","events","state"}

    model_config = ConfigDict(use_enum_values=True, extra="allow")

    def get_inputs(self) -> List[InputPort]:
        """입력 포트 목록 반환"""
        return self._inputs

    def get_outputs(self) -> List[OutputPort]:
        """출력 포트 목록 반환"""
        return self._outputs

    def validate_config(self) -> bool:
        """설정 유효성 검증 (서브클래스에서 오버라이드)"""
        return True

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """
        노드의 설정 가능한 필드 스키마 반환 (UI 렌더링용)

        서브클래스에서 오버라이드하여 PARAMETERS/SETTINGS 카테고리 구분.

        Returns:
            Dict[str, FieldSchema]: 필드명 → 스키마 매핑

        Example:
            @classmethod
            def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
                from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
                return {
                    "url": FieldSchema(name="url", type=FieldType.STRING,
                        category=FieldCategory.PARAMETERS),
                    "timeout": FieldSchema(name="timeout", type=FieldType.INTEGER,
                        category=FieldCategory.SETTINGS),
                }
        """
        return {}

    @classmethod
    def is_tool_enabled(cls) -> bool:
        """
        이 노드가 AI Agent의 Tool로 사용 가능한지 여부.

        tool 엣지로 AIAgentNode에 연결 가능한 노드는 True를 반환합니다.
        서브클래스에서 오버라이드하여 변경 가능.

        Returns:
            bool: Tool로 사용 가능 여부 (기본 False)
        """
        return False

    @classmethod
    def _to_snake_case(cls, name: str) -> str:
        """CamelCase를 snake_case로 변환 (LLM function calling용)

        약어(AI, HTTP, LLM 등)도 올바르게 처리:
        - OverseasStockMarketDataNode → overseas_stock_market_data
        - AIAgentNode → ai_agent
        - HTTPRequestNode → http_request
        - LLMModelNode → llm_model
        """
        import re
        name = name.replace("Node", "")
        # 1단계: 약어 뒤에 소문자 단어가 오는 경계 (HTTPRequest → HTTP_Request)
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
        # 2단계: 소문자/숫자 뒤에 대문자가 오는 경계 (stockMarket → stock_Market)
        return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @classmethod
    def as_tool_schema(cls) -> Dict[str, Any]:
        """
        이 노드를 AI Tool로 사용할 때의 스키마.

        AI Agent가 LLM에 Tool 목록을 전달할 때 사용합니다.
        노드의 설정 가능한 필드(FieldSchema)를 Tool 파라미터로 변환합니다.

        Returns:
            dict: {
                "tool_name": "overseas_stock_market_data",  (LLM function calling용 snake_case)
                "node_type": "OverseasStockMarketDataNode", (원본 클래스명)
                "display_name": "i18n:nodes.OverseasStockMarketDataNode.name", (UI 표시용 i18n 키)
                "description": "...",
                "parameters": {...},
                "returns": {...},
            }
        """
        field_schemas = cls.get_field_schema()
        parameters = {}
        for field_name, fs in field_schemas.items():
            param = {
                "type": fs.type.value if hasattr(fs.type, 'value') else str(fs.type),
                "required": fs.required,
            }
            if fs.description:
                param["description"] = fs.description
            if fs.enum_values:
                param["enum"] = fs.enum_values
            if fs.default is not None:
                param["default"] = fs.default
            # object 타입: 내부 스키마 정보 전달 (AI Tool에서 LLM이 올바른 구조를 생성할 수 있도록)
            if hasattr(fs, 'object_schema') and fs.object_schema:
                param["object_schema"] = fs.object_schema
            if hasattr(fs, 'example') and fs.example is not None:
                param["example"] = fs.example
            if hasattr(fs, 'expected_type') and fs.expected_type:
                param["expected_type"] = fs.expected_type
            parameters[field_name] = param

        # 출력 포트 → returns
        # _outputs는 Pydantic에서 ModelPrivateAttr가 될 수 있으므로 인스턴스를 생성하여 접근
        returns = {}
        try:
            temp_instance = cls(id="__tool_schema__", type=cls.__name__)
            instance_outputs = temp_instance.get_outputs()
        except Exception:
            instance_outputs = []
        for out in instance_outputs:
            out_dict = {"type": out.type}
            if out.description:
                out_dict["description"] = out.description
            returns[out.name] = out_dict

        return {
            "tool_name": cls._to_snake_case(cls.__name__),
            "node_type": cls.__name__,
            "display_name": f"i18n:nodes.{cls.__name__}.name",
            "description": cls.__doc__.strip() if cls.__doc__ else "",
            "parameters": parameters,
            "returns": returns,
        }


class PluginNode(BaseNode):
    """
    플러그인을 사용하는 노드의 베이스 클래스

    ConditionNode, NewOrderNode, ModifyOrderNode, CancelOrderNode 등이 상속
    """

    plugin: str = Field(..., description="플러그인 ID (예: RSI, MarketOrder)")
    plugin_version: Optional[str] = Field(
        default=None, description="플러그인 버전 (예: 1.2.0)"
    )
    fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="플러그인 필드 (고정값, 바인딩, 표현식 지원)",
    )

    def get_plugin_ref(self) -> str:
        """플러그인 참조 문자열 반환 (예: RSI@1.2.0)"""
        if self.plugin_version:
            return f"{self.plugin}@{self.plugin_version}"
        return self.plugin

    def has_expressions(self) -> bool:
        """표현식이 포함된 필드가 있는지 확인"""
        from programgarden_core.models.field_binding import is_expression
        return any(is_expression(v) for v in self.fields.values())


class BaseMessagingNode(BaseNode):
    """
    메시징 노드의 베이스 클래스 (커뮤니티 확장용)

    TelegramNode, SlackNode, DiscordNode 등이 상속.
    각 노드는 execute() 메서드를 구현해야 함.

    Credential 자동 주입:
        credential_id를 설정하면 GenericNodeExecutor가 실행 전에
        credential 값을 노드 필드에 자동 주입합니다.

        Example:
            class TelegramNode(BaseMessagingNode):
                bot_token: Optional[str] = None  # credential에서 자동 주입됨
                chat_id: Optional[str] = None

                async def execute(self, context):
                    # self.bot_token에 이미 값이 있음!
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    Resilience (Retry/Fallback):
        외부 API 호출 실패 시 자동 재시도 및 실패 처리 설정.

        Example:
            class MyAPINode(BaseMessagingNode):
                resilience: ResilienceConfig = Field(
                    default_factory=lambda: ResilienceConfig(
                        retry=RetryConfig(enabled=True, max_retries=3),
                        fallback=FallbackConfig(mode=FallbackMode.SKIP),
                    )
                )
    """

    category: NodeCategory = NodeCategory.MESSAGING

    # 메시지 템플릿
    template: Optional[str] = Field(
        default=None,
        description="Message template with {{ }} placeholders (e.g., '체결: {{symbol}} {{quantity}}주 @ {{price}}')",
    )

    # Credential 연동 (GenericNodeExecutor가 자동 주입)
    credential_id: Optional[str] = Field(
        default=None,
        description="Credential ID from CredentialRegistry. 해당 credential의 필드들이 노드 필드에 자동 주입됨",
    )

    # Resilience 설정 (Retry/Fallback)
    resilience: ResilienceConfig = Field(
        default_factory=ResilienceConfig,
        description="외부 API 호출 실패 시 재시도 및 실패 처리 설정",
    )
    
    _inputs: List[InputPort] = [
        InputPort(
            name="event",
            type="event_data",
            description="Event data to send notification",
            required=False,
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="Manual trigger signal",
            required=False,
        ),
    ]
    
    _outputs: List[OutputPort] = [
        OutputPort(
            name="sent",
            type="signal",
            description="Notification sent confirmation",
        ),
    ]
    
    async def execute(self, context: Any) -> Dict[str, Any]:
        """
        알림 전송 실행 (서브클래스에서 구현 필수)

        Args:
            context: ExecutionContext with render_template() etc.

        Returns:
            dict with 'sent': bool, and optional 'message_id', 'error' etc.

        Note:
            credential_id가 설정되어 있으면 GenericNodeExecutor가 실행 전에
            credential 값을 노드 필드에 자동 주입합니다.
            따라서 self.bot_token, self.api_key 등을 바로 사용할 수 있습니다.
        """
        raise NotImplementedError("Subclass must implement execute()")

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        """
        에러가 재시도 가능한지 판단하고, 에러 유형 반환.

        서브클래스에서 오버라이드하여 노드별 에러 판단 로직 구현 가능.

        Args:
            error: 발생한 예외

        Returns:
            RetryableError 유형, 또는 None (재시도 불가)

        Example:
            class MyAPINode(BaseMessagingNode):
                def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
                    # 기본 판단 먼저 수행
                    base_result = super().is_retryable_error(error)
                    if base_result:
                        return base_result

                    # 노드별 추가 판단
                    if "quota exceeded" in str(error).lower():
                        return RetryableError.RATE_LIMIT

                    return None
        """
        error_str = str(error).lower()

        if "timeout" in error_str or "timed out" in error_str:
            return RetryableError.TIMEOUT
        if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
            return RetryableError.RATE_LIMIT
        if "connection" in error_str or "network" in error_str or "unreachable" in error_str:
            return RetryableError.NETWORK_ERROR
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return RetryableError.SERVER_ERROR

        return None

    @classmethod
    def get_resilience_field_schema(cls) -> Dict[str, FieldSchema]:
        """
        Resilience 설정의 UI 필드 스키마.

        Returns:
            Dict[str, FieldSchema]: 필드명 → 스키마 매핑
        """
        return {
            "resilience.retry.enabled": FieldSchema(
                name="resilience.retry.enabled",
                type=FieldType.BOOLEAN,
                label="재시도 활성화",
                description="실패 시 자동으로 재시도합니다",
                default=False,
                category=FieldCategory.SETTINGS,
            ),
            "resilience.retry.max_retries": FieldSchema(
                name="resilience.retry.max_retries",
                type=FieldType.INTEGER,
                label="최대 재시도 횟수",
                description="1~10회 사이로 설정",
                default=3,
                min=1,
                max=10,
                category=FieldCategory.SETTINGS,
                depends_on={"resilience.retry.enabled": True},
            ),
            "resilience.retry.base_delay": FieldSchema(
                name="resilience.retry.base_delay",
                type=FieldType.NUMBER,
                label="재시도 대기 시간 (초)",
                description="첫 재시도까지 대기 시간",
                default=1.0,
                min=0.1,
                max=30.0,
                category=FieldCategory.SETTINGS,
                depends_on={"resilience.retry.enabled": True},
            ),
            "resilience.fallback.mode": FieldSchema(
                name="resilience.fallback.mode",
                type=FieldType.STRING,
                label="실패 시 동작",
                description="모든 재시도 실패 후 동작",
                default="error",
                options=[
                    {"value": "error", "label": "워크플로우 중단"},
                    {"value": "skip", "label": "이 노드 건너뛰기"},
                    {"value": "default_value", "label": "기본값 사용"},
                ],
                category=FieldCategory.SETTINGS,
            ),
            "resilience.fallback.default_value": FieldSchema(
                name="resilience.fallback.default_value",
                type=FieldType.JSON,
                label="기본값",
                description="실패 시 반환할 기본값 (JSON)",
                category=FieldCategory.SETTINGS,
                depends_on={"resilience.fallback.mode": "default_value"},
            ),
        }