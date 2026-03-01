from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ00600RequestHeader(BlockRequestHeader):
    """CSPAQ00600 요청용 Header"""
    pass


class CSPAQ00600ResponseHeader(BlockResponseHeader):
    """CSPAQ00600 응답용 Header"""
    pass


class CSPAQ00600InBlock1(BaseModel):
    """
    CSPAQ00600InBlock1 - 계좌별신용한도조회 입력 블록

    계좌의 신용한도 및 주문가능금액/수량을 조회합니다.

    Attributes:
        LoanDtlClssCode (str): 대출상세분류코드
        IsuNo (str): 종목번호
        OrdPrc (float): 주문가
        CommdaCode (str): 통신매체코드 (default: "41")
    """
    LoanDtlClssCode: str = Field(
        default="",
        title="대출상세분류코드",
        description="대출상세분류코드"
    )
    """ 대출상세분류코드 """
    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="종목번호"
    )
    """ 종목번호 """
    OrdPrc: float = Field(
        default=0.0,
        title="주문가",
        description="주문가"
    )
    """ 주문가 """
    CommdaCode: str = Field(
        default="41",
        title="통신매체코드",
        description="통신매체코드 (default: 41)"
    )
    """ 통신매체코드 """


class CSPAQ00600Request(BaseModel):
    """
    CSPAQ00600 API 요청 - 계좌별신용한도조회

    Attributes:
        header (CSPAQ00600RequestHeader)
        body (dict[Literal["CSPAQ00600InBlock1"], CSPAQ00600InBlock1])
    """
    header: CSPAQ00600RequestHeader = CSPAQ00600RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ00600",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CSPAQ00600InBlock1"], CSPAQ00600InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ00600"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CSPAQ00600OutBlock1(BaseModel):
    """
    CSPAQ00600OutBlock1 - 입력 echo-back 블록

    Attributes:
        RecCnt (int): 레코드갯수
        AcntNo (str): 계좌번호
        InptPwd (str): 입력비밀번호
        LoanDtlClssCode (str): 대출상세분류코드
        IsuNo (str): 종목번호
        OrdPrc (float): 주문가
        CommdaCode (str): 통신매체코드
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """ 계좌번호 """
    InptPwd: str = Field(default="", title="입력비밀번호", description="입력비밀번호")
    """ 입력비밀번호 """
    LoanDtlClssCode: str = Field(default="", title="대출상세분류코드", description="대출상세분류코드")
    """ 대출상세분류코드 """
    IsuNo: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """
    OrdPrc: float = Field(default=0.0, title="주문가", description="주문가")
    """ 주문가 """
    CommdaCode: str = Field(default="", title="통신매체코드", description="통신매체코드")
    """ 통신매체코드 """


class CSPAQ00600OutBlock2(BaseModel):
    """
    CSPAQ00600OutBlock2 - 계좌별신용한도조회 응답 블록

    계좌의 신용한도 및 주문가능금액/수량 정보를 제공합니다.
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    AcntNm: str = Field(default="", title="계좌명", description="계좌명")
    """ 계좌명 """
    SloanLmtAmt: int = Field(default=0, title="신용융자한도금액", description="신용융자한도금액")
    """ 신용융자한도금액 """
    SloanAmtSum: int = Field(default=0, title="신용융자금액합계", description="신용융자금액합계")
    """ 신용융자금액합계 """
    MktcplMloanLmtAmt: int = Field(default=0, title="시장조성융자한도금액", description="시장조성융자한도금액")
    """ 시장조성융자한도금액 """
    MktcplMloanAmtSum: int = Field(default=0, title="시장조성융자금액합계", description="시장조성융자금액합계")
    """ 시장조성융자금액합계 """
    SfaccMloanLmtAmt: int = Field(default=0, title="자사주융자한도금액", description="자사주융자한도금액")
    """ 자사주융자한도금액 """
    SfaccMloanAmtSum: int = Field(default=0, title="자사주융자금액합계", description="자사주융자금액합계")
    """ 자사주융자금액합계 """
    OrdAbleAmt: int = Field(default=0, title="주문가능금액", description="주문가능금액")
    """ 주문가능금액 """
    OrdAbleQty: int = Field(default=0, title="주문가능수량", description="주문가능수량")
    """ 주문가능수량 """
    DpsastSum: int = Field(default=0, title="예탁자산합계", description="예탁자산합계")
    """ 예탁자산합계 """
    PldgMaintRat: float = Field(default=0.0, title="담보유지비율", description="담보유지비율")
    """ 담보유지비율 """
    PldgRat: float = Field(default=0.0, title="담보비율", description="담보비율")
    """ 담보비율 """
    IsuNm: str = Field(default="", title="종목명", description="종목명")
    """ 종목명 """
    BnsTpCode: str = Field(default="", title="매매구분코드", description="매매구분코드")
    """ 매매구분코드 """
    MgnRat: float = Field(default=0.0, title="증거금률", description="증거금률")
    """ 증거금률 """
    MnyMgn: int = Field(default=0, title="현금증거금", description="현금증거금")
    """ 현금증거금 """
    SubstMgn: int = Field(default=0, title="대용증거금", description="대용증거금")
    """ 대용증거금 """


class CSPAQ00600Response(BaseModel):
    """
    CSPAQ00600 API 전체 응답 - 계좌별신용한도조회

    Attributes:
        header (Optional[CSPAQ00600ResponseHeader])
        block1 (Optional[CSPAQ00600OutBlock1]): 입력 echo-back
        block2 (Optional[CSPAQ00600OutBlock2]): 신용한도/주문가능 데이터
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CSPAQ00600ResponseHeader] = None
    block1: Optional[CSPAQ00600OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="입력 파라미터 echo-back 블록"
    )
    block2: Optional[CSPAQ00600OutBlock2] = Field(
        None,
        title="신용한도/주문가능 데이터",
        description="계좌 신용한도 및 주문가능금액/수량 정보"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str
    rsp_msg: str
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
