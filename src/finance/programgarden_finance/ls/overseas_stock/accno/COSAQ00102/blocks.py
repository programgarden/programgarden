from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSAQ00102RequestHeader(BlockRequestHeader):
    pass


class COSAQ00102ResponseHeader(BlockResponseHeader):
    pass


class COSAQ00102InBlock1(BaseModel):
    """
    COSAQ00102InBlock1 데이터 블록

    LS증권 OpenAPI의 COSAQ00102 계좌 주문 내역 조회에 사용되는 입력 데이터 블록입니다.

    Attributes:
        RecCnt (int): 레코드 갯수 (예: 1건)
        QryTpCode (str): 조회 구분 코드 (1: 계좌별)
        BkseqTpCode (str): 역순 구분 코드 (1: 역순, 2: 정순)
        OrdMktCode (str): 주문 시장 코드 (81: 뉴욕, 82: 나스닥 등)
        BnsTpCode (str): 매매 구분 코드 (0: 전체, 1: 매도, 2: 매수)
        IsuNo (str): 종목 번호 (전체: 빈값)
        SrtOrdNo (int): 시작 주문 번호 (역순: 999999999, 정순: 0)
        OrdDt (str): 주문 일자 (조회 시작일)
        ExecYn (str): 체결 여부 (0: 전체, 1: 체결, 2: 미체결)
        CrcyCode (str): 통화 코드 (000: 전체, USD: 미국)
        ThdayBnsAppYn (str): 당일 매매 적용 여부 (0: 미적용, 1: 적용)
        LoanBalHldYn (str): 대출 잔고 보유 여부 (0: 전체, 1: 대출 잔고만)
    """

    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드 갯수 (예: 1건)"
    )
    """레코드 갯수 (예: 1건)"""

    QryTpCode: Literal["1"] = Field(
        default="1",
        title="조회구분코드",
        description="1@계좌별",
    )
    """조회구분코드 1@계좌별"""

    BkseqTpCode: str = Field(
        default="1",
        title="역순구분코드",
        description="1@역순, 2@정순",
    )
    """역순구분코드 1@역순, 2@정순"""

    OrdMktCode: str = Field(
        default="81",
        title="주문시장코드",
        description="81@뉴욕, 82@나스닥 등"
    )
    """주문시장코드 81@뉴욕, 82@나스닥 등"""

    BnsTpCode: str = Field(
        default="0",
        title="매매구분코드",
        description="0@전체, 1@매도, 2@매수"
    )
    """매매구분코드 0@전체, 1@매도, 2@매수"""

    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="전체: 빈값"
    )
    """종목번호 전체: 빈값"""

    SrtOrdNo: int = Field(
        default=999999999,
        title="시작주문번호",
        description="역순: 999999999, 정순: 0"
    )
    """시작주문번호 역순: 999999999, 정순: 0"""

    OrdDt: str = Field(
        ...,
        title="주문일자",
        description="조회 시작일"
    )
    """주문일자 조회 시작일"""

    ExecYn: str = Field(
        default="0",
        title="체결여부",
        description="0@전체, 1@체결, 2@미체결"
    )
    """체결여부 0@전체, 1@체결, 2@미체결"""

    CrcyCode: str = Field(
        default="000",
        title="통화코드",
        description="000@전체, USD@미국"
    )
    """통화코드 000@전체, USD@미국"""

    ThdayBnsAppYn: str = Field(
        default="0",
        title="당일매매적용여부",
        description="0@미적용, 1@적용"
    )
    """당일매매적용여부 0@미적용, 1@적용"""

    LoanBalHldYn: str = Field(
        default="0",
        title="대출잔고보유여부",
        description="0@전체, 1@대출잔고만"
    )
    """대출잔고보유여부 0@전체, 1@대출잔고만"""


class COSAQ00102Request(BaseModel):
    """
    COSAQ00102 API 요청 클래스.

    Attributes:
        header (COSAQ00102RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["COSAQ00102InBlock1"], COSAQ00102InBlock1]): 주문 내역 조회를 위한 입력 데이터 블록.
    """
    header: COSAQ00102RequestHeader = Field(
        COSAQ00102RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSAQ00102",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="COSAQ00102 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["COSAQ00102InBlock1"], COSAQ00102InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="주문 내역 조회를 위한 입력 데이터 블록"
    )
    """입력 데이터 블록"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=2,
            on_rate_limit="wait",
            rate_limit_key="COSAQ00102"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class COSAQ00102OutBlock1(BaseModel):
    """
    COSAQ00102OutBlock1 데이터 블록

    LS증권 OpenAPI의 COSAQ00102 계좌 주문 내역 조회에 사용되는 출력 데이터 블록입니다.
    이 블록은 주문 내역 조회 요청에 대한 응답 정보를 포함하고 있습니다.

    Attributes:
        RecCnt (int): 레코드 갯수
        QryTpCode (str): 조회 구분 코드
        BkseqTpCode (str): 역순 구분 코드
        OrdMktCode (str): 주문 시장 코드
        AcntNo (str): 계좌 번호
        Pwd (str): 비밀번호
        BnsTpCode (str): 매매 구분 코드
        IsuNo (str): 종목 번호
        SrtOrdNo (int): 시작 주문 번호
        OrdDt (str): 주문 일자
        ExecYn (str): 체결 여부
        CrcyCode (str): 통화 코드
        ThdayBnsAppYn (str): 당일 매매 적용 여부
        LoanBalHldYn (str): 대출 잔고 보유 여부
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""

    QryTpCode: str = Field(
        default="",
        title="조회구분코드",
        description="1: 계좌별 조회"
    )
    """조회구분코드"""

    BkseqTpCode: str = Field(
        default="",
        title="역순구분코드",
        description="1: 역순, 2: 정순"
    )
    """역순구분코드"""

    OrdMktCode: str = Field(
        default="81",
        title="주문시장코드",
        description="81: 뉴욕, 82: 나스닥 등"
    )
    """주문시장코드"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="조회 대상 계좌 번호"
    )
    """계좌번호"""

    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="계좌 비밀번호"
    )
    """비밀번호"""

    BnsTpCode: str = Field(
        default="",
        title="매매구분코드",
        description="0: 전체, 1: 매도, 2: 매수"
    )
    """매매구분코드"""

    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="종목 번호, 전체 호출 시 빈값"
    )
    """종목번호"""

    SrtOrdNo: int = Field(
        default=0,
        title="시작주문번호",
        description="시작 주문 번호 (역순: 큰 값)"
    )
    """시작주문번호"""

    OrdDt: str = Field(
        default="",
        title="주문일자",
        description="주문일자 (YYYYMMDD)"
    )
    """주문일자"""

    ExecYn: str = Field(
        default="",
        title="체결여부",
        description="0: 전체, 1: 체결, 2: 미체결"
    )
    """체결여부"""

    CrcyCode: str = Field(
        default="",
        title="통화코드",
        description="000: 전체, USD: 미국 달러"
    )
    """통화코드"""

    ThdayBnsAppYn: str = Field(
        default="",
        title="당일매매적용여부",
        description="0: 미적용, 1: 적용"
    )
    """당일매매적용여부"""

    LoanBalHldYn: str = Field(
        default="",
        title="대출잔고보유여부",
        description="0: 전체, 1: 대출 잔고만"
    )
    """대출잔고보유여부"""


class COSAQ00102OutBlock2(BaseModel):
    """
    COSAQ00102OutBlock2 데이터 블록

    LS증권 OpenAPI의 COSAQ00102 계좌 주문 내역 조회에 사용되는 출력 데이터 블록입니다.
    이 블록은 계좌별 매도/매수 체결 정보를 포함하고 있습니다.

    Attributes:
        RecCnt (int): 레코드 갯수
        AcntNm (str): 계좌명
        JpnMktHanglIsuNm (str): 일본시장한글종목명
        MgmtBrnNm (str): 관리지점명
        SellExecFcurrAmt (str): 매도체결외화금액
        SellExecQty (int): 매도체결수량
        BuyExecFcurrAmt (str): 매수체결외화금액
        BuyExecQty (int): 매수체결수량
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""

    AcntNm: str = Field(
        default="",
        title="계좌명",
        description="조회된 계좌 이름"
    )
    """계좌명"""

    JpnMktHanglIsuNm: str = Field(
        default="",
        title="일본시장한글종목명",
        description="일본시장 한글 종목명"
    )
    """일본시장한글종목명"""

    MgmtBrnNm: str = Field(
        default="",
        title="관리지점명",
        description="관리 지점 이름"
    )
    """관리지점명"""

    SellExecFcurrAmt: str = Field(
        default="",
        title="매도체결외화금액",
        description="매도 체결된 외화 금액"
    )
    """매도체결외화금액"""

    SellExecQty: int = Field(
        default=0,
        title="매도체결수량",
        description="매도 체결된 수량"
    )
    """매도체결수량"""

    BuyExecFcurrAmt: str = Field(
        default="",
        title="매수체결외화금액",
        description="매수 체결된 외화 금액"
    )
    """매수체결외화금액"""

    BuyExecQty: int = Field(
        default=0,
        title="매수체결수량",
        description="매수 체결된 수량"
    )
    """매수체결수량"""


class COSAQ00102OutBlock3(BaseModel):
    """
    COSAQ00102OutBlock3 데이터 블록

    LS증권 OpenAPI의 COSAQ00102 계좌 주문 내역 조회에 사용되는 출력 데이터 블록입니다.
    이 블록은 개별 주문 및 체결에 대한 상세 정보를 포함하고 있습니다.

    Attributes:
        MgmtBrnNo (str): 관리지점번호
        AcntNo (str): 계좌번호
        AcntNm (str): 계좌명
        ExecTime (str): 체결시각
        OrdTime (str): 주문시각
        OrdNo (int): 주문번호
        OrgOrdNo (int): 원주문번호
        ShtnIsuNo (str): 단축종목번호
        OrdTrxPtnNm (str): 주문처리유형명
        OrdTrxPtnCode (int): 주문처리유형코드
        MrcAbleQty (int): 정정취소가능수량
        OrdQty (int): 주문수량
        OvrsOrdPrc (float): 해외주문가
        ExecQty (int): 체결수량
        OvrsExecPrc (float): 해외체결가
        OrdprcPtnCode (str): 호가유형코드
        OrdprcPtnNm (str): 호가유형명
        OrdPtnNm (str): 주문유형명
        OrdPtnCode (str): 주문유형코드
        MrcTpCode (str): 정정취소구분코드
        MrcTpNm (str): 정정취소구분명
        AllExecQty (int): 전체체결수량
        CommdaCode (str): 통신매체코드
        OrdMktCode (str): 주문시장코드
        MktNm (str): 시장명
        CommdaNm (str): 통신매체명
        JpnMktHanglIsuNm (str): 일본시장한글종목명
        UnercQty (int): 미체결수량
        CnfQty (int): 확인수량
        CrcyCode (str): 통화코드
        RegMktCode (str): 등록시장코드
        IsuNo (str): 종목번호
        BrkTpCode (str): 중개인구분코드
        OppBrkNm (str): 상대중개인명
        BnsTpCode (str): 매매구분코드
        LoanDt (str): 대출일자
        LoanAmt (float): 대출금액
    """
    MgmtBrnNo: str = Field(
        default="",
        title="관리지점번호",
        description="관리 지점 번호"
    )
    """관리지점번호"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌 번호"
    )
    """계좌번호"""

    AcntNm: str = Field(
        default="",
        title="계좌명",
        description="계좌 이름"
    )
    """계좌명"""

    ExecTime: str = Field(
        default="",
        title="체결시각",
        description="체결 시각 (HHMMSSmmm)"
    )
    """체결시각"""

    OrdTime: str = Field(
        default="",
        title="주문시각",
        description="주문 시각 (HHMMSSmmm)"
    )
    """주문시각"""

    OrdNo: int = Field(
        default=0,
        title="주문번호",
        description="주문 번호"
    )
    """주문번호"""

    OrgOrdNo: int = Field(
        default=0,
        title="원주문번호",
        description="원 주문 번호"
    )
    """원주문번호"""

    ShtnIsuNo: str = Field(
        default="",
        title="단축종목번호",
        description="단축 종목 번호"
    )
    """단축종목번호"""

    OrdTrxPtnNm: str = Field(
        default="",
        title="주문처리유형명",
        description="주문 처리 유형명"
    )
    """주문처리유형명"""

    OrdTrxPtnCode: int = Field(
        default="",
        title="주문처리유형코드",
        description="주문 처리 유형 코드"
    )
    """주문처리유형코드"""

    MrcAbleQty: int = Field(
        default=0,
        title="정정취소가능수량",
        description="정정/취소 가능한 수량"
    )
    """정정취소가능수량"""

    OrdQty: int = Field(
        default=0,
        title="주문수량",
        description="주문 수량"
    )
    """注文수량"""

    OvrsOrdPrc: float = Field(
        default=0.0,
        title="해외주문가",
        description="해외 주문 가격"
    )
    """해외주문가"""

    ExecQty: int = Field(
        default=0,
        title="체결수량",
        description="체결된 수량"
    )
    """체결수량"""

    OvrsExecPrc: float = Field(
        default=0.0,
        title="해외체결가",
        description="해외 체결 가격"
    )
    """해외체결가"""

    OrdprcPtnCode: str = Field(
        default="",
        title="호가유형코드",
        description="호가 유형 코드"
    )
    """호가유형코드"""

    OrdprcPtnNm: str = Field(
        default="",
        title="호가유형명",
        description="호가 유형명"
    )
    """호가유형명"""

    OrdPtnNm: str = Field(
        default="",
        title="주문유형명",
        description="주문 유형명"
    )
    """주문유형명"""

    OrdPtnCode: str = Field(
        default="",
        title="주문유형코드",
        description="주문 유형 코드"
    )
    """주문유형코드"""

    MrcTpCode: str = Field(
        default="",
        title="정정취소구분코드",
        description="정정/취소 구분 코드"
    )
    """정정취소구분코드"""

    MrcTpNm: str = Field(
        default="",
        title="정정취소구분명",
        description="정정/취소 구분명"
    )
    """정정취소구분명"""

    AllExecQty: int = Field(
        default=0,
        title="전체체결수량",
        description="전체 체결 수량"
    )
    """전체체결수량"""

    CommdaCode: str = Field(
        default="",
        title="통신매체코드",
        description="통신 매체 코드"
    )
    """통신매체코드"""

    OrdMktCode: str = Field(
        default="",
        title="주문시장코드",
        description="81: 뉴욕, 82: 나스닥 등"
    )
    """주문시장코드"""

    MktNm: str = Field(
        default="",
        title="시장명",
        description="시장명"
    )
    """시장명"""

    CommdaNm: str = Field(
        default="",
        title="통신매체명",
        description="통신 매체명"
    )
    """통신매체명"""

    JpnMktHanglIsuNm: str = Field(
        default="",
        title="일본시장한글종목명",
        description="일본시장 한글 종목명"
    )
    """일본시장한글종목명"""

    UnercQty: int = Field(
        default=0,
        title="미체결수량",
        description="미체결 수량"
    )
    """미체결수량"""

    CnfQty: int = Field(
        default=0,
        title="확인수량",
        description="확인 수량"
    )
    """확인수량"""

    CrcyCode: str = Field(
        default="",
        title="통화코드",
        description="통화 코드"
    )
    """통화코드"""

    RegMktCode: str = Field(
        default="",
        title="등록시장코드",
        description="등록 시장 코드"
    )
    """등록시장코드"""

    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="종목 번호"
    )
    """종목번호"""

    BrkTpCode: str = Field(
        default="",
        title="중개인구분코드",
        description="중개인 구분 코드"
    )
    """중개인구분코드"""

    OppBrkNm: str = Field(
        default="",
        title="상대중개인명",
        description="상대 중개인명"
    )
    """상대중개인명"""

    BnsTpCode: str = Field(
        default="",
        title="매매구분코드",
        description="0: 전체, 1: 매도, 2: 매수"
    )
    """매매구분코드"""

    LoanDt: str = Field(
        default="",
        title="대출일자",
        description="대출일자 (YYYYMMDD)"
    )
    """대출일자"""

    LoanAmt: float = Field(
        default=0.0,
        title="대출금액",
        description="대출 금액"
    )
    """대출금액"""


class COSAQ00102Response(BaseModel):
    """
    COSAQ00102 API에 대한 응답 클래스.

    Attributes:
        header (Optional[COSAQ00102ResponseHeader]): 요청 헤더 데이터 블록, None일 경우 헤더가 없는 응답.
        COSAQ00102OutBlock1 (Optional[COSAQ00102OutBlock1]): 일반 응답 데이터가 포함된 첫 번째 출력 블록.
        COSAQ00102OutBlock2 (Optional[COSAQ00102OutBlock2]): 추가 응답 데이터가 포함된 두 번째 출력 블록.
        COSAQ00102OutBlock3 (List[COSAQ00102OutBlock3]): 세 번째 출력 블록 항목 목록으로, 상세 데이터 기록 또는 거래를 나타냅니다.
        rsp_cd (str): API 호출 상태를 나타내는 응답 코드.
        rsp_msg (str): API 호출 결과에 대한 추가 정보를 제공하는 응답 메시지.
        error_msg (Optional[str]): 오류 발생 시 오류 메시지, 없을 경우 None.
    """
    header: Optional[COSAQ00102ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="COSAQ00102 API 응답을 위한 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    block1: Optional[COSAQ00102OutBlock1] = Field(
        None,
        title="첫번째 출력 블록",
        description="COSAQ00102 API 응답의 첫번째 출력 블록"
    )
    """첫번째 출력 블록"""
    block2: Optional[COSAQ00102OutBlock2] = Field(
        None,
        title="두번째 출력 블록",
        description="COSAQ00102 API 응답의 두번째 출력 블록"
    )
    """두번째 출력 블록"""
    block3: List[COSAQ00102OutBlock3] = Field(
        default_factory=list,
        title="세번째 출력 블록 리스트",
        description="COSAQ00102 API 응답의 세번째 출력 블록 리스트"
    )
    """세번째 출력 블록 리스트"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    """HTTP 상태 코드"""
    rsp_cd: str = Field(
        ...,
        title="응답 코드",
        description="COSAQ00102 API 응답의 상태 코드"
    )
    """응답 코드"""
    rsp_msg: str = Field(
        ...,
        title="응답 메시지",
        description="COSAQ00102 API 응답의 상태 메시지"
    )
    """응답 메시지"""
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지",
        description="COSAQ00102 API 응답의 오류 메시지"
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
