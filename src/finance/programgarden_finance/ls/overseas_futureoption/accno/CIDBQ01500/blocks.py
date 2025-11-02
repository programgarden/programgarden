from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ01500RequestHeader(BlockRequestHeader):
    pass


class CIDBQ01500ResponseHeader(BlockResponseHeader):
    pass


class CIDBQ01500InBlock1(BaseModel):
    """
    CIDBQ01500InBlock1 데이터 블록

    해외선물 미결제잔고내역 조회에 사용되는 입력 데이터 블록입니다.

    Attributes:
        RecCnt (int): 레코드갯수
        AcntTpCode (str): 계좌구분코드 (1:위탁)
        QryDt (str): 조회일자 (YYYYMMDD)
        BalTpCode (str): 잔고구분코드 (1:합산, 2:건별)
        FcmAcntNo (str): FCM계좌번호 (선택, 예제에 포함되어 있음)
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수 (예: 1)"
    )
    """레코드갯수"""

    AcntTpCode: str = Field(
        default="1",
        title="계좌구분코드",
        description="계좌구분코드 (1:위탁)"
    )
    """계좌구분코드 (1:위탁)"""

    QryDt: str = Field(
        default="",
        title="조회일자",
        description="조회일자 (YYYYMMDD)"
    )
    """조회일자 (YYYYMMDD)"""

    BalTpCode: str = Field(
        default="1",
        title="잔고구분코드",
        description="잔고구분코드 (1:합산, 2:건별)"
    )
    """잔고구분코드 (1:합산, 2:건별)"""

    FcmAcntNo: str = Field(
        default="",
        title="FCM계좌번호",
        description="FCM계좌번호 (예제에 존재하므로 선택적으로 포함)"
    )
    """FCM계좌번호 (선택)"""


class CIDBQ01500Request(BaseModel):
    """
    CIDBQ01500Request 데이터 블록

    해외선물 미결제잔고내역 조회 요청을 위한 데이터 블록입니다.

    Attributes:
        header (CIDBQ01500RequestHeader): 요청 헤더 데이터 블록
        body (CIDBQ01500InBlock1): 요청 본문 데이터 블록
    """
    header: CIDBQ01500RequestHeader = CIDBQ01500RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CIDBQ01500",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""

    body: dict[Literal["CIDBQ01500InBlock1"], CIDBQ01500InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 미결제잔고내역 조회를 위한 입력 데이터 블록"
    )
    """요청 본문 데이터 블록"""

    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CIDBQ01500"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CIDBQ01500OutBlock1(BaseModel):
    """
    CIDBQ01500OutBlock1 데이터 블록

    응답의 첫 번째 출력 블록으로 계좌 기본정보를 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        AcntTpCode (str): 계좌구분코드
        AcntNo (str): 계좌번호
        FcmAcntNo (str): FCM계좌번호
        Pwd (str): 비밀번호
        QryDt (str): 조회일자
        BalTpCode (str): 잔고구분코드
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""

    AcntTpCode: str = Field(
        default="",
        title="계좌구분코드",
        description="계좌구분코드"
    )
    """계좌구분코드"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""

    FcmAcntNo: str = Field(
        default="",
        title="FCM계좌번호",
        description="FCM계좌번호"
    )
    """FCM계좌번호"""

    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="비밀번호"
    )
    """비밀번호"""

    QryDt: str = Field(
        default="",
        title="조회일자",
        description="조회일자 (YYYYMMDD)"
    )
    """조회일자 (YYYYMMDD)"""

    BalTpCode: str = Field(
        default="",
        title="잔고구분코드",
        description="잔고구분코드"
    )
    """잔고구분코드"""


class CIDBQ01500OutBlock2(BaseModel):
    """
    CIDBQ01500OutBlock2 데이터 블록 (Occurs)

    응답의 두 번째 출력 블록으로 일별/종목별 상세 잔고 항목 리스트입니다.

    Attributes (주요):
        BaseDt (str): 기준일자
        Dps (float): 예수금
        LpnlAmt (float): 청산손익금액
        FutsDueBfLpnlAmt (float): 선물만기전청산손익금액
        FutsDueBfCmsn (float): 선물만기전수수료
        CsgnMgn (float): 위탁증거금액
        MaintMgn (float): 유지증거금
        CtlmtAmt (float): 신용한도금액
        AddMgn (float): 추가증거금액
        MgnclRat (float): 마진콜율
        OrdAbleAmt (float): 주문가능금액
        WthdwAbleAmt (float): 인출가능금액
        AcntNo (str): 계좌번호
        IsuCodeVal (str): 종목코드값
        IsuNm (str): 종목명
        CrcyCodeVal (str): 통화코드값
        OvrsDrvtPrdtCode (str): 해외파생상품코드
        OvrsDrvtOptTpCode (str): 해외파생옵션구분코드
        DueDt (str): 만기일자
        OvrsDrvtXrcPrc (float): 해외파생행사가격
        BnsTpCode (str): 매매구분코드
        CmnCodeNm (str): 공통코드명
        TpCodeNm (str): 구분코드명
        BalQty (float): 잔고수량
        PchsPrc (float): 매입가격
        OvrsDrvtNowPrc (float): 해외파생현재가
        AbrdFutsEvalPnlAmt (float): 해외선물평가손익금액
        CsgnCmsn (float): 위탁수수료
        PosNo (str): 포지션번호
        EufOneCmsnAmt (float): 거래소비용1수수료금액
        EufTwoCmsnAmt (float): 거래소비용2수수료금액
    """
    BaseDt: str = Field(
        default="",
        title="기준일자",
        description="기준일자 (YYYYMMDD)"
    )
    """기준일자"""

    Dps: float = Field(
        default=0.0,
        title="예수금",
        description="예수금"
    )
    """예수금"""

    LpnlAmt: float = Field(
        default=0.0,
        title="청산손익금액",
        description="청산손익금액"
    )
    """청산손익금액"""

    FutsDueBfLpnlAmt: float = Field(
        default=0.0,
        title="선물만기전청산손익금액",
        description="선물만기전청산손익금액"
    )
    """선물만기전청산손익금액"""

    FutsDueBfCmsn: float = Field(
        default=0.0,
        title="선물만기전수수료",
        description="선물만기전수수료"
    )
    """선물만기전수수료"""

    CsgnMgn: float = Field(
        default=0.0,
        title="위탁증거금액",
        description="위탁증거금액"
    )
    """위탁증거금액"""

    MaintMgn: float = Field(
        default=0.0,
        title="유지증거금",
        description="유지증거금"
    )
    """유지증거금"""

    CtlmtAmt: float = Field(
        default=0.0,
        title="신용한도금액",
        description="신용한도금액"
    )
    """신용한도금액"""

    AddMgn: float = Field(
        default=0.0,
        title="추가증거금액",
        description="추가증거금액"
    )
    """추가증거금액"""

    MgnclRat: float = Field(
        default=0.0,
        title="마진콜율",
        description="마진콜율"
    )
    """마진콜율"""

    OrdAbleAmt: float = Field(
        default=0.0,
        title="주문가능금액",
        description="주문가능금액"
    )
    """주문가능금액"""

    WthdwAbleAmt: float = Field(
        default=0.0,
        title="인출가능금액",
        description="인출가능금액"
    )
    """인출가능금액"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""

    IsuCodeVal: str = Field(
        default="",
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""

    IsuNm: str = Field(
        default="",
        title="종목명",
        description="종목명"
    )
    """종목명"""

    CrcyCodeVal: str = Field(
        default="",
        title="통화코드값",
        description="통화코드값"
    )
    """통화코드값"""

    OvrsDrvtPrdtCode: str = Field(
        default="",
        title="해외파생상품코드",
        description="해외파생상품코드"
    )
    """해외파생상품코드"""

    OvrsDrvtOptTpCode: str = Field(
        default="",
        title="해외파생옵션구분코드",
        description="해외파생옵션구분코드"
    )
    """해외파생옵션구분코드"""

    DueDt: str = Field(
        default="",
        title="만기일자",
        description="만기일자 (YYYYMMDD)"
    )
    """만기일자"""

    OvrsDrvtXrcPrc: float = Field(
        default=0.0,
        title="해외파생행사가격",
        description="해외파생행사가격"
    )
    """해외파생행사가격"""

    BnsTpCode: str = Field(
        default="",
        title="매매구분코드",
        description="매매구분코드 (1: 매도, 2: 매수)"
    )
    """매매구분코드 (1: 매도, 2: 매수)"""

    CmnCodeNm: str = Field(
        default="",
        title="공통코드명",
        description="공통코드명"
    )
    """공통코드명"""

    TpCodeNm: str = Field(
        default="",
        title="구분코드명",
        description="구분코드명"
    )
    """구분코드명"""

    BalQty: float = Field(
        default=0.0,
        title="잔고수량",
        description="잔고수량"
    )
    """잔고수량"""

    PchsPrc: float = Field(
        default=0.0,
        title="매입가격",
        description="매입가격"
    )
    """매입가격"""

    OvrsDrvtNowPrc: float = Field(
        default=0.0,
        title="해외파생현재가",
        description="해외파생현재가"
    )
    """해외파생현재가"""

    AbrdFutsEvalPnlAmt: float = Field(
        default=0.0,
        title="해외선물평가손익금액",
        description="해외선물평가손익금액"
    )
    """해외선물평가손익금액"""

    CsgnCmsn: float = Field(
        default=0.0,
        title="위탁수수료",
        description="위탁수수료"
    )
    """위탁수수료"""

    PosNo: str = Field(
        default="",
        title="포지션번호",
        description="포지션번호"
    )
    """포지션번호"""

    EufOneCmsnAmt: float = Field(
        default=0.0,
        title="거래소비용1수수료금액",
        description="거래소비용1수수료금액"
    )
    """거래소비용1수수료금액"""

    EufTwoCmsnAmt: float = Field(
        default=0.0,
        title="거래소비용2수수료금액",
        description="거래소비용2수수료금액"
    )
    """거래소비용2수수료금액"""


class CIDBQ01500Response(BaseModel):
    """
    CIDBQ01500 API에 대한 응답 클래스.

    Attributes:
        header (Optional[CIDBQ01500ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[CIDBQ01500OutBlock1]): 첫 번째 출력 블록
        block2 (List[CIDBQ01500OutBlock2]): 두 번째 출력 블록 리스트 (Occurs)
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        status_code (int): HTTP 상태 코드
        error_msg (Optional[str]): 오류 메시지
    """
    header: Optional[CIDBQ01500ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="CIDBQ01500 API 응답의 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    block1: Optional[CIDBQ01500OutBlock1] = Field(
        None,
        title="첫 번째 출력 블록",
        description="첫 번째 출력 블록"
    )
    """첫 번째 출력 블록"""

    block2: List[CIDBQ01500OutBlock2] = Field(
        default_factory=list,
        title="두 번째 출력 블록 리스트",
        description="두 번째 출력 블록 리스트"
    )
    """두 번째 출력 블록 리스트"""
    status_code: int = Field(
        ...,
        title="HTTP 상태 코드",
        description="API 호출에 대한 HTTP 상태 코드"
    )
    """HTTP 상태 코드"""
    rsp_cd: str = Field(
        ...,
        title="응답코드",
        description="API 호출 상태를 나타내는 응답 코드"
    )
    """응답코드"""

    rsp_msg: str = Field(
        ...,
        title="응답메시지",
        description="API 호출 결과에 대한 추가 정보를 제공하는 응답 메시지"
    )
    """응답메시지"""

    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지",
        description="오류 발생 시 오류 메시지"
    )
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
