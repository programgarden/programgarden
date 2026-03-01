from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1901RequestHeader(BlockRequestHeader):
    """T1901 요청용 Header"""
    pass


class T1901ResponseHeader(BlockResponseHeader):
    """T1901 응답용 Header"""
    pass


class T1901InBlock(BaseModel):
    """ETF현재가(시세)조회 입력 블록"""
    shcode: str = Field(default="", description="단축코드")


class T1901OutBlock(BaseModel):
    """ETF현재가(시세)조회 출력 블록 - t1901OutBlock"""
    hname: str = Field(default="", description="한글명")
    price: int = Field(default=0, description="현재가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    diff: float = Field(default=0.0, description="등락율")
    volume: int = Field(default=0, description="누적거래량")
    recprice: int = Field(default=0, description="기준가")
    avg: int = Field(default=0, description="가중평균")
    uplmtprice: int = Field(default=0, description="상한가")
    dnlmtprice: int = Field(default=0, description="하한가")
    jnilvolume: int = Field(default=0, description="전일거래량")
    volumediff: int = Field(default=0, description="거래량차")
    open: int = Field(default=0, description="시가")
    opentime: str = Field(default="", description="시가시간")
    high: int = Field(default=0, description="고가")
    hightime: str = Field(default="", description="고가시간")
    low: int = Field(default=0, description="저가")
    lowtime: str = Field(default="", description="저가시간")
    high52w: int = Field(default=0, description="52최고가")
    high52wdate: str = Field(default="", description="52최고가일")
    low52w: int = Field(default=0, description="52최저가")
    low52wdate: str = Field(default="", description="52최저가일")
    exhratio: float = Field(default=0.0, description="소진율")
    flmtvol: int = Field(default=0, description="외국인보유수량")
    per: float = Field(default=0.0, description="PER")
    listing: int = Field(default=0, description="상장주식수(천)")
    jkrate: int = Field(default=0, description="증거금율")
    vol: float = Field(default=0.0, description="회전율")
    shcode: str = Field(default="", description="단축코드")
    value: int = Field(default=0, description="누적거래대금")
    highyear: int = Field(default=0, description="연중최고가")
    highyeardate: str = Field(default="", description="연중최고일자")
    lowyear: int = Field(default=0, description="연중최저가")
    lowyeardate: str = Field(default="", description="연중최저일자")
    upname: str = Field(default="", description="업종명")
    upcode: str = Field(default="", description="업종코드")
    upprice: float = Field(default=0.0, description="업종현재가")
    upsign: str = Field(default="", description="업종전일비구분")
    upchange: float = Field(default=0.0, description="업종전일대비")
    updiff: float = Field(default=0.0, description="업종등락율")
    futname: str = Field(default="", description="선물최근월물명")
    futcode: str = Field(default="", description="선물최근월물코드")
    futprice: float = Field(default=0.0, description="선물현재가")
    futsign: str = Field(default="", description="선물전일비구분")
    futchange: float = Field(default=0.0, description="선물전일대비")
    futdiff: float = Field(default=0.0, description="선물등락율")
    nav: float = Field(default=0.0, description="NAV")
    navsign: str = Field(default="", description="NAV전일대비구분")
    navchange: float = Field(default=0.0, description="NAV전일대비")
    navdiff: float = Field(default=0.0, description="NAV등락율")
    cocrate: float = Field(default=0.0, description="추적오차율")
    kasis: float = Field(default=0.0, description="괴리율")
    subprice: int = Field(default=0, description="대용가")
    offerno1: str = Field(default="", description="매도증권사코드1")
    bidno1: str = Field(default="", description="매수증권사코드1")
    dvol1: int = Field(default=0, description="총매도수량1")
    svol1: int = Field(default=0, description="총매수수량1")
    dcha1: int = Field(default=0, description="매도증감1")
    scha1: int = Field(default=0, description="매수증감1")
    ddiff1: float = Field(default=0.0, description="매도비율1")
    sdiff1: float = Field(default=0.0, description="매수비율1")
    offerno2: str = Field(default="", description="매도증권사코드2")
    bidno2: str = Field(default="", description="매수증권사코드2")
    dvol2: int = Field(default=0, description="총매도수량2")
    svol2: int = Field(default=0, description="총매수수량2")
    dcha2: int = Field(default=0, description="매도증감2")
    scha2: int = Field(default=0, description="매수증감2")
    ddiff2: float = Field(default=0.0, description="매도비율2")
    sdiff2: float = Field(default=0.0, description="매수비율2")
    offerno3: str = Field(default="", description="매도증권사코드3")
    bidno3: str = Field(default="", description="매수증권사코드3")
    dvol3: int = Field(default=0, description="총매도수량3")
    svol3: int = Field(default=0, description="총매수수량3")
    dcha3: int = Field(default=0, description="매도증감3")
    scha3: int = Field(default=0, description="매수증감3")
    ddiff3: float = Field(default=0.0, description="매도비율3")
    sdiff3: float = Field(default=0.0, description="매수비율3")
    offerno4: str = Field(default="", description="매도증권사코드4")
    bidno4: str = Field(default="", description="매수증권사코드4")
    dvol4: int = Field(default=0, description="총매도수량4")
    svol4: int = Field(default=0, description="총매수수량4")
    dcha4: int = Field(default=0, description="매도증감4")
    scha4: int = Field(default=0, description="매수증감4")
    ddiff4: float = Field(default=0.0, description="매도비율4")
    sdiff4: float = Field(default=0.0, description="매수비율4")
    offerno5: str = Field(default="", description="매도증권사코드5")
    bidno5: str = Field(default="", description="매수증권사코드5")
    dvol5: int = Field(default=0, description="총매도수량5")
    svol5: int = Field(default=0, description="총매수수량5")
    dcha5: int = Field(default=0, description="매도증감5")
    scha5: int = Field(default=0, description="매수증감5")
    ddiff5: float = Field(default=0.0, description="매도비율5")
    sdiff5: float = Field(default=0.0, description="매수비율5")
    fwdvl: int = Field(default=0, description="외국계매도합계수량")
    ftradmdcha: int = Field(default=0, description="외국계매도직전대비")
    ftradmddiff: float = Field(default=0.0, description="외국계매도비율")
    fwsvl: int = Field(default=0, description="외국계매수합계수량")
    ftradmscha: int = Field(default=0, description="외국계매수직전대비")
    ftradmsdiff: float = Field(default=0.0, description="외국계매수비율")
    upname2: str = Field(default="", description="참고지수명")
    upcode2: str = Field(default="", description="참고지수코드")
    upprice2: float = Field(default=0.0, description="참고지수현재가")
    jnilnav: float = Field(default=0.0, description="전일NAV")
    jnilnavsign: str = Field(default="", description="전일NAV전일대비구분")
    jnilnavchange: float = Field(default=0.0, description="전일NAV전일대비")
    jnilnavdiff: float = Field(default=0.0, description="전일NAV등락율")
    etftotcap: int = Field(default=0, description="순자산총액(억원)")
    spread: float = Field(default=0.0, description="스프레드")
    leverage: int = Field(default=0, description="레버리지")
    taxgubun: str = Field(default="", description="과세구분")
    opcom_nmk: str = Field(default="", description="운용사")
    lp_nm1: str = Field(default="", description="LP1")
    lp_nm2: str = Field(default="", description="LP2")
    lp_nm3: str = Field(default="", description="LP3")
    lp_nm4: str = Field(default="", description="LP4")
    lp_nm5: str = Field(default="", description="LP5")
    etf_cp: str = Field(default="", description="복제방법")
    etf_kind: str = Field(default="", description="상품유형(Filler)")
    vi_gubun: str = Field(default="", description="VI발동해제")
    etn_kind_cd: str = Field(default="", description="ETN상품분류")
    lastymd: str = Field(default="", description="ETN만기일")
    payday: str = Field(default="", description="ETN지급일")
    lastdate: str = Field(default="", description="ETN최종거래일")
    issuernmk: str = Field(default="", description="ETN발행시장참가자")
    last_sdate: str = Field(default="", description="ETN만기상환가격결정시작일")
    last_edate: str = Field(default="", description="ETN만기상환가격결정종료일")
    lp_holdvol: str = Field(default="", description="ETNLP보유수량")
    listdate: str = Field(default="", description="상장일")
    etp_gb: str = Field(default="", description="ETP상품구분코드")
    etn_elback_yn: str = Field(default="", description="ETN조기상환가능여부")
    settletype: str = Field(default="", description="최종결제")
    idx_asset_class1: str = Field(default="", description="지수자산분류코드(대분류)")
    ty_text: str = Field(default="", description="ETF/ETN투자유의")
    leverage2: float = Field(default=0.0, description="추적수익률배수")


class T1901Request(BaseModel):
    """ETF현재가(시세)조회 요청 모델"""
    header: T1901RequestHeader = T1901RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1901",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1901Response(BaseModel):
    """ETF현재가(시세)조회 응답 모델"""
    header: Optional[T1901ResponseHeader] = None
    block: Optional[T1901OutBlock] = None
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1901RequestHeader",
    "T1901ResponseHeader",
    "T1901InBlock",
    "T1901OutBlock",
    "T1901Request",
    "T1901Response",
]
