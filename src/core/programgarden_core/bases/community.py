from abc import ABC, abstractmethod
from typing import List, Literal, Optional, TypedDict, Any, Dict, TypeVar, Generic

OrderCategoryType = Literal["submitted_new_buy", "submitted_new_sell",
                            "filled_new_buy", "filled_new_sell",
                            "cancel_request_buy", "cancel_request_sell",
                            "modify_buy", "modify_sell", "cancel_complete_buy", "cancel_complete_sell",
                            "reject_buy", "reject_sell"]
"""
- submitted_new_buy: 신규 매수 접수
- submitted_new_sell: 신규 매도 접수
- filled_new_buy: 신규 매수 체결
- filled_new_sell: 신규 매도 체결
- cancel_request_buy: 매수 취소 접수
- cancel_request_sell: 매도 취소 접수
- modify_buy: 매수 정정 접수
- modify_sell: 매도 정정 접수
- cancel_complete_buy: 매수 취소 완료
- cancel_complete_sell: 매도 취소 완료
- reject_buy: 매수 주문 거부
- reject_sell: 매도 주문 거부
"""


class SymbolInfo(TypedDict):
    """
    종목 정보를 담기 위한 타입

    Args
    ----------
    symbol: str
        종목 코드
    exchcd: Literal["81", "82"]
        거래소 코드
    """
    symbol: str
    """종목 코드"""
    exchcd: Literal["81", "82"]
    """
    거래소 코드
    82: NASDAQ
    81: 뉴욕증권거래소
    """
    mcap: Optional[float] = None
    """시가총액 (단위: 백만 달러)"""


class HeldSymbol(TypedDict):
    """
    주문해서 보유중인 종목들
    """
    CrcyCode: str
    """통화코드"""
    ShtnIsuNo: str
    """단축종목번호"""
    AstkBalQty: float
    """해외증권잔고수량"""
    AstkSellAbleQty: float
    """해외증권매도가능수량"""
    PnlRat: float
    """손익율"""
    BaseXchrat: float
    """기준환율"""
    PchsAmt: float
    """매입금액"""
    FcurrMktCode: str
    """외화시장코드"""


class NonTradedSymbol(TypedDict):
    """
    미체결 종목
    """
    OrdTime: str
    """주문시각"""
    OrdNo: int
    """주문번호"""
    OrgOrdNo: int
    """원주문번호"""
    ShtnIsuNo: str
    """단축종목번호"""
    MrcAbleQty: int
    """정정취소가능수량"""
    OrdQty: int
    """주문수량"""
    OvrsOrdPrc: float
    """해외주문가"""
    OrdprcPtnCode: str
    """호가유형코드"""
    OrdPtnCode: str
    """주문유형코드"""
    MrcTpCode: str
    """정정취소구분코드"""
    OrdMktCode: str
    """주문시장코드"""
    UnercQty: int
    """미체결수량"""
    CnfQty: int
    """확인수량"""
    CrcyCode: str
    """통화코드"""
    RegMktCode: str
    """등록시장코드"""
    IsuNo: str
    """종목번호"""
    BnsTpCode: str
    """매매구분코드"""


class BaseCondition(ABC):
    """
    기본 전략의 조건 타입을 정의하는 추상 클래스입니다.
    """

    id: str
    """전략의 고유 ID"""
    description: str
    """전략에 대한 설명"""
    securities: List[str]
    """사용 가능한 증권사/거래소들"""

    @abstractmethod
    def __init__(self, **kwargs):
        self.symbol: Optional[SymbolInfo] = None

    @abstractmethod
    async def execute(self) -> 'BaseConditionResponseType':
        """
        전략을 실행하는 메서드입니다.
        구체적인 전략 클래스에서 구현해야 합니다.
        """
        pass

    def _set_system_id(self, system_id: Optional[str]) -> None:
        """
        시스템 고유 ID를 설정합니다.
        """
        self.system_id = system_id

    def _set_symbol(self, symbol: SymbolInfo) -> None:
        """
        계산할 종목들을 선정합니다.
        선정된 종목들 위주로 조건 충족 여부를 확인해서 반환해줍니다.
        """
        self.symbol = symbol


class BaseConditionResponseType(TypedDict):
    """기본 응답 데이터"""

    condition_id: Optional[str]
    """조건 ID"""
    success: bool
    """조건 통과한 종목이 1개라도 있으면 True로 처리합니다."""
    symbol: str
    """종목 코드"""
    exchcd: str
    """거래소 코드"""
    data: Any
    """조건 통과한 종목에 대한 추가 데이터"""
    weight: Optional[int] = 0
    """조건의 가중치는 0과 1사이의 값, 기본값은 0"""


class BaseBuyOverseasStockResponseType(TypedDict):
    """주문을 넣기 위한 반환값 데이터"""
    success: bool
    """전략 통과 성공 여부"""
    ord_ptn_code: Literal["02"] = "02"
    """주문유형코드 (02: 매수주문)"""
    ord_mkt_code: Literal["81", "82"]
    """주문시장코드 (81: 뉴욕거래소, 82: NASDAQ)"""
    isu_no: str
    """종목번호 (단축종목코드 ex.TSLA)"""
    ord_qty: int
    """주문수량"""
    ovrs_ord_prc: float
    """해외주문가"""
    ordprc_ptn_code: Literal["00", "M1", "M2"]
    """호가유형코드 (00: 지정가, M1: LOO, M2: LOC)"""


class BaseSellOverseasStockResponseType(TypedDict):
    """주문을 넣기 위한 반환값 데이터"""
    success: bool
    """전략 통과 성공 여부"""
    ord_ptn_code: Literal["01"] = "01"
    """주문유형코드 (01: 매도주문)"""
    ord_mkt_code: Literal["81", "82"]
    """주문시장코드 (81: 뉴욕거래소, 82: NASDAQ)"""
    shtn_isu_no: str
    """종목번호 (단축종목코드 ex.TSLA)"""
    ord_qty: int
    """주문수량"""
    ovrs_ord_prc: float
    """해외주문가"""
    ordprc_ptn_code: Literal["00", "M1", "M2"]
    """호가유형코드 (00: 지정가, M1: LOO, M2: LOC, 03@시장가, M3@MOO, M4@MOC)"""
    crcy_code: Literal["USD"] = "USD"
    """통화코드 (USD)"""
    pnl_rat: float
    """손익률"""
    pchs_amt: float
    """매입금액"""


OrderResGenericT = TypeVar("OrderResGenericType", bound=Dict[str, Any])


class BaseOrderOverseasStock(Generic[OrderResGenericT], ABC):
    """
    해외주식 매매 주문을 위한 기본 전략 클래스
    """

    id: str
    """전략의 고유 ID"""
    description: str
    """전략에 대한 설명"""
    securities: List[str]
    """사용 가능한 증권사/거래소들"""

    @abstractmethod
    def __init__(
        self,
    ):
        self.available_symbols = []

    @abstractmethod
    async def execute(self) -> 'List[OrderResGenericT]':
        """
        매수 전략을 실행하는 메서드입니다.
        """
        pass

    def _set_system_id(self, system_id: Optional[str]) -> None:
        """
        시스템 고유 ID를 설정합니다.
        """
        self.system_id = system_id

    def _set_available_symbols(self, symbols: List[SymbolInfo]) -> None:
        """
        매매 전략 계산에 사용하려는 종목들을 전달합니다.
        """
        self.available_symbols = symbols

    def _set_held_symbols(self, symbols: List[HeldSymbol]) -> None:
        """
        현재 보유중인 종목들을 받습니다.
        """
        self.held_symbols = symbols

    def _set_non_traded_symbols(self, symbols: List[NonTradedSymbol]) -> None:
        """
        현재 미체결 종목들을 받습니다.
        """
        self.non_traded_symbols = symbols

    @abstractmethod
    async def on_real_order_receive(self, order_type: OrderCategoryType, response: OrderResGenericT) -> None:
        """
        매매 주문 상태를 받습니다.
        """
        pass


class BaseBuyOverseasStock(BaseOrderOverseasStock[BaseBuyOverseasStockResponseType]):
    """
    매수를 하기 위한 전략을 계산하고 매수를 위한 값을 던져줍니다.
    """

    @abstractmethod
    def __init__(
        self,
    ):
        super().__init__()

        self.fcurr_dps = 0.0
        self.fcurr_ord_able_amt = 0.0

    def _set_available_balance(
        self,
        fcurr_dps: float,
        fcurr_ord_able_amt: float
    ) -> None:
        """
        사용 가능한 잔고를 설정합니다.

        Args:
            fcurr_dps (float): 외화 예금
            fcurr_ord_able_amt (float): 외화 주문 가능 금액
        """
        self.fcurr_dps = fcurr_dps
        self.fcurr_ord_able_amt = fcurr_ord_able_amt


class BaseSellOverseasStock(BaseOrderOverseasStock[BaseSellOverseasStockResponseType]):
    """
    매도를 하기 위한 전략을 계산하고 매도를 위한 값을 던져줍니다.
    """

    id: str
    """전략의 고유 ID"""
    description: str
    """전략에 대한 설명"""
    securities_domains: List[str]
    """사용 가능한 증권사/거래소들 주소"""

    @abstractmethod
    def __init__(
        self,
        **kwargs
    ):
        """
        symbols: 종목 정보 리스트
        """
        self.symbols = []

    @abstractmethod
    async def on_real_order_receive(self, order_type: OrderCategoryType, response: Dict[str, Any]) -> None:
        """
        매매 주문 상태를 받습니다.
        """
        pass
