from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ05300RequestHeader(BlockRequestHeader):
    pass


class CIDBQ05300ResponseHeader(BlockResponseHeader):
    pass


class CIDBQ05300InBlock1(BaseModel):
    """
    CIDBQ05300InBlock1 데이터 블록

    해외선물 예탁자산 조회를 위한 입력 데이터 블록입니다.

    Attributes:
        RecCnt (int): 레코드갯수
        OvrsAcntTpCode (str): 해외계좌구분코드
        FcmAcntNo (str): FCM계좌번호
        CrcyCode (str): 통화코드 ex) ALL:전체 CAD:캐나다 달러 CHF:스위스 프랑 EUR:유럽연합 유로 GBP:영국 파운드 HKD:홍콩 달러 JPY:일본 엔 SGD:싱가포르 달러 USD:미국 달러
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수"
    )
    """레코드갯수"""

    OvrsAcntTpCode: Literal["1"] = Field(
        default="1",
        title="해외계좌구분코드",
        description="1:위탁"
    )
    """해외계좌구분코드"""

    FcmAcntNo: str = Field(
        default="",
        title="FCM계좌번호",
        description="FCM계좌번호"
    )
    """FCM계좌번호"""

    CrcyCode: Literal["ALL", "CAD", "CHF", "EUR", "GBP", "HKD", "JPY", "SGD", "USD"] = Field(
        default="",
        title="통화코드",
        description="ALL:전체 CAD:캐나다 달러 CHF:스위스 프랑 EUR:유럽연합 유로 GBP:영국 파운드 HKD:홍콩 달러 JPY:일본 엔 SGD:싱가포르 달러 USD:미국 달러"
    )
    """통화코드"""


class CIDBQ05300Request(BaseModel):
    """
    CIDBQ05300 API 요청 클래스.

    Attributes:
        header (CIDBQ05300RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["CIDBQ05300InBlock1"], CIDBQ05300InBlock1]): 입력 데이터 블록.
    """
    header: CIDBQ05300RequestHeader = Field(
        CIDBQ05300RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ05300",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="CIDBQ05300 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    body: dict[Literal["CIDBQ05300InBlock1"], CIDBQ05300InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 예탁자산 조회를 위한 입력 데이터 블록"
    )
    """입력 데이터 블록"""

    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ05300"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CIDBQ05300OutBlock1(BaseModel):
    """
    CIDBQ05300OutBlock1 데이터 블록

    응답의 첫 번째 출력 블록으로 계좌 기본정보를 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        OvrsAcntTpCode (str): 해외계좌구분코드
        FcmAcntNo (str): FCM계좌번호
        AcntNo (str): 계좌번호
        AcntPwd (str): 계좌비밀번호
        CrcyCode (str): 통화코드
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """레코드갯수"""

    OvrsAcntTpCode: str = Field(default="", title="해외계좌구분코드", description="해외계좌구분코드")
    """해외계좌구분코드"""

    FcmAcntNo: str = Field(default="", title="FCM계좌번호", description="FCM계좌번호")
    """FCM계좌번호"""

    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """계좌번호"""

    AcntPwd: str = Field(default="", title="계좌비밀번호", description="계좌비밀번호")
    """계좌비밀번호"""

    CrcyCode: str = Field(default="", title="통화코드", description="통화코드")
    """통화코드"""


class CIDBQ05300OutBlock2(BaseModel):
    """
    CIDBQ05300OutBlock2 데이터 블록

    응답의 두 번째 출력 블록으로 통화별 상세 정보를 포함한 리스트입니다.
    """
    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """계좌번호"""

    CrcyCode: str = Field(default="", title="통화코드", description="통화코드")
    """통화코드"""

    OvrsFutsDps: float = Field(default=0.0, title="해외선물예수금", description="해외선물예수금")
    """해외선물예수금"""

    AbrdFutsCsgnMgn: float = Field(default=0.0, title="해외선물위탁증거금액", description="해외선물위탁증거금액")
    """해외선물위탁증거금액"""

    OvrsFutsSplmMgn: float = Field(default=0.0, title="해외선물추가증거금", description="해외선물추가증거금")
    """해외선물추가증거금"""

    CustmLpnlAmt: float = Field(default=0.0, title="고객청산손익금액", description="고객청산손익금액")
    """고객청산손익금액"""

    AbrdFutsEvalPnlAmt: float = Field(default=0.0, title="해외선물평가손익금액", description="해외선물평가손익금액")
    """해외선물평가손익금액"""

    AbrdFutsCmsnAmt: float = Field(default=0.0, title="해외선물수수료금액", description="해외선물수수료금액")
    """해외선물수수료금액"""

    AbrdFutsEvalDpstgTotAmt: float = Field(default=0.0, title="해외선물평가예탁총금액", description="해외선물평가예탁총금액")
    """해외선물평가예탁총금액"""

    Xchrat: float = Field(default=0.0, title="환율", description="환율")
    """환율"""

    FcurrRealMxchgAmt: float = Field(default=0.0, title="외화실환전금액", description="외화실환전금액")
    """외화실환전금액"""

    AbrdFutsWthdwAbleAmt: float = Field(default=0.0, title="해외선물인출가능금액", description="해외선물인출가능금액")
    """해외선물인출가능금액"""

    AbrdFutsOrdAbleAmt: float = Field(default=0.0, title="해외선물주문가능금액", description="해외선물주문가능금액")
    """해외선물주문가능금액"""

    FutsDueNarrvLqdtPnlAmt: float = Field(default=0.0, title="선물만기미도래청산손익금액", description="선물만기미도래청산손익금액")
    """선물만기미도래청산손익금액"""

    FutsDueNarrvCmsn: float = Field(default=0.0, title="선물만기미도래수수료", description="선물만기미도래수수료")
    """선물만기미도래수수료"""

    AbrdFutsLqdtPnlAmt: float = Field(default=0.0, title="해외선물청산손익금액", description="해외선물청산손익금액")
    """해외선물청산손익금액"""

    OvrsFutsDueCmsn: float = Field(default=0.0, title="해외선물만기수수료", description="해외선물만기수수료")
    """해외선물만기수수료"""

    OvrsFutsOptBuyAmt: float = Field(default=0.0, title="해외선물옵션매수금액", description="해외선물옵션매수금액")
    """해외선물옵션매수금액"""

    OvrsFutsOptSellAmt: float = Field(default=0.0, title="해외선물옵션매도금액", description="해외선물옵션매도금액")
    """해외선물옵션매도금액"""

    OptBuyMktWrthAmt: float = Field(default=0.0, title="옵션매수시장가치금액", description="옵션매수시장가치금액")
    """옵션매수시장가치금액"""

    OptSellMktWrthAmt: float = Field(default=0.0, title="옵션매도시장가치금액", description="옵션매도시장가치금액")
    """옵션매도시장가치금액"""


class CIDBQ05300OutBlock3(BaseModel):
    """
    CIDBQ05300OutBlock3 데이터 블록

    응답의 세 번째 출력 블록으로 집계/요약 정보를 포함합니다.
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """레코드갯수"""

    OvrsFutsDps: float = Field(default=0.0, title="해외선물예수금", description="해외선물예수금")
    """해외선물예수금"""

    AbrdFutsLqdtPnlAmt: float = Field(default=0.0, title="해외선물청산손익금액", description="해외선물청산손익금액")
    """해외선물청산손익금액"""

    FutsDueNarrvLqdtPnlAmt: float = Field(default=0.0, title="선물만기미도래청산손익금액", description="선물만기미도래청산손익금액")
    """선물만기미도래청산손익금액"""

    AbrdFutsEvalPnlAmt: float = Field(default=0.0, title="해외선물평가손익금액", description="해외선물평가손익금액")
    """해외선물평가손익금액"""

    AbrdFutsEvalDpstgTotAmt: float = Field(default=0.0, title="해외선물평가예탁총금액", description="해외선물평가예탁총금액")
    """해외선물평가예탁총금액"""

    CustmLpnlAmt: float = Field(default=0.0, title="고객청산손익금액", description="고객청산손익금액")
    """고객청산손익금액"""

    OvrsFutsDueCmsn: float = Field(default=0.0, title="해외선물만기수수료", description="해외선물만기수수료")
    """해외선물만기수수료"""

    FcurrRealMxchgAmt: float = Field(default=0.0, title="외화실환전금액", description="외화실환전금액")
    """외화실환전금액"""

    AbrdFutsCmsnAmt: float = Field(default=0.0, title="해외선물수수료금액", description="해외선물수수료금액")
    """해외선물수수료금액"""

    FutsDueNarrvCmsn: float = Field(default=0.0, title="선물만기미도래수수료", description="선물만기미도래수수료")
    """선물만기미도래수수료"""

    AbrdFutsCsgnMgn: float = Field(default=0.0, title="해외선물위탁증거금액", description="해외선물위탁증거금액")
    """해외선물위탁증거금액"""

    OvrsFutsMaintMgn: float = Field(default=0.0, title="해외선물유지증거금", description="해외선물유지증거금")
    """해외선물유지증거금"""

    OvrsFutsOptBuyAmt: float = Field(default=0.0, title="해외선물옵션매수금액", description="해외선물옵션매수금액")
    """해외선물옵션매수금액"""

    OvrsFutsOptSellAmt: float = Field(default=0.0, title="해외선물옵션매도금액", description="해외선물옵션매도금액")
    """해외선물옵션매도금액"""

    CtlmtAmt: float = Field(default=0.0, title="신용한도금액", description="신용한도금액")
    """신용한도금액"""

    OvrsFutsSplmMgn: float = Field(default=0.0, title="해외선물추가증거금", description="해외선물추가증거금")
    """해외선물추가증거금"""

    MgnclRat: float = Field(default=0.0, title="마진콜율", description="마진콜율")
    """마진콜율"""

    AbrdFutsOrdAbleAmt: float = Field(default=0.0, title="해외선물주문가능금액", description="해외선물주문가능금액")
    """해외선물주문가능금액"""

    AbrdFutsWthdwAbleAmt: float = Field(default=0.0, title="해외선물인출가능금액", description="해외선물인출가능금액")
    """해외선물인출가능금액"""

    OptBuyMktWrthAmt: float = Field(default=0.0, title="옵션매수시장가치금액", description="옵션매수시장가치금액")
    """옵션매수시장가치금액"""

    OptSellMktWrthAmt: float = Field(default=0.0, title="옵션매도시장가치금액", description="옵션매도시장가치금액")
    """옵션매도시장가치금액"""

    OvrsOptSettAmt: float = Field(default=0.0, title="해외옵션결제금액", description="해외옵션결제금액")
    """해외옵션결제금액"""

    OvrsOptBalEvalAmt: float = Field(default=0.0, title="해외옵션잔고평가금액", description="해외옵션잔고평가금액")
    """해외옵션잔고평가금액"""


class CIDBQ05300Response(BaseModel):
    """
    CIDBQ05300 API 응답 전체 구조

    Attributes:
        header (Optional[CIDBQ05300ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[CIDBQ05300OutBlock1]): 첫 번째 출력 블록
        block2 (List[CIDBQ05300OutBlock2]): 두 번째 출력 블록 리스트
        block3 (Optional[CIDBQ05300OutBlock3]): 세 번째 출력 블록
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
    """
    header: Optional[CIDBQ05300ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="CIDBQ05300 API 응답을 위한 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    block1: Optional[CIDBQ05300OutBlock1] = Field(
        None,
        title="첫 번째 출력 블록",
        description="첫 번째 출력 블록"
    )
    """첫 번째 출력 블록"""

    block2: List[CIDBQ05300OutBlock2] = Field(
        default_factory=list,
        title="두 번째 출력 블록 리스트",
        description="두 번째 출력 블록 리스트"
    )
    """두 번째 출력 블록 리스트"""

    block3: Optional[CIDBQ05300OutBlock3] = Field(
        None,
        title="세 번째 출력 블록",
        description="세 번째 출력 블록"
    )
    """세 번째 출력 블록"""

    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    """HTTP 상태 코드"""

    rsp_cd: str = Field(..., title="응답코드", description="응답코드")
    """응답코드"""

    rsp_msg: str = Field(..., title="응답메시지", description="응답메시지")
    """응답메시지"""

    error_msg: Optional[str] = Field(None, title="오류 메시지", description="오류 메시지 (오류 발생 시)")
    """오류 메시지 (오류 발생 시)"""
    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """ private으로 BaseModel의 직렬화에 포함시키지 않는다 """

    @property
    def raw_data(self) -> Optional[Response]:
        """API 호출에 대한 원시 응답 데이터"""
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
