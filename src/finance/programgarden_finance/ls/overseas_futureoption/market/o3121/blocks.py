from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3121RequestHeader(BlockRequestHeader):
    pass


class O3121ResponseHeader(BlockResponseHeader):
    pass


class O3121InBlock(BaseModel):
    """
    o3121InBlock 데이터 블록

    Attributes:
        MktGb (str): 시장구분 (F: 선물, O: 옵션)
        BscGdsCd (str): 옵션기초상품코드, ['시장구분' 옵션의 경우] 공란(옵션상품 목록), O_ES(ES상품옵션종목 목록)
    """
    MktGb: Optional[Literal["F", "O"]] = Field(
        title="시장구분",
        description="시장구분 (F: 선물, O: 옵션)"
    )
    BscGdsCd: Optional[str] = Field(
        title="옵션기초상품코드",
        description="['시장구분' 옵션의 경우] 공란(옵션상품 목록), O_ES(ES상품옵션종목 목록)"
    )


class O3121Request(BaseModel):
    """
    o3121 API 요청 전체 구조
    """
    header: O3121RequestHeader = O3121RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3121",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3121InBlock"], O3121InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3121InBlock')"
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3121"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3121OutBlock(BaseModel):
    """
    o3121OutBlock 데이터 블록 리스트 항목
    """
    Symbol: str = Field(default="", title="종목코드", description="종목코드")
    """종목코드"""
    SymbolNm: str = Field(default="", title="종목명", description="종목명")
    """종목명"""
    ApplDate: str = Field(default="", title="종목배치수신일(한국일자)", description="종목배치수신일(한국일자)")
    """종목배치수신일(한국일자)"""
    BscGdsCd: str = Field(default="", title="기초상품코드", description="기초상품코드")
    """기초상품코드"""
    BscGdsNm: str = Field(default="", title="기초상품명", description="기초상품명")
    """기초상품명"""
    ExchCd: str = Field(default="", title="거래소코드", description="거래소코드")
    """거래소코드"""
    ExchNm: str = Field(default="", title="거래소명", description="거래소명")
    """거래소명"""
    CrncyCd: str = Field(default="", title="기준통화코드", description="기준통화코드")
    """기준통화코드"""
    NotaCd: str = Field(default="", title="진법구분코드", description="진법구분코드")
    """진법구분코드"""
    UntPrc: float = Field(default=0.0, title="호가단위가격", description="호가단위가격")
    """호가단위가격"""
    MnChgAmt: float = Field(default=0.0, title="최소가격변동금액", description="최소가격변동금액")
    """최소가격변동금액"""
    RgltFctr: float = Field(default=0.0, title="가격조정계수", description="가격조정계수")
    """가격조정계수"""
    CtrtPrAmt: float = Field(default=0.0, title="계약당금액", description="계약당금액")
    """계약당금액"""
    GdsCd: str = Field(default="", title="상품구분코드", description="상품구분코드")
    """상품구분코드"""
    LstngYr: str = Field(default="", title="월물(년)", description="월물(년)")
    """월물(년)"""
    LstngM: str = Field(default="", title="월물(월)", description="월물(월)")
    """월물(월)"""
    EcPrc: float = Field(default=0.0, title="정산가격", description="정산가격")
    """정산가격"""
    DlStrtTm: str = Field(default="", title="거래시작시간", description="거래시작시간")
    """거래시작시간"""
    DlEndTm: str = Field(default="", title="거래종료시간", description="거래종료시간")
    """거래종료시간"""
    DlPsblCd: str = Field(default="", title="거래가능구분코드", description="거래가능구분코드")
    """거래가능구분코드"""
    MgnCltCd: str = Field(default="", title="증거금징수구분코드", description="증거금징수구분코드")
    """증거금징수구분코드"""
    OpngMgn: float = Field(default=0.0, title="개시증거금", description="개시증거금")
    """개시증거금"""
    MntncMgn: float = Field(default=0.0, title="유지증거금", description="유지증거금")
    """유지증거금"""
    OpngMgnR: float = Field(default=0.0, title="개시증거금율", description="개시증거금율")
    """개시증거금율"""
    MntncMgnR: float = Field(default=0.0, title="유지증거금율", description="유지증거금율")
    """유지증거금율"""
    DotGb: int = Field(default=0, title="유효소수점자리수", description="유효소수점자리수")
    """유효소수점자리수"""
    XrcPrc: str = Field(default="", title="옵션행사가", description="옵션행사가")
    """옵션행사가"""
    FdasBasePrc: str = Field(default="", title="기초자산기준가격", description="기초자산기준가격")
    """기초자산기준가격"""
    OptTpCode: str = Field(default="", title="옵션콜풋구분", description="옵션콜풋구분")
    """옵션콜풋구분"""
    RgtXrcPtnCode: str = Field(default="", title="권리행사구분코드", description="권리행사구분코드")
    """권리행사구분코드"""
    Moneyness: str = Field(default="", title="ATM구분", description="ATM구분")
    """ATM구분"""
    LastSettPtnCode: str = Field(default="", title="해외파생기초자산종목코드", description="해외파생기초자산종목코드")
    """해외파생기초자산종목코드"""
    OptMinOrcPrc: str = Field(default="", title="해외옵션최소호가", description="해외옵션최소호가")
    """해외옵션최소호가"""
    OptMinBaseOrcPrc: str = Field(default="", title="해외옵션최소기준호가", description="해외옵션최소기준호가")
    """해외옵션최소기준호가"""


class O3121Response(BaseModel):
    """
    O3121 API 응답 전체 구조
    """
    header: Optional[O3121ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: List[O3121OutBlock] = Field(
        ...,
        title="출력 블록 리스트",
        description="O3121 응답의 출력 블록 리스트"
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
