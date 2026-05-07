"""Pydantic models for LS Securities OpenAPI CDPCQ04700 (Account Transaction History).

CDPCQ04700 returns the account transaction history (deposit / withdrawal /
trade ledger) for a date range, in three response blocks:
    - ``CDPCQ04700OutBlock1`` (block1): echo-back of the input parameters.
    - ``CDPCQ04700OutBlock2`` (block2): summary — account display name and
      record count.
    - ``CDPCQ04700OutBlock3`` (block3): per-transaction detail rows
      including transaction date, classification, summary text, quantity /
      amount, fees and taxes.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CDPCQ04700RequestHeader(BlockRequestHeader):
    """CDPCQ04700 request header. Inherits the standard LS request header schema."""
    pass


class CDPCQ04700ResponseHeader(BlockResponseHeader):
    """CDPCQ04700 response header. Standard LS response header schema."""
    pass


class CDPCQ04700InBlock1(BaseModel):
    """CDPCQ04700InBlock1 — input block for account transaction history.

    Specify the date range with ``QrySrtDt`` / ``QryEndDt`` (YYYYMMDD).
    Default product / asset-class filters scope the query to cash-equity
    holdings.
    """

    QryTp: str = Field(
        default="0",
        title="조회구분 (Query mode)",
        description=(
            "Query mode. Default ``\"0\"``. The complete enum mapping is not "
            "declared in the available LS source — consume per LS convention."
        ),
        examples=["0", "1"],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description=(
            "Account number to query. Length 11. The server typically resolves "
            "the account from the authenticated session — pass an empty string "
            "to use the default account."
        ),
        examples=["", "12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="비밀번호 (Account password)",
        description=(
            "Account password placeholder. Server-side encryption applies — "
            "pass an empty string when relying on session-based authentication."
        ),
        examples=[""],
    )
    QrySrtDt: str = Field(
        default="",
        title="조회시작일 (Query start date, YYYYMMDD)",
        description=(
            "Inclusive lower bound of the query date range, formatted as "
            "YYYYMMDD."
        ),
        examples=["", "20260101", "20260201"],
    )
    QryEndDt: str = Field(
        default="",
        title="조회종료일 (Query end date, YYYYMMDD)",
        description=(
            "Inclusive upper bound of the query date range, formatted as "
            "YYYYMMDD."
        ),
        examples=["", "20260131", "20260228"],
    )
    SrtNo: int = Field(
        default=0,
        title="시작번호 (Pagination start number)",
        description=(
            "Starting record number for paging. Pass 0 on the first call. "
            "On subsequent calls reuse the highest record number observed in "
            "the previous page."
        ),
        examples=[0, 100],
    )
    PdptnCode: str = Field(
        default="01",
        title="상품유형코드 (Product type code)",
        description=(
            "Product type code. Default ``\"01\"`` selects cash-equity. The "
            "complete enum mapping is not declared in the available LS source — "
            "consume per LS convention."
        ),
        examples=["01", "02"],
    )
    IsuLgclssCode: str = Field(
        default="01",
        title="종목대분류코드 (Asset major-class code)",
        description=(
            "Asset major-classification code. Default ``\"01\"``. The complete "
            "enum mapping is not declared in the available LS source — consume "
            "per LS convention."
        ),
        examples=["01", "02"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "LS-prefixed Korean stock code (``A`` + 6-digit short code) to "
            "filter by, or empty string for all symbols."
        ),
        examples=["", "A005930", "A000660"],
    )


class CDPCQ04700Request(BaseModel):
    """CDPCQ04700 full request envelope (header + body + setup options)."""

    header: CDPCQ04700RequestHeader = CDPCQ04700RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CDPCQ04700",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["CDPCQ04700InBlock1"], CDPCQ04700InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CDPCQ04700",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class CDPCQ04700OutBlock1(BaseModel):
    """CDPCQ04700OutBlock1 — input echo-back block."""

    QryTp: str = Field(
        default="0",
        title="조회구분 (Query mode)",
        description="Echo of the input ``QryTp``.",
        examples=["0", "1"],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Echo of the input ``AcntNo``. Length 11.",
        examples=["", "12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="비밀번호 (Account password marker)",
        description="Always returned redacted by the server.",
        examples=[""],
    )
    QrySrtDt: str = Field(
        default="",
        title="조회시작일 (Query start date, YYYYMMDD)",
        description="Echo of the input ``QrySrtDt``.",
        examples=["", "20260101"],
    )
    QryEndDt: str = Field(
        default="",
        title="조회종료일 (Query end date, YYYYMMDD)",
        description="Echo of the input ``QryEndDt``.",
        examples=["", "20260131"],
    )
    SrtNo: int = Field(
        default=0,
        title="시작번호 (Pagination start number)",
        description="Echo of the input ``SrtNo``.",
        examples=[0, 100],
    )
    PdptnCode: str = Field(
        default="01",
        title="상품유형코드 (Product type code)",
        description="Echo of the input ``PdptnCode``.",
        examples=["01", "02"],
    )
    IsuLgclssCode: str = Field(
        default="01",
        title="종목대분류코드 (Asset major-class code)",
        description="Echo of the input ``IsuLgclssCode``.",
        examples=["01", "02"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description="Echo of the input ``IsuNo``.",
        examples=["", "A005930"],
    )


class CDPCQ04700OutBlock2(BaseModel):
    """CDPCQ04700OutBlock2 — transaction history summary block.

    Returns the account display name and the count of transaction records
    returned for the requested date range.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of transaction rows returned in ``block3``.",
        examples=[0, 27, 312],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account display name)",
        description="Korean display name of the account.",
        examples=["", "홍길동"],
    )


class CDPCQ04700OutBlock3(BaseModel):
    """CDPCQ04700OutBlock3 — per-transaction detail row.

    Each row describes one transaction (deposit / withdrawal / trade
    settlement) with quantity, amount, fees and taxes. Trade rows additionally
    populate the symbol, side, quantity and unit price fields.
    """

    TrdDt: str = Field(
        default="",
        title="거래일자 (Transaction date, YYYYMMDD)",
        description="Trading / settlement date of the transaction.",
        examples=["", "20260203", "20260307"],
    )
    TrdNo: int = Field(
        default=0,
        title="거래번호 (Transaction number)",
        description="LS-assigned transaction number for the date.",
        examples=[1, 27, 312],
    )
    TpCodeNm: str = Field(
        default="",
        title="구분코드명 (Classification display name)",
        description=(
            "Korean display name of the transaction classification (e.g., "
            "매수, 매도, 입금, 출금)."
        ),
        examples=["", "매수", "매도", "입금"],
    )
    SmryNm: str = Field(
        default="",
        title="적요명 (Summary text)",
        description=(
            "Free-form Korean summary text attached by LS to the transaction."
        ),
        examples=["", "유가증권매수", "유가증권매도"],
    )
    TrdQty: int = Field(
        default=0,
        title="거래수량 (Transaction quantity)",
        description="Quantity of the transaction (shares for trade rows).",
        examples=[0, 10, 100],
    )
    TrdAmt: int = Field(
        default=0,
        title="거래금액 (Transaction amount)",
        description="Transaction amount. Currency: KRW.",
        examples=[0, 700_000, 7_000_000],
    )
    AdjstAmt: int = Field(
        default=0,
        title="정산금액 (Settled amount)",
        description=(
            "Settled amount net of fees and taxes. Currency: KRW."
        ),
        examples=[0, 698_500, 6_985_000],
    )
    CmsnAmt: int = Field(
        default=0,
        title="수수료 (Fee)",
        description="Brokerage fee for this transaction. Currency: KRW.",
        examples=[0, 1_500],
    )
    IsuNm: str = Field(
        default="",
        title="종목명 (Stock display name)",
        description="Korean stock display name. Empty for non-trade rows.",
        examples=["", "삼성전자", "SK하이닉스"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "LS-prefixed Korean stock code. Empty for non-trade rows."
        ),
        examples=["", "A005930"],
    )
    EvrTax: int = Field(
        default=0,
        title="제세금 (Tax)",
        description="Securities transaction tax and other taxes. Currency: KRW.",
        examples=[0, 7_500],
    )
    TrxTime: str = Field(
        default="",
        title="처리시각 (Processing time)",
        description=(
            "Server-side processing timestamp. Format follows LS convention "
            "(HHMMSS or HHMMSSmmm) — consume as returned."
        ),
        examples=["", "093015", "153000"],
    )
    BnsTpCode: str = Field(
        default="",
        title="매매구분 (Side code)",
        description=(
            "Side code for trade rows. The complete enum mapping is not "
            "declared in the available LS source — consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )
    TrdPrc: float = Field(
        default=0.0,
        title="거래단가 (Transaction unit price)",
        description=(
            "Per-share transaction price for trade rows. Currency: KRW. "
            "LS may serialize this value as a string; Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 70_000.0, 250_000.0],
    )


class CDPCQ04700Response(BaseModel):
    """CDPCQ04700 full API response envelope."""

    header: Optional[CDPCQ04700ResponseHeader] = None
    block1: Optional[CDPCQ04700OutBlock1] = Field(
        default=None,
        title="CDPCQ04700OutBlock1 (Input echo-back)",
        description="Echo-back of the input parameters.",
    )
    block2: Optional[CDPCQ04700OutBlock2] = Field(
        default=None,
        title="CDPCQ04700OutBlock2 (Transaction summary)",
        description="Account display name and record count for the date range.",
    )
    block3: List[CDPCQ04700OutBlock3] = Field(
        default_factory=list,
        title="CDPCQ04700OutBlock3 (Per-transaction detail list)",
        description="List of per-transaction rows for the requested date range.",
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str = Field(default="", title="Response code")
    rsp_msg: str = Field(default="", title="Response message")
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
