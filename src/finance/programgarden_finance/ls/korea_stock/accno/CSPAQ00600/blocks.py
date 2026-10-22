"""Pydantic models for LS Securities OpenAPI CSPAQ00600 (Account Credit Limit Inquiry).

CSPAQ00600 returns the credit / margin limit and orderable amount / quantity
for a Korean cash-equity account on a per-symbol basis. Two response blocks
are returned:
    - ``CSPAQ00600OutBlock1`` (block1): echo-back of the input parameters
      together with the resolved account number and password (server-side
      only, never returned in plaintext).
    - ``CSPAQ00600OutBlock2`` (block2): credit limit / used amount across the
      different loan classifications (general credit, market-making credit,
      treasury-stock credit), orderable amount / quantity for the requested
      symbol at the requested price, deposited assets, collateral ratios,
      and per-symbol margin requirements.

Symbol numbering convention: LS CSPA-family TRs use the LS-prefixed format
(``"A" + 6-digit stock code``), e.g., ``"A005930"`` for Samsung Electronics.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ00600RequestHeader(BlockRequestHeader):
    """CSPAQ00600 request header. Inherits the standard LS request header schema."""
    pass


class CSPAQ00600ResponseHeader(BlockResponseHeader):
    """CSPAQ00600 response header. Standard LS response header schema."""
    pass


class CSPAQ00600InBlock1(BaseModel):
    """CSPAQ00600InBlock1 — input block for account credit limit inquiry.

    Targets a single symbol at a candidate order price; the response reports
    the credit limit and the orderable amount / quantity for that scenario.
    """

    LoanDtlClssCode: str = Field(
        default="",
        title="대출상세분류코드 (Loan detail classification code)",
        description=(
            "Loan detail classification code used to scope the credit limit "
            "lookup. Empty string is treated as the default (general) "
            "classification. The complete enum mapping is not declared in the "
            "available LS source — consume per LS convention."
        ),
        examples=["", "001", "002"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "LS-prefixed Korean stock code (``A`` + 6-digit short code), "
            "e.g., ``A005930`` for Samsung Electronics. Empty string is "
            "treated as no symbol filter."
        ),
        examples=["", "A005930", "A000660"],
    )
    OrdPrc: float = Field(
        default=0.0,
        title="주문가 (Order price)",
        description=(
            "Candidate order price (KRW) for which the orderable quantity is "
            "computed. 0.0 may be used for market-order scenarios — consume "
            "per LS convention."
        ),
        examples=[0.0, 50_000.0, 250_000.0],
    )
    CommdaCode: str = Field(
        default="41",
        title="통신매체코드 (Communication channel code)",
        description=(
            "Communication channel code. Default is ``\"41\"`` (OpenAPI per LS "
            "convention). The complete enum mapping is not declared in the "
            "available LS source — consume per LS convention."
        ),
        examples=["41"],
    )


class CSPAQ00600Request(BaseModel):
    """CSPAQ00600 full request envelope (header + body + setup options)."""

    header: CSPAQ00600RequestHeader = CSPAQ00600RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ00600",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["CSPAQ00600InBlock1"], CSPAQ00600InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ00600",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class CSPAQ00600OutBlock1(BaseModel):
    """CSPAQ00600OutBlock1 — input echo-back block.

    Returns the resolved account context (account number, redacted password)
    and the input parameters as observed by the server.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this echo block.",
        examples=[0, 1],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description=(
            "Resolved account number associated with the authenticated session. "
            "Length 11."
        ),
        examples=["", "12345678901"],
    )
    InptPwd: str = Field(
        default="",
        title="입력비밀번호 (Account password marker)",
        description=(
            "Account password placeholder. Always returned redacted (empty or "
            "masked) by the server — never the plaintext password."
        ),
        examples=[""],
    )
    LoanDtlClssCode: str = Field(
        default="",
        title="대출상세분류코드 (Loan detail classification code)",
        description="Echo of the input ``LoanDtlClssCode``.",
        examples=["", "001"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description="Echo of the input ``IsuNo``.",
        examples=["", "A005930"],
    )
    OrdPrc: float = Field(
        default=0.0,
        title="주문가 (Order price)",
        description="Echo of the input ``OrdPrc``.",
        examples=[0.0, 50_000.0],
    )
    CommdaCode: str = Field(
        default="",
        title="통신매체코드 (Communication channel code)",
        description="Echo of the input ``CommdaCode``.",
        examples=["", "41"],
    )


class CSPAQ00600OutBlock2(BaseModel):
    """CSPAQ00600OutBlock2 — credit limit and orderable amount block.

    Returns the credit-limit ceilings, used amounts across loan
    classifications, the orderable amount / quantity at the requested order
    price, deposited assets, collateral ratios and per-symbol margin
    requirements.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this block.",
        examples=[0, 1],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account display name)",
        description="Korean display name of the account.",
        examples=["", "홍길동"],
    )
    SloanLmtAmt: int = Field(
        default=0,
        title="신용융자한도금액 (General credit loan limit)",
        description=(
            "Maximum amount the account is permitted to borrow under the "
            "general credit classification. Currency: KRW."
        ),
        examples=[0, 100_000_000, 500_000_000],
    )
    SloanAmtSum: int = Field(
        default=0,
        title="신용융자금액합계 (General credit loan used)",
        description=(
            "Currently outstanding general credit loan amount. Currency: KRW."
        ),
        examples=[0, 25_000_000],
    )
    MktcplMloanLmtAmt: int = Field(
        default=0,
        title="시장조성융자한도금액 (Market-making credit limit)",
        description=(
            "Maximum amount permitted under the market-making credit "
            "classification. Currency: KRW."
        ),
        examples=[0, 50_000_000],
    )
    MktcplMloanAmtSum: int = Field(
        default=0,
        title="시장조성융자금액합계 (Market-making credit used)",
        description=(
            "Currently outstanding market-making credit loan amount. "
            "Currency: KRW."
        ),
        examples=[0, 10_000_000],
    )
    SfaccMloanLmtAmt: int = Field(
        default=0,
        title="자사주융자한도금액 (Treasury-stock credit limit)",
        description=(
            "Maximum amount permitted under the treasury-stock credit "
            "classification. Currency: KRW."
        ),
        examples=[0, 30_000_000],
    )
    SfaccMloanAmtSum: int = Field(
        default=0,
        title="자사주융자금액합계 (Treasury-stock credit used)",
        description=(
            "Currently outstanding treasury-stock credit loan amount. "
            "Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    OrdAbleAmt: int = Field(
        default=0,
        title="주문가능금액 (Orderable amount)",
        description=(
            "Maximum order amount permitted at the input ``OrdPrc`` for the "
            "input ``IsuNo`` under the input ``LoanDtlClssCode``. "
            "Currency: KRW."
        ),
        examples=[0, 5_000_000, 50_000_000],
    )
    OrdAbleQty: int = Field(
        default=0,
        title="주문가능수량 (Orderable quantity)",
        description=(
            "Maximum order quantity (shares) derived from ``OrdAbleAmt`` and "
            "``OrdPrc`` per LS server logic."
        ),
        examples=[0, 100, 1_000],
    )
    DpsastSum: int = Field(
        default=0,
        title="예탁자산합계 (Deposited assets total)",
        description=(
            "Sum of deposited assets backing the credit limit calculation. "
            "Currency: KRW."
        ),
        examples=[0, 100_000_000],
    )
    PldgMaintRat: float = Field(
        default=0.0,
        title="담보유지비율 (Collateral maintenance ratio)",
        description=(
            "Collateral maintenance ratio in percent. LS may serialize this "
            "value as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 140.0, 170.0],
    )
    PldgRat: float = Field(
        default=0.0,
        title="담보비율 (Collateral ratio)",
        description=(
            "Current collateral ratio in percent. LS may serialize this value "
            "as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 200.0, 350.0],
    )
    IsuNm: str = Field(
        default="",
        title="종목명 (Stock display name)",
        description="Korean stock display name corresponding to ``IsuNo``.",
        examples=["", "삼성전자", "SK하이닉스"],
    )
    BnsTpCode: str = Field(
        default="",
        title="매매구분코드 (Buy/sell side code)",
        description=(
            "Side code applicable to the orderable scenario. The complete enum "
            "mapping is not declared in the available LS source — consume as "
            "returned by LS."
        ),
        examples=["", "1", "2"],
    )
    MgnRat: float = Field(
        default=0.0,
        title="증거금률 (Margin ratio)",
        description=(
            "Margin requirement ratio in percent applicable to ``IsuNo``. LS "
            "may serialize this value as a string; Pydantic auto-coerces to "
            "float."
        ),
        examples=[0.0, 20.0, 40.0, 100.0],
    )
    MnyMgn: int = Field(
        default=0,
        title="현금증거금 (Cash margin)",
        description=(
            "Cash component of the margin requirement for the orderable "
            "scenario. Currency: KRW."
        ),
        examples=[0, 1_000_000, 10_000_000],
    )
    SubstMgn: int = Field(
        default=0,
        title="대용증거금 (Substitute margin)",
        description=(
            "Substitute (non-cash collateral) component of the margin "
            "requirement for the orderable scenario. Currency: KRW."
        ),
        examples=[0, 500_000, 5_000_000],
    )


class CSPAQ00600Response(BaseModel):
    """CSPAQ00600 full API response envelope."""

    header: Optional[CSPAQ00600ResponseHeader] = None
    block1: Optional[CSPAQ00600OutBlock1] = Field(
        default=None,
        title="CSPAQ00600OutBlock1 (Input echo-back)",
        description="Echo-back of the input parameters with resolved account context.",
    )
    block2: Optional[CSPAQ00600OutBlock2] = Field(
        default=None,
        title="CSPAQ00600OutBlock2 (Credit limit / orderable data)",
        description=(
            "Credit limits, used amounts, orderable amount / quantity, "
            "deposited assets, collateral ratios and per-symbol margin "
            "requirements."
        ),
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
