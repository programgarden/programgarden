from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSOQ00201RequestHeader(BlockRequestHeader):
    pass


class COSOQ00201ResponseHeader(BlockResponseHeader):
    pass


class COSOQ00201InBlock1(BaseModel):
    """
    COSOQ00201InBlock1 데이터 블록

    LS증권 OpenAPI의 COSOQ00201 해외주식 종합잔고평가 조회에 사용되는 입력 데이터 블록입니다.

    Attributes:
        RecCnt (int): 레코드갯수 (예: 1)
        BaseDt (str): 기준일자 (YYYYMMDD)
        CrcyCode (str): 통화코드 (ALL: 전체, USD: 미국 등)
        AstkBalTpCode (str): 해외증권잔고구분코드 (00: 전체, 10: 일반, 20: 소수점)
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수 (예: 1)"
    )
    """레코드갯수"""

    BaseDt: str = Field(
        default="",
        title="기준일자",
        description="기준일자 (YYYYMMDD)"
    )
    """기준일자 (YYYYMMDD)"""

    CrcyCode: str = Field(
        default="ALL",
        title="통화코드",
        description="통화코드 (ALL: 전체, USD: 미국 등)"
    )
    """통화코드 (ALL: 전체, USD: 미국 등)"""

    AstkBalTpCode: str = Field(
        default="00",
        title="해외증권잔고구분코드",
        description="해외증권잔고구분코드 (00: 전체, 10: 일반, 20: 소수점)"
    )
    """해외증권잔고구분코드 (00: 전체, 10: 일반, 20: 소수점)"""


class COSOQ00201Request(BaseModel):
    """
    COSOQ00201Request 데이터 블록
    해외주식 종합잔고평가 조회 요청을 위한 데이터 블록입니다.

    Attributes:
        header (COSOQ00201RequestHeader): 요청 헤더 데이터 블록
        body (COSOQ00201InBlock1): 요청 본문 데이터 블록
    """
    header: COSOQ00201RequestHeader = COSOQ00201RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="COSOQ00201",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["COSOQ00201InBlock1"], COSOQ00201InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="해외주식 종합잔고평가 조회를 위한 입력 데이터 블록"
    )
    """요청 본문 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=2,
        on_rate_limit="wait",
        rate_limit_key="COSOQ00201"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class COSOQ00201OutBlock1(BaseModel):
    """
    COSOQ00201OutBlock1 데이터 블록

    응답의 첫 번째 출력 블록으로 계좌 기본정보를 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        BaseDt (str): 기준일자
        CrcyCode (str): 통화코드
        AstkBalTpCode (str): 해외증권잔고구분코드
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

    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="비밀번호"
    )
    """비밀번호"""

    BaseDt: str = Field(
        default="",
        title="기준일자",
        description="기준일자 (YYYYMMDD)"
    )
    """기준일자"""

    CrcyCode: str = Field(
        default="",
        title="통화코드",
        description="통화코드"
    )
    """통화코드"""

    AstkBalTpCode: str = Field(
        default="",
        title="해외증권잔고구분코드",
        description="해외증권잔고구분코드"
    )
    """해외증권잔고구분코드"""


class COSOQ00201OutBlock2(BaseModel):
    """
    COSOQ00201OutBlock2 데이터 블록

    응답의 두 번째 출력 블록으로 전체 평가 요약을 포함합니다.

    Attributes:
        RecCnt (int): 레코드갯수
        ErnRat (float): 수익율
        DpsConvEvalAmt (float): 예수금환산평가금액
        StkConvEvalAmt (float): 주식환산평가금액
        DpsastConvEvalAmt (float): 예탁자산환산평가금액
        WonEvalSumAmt (float): 원화평가합계금액
        ConvEvalPnlAmt (float): 환산평가손익금액
        WonDpsBalAmt (float): 원화예수금잔고금액
        D2EstiDps (float): D2추정예수금
        LoanAmt (float): 대출금액
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""

    ErnRat: float = Field(
        default=0.0,
        title="수익율",
        description="수익율"
    )
    """수익율"""

    DpsConvEvalAmt: float = Field(
        default=0.0,
        title="예수금환산평가금액",
        description="예수금환산평가금액"
    )
    """예수금환산평가금액"""

    StkConvEvalAmt: float = Field(
        default=0.0,
        title="주식환산평가금액",
        description="주식환산평가금액"
    )
    """주식환산평가금액"""

    DpsastConvEvalAmt: float = Field(
        default=0.0,
        title="예탁자산환산평가금액",
        description="예탁자산환산평가금액"
    )
    """예탁자산환산평가금액"""

    WonEvalSumAmt: float = Field(
        default=0.0,
        title="원화평가합계금액",
        description="원화평가합계금액"
    )
    """원화평가합계금액"""

    ConvEvalPnlAmt: float = Field(
        default=0.0,
        title="환산평가손익금액",
        description="환산평가손익금액"
    )
    """환산평가손익금액"""

    WonDpsBalAmt: float = Field(
        default=0.0,
        title="원화예수금잔고금액",
        description="원화예수금잔고금액"
    )
    """원화예수금잔고금액"""

    D2EstiDps: float = Field(
        default=0.0,
        title="D2추정예수금",
        description="D2추정예수금"
    )
    """D2추정예수금"""

    LoanAmt: float = Field(
        default=0.0,
        title="대출금액",
        description="대출금액"
    )
    """대출금액"""


class COSOQ00201OutBlock3(BaseModel):
    """
    COSOQ00201OutBlock3 데이터 블록

    응답의 세 번째 출력 블록으로 통화별 잔고 상세를 포함한 리스트입니다.

    Attributes:
        CrcyCode (str): 통화코드
        FcurrDps (float): 외화예수금
        FcurrEvalAmt (float): 외화평가금액
        FcurrEvalPnlAmt (float): 외화평가손익금액
        PnlRat (float): 손익율
        BaseXchrat (float): 기준환율
        DpsConvEvalAmt (float): 예수금환산평가금액
        PchsAmt (float): 매입금액
        StkConvEvalAmt (float): 주식환산평가금액
        ConvEvalPnlAmt (float): 환산평가손익금액
        FcurrBuyAmt (float): 외화매수금액
        FcurrOrdAbleAmt (float): 외화주문가능금액
        LoanAmt (float): 대출금액
    """
    CrcyCode: str = Field(
        default="",
        title="통화코드",
        description="통화코드"
    )
    """통화코드"""

    FcurrDps: float = Field(
        default=0.0,
        title="외화예수금",
        description="외화예수금"
    )
    """외화예수금"""

    FcurrEvalAmt: float = Field(
        default=0.0,
        title="외화평가금액",
        description="외화평가금액"
    )
    """외화평가금액"""

    FcurrEvalPnlAmt: float = Field(
        default=0.0,
        title="외화평가손익금액",
        description="외화평가손익금액"
    )
    """외화평가손익금액"""

    PnlRat: float = Field(
        default=0.0,
        title="손익율",
        description="손익율"
    )
    """손익율"""

    BaseXchrat: float = Field(
        default=0.0,
        title="기준환율",
        description="기준환율"
    )
    """기준환율"""

    DpsConvEvalAmt: float = Field(
        default=0.0,
        title="예수금환산평가금액",
        description="예수금환산평가금액"
    )
    """예수금환산평가금액"""

    PchsAmt: float = Field(
        default=0.0,
        title="매입금액",
        description="매입금액"
    )
    """매입금액"""

    StkConvEvalAmt: float = Field(
        default=0.0,
        title="주식환산평가금액",
        description="주식환산평가금액"
    )
    """주식환산평가금액"""

    ConvEvalPnlAmt: float = Field(
        default=0.0,
        title="환산평가손익금액",
        description="환산평가손익금액"
    )
    """환산평가손익금액"""

    FcurrBuyAmt: float = Field(
        default=0.0,
        title="외화매수금액",
        description="외화매수금액"
    )
    """외화매수금액"""

    FcurrOrdAbleAmt: float = Field(
        default=0.0,
        title="외화주문가능금액",
        description="외화주문가능금액"
    )
    """외화주문가능금액"""

    LoanAmt: float = Field(
        default=0.0,
        title="대출금액",
        description="대출금액"
    )
    """대출금액"""


class COSOQ00201OutBlock4(BaseModel):
    """
    COSOQ00201OutBlock4 데이터 블록

    응답의 네 번째 출력 블록으로 종목별 잔고 상세를 포함한 리스트입니다.

    Attributes:
        CrcyCode (str): 통화코드
        ShtnIsuNo (str): 단축종목번호
        IsuNo (str): 종목번호
        JpnMktHanglIsuNm (str): 일본시장한글종목명
        AstkBalTpCode (str): 해외증권잔고구분코드
        AstkBalTpCodeNm (str): 해외증권잔고구분코드명
        AstkBalQty (float): 해외증권잔고수량
        AstkSellAbleQty (float): 해외증권매도가능수량
        FcstckUprc (float): 외화증권단가
        FcurrBuyAmt (float): 외화매수금액
        FcstckMktIsuCode (str): 외화증권시장종목코드
        OvrsScrtsCurpri (float): 해외증권시세
        FcurrEvalAmt (float): 외화평가금액
        FcurrEvalPnlAmt (float): 외화평가손익금액
        PnlRat (float): 손익율
        BaseXchrat (float): 기준환율
        PchsAmt (float): 매입금액
        DpsConvEvalAmt (float): 예수금환산평가금액
        StkConvEvalAmt (float): 주식환산평가금액
        ConvEvalPnlAmt (float): 환산평가손익금액
        AstkSettQty (float): 해외증권결제수량
        MktTpNm (str): 시장구분명
        FcurrMktCode (str): 외화시장코드
        LoanDt (str): 대출일자
        LoanDtlClssCode (str): 대출상세분류코드
        LoanAmt (float): 대출금액
        DueDt (str): 만기일자
        AstkBasePrc (float): 해외증권기준가격
    """
    CrcyCode: str = Field(
        default="",
        title="통화코드",
        description="통화코드"
    )
    """통화코드"""

    ShtnIsuNo: str = Field(
        default="",
        title="단축종목번호",
        description="단축종목번호"
    )
    """단축종목번호"""

    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="종목번호"
    )
    """종목번호"""

    JpnMktHanglIsuNm: str = Field(
        default="",
        title="일본시장한글종목명",
        description="일본시장한글종목명"
    )
    """일본시장한글종목명"""

    AstkBalTpCode: str = Field(
        default="",
        title="해외증권잔고구분코드",
        description="해외증권잔고구분코드"
    )
    """해외증권잔고구분코드"""

    AstkBalTpCodeNm: str = Field(
        default="",
        title="해외증권잔고구분코드명",
        description="해외증권잔고구분코드명"
    )
    """해외증권잔고구분코드명"""

    AstkBalQty: int = Field(
        default=0,
        title="해외증권잔고수량",
        description="해외증권잔고수량"
    )
    """해외증권잔고수량"""

    AstkSellAbleQty: int = Field(
        default=0,
        title="해외증권매도가능수량",
        description="해외증권매도가능수량"
    )
    """해외증권매도가능수량"""

    FcstckUprc: float = Field(
        default=0.0,
        title="외화증권단가",
        description="외화증권단가"
    )
    """외화증권단가"""

    FcurrBuyAmt: float = Field(
        default=0.0,
        title="외화매수금액",
        description="외화매수금액"
    )
    """외화매수금액"""

    FcstckMktIsuCode: str = Field(
        default="",
        title="외화증권시장종목코드",
        description="외화증권시장종목코드"
    )
    """외화증권시장종목코드"""

    OvrsScrtsCurpri: float = Field(
        default=0.0,
        title="해외증권시세",
        description="해외증권시세"
    )
    """해외증권시세"""

    FcurrEvalAmt: float = Field(
        default=0.0,
        title="외화평가금액",
        description="외화평가금액"
    )
    """외화평가금액"""

    FcurrEvalPnlAmt: float = Field(
        default=0.0,
        title="외화평가손익금액",
        description="외화평가손익금액"
    )
    """외화평가손익금액"""

    PnlRat: float = Field(
        default=0.0,
        title="손익율",
        description="손익율"
    )
    """손익율"""

    BaseXchrat: float = Field(
        default=0.0,
        title="기준환율",
        description="기준환율"
    )
    """기준환율"""

    PchsAmt: float = Field(
        default=0.0,
        title="매입금액",
        description="매입금액"
    )
    """매입금액"""

    DpsConvEvalAmt: float = Field(
        default=0.0,
        title="예수금환산평가금액",
        description="예수금환산평가금액"
    )
    """예수금환산평가금액"""

    StkConvEvalAmt: float = Field(
        default=0.0,
        title="주식환산평가금액",
        description="주식환산평산가금액"
    )
    """주식환산평가금액"""

    ConvEvalPnlAmt: float = Field(
        default=0.0,
        title="환산평가손익금액",
        description="환산평가손익금액"
    )
    """환산평가손익금액"""

    AstkSettQty: float = Field(
        default=0.0,
        title="해외증권결제수량",
        description="해외증권결제수량"
    )
    """해외증권결제수량"""

    MktTpNm: str = Field(
        default="",
        title="시장구분명",
        description="시장구분명"
    )
    """시장구분명"""

    FcurrMktCode: str = Field(
        default="",
        title="외화시장코드",
        description="외화시장코드"
    )
    """외화시장코드"""

    LoanDt: str = Field(
        default="",
        title="대출일자",
        description="대출일자"
    )
    """대출일자"""

    LoanDtlClssCode: str = Field(
        default="",
        title="대출상세분류코드",
        description="대출상세분류코드"
    )
    """대출상세분류코드"""

    LoanAmt: float = Field(
        default=0.0,
        title="대출금액",
        description="대출금액"
    )
    """대출금액"""

    DueDt: str = Field(
        default="",
        title="만기일자",
        description="만기일자"
    )
    """만기일자"""

    AstkBasePrc: float = Field(
        default=0.0,
        title="해외증권기준가격",
        description="해외증권기준가격"
    )
    """해외증권기준가격"""


class COSOQ00201Response(BaseModel):
    """
    COSOQ00201 API에 대한 응답 클래스.

    Attributes:
        header (Optional[COSOQ00201ResponseHeader]): 요청 헤더 데이터 블록
        COSOQ00201OutBlock1 (Optional[COSOQ00201OutBlock1]): 첫 번째 출력 블록
        COSOQ00201OutBlock2 (Optional[COSOQ00201OutBlock2]): 두 번째 출력 블록
        COSOQ00201OutBlock3 (List[COSOQ00201OutBlock3]): 세 번째 출력 블록 리스트
        COSOQ00201OutBlock4 (List[COSOQ00201OutBlock4]): 네 번째 출력 블록 리스트
        rsp_cd (str): API 호출 상태를 나타내는 응답 코드.
        rsp_msg (str): API 호출 결과에 대한 추가 정보를 제공하는 응답 메시지
        error_msg (Optional[str]): 오류 발생 시 오류 메시지, 없을 경우 None
    """
    header: Optional[COSOQ00201ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="COSOQ00201 API 응답의 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    block1: Optional[COSOQ00201OutBlock1] = Field(
        None,
        title="첫 번째 출력 블록",
        description="첫 번째 출력 블록"
    )
    """첫 번째 출력 블록"""

    block2: Optional[COSOQ00201OutBlock2] = Field(
        None,
        title="두 번째 출력 블록",
        description="두 번째 출력 블록"
    )
    """두 번째 출력 블록"""

    block3: List[COSOQ00201OutBlock3] = Field(
        default_factory=list,
        title="세 번째 출력 블록 리스트",
        description="세 번째 출력 블록 리스트"
    )
    """세 번째 출력 블록 리스트"""

    block4: List[COSOQ00201OutBlock4] = Field(
        default_factory=list,
        title="네 번째 출력 블록 리스트",
        description="네 번째 출력 블록 리스트"
    )
    """네 번째 출력 블록 리스트"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
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
