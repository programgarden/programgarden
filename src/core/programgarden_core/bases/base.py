
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, TypedDict

OrderType = Literal[
    "new_buy",
    "new_sell",
    "cancel_buy",
    "cancel_sell",
    "modify_buy",
    "modify_sell"
]


OrderRealResponseType = Literal[
    "submitted_new_buy", "submitted_new_sell",
    "filled_new_buy", "filled_new_sell",
    "cancel_request_buy", "cancel_request_sell",
    "modify_buy", "modify_sell", "cancel_complete_buy", "cancel_complete_sell",
    "reject_buy", "reject_sell"
]
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
    OrdNo: Optional[int] = None
    """주문번호"""


class HeldSymbol(TypedDict):
    """
    주문해서 보유중인 종목들
    """
    CrcyCode: str
    """통화코드"""
    ShtnIsuNo: str
    """단축종목번호"""
    AstkBalQty: int
    """해외증권잔고수량"""
    AstkSellAbleQty: int
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
    """주문시각 (
    HHMMSSmmm
    HH → 시 (00-23)
    MM → 분 (00-59)
    SS → 초 (00-59)
    mmm → 밀리초 (000-999))"""
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
    """이 전략에서 사용되는 증권사들"""
    order_types: List[OrderType]
    """이 전략이 지원하는 주문 유형들"""

    @abstractmethod
    def __init__(
        self,
    ):
        self.available_symbols = []
        self.fcurr_dps = 0.0
        self.fcurr_ord_able_amt = 0.0

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

    @abstractmethod
    async def on_real_order_receive(self, order_type: OrderRealResponseType, response: OrderResGenericT) -> None:
        """
        매매 주문 상태를 받습니다.
        """
        pass
