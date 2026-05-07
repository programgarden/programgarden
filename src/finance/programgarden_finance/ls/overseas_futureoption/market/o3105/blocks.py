"""Pydantic models for LS Securities OpenAPI o3105 (Overseas futures current-price / instrument detail).

o3105 returns a single-block snapshot combining instrument master metadata and
the latest market data (current price, OHLC, volume, change) for one overseas
futures contract identified by its symbol.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale, currency unit, multiplier, and tick-value semantics are
      NOT enumerated in the source available to this codebase.
    - ``sign``/``YdiffSign``/``Cgubun`` enum codes: consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3105.py``
      (symbol='ESZ25') plus neutral placeholder values.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3105RequestHeader(BlockRequestHeader):
    """o3105 request header. Inherits the standard LS request header schema."""
    pass


class O3105ResponseHeader(BlockResponseHeader):
    """o3105 response header. Inherits the standard LS response header schema."""
    pass


class O3105InBlock(BaseModel):
    """o3105InBlock — input block for the overseas futures current-price query."""

    symbol: str = Field(
        ...,
        title="Symbol (종목심볼)",
        description="LS instrument symbol code for the contract (e.g., 'ESZ25', 'NQU26').",
        examples=["ESZ25", "NQU26"],
    )


class O3105Request(BaseModel):
    """o3105 full request envelope (header + body + setup options)."""

    header: O3105RequestHeader = Field(
        O3105RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3105",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3105InBlock"], O3105InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3105InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=2,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3105"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3105OutBlock(BaseModel):
    """o3105OutBlock — combined instrument master and latest market-data snapshot.

    Decimal scale, currency unit, multiplier, and tick-value semantics are
    not declared in the source available to this codebase.
    """

    Symbol: str = Field(
        default="",
        title="Symbol code (종목코드)",
        description="LS instrument symbol code for the contract.",
        examples=["ESZ25", "NQU26"],
    )
    SymbolNm: str = Field(
        default="",
        title="Symbol name (종목명)",
        description="Human-readable instrument name.",
        examples=["E-MINI S&P500 DEC25"],
    )
    ApplDate: str = Field(
        default="",
        title="Batch receive date YYYYMMDD (종목배치수신일)",
        description=(
            "Date on which LS received this instrument's master data in batch "
            "(YYYYMMDD format)."
        ),
        examples=["20260101"],
    )
    BscGdsCd: str = Field(
        default="",
        title="Underlying product code (기초상품코드)",
        description=(
            "LS code for the underlying product. "
            "Other LS-defined codes may appear; consume as returned by LS."
        ),
        examples=["ES", "NQ"],
    )
    BscGdsNm: str = Field(
        default="",
        title="Underlying product name (기초상품명)",
        description="Name of the underlying product.",
        examples=["E-MINI S&P500"],
    )
    ExchCd: str = Field(
        default="",
        title="Exchange code (거래소코드)",
        description=(
            "LS exchange code. "
            "Other LS-defined codes may appear; consume as returned by LS."
        ),
        examples=["CME"],
    )
    ExchNm: str = Field(
        default="",
        title="Exchange name (거래소명)",
        description="Name of the listing exchange.",
        examples=["Chicago Mercantile Exchange"],
    )
    EcCd: str = Field(
        default="",
        title="Settlement type code (정산구분코드)",
        description=(
            "Settlement classification code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1"],
    )
    CrncyCd: str = Field(
        default="",
        title="Base currency code (기준통화코드)",
        description=(
            "ISO-style currency code for the contract's settlement currency."
        ),
        examples=["USD"],
    )
    NotaCd: str = Field(
        default="",
        title="Numeral system code (진법구분코드)",
        description=(
            "Numeral system classification code for price quotation. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["10"],
    )
    UntPrc: float = Field(
        default=0.0,
        title="Tick price (호가단위가격)",
        description=(
            "Minimum price tick size. Decimal scale not declared in available source."
        ),
        examples=[0.25, 0.5],
    )
    MnChgAmt: float = Field(
        default=0.0,
        title="Minimum price change amount (최소가격변동금액)",
        description=(
            "Monetary value of one minimum price movement. "
            "Multiplier semantics not declared in available source."
        ),
        examples=[12.5, 5.0],
    )
    RgltFctr: float = Field(
        default=0.0,
        title="Price adjustment factor (가격조정계수)",
        description=(
            "Price adjustment factor used by LS. Semantics not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[1.0],
    )
    CtrtPrAmt: float = Field(
        default=0.0,
        title="Per-contract amount (계약당금액)",
        description=(
            "Notional value per contract. Multiplier semantics not declared in "
            "available source."
        ),
        examples=[50.0, 20.0],
    )
    LstngMCnt: int = Field(
        default=0,
        title="Listing month count (상장개월수)",
        description="Number of listed months for this contract series.",
        examples=[3, 12],
    )
    GdsCd: str = Field(
        default="",
        title="Product type code (상품구분코드)",
        description=(
            "LS product-type classification code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["F"],
    )
    MrktCd: str = Field(
        default="",
        title="Market classification code (시장구분코드)",
        description=(
            "LS market classification code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["CME"],
    )
    EminiCd: str = Field(
        default="",
        title="E-mini classification code (Emini구분코드)",
        description=(
            "E-mini contract classification code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["Y", "N"],
    )
    LstngYr: str = Field(
        default="",
        title="Contract year (상장년)",
        description="Year component of the contract listing month.",
        examples=["2025", "2026"],
    )
    LstngM: str = Field(
        default="",
        title="Contract month (상장월)",
        description="Month component of the contract listing month as returned by LS.",
        examples=["12", "06"],
    )
    SeqNo: int = Field(
        default=0,
        title="Contract series sequence number (월물순서)",
        description=(
            "Sequence number within the contract series. "
            "Ordering semantics not declared in available source; consume as returned by LS."
        ),
        examples=[1, 2],
    )
    LstngDt: str = Field(
        default="",
        title="Listing date (상장일자)",
        description="Date the contract was listed (YYYYMMDD format).",
        examples=["20250101"],
    )
    MtrtDt: str = Field(
        default="",
        title="Maturity date (만기일자)",
        description="Contract maturity date (YYYYMMDD format).",
        examples=["20251219"],
    )
    FnlDlDt: str = Field(
        default="",
        title="Last trading date (최종거래일)",
        description="Last trading date for the contract (YYYYMMDD format).",
        examples=["20251217"],
    )
    FstTrsfrDt: str = Field(
        default="",
        title="First notice date (최초인도통지일자)",
        description=(
            "First notice / delivery date (YYYYMMDD format). "
            "May be empty for cash-settled contracts."
        ),
        examples=["", "20251201"],
    )
    EcPrc: float = Field(
        default=0.0,
        title="Settlement price (정산가격)",
        description=(
            "Previous settlement price. Decimal scale not declared in available source."
        ),
        examples=[5800.25, 21300.0],
    )
    DlDt: str = Field(
        default="",
        title="Korea trading start date (거래시작일자(한국))",
        description="Trading session start date in Korean time (YYYYMMDD).",
        examples=["20251201"],
    )
    DlStrtTm: str = Field(
        default="",
        title="Korea trading start time HHMMSS (거래시작시간(한국))",
        description=(
            "Daily trading session start time in Korean time (HHMMSS). "
            "Time zone not declared in available source."
        ),
        examples=["230000", "090000"],
    )
    DlEndTm: str = Field(
        default="",
        title="Korea trading end time HHMMSS (거래종료시간(한국))",
        description=(
            "Daily trading session end time in Korean time (HHMMSS). "
            "Time zone not declared in available source."
        ),
        examples=["160000", "153000"],
    )
    OvsStrDay: str = Field(
        default="",
        title="Local trading start date (거래시작일자(현지))",
        description="Trading session start date in local exchange time (YYYYMMDD).",
        examples=["20251201"],
    )
    OvsStrTm: str = Field(
        default="",
        title="Local trading start time HHMMSS (거래시작시간(현지))",
        description=(
            "Daily trading session start time in local exchange time (HHMMSS). "
            "Time zone not declared in available source."
        ),
        examples=["170000"],
    )
    OvsEndDay: str = Field(
        default="",
        title="Local trading end date (거래종료일자(현지))",
        description="Trading session end date in local exchange time (YYYYMMDD).",
        examples=["20251202"],
    )
    OvsEndTm: str = Field(
        default="",
        title="Local trading end time HHMMSS (거래종료시간(현지))",
        description=(
            "Daily trading session end time in local exchange time (HHMMSS). "
            "Time zone not declared in available source."
        ),
        examples=["160000"],
    )
    DlPsblCd: str = Field(
        default="",
        title="Tradeable classification code (거래가능구분코드)",
        description=(
            "Code indicating whether the contract is currently tradeable. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1", "0"],
    )
    MgnCltCd: str = Field(
        default="",
        title="Margin collection code (증거금징수구분코드)",
        description=(
            "Margin collection type code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1"],
    )
    OpngMgn: float = Field(
        default=0.0,
        title="Initial margin (개시증거금)",
        description=(
            "Initial margin requirement. "
            "Currency unit not declared in available source."
        ),
        examples=[12000.0, 5000.0],
    )
    MntncMgn: float = Field(
        default=0.0,
        title="Maintenance margin (유지증거금)",
        description=(
            "Maintenance margin requirement. "
            "Currency unit not declared in available source."
        ),
        examples=[11000.0, 4500.0],
    )
    OpngMgnR: float = Field(
        default=0.0,
        title="Initial margin rate (개시증거금율)",
        description=(
            "Initial margin rate. Scale not declared in available source."
        ),
        examples=[0.05, 0.1],
    )
    MntncMgnR: float = Field(
        default=0.0,
        title="Maintenance margin rate (유지증거금율)",
        description=(
            "Maintenance margin rate. Scale not declared in available source."
        ),
        examples=[0.04, 0.09],
    )
    DotGb: int = Field(
        default=0,
        title="Effective decimal places (유효소수점자리수)",
        description="Number of effective decimal places LS uses for price display.",
        examples=[2, 4],
    )
    TimeDiff: int = Field(
        default=0,
        title="Time difference (시차)",
        description=(
            "Time difference between local exchange time and Korean time. "
            "Unit not declared in available source; consume as returned by LS."
        ),
        examples=[-9, 0],
    )
    OvsDate: str = Field(
        default="",
        title="Local execution date (현지체결일자)",
        description="Date of the latest trade in local exchange time (YYYYMMDD).",
        examples=["20251201"],
    )
    KorDate: str = Field(
        default="",
        title="Korean execution date (한국체결일자)",
        description="Date of the latest trade in Korean time (YYYYMMDD).",
        examples=["20251202"],
    )
    TrdTm: str = Field(
        default="",
        title="Local execution time (현지체결시간)",
        description="Time of the latest trade in local exchange time (HHMMSS).",
        examples=["143025"],
    )
    RcvTm: str = Field(
        default="",
        title="Korean receipt time (한국체결시각)",
        description="Time LS received the trade in Korean time (HHMMSS).",
        examples=["233025"],
    )
    TrdP: float = Field(
        default=0.0,
        title="Execution price (체결가격)",
        description=(
            "Latest trade execution price. "
            "Decimal scale not declared in available source."
        ),
        examples=[5800.25, 21300.0],
    )
    TrdQ: int = Field(
        default=0,
        title="Execution quantity (체결수량)",
        description="Quantity of the latest trade (contracts).",
        examples=[1, 10],
    )
    TotQ: int = Field(
        default=0,
        title="Cumulative volume (누적거래량)",
        description="Cumulative trading volume for the session (contracts).",
        examples=[150000, 320000],
    )
    TrdAmt: float = Field(
        default=0.0,
        title="Trade amount (체결거래대금)",
        description=(
            "Monetary value of the latest trade. "
            "Currency unit not declared in available source."
        ),
        examples=[290012.5, 213000.0],
    )
    TotAmt: float = Field(
        default=0.0,
        title="Cumulative trade amount (누적거래대금)",
        description=(
            "Cumulative monetary value traded for the session. "
            "Currency unit not declared in available source."
        ),
        examples=[1000000000.0],
    )
    OpenP: float = Field(
        default=0.0,
        title="Open price (시가)",
        description=(
            "Opening price of the session. "
            "Decimal scale not declared in available source."
        ),
        examples=[5790.0, 21280.0],
    )
    HighP: float = Field(
        default=0.0,
        title="High price (고가)",
        description="Highest traded price of the session.",
        examples=[5810.0, 21350.0],
    )
    LowP: float = Field(
        default=0.0,
        title="Low price (저가)",
        description="Lowest traded price of the session.",
        examples=[5775.0, 21260.0],
    )
    CloseP: float = Field(
        default=0.0,
        title="Previous close price (전일종가)",
        description=(
            "Previous session's closing price. "
            "Decimal scale not declared in available source."
        ),
        examples=[5790.0, 21295.0],
    )
    YdiffP: float = Field(
        default=0.0,
        title="Change vs. previous (전일대비)",
        description=(
            "Absolute change vs. previous session's closing price. "
            "Decimal scale not declared in available source."
        ),
        examples=[10.25, -5.0],
    )
    YdiffSign: str = Field(
        default="",
        title="Change-vs-previous sign (전일대비구분)",
        description=(
            "Sign indicator vs. previous session. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["2", "5"],
    )
    Cgubun: str = Field(
        default="",
        title="Trade-side classification (체결구분)",
        description=(
            "Trade-side classification code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1", "2"],
    )
    Diff: float = Field(
        default=0.0,
        title="Change rate (등락율)",
        description=(
            "Percent change vs. previous session. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.18, -0.02],
    )


class O3105Response(BaseModel):
    """o3105 full response envelope."""

    header: Optional[O3105ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3105OutBlock] = Field(
        None,
        title="Snapshot block (출력 블록)",
        description="Combined instrument master and latest market-data snapshot.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP status code (HTTP 상태 코드)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="LS response code (응답 코드)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="LS response message (응답 메시지)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="Error message (오류 메시지)",
        description="Error message when an exception or HTTP error occurred. None on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        """Raw underlying response object (for debugging)."""
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
