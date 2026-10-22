"""Pydantic models for LS Securities OpenAPI COSOQ02701 (Overseas Foreign-Currency Deposit & Orderable Amount).

COSOQ02701 returns the foreign-currency deposit / settlement amounts and
the orderable amount available against an overseas stock account, broken
down into:

    - OutBlock1: input echo (account / currency).
    - OutBlock2: D+1 .. D+4 settlement / estimated-deposit / estimated-
      exchangeable amount projections.
    - OutBlock3: per-country / per-currency deposit + orderable amount
      detail.
    - OutBlock4: KRW deposit, withdrawable amount, KRW pre-exchange
      orderable amount, overseas margin.
    - OutBlock5: domestic / foreign-resident classification code.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Field length, currency unit, decimal scale, and the precise day
      offset for the ``…1 / …2 / …3 / …4`` suffixed projection fields
      are NOT declared in the source available to this codebase. The
      common LS convention is ``1 = D+1``, ``2 = D+2``, ``3 = D+3``,
      ``4 = D+4``, but this is not asserted as ground truth in this
      module. Consume each value as returned by LS.
    - ``examples`` come from
      ``src/finance/example/overseas_stock/run_cosoq02701.py`` where
      present, plus safe placeholder values
      (``"12345678901"`` for account numbers — never real accounts).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSOQ02701RequestHeader(BlockRequestHeader):
    """COSOQ02701 request header. Inherits the standard LS request header schema."""
    pass


class COSOQ02701ResponseHeader(BlockResponseHeader):
    """COSOQ02701 response header. Inherits the standard LS response header schema."""
    pass


class COSOQ02701InBlock1(BaseModel):
    """COSOQ02701InBlock1 — input block for foreign-currency deposit & orderable amount."""

    RecCnt: int = Field(
        default=1,
        title="레코드갯수 (Record count)",
        description="Number of records sent in this request. LS examples typically use 1.",
        examples=[1],
    )
    CrcyCode: Literal["USD"] = Field(
        default="USD",
        title="통화코드 (Currency code)",
        description=(
            "Currency code. Documented allowed value: 'USD' (U.S. dollar). The "
            "Pydantic Literal narrows to 'USD' to match the LS spec wording — "
            "additional values, if any, are not declared in available source."
        ),
        examples=["USD"],
    )


class COSOQ02701Request(BaseModel):
    """COSOQ02701 full request envelope (header + body + setup options)."""
    header: COSOQ02701RequestHeader = Field(
        COSOQ02701RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSOQ02701",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["COSOQ02701InBlock1"], COSOQ02701InBlock1] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'COSOQ02701InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=2,
            on_rate_limit="wait",
            rate_limit_key="COSOQ02701"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class COSOQ02701OutBlock1(BaseModel):
    """COSOQ02701OutBlock1 — input echo block.

    LS echoes the InBlock1 inputs back along with the account number.
    The actual data lives in OutBlock2 / 3 / 4 / 5.
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
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="Echoed currency code from the request.",
        examples=["USD"],
    )


class COSOQ02701OutBlock2(BaseModel):
    """COSOQ02701OutBlock2 — multi-day settlement / deposit / exchange projections.

    Each ``…1 / …2 / …3 / …4`` suffixed field set covers a successive
    settlement day. The exact day offset (commonly D+1 .. D+4 in LS
    products) is not asserted in this module — consume as returned by LS.
    """
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="Currency code for this row (e.g., 'USD').",
        examples=["USD"],
    )

    FcurrBuyAdjstAmt1: float = Field(
        default=0.0,
        title="외화매수정산금1 (Foreign-currency buy adjustment amount 1)",
        description="Foreign-currency buy adjustment amount, projection bucket 1.",
        examples=[0.0, 1000.0],
    )
    FcurrBuyAdjstAmt2: float = Field(
        default=0.0,
        title="외화매수정산금2 (Foreign-currency buy adjustment amount 2)",
        description="Foreign-currency buy adjustment amount, projection bucket 2.",
        examples=[0.0, 1000.0],
    )
    FcurrBuyAdjstAmt3: float = Field(
        default=0.0,
        title="외화매수정산금3 (Foreign-currency buy adjustment amount 3)",
        description="Foreign-currency buy adjustment amount, projection bucket 3.",
        examples=[0.0, 1000.0],
    )
    FcurrBuyAdjstAmt4: float = Field(
        default=0.0,
        title="외화매수정산금4 (Foreign-currency buy adjustment amount 4)",
        description="Foreign-currency buy adjustment amount, projection bucket 4.",
        examples=[0.0, 1000.0],
    )

    FcurrSellAdjstAmt1: float = Field(
        default=0.0,
        title="외화매도정산금1 (Foreign-currency sell adjustment amount 1)",
        description="Foreign-currency sell adjustment amount, projection bucket 1.",
        examples=[0.0, 1000.0],
    )
    FcurrSellAdjstAmt2: float = Field(
        default=0.0,
        title="외화매도정산금2 (Foreign-currency sell adjustment amount 2)",
        description="Foreign-currency sell adjustment amount, projection bucket 2.",
        examples=[0.0, 1000.0],
    )
    FcurrSellAdjstAmt3: float = Field(
        default=0.0,
        title="외화매도정산금3 (Foreign-currency sell adjustment amount 3)",
        description="Foreign-currency sell adjustment amount, projection bucket 3.",
        examples=[0.0, 1000.0],
    )
    FcurrSellAdjstAmt4: float = Field(
        default=0.0,
        title="외화매도정산금4 (Foreign-currency sell adjustment amount 4)",
        description="Foreign-currency sell adjustment amount, projection bucket 4.",
        examples=[0.0, 1000.0],
    )

    PrsmptFcurrDps1: float = Field(
        default=0.0,
        title="추정외화예수금1 (Estimated foreign-currency deposit 1)",
        description="Estimated foreign-currency deposit, projection bucket 1.",
        examples=[0.0, 1000.0],
    )
    PrsmptFcurrDps2: float = Field(
        default=0.0,
        title="추정외화예수금2 (Estimated foreign-currency deposit 2)",
        description="Estimated foreign-currency deposit, projection bucket 2.",
        examples=[0.0, 1000.0],
    )
    PrsmptFcurrDps3: float = Field(
        default=0.0,
        title="추정외화예수금3 (Estimated foreign-currency deposit 3)",
        description="Estimated foreign-currency deposit, projection bucket 3.",
        examples=[0.0, 1000.0],
    )
    PrsmptFcurrDps4: float = Field(
        default=0.0,
        title="추정외화예수금4 (Estimated foreign-currency deposit 4)",
        description="Estimated foreign-currency deposit, projection bucket 4.",
        examples=[0.0, 1000.0],
    )

    PrsmptMxchgAbleAmt1: float = Field(
        default=0.0,
        title="추정환전가능금1 (Estimated exchangeable amount 1)",
        description="Estimated exchangeable amount, projection bucket 1.",
        examples=[0.0, 1000.0],
    )
    PrsmptMxchgAbleAmt2: float = Field(
        default=0.0,
        title="추정환전가능금2 (Estimated exchangeable amount 2)",
        description="Estimated exchangeable amount, projection bucket 2.",
        examples=[0.0, 1000.0],
    )
    PrsmptMxchgAbleAmt3: float = Field(
        default=0.0,
        title="추정환전가능금3 (Estimated exchangeable amount 3)",
        description="Estimated exchangeable amount, projection bucket 3.",
        examples=[0.0, 1000.0],
    )
    PrsmptMxchgAbleAmt4: float = Field(
        default=0.0,
        title="추정환전가능금4 (Estimated exchangeable amount 4)",
        description="Estimated exchangeable amount, projection bucket 4.",
        examples=[0.0, 1000.0],
    )


class COSOQ02701OutBlock3(BaseModel):
    """COSOQ02701OutBlock3 — per-country / per-currency deposit + orderable amount detail.

    One row per country / currency for which the account holds funds.
    Decimal scale not declared in available source — consume as returned
    by LS.
    """
    CntryNm: str = Field(
        default="",
        title="국가명 (Country name)",
        description="Display name of the country (Korean text per LS spec wording).",
        examples=["미국", "일본"],
    )
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="ISO-4217-style currency code for this country bucket.",
        examples=["USD", "JPY"],
    )
    T4FcurrDps: float = Field(
        default=0.0,
        title="T4외화예수금 (T+4 foreign-currency deposit)",
        description="Foreign-currency deposit projected to T+4 settlement.",
        examples=[0.0, 1000.0],
    )
    FcurrDps: float = Field(
        default=0.0,
        title="외화예수금 (Foreign-currency deposit)",
        description="Current foreign-currency deposit balance.",
        examples=[0.0, 1000.0],
    )
    FcurrOrdAbleAmt: float = Field(
        default=0.0,
        title="외화주문가능금액 (Foreign-currency orderable amount)",
        description="Foreign-currency amount available for new orders.",
        examples=[0.0, 1000.0],
    )
    PrexchOrdAbleAmt: float = Field(
        default=0.0,
        title="가환전주문가능금액 (Pre-exchange orderable amount)",
        description="Foreign-currency amount available for new orders via pre-exchange.",
        examples=[0.0, 1000.0],
    )
    FcurrOrdAmt: float = Field(
        default=0.0,
        title="외화주문금액 (Foreign-currency order amount)",
        description="Foreign-currency amount currently committed to open orders.",
        examples=[0.0, 1000.0],
    )
    FcurrPldgAmt: float = Field(
        default=0.0,
        title="외화담보금액 (Foreign-currency pledge amount)",
        description="Foreign-currency amount held as collateral / pledge.",
        examples=[0.0, 1000.0],
    )
    ExecRuseFcurrAmt: float = Field(
        default=0.0,
        title="체결재사용외화금액 (Execution-reuse foreign-currency amount)",
        description="Foreign-currency amount available for reuse from same-day executions.",
        examples=[0.0, 1000.0],
    )
    FcurrMxchgAbleAmt: float = Field(
        default=0.0,
        title="외화환전가능금 (Foreign-currency exchangeable amount)",
        description="Foreign-currency amount eligible for exchange (back to KRW or other).",
        examples=[0.0, 1000.0],
    )
    BaseXchrat: float = Field(
        default=0.0,
        title="기준환율 (Base FX rate)",
        description=(
            "Base FX rate used for KRW conversion of this currency. Decimal scale "
            "not declared in available source."
        ),
        examples=[0.0, 1300.0],
    )


class COSOQ02701OutBlock4(BaseModel):
    """COSOQ02701OutBlock4 — KRW deposit & overseas-margin summary.

    Note on integer typing: ``WonDpsBalAmt`` / ``MnyoutAbleAmt`` /
    ``WonPrexchAbleAmt`` are declared ``int`` in this SDK matching LS
    response shape. Decimal precision is not preserved if LS ever returns
    fractional KRW amounts; consume as returned by LS.
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Record count for this aggregate block.",
        examples=[0, 1],
    )
    WonDpsBalAmt: int = Field(
        default=0,
        title="원화예수금잔고금액 (KRW deposit balance amount)",
        description="KRW deposit balance.",
        examples=[0, 1000000],
    )
    MnyoutAbleAmt: int = Field(
        default=0,
        title="출금가능금액 (Withdrawable amount)",
        description="Withdrawable balance, in KRW.",
        examples=[0, 1000000],
    )
    WonPrexchAbleAmt: int = Field(
        default=0,
        title="원화가환전가능금액 (KRW pre-exchange orderable amount)",
        description="KRW amount available for pre-exchange order placement.",
        examples=[0, 1000000],
    )
    OvrsMgn: float = Field(
        default=0.0,
        title="해외증거금 (Overseas margin)",
        description=(
            "Overseas trading margin amount. Currency / decimal scale not declared "
            "in available source — consume as returned by LS."
        ),
        examples=[0.0, 100000.0],
    )


class COSOQ02701OutBlock5(BaseModel):
    """COSOQ02701OutBlock5 — domestic / foreign-resident classification code."""
    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Record count for this aggregate block.",
        examples=[0, 1],
    )
    NrfCode: str = Field(
        default="",
        title="내외국인코드 (Domestic / foreign-resident code)",
        description=(
            "Domestic / foreign-resident classification code. Enum mapping not "
            "declared in available source — consume as returned by LS."
        ),
        examples=["", "1"],
    )


class COSOQ02701Response(BaseModel):
    """COSOQ02701 full response envelope."""
    header: Optional[COSOQ02701ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[COSOQ02701OutBlock1] = Field(
        None,
        title="첫번째 출력 블록 (First output block — input echo)",
        description="Input echo block (mirrors the InBlock1 inputs).",
    )
    block2: List[COSOQ02701OutBlock2] = Field(
        default_factory=list,
        title="두번째 출력 블록 리스트 (Second output block — projection rows)",
        description="Multi-day settlement / deposit / exchange projection rows.",
    )
    block3: List[COSOQ02701OutBlock3] = Field(
        default_factory=list,
        title="세번째 출력 블록 리스트 (Third output block — per-country rows)",
        description="Per-country / per-currency deposit + orderable amount detail.",
    )
    block4: Optional[COSOQ02701OutBlock4] = Field(
        None,
        title="네번째 출력 블록 (Fourth output block — KRW deposit summary)",
        description="KRW deposit / withdrawable amount / overseas margin summary.",
    )
    block5: Optional[COSOQ02701OutBlock5] = Field(
        None,
        title="다섯번째 출력 블록 (Fifth output block — resident code)",
        description="Domestic / foreign-resident classification code.",
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
