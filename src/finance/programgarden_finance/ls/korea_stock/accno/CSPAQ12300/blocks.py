from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ12300RequestHeader(BlockRequestHeader):
    """CSPAQ12300 요청용 Header"""
    pass


class CSPAQ12300ResponseHeader(BlockResponseHeader):
    """CSPAQ12300 응답용 Header"""
    pass


class CSPAQ12300InBlock1(BaseModel):
    """
    CSPAQ12300InBlock1 - BEP단가조회/현물계좌잔고내역 입력 블록

    계좌의 잔고 내역 및 BEP 단가 정보를 조회합니다.

    Attributes:
        BalCreTp (str): 잔고생성구분 (기본 "0")
        CmsnAppTpCode (str): 수수료적용구분코드 (기본 "0")
        D2balBaseQryTp (str): D2잔고기준조회구분 (기본 "0")
        UprcTpCode (str): 단가구분코드 (기본 "0")
    """
    BalCreTp: str = Field(
        default="0",
        title="잔고생성구분",
        description="잔고생성구분"
    )
    """ 잔고생성구분 """
    CmsnAppTpCode: str = Field(
        default="0",
        title="수수료적용구분코드",
        description="수수료적용구분코드"
    )
    """ 수수료적용구분코드 """
    D2balBaseQryTp: str = Field(
        default="0",
        title="D2잔고기준조회구분",
        description="D2잔고기준조회구분"
    )
    """ D2잔고기준조회구분 """
    UprcTpCode: str = Field(
        default="0",
        title="단가구분코드",
        description="단가구분코드"
    )
    """ 단가구분코드 """


class CSPAQ12300Request(BaseModel):
    """
    CSPAQ12300 API 요청 - BEP단가조회/현물계좌잔고내역

    Attributes:
        header (CSPAQ12300RequestHeader)
        body (dict[Literal["CSPAQ12300InBlock1"], CSPAQ12300InBlock1])
    """
    header: CSPAQ12300RequestHeader = CSPAQ12300RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ12300",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CSPAQ12300InBlock1"], CSPAQ12300InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ12300"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CSPAQ12300OutBlock1(BaseModel):
    """
    CSPAQ12300OutBlock1 - 입력 echo-back 블록

    Attributes:
        RecCnt (int): 레코드갯수
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        BalCreTp (str): 잔고생성구분
        CmsnAppTpCode (str): 수수료적용구분코드
        D2balBaseQryTp (str): D2잔고기준조회구분
        UprcTpCode (str): 단가구분코드
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """ 계좌번호 """
    Pwd: str = Field(default="", title="비밀번호", description="비밀번호")
    """ 비밀번호 """
    BalCreTp: str = Field(default="0", title="잔고생성구분", description="잔고생성구분")
    """ 잔고생성구분 """
    CmsnAppTpCode: str = Field(default="0", title="수수료적용구분코드", description="수수료적용구분코드")
    """ 수수료적용구분코드 """
    D2balBaseQryTp: str = Field(default="0", title="D2잔고기준조회구분", description="D2잔고기준조회구분")
    """ D2잔고기준조회구분 """
    UprcTpCode: str = Field(default="0", title="단가구분코드", description="단가구분코드")
    """ 단가구분코드 """


class CSPAQ12300OutBlock2(BaseModel):
    """
    CSPAQ12300OutBlock2 - 잔고 요약 블록

    Attributes:
        RecCnt (int): 레코드갯수
        BrnNm (str): 지점명
        AcntNm (str): 계좌명
        MnyOrdAbleAmt (int): 현금주문가능금액
        BalEvalAmt (int): 잔고평가금액
        PchsAmt (int): 매입금액
        EvalPnl (int): 평가손익
        PnlRat (float): 손익율
        DpsastTotamt (int): 예탁자산총액
        InvstOrgAmt (int): 투자원금
        InvstPlAmt (int): 투자손익
        Dps (int): 예수금
        D1Dps (int): D1예수금
        D2Dps (int): D2예수금
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    BrnNm: str = Field(default="", title="지점명", description="지점명")
    """ 지점명 """
    AcntNm: str = Field(default="", title="계좌명", description="계좌명")
    """ 계좌명 """
    MnyOrdAbleAmt: int = Field(default=0, title="현금주문가능금액", description="현금주문가능금액")
    """ 현금주문가능금액 """
    BalEvalAmt: int = Field(default=0, title="잔고평가금액", description="잔고평가금액")
    """ 잔고평가금액 """
    PchsAmt: int = Field(default=0, title="매입금액", description="매입금액")
    """ 매입금액 """
    EvalPnl: int = Field(default=0, title="평가손익", description="평가손익")
    """ 평가손익 """
    PnlRat: float = Field(default=0.0, title="손익율", description="손익율")
    """ 손익율 """
    DpsastTotamt: int = Field(default=0, title="예탁자산총액", description="예탁자산총액")
    """ 예탁자산총액 """
    InvstOrgAmt: int = Field(default=0, title="투자원금", description="투자원금")
    """ 투자원금 """
    InvstPlAmt: int = Field(default=0, title="투자손익", description="투자손익")
    """ 투자손익 """
    Dps: int = Field(default=0, title="예수금", description="예수금")
    """ 예수금 """
    D1Dps: int = Field(default=0, title="D1예수금", description="D1예수금")
    """ D1예수금 """
    D2Dps: int = Field(default=0, title="D2예수금", description="D2예수금")
    """ D2예수금 """


class CSPAQ12300OutBlock3(BaseModel):
    """
    CSPAQ12300OutBlock3 - 잔고 종목 배열 블록

    Attributes:
        IsuNo (str): 종목번호
        IsuNm (str): 종목명
        BalQty (int): 잔고수량
        BnsBaseBalQty (int): 매매기준잔고수량
        SellPrc (float): 매도단가
        BuyPrc (float): 매수단가
        NowPrc (float): 현재가
        AvrUprc (float): 평균단가
        BalEvalAmt (int): 잔고평가금액
        EvalPnl (int): 평가손익
        PnlRat (float): 손익율
        SellAbleQty (int): 매도가능수량
        CrdtAmt (int): 신용금액
        LoanDt (str): 대출일
        Expdt (str): 만기일
        SellQty (int): 매도수량
        BuyQty (int): 매수수량
    """
    IsuNo: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """
    IsuNm: str = Field(default="", title="종목명", description="종목명")
    """ 종목명 """
    BalQty: int = Field(default=0, title="잔고수량", description="잔고수량")
    """ 잔고수량 """
    BnsBaseBalQty: int = Field(default=0, title="매매기준잔고수량", description="매매기준잔고수량")
    """ 매매기준잔고수량 """
    SellPrc: float = Field(default=0.0, title="매도단가", description="매도단가")
    """ 매도단가 """
    BuyPrc: float = Field(default=0.0, title="매수단가", description="매수단가")
    """ 매수단가 """
    NowPrc: float = Field(default=0.0, title="현재가", description="현재가")
    """ 현재가 """
    AvrUprc: float = Field(default=0.0, title="평균단가", description="평균단가")
    """ 평균단가 """
    BalEvalAmt: int = Field(default=0, title="잔고평가금액", description="잔고평가금액")
    """ 잔고평가금액 """
    EvalPnl: int = Field(default=0, title="평가손익", description="평가손익")
    """ 평가손익 """
    PnlRat: float = Field(default=0.0, title="손익율", description="손익율")
    """ 손익율 """
    SellAbleQty: int = Field(default=0, title="매도가능수량", description="매도가능수량")
    """ 매도가능수량 """
    CrdtAmt: int = Field(default=0, title="신용금액", description="신용금액")
    """ 신용금액 """
    LoanDt: str = Field(default="", title="대출일", description="대출일")
    """ 대출일 """
    Expdt: str = Field(default="", title="만기일", description="만기일")
    """ 만기일 """
    SellQty: int = Field(default=0, title="매도수량", description="매도수량")
    """ 매도수량 """
    BuyQty: int = Field(default=0, title="매수수량", description="매수수량")
    """ 매수수량 """


class CSPAQ12300Response(BaseModel):
    """
    CSPAQ12300 API 전체 응답 - BEP단가조회/현물계좌잔고내역

    Attributes:
        header (Optional[CSPAQ12300ResponseHeader])
        block1 (Optional[CSPAQ12300OutBlock1]): 입력 echo-back
        block2 (Optional[CSPAQ12300OutBlock2]): 잔고 요약 데이터
        block3 (List[CSPAQ12300OutBlock3]): 잔고 종목 배열
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CSPAQ12300ResponseHeader] = None
    block1: Optional[CSPAQ12300OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="입력 파라미터 echo-back 블록"
    )
    block2: Optional[CSPAQ12300OutBlock2] = Field(
        None,
        title="잔고 요약 데이터",
        description="계좌 잔고 요약 정보"
    )
    block3: List[CSPAQ12300OutBlock3] = Field(
        default_factory=list,
        title="잔고 종목 배열",
        description="계좌 내 종목별 잔고 내역"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str = Field(default="", title="응답코드", description="응답코드")
    rsp_msg: str = Field(default="", title="응답메시지", description="응답메시지")
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
