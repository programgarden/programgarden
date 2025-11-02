from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3125RequestHeader(BlockRequestHeader):
    pass


class O3125ResponseHeader(BlockResponseHeader):
    pass


class O3125InBlock(BaseModel):
    """
    o3125InBlock 데이터 블록

    Attributes:
        mktgb (Literal["F", "O"]): 시장구분, ex) F(선물), O(옵션)
        symbol (str): 종목심볼
    """
    mktgb: Literal["F", "O"] = Field(..., title="시장구분", description="ex) F(선물), O(옵션)")
    symbol: str = Field(..., title="종목심볼", description="종목심볼 (예: 2ESF16_1915)")


class O3125Request(BaseModel):
    """
    o3125 API 요청 전체 구조
    """
    header: O3125RequestHeader = O3125RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3125",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3125InBlock"], O3125InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3125InBlock')"
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=2,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3125"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3125OutBlock(BaseModel):
    """
    o3125OutBlock 데이터 블록 리스트 항목
    """
    Symbol: str = Field(default="", title="종목코드", description="종목코드")
    """종목코드"""
    SymbolNm: str = Field(default="", title="종목명", description="종목명")
    """종목명"""
    ApplDate: str = Field(default="", title="종목배치수신일", description="종목배치수신일(YYYYMMDD)")
    """종목배치수신일(YYYYMMDD)"""
    BscGdsCd: str = Field(default="", title="기초상품코드", description="기초상품코드")
    """기초상품코드"""
    BscGdsNm: str = Field(default="", title="기초상품명", description="기초상품명")
    """기초상품명"""
    ExchCd: str = Field(default="", title="거래소코드", description="거래소코드")
    """거래소코드"""
    ExchNm: str = Field(default="", title="거래소명", description="거래소명")
    """거래소명"""
    EcCd: str = Field(default="", title="정산구분코드", description="정산구분코드")
    """정산구분코드"""
    CrncyCd: str = Field(default="", title="기준통화코드", description="기준통화코드")
    """기준통화코드"""
    NotaCd: str = Field(default="", title="진법구분코드", description="진법구분코드")
    """진법구분코드"""
    UntPrc: float = Field(default=0.0, title="호가단위가격", description="호가단위가격")
    """호가단위가격 (Number - precision 15.9)"""
    MnChgAmt: float = Field(default=0.0, title="최소가격변동금액", description="최소가격변동금액")
    """최소가격변동금액 (Number - precision 15.9)"""
    RgltFctr: float = Field(default=0.0, title="가격조정계수", description="가격조정계수")
    """가격조정계수 (Number - precision 15.10)"""
    CtrtPrAmt: float = Field(default=0.0, title="계약당금액", description="계약당금액")
    """계약당금액 (Number - precision 15.2)"""
    LstngMCnt: int = Field(default=0, title="상장개월수", description="상장개월수")
    """상장개월수"""
    GdsCd: str = Field(default="", title="상품구분코드", description="상품구분코드")
    """상품구분코드"""
    MrktCd: str = Field(default="", title="시장구분코드", description="시장구분코드")
    """시장구분코드"""
    EminiCd: str = Field(default="", title="Emini구분코드", description="Emini구분코드")
    """Emini구분코드"""
    LstngYr: str = Field(default="", title="상장년", description="상장년")
    """상장년"""
    LstngM: str = Field(default="", title="상장월", description="상장월")
    """상장월"""
    SeqNo: int = Field(default=0, title="월물순서", description="월물순서")
    """월물순서"""
    LstngDt: str = Field(default="", title="상장일자", description="상장일자")
    """상장일자"""
    MtrtDt: str = Field(default="", title="만기일자", description="만기일자")
    """만기일자"""
    FnlDlDt: str = Field(default="", title="최종거래일", description="최종거래일")
    """최종거래일"""
    FstTrsfrDt: str = Field(default="", title="최초인도통지일자", description="최초인도통지일자")
    """최초인도통지일자"""
    EcPrc: float = Field(default=0.0, title="정산가격", description="정산가격")
    """정산가격 (Number - precision 15.9)"""
    DlDt: str = Field(default="", title="거래시작일자(한국)", description="거래시작일자(한국)")
    """거래시작일자(한국)"""
    DlStrtTm: str = Field(default="", title="거래시작시간(한국)", description="거래시작시간(한국)")
    """거래시작시간(한국)"""
    DlEndTm: str = Field(default="", title="거래종료시간(한국)", description="거래종료시간(한국)")
    """거래종료시간(한국)"""
    OvsStrDay: str = Field(default="", title="거래시작일자(현지)", description="거래시작일자(현지)")
    """거래시작일자(현지)"""
    OvsStrTm: str = Field(default="", title="거래시작시간(현지)", description="거래시작시간(현지)")
    """거래시작시간(현지)"""
    OvsEndDay: str = Field(default="", title="거래종료일자(현지)", description="거래종료일자(현지)")
    """거래종료일자(현지)"""
    OvsEndTm: str = Field(default="", title="거래종료시간(현지)", description="거래종료시간(현지)")
    """거래종료시간(현지)"""
    DlPsblCd: str = Field(default="", title="거래가능구분코드", description="거래가능구분코드")
    """거래가능구분코드"""
    MgnCltCd: str = Field(default="", title="증거금징수구분코드", description="증거금징수구분코드")
    """증거금징수구분코드"""
    OpngMgn: float = Field(default=0.0, title="개시증거금", description="개시증거금")
    """개시증거금 (Number - precision 15.2)"""
    MntncMgn: float = Field(default=0.0, title="유지증거금", description="유지증거금")
    """유지증거금 (Number - precision 15.2)"""
    OpngMgnR: float = Field(default=0.0, title="개시증거금율", description="개시증거금율")
    """개시증거금율 (Number - precision 7.3)"""
    MntncMgnR: float = Field(default=0.0, title="유지증거금율", description="유지증거금율")
    """유지증거금율 (Number - precision 7.3)"""
    DotGb: int = Field(default=0, title="유효소수점자리수", description="유효소수점자리수")
    """유효소수점자리수"""
    TimeDiff: int = Field(default=0, title="시차", description="시차")
    """시차"""
    OvsDate: str = Field(default="", title="현지체결일자", description="현지체결일자")
    """현지체결일자"""
    KorDate: str = Field(default="", title="한국체결일자", description="한국체결일자")
    """한국체결일자"""
    TrdTm: str = Field(default="", title="현지체결시간", description="현지체결시간")
    """현지체결시간"""
    RcvTm: str = Field(default="", title="한국체결시각", description="한국체결시각")
    """한국체결시각"""
    TrdP: float = Field(default=0.0, title="체결가격", description="체결가격")
    """체결가격 (Number - precision 15.9)"""
    TrdQ: int = Field(default=0, title="체결수량", description="체결수량")
    """체결수량"""
    TotQ: int = Field(default=0, title="누적거래량", description="누적거래량")
    """누적거래량"""
    TrdAmt: float = Field(default=0.0, title="체결거래대금", description="체결거래대금")
    """체결거래대금 (Number - precision 15.2)"""
    TotAmt: float = Field(default=0.0, title="누적거래대금", description="누적거래대금")
    """누적거래대금 (Number - precision 15.2)"""
    OpenP: float = Field(default=0.0, title="시가", description="시가")
    """시가 (Number - precision 15.9)"""
    HighP: float = Field(default=0.0, title="고가", description="고가")
    """고가 (Number - precision 15.9)"""
    LowP: float = Field(default=0.0, title="저가", description="저가")
    """저가 (Number - precision 15.9)"""
    CloseP: float = Field(default=0.0, title="전일종가", description="전일종가")
    """전일종가 (Number - precision 15.9)"""
    YdiffP: float = Field(default=0.0, title="전일대비", description="전일대비")
    """전일대비 (Number - precision 15.9)"""
    YdiffSign: str = Field(default="", title="전일대비구분", description="전일대비구분")
    """전일대비구분"""
    Cgubun: str = Field(default="", title="체결구분", description="체결구분")
    """체결구분"""
    Diff: float = Field(default=0.0, title="등락율", description="등락율")
    """등락율 (Number - precision 6.2)"""
    MinOrcPrc: float = Field(default=0.0, title="최소호가", description="최소호가")
    """최소호가 (Number - precision 15.9)"""
    MinBaseOrcPrc: float = Field(default=0.0, title="최소기준호가", description="최소기준호가")
    """최소기준호가 (Number - precision 15.9)"""


class O3125Response(BaseModel):
    """
    o3125 API 응답 전체 구조
    """
    header: Optional[O3125ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: Optional[O3125OutBlock] = Field(
        None,
        title="출력 블록",
        description="o3125 응답의 출력 블록"
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
