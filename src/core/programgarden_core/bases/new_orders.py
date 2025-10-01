
from typing import Literal, TypedDict

from programgarden_core.bases.base import BaseOrderOverseasStock


class BaseNewOrderOverseasStockResponseType(TypedDict):
    """주문을 넣기 위한 반환값 데이터"""
    success: bool
    """전략 통과 성공 여부"""
    ord_ptn_code: Literal["01", "02"]
    """주문유형코드 (01: 매도주문, 02: 매수주문)"""
    ord_mkt_code: Literal["81", "82"]
    """주문시장코드 (81: 뉴욕거래소, 82: NASDAQ)"""
    shtn_isu_no: str
    """종목번호 (단축종목코드 ex.TSLA)"""
    ord_qty: int
    """주문수량"""
    ovrs_ord_prc: float
    """해외주문가"""
    ordprc_ptn_code: Literal["00", "M1", "M2", "03", "M3", "M4"]
    """호가유형코드 (00: 지정가, M1: LOO, M2: LOC, 03: 시장가, M3: MOO, M4: MOC)"""
    brk_tp_code: str = ""
    """중개인코드"""
    crcy_code: str = "USD"
    """통화코드"""
    pnl_rat: float = 0.0
    """손익률"""
    pchs_amt: float = 0.0
    """매입금액"""
    bns_tp_code: Literal["1", "2"]
    """매매구분코드 (1: 매도, 2: 매수)"""


class BaseNewOrderOverseasStock(BaseOrderOverseasStock[BaseNewOrderOverseasStockResponseType]):
    """
    매수 또는 매도를 하기 위한 전략을 계산하고 주문을 위한 값을 던져줍니다.
    """
    pass
