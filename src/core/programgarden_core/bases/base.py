"""Foundational base types and strategy scaffolding for ProgramGarden.

EN:
    Provide reusable TypedDict definitions and abstract base classes that power
    overseas stock and futures trading workflows.

KO:
    해외 주식과 해외 선물 매매 워크플로를 구성하는 TypedDict 정의와 추상 베이스
    클래스를 제공합니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, TypedDict, Union, TYPE_CHECKING
from typing_extensions import NotRequired

if TYPE_CHECKING:
    from .system import DpsTyped

# EN: Supported order action identifiers within ProgramGarden strategies.
# KO: ProgramGarden 전략에서 지원하는 주문 동작 식별자 목록입니다.
OrderType = Literal[
    "new_buy",
    "new_sell",
    "cancel_buy",
    "cancel_sell",
    "modify_buy",
    "modify_sell"
]

# EN: Possible real-time order events delivered from brokerage callbacks.
# KO: 증권사 콜백으로 전달되는 실시간 주문 이벤트 유형 목록입니다.
OrderRealResponseType = Literal[
    "submitted_new_buy", "submitted_new_sell",
    "filled_new_buy", "filled_new_sell",
    "cancel_request_buy", "cancel_request_sell",
    "modify_buy", "modify_sell", "cancel_complete_buy", "cancel_complete_sell",
    "reject_buy", "reject_sell"
]
"""EN:
    Broker event keywords describing order lifecycle transitions.
    - submitted_new_buy: Exchange acknowledged a new buy order submission.
    - submitted_new_sell: Exchange acknowledged a new sell order submission.
    - filled_new_buy: New buy order filled.
    - filled_new_sell: New sell order filled.
    - cancel_request_buy: Cancellation request submitted for a buy order.
    - cancel_request_sell: Cancellation request submitted for a sell order.
    - modify_buy: Modification request submitted for a buy order.
    - modify_sell: Modification request submitted for a sell order.
    - cancel_complete_buy: Buy order cancellation fully processed.
    - cancel_complete_sell: Sell order cancellation fully processed.
    - reject_buy: Buy order rejected by the broker.
    - reject_sell: Sell order rejected by the broker.

KO:
    주문 수명 주기 변화를 나타내는 브로커 이벤트 키워드입니다.
    - submitted_new_buy: 신규 매수 주문이 접수되었습니다.
    - submitted_new_sell: 신규 매도 주문이 접수되었습니다.
    - filled_new_buy: 신규 매수 주문이 체결되었습니다.
    - filled_new_sell: 신규 매도 주문이 체결되었습니다.
    - cancel_request_buy: 매수 주문 취소 요청이 접수되었습니다.
    - cancel_request_sell: 매도 주문 취소 요청이 접수되었습니다.
    - modify_buy: 매수 주문 정정 요청이 접수되었습니다.
    - modify_sell: 매도 주문 정정 요청이 접수되었습니다.
    - cancel_complete_buy: 매수 주문 취소가 완료되었습니다.
    - cancel_complete_sell: 매도 주문 취소가 완료되었습니다.
    - reject_buy: 매수 주문이 거부되었습니다.
    - reject_sell: 매도 주문이 거부되었습니다.
"""


class SymbolInfoBase(TypedDict):
    """Shared symbol metadata used by overseas products.

    EN:
        Capture core attributes such as the broker symbol code and optional
        human-readable names that apply to both stock and futures instruments.

    KO:
        해외 주식과 선물 모두에 공통으로 사용되는 핵심 속성(브로커 종목 코드,
        사람 친화적인 이름 등)을 정의합니다.
    """

    symbol: str
    """EN: Broker-provided unique symbol code.
    KO: 종목코드(브로커가 제공하는 고유 종목 코드입니다.)"""

    product_type: NotRequired[Literal["overseas_stock", "overseas_futures"]]
    """EN: Instrument category identifying stock or futures.
    KO: 상품유형(종목이 주식인지 선물인지 구분하는 상품 유형입니다.)"""

    symbol_name: NotRequired[str]
    """EN: Human-friendly symbol name, if supplied by the broker.
    KO: 종목명(브로커가 제공하는 사람 친화적인 종목명입니다.)"""


class SymbolInfoOverseasStock(SymbolInfoBase):
    """Structured view of overseas stock symbol information.

    EN:
        Extends :class:`SymbolInfoBase` with equity-specific metadata required
        for trading and order reconciliation.

    KO:
        해외 주식 주문과 체결 정리에 필요한 주식 전용 메타데이터를
        :class:`SymbolInfoBase` 에서 확장합니다.
    """

    product_type: Literal["overseas_stock"] = "overseas_stock"
    """EN: Fixed literal indicating the stock asset class.
    KO: 해외주식상품유형식별자(주식 자산군을 나타내는 고정 literal 값입니다.)"""

    exchcd: Literal["81", "82"]
    """EN: Exchange code (81: NYSE/AMEX, 82: NASDAQ).
    KO: 거래소코드(81: 뉴욕/아멕스, 82: 나스닥)."""

    mcap: NotRequired[float]
    """EN: Market capitalization in millions of USD.
    KO: 시가총액(단위: 백만 달러)입니다."""

    OrdNo: NotRequired[int]
    """EN: Order identifier for pending or amended requests.
    KO: 주문번호(미체결 또는 정정 주문을 추적하는 주문 번호입니다.)"""


class SymbolInfoOverseasFutures(SymbolInfoBase):
    """Structured view of overseas futures symbol information.

    EN:
        Adds derivatives-specific attributes like expiration codes and
        contract sizes for futures markets.

    KO:
        선물 시장에서 사용하는 만기 코드, 계약 단위 등 파생상품 전용 속성을
        포함합니다.
    """

    product_type: Literal["overseas_futures"] = "overseas_futures"
    """EN: Literal indicating the futures asset class.
    KO: 해외선물상품유형식별자(선물 자산군을 나타내는 literal 입니다.)"""

    exchcd: NotRequired[str]
    """EN: Exchange code such as CME or NYMEX.
    KO: 거래소코드(CME, NYMEX 등 거래소 코드를 나타냅니다.)"""

    due_yymm: NotRequired[str]
    """EN: Expiration year and month (``YYMM`` format).
    KO: 해외선물만기년월(``YYMM`` 형식 값입니다.)"""

    prdt_code: NotRequired[str]
    """EN: Broker-specific product identifier.
    KO: 상품코드(브로커가 사용하는 상품 코드입니다.)"""

    currency_code: NotRequired[str]
    """EN: Settlement currency code.
    KO: 통화코드(결제 통화 코드입니다.)"""

    contract_size: NotRequired[float]
    """EN: Contract unit size for the futures instrument.
    KO: 계약단위(선물 계약 단위입니다.)"""

    position_side: NotRequired[Literal["long", "short", "flat"]] = "flat"
    """EN: Current directional exposure; defaults to ``flat``.
    KO: 포지션방향(기본값은 ``flat`` 이며 ``long``: 매수, ``short``: 매도, ``flat``: 보유 없음입니다.)"""

    unit_price: NotRequired[float]
    """EN: Minimum tick price.
    KO: 호가단위가격(최소 호가 단위 가격입니다.)"""

    min_change_amount: NotRequired[float]
    """EN: Monetary value of a single tick movement.
    KO: 최소변동액(한 틱 움직임의 금액 값을 나타냅니다.)"""

    maintenance_margin: NotRequired[float]
    """EN: Maintenance margin requirement.
    KO: 유지증거금(유지 증거금 요구 사항입니다.)"""

    opening_margin: NotRequired[float]
    """EN: Initial margin requirement.
    KO: 개시증거금(개시 증거금 요구 사항입니다.)"""


class HeldSymbolOverseasStock(TypedDict):
    """Snapshot of overseas stock holdings.

    EN:
        Represents balances, currencies, and exposure metrics for equity
        positions retrieved from the brokerage.

    KO:
        증권사에서 전달되는 주식 포지션의 잔고, 통화, 수익률 정보를 포함합니다.
    """

    CrcyCode: str
    """EN: Currency code associated with the position.
    KO: 통화코드(포지션이 표시되는 통화 코드입니다.)"""

    ShtnIsuNo: str
    """EN: Short symbol identifier used by the broker.
    KO: 단축종목번호(브로커가 사용하는 단축 종목 번호입니다.)"""

    AstkBalQty: int
    """EN: Total shares currently held.
    KO: 해외증권잔고수량(현재 보유하고 있는 총 주식 수량입니다.)"""

    AstkSellAbleQty: int
    """EN: Shares available for selling.
    KO: 해외증권매도가능수량(매도 가능한 주식 수량입니다.)"""

    PnlRat: float
    """EN: Profit and loss ratio expressed as a percentage.
    KO: 손익율(퍼센트 단위 손익률입니다.)"""

    BaseXchrat: float
    """EN: Base exchange rate applied for currency conversion.
    KO: 기준환율(환산에 사용되는 기준 환율입니다.)"""

    PchsAmt: float
    """EN: Total purchase amount in settlement currency.
    KO: 매입금액(결제 통화 기준의 총 매입 금액입니다.)"""

    FcurrMktCode: str
    """EN: Foreign market code describing the trading venue.
    KO: 외화시장코드(거래 시장을 나타내는 외화 시장 코드입니다.)"""


class HeldSymbolOverseasFutures(TypedDict, total=False):
    """Snapshot of overseas futures positions.

    EN:
        Includes derivative-specific metrics such as position numbers and
        margin requirements.

    KO:
        파생상품 전용 속성(포지션 번호, 증거금 등)을 포함한 해외 선물 포지션
        정보입니다.
    """

    IsuCodeVal: str
    """EN: Futures instrument code.
    KO: 종목코드값(선물 종목 코드 값입니다.)"""

    IsuNm: str
    """EN: Futures instrument name.
    KO: 종목명(선물 종목명입니다.)"""

    BnsTpCode: str
    """EN: Buy/sell type code.
    KO: 매매구분코드(매수/매도 구분 코드입니다.)"""

    BalQty: float
    """EN: Quantity currently held.
    KO: 잔고수량(현재 보유 수량입니다.)"""

    OrdAbleAmt: float
    """EN: Available amount for new orders.
    KO: 주문가능금액(신규 주문에 사용할 수 있는 금액입니다.)"""

    DueDt: str
    """EN: Contract maturity date.
    KO: 만기일자(계약 만기 일자입니다.)"""

    OvrsDrvtNowPrc: float
    """EN: Latest derivative price from the broker.
    KO: 해외파생현재가(브로커가 제공하는 최신 파생상품 가격입니다.)"""

    AbrdFutsEvalPnlAmt: float
    """EN: Evaluated profit and loss amount.
    KO: 해외선물평가손익금액(평가 손익 금액입니다.)"""

    PchsPrc: float
    """EN: Average purchase price.
    KO: 매입가격(평균 매입 가격입니다.)"""

    CrcyCodeVal: str
    """EN: Currency code value for the position.
    KO: 통화코드값(포지션의 통화 코드 값입니다.)"""

    PosNo: str
    """EN: Position identifier assigned by the broker.
    KO: 포지션번호(브로커가 부여한 포지션 번호입니다.)"""

    MaintMgn: float
    """EN: Maintenance margin requirement.
    KO: 유지증거금(유지 증거금 금액입니다.)"""

    CsgnMgn: float
    """EN: Initial margin (customer margin) requirement.
    KO: 위탁증거금액(초기 증거금 금액입니다.)"""


HeldSymbol = Union[HeldSymbolOverseasStock, HeldSymbolOverseasFutures]
"""EN: Unified type hint for overseas stock and futures holdings.
KO: 해외 주식과 선물 보유 잔고를 모두 표현하는 통합 타입 힌트입니다."""


class NonTradedSymbolOverseasStock(TypedDict):
    """Open overseas stock order details that remain pending.

    EN:
        Captures identifiers and quantities for orders awaiting execution or
        confirmation.

    KO:
        해외주식 미체결 주문 정보로서 체결 대기 중인 주문의 식별자와 수량 정보를 수집합니다.
    """

    OrdTime: str
    """EN: Order timestamp in ``HHMMSSmmm`` format.
    KO: 주문시각(``HHMMSSmmm`` 형식이며 HH/시(00-23), MM/분(00-59), SS/초(00-59), mmm/밀리초(000-999)입니다.)
    
    HH -> hours (00-23)
    MM -> minutes (00-59)
    SS -> seconds (00-59)
    mmm -> milliseconds (000-999)
    """

    OrdNo: int
    """EN: Unique order number assigned by the broker.
    KO: 주문번호(브로커가 부여한 고유 주문 번호입니다.)"""

    OrgOrdNo: int
    """EN: Original order number used when amendments exist.
    KO: 원주문번호(정정 주문 시 참조되는 번호입니다.)"""

    ShtnIsuNo: str
    """EN: Short instrument identifier matching the symbol.
    KO: 단축종목번호(종목에 해당하는 단축 종목 번호입니다.)"""

    MrcAbleQty: int
    """EN: Quantity available for modification or cancellation.
    KO: 정정취소가능수량(정정/취소가 가능한 수량입니다.)"""

    OrdQty: int
    """EN: Total quantity originally ordered.
    KO: 주문수량(주문했었던 총 수량입니다.)"""

    OvrsOrdPrc: float
    """EN: Order price in the overseas market.
    KO: 해외주문가(해외 시장 기준 주문 가격입니다.)"""

    OrdprcPtnCode: str
    """EN: Order price type code.
    KO: 호가유형코드(호가 유형 코드입니다.)"""

    OrdPtnCode: str
    """EN: Order type code.
    KO: 주문유형코드(주문 유형 코드입니다.)"""

    MrcTpCode: str
    """EN: Modification/cancellation type code.
    KO: 정정취소구분코드(정정/취소 구분 코드입니다.)"""

    OrdMktCode: str
    """EN: Market code where the order was submitted.
    KO: 주문시장코드(주문을 접수한 시장 코드입니다.)"""

    UnercQty: int
    """EN: Remaining unfilled quantity.
    KO: 미체결수량(아직 체결되지 않은 수량입니다.)"""

    CnfQty: int
    """EN: Confirmed quantity acknowledged by the broker.
    KO: 확인수량(브로커가 확인한 수량입니다.)"""

    CrcyCode: str
    """EN: Currency code of the transaction.
    KO: 통화코드(거래에 사용된 통화 코드입니다.)"""

    RegMktCode: str
    """EN: Registered market code.
    KO: 등록시장코드(등록된 시장 코드입니다.)"""

    IsuNo: str
    """EN: Full instrument number.
    KO: 종목번호(전체 종목 번호입니다.)"""

    BnsTpCode: str
    """EN: Buy/sell direction code.
    KO: 매매구분코드(매수/매도 구분 코드입니다.)"""


class NonTradedSymbolOverseasFutures(TypedDict, total=False):
    """Open overseas futures order details that remain pending.

    EN:
        Mirrors the stock structure while including futures-specific metadata
        such as FCM references and derivative order types.

    KO:
        해외선물 미체결 주문 정보로서 주식 구조와 유사하지만 FCM 참조나 파생 주문 유형처럼 선물 전용 정보를
        추가로 포함합니다.
    """

    OvrsFutsOrdNo: str
    """EN: Futures order number.
    KO: 해외선물주문번호(해외 선물 주문 번호입니다.)"""

    OvrsFutsOrgOrdNo: str
    """EN: Original futures order number used when amending.
    KO: 해외선물원주문번호(정정 요청 시 참조하는 원주문 번호입니다.)"""

    FcmOrdNo: str
    """EN: Order number assigned by the Futures Commission Merchant (FCM).
    KO: FCM주문번호(FCM이 부여한 주문 번호입니다.)"""

    IsuCodeVal: str
    """EN: Futures instrument code value.
    KO: 종목코드값(선물 종목 코드 값입니다.)"""

    IsuNm: str
    """EN: Futures instrument name.
    KO: 종목명(선물 종목 명칭입니다.)"""

    BnsTpCode: str
    """EN: Buy/sell direction code.
    KO: 매매구분코드(매수/매도 구분 코드입니다.)"""

    FutsOrdStatCode: str
    """EN: Futures order status code.
    KO: 선물주문상태코드(선물 주문 상태 코드입니다.)"""

    FutsOrdTpCode: str
    """EN: Futures order type code.
    KO: 선물주문구분코드(선물 주문 구분 코드입니다.)"""

    AbrdFutsOrdPtnCode: str
    """EN: Overseas futures order pattern code.
    KO: 해외선물주문유형코드(해외 선물 주문 유형 코드입니다.)"""

    OrdQty: int
    """EN: Quantity submitted with the order.
    KO: 주문수량(주문에 제출한 수량입니다.)"""

    ExecQty: int
    """EN: Quantity already executed.
    KO: 체결수량(이미 체결된 수량입니다.)"""

    UnercQty: int
    """EN: Remaining unexecuted quantity.
    KO: 미체결수량(아직 체결되지 않은 수량입니다.)"""

    OvrsDrvtOrdPrc: float
    """EN: Order price for the derivative instrument.
    KO: 해외파생주문가격(파생상품 주문 가격입니다.)"""

    OrdDt: str
    """EN: Order date in ``YYYYMMDD`` format.
    KO: 주문일자(``YYYYMMDD`` 형식의 주문 일자입니다.)"""

    OrdTime: str
    """EN: Order time stamp.
    KO: 주문시각(주문 시각입니다.)"""

    CvrgYn: str
    """EN: Flag indicating whether the order is for covering positions.
    KO: 반대매매여부(반대 매매 여부 플래그입니다.)"""

    ExecBnsTpCode: str
    """EN: Execution direction code.
    KO: 체결매매구분코드(체결 매매 구분 코드입니다.)"""

    FcmAcntNo: str
    """EN: FCM account number associated with the order.
    KO: FCM계좌번호(주문과 연결된 FCM 계좌 번호입니다.)"""


NonTradedSymbol = Union[NonTradedSymbolOverseasStock, NonTradedSymbolOverseasFutures]
"""EN: Unified type hint for pending overseas stock and futures orders.
KO: 해외 주식/선물 미체결 주문을 모두 표현하는 통합 타입 힌트입니다."""


SymbolInfoType = TypeVar("SymbolInfoType", SymbolInfoOverseasStock, SymbolInfoOverseasFutures)
OrderResGenericT = TypeVar("OrderResGenericType", bound=Dict[str, Any])


class BaseOrderOverseas(Generic[OrderResGenericT, SymbolInfoType], ABC):
    """Abstract base class for overseas order strategies.

    EN:
        Defines the minimum surface area required to implement trading
        strategies that submit, modify, or cancel overseas orders.

    KO:
        해외 주문을 신규, 정정, 취소하는 전략을 구현할 때 필요한 최소 인터페이스를
        정의합니다.
    """

    product: Literal["overseas_stock", "overseas_futures"]
    """EN: Product category handled by the strategy implementation.
    KO: 전략 구현이 처리하는 상품 유형입니다."""

    id: str
    """EN: Unique identifier for the strategy.
    KO: 전략을 구분하는 고유 식별자입니다."""

    name: str
    """EN: name of the strategy.
    KO: 전략의 이름입니다."""

    description: str
    """EN: description of the strategy.
    KO: 전략에 대한 설명입니다."""

    securities: List[str]
    """EN: Broker identifiers this strategy communicates with.
    KO: 전략이 연동하는 증권사 식별자 목록입니다."""

    order_types: List[OrderType]
    """EN: Order actions supported by the strategy (e.g., ``new_buy``).
    KO: 전략이 지원하는 주문 동작 목록입니다 (예: ``new_buy``)."""

    parameter_schema: dict[str, Any]
    """EN: Configurable parameters for the condition.

    KO: 조건의 `def __init__`에 전달되는 매개변수가 어떤 것들이 있는지 설명하는 변수입니다. 투자자가 인지하는 중요한 값이며 아래처럼 세팅해야합니다.

    ```python

    # 1.매개변수를 설명하는 BaseModel 라이브러리를 이용하여 아래처럼 정의해야합니다.
    class SMAGoldenDeadCrossParams(BaseModel):
        start_date: Optional[str] = Field(
            None,
            title="시작 날짜",
            description="차트가 시작하는 날짜입니다",
            json_schema_extra={"example": "20230101"}
        )

        end_date: Optional[str] = Field(
            None,
            title="종료 날짜",
            description="차트가 종료되는 날짜입니다",
            json_schema_extra={"example": "20231231"}
        )

    # 2.정의된 BaseModel을 기반으로 paramters를 model_json_schema()로 json 스키마로 합니다.
    parameter_schema: SMAGoldenDeadCrossParams.model_json_schema()
    ```
    """

    @abstractmethod
    def __init__(self) -> None:
        """Initialize default state containers used across implementations."""
        self.available_symbols: List[SymbolInfoType] = []
        """EN: Candidate symbols retrieved for upcoming order decisions.
        KO: 주문 의사결정에 사용할 후보 종목 목록입니다."""

        self.held_symbols: List[HeldSymbol] = []
        """EN: Currently held positions provided by account queries.
        KO: 계좌 조회를 통해 전달받은 현재 보유 포지션입니다."""

        self.non_traded_symbols: List[NonTradedSymbol] = []
        """EN: Outstanding orders waiting to be filled or cancelled.
        KO: 체결 또는 취소 대기 중인 미체결 주문 목록입니다."""

        self.dps: Optional[List[DpsTyped]] = None
        """EN: Available cash balances USD for order sizing.
        KO: 주문 규모 계산에 사용하는 USD 예수금 정보입니다."""

        self.system_id: Optional[str] = None
        """EN: Identifier ID of system orchestrating this strategy.
        KO: 이 전략을 구동하는 시스템 식별자 ID 입니다."""

    @abstractmethod
    async def execute(self) -> List[OrderResGenericT]:
        """Run the strategy and produce order instructions.

        EN:
            Implementations should analyze symbols, holdings, and balances to
            generate brokerage payloads or order commands.

        KO:
            구현체는 종목, 보유 자산, 잔고를 분석하여 주문 지시나 브로커 요청
            페이로드를 생성해야 합니다.

        Returns:
            List[OrderResGenericT]: Collection of order messages to submit.
        """
        raise NotImplementedError()

    def _set_system_id(self, system_id: Optional[str]) -> None:
        """Store the system identifier controlling this strategy.

        EN:
            Useful when logging or cross-referencing actions with orchestrators.

        KO:
            오케스트레이터와 로그를 연동할 때 참조할 수 있도록 시스템 ID를
            저장합니다.

        Parameters:
            system_id (Optional[str]): Identifier provided by the runtime.
        """
        self.system_id = system_id

    def _set_available_symbols(self, symbols: List[SymbolInfoType]) -> None:
        """Inject symbol candidates used during strategy evaluation.

        EN:
            Allows executors to supply filtered watchlists prior to ``execute``.

        KO:
            ``execute`` 전에 필터링된 감시 목록을 전략에 전달할 때 사용합니다.

        Parameters:
            symbols (List[SymbolInfoType]): Symbol metadata list.
        """
        self.available_symbols = symbols

    def _set_held_symbols(self, symbols: List[HeldSymbol]) -> None:
        """Update the cache of currently held positions.

        EN:
            Provides context for position-aware strategies (e.g., exits).

        KO:
            보유 포지션 기반 전략이 참고할 수 있도록 현재 상태를 갱신합니다.

        Parameters:
            symbols (List[HeldSymbol]): Holdings returned from account queries.
        """
        self.held_symbols = symbols

    def _set_non_traded_symbols(self, symbols: List[NonTradedSymbol]) -> None:
        """Update open orders awaiting execution.

        EN:
            Enables duplicate-order prevention or advanced reconciliation.

        KO:
            중복 주문 방지나 고급 정합 기능이 활용할 수 있도록 미체결 정보를
            갱신합니다.

        Parameters:
            symbols (List[NonTradedSymbol]): Outstanding order records.
        """
        self.non_traded_symbols = symbols

    def _set_available_balance(
        self,
        dps: Optional[List[DpsTyped]],
    ) -> None:
        """Record the available balance disclosed by the broker.

        EN:
            Cash balances inform position sizing and risk checks.

        KO:
            예수금 정보는 포지션 사이징과 리스크 점검에 활용됩니다.

        Parameters:
            dps (Optional[List[DpsTyped]]): Foreign currency balance details.

        Returns:
            None: The function updates internal state in place.
        """
        self.dps = dps

    @abstractmethod
    async def on_real_order_receive(self, order_type: OrderRealResponseType, response: OrderResGenericT) -> None:
        """Handle order status callbacks emitted by the broker.

        EN:
            Use this hook to react to fills, rejections, or cancellation events.

        KO:
            체결, 거부, 취소 이벤트에 반응하도록 구현해야 하는 콜백 훅입니다.

        Parameters:
            order_type (OrderRealResponseType): Event keyword describing status.
            response (OrderResGenericT): Raw payload provided by the broker.
        """
        raise NotImplementedError()


class BaseOrderOverseasStock(BaseOrderOverseas[OrderResGenericT, SymbolInfoOverseasStock], ABC):
    """Base strategy scaffold for overseas stock order flows.

    EN:
        Specializes :class:`BaseOrderOverseas` with stock-specific symbol types.

    KO:
        해외주식 매매 주문을 위한 기본 전략 클래스로서, 주식 전용 심볼 타입을 사용하도록 :class:`BaseOrderOverseas` 를 특화합니다.
    """

    product: Literal["overseas_stock"] = "overseas_stock"
    """EN: Literal used to signal stock trading workflows.
    KO: 해외주식 거래 워크플로를 나타내는 literal 값입니다."""


class BaseOrderOverseasFutures(BaseOrderOverseas[OrderResGenericT, SymbolInfoOverseasFutures], ABC):
    """Base strategy scaffold for overseas futures order flows.

    EN:
        Specializes :class:`BaseOrderOverseas` with futures-specific symbol types.

    KO:
        해외선물 매매 주문을 위한 기본 전략 클래스로서, 전용 심볼 타입을 사용하도록 :class:`BaseOrderOverseas` 를 특화합니다.
    """
    product: Literal["overseas_futures"] = "overseas_futures"
    """EN: Literal used to signal futures trading workflows.
    KO: 해외선물 거래 워크플로를 나타내는 literal 값입니다."""
