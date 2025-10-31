
from typing import Literal, TypedDict

from programgarden_core.bases.base import BaseOrderOverseasStock, BaseOrderOverseasFutures


class BaseCancelOrderOverseasStockResponseType(TypedDict):
    """주문을 넣기 위한 반환값 데이터"""
    success: bool
    """전략 통과 성공 여부"""
    ord_ptn_code: Literal["08"]
    """주문유형코드 (08: 취소주문)"""
    org_ord_no: str
    """원주문번호"""
    ord_mkt_code: Literal["81", "82"]
    """주문시장코드 (81: 뉴욕거래소, 82: NASDAQ)"""
    shtn_isu_no: str
    """종목번호 (단축종목코드 ex.TSLA)"""
    ord_qty: int
    """주문수량"""
    ovrs_ord_prc: float = 0.0
    """해외주문가"""
    ordprc_ptn_code: Literal["00", "M1", "M2", "03", "M3", "M4"]
    """호가유형코드 (00: 지정가, M1: LOO, M2: LOC, 03: 시장가, M3: MOO, M4: MOC)"""
    bns_tp_code: Literal["1", "2"]
    """매매구분코드 (1: 매도, 2: 매수)"""
    brk_tp_code: str = ""
    """중개인코드"""


class BaseCancelOrderOverseasStock(BaseOrderOverseasStock[BaseCancelOrderOverseasStockResponseType]):
    """
    취소 주문을 하기 위한 전략을 계산하고 주문을 위한 값을 던져줍니다.
    """
    product = "overseas_stock"


class BaseCancelOrderOverseasFuturesResponseType(TypedDict, total=False):
    """해외선물 취소주문을 넣기 위한 반환값 데이터"""

    success: bool
    """전략 통과 성공 여부"""

    ord_dt: str
    """주문일자 (YYYYMMDD)"""

    isu_code_val: str
    """종목코드값"""

    ovrs_futs_org_ord_no: str
    """해외선물 원주문번호"""

    futs_ord_tp_code: Literal["3"]
    """선물주문구분코드 (3: 취소)"""

    prdt_tp_code: str = ""
    """상품구분코드 (빈값으로)"""

    exch_code: str = ""
    """거래소코드 (빈값으로 해도됨), 모의투자는 HKEX 고정"""


class BaseCancelOrderOverseasFutures(BaseOrderOverseasFutures[BaseCancelOrderOverseasFuturesResponseType]):
    """해외선물 취소 주문 전략 기본 클래스"""

    product = "overseas_futures"
