"""Pydantic models for LS Securities OpenAPI CSPBQ00200 (Cash Account Margin-Rate Order Ability).

CSPBQ00200 returns the per-symbol orderable amount and quantity for a cash
equity account, broken down by margin-rate buckets. Two response blocks
are returned:
    - ``CSPBQ00200OutBlock1`` (block1): echo-back of the input parameters
      together with the resolved account number.
    - ``CSPBQ00200OutBlock2`` (block2): account-level cash / substitute
      collateral, per-bucket orderable amounts (20% / 25% / 30% / 35% /
      40% / 50% / 60% / 100%-cash buckets and the 미수 (credit) bucket),
      exchange / KOSDAQ orderable amounts, and the resolved orderable
      quantity / amount for the requested order scenario.

⚠ Field semantic change (2026-04-11 LS Securities):
    ``MgnRat100pctOrdAbleAmt`` now exposes the **미수주문가능금액**
    (orderable amount eligible for 미수 / credit ordering). Until
    2026-04-10 this same field held the legacy 증거금률 100% 주문가능
    금액 (100% margin-rate orderable amount). From 2026-04-11 onward, the
    legacy 증거금률 100% semantic is exposed as ``RcvblUablOrdAbleAmt`` on
    ``CSPAQ12200`` / ``CSPAQ22200`` only — CSPBQ00200 does not surface that
    legacy value. Callers needing the 증거금률 100% semantic must call
    CSPAQ12200 or CSPAQ22200 instead.

Symbol numbering convention: LS CSPB-family TRs use the LS-prefixed format
(``"A" + 6-digit stock code``), e.g., ``"A005930"`` for Samsung Electronics.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPBQ00200RequestHeader(BlockRequestHeader):
    """CSPBQ00200 request header. Inherits the standard LS request header schema."""
    pass


class CSPBQ00200ResponseHeader(BlockResponseHeader):
    """CSPBQ00200 response header. Standard LS response header schema."""
    pass


class CSPBQ00200InBlock1(BaseModel):
    """CSPBQ00200InBlock1 — input block for cash account margin-rate orderable.

    Targets a single symbol at a candidate order price on a specific side;
    the response reports orderable amount / quantity per margin-rate bucket
    for that scenario.
    """

    BnsTpCode: Literal["1", "2"] = Field(
        ...,
        title="매매구분 (Side code)",
        description=(
            "Side of the orderable scenario. '1' = 매도 (sell), '2' = 매수 "
            "(buy). Required. Length 1."
        ),
        examples=["1", "2"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "LS-prefixed Korean stock code (``A`` + 6-digit short code), "
            "e.g., ``A005930`` for Samsung Electronics."
        ),
        examples=["", "A005930", "A000660"],
    )
    OrdPrc: float = Field(
        default=0.0,
        title="주문가격 (Order price)",
        description=(
            "Candidate order price (KRW) for which the orderable amount / "
            "quantity is computed. 0.0 may be used for market-order scenarios — "
            "consume per LS convention."
        ),
        examples=[0.0, 50_000.0, 250_000.0],
    )


class CSPBQ00200Request(BaseModel):
    """CSPBQ00200 full request envelope (header + body + setup options)."""

    header: CSPBQ00200RequestHeader = CSPBQ00200RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPBQ00200",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["CSPBQ00200InBlock1"], CSPBQ00200InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPBQ00200",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class CSPBQ00200OutBlock1(BaseModel):
    """CSPBQ00200OutBlock1 — input echo-back block."""

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this echo block.",
        examples=[0, 1],
    )
    BnsTpCode: str = Field(
        default="",
        title="매매구분 (Side code)",
        description=(
            "Echo of the input ``BnsTpCode`` ('1' = 매도, '2' = 매수)."
        ),
        examples=["", "1", "2"],
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
            "Account password placeholder. Always returned redacted by the "
            "server — never the plaintext password."
        ),
        examples=[""],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description="Echo of the input ``IsuNo``.",
        examples=["", "A005930"],
    )
    OrdPrc: float = Field(
        default=0.0,
        title="주문가격 (Order price)",
        description="Echo of the input ``OrdPrc``.",
        examples=[0.0, 50_000.0],
    )
    RegCommdaCode: str = Field(
        default="",
        title="등록통신매체코드 (Registered channel code)",
        description=(
            "Registered communication channel code. The complete enum mapping "
            "is not declared in the available LS source — consume per LS "
            "convention."
        ),
        examples=["", "41"],
    )


class CSPBQ00200OutBlock2(BaseModel):
    """CSPBQ00200OutBlock2 — margin-rate orderable amount and quantity block.

    Returns account-level cash / substitute collateral, per-bucket orderable
    amounts at every standard margin rate, exchange / KOSDAQ orderable
    amounts, and the resolved orderable quantity / amount for the scenario.

    See module docstring for the 2026-04-11 semantic change on
    ``MgnRat100pctOrdAbleAmt``.
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
    IsuNm: str = Field(
        default="",
        title="종목명 (Stock display name)",
        description="Korean stock display name corresponding to ``IsuNo``.",
        examples=["", "삼성전자", "SK하이닉스"],
    )
    Dps: int = Field(
        default=0,
        title="예수금 (Cash deposit)",
        description="Cash deposit balance. Currency: KRW.",
        examples=[0, 5_000_000, 100_000_000],
    )
    SubstAmt: int = Field(
        default=0,
        title="대용금액 (Substitute collateral amount)",
        description=(
            "Substitute (non-cash collateral) amount available against margin "
            "requirements. Currency: KRW."
        ),
        examples=[0, 2_000_000, 50_000_000],
    )
    MnyOrdAbleAmt: int = Field(
        default=0,
        title="현금주문가능금액 (Cash orderable amount)",
        description="Cash amount available for placing buy orders. Currency: KRW.",
        examples=[0, 5_000_000, 100_000_000],
    )
    SubstOrdAbleAmt: int = Field(
        default=0,
        title="대용주문가능금액 (Substitute orderable amount)",
        description=(
            "Substitute-collateral amount available for placing buy orders. "
            "Currency: KRW."
        ),
        examples=[0, 2_000_000, 50_000_000],
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
    SeOrdAbleAmt: int = Field(
        default=0,
        title="거래소주문가능금액 (Exchange orderable amount)",
        description=(
            "Orderable amount applicable on the KRX main board. Currency: KRW."
        ),
        examples=[0, 5_000_000, 100_000_000],
    )
    KdqOrdAbleAmt: int = Field(
        default=0,
        title="코스닥주문가능금액 (KOSDAQ orderable amount)",
        description=(
            "Orderable amount applicable on the KOSDAQ market. Currency: KRW."
        ),
        examples=[0, 4_500_000, 90_000_000],
    )
    MgnRat20pctOrdAbleAmt: int = Field(
        default=0,
        title="증거금률20%주문가능금액 (20% margin-rate orderable)",
        description=(
            "Orderable amount under a 20% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 25_000_000],
    )
    MgnRat25pctOrdAbleAmt: int = Field(
        default=0,
        title="증거금률25%주문가능금액 (25% margin-rate orderable)",
        description=(
            "Orderable amount under a 25% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 20_000_000],
    )
    MgnRat30pctOrdAbleAmt: int = Field(
        default=0,
        title="증거금률30%주문가능금액 (30% margin-rate orderable)",
        description=(
            "Orderable amount under a 30% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 16_500_000],
    )
    MgnRat35pctOrdAbleAmt: int = Field(
        default=0,
        title="증거금률35%주문가능금액 (35% margin-rate orderable)",
        description=(
            "Orderable amount under a 35% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 14_000_000],
    )
    MgnRat40pctOrdAbleAmt: int = Field(
        default=0,
        title="증거금률40%주문가능금액 (40% margin-rate orderable)",
        description=(
            "Orderable amount under a 40% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 12_500_000],
    )
    MgnRat50pctOrdAbleAmt: int = Field(
        default=0,
        title="증거금률50%주문가능금액 (50% margin-rate orderable)",
        description=(
            "Orderable amount under a 50% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 10_000_000],
    )
    MgnRat60pctOrdAbleAmt: int = Field(
        default=0,
        title="증거금률60%주문가능금액 (60% margin-rate orderable)",
        description=(
            "Orderable amount under a 60% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 8_300_000],
    )
    MgnRat100pctOrdAbleAmt: int = Field(
        default=0,
        title="미수주문가능금액 (Order-able amount eligible for 미수 / credit ordering)",
        description=(
            "Order-able amount eligible for 미수주문 (missed-payment / credit "
            "ordering). Field semantic was changed by LS Securities on "
            "2026-04-11 12:00 KST: until 2026-04-10 this field held 증거금률 "
            "100% 주문가능 금액 (100% margin-rate order-able amount). From "
            "2026-04-11 onward, the legacy 증거금률 100% value is exposed by "
            "RcvblUablOrdAbleAmt on CSPAQ12200/22200; CSPBQ00200 itself does "
            "not expose the legacy value (LS notice marks CSPBQ00200 as "
            "semantic-change-only, no field addition). Callers needing the "
            "증거금률 100% semantic must call CSPAQ12200 or CSPAQ22200 and "
            "read RcvblUablOrdAbleAmt instead. The Korean field title was "
            "also updated upstream to reflect the new semantic. Currency: KRW. "
            "Length 16. Pydantic auto-coerces."
        ),
        examples=[79744009, 306, 0],
    )
    MgnRat100MnyOrdAbleAmt: int = Field(
        default=0,
        title="증거금률100%현금주문가능금액 (100% margin-rate cash orderable)",
        description=(
            "Orderable amount under a 100% margin-rate bucket using cash only. "
            "Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    OrdAbleQty: int = Field(
        default=0,
        title="주문가능수량 (Orderable quantity)",
        description=(
            "Resolved orderable quantity (shares) for the input ``IsuNo`` at "
            "the input ``OrdPrc`` and ``BnsTpCode`` per LS server logic."
        ),
        examples=[0, 100, 1_000],
    )
    OrdAbleAmt: int = Field(
        default=0,
        title="주문가능금액 (Orderable amount)",
        description=(
            "Resolved orderable amount for the input scenario. Currency: KRW."
        ),
        examples=[0, 5_000_000, 50_000_000],
    )
    SellOrdAbleQty: int = Field(
        default=0,
        title="매도주문가능수량 (Sellable quantity)",
        description=(
            "Quantity available for sell-side orders on this symbol (shares)."
        ),
        examples=[0, 100, 1_000],
    )


class CSPBQ00200Response(BaseModel):
    """CSPBQ00200 full API response envelope."""

    header: Optional[CSPBQ00200ResponseHeader] = None
    block1: Optional[CSPBQ00200OutBlock1] = Field(
        default=None,
        title="CSPBQ00200OutBlock1 (Input echo-back)",
        description="Echo-back of the input parameters with resolved account context.",
    )
    block2: Optional[CSPBQ00200OutBlock2] = Field(
        default=None,
        title="CSPBQ00200OutBlock2 (Margin-rate orderable data)",
        description=(
            "Cash / substitute collateral, per-bucket orderable amounts "
            "across margin rates, exchange / KOSDAQ orderable amounts, "
            "and the resolved orderable quantity / amount for the scenario."
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
