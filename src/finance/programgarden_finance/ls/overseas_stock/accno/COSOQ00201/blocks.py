"""Pydantic models for LS Securities OpenAPI COSOQ00201 (Overseas Stock Comprehensive Balance Valuation).

COSOQ00201 returns a comprehensive snapshot of an overseas stock account's
balance and valuation as of ``BaseDt`` (YYYYMMDD), broken down into:

    - OutBlock1: input echo (account / base date / filters).
    - OutBlock2: overall valuation summary (returns, KRW-converted totals,
      per-day estimated deposit, loan amount, etc.).
    - OutBlock3: per-currency balance detail (deposit, valuation, P&L,
      base FX rate, etc.).
    - OutBlock4: per-symbol balance detail (quantity, unit price,
      foreign-currency valuation, base FX rate, loan terms, etc.).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Field length, currency unit, decimal scale, and complete enum
      mappings are NOT declared in the source available to this codebase.
      Where the Korean spec is silent the description states "consume
      as returned by LS" and does not invent additional values.
    - ``examples`` come from
      ``src/finance/example/overseas_stock/run_cosoq00201.py`` where
      present, plus safe placeholder values
      (``"12345678901"`` for account numbers — never real accounts).

Note on amount-field types:
    Several fields that semantically represent monetary amounts are
    declared as ``float`` (``DpsConvEvalAmt``, ``StkConvEvalAmt``, …).
    LS may return these as numeric or stringified-numeric depending on
    the gateway; Pydantic v2 coerces stringified numerics into ``float``
    automatically. The decimal scale is not declared in the source
    available to this codebase — consume the value as returned by LS.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSOQ00201RequestHeader(BlockRequestHeader):
    """COSOQ00201 request header. Inherits the standard LS request header schema."""
    pass


class COSOQ00201ResponseHeader(BlockResponseHeader):
    """COSOQ00201 response header. Inherits the standard LS response header schema."""
    pass


class COSOQ00201InBlock1(BaseModel):
    """COSOQ00201InBlock1 — input block for overseas stock comprehensive balance valuation."""

    RecCnt: int = Field(
        default=1,
        title="레코드갯수 (Record count)",
        description="Number of records sent in this request. LS examples typically use 1.",
        examples=[1],
    )
    BaseDt: str = Field(
        default="",
        title="기준일자 (Base date)",
        description=(
            "Reference date for the balance snapshot, in YYYYMMDD format. "
            "Empty string is rejected by LS; pass a concrete date."
        ),
        examples=["20231020", "20260122"],
    )
    CrcyCode: str = Field(
        default="ALL",
        title="통화코드 (Currency code)",
        description=(
            "Currency filter. 'ALL' = all currencies (전체), 'USD' = U.S. dollar "
            "(미국). The LS spec wording for this TR ends with '등' (etc.); "
            "additional ISO-4217-style currency codes may be accepted server-side."
        ),
        examples=["ALL", "USD"],
    )
    AstkBalTpCode: str = Field(
        default="00",
        title="해외증권잔고구분코드 (Overseas-stock balance type code)",
        description=(
            "Overseas-stock balance classification filter. '00' = all (전체), "
            "'10' = standard (일반), '20' = fractional (소수점)."
        ),
        examples=["00", "10", "20"],
    )


class COSOQ00201Request(BaseModel):
    """COSOQ00201 full request envelope (header + body + setup options)."""
    header: COSOQ00201RequestHeader = COSOQ00201RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="COSOQ00201",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["COSOQ00201InBlock1"], COSOQ00201InBlock1] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'COSOQ00201InBlock1'.",
    )
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=2,
        on_rate_limit="wait",
        rate_limit_key="COSOQ00201"
    )


class COSOQ00201OutBlock1(BaseModel):
    """COSOQ00201OutBlock1 — input echo block.

    LS echoes the InBlock1 inputs back in OutBlock1 along with the
    account number. The actual valuation data lives in OutBlock2 / 3 / 4.
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Echoed record count from the request.",
        examples=[0, 1],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Account number associated with the query. Length not declared in available source.",
        examples=["12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="비밀번호 (Account password)",
        description=(
            "Account password as echoed by LS. Treat as sensitive — avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )
    BaseDt: str = Field(
        default="",
        title="기준일자 (Base date)",
        description="Echoed base date in YYYYMMDD format.",
        examples=["20231020"],
    )
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="Echoed currency filter ('ALL' = all, 'USD' = U.S. dollar, etc.).",
        examples=["ALL", "USD"],
    )
    AstkBalTpCode: str = Field(
        default="",
        title="해외증권잔고구분코드 (Overseas-stock balance type code)",
        description="Echoed balance type filter. '00' = all, '10' = standard, '20' = fractional.",
        examples=["00", "10", "20"],
    )


class COSOQ00201OutBlock2(BaseModel):
    """COSOQ00201OutBlock2 — overall valuation summary.

    Aggregated valuation across all currencies, expressed in KRW where
    converted (``…ConvEvalAmt``) and in KRW directly for ``WonEvalSumAmt``
    / ``WonDpsBalAmt``. Decimal scale not declared in available source.
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Record count for this aggregate block.",
        examples=[0, 1],
    )
    ErnRat: float = Field(
        default=0.0,
        title="수익율 (Return rate)",
        description=(
            "Account-level return rate. Unit (percent vs. ratio) and sign convention "
            "are not declared in available source — consume as returned by LS."
        ),
        examples=[0.0, 12.34, -3.21],
    )
    DpsConvEvalAmt: float = Field(
        default=0.0,
        title="예수금환산평가금액 (Deposit converted-valuation amount)",
        description="Deposit valuation converted to KRW.",
        examples=[0.0, 1000000.0],
    )
    StkConvEvalAmt: float = Field(
        default=0.0,
        title="주식환산평가금액 (Stock converted-valuation amount)",
        description="Stock valuation converted to KRW.",
        examples=[0.0, 5000000.0],
    )
    DpsastConvEvalAmt: float = Field(
        default=0.0,
        title="예탁자산환산평가금액 (Deposited-asset converted-valuation amount)",
        description="Deposited-asset valuation converted to KRW.",
        examples=[0.0, 6000000.0],
    )
    WonEvalSumAmt: float = Field(
        default=0.0,
        title="원화평가합계금액 (KRW total valuation amount)",
        description="Total valuation expressed directly in KRW.",
        examples=[0.0, 6000000.0],
    )
    ConvEvalPnlAmt: float = Field(
        default=0.0,
        title="환산평가손익금액 (Converted-valuation P&L amount)",
        description="Converted P&L amount (in KRW). Sign indicates gain (+) / loss (-).",
        examples=[0.0, 100000.0, -50000.0],
    )
    WonDpsBalAmt: float = Field(
        default=0.0,
        title="원화예수금잔고금액 (KRW deposit balance amount)",
        description="KRW deposit balance.",
        examples=[0.0, 200000.0],
    )
    D2EstiDps: float = Field(
        default=0.0,
        title="D2추정예수금 (D+2 estimated deposit)",
        description="Estimated deposit balance two business days after the base date.",
        examples=[0.0, 250000.0],
    )
    LoanAmt: float = Field(
        default=0.0,
        title="대출금액 (Loan amount)",
        description="Total loan amount. Currency / decimal scale not declared in available source.",
        examples=[0.0, 100000.0],
    )


class COSOQ00201OutBlock3(BaseModel):
    """COSOQ00201OutBlock3 — per-currency balance detail row.

    One record per currency present in the account. Foreign-currency
    fields are denominated in ``CrcyCode``; converted-valuation fields
    are expressed in KRW. Decimal scale not declared in available source.
    """
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="ISO-4217-style currency code (e.g., 'USD', 'JPY').",
        examples=["USD", "JPY"],
    )
    FcurrDps: float = Field(
        default=0.0,
        title="외화예수금 (Foreign-currency deposit)",
        description="Foreign-currency deposit balance in ``CrcyCode``.",
        examples=[0.0, 1000.0],
    )
    FcurrEvalAmt: float = Field(
        default=0.0,
        title="외화평가금액 (Foreign-currency valuation amount)",
        description="Foreign-currency valuation amount in ``CrcyCode``.",
        examples=[0.0, 5000.0],
    )
    FcurrEvalPnlAmt: float = Field(
        default=0.0,
        title="외화평가손익금액 (Foreign-currency valuation P&L amount)",
        description="Foreign-currency P&L in ``CrcyCode``. Sign indicates gain (+) / loss (-).",
        examples=[0.0, 100.0, -50.0],
    )
    PnlRat: float = Field(
        default=0.0,
        title="손익율 (P&L ratio)",
        description=(
            "P&L ratio for this currency bucket. Unit (percent vs. ratio) not "
            "declared in available source — consume as returned by LS."
        ),
        examples=[0.0, 12.34],
    )
    BaseXchrat: float = Field(
        default=0.0,
        title="기준환율 (Base FX rate)",
        description=(
            "Base FX rate used to convert ``CrcyCode`` to KRW. Decimal scale not "
            "declared in available source."
        ),
        examples=[0.0, 1300.0],
    )
    DpsConvEvalAmt: float = Field(
        default=0.0,
        title="예수금환산평가금액 (Deposit converted-valuation amount, KRW)",
        description="Deposit valuation for this currency converted to KRW.",
        examples=[0.0, 1300000.0],
    )
    PchsAmt: float = Field(
        default=0.0,
        title="매입금액 (Purchase amount)",
        description="Total purchase amount for instruments held in ``CrcyCode``.",
        examples=[0.0, 4000.0],
    )
    StkConvEvalAmt: float = Field(
        default=0.0,
        title="주식환산평가금액 (Stock converted-valuation amount, KRW)",
        description="Stock valuation for this currency converted to KRW.",
        examples=[0.0, 5500000.0],
    )
    ConvEvalPnlAmt: float = Field(
        default=0.0,
        title="환산평가손익금액 (Converted-valuation P&L amount, KRW)",
        description="Converted P&L for this currency in KRW. Sign indicates gain (+) / loss (-).",
        examples=[0.0, 100000.0, -50000.0],
    )
    FcurrBuyAmt: float = Field(
        default=0.0,
        title="외화매수금액 (Foreign-currency buy amount)",
        description="Foreign-currency buy amount in ``CrcyCode``.",
        examples=[0.0, 4000.0],
    )
    FcurrOrdAbleAmt: float = Field(
        default=0.0,
        title="외화주문가능금액 (Foreign-currency orderable amount)",
        description="Foreign-currency amount available for new orders in ``CrcyCode``.",
        examples=[0.0, 1000.0],
    )
    LoanAmt: float = Field(
        default=0.0,
        title="대출금액 (Loan amount)",
        description="Loan amount for this currency bucket. Currency / scale not declared in available source.",
        examples=[0.0, 1000.0],
    )


class COSOQ00201OutBlock4(BaseModel):
    """COSOQ00201OutBlock4 — per-symbol balance detail row.

    One record per held symbol. Foreign-currency fields are in
    ``CrcyCode``; converted-valuation fields are in KRW. Decimal scale
    not declared in available source — consume as returned by LS.
    """
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="ISO-4217-style currency code for the symbol's quote currency.",
        examples=["USD", "JPY"],
    )
    ShtnIsuNo: str = Field(
        default="",
        title="단축종목번호 (Short issue code)",
        description="Short symbol code (e.g., 'AAPL', 'MSFT').",
        examples=["AAPL", "MSFT"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Issue code)",
        description="Full LS-internal issue code. May differ from ``ShtnIsuNo`` for some markets.",
        examples=["AAPL", "MSFT"],
    )
    JpnMktHanglIsuNm: str = Field(
        default="",
        title="일본시장한글종목명 (Japan market Korean issue name)",
        description="Korean display name when applicable to Japan market; empty otherwise.",
        examples=["", "도요타자동차"],
    )
    AstkBalTpCode: str = Field(
        default="",
        title="해외증권잔고구분코드 (Overseas-stock balance type code)",
        description="Balance type for this position. '10' = standard, '20' = fractional.",
        examples=["10", "20"],
    )
    AstkBalTpCodeNm: str = Field(
        default="",
        title="해외증권잔고구분코드명 (Overseas-stock balance type name)",
        description="Display name of the balance type.",
        examples=["일반", "소수점"],
    )
    AstkBalQty: int = Field(
        default=0,
        title="해외증권잔고수량 (Overseas-stock balance quantity)",
        description=(
            "Holdings quantity. Integer typed in the SDK — fractional positions "
            "(``AstkBalTpCode='20'``) may be truncated by Pydantic int coercion."
        ),
        examples=[0, 100],
    )
    AstkSellAbleQty: int = Field(
        default=0,
        title="해외증권매도가능수량 (Overseas-stock sellable quantity)",
        description=(
            "Quantity available to sell. Integer typed in the SDK — fractional "
            "positions may be truncated by Pydantic int coercion."
        ),
        examples=[0, 100],
    )
    FcstckUprc: float = Field(
        default=0.0,
        title="외화증권단가 (Foreign-currency security unit price)",
        description="Average unit price in ``CrcyCode``.",
        examples=[0.0, 150.25],
    )
    FcurrBuyAmt: float = Field(
        default=0.0,
        title="외화매수금액 (Foreign-currency buy amount)",
        description="Total purchase amount in ``CrcyCode``.",
        examples=[0.0, 15025.0],
    )
    FcstckMktIsuCode: str = Field(
        default="",
        title="외화증권시장종목코드 (Foreign-currency market issue code)",
        description="Market-prefixed issue code (LS-internal format).",
        examples=["", "NASD.AAPL"],
    )
    OvrsScrtsCurpri: float = Field(
        default=0.0,
        title="해외증권시세 (Overseas-stock current price)",
        description="Current market price in ``CrcyCode`` as of ``BaseDt``.",
        examples=[0.0, 152.10],
    )
    FcurrEvalAmt: float = Field(
        default=0.0,
        title="외화평가금액 (Foreign-currency valuation amount)",
        description="Foreign-currency valuation in ``CrcyCode``.",
        examples=[0.0, 15210.0],
    )
    FcurrEvalPnlAmt: float = Field(
        default=0.0,
        title="외화평가손익금액 (Foreign-currency valuation P&L amount)",
        description="Foreign-currency P&L in ``CrcyCode``. Sign indicates gain (+) / loss (-).",
        examples=[0.0, 185.0, -50.0],
    )
    PnlRat: float = Field(
        default=0.0,
        title="손익율 (P&L ratio)",
        description=(
            "P&L ratio for this position. Unit (percent vs. ratio) not declared "
            "in available source — consume as returned by LS."
        ),
        examples=[0.0, 12.34, -3.21],
    )
    BaseXchrat: float = Field(
        default=0.0,
        title="기준환율 (Base FX rate)",
        description="Base FX rate used to convert ``CrcyCode`` to KRW.",
        examples=[0.0, 1300.0],
    )
    PchsAmt: float = Field(
        default=0.0,
        title="매입금액 (Purchase amount)",
        description="Total purchase amount. Currency follows ``CrcyCode`` per LS spec wording.",
        examples=[0.0, 15025.0],
    )
    DpsConvEvalAmt: float = Field(
        default=0.0,
        title="예수금환산평가금액 (Deposit converted-valuation amount, KRW)",
        description="Deposit converted-valuation contribution from this position, in KRW.",
        examples=[0.0, 1300000.0],
    )
    StkConvEvalAmt: float = Field(
        default=0.0,
        title="주식환산평가금액 (Stock converted-valuation amount, KRW)",
        description="Stock valuation for this position converted to KRW.",
        examples=[0.0, 19773000.0],
    )
    ConvEvalPnlAmt: float = Field(
        default=0.0,
        title="환산평가손익금액 (Converted-valuation P&L amount, KRW)",
        description="Converted P&L for this position in KRW. Sign indicates gain (+) / loss (-).",
        examples=[0.0, 240500.0, -65000.0],
    )
    AstkSettQty: float = Field(
        default=0.0,
        title="해외증권결제수량 (Overseas-stock settlement quantity)",
        description=(
            "Settled quantity. Float typed to accommodate fractional positions "
            "(``AstkBalTpCode='20'``)."
        ),
        examples=[0.0, 100.0, 0.5],
    )
    MktTpNm: str = Field(
        default="",
        title="시장구분명 (Market type name)",
        description="Display name of the market (e.g., '뉴욕', '나스닥', '도쿄').",
        examples=["뉴욕", "나스닥"],
    )
    FcurrMktCode: str = Field(
        default="",
        title="외화시장코드 (Foreign-currency market code)",
        description=(
            "LS-internal foreign-currency market code. Enum mapping not declared "
            "in available source — consume as returned by LS."
        ),
        examples=["81", "82"],
    )
    LoanDt: str = Field(
        default="",
        title="대출일자 (Loan date)",
        description="Loan date in YYYYMMDD format. Empty when not applicable.",
        examples=["", "20260101"],
    )
    LoanDtlClssCode: str = Field(
        default="",
        title="대출상세분류코드 (Loan detail classification code)",
        description=(
            "Loan classification code. Enum mapping not declared in available "
            "source — consume as returned by LS."
        ),
        examples=["", "01"],
    )
    LoanAmt: float = Field(
        default=0.0,
        title="대출금액 (Loan amount)",
        description="Loan amount for this position. Currency / scale not declared in available source.",
        examples=[0.0, 1000.0],
    )
    DueDt: str = Field(
        default="",
        title="만기일자 (Due / maturity date)",
        description="Loan maturity date in YYYYMMDD format. Empty when not applicable.",
        examples=["", "20260301"],
    )
    AstkBasePrc: float = Field(
        default=0.0,
        title="해외증권기준가격 (Overseas-stock base price)",
        description=(
            "Base reference price for the position in ``CrcyCode``. Exact derivation "
            "(close-of-day, settlement price, etc.) not declared in available source."
        ),
        examples=[0.0, 150.0],
    )


class COSOQ00201Response(BaseModel):
    """COSOQ00201 full response envelope."""
    header: Optional[COSOQ00201ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[COSOQ00201OutBlock1] = Field(
        None,
        title="첫번째 출력 블록 (First output block — input echo)",
        description="Input echo block (mirrors the InBlock1 inputs).",
    )
    block2: Optional[COSOQ00201OutBlock2] = Field(
        None,
        title="두번째 출력 블록 (Second output block — overall valuation summary)",
        description="Overall valuation summary across all currencies.",
    )
    block3: List[COSOQ00201OutBlock3] = Field(
        default_factory=list,
        title="세번째 출력 블록 리스트 (Third output block — per-currency rows)",
        description="Per-currency balance detail rows.",
    )
    block4: List[COSOQ00201OutBlock4] = Field(
        default_factory=list,
        title="네번째 출력 블록 리스트 (Fourth output block — per-symbol rows)",
        description="Per-symbol balance detail rows.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="응답 코드 (LS response code)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="응답 메시지 (LS response message)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지 (Error message)",
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
