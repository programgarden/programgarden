from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSAQ01400RequestHeader(BlockRequestHeader):
    pass


class COSAQ01400ResponseHeader(BlockResponseHeader):
    pass


class COSAQ01400InBlock1(BaseModel):
    """
    COSAQ01400InBlock1 데이터 블록

    LS증권 OpenAPI의 COSAQ01400 예약주문 처리결과 조회에 사용되는 입력 데이터 블록입니다.

    Attributes:
        RecCnt (int): 레코드갯수
        QryTpCode (str): 조회구분코드
        CntryCode (str): 국가코드
        SrtDt (str): 시작일자
        EndDt (str): 종료일자
        BnsTpCode (str): 매매구분코드
        RsvOrdCndiCode (str): 예약주문조건코드
        RsvOrdStatCode (str): 예약주문상태코드
    """
    RecCnt: int = Field(
        default=1,
        title="레코드 갯수",
        description="레코드 갯수 (예: 1건)"
    )
    """레코드갯수"""
    QryTpCode: str = Field(
        default="1",
        title="조회구분코드",
        description="조회 구분 코드"
    )
    """조회구분코드 1@계좌별"""

    CntryCode: str = Field(
        ...,
        title="국가코드",
        description="국가 코드"
    )
    """국가코드"""

    SrtDt: str = Field(
        ...,
        title="시작일자",
        description="시작 일자"
    )
    """시작일자"""

    EndDt: str = Field(
        ...,
        title="종료일자",
        description="종료 일자"
    )
    """종료일자"""

    BnsTpCode: str = Field(
        ...,
        title="매매구분코드",
        description="매매 구분 코드"
    )
    """매매구분코드 0@전체, 1@매도, 2@매수"""

    RsvOrdCndiCode: str = Field(
        ...,
        title="예약주문조건코드",
        description="예약 주문 조건 코드"
    )
    """예약주문조건코드"""

    RsvOrdStatCode: str = Field(
        ...,
        title="예약주문상태코드",
        description="예약 주문 상태 코드"
    )
    """예약주문상태코드"""


class COSAQ01400Request(BaseModel):
    """
    COSAQ01400 API 요청 클래스.

    Attributes:
        header (COSAQ01400RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["COSAQ01400InBlock1"], COSAQ01400InBlock1]): 주문 내역 조회를 위한 입력 데이터 블록.
    """
    header: COSAQ01400RequestHeader = Field(
        COSAQ01400RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSAQ01400",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="API 요청에 필요한 헤더 정보"
    )
    """요청 헤더 데이터 블록"""

    body: dict[Literal["COSAQ01400InBlock1"], COSAQ01400InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="주문 내역 조회를 위한 입력 데이터 블록"
    )
    """ 입력 데이터 블록"""

    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="COSAQ01400"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class COSAQ01400OutBlock1(BaseModel):
    """
    COSAQ01400OutBlock1 데이터 블록

    LS증권 OpenAPI의 COSAQ01400 예약주문 처리결과 조회 응답 첫 번째 출력 블록입니다.

    Attributes:
        RecCnt (int): 레코드갯수
        QryTpCode (str): 조회구분코드
        CntryCode (str): 국가코드
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        SrtDt (str): 시작일자
        EndDt (str): 종료일자
        BnsTpCode (str): 매매구분코드
        RsvOrdCndiCode (str): 예약주문조건코드
        RsvOrdStatCode (str): 예약주문상태코드
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""
    QryTpCode: str = Field(
        default="1",
        title="조회구분코드",
        description="조회 구분 코드 (예: 1@계좌별)"
    )
    """조회구분코드"""
    CntryCode: str = Field(
        default="",
        title="국가코드",
        description="국가 코드"
    )
    """국가코드"""
    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌 번호"
    )
    """계좌번호"""
    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="계좌 비밀번호"
    )
    """비밀번호"""
    SrtDt: str = Field(
        default="",
        title="시작일자",
        description="조회 시작일자 (YYYYMMDD)"
    )
    """시작일자"""
    EndDt: str = Field(
        default="",
        title="종료일자",
        description="조회 종료일자 (YYYYMMDD)"
    )
    """종료일자"""
    BnsTpCode: str = Field(
        default="0",
        title="매매구분코드",
        description="매매 구분 코드 (0@전체, 1@매도, 2@매수)"
    )
    """매매구분코드"""
    RsvOrdCndiCode: str = Field(
        default="",
        title="예약주문조건코드",
        description="예약 주문 조건 코드"
    )
    """예약주문조건코드"""
    RsvOrdStatCode: str = Field(
        default="",
        title="예약주문상태코드",
        description="예약 주문 상태 코드"
    )
    """예약주문상태코드"""


class COSAQ01400OutBlock2(BaseModel):
    """
    COSAQ01400OutBlock2 데이터 블록

    LS증권 OpenAPI의 COSAQ01400 예약주문 처리결과 조회 응답 두 번째 출력 블록입니다.

    Attributes:
        AcntNo (str): 계좌번호
        AcntNm (str): 계좌명
        OrdDt (str): 주문일자
        OrdNo (int): 주문번호
        RsvOrdInptDt (str): 예약주문입력일자
        RsvOrdNo (int): 예약주문번호
        ShtnIsuNo (str): 단축종목번호
        JpnMktHanglIsuNm (str): 일본시장한글종목명
        OrdQty (int): 주문수량
        OrdprcPtnNm (str): 호가유형명
        OvrsOrdPrc (float): 해외주문가
        BnsTpNm (str): 매매구분명
        ExecQty (int): 체결수량
        UnercQty (int): 미체결수량
        TotExecQty (int): 총체결수량
        CrcyCode (str): 통화코드
        RsvOrdStatCode (str): 예약주문상태코드
        MktTpNm (str): 시장구분명
        ErrCnts (str): 오류내용
        LoanDt (str): 대출일자
        MgntrnCode (str): 신용거래코드
    """
    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""
    AcntNm: str = Field(
        default="",
        title="계좌명",
        description="계좌명"
    )
    """계좌명"""
    OrdDt: str = Field(
        default="",
        title="주문일자",
        description="주문일자 (YYYYMMDD)"
    )
    """주문일자"""
    OrdNo: int = Field(
        default=0,
        title="주문번호",
        description="주문번호"
    )
    """주문번호"""
    RsvOrdInptDt: str = Field(
        default="",
        title="예약주문입력일자",
        description="예약주문 입력일자"
    )
    """예약주문입력일자"""
    RsvOrdNo: int = Field(
        default=0,
        title="예약주문번호",
        description="예약주문번호"
    )
    """예약주문번호"""
    ShtnIsuNo: str = Field(
        default="",
        title="단축종목번호",
        description="단축 종목 번호"
    )
    """단축종목번호"""
    JpnMktHanglIsuNm: str = Field(
        default="",
        title="일본시장한글종목명",
        description="일본시장 한글 종목명"
    )
    """일본시장한글종목명"""
    OrdQty: int = Field(
        default=0,
        title="주문수량",
        description="주문 수량"
    )
    """주문수량"""
    OrdprcPtnNm: str = Field(
        default="",
        title="호가유형명",
        description="호가 유형명"
    )
    """호가유형명"""
    OvrsOrdPrc: float = Field(
        default=0.0,
        title="해외주문가",
        description="해외 주문 가격"
    )
    """해외주문가"""
    BnsTpNm: str = Field(
        default="",
        title="매매구분명",
        description="매매구분명"
    )
    """매매구분명"""
    ExecQty: int = Field(
        default=0,
        title="체결수량",
        description="체결 수량"
    )
    """체결수량"""
    UnercQty: int = Field(
        default=0,
        title="미체결수량",
        description="미체결 수량"
    )
    """미체결수량"""
    TotExecQty: int = Field(
        default=0,
        title="총체결수량",
        description="총 체결 수량"
    )
    """총체결수량"""
    CrcyCode: str = Field(
        default="",
        title="통화코드",
        description="통화 코드"
    )
    """통화코드"""
    RsvOrdStatCode: str = Field(
        default="",
        title="예약주문상태코드",
        description="예약주문 상태 코드"
    )
    """예약주문상태코드"""
    MktTpNm: str = Field(
        default="",
        title="시장구분명",
        description="시장 구분명"
    )
    """시장구분명"""
    ErrCnts: str = Field(
        default="",
        title="오류내용",
        description="오류 내용"
    )
    """오류내용"""
    LoanDt: str = Field(
        default="",
        title="대출일자",
        description="대출일자 (YYYYMMDD)"
    )
    """대출일자"""
    MgntrnCode: str = Field(
        default="",
        title="신용거래코드",
        description="신용거래코드"
    )
    """신용거래코드"""


class COSAQ01400Response(BaseModel):
    """
    COSAQ01400 API에 대한 응답 클래스.

    Attributes:
        header (Optional[COSAQ01400ResponseHeader]): 요청 헤더 데이터 블록
        COSAQ01400OutBlock1 (Optional[COSAQ01400OutBlock1]): 첫 번째 출력 블록
        COSAQ01400OutBlock2 (List[COSAQ01400OutBlock2]): 두 번째 출력 블록 리스트
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류 메시지 (오류 발생 시)
    """
    header: Optional[COSAQ01400ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    block1: Optional[COSAQ01400OutBlock1] = Field(
        None,
        title="첫 번째 출력 블록",
        description="첫 번째 출력 블록"
    )
    """첫 번째 출력 블록"""
    block2: List[COSAQ01400OutBlock2] = Field(
        default_factory=list,
        title="두 번째 출력 블록 리스트",
        description="두 번째 출력 블록 리스트"
    )
    """두 번째 출력 블록 리스트"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    """HTTP 상태 코드"""
    rsp_cd: str = Field(
        ...,
        title="응답코드",
        description="응답코드"
    )
    """응답코드"""
    rsp_msg: str = Field(
        ...,
        title="응답메시지",
        description="응답메시지"
    )
    """응답메시지"""
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지",
        description="오류 메시지 (오류 발생 시)"
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
