from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3136RequestHeader(BlockRequestHeader):
    pass


class O3136ResponseHeader(BlockResponseHeader):
    pass


class O3136InBlock(BaseModel):
    """
    o3136InBlock 입력 블록

    Attributes:
        gubun (Literal["0", "1"]): 조회구분 (0: 당일, 1: 전일)
        mktgb (Literal["F", "O"]): 시장구분 (F: 선물, O: 옵션)
        shcode (str): 단축코드
        readcnt (int): 조회갯수
        cts_seq (int): 순번CTS
    """
    gubun: Literal["0", "1"] = Field(..., title="조회구분", description="조회구분 (0:당일, 1:전일)")
    """조회구분 (0:당일, 1:전일)"""
    mktgb: Literal["F", "O"] = Field(..., title="시장구분", description="시장구분 (F:선물, O:옵션)")
    """시장구분 (F:선물, O:옵션)"""
    shcode: str = Field(..., title="단축코드", description="단축코드")
    """단축코드"""
    readcnt: int = Field(..., le=100, title="조회갯수", description="조회갯수 (최대: 100)")
    """조회갯수 (최대: 100)"""
    cts_seq: int = Field(0, title="순번CTS", description="순번CTS")
    """순번CTS"""


class O3136Request(BaseModel):
    header: O3136RequestHeader = O3136RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3136",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3136InBlock"], O3136InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3136InBlock')"
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3136"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )


class O3136OutBlock(BaseModel):
    """
    o3136OutBlock 응답 기본 블록
    """
    cts_seq: int = Field(
        default=0,
        title="순번CTS",
        description="순번CTS (연속 조회용 시퀀스)"
    )


class O3136OutBlock1(BaseModel):
    """
    o3136OutBlock1 리스트 항목

    Attributes:
        ovsdate (str): 현지일자 (YYYYMMDD)
        ovstime (str): 현지시간 (HHMMSS)
        price (float): 현재가
        sign (str): 전일대비구분
        change (float): 전일대비
        diff (float): 등락율
        cvolume (int): 체결수량
        volume (int): 누적거래량
    """
    ovsdate: str = Field(default="", title="현지일자", description="현지일자 (YYYYMMDD)")
    """현지일자 (YYYYMMDD)"""
    ovstime: str = Field(default="", title="현지시간", description="현지시간 (HHMMSS)")
    """현지시간 (HHMMSS)"""
    price: float = Field(default=0.0, title="현재가", description="현재가")
    """현재가"""
    sign: str = Field(default="", title="전일대비구분", description="전일대비구분")
    """전일대비구분"""
    change: float = Field(default=0.0, title="전일대비", description="전일대비")
    """전일대비"""
    diff: float = Field(default=0.0, title="등락율", description="등락율")
    """등락율"""
    cvolume: int = Field(default=0, title="체결수량", description="체결수량")
    """체결수량"""
    volume: int = Field(default=0, title="누적거래량", description="누적거래량")
    """누적거래량"""


class O3136Response(BaseModel):
    header: Optional[O3136ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: Optional[O3136OutBlock] = Field(
        None,
        title="기본 응답 블록",
        description="기본 응답 블록"
    )
    block1: List[O3136OutBlock1] = Field(
        ...,
        title="상세 리스트",
        description="상세 리스트 (여러 레코드)"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    rsp_cd: str = Field(..., title="응답코드", description="응답코드")
    rsp_msg: str = Field(..., title="응답메시지", description="응답메시지")
    error_msg: Optional[str] = Field(None, title="오류메시지", description="오류메시지 (있으면)")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
