from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3101RequestHeader(BlockRequestHeader):
    pass


class O3101ResponseHeader(BlockResponseHeader):
    pass


class O3101InBlock(BaseModel):
    """
    o3101InBlock 데이터 블록

    Attributes:
        gubun (str): 입력구분
    """
    gubun: str = Field(
        ...,
        title="입력구분",
        description="입력구분"
    )


class O3101Request(BaseModel):
    """
    o3101 API 요청 전체 구조
    """
    header: O3101RequestHeader = O3101RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3101",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3101InBlock"], O3101InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3101InBlock')"
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3101"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3101OutBlock(BaseModel):
    """
    o3101OutBlock 데이터 블록 리스트 항목

    Attributes:
        Symbol (str): 종목코드
        SymbolNm (str): 종목명
        ApplDate (str): 종목배치수신일(YYYYMMDD)
        BscGdsCd (str): 기초상품코드
        BscGdsNm (str): 기초상품명
        ExchCd (str): 거래소코드
        ExchNm (str): 거래소명
        CrncyCd (str): 기준통화코드
        NotaCd (str): 진법구분코드
        UntPrc (str): 호가단위가격
        MnChgAmt (str): 최소가격변동금액
        RgltFctr (str): 가격조정계수
        CtrtPrAmt (str): 계약당금액
        GdsCd (str): 상품구분코드
        LstngYr (str): 월물(년)
        LstngM (str): 월물(월)
        EcPrc (str): 정산가격
        DlStrtTm (str): 거래시작시간(HHMMSS)
        DlEndTm (str): 거래종료시간(HHMMSS)
        DlPsblCd (str): 거래가능구분코드
        MgnCltCd (str): 증거금징수구분코드
        OpngMgn (str): 개시증거금
        MntncMgn (str): 유지증거금
        OpngMgnR (str): 개시증거금율
        MntncMgnR (str): 유지증거금율
        DotGb (int): 유효소수점자리수
    """
    Symbol: str = Field(
        default="",
        title="종목코드",
        description="종목코드"
    )
    """종목코드"""
    SymbolNm: str = Field(
        default="",
        title="종목명",
        description="종목명"
    )
    """종목명"""
    ApplDate: str = Field(
        default="",
        title="종목배치수신일",
        description="종목배치수신일(YYYYMMDD)"
    )
    """종목배치수신일(YYYYMMDD)"""
    BscGdsCd: str = Field(
        default="",
        title="기초상품코드",
        description="기초상품코드"
    )
    """기초상품코드"""
    BscGdsNm: str = Field(
        default="",
        title="기초상품명",
        description="기초상품명"
    )
    """기초상품명"""
    ExchCd: str = Field(
        default="",
        title="거래소코드",
        description="거래소코드"
    )
    """거래소코드"""
    ExchNm: str = Field(
        default="",
        title="거래소명",
        description="거래소명"
    )
    """거래소명"""
    CrncyCd: str = Field(
        default="",
        title="기준통화코드",
        description="기준통화코드"
    )
    """기준통화코드"""
    NotaCd: str = Field(
        default="",
        title="진법구분코드",
        description="진법구분코드"
    )
    """진법구분코드"""
    UntPrc: str = Field(
        default="",
        title="호가단위가격",
        description="호가단위가격"
    )
    """호가단위가격"""
    MnChgAmt: str = Field(
        default="",
        title="최소가격변동금액",
        description="최소가격변동금액"
    )
    """최소가격변동금액"""
    RgltFctr: str = Field(
        default="",
        title="가격조정계수",
        description="가격조정계수"
    )
    """가격조정계수"""
    CtrtPrAmt: str = Field(
        default="",
        title="계약당금액",
        description="계약당금액"
    )
    """계약당금액"""
    GdsCd: str = Field(
        default="",
        title="상품구분코드",
        description="상품구분코드"
    )
    """상품구분코드"""
    LstngYr: str = Field(
        default="",
        title="월물(년)",
        description="월물(년)"
    )
    """월물(년)"""
    LstngM: str = Field(
        default="",
        title="월물(월)",
        description="월물(월)"
    )
    """월물(월)"""
    EcPrc: str = Field(
        default="",
        title="정산가격",
        description="정산가격"
    )
    """정산가격"""
    DlStrtTm: str = Field(
        default="",
        title="거래시작시간",
        description="거래시작시간(HHMMSS)"
    )
    """거래시작시간(HHMMSS)"""
    DlEndTm: str = Field(
        default="",
        title="거래종료시간",
        description="거래종료시간(HHMMSS)"
    )
    """거래종료시간(HHMMSS)"""
    DlPsblCd: str = Field(
        default="",
        title="거래가능구분코드",
        description="거래가능구분코드"
    )
    """거래가능구분코드"""
    MgnCltCd: str = Field(
        default="",
        title="증거금징수구분코드",
        description="증거금징수구분코드"
    )
    """증거금징수구분코드"""
    OpngMgn: str = Field(
        default="",
        title="개시증거금",
        description="개시증거금"
    )
    """개시증거금"""
    MntncMgn: str = Field(
        default="",
        title="유지증거금",
        description="유지증거금"
    )
    """유지증거금"""
    OpngMgnR: str = Field(
        default="",
        title="개시증거금율",
        description="개시증거금율"
    )
    """개시증거금율"""
    MntncMgnR: str = Field(
        default="",
        title="유지증거금율",
        description="유지증거금율"
    )
    """유지증거금율"""
    DotGb: int = Field(
        default=0,
        title="유효소수점자리수",
        description="유효소수점자리수"
    )
    """유효소수점자리수"""


class O3101Response(BaseModel):
    """
    O3101 API 응답 전체 구조
    """
    header: Optional[O3101ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: List[O3101OutBlock] = Field(
        ...,
        title="출력 블록 리스트",
        description="O3101 응답의 출력 블록 리스트"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    rsp_cd: str = Field(..., title="응답 코드", description="응답 코드")
    rsp_msg: str = Field(..., title="응답 메시지", description="응답 메시지")
    error_msg: Optional[str] = Field(None, title="오류 메시지", description="오류 메시지 (있으면)")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
