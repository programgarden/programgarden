from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1102RequestHeader(BlockRequestHeader):
    """t1102 요청용 Header"""
    pass


class T1102ResponseHeader(BlockResponseHeader):
    """t1102 응답용 Header"""
    pass


class T1102InBlock(BaseModel):
    """
    t1102InBlock - 주식현재가(시세)조회 입력 블록

    종목코드로 현재가 시세 정보를 조회합니다.
    호가(매도/매수 10단계)가 필요하면 t1101을 사용하세요.

    Attributes:
        shcode (str): 종목코드 6자리 (예: "005930")
        exchgubun (str): 거래소구분 (K:KRX, N:NXT, U:통합, 그외:KRX)
    """
    shcode: str
    """ 단축코드 (6자리, 예: "005930") """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX, N:NXT, U:통합, 그외:KRX로 처리) """


class T1102Request(BaseModel):
    """
    T1102 API 요청 - 주식현재가(시세)조회

    Attributes:
        header (T1102RequestHeader)
        body (Dict[Literal["t1102InBlock"], T1102InBlock])
    """
    header: T1102RequestHeader = T1102RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1102",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1102InBlock"], T1102InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1102"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1102OutBlock(BaseModel):
    """
    t1102OutBlock - 주식현재가(시세)조회 응답 블록

    종목의 종합 시세 정보를 제공합니다.
    현재가/등락률, 거래량, 시가/고가/저가, 52주 고저가, PER/PBR,
    시가총액, 상장주식수, 증권사별 매매동향(Top5), 외국계 매매동향,
    재무 실적(전분기/전전분기), VI 발동 정보, NXT 정보 등을 포함합니다.

    ※ 호가(매도/매수 10단계)를 조회하려면 t1101을 사용하세요.
    ※ t1101은 호가 전용, t1102는 시세/종합정보 전용입니다.
    """

    # ── 기본 시세 ──
    hname: str
    """ 한글 종목명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락) """
    change: int
    """ 전일대비 (부호 없는 절대값) """
    diff: float
    """ 등락율 (%) """
    volume: int
    """ 누적거래량 """
    recprice: int
    """ 기준가(평가가격) """
    avg: int
    """ 가중평균가 """
    uplmtprice: int
    """ 상한가(최고호가가격) """
    dnlmtprice: int
    """ 하한가(최저호가가격) """
    jnilvolume: int
    """ 전일거래량 """
    volumediff: int
    """ 거래량차 (당일 - 전일동시간) """
    open: int
    """ 시가 """
    opentime: str
    """ 시가시간 (HHMMSS) """
    high: int
    """ 고가 """
    hightime: str
    """ 고가시간 (HHMMSS) """
    low: int
    """ 저가 """
    lowtime: str
    """ 저가시간 (HHMMSS) """

    # ── 52주/연중 고저가 ──
    high52w: int
    """ 52주 최고가 """
    high52wdate: str
    """ 52주 최고가일 (YYYYMMDD) """
    low52w: int
    """ 52주 최저가 """
    low52wdate: str
    """ 52주 최저가일 (YYYYMMDD) """

    # ── 투자지표 ──
    exhratio: float
    """ 소진율 (%) """
    per: float
    """ PER (주가수익비율) """
    pbrx: float
    """ PBR (주가순자산비율) """
    listing: int
    """ 상장주식수 (천 단위) """
    jkrate: int
    """ 증거금율 (%) """
    memedan: str
    """ 수량단위 """

    # ── 증권사별 매매동향 Top5 (매도) ──
    offernocd1: str
    """ 매도증권사코드1 """
    offerno1: str
    """ 매도증권사명1 """
    dvol1: int
    """ 총매도수량1 """
    dcha1: int
    """ 매도증감1 """
    ddiff1: float
    """ 매도비율1 (%) """
    dval1: int
    """ 총매도대금1 (백만원) """
    davg1: int
    """ 총매도평단가1 """

    offernocd2: str
    """ 매도증권사코드2 """
    offerno2: str
    """ 매도증권사명2 """
    dvol2: int
    """ 총매도수량2 """
    dcha2: int
    """ 매도증감2 """
    ddiff2: float
    """ 매도비율2 (%) """
    dval2: int
    """ 총매도대금2 (백만원) """
    davg2: int
    """ 총매도평단가2 """

    offernocd3: str
    """ 매도증권사코드3 """
    offerno3: str
    """ 매도증권사명3 """
    dvol3: int
    """ 총매도수량3 """
    dcha3: int
    """ 매도증감3 """
    ddiff3: float
    """ 매도비율3 (%) """
    dval3: int
    """ 총매도대금3 (백만원) """
    davg3: int
    """ 총매도평단가3 """

    offernocd4: str
    """ 매도증권사코드4 """
    offerno4: str
    """ 매도증권사명4 """
    dvol4: int
    """ 총매도수량4 """
    dcha4: int
    """ 매도증감4 """
    ddiff4: float
    """ 매도비율4 (%) """
    dval4: int
    """ 총매도대금4 (백만원) """
    davg4: int
    """ 총매도평단가4 """

    offernocd5: str
    """ 매도증권사코드5 """
    offerno5: str
    """ 매도증권사명5 """
    dvol5: int
    """ 총매도수량5 """
    dcha5: int
    """ 매도증감5 """
    ddiff5: float
    """ 매도비율5 (%) """
    dval5: int
    """ 총매도대금5 (백만원) """
    davg5: int
    """ 총매도평단가5 """

    # ── 증권사별 매매동향 Top5 (매수) ──
    bidnocd1: str
    """ 매수증권사코드1 """
    bidno1: str
    """ 매수증권사명1 """
    svol1: int
    """ 총매수수량1 """
    scha1: int
    """ 매수증감1 """
    sdiff1: float
    """ 매수비율1 (%) """
    sval1: int
    """ 총매수대금1 (백만원) """
    savg1: int
    """ 총매수평단가1 """

    bidnocd2: str
    """ 매수증권사코드2 """
    bidno2: str
    """ 매수증권사명2 """
    svol2: int
    """ 총매수수량2 """
    scha2: int
    """ 매수증감2 """
    sdiff2: float
    """ 매수비율2 (%) """
    sval2: int
    """ 총매수대금2 (백만원) """
    savg2: int
    """ 총매수평단가2 """

    bidnocd3: str
    """ 매수증권사코드3 """
    bidno3: str
    """ 매수증권사명3 """
    svol3: int
    """ 총매수수량3 """
    scha3: int
    """ 매수증감3 """
    sdiff3: float
    """ 매수비율3 (%) """
    sval3: int
    """ 총매수대금3 (백만원) """
    savg3: int
    """ 총매수평단가3 """

    bidnocd4: str
    """ 매수증권사코드4 """
    bidno4: str
    """ 매수증권사명4 """
    svol4: int
    """ 총매수수량4 """
    scha4: int
    """ 매수증감4 """
    sdiff4: float
    """ 매수비율4 (%) """
    sval4: int
    """ 총매수대금4 (백만원) """
    savg4: int
    """ 총매수평단가4 """

    bidnocd5: str
    """ 매수증권사코드5 """
    bidno5: str
    """ 매수증권사명5 """
    svol5: int
    """ 총매수수량5 """
    scha5: int
    """ 매수증감5 """
    sdiff5: float
    """ 매수비율5 (%) """
    sval5: int
    """ 총매수대금5 (백만원) """
    savg5: int
    """ 총매수평단가5 """

    # ── 외국계 매매동향 ──
    fwdvl: int
    """ 외국계 매도합계수량 """
    ftradmdcha: int
    """ 외국계 매도 직전대비 """
    ftradmddiff: float
    """ 외국계 매도비율 (%) """
    ftradmdval: int
    """ 외국계 매도대금 """
    ftradmdvag: int
    """ 외국계 매도평단가 """
    fwsvl: int
    """ 외국계 매수합계수량 """
    ftradmscha: int
    """ 외국계 매수 직전대비 """
    ftradmsdiff: float
    """ 외국계 매수비율 (%) """
    ftradmsval: int
    """ 외국계 매수대금 """
    ftradmsvag: int
    """ 외국계 매수평단가 """

    # ── 거래/시장 정보 ──
    vol: float
    """ 회전율 (%) """
    shcode: str
    """ 단축코드 """
    value: int
    """ 누적거래대금 (백만원) """
    jvolume: int
    """ 전일동시간거래량 """
    highyear: int
    """ 연중최고가 """
    highyeardate: str
    """ 연중최고일자 (YYYYMMDD) """
    lowyear: int
    """ 연중최저가 """
    lowyeardate: str
    """ 연중최저일자 (YYYYMMDD) """
    target: int
    """ 목표가 """
    capital: int
    """ 자본금 (백만원) """
    abscnt: int
    """ 유동주식수 (천 단위) """
    parprice: int
    """ 액면가 """
    gsmm: str
    """ 결산월 (MM) """
    subprice: int
    """ 대용가 """
    total: int
    """ 시가총액 (억원) """
    listdate: str
    """ 상장일 (YYYYMMDD) """

    # ── 재무 실적 (전분기) ──
    name: str
    """ 전분기명 (예: "2403 1분기") """
    bfsales: int
    """ 전분기 매출액 (억원) """
    bfoperatingincome: int
    """ 전분기 영업이익 (억원) """
    bfordinaryincome: int
    """ 전분기 경상이익 (억원) """
    bfnetincome: int
    """ 전분기 순이익 (억원) """
    bfeps: float
    """ 전분기 EPS (주당순이익) """

    # ── 재무 실적 (전전분기) ──
    name2: str
    """ 전전분기명 (예: "2312 결산") """
    bfsales2: int
    """ 전전분기 매출액 (억원) """
    bfoperatingincome2: int
    """ 전전분기 영업이익 (억원) """
    bfordinaryincome2: int
    """ 전전분기 경상이익 (억원) """
    bfnetincome2: int
    """ 전전분기 순이익 (억원) """
    bfeps2: float
    """ 전전분기 EPS (주당순이익) """

    # ── 전년 대비 증감율 ──
    salert: float
    """ 전년대비 매출액 증감율 (%) """
    opert: float
    """ 전년대비 영업이익 증감율 (%) """
    ordrt: float
    """ 전년대비 경상이익 증감율 (%) """
    netrt: float
    """ 전년대비 순이익 증감율 (%) """
    epsrt: float
    """ 전년대비 EPS 증감율 (%) """

    # ── 종목 상태/구분 정보 ──
    info1: str
    """ 락구분 (권배락/권리락/배당락/액면분할/액면병합/감자 등, 빈값이면 해당없음) """
    info2: str
    """ 관리/급등구분 (관리/경고/위험/예고 등, 빈값이면 해당없음) """
    info3: str
    """ 정지/연장구분 (거래정지/거래중단/시가연장/종가연장, 빈값이면 해당없음) """
    info4: str
    """ 투자/불성실구분 """
    info5: str
    """ 투자주의환기 """
    janginfo: str
    """ 장구분 (KOSPI/KOSPI200/KOSDAQ/KOSDAQ50/CB 등) """
    t_per: float
    """ T.PER (Trailing PER) """
    tonghwa: str
    """ 통화ISO코드 (KRW) """

    # ── VI/과열 정보 ──
    shterm_text: str
    """ 단기과열/VI발동 (빈값이면 해당없음) """
    svi_uplmtprice: int
    """ 정적VI 상한가 """
    svi_dnlmtprice: int
    """ 정적VI 하한가 """

    # ── 종목 특성 플래그 ──
    spac_gubun: str
    """ 기업인수목적회사(SPAC) 여부 (Y/N) """
    issueprice: int
    """ 발행가격 """
    alloc_gubun: str
    """ 배분적용구분코드 (1:배분발생 2:배분해제 그외:미발생) """
    alloc_text: str
    """ 배분적용구분 텍스트 """
    low_lqdt_gu: str
    """ 저유동성종목여부 (0:해당없음 1:저유동) """
    abnormal_rise_gu: str
    """ 이상급등종목여부 (0:해당없음 1:이상급등) """
    lend_text: str
    """ 대차불가표시 (빈값이면 대차가능, "대차불가"이면 불가) """
    ty_text: str
    """ ETF/ETN투자유의 (빈값이면 해당없음, "투자유의"이면 해당) """

    # ── NXT 대체거래소 정보 ──
    nxt_janginfo: str = ""
    """ NXT 장구분 """
    nxt_shterm_text: str = ""
    """ NXT 단기과열/VI발동 """
    nxt_svi_uplmtprice: int = 0
    """ NXT 정적VI 상한가 """
    nxt_svi_dnlmtprice: int = 0
    """ NXT 정적VI 하한가 """
    ex_shcode: str = ""
    """ 거래소별 단축코드 """


class T1102Response(BaseModel):
    """
    T1102 API 전체 응답 - 주식현재가(시세)조회

    종목의 종합 시세/펀더멘탈/증권사동향/외국계동향을 한 번에 반환합니다.
    호가(매도/매수 10단계)가 필요하면 t1101을 사용하세요.

    Attributes:
        header (Optional[T1102ResponseHeader])
        block (Optional[T1102OutBlock]): 시세 데이터
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[T1102ResponseHeader]
    block: Optional[T1102OutBlock] = Field(
        None,
        title="시세 데이터",
        description="주식현재가(시세)조회 결과 - 종합 시세/펀더멘탈/증권사동향"
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
