from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1101RequestHeader(BlockRequestHeader):
    """t1101 요청용 Header"""
    pass


class T1101ResponseHeader(BlockResponseHeader):
    """t1101 응답용 Header"""
    pass


class T1101InBlock(BaseModel):
    """
    t1101InBlock - 주식현재가호가조회 입력 블록

    종목코드로 매도/매수 10단계 호가를 조회합니다.
    시세/펀더멘탈/증권사동향이 필요하면 t1102를 사용하세요.

    Attributes:
        shcode (str): 종목코드 6자리 (예: "005930")
    """
    shcode: str
    """ 단축코드 (6자리, 예: "005930") """


class T1101Request(BaseModel):
    """
    T1101 API 요청 - 주식현재가호가조회

    Attributes:
        header (T1101RequestHeader)
        body (Dict[Literal["t1101InBlock"], T1101InBlock])
    """
    header: T1101RequestHeader = T1101RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1101",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1101InBlock"], T1101InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1101"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1101OutBlock(BaseModel):
    """
    t1101OutBlock - 주식현재가호가조회 응답 블록

    매도/매수 10단계 호가와 잔량, 직전대비, 예상체결가를 제공합니다.
    간단한 현재가/등락률/거래량도 포함하지만, PER/PBR/시가총액/증권사동향/재무실적 등
    종합 시세 정보는 포함하지 않습니다. 종합 시세가 필요하면 t1102를 사용하세요.

    ※ t1101은 호가 전용, t1102는 시세/종합정보 전용입니다.
    """
    hname: str
    """ 한글명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락) """
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
    preoffercha1: int
    """ 직전매도대비수량1 """
    prebidcha1: int
    """ 직전매수대비수량1 """
    offerho2: int
    """ 매도호가2 """
    bidho2: int
    """ 매수호가2 """
    offerrem2: int
    """ 매도호가수량2 """
    bidrem2: int
    """ 매수호가수량2 """
    preoffercha2: int
    """ 직전매도대비수량2 """
    prebidcha2: int
    """ 직전매수대비수량2 """
    offerho3: int
    """ 매도호가3 """
    bidho3: int
    """ 매수호가3 """
    offerrem3: int
    """ 매도호가수량3 """
    bidrem3: int
    """ 매수호가수량3 """
    preoffercha3: int
    """ 직전매도대비수량3 """
    prebidcha3: int
    """ 직전매수대비수량3 """
    offerho4: int
    """ 매도호가4 """
    bidho4: int
    """ 매수호가4 """
    offerrem4: int
    """ 매도호가수량4 """
    bidrem4: int
    """ 매수호가수량4 """
    preoffercha4: int
    """ 직전매도대비수량4 """
    prebidcha4: int
    """ 직전매수대비수량4 """
    offerho5: int
    """ 매도호가5 """
    bidho5: int
    """ 매수호가5 """
    offerrem5: int
    """ 매도호가수량5 """
    bidrem5: int
    """ 매수호가수량5 """
    preoffercha5: int
    """ 직전매도대비수량5 """
    prebidcha5: int
    """ 직전매수대비수량5 """
    offerho6: int
    """ 매도호가6 """
    bidho6: int
    """ 매수호가6 """
    offerrem6: int
    """ 매도호가수량6 """
    bidrem6: int
    """ 매수호가수량6 """
    preoffercha6: int
    """ 직전매도대비수량6 """
    prebidcha6: int
    """ 직전매수대비수량6 """
    offerho7: int
    """ 매도호가7 """
    bidho7: int
    """ 매수호가7 """
    offerrem7: int
    """ 매도호가수량7 """
    bidrem7: int
    """ 매수호가수량7 """
    preoffercha7: int
    """ 직전매도대비수량7 """
    prebidcha7: int
    """ 직전매수대비수량7 """
    offerho8: int
    """ 매도호가8 """
    bidho8: int
    """ 매수호가8 """
    offerrem8: int
    """ 매도호가수량8 """
    bidrem8: int
    """ 매수호가수량8 """
    preoffercha8: int
    """ 직전매도대비수량8 """
    prebidcha8: int
    """ 직전매수대비수량8 """
    offerho9: int
    """ 매도호가9 """
    bidho9: int
    """ 매수호가9 """
    offerrem9: int
    """ 매도호가수량9 """
    bidrem9: int
    """ 매수호가수량9 """
    preoffercha9: int
    """ 직전매도대비수량9 """
    prebidcha9: int
    """ 직전매수대비수량9 """
    offerho10: int
    """ 매도호가10 """
    bidho10: int
    """ 매수호가10 """
    offerrem10: int
    """ 매도호가수량10 """
    bidrem10: int
    """ 매수호가수량10 """
    preoffercha10: int
    """ 직전매도대비수량10 """
    prebidcha10: int
    """ 직전매수대비수량10 """

    offer: int
    """ 매도호가수량합 """
    bid: int
    """ 매수호가수량합 """
    preoffercha: int
    """ 직전매도대비수량합 """
    prebidcha: int
    """ 직전매수대비수량합 """
    hotime: str
    """ 수신시간 """

    # 예상체결
    yeprice: int
    """ 예상체결가격 """
    yevolume: int
    """ 예상체결수량 """
    yesign: str
    """ 예상체결전일구분 (1:상한 2:상승 3:보합 4:하한 5:하락) """
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
    """ 동시구분 (1:장중 2:시간외 3:장전/장중/장마감 동시) """
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

    # KRX 중간가 관련
    krx_midprice: int = 0
    """ KRX중간가격 """
    krx_offermidsumrem: int = 0
    """ KRX매도중간가잔량합계수량 """
    krx_bidmidsumrem: int = 0
    """ KRX매수중간가잔량합계수량 """
    krx_midsumrem: int = 0
    """ KRX중간가잔량합계수량 """
    krx_midsumremgubun: str = ""
    """ KRX중간가잔량구분 (''없음 '1'매도 '2'매수) """


class T1101Response(BaseModel):
    """
    T1101 API 전체 응답 - 주식현재가호가조회

    매도/매수 10단계 호가, 잔량, 직전대비, 예상체결가를 반환합니다.
    종합 시세/펀더멘탈/증권사동향이 필요하면 t1102를 사용하세요.

    Attributes:
        header (Optional[T1101ResponseHeader])
        block (Optional[T1101OutBlock]): 호가 데이터 (10단계)
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[T1101ResponseHeader]
    block: Optional[T1101OutBlock] = Field(
        None,
        title="호가 데이터",
        description="주식현재가호가조회 결과 - 매도/매수 10단계 호가 및 잔량"
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
