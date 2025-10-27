from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, TypedDict, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .system import DpsTyped

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


class SymbolInfoBase(TypedDict, total=False):
    """Symbol shared fields across overseas products."""

    symbol: str
    """종목 코드"""

    product_type: Optional[Literal["overseas_stock", "overseas_futures"]]
    """종목이 속한 상품 유형"""

    symbol_name: Optional[str]
    """종목명"""

    additional: Optional[Dict[str, Any]]
    """추가 필드 (확장 용도)"""


class SymbolInfoOverseasStock(SymbolInfoBase, total=False):
    """해외주식 종목 정보를 담는 타입"""

    product_type: Optional[Literal["overseas_stock"]]
    """해외주식 상품 유형 식별자"""

    exchcd: Literal["81", "82"]
    """거래소 코드 (해외주식: 81: 뉴욕,아멕스 / 82: 나스닥)"""

    mcap: Optional[float]
    """시가총액 (단위: 백만 달러)"""

    OrdNo: Optional[int]
    """주문번호 (미체결/정정/취소용)"""


class SymbolInfoOverseasFutures(SymbolInfoBase, total=False):
    """해외선물 종목 정보를 담는 타입"""

    product_type: Optional[Literal["overseas_futures"]]
    """해외선물 상품 유형 식별자"""

    exchcd: Optional[str]
    """거래소 코드 (예: CME, NYMEX 등)"""

    due_yymm: Optional[str]
    """해외선물 만기년월"""

    prdt_code: Optional[str]
    """상품코드"""

    currency_code: Optional[str]
    """통화 코드"""

    contract_size: Optional[float]
    """계약 단위"""


class HeldSymbolOverseasStock(TypedDict):
    """해외주식 보유 종목 잔고 정보"""

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


class HeldSymbolOverseasFutures(TypedDict, total=False):
    """해외선물 보유(포지션) 잔고 정보"""

    IsuCodeVal: str
    """종목코드값"""
    IsuNm: str
    """종목명"""
    BnsTpCode: str
    """매매구분코드"""
    BalQty: float
    """잔고수량"""
    OrdAbleAmt: float
    """주문가능금액"""
    DueDt: str
    """만기일자"""
    OvrsDrvtNowPrc: float
    """해외파생현재가"""
    AbrdFutsEvalPnlAmt: float
    """해외선물평가손익금액"""
    PchsPrc: float
    """매입가격"""
    CrcyCodeVal: str
    """통화코드값"""
    PosNo: str
    """포지션번호"""
    MaintMgn: float
    """유지증거금"""
    CsgnMgn: float
    """위탁증거금액"""


HeldSymbol = Union[HeldSymbolOverseasStock, HeldSymbolOverseasFutures]
"""통합 보유 잔고 정보 타입 (해외주식/해외선물)"""


class NonTradedSymbolOverseasStock(TypedDict):
    """해외주식 미체결 주문 정보"""

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


class NonTradedSymbolOverseasFutures(TypedDict, total=False):
    """해외선물 미체결 주문 정보"""

    OvrsFutsOrdNo: str
    """해외선물주문번호"""
    OvrsFutsOrgOrdNo: str
    """해외선물원주문번호"""
    FcmOrdNo: str
    """FCM주문번호"""
    IsuCodeVal: str
    """종목코드값"""
    IsuNm: str
    """종목명"""
    BnsTpCode: str
    """매매구분코드"""
    FutsOrdStatCode: str
    """선물주문상태코드"""
    FutsOrdTpCode: str
    """선물주문구분코드"""
    AbrdFutsOrdPtnCode: str
    """해외선물주문유형코드"""
    OrdQty: int
    """주문수량"""
    ExecQty: int
    """체결수량"""
    UnercQty: int
    """미체결수량"""
    OvrsDrvtOrdPrc: float
    """해외파생주문가격"""
    OrdDt: str
    """주문일자"""
    OrdTime: str
    """주문시각"""
    CvrgYn: str
    """반대매매여부"""
    ExecBnsTpCode: str
    """체결매매구분코드"""
    FcmAcntNo: str
    """FCM계좌번호"""


NonTradedSymbol = Union[NonTradedSymbolOverseasStock, NonTradedSymbolOverseasFutures]
"""통합 미체결 주문 정보 타입 (해외주식/해외선물)"""


SymbolInfoType = TypeVar("SymbolInfoType", SymbolInfoOverseasStock, SymbolInfoOverseasFutures)
OrderResGenericT = TypeVar("OrderResGenericType", bound=Dict[str, Any])


class BaseOrderOverseas(Generic[OrderResGenericT, SymbolInfoType], ABC):
    """
    해외상품 매매 주문을 위한 기본 전략 클래스
    """

    product: Literal["overseas_stock", "overseas_futures"]
    """전략이 동작하는 상품 유형"""

    id: str
    """전략의 고유 ID"""

    description: str
    """전략에 대한 설명"""

    securities: List[str]
    """이 전략에서 사용되는 증권사들"""

    order_types: List[OrderType]
    """이 전략이 지원하는 주문 유형들"""

    @abstractmethod
    def __init__(self) -> None:
        self.available_symbols: List[SymbolInfoType] = []
        """ 매매 전략에 사용하려는 신규 종목들입니다. """
        self.held_symbols: List[HeldSymbol] = []
        """ 보유종목 리스트입니다. """
        self.non_traded_symbols: List[NonTradedSymbol] = []
        """ 미체결 종목 리스트입니다. """
        self.dps: Optional[List[DpsTyped]] = None
        """ USD 예수금만 지원합니다. """
        self.system_id: Optional[str] = None
        """ 시스템 식별 ID 입니다. """

    @abstractmethod
    async def execute(self) -> List[OrderResGenericT]:
        """전략을 실행하고 주문에 사용할 정보를 반환합니다."""
        raise NotImplementedError()

    def _set_system_id(self, system_id: Optional[str]) -> None:
        """시스템 고유 ID를 설정합니다."""
        self.system_id = system_id

    def _set_available_symbols(self, symbols: List[SymbolInfoType]) -> None:
        """매매 전략 계산에 사용하려는 종목들을 전달합니다."""
        self.available_symbols = symbols

    def _set_held_symbols(self, symbols: List[HeldSymbol]) -> None:
        """현재 보유중인 종목들을 받습니다."""
        self.held_symbols = symbols

    def _set_non_traded_symbols(self, symbols: List[NonTradedSymbol]) -> None:
        """현재 미체결 종목들을 받습니다."""
        self.non_traded_symbols = symbols

    def _set_available_balance(
        self,
        dps: Optional[List[DpsTyped]],
    ) -> None:
        """
        사용 가능한 잔고를 설정합니다.

        Args:
            dps (List[DpsTyped]): 외화 예금 또는 예수금
        """
        self.dps = dps

    @abstractmethod
    async def on_real_order_receive(self, order_type: OrderRealResponseType, response: OrderResGenericT) -> None:
        """매매 주문 상태를 받습니다."""
        raise NotImplementedError()


class BaseOrderOverseasStock(BaseOrderOverseas[OrderResGenericT, SymbolInfoOverseasStock], ABC):
    """해외주식 매매 주문을 위한 기본 전략 클래스"""

    product: Literal["overseas_stock"] = "overseas_stock"


class BaseOrderOverseasFutures(BaseOrderOverseas[OrderResGenericT, SymbolInfoOverseasFutures], ABC):
    """해외선물 매매 주문을 위한 기본 전략 클래스"""
    product: Literal["overseas_futures"] = "overseas_futures"
