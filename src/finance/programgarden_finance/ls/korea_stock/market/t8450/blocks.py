from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8450RequestHeader(BlockRequestHeader):
    """t8450 요청용 Header"""
    pass


class T8450ResponseHeader(BlockResponseHeader):
    """t8450 응답용 Header"""
    pass


class T8450InBlock(BaseModel):
    """
    t8450InBlock 입력 블록

    Attributes:
        shcode (str): 단축코드 (6자리)
        exchgubun (str): 거래소구분코드 (K: KRX, N: NXT, U: 통합)
    """
    shcode: str
    """ 단축코드 """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K: KRX, N: NXT, U: 통합, 그외: KRX로 처리) """


class T8450Request(BaseModel):
    """
    T8450 API 요청

    Attributes:
        header (T8450RequestHeader)
        body (Dict[Literal["t8450InBlock"], T8450InBlock])
    """
    header: T8450RequestHeader = T8450RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8450",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t8450InBlock"], T8450InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t8450"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T8450OutBlock(BaseModel):
    """
    t8450OutBlock 응답 블록 (주식현재가호가조회2)

    Attributes:
        hname (str): 한글명
        price (int): 현재가
        sign (str): 전일대비구분
        change (int): 전일대비
        diff (float): 등락율
        volume (int): 누적거래량
        jnilclose (int): 전일종가(기준가)
        offerho1~10 (int): 매도호가1~10
        bidho1~10 (int): 매수호가1~10
        offerrem1~10 (int): 매도호가수량1~10
        bidrem1~10 (int): 매수호가수량1~10
        offer (int): 매도호가수량합
        bid (int): 매수호가수량합
        hotime (str): 수신시간
        shcode (str): 단축코드
        uplmtprice (int): 상한가
        dnlmtprice (int): 하한가
        open (int): 시가
        high (int): 고가
        low (int): 저가
    """
    hname: str
    """ 한글명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 """
    change: int
    """ 전일대비 """
    diff: float
    """ 등락율 """
    volume: int
    """ 누적거래량 """
    jnilclose: int
    """ 전일종가(기준가) """

    # 매도/매수 호가 1~10
    offerho1: int
    """ 매도호가1 """
    bidho1: int
    """ 매수호가1 """
    offerrem1: int
    """ 매도호가수량1 """
    bidrem1: int
    """ 매수호가수량1 """
    offerho2: int
    """ 매도호가2 """
    bidho2: int
    """ 매수호가2 """
    offerrem2: int
    """ 매도호가수량2 """
    bidrem2: int
    """ 매수호가수량2 """
    offerho3: int
    """ 매도호가3 """
    bidho3: int
    """ 매수호가3 """
    offerrem3: int
    """ 매도호가수량3 """
    bidrem3: int
    """ 매수호가수량3 """
    offerho4: int
    """ 매도호가4 """
    bidho4: int
    """ 매수호가4 """
    offerrem4: int
    """ 매도호가수량4 """
    bidrem4: int
    """ 매수호가수량4 """
    offerho5: int
    """ 매도호가5 """
    bidho5: int
    """ 매수호가5 """
    offerrem5: int
    """ 매도호가수량5 """
    bidrem5: int
    """ 매수호가수량5 """
    offerho6: int
    """ 매도호가6 """
    bidho6: int
    """ 매수호가6 """
    offerrem6: int
    """ 매도호가수량6 """
    bidrem6: int
    """ 매수호가수량6 """
    offerho7: int
    """ 매도호가7 """
    bidho7: int
    """ 매수호가7 """
    offerrem7: int
    """ 매도호가수량7 """
    bidrem7: int
    """ 매수호가수량7 """
    offerho8: int
    """ 매도호가8 """
    bidho8: int
    """ 매수호가8 """
    offerrem8: int
    """ 매도호가수량8 """
    bidrem8: int
    """ 매수호가수량8 """
    offerho9: int
    """ 매도호가9 """
    bidho9: int
    """ 매수호가9 """
    offerrem9: int
    """ 매도호가수량9 """
    bidrem9: int
    """ 매수호가수량9 """
    offerho10: int
    """ 매도호가10 """
    bidho10: int
    """ 매수호가10 """
    offerrem10: int
    """ 매도호가수량10 """
    bidrem10: int
    """ 매수호가수량10 """

    offer: int
    """ 매도호가수량합 """
    bid: int
    """ 매수호가수량합 """
    hotime: str
    """ 수신시간 """

    # 예상체결
    yeprice: int
    """ 예상체결가격 """
    yevolume: int
    """ 예상체결수량 """
    yesign: str
    """ 예상체결전일구분 """
    yechange: int
    """ 예상체결전일대비 """
    yediff: float
    """ 예상체결등락율 """

    # 시간외
    tmoffer: int
    """ 시간외매도잔량 """
    tmbid: int
    """ 시간외매수잔량 """

    ho_status: str
    """ 동시구분 """
    shcode: str
    """ 단축코드 """
    uplmtprice: int
    """ 상한가 """
    dnlmtprice: int
    """ 하한가 """
    open: int
    """ 시가 """
    high: int
    """ 고가 """
    low: int
    """ 저가 """

    # NXT 호가수량 1~10
    nxt_offerrem1: int = 0
    """ NXT매도호가수량1 """
    nxt_bidrem1: int = 0
    """ NXT매수호가수량1 """
    nxt_offerrem2: int = 0
    """ NXT매도호가수량2 """
    nxt_bidrem2: int = 0
    """ NXT매수호가수량2 """
    nxt_offerrem3: int = 0
    """ NXT매도호가수량3 """
    nxt_bidrem3: int = 0
    """ NXT매수호가수량3 """
    nxt_offerrem4: int = 0
    """ NXT매도호가수량4 """
    nxt_bidrem4: int = 0
    """ NXT매수호가수량4 """
    nxt_offerrem5: int = 0
    """ NXT매도호가수량5 """
    nxt_bidrem5: int = 0
    """ NXT매수호가수량5 """
    nxt_offerrem6: int = 0
    """ NXT매도호가수량6 """
    nxt_bidrem6: int = 0
    """ NXT매수호가수량6 """
    nxt_offerrem7: int = 0
    """ NXT매도호가수량7 """
    nxt_bidrem7: int = 0
    """ NXT매수호가수량7 """
    nxt_offerrem8: int = 0
    """ NXT매도호가수량8 """
    nxt_bidrem8: int = 0
    """ NXT매수호가수량8 """
    nxt_offerrem9: int = 0
    """ NXT매도호가수량9 """
    nxt_bidrem9: int = 0
    """ NXT매수호가수량9 """
    nxt_offerrem10: int = 0
    """ NXT매도호가수량10 """
    nxt_bidrem10: int = 0
    """ NXT매수호가수량10 """

    nxt_offer: int = 0
    """ NXT매도호가수량합 """
    nxt_bid: int = 0
    """ NXT매수호가수량합 """
    nxt_yeprice: int = 0
    """ NXT예상체결가격 """
    nxt_yevolume: int = 0
    """ NXT예상체결수량 """
    nxt_yesign: str = ""
    """ NXT예상체결전일구분 """
    nxt_yechange: int = 0
    """ NXT예상체결전일대비 """
    nxt_yediff: float = 0.0
    """ NXT예상체결등락율 """
    nxt_ho_status: str = ""
    """ NXT동시구분 """

    # 통합 호가수량 1~10
    unx_offerrem1: int = 0
    """ 통합매도호가수량1 """
    unx_bidrem1: int = 0
    """ 통합매수호가수량1 """
    unx_offerrem2: int = 0
    """ 통합매도호가수량2 """
    unx_bidrem2: int = 0
    """ 통합매수호가수량2 """
    unx_offerrem3: int = 0
    """ 통합매도호가수량3 """
    unx_bidrem3: int = 0
    """ 통합매수호가수량3 """
    unx_offerrem4: int = 0
    """ 통합매도호가수량4 """
    unx_bidrem4: int = 0
    """ 통합매수호가수량4 """
    unx_offerrem5: int = 0
    """ 통합매도호가수량5 """
    unx_bidrem5: int = 0
    """ 통합매수호가수량5 """
    unx_offerrem6: int = 0
    """ 통합매도호가수량6 """
    unx_bidrem6: int = 0
    """ 통합매수호가수량6 """
    unx_offerrem7: int = 0
    """ 통합매도호가수량7 """
    unx_bidrem7: int = 0
    """ 통합매수호가수량7 """
    unx_offerrem8: int = 0
    """ 통합매도호가수량8 """
    unx_bidrem8: int = 0
    """ 통합매수호가수량8 """
    unx_offerrem9: int = 0
    """ 통합매도호가수량9 """
    unx_bidrem9: int = 0
    """ 통합매수호가수량9 """
    unx_offerrem10: int = 0
    """ 통합매도호가수량10 """
    unx_bidrem10: int = 0
    """ 통합매수호가수량10 """

    unx_offer: int = 0
    """ 통합매도호가수량합 """
    unx_bid: int = 0
    """ 통합매수호가수량합 """

    # KRX/NXT 중간가 관련
    krx_midprice: int = 0
    """ KRX중간가격 """
    krx_offermidsumrem: int = 0
    """ KRX매도중간가잔량합계수량 """
    krx_bidmidsumrem: int = 0
    """ KRX매수중간가잔량합계수량 """
    nxt_midprice: int = 0
    """ NXT중간가격 """
    nxt_offermidsumrem: int = 0
    """ NXT매도중간가잔량합계수량 """
    nxt_bidmidsumrem: int = 0
    """ NXT매수중간가잔량합계수량 """

    ex_shcode: str = ""
    """ 거래소별단축코드 """
    krx_midsumrem: int = 0
    """ KRX중간가잔량합계수량 """
    krx_midsumremgubun: str = ""
    """ KRX중간가잔량구분 (''없음 '1'매도 '2'매수) """
    nxt_midsumrem: int = 0
    """ NXT중간가잔량합계수량 """
    nxt_midsumremgubun: str = ""
    """ NXT중간가잔량구분 (''없음 '1'매도 '2'매수) """


class T8450Response(BaseModel):
    """
    T8450 API 전체 응답

    Attributes:
        header (Optional[T8450ResponseHeader])
        block (Optional[T8450OutBlock]): 호가 데이터
        rsp_cd (str)
        rsp_msg (str)
        error_msg (Optional[str])
    """
    header: Optional[T8450ResponseHeader]
    block: Optional[T8450OutBlock] = Field(
        None,
        title="호가 데이터",
        description="주식현재가호가조회2 결과"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지",
        description="오류메시지 (있으면)"
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
