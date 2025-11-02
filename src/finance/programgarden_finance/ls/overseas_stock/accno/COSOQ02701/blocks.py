from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSOQ02701RequestHeader(BlockRequestHeader):
    pass


class COSOQ02701ResponseHeader(BlockResponseHeader):
    pass


class COSOQ02701InBlock1(BaseModel):
    """
    COSOQ02701InBlock1 데이터 블록

    LS증권 OpenAPI의 COSOQ02701 외화 예수금 및 주문 가능 금액 조회에 사용되는 입력 데이터 블록입니다.

    Attributes:
        RecCnt (int): 레코드갯수
        CrcyCode (str): 통화코드
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수"
    )
    """레코드갯수"""

    CrcyCode: Literal["USD"] = Field(
        default="USD",
        title="통화코드",
        description="통화코드 (허용값: 'USD')"
    )
    """통화코드"""


class COSOQ02701Request(BaseModel):
    """
    COSOQ02701 API 요청 클래스.

    Attributes:
        header (COSOQ02701RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["COSOQ02701InBlock1"], COSOQ02701InBlock1]): 예수금 조회를 위한 입력 데이터 블록.
    """
    header: COSOQ02701RequestHeader = Field(
        COSOQ02701RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSOQ02701",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="COSOQ02701 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    body: dict[Literal["COSOQ02701InBlock1"], COSOQ02701InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="예수금 조회를 위한 입력 데이터 블록"
    )
    """ 입력 데이터 블록"""

    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=2,
            on_rate_limit="wait",
            rate_limit_key="COSOQ02701"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class COSOQ02701OutBlock1(BaseModel):
    """
    COSOQ02701OutBlock1 데이터 블록

    응답의 첫 번째 출력 블록으로 계좌 기본정보를 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        CrcyCode (str): 통화코드
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="레코드갯수"
    )
    """레코드갯수"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""

    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="비밀번호"
    )
    """비밀번호"""

    CrcyCode: str = Field(
        default="",
        title="통화코드",
        description="통화코드"
    )
    """통화코드"""


class COSOQ02701OutBlock2(BaseModel):
    """
    COSOQ02701OutBlock2 데이터 블록

    응답의 두 번째 출력 블록으로 외화매매정산금 및 예수금 정보를 포함한 리스트입니다.

    Attributes:
        CrcyCode (str): 통화코드
        FcurrBuyAdjstAmt1 (float): 외화매수정산금1
        FcurrBuyAdjstAmt2 (float): 외화매수정산금2
        FcurrBuyAdjstAmt3 (float): 외화매수정산금3
        FcurrBuyAdjstAmt4 (float): 외화매수정산금4
        FcurrSellAdjstAmt1 (float): 외화매도정산금1
        FcurrSellAdjstAmt2 (float): 외화매도정산금2
        FcurrSellAdjstAmt3 (float): 외화매도정산금3
        FcurrSellAdjstAmt4 (float): 외화매도정산금4
        PrsmptFcurrDps1 (float): 추정외화예수금1
        PrsmptFcurrDps2 (float): 추정외화예수금2
        PrsmptFcurrDps3 (float): 추정외화예수금3
        PrsmptFcurrDps4 (float): 추정외화예수금4
        PrsmptMxchgAbleAmt1 (float): 추정환전가능금1
        PrsmptMxchgAbleAmt2 (float): 추정환전가능금2
        PrsmptMxchgAbleAmt3 (float): 추정환전가능금3
        PrsmptMxchgAbleAmt4 (float): 추정환전가능금4
    """
    CrcyCode: str = Field(
        default="",
        title="통화코드",
        description="통화코드"
    )
    """통화코드"""

    FcurrBuyAdjstAmt1: float = Field(
        default=0.0,
        title="외화매수정산금1",
        description="외화매수정산금1"
    )
    """외화매수정산금1"""

    FcurrBuyAdjstAmt2: float = Field(default=0.0, title="외화매수정산금2", description="외화매수정산금2")
    FcurrBuyAdjstAmt3: float = Field(default=0.0, title="외화매수정산금3", description="외화매수정산금3")
    FcurrBuyAdjstAmt4: float = Field(default=0.0, title="외화매수정산금4", description="외화매수정산금4")

    FcurrSellAdjstAmt1: float = Field(default=0.0, title="외화매도정산금1", description="외화매도정산금1")
    FcurrSellAdjstAmt2: float = Field(default=0.0, title="외화매도정산금2", description="외화매도정산금2")
    FcurrSellAdjstAmt3: float = Field(default=0.0, title="외화매도정산금3", description="외화매도정산금3")
    FcurrSellAdjstAmt4: float = Field(default=0.0, title="외화매도정산금4", description="외화매도정산금4")

    PrsmptFcurrDps1: float = Field(default=0.0, title="추정외화예수금1", description="추정외화예수금1")
    PrsmptFcurrDps2: float = Field(default=0.0, title="추정외화예수금2", description="추정외화예수금2")
    PrsmptFcurrDps3: float = Field(default=0.0, title="추정외화예수금3", description="추정외화예수금3")
    PrsmptFcurrDps4: float = Field(default=0.0, title="추정외화예수금4", description="추정외화예수금4")

    PrsmptMxchgAbleAmt1: float = Field(default=0.0, title="추정환전가능금1", description="추정환전가능금1")
    PrsmptMxchgAbleAmt2: float = Field(default=0.0, title="추정환전가능금2", description="추정환전가능금2")
    PrsmptMxchgAbleAmt3: float = Field(default=0.0, title="추정환전가능금3", description="추정환전가능금3")
    PrsmptMxchgAbleAmt4: float = Field(default=0.0, title="추정환전가능금4", description="추정환전가능금4")


class COSOQ02701OutBlock3(BaseModel):
    """
    COSOQ02701OutBlock3 데이터 블록

    응답의 세 번째 출력 블록으로 국가별 외화예수금·주문가능금액 상세 정보를 포함한 리스트입니다.

    Attributes:
        CntryNm (str): 국가명
        CrcyCode (str): 통화코드
        T4FcurrDps (float): T4외화예수금
        FcurrDps (float): 외화예수금
        FcurrOrdAbleAmt (float): 외화주문가능금액
        PrexchOrdAbleAmt (float): 가환전주문가능금액
        FcurrOrdAmt (float): 외화주문금액
        FcurrPldgAmt (float): 외화담보금액
        ExecRuseFcurrAmt (float): 체결재사용외화금액
        FcurrMxchgAbleAmt (float): 외화환전가능금
        BaseXchrat (float): 기준환율
    """
    CntryNm: str = Field(default="", title="국가명", description="국가명")
    """국가명"""

    CrcyCode: str = Field(default="", title="통화코드", description="통화코드")
    """통화코드"""

    T4FcurrDps: float = Field(default=0.0, title="T4외화예수금", description="T4외화예수금")
    """T4외화예수금"""

    FcurrDps: float = Field(default=0.0, title="외화예수금", description="외화예수금")
    """외화예수금"""

    FcurrOrdAbleAmt: float = Field(default=0.0, title="외화주문가능금액", description="외화주문가능금액")
    """외화주문가능금액"""

    PrexchOrdAbleAmt: float = Field(default=0.0, title="가환전주문가능금액", description="가환전주문가능금액")
    """가환전주문가능금액"""

    FcurrOrdAmt: float = Field(default=0.0, title="외화주문금액", description="외화주문금액")
    """외화주문금액"""

    FcurrPldgAmt: float = Field(default=0.0, title="외화담보금액", description="외화담보금액")
    """외화담보금액"""

    ExecRuseFcurrAmt: float = Field(default=0.0, title="체결재사용외화금액", description="체결재사용외화금액")
    """체결재사용외화금액"""

    FcurrMxchgAbleAmt: float = Field(default=0.0, title="외화환전가능금", description="외화환전가능금")
    """외화환전가능금"""

    BaseXchrat: float = Field(default=0.0, title="기준환율", description="기준환율")
    """기준환율"""


class COSOQ02701OutBlock4(BaseModel):
    """
    COSOQ02701OutBlock4 데이터 블록

    응답의 네 번째 출력 블록으로 원화예수금·해외증거금 등의 정보를 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        WonDpsBalAmt (int): 원화예수금잔고금액
        MnyoutAbleAmt (int): 출금가능금액
        WonPrexchAbleAmt (int): 원화가환전가능금액
        OvrsMgn (float): 해외증거금
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """레코드갯수"""

    WonDpsBalAmt: int = Field(default=0, title="원화예수금잔고금액", description="원화예수금잔고금액")
    """원화예수금잔고금액"""

    MnyoutAbleAmt: int = Field(default=0, title="출금가능금액", description="출금가능금액")
    """출금가능금액"""

    WonPrexchAbleAmt: int = Field(default=0, title="원화가환전가능금액", description="원화가환전가능금액")
    """원화가환전가능금액"""

    OvrsMgn: float = Field(default=0.0, title="해외증거금", description="해외증거금")
    """해외증거금"""


class COSOQ02701OutBlock5(BaseModel):
    """
    COSOQ02701OutBlock5 데이터 블록

    응답의 다섯 번째 출력 블록으로 내외국인코드를 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        NrfCode (str): 내외국인코드
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """레코드갯수"""

    NrfCode: str = Field(default="", title="내외국인코드", description="내외국인코드")
    """내외국인코드"""


class COSOQ02701Response(BaseModel):
    """
    COSOQ02701 API 응답 전체 구조

    Attributes:
        header (Optional[COSOQ02701ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[COSOQ02701OutBlock1]): 첫 번째 출력 블록
        block2 (List[COSOQ02701OutBlock2]): 두 번째 출력 블록 리스트
        block3 (List[COSOQ02701OutBlock3]): 세 번째 출력 블록 리스트
        block4 (Optional[COSOQ02701OutBlock4]): 네 번째 출력 블록
        block5 (Optional[COSOQ02701OutBlock5]): 다섯 번째 출력 블록
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
    """
    header: Optional[COSOQ02701ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="COSOQ02701 API 응답을 위한 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    block1: Optional[COSOQ02701OutBlock1] = Field(
        None,
        title="첫 번째 출력 블록",
        description="첫 번째 출력 블록"
    )
    """첫 번째 출력 블록"""

    block2: List[COSOQ02701OutBlock2] = Field(
        default_factory=list,
        title="두 번째 출력 블록 리스트",
        description="두 번째 출력 블록 리스트"
    )
    """두 번째 출력 블록 리스트"""

    block3: List[COSOQ02701OutBlock3] = Field(
        default_factory=list,
        title="세 번째 출력 블록 리스트",
        description="세 번째 출력 블록 리스트"
    )
    """세 번째 출력 블록 리스트"""

    block4: Optional[COSOQ02701OutBlock4] = Field(
        None,
        title="네 번째 출력 블록",
        description="네 번째 출력 블록"
    )
    """네 번째 출력 블록"""

    block5: Optional[COSOQ02701OutBlock5] = Field(
        None,
        title="다섯 번째 출력 블록",
        description="다섯 번째 출력 블록"
    )
    """다섯 번째 출력 블록"""

    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
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
