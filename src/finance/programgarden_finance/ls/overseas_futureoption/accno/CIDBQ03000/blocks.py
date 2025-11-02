from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ03000RequestHeader(BlockRequestHeader):
    pass


class CIDBQ03000ResponseHeader(BlockResponseHeader):
    pass


class CIDBQ03000InBlock1(BaseModel):
    """
    CIDBQ03000InBlock1 데이터 블록

    해외선물 예수금/잔고현황 조회를 위한 입력 데이터 블록입니다.

    Attributes:
        RecCnt (int): 레코드갯수
        AcntTpCode (str): 계좌구분코드
        TrdDt (str): 거래일자
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수"
    )
    """레코드갯수"""

    AcntTpCode: str = Field(
        default="",
        title="계좌구분코드",
        description="1 : 위탁계좌 2 : 중개계좌"
    )
    """계좌구분코드"""

    TrdDt: str = Field(
        default="",
        title="거래일자",
        description="거래일자(YYYYMMDD)"
    )
    """거래일자(YYYYMMDD)"""


class CIDBQ03000Request(BaseModel):
    """
    CIDBQ03000 API 요청 클래스.

    Attributes:
        header (CIDBQ03000RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["CIDBQ03000InBlock1"], CIDBQ03000InBlock1]): 입력 데이터 블록.
    """
    header: CIDBQ03000RequestHeader = Field(
        CIDBQ03000RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ03000",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="CIDBQ03000 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    body: dict[Literal["CIDBQ03000InBlock1"], CIDBQ03000InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 예수금/잔고현황 조회를 위한 입력 데이터 블록"
    )
    """입력 데이터 블록"""

    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ03000"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CIDBQ03000OutBlock1(BaseModel):
    """
    CIDBQ03000OutBlock1 데이터 블록

    응답의 첫 번째 출력 블록으로 계좌 기본정보를 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        AcntTpCode (str): 계좌구분코드
        AcntNo (str): 계좌번호
        AcntPwd (str): 계좌비밀번호
        TrdDt (str): 거래일자
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """레코드갯수"""

    AcntTpCode: str = Field(default="", title="계좌구분코드", description="계좌구분코드")
    """계좌구분코드"""

    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """계좌번호"""

    AcntPwd: str = Field(default="", title="계좌비밀번호", description="계좌비밀번호")
    """계좌비밀번호"""

    TrdDt: str = Field(default="", title="거래일자", description="거래일자")
    """거래일자"""


class CIDBQ03000OutBlock2(BaseModel):
    """
    CIDBQ03000OutBlock2 데이터 블록

    응답의 두 번째 출력 블록으로 해외선물 예수금/잔고 상세 정보를 포함한 리스트입니다.

    Attributes:
        AcntNo (str): 계좌번호
        TrdDt (str): 거래일자
        CrcyObjCode (str): 통화대상코드
        OvrsFutsDps (float): 해외선물예수금
        CustmMnyioAmt (float): 고객입출금금액
        AbrdFutsLqdtPnlAmt (float): 해외선물청산손익금액
        AbrdFutsCmsnAmt (float): 해외선물수수료금액
        PrexchDps (float): 가환전예수금
        EvalAssetAmt (float): 평가자산금액
        AbrdFutsCsgnMgn (float): 해외선물위탁증거금액
        AbrdFutsAddMgn (float): 해외선물추가증거금액
        AbrdFutsWthdwAbleAmt (float): 해외선물인출가능금액
        AbrdFutsOrdAbleAmt (float): 해외선물주문가능금액
        AbrdFutsEvalPnlAmt (float): 해외선물평가손익금액
        LastSettPnlAmt (float): 최종결제손익금액
        OvrsOptSettAmt (float): 해외옵션결제금액
        OvrsOptBalEvalAmt (float): 해외옵션잔고평가금액
    """
    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """계좌번호"""

    TrdDt: str = Field(default="", title="거래일자", description="거래일자")
    """거래일자"""

    CrcyObjCode: str = Field(default="", title="통화대상코드", description="통화대상코드")
    """통화대상코드"""

    OvrsFutsDps: float = Field(default=0.0, title="해외선물예수금", description="해외선물예수금")
    """해외선물예수금"""

    CustmMnyioAmt: float = Field(default=0.0, title="고객입출금금액", description="고객입출금금액")
    """고객입출금금액"""

    AbrdFutsLqdtPnlAmt: float = Field(default=0.0, title="해외선물청산손익금액", description="해외선물청산손익금액")
    """해외선물청산손익금액"""

    AbrdFutsCmsnAmt: float = Field(default=0.0, title="해외선물수수료금액", description="해외선물수수료금액")
    """해외선물수수료금액"""

    PrexchDps: float = Field(default=0.0, title="가환전예수금", description="가환전예수금")
    """가환전예수금"""

    EvalAssetAmt: float = Field(default=0.0, title="평가자산금액", description="평가자산금액")
    """평가자산금액"""

    AbrdFutsCsgnMgn: float = Field(default=0.0, title="해외선물위탁증거금액", description="해외선물위탁증거금액")
    """해외선물위탁증거금액"""

    AbrdFutsAddMgn: float = Field(default=0.0, title="해외선물추가증거금액", description="해외선물추가증거금액")
    """해외선물추가증거금액"""

    AbrdFutsWthdwAbleAmt: float = Field(default=0.0, title="해외선물인출가능금액", description="해외선물인출가능금액")
    """해외선물인출가능금액"""

    AbrdFutsOrdAbleAmt: float = Field(default=0.0, title="해외선물주문가능금액", description="해외선물주문가능금액")
    """해외선물주문가능금액"""

    AbrdFutsEvalPnlAmt: float = Field(default=0.0, title="해외선물평가손익금액", description="해외선물평가손익금액")
    """해외선물평가손익금액"""

    LastSettPnlAmt: float = Field(default=0.0, title="최종결제손익금액", description="최종결제손익금액")
    """최종결제손익금액"""

    OvrsOptSettAmt: float = Field(default=0.0, title="해외옵션결제금액", description="해외옵션결제금액")
    """해외옵션결제금액"""

    OvrsOptBalEvalAmt: float = Field(default=0.0, title="해외옵션잔고평가금액", description="해외옵션잔고평가금액")
    """해외옵션잔고평가금액"""


class CIDBQ03000Response(BaseModel):
    """
    CIDBQ03000 API 응답 전체 구조

    Attributes:
        header (Optional[CIDBQ03000ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[CIDBQ03000OutBlock1]): 첫 번째 출력 블록
        block2 (List[CIDBQ03000OutBlock2]): 두 번째 출력 블록 리스트
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
    """
    header: Optional[CIDBQ03000ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="CIDBQ03000 API 응답을 위한 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    block1: Optional[CIDBQ03000OutBlock1] = Field(
        None,
        title="첫 번째 출력 블록",
        description="첫 번째 출력 블록"
    )
    """첫 번째 출력 블록"""

    block2: List[CIDBQ03000OutBlock2] = Field(
        default_factory=list,
        title="두 번째 출력 블록 리스트",
        description="두 번째 출력 블록 리스트"
    )
    """두 번째 출력 블록 리스트"""

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
