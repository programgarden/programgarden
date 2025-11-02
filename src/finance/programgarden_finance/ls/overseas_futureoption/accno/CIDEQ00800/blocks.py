from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDEQ00800RequestHeader(BlockRequestHeader):
    pass


class CIDEQ00800ResponseHeader(BlockResponseHeader):
    pass


class CIDEQ00800InBlock1(BaseModel):
    """
    CIDEQ00800InBlock1 데이터 블록

    일자별 미결제 잔고내역 조회에 사용되는 입력 데이터 블록입니다.

    Attributes:
        RecCnt (int): 레코드갯수
        TrdDt (str): 거래일자 (YYYYMMDD)
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수 (예: 1)"
    )
    """레코드갯수"""

    TrdDt: str = Field(
        default="",
        title="거래일자",
        description="거래일자 (YYYYMMDD)"
    )
    """거래일자 (YYYYMMDD)"""


class CIDEQ00800Request(BaseModel):
    """
    CIDEQ00800Request 데이터 블록

    일자별 미결제 잔고내역 조회 요청을 위한 데이터 블록입니다.

    Attributes:
        header (CIDEQ00800RequestHeader): 요청 헤더 데이터 블록
        body (CIDEQ00800InBlock1): 요청 본문 데이터 블록
    """
    header: CIDEQ00800RequestHeader = CIDEQ00800RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CIDEQ00800",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""

    body: dict[Literal["CIDEQ00800InBlock1"], CIDEQ00800InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="일자별 미결제 잔고내역 조회를 위한 입력 데이터 블록"
    )
    """요청 본문 데이터 블록"""

    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CIDEQ00800"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CIDEQ00800OutBlock1(BaseModel):
    """
    CIDEQ00800OutBlock1 데이터 블록

    응답의 첫 번째 출력 블록으로 계좌 기본정보를 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        AcntNo (str): 계좌번호
        AcntPwd (str): 계좌비밀번호
        TrdDt (str): 거래일자
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""

    AcntPwd: str = Field(
        default="",
        title="계좌비밀번호",
        description="계좌비밀번호"
    )
    """계좌비밀번호"""

    TrdDt: str = Field(
        default="",
        title="거래일자",
        description="거래일자 (YYYYMMDD)"
    )
    """거래일자 (YYYYMMDD)"""


class CIDEQ00800OutBlock2(BaseModel):
    """
    CIDEQ00800OutBlock2 데이터 블록 (Occurs)

    응답의 두 번째 출력 블록으로 일별/종목별 상세 잔고 항목 리스트입니다.

    Attributes (주요):
        AcntNo (str): 계좌번호
        TrdDt (str): 거래일자
        IsuCodeVal (str): 종목코드값
        BnsTpNm (str): 매매구분명
        BalQty (float): 잔고수량
        LqdtAbleQty (float): 청산가능수량
        PchsPrc (float): 매입가격
        OvrsDrvtNowPrc (float): 해외파생현재가
        AbrdFutsEvalPnlAmt (float): 해외선물평가손익금액
        CustmBalAmt (float): 고객잔고금액
        FcurrEvalAmt (float): 외화평가금액
        IsuNm (str): 종목명
        CrcyCodeVal (str): 통화코드값
        OvrsDrvtPrdtCode (str): 해외파생상품코드
        DueDt (str): 만기일자
        PrcntrAmt (float): 계약당금액
        FcurrEvalPnlAmt (float): 외화평가손익금액
    """
    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""

    TrdDt: str = Field(
        default="",
        title="거래일자",
        description="거래일자 (YYYYMMDD)"
    )
    """거래일자 (YYYYMMDD)"""

    IsuCodeVal: str = Field(
        default="",
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""

    BnsTpNm: str = Field(
        default="",
        title="매매구분명",
        description="매매구분명"
    )
    """매매구분명"""

    BalQty: float = Field(
        default=0.0,
        title="잔고수량",
        description="잔고수량"
    )
    """잔고수량"""

    LqdtAbleQty: float = Field(
        default=0.0,
        title="청산가능수량",
        description="청산가능수량"
    )
    """청산가능수량"""

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

    CustmBalAmt: float = Field(
        default=0.0,
        title="고객잔고금액",
        description="고객잔고금액"
    )
    """고객잔고금액"""

    FcurrEvalAmt: float = Field(
        default=0.0,
        title="외화평가금액",
        description="외화평가금액"
    )
    """외화평가금액"""

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

    DueDt: str = Field(
        default="",
        title="만기일자",
        description="만기일자 (YYYYMMDD)"
    )
    """만기일자 (YYYYMMDD)"""

    PrcntrAmt: float = Field(
        default=0.0,
        title="계약당금액",
        description="계약당금액"
    )
    """계약당금액"""

    FcurrEvalPnlAmt: float = Field(
        default=0.0,
        title="외화평가손익금액",
        description="외화평가손익금액"
    )
    """외화평가손익금액"""


class CIDEQ00800Response(BaseModel):
    """
    CIDEQ00800 API에 대한 응답 클래스.

    Attributes:
        header (Optional[CIDEQ00800ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[CIDEQ00800OutBlock1]): 첫 번째 출력 블록
        block2 (List[CIDEQ00800OutBlock2]): 두 번째 출력 블록 리스트 (Occurs)
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류 메시지
    """
    header: Optional[CIDEQ00800ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="CIDEQ00800 API 응답의 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    block1: Optional[CIDEQ00800OutBlock1] = Field(
        None,
        title="첫 번째 출력 블록",
        description="첫 번째 출력 블록"
    )
    """첫 번째 출력 블록"""

    block2: List[CIDEQ00800OutBlock2] = Field(
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
