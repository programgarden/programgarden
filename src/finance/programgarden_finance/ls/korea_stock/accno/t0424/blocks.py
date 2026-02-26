from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T0424RequestHeader(BlockRequestHeader):
    """t0424 요청용 Header"""
    pass


class T0424ResponseHeader(BlockResponseHeader):
    """t0424 응답용 Header"""
    pass


class T0424InBlock(BaseModel):
    """
    t0424InBlock - 주식잔고2 입력 블록

    단가구분, 체결구분, 단일가구분, 제비용포함 여부와
    연속조회키(cts_expcode)로 계좌 잔고를 조회합니다.

    Attributes:
        prcgb (str): 단가구분 (1:평균단가 2:BEP단가)
        chegb (str): 체결구분 (0:결제기준잔고 2:체결기준잔고)
        dangb (str): 단일가구분 (0:정규장 1:시간외단일가)
        charge (str): 제비용포함여부 (0:미포함 1:포함)
        cts_expcode (str): CTS_종목번호 (연속조회시 OutBlock의 동일필드 입력)
    """
    prcgb: str = Field(
        default="",
        title="단가구분",
        description="1:평균단가 2:BEP단가"
    )
    """ 단가구분 (1:평균단가 2:BEP단가) """
    chegb: str = Field(
        default="",
        title="체결구분",
        description="0:결제기준잔고 2:체결기준잔고"
    )
    """ 체결구분 (0:결제기준잔고 2:체결기준잔고) """
    dangb: str = Field(
        default="",
        title="단일가구분",
        description="0:정규장 1:시간외단일가"
    )
    """ 단일가구분 (0:정규장 1:시간외단일가) """
    charge: str = Field(
        default="",
        title="제비용포함여부",
        description="0:미포함 1:포함"
    )
    """ 제비용포함여부 (0:미포함 1:포함) """
    cts_expcode: str = Field(
        default="",
        title="CTS_종목번호",
        description="연속조회시 OutBlock의 동일필드 입력"
    )
    """ CTS_종목번호 (연속조회키) """


class T0424Request(BaseModel):
    """
    T0424 API 요청 - 주식잔고2

    Attributes:
        header (T0424RequestHeader)
        body (Dict[Literal["t0424InBlock"], T0424InBlock])
        options (SetupOptions)
    """
    header: T0424RequestHeader = T0424RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t0424",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t0424InBlock"], T0424InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t0424"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T0424OutBlock(BaseModel):
    """
    t0424OutBlock - 주식잔고2 연속조회 블록

    계좌 전체 추정순자산, 실현손익, 매입금액 등 합산 정보와
    연속조회키(cts_expcode)를 반환합니다.

    Attributes:
        sunamt (int): 추정순자산
        dtsunik (int): 실현손익
        mamt (int): 매입금액
        sunamt1 (int): 추정D2예수금
        cts_expcode (str): CTS_종목번호 (연속조회키)
        tappamt (int): 평가금액
        tdtsunik (int): 평가손익
    """
    sunamt: int = Field(default=0, title="추정순자산", description="추정순자산")
    """ 추정순자산 """
    dtsunik: int = Field(default=0, title="실현손익", description="실현손익")
    """ 실현손익 """
    mamt: int = Field(default=0, title="매입금액", description="매입금액")
    """ 매입금액 """
    sunamt1: int = Field(default=0, title="추정D2예수금", description="추정D2예수금")
    """ 추정D2예수금 """
    cts_expcode: str = Field(default="", title="CTS_종목번호", description="연속조회키")
    """ CTS_종목번호 (연속조회키) """
    tappamt: int = Field(default=0, title="평가금액", description="평가금액")
    """ 평가금액 """
    tdtsunik: int = Field(default=0, title="평가손익", description="평가손익")
    """ 평가손익 """


class T0424OutBlock1(BaseModel):
    """
    t0424OutBlock1 - 주식잔고2 종목별 잔고 정보

    계좌 내 보유 종목별 잔고수량, 단가, 평가금액, 손익 등 상세 정보를 제공합니다.

    Attributes:
        expcode (str): 종목번호
        jangb (str): 잔고구분
        janqty (int): 잔고수량
        mdposqt (int): 매도가능수량
        pamt (int): 평균단가
        mamt (int): 매입금액
        sinamt (int): 대출금액
        lastdt (str): 만기일자
        msat (int): 당일매수금액
        mpms (int): 당일매수단가
        mdat (int): 당일매도금액
        mpmd (int): 당일매도단가
        jsat (int): 전일매수금액
        jpms (int): 전일매수단가
        jdat (int): 전일매도금액
        jpmd (int): 전일매도단가
        sysprocseq (int): 처리순번
        loandt (str): 대출일자
        hname (str): 종목명
        marketgb (str): 시장구분
        jonggb (str): 종목구분
        janrt (float): 보유비중
        price (int): 현재가
        appamt (int): 평가금액
        dtsunik (int): 평가손익
        sunikrt (float): 수익율
        fee (int): 수수료
        tax (int): 제세금
        sininter (int): 신용이자
    """
    expcode: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """
    jangb: str = Field(default="", title="잔고구분", description="잔고구분")
    """ 잔고구분 """
    janqty: int = Field(default=0, title="잔고수량", description="잔고수량")
    """ 잔고수량 """
    mdposqt: int = Field(default=0, title="매도가능수량", description="매도가능수량")
    """ 매도가능수량 """
    pamt: int = Field(default=0, title="평균단가", description="평균단가")
    """ 평균단가 """
    mamt: int = Field(default=0, title="매입금액", description="매입금액")
    """ 매입금액 """
    sinamt: int = Field(default=0, title="대출금액", description="대출금액")
    """ 대출금액 """
    lastdt: str = Field(default="", title="만기일자", description="만기일자")
    """ 만기일자 """
    msat: int = Field(default=0, title="당일매수금액", description="당일매수금액")
    """ 당일매수금액 """
    mpms: int = Field(default=0, title="당일매수단가", description="당일매수단가")
    """ 당일매수단가 """
    mdat: int = Field(default=0, title="당일매도금액", description="당일매도금액")
    """ 당일매도금액 """
    mpmd: int = Field(default=0, title="당일매도단가", description="당일매도단가")
    """ 당일매도단가 """
    jsat: int = Field(default=0, title="전일매수금액", description="전일매수금액")
    """ 전일매수금액 """
    jpms: int = Field(default=0, title="전일매수단가", description="전일매수단가")
    """ 전일매수단가 """
    jdat: int = Field(default=0, title="전일매도금액", description="전일매도금액")
    """ 전일매도금액 """
    jpmd: int = Field(default=0, title="전일매도단가", description="전일매도단가")
    """ 전일매도단가 """
    sysprocseq: int = Field(default=0, title="처리순번", description="처리순번")
    """ 처리순번 """
    loandt: str = Field(default="", title="대출일자", description="대출일자")
    """ 대출일자 """
    hname: str = Field(default="", title="종목명", description="종목명")
    """ 종목명 """
    marketgb: str = Field(default="", title="시장구분", description="시장구분")
    """ 시장구분 """
    jonggb: str = Field(default="", title="종목구분", description="종목구분")
    """ 종목구분 """
    janrt: float = Field(default=0.0, title="보유비중", description="보유비중")
    """ 보유비중 """
    price: int = Field(default=0, title="현재가", description="현재가")
    """ 현재가 """
    appamt: int = Field(default=0, title="평가금액", description="평가금액")
    """ 평가금액 """
    dtsunik: int = Field(default=0, title="평가손익", description="평가손익")
    """ 평가손익 """
    sunikrt: float = Field(default=0.0, title="수익율", description="수익율")
    """ 수익율 """
    fee: int = Field(default=0, title="수수료", description="수수료")
    """ 수수료 """
    tax: int = Field(default=0, title="제세금", description="제세금")
    """ 제세금 """
    sininter: int = Field(default=0, title="신용이자", description="신용이자")
    """ 신용이자 """


class T0424Response(BaseModel):
    """
    T0424 API 전체 응답 - 주식잔고2

    계좌 전체 합산 정보(cont_block)와 보유 종목별 잔고 리스트(block)를 반환합니다.
    연속조회가 필요하면 cont_block.cts_expcode를 다음 요청의 InBlock.cts_expcode에 설정합니다.

    Attributes:
        header (Optional[T0424ResponseHeader])
        cont_block (Optional[T0424OutBlock]): 합산 정보 및 연속조회키 블록
        block (List[T0424OutBlock1]): 보유 종목별 잔고 리스트
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[T0424ResponseHeader] = None
    cont_block: Optional[T0424OutBlock] = Field(
        None,
        title="합산 및 연속조회 블록",
        description="추정순자산, 실현손익 등 합산 정보와 연속조회키(cts_expcode)를 포함하는 블록"
    )
    block: List[T0424OutBlock1] = Field(
        default_factory=list,
        title="보유 종목별 잔고 리스트",
        description="계좌 내 보유 종목별 잔고 상세 정보 리스트"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str = ""
    rsp_msg: str = ""
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
