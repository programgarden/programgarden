"""Pydantic models for LS Securities OpenAPI t1488 (예상체결가등락율상위조회 / Top expected-conclusion percent-change screen).

t1488 returns the ranked list of Korean stock issues by expected-conclusion
(auction-anticipated) percent change versus previous close. Filters include
market division (KOSPI / KOSDAQ), up/down side, session phase (pre-open /
post-close / latest-quote), target-exclusion bitmask, volume bucket and an
expected-price / expected-volume window. Pagination uses the ``idx`` cursor
echoed back in ``t1488OutBlock``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``jongchk`` (target-exclusion bitmask) — bit values listed in the
      LS source are mirrored verbatim; LS publishes the bit layout for
      this TR (e.g., ``0x00000080`` = 관리종목).
    - The output ``OutBlock1.sign`` (전일대비구분) — LS does NOT declare
      the enum mapping for t1488 in the source available to this
      codebase. Consume as returned by LS; do not assume the
      ``1~5`` mapping used by other LS market TRs.
    - Sign convention of ``change``, currency unit of price / quote /
      change fields, decimal scale of ``price``/``offerho``/``bidho``,
      row ordering within ``OutBlock1``, and meaning of ``cnt``
      (연속일수) counting window are NOT declared in available source —
      consume as returned by LS.
    - ``diff`` (LS scale 6.2) is serialized as a JSON string by LS in
      the example response (e.g., ``"029.01"``, ``"009.66"``); Pydantic
      coerces to float.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1488RequestHeader(BlockRequestHeader):
    """t1488 request header. Inherits the standard LS request header schema."""
    pass


class T1488ResponseHeader(BlockResponseHeader):
    """t1488 response header. Inherits the standard LS response header schema."""
    pass


class T1488InBlock(BaseModel):
    """t1488InBlock — input block for the expected-conclusion percent-change top screen."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="거래소구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ. Length 1.",
        examples=["0", "1", "2"],
    )
    sign: Literal["1", "2"] = Field(
        ...,
        title="상하락구분 (Direction filter)",
        description="Direction filter for ranking. '1' = up (상승), '2' = down (하락). Length 1.",
        examples=["1", "2"],
    )
    jgubun: Literal["1", "2", "3"] = Field(
        ...,
        title="장구분 (Session phase)",
        description=(
            "Session phase. '1' = pre-open (장전), '2' = post-close (장후), "
            "'3' = latest quote vs. previous close (직전대비). Length 1."
        ),
        examples=["1", "2", "3"],
    )
    jongchk: str = Field(
        ...,
        title="종목체크 (Target-exclusion bitmask)",
        description=(
            "Target-exclusion bitmask string (length 12). LS-declared bits: "
            "0x00000080 관리종목, 0x00000100 시장경보, 0x00000200 거래정지, "
            "0x00004000 우선주, 0x00200000 증거금50/100, 0x00400000 증거금50, "
            "0x00800000 증거금100, 0x01000000 정리매매, 0x04000000 투자유의, "
            "0x80000000 불성실공시. Combine bits with bitwise OR and "
            "serialize as a hex string (e.g., '0x00000080'). '0' or '0x00000000' "
            "means no exclusion."
        ),
        examples=["0x00000080", "0x00000000", "0"],
    )
    idx: int = Field(
        default=0,
        title="IDX (Pagination cursor)",
        description=(
            "Pagination cursor (LS spec: Space on first request, then echo "
            "back ``T1488OutBlock.idx`` from the previous response). "
            "Treat as opaque LS-defined token; this client serializes 0 "
            "on the first request, which LS accepts per the official "
            "example. Length 4."
        ),
        examples=[0, 20],
    )
    volume: Literal["0", "1", "2", "3", "4", "5"] = Field(
        ...,
        title="거래량 (Cumulative volume bucket)",
        description=(
            "Cumulative volume bucket filter. Length 1. "
            "'0' = all (전체), "
            "'1' = ≥10,000 shares (1만주이상), "
            "'2' = ≥50,000 shares (5만주이상), "
            "'3' = ≥100,000 shares (10만주이상), "
            "'4' = ≥500,000 shares (50만주이상), "
            "'5' = ≥1,000,000 shares (백만주이상)."
        ),
        examples=["0", "1", "2", "3", "4", "5"],
    )
    yesprice: int = Field(
        default=0,
        title="예상체결시작가격 (Expected-conclusion price lower bound)",
        description=(
            "Inclusive lower bound for the expected-conclusion price filter. "
            "Rows satisfy ``yesprice <= 예상체결가``. 0 means no lower bound. "
            "Decimal scale and currency unit not declared in available "
            "source. Length 8."
        ),
        examples=[0, 1000],
    )
    yeeprice: int = Field(
        default=0,
        title="예상체결종료가격 (Expected-conclusion price upper bound)",
        description=(
            "Inclusive upper bound for the expected-conclusion price filter. "
            "Rows satisfy ``예상체결가 <= yeeprice``. 0 means no upper bound. "
            "Length 8."
        ),
        examples=[0, 100000],
    )
    yevolume: int = Field(
        default=0,
        title="예상체결량 (Expected-conclusion volume threshold)",
        description=(
            "Inclusive lower bound for the expected-conclusion volume filter "
            "in shares. Rows satisfy ``예상체결량 >= yevolume``. 0 means no "
            "minimum. Length 12."
        ),
        examples=[0, 10000],
    )


class T1488Request(BaseModel):
    """t1488 request envelope."""

    header: T1488RequestHeader = T1488RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1488",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1488InBlock"], T1488InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1488"
    )


class T1488OutBlock(BaseModel):
    """t1488OutBlock — continuation block carrying the ``idx`` paging cursor."""

    idx: int = Field(
        ...,
        title="IDX (Pagination cursor)",
        description=(
            "Pagination cursor for the next paged request. Pass back as "
            "``T1488InBlock.idx``. Treat as opaque LS-defined token. "
            "Length 4."
        ),
        examples=[0, 20],
    )


class T1488OutBlock1(BaseModel):
    """t1488OutBlock1 — one ranked expected-conclusion percent-change row.

    Row ordering within the list is NOT declared in the source available to
    this codebase; consume as returned by LS.
    """

    hname: str = Field(
        default="",
        title="한글명 (Korean name)",
        description="Korean issue name as reported by LS. Length 20.",
        examples=["프로스테믹스", "에이프로젠"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description=(
            "Current price as reported by LS. Decimal scale and currency "
            "unit not declared in available source. Length 8."
        ),
        examples=[5870, 1635],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus previous close. Length 1. Enum mapping "
            "is NOT declared in available LS source for t1488 — consume "
            "as returned by LS. Do not assume the 1=상한 / 2=상승 / "
            "3=보합 / 4=하한 / 5=하락 mapping used by other LS market TRs."
        ),
        examples=["2", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of price change versus previous close. Sign "
            "convention is not declared in available LS source — consume "
            "as returned by LS. Length 8."
        ),
        examples=[1320, 144],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '029.01' or "
            "'009.66'); Pydantic auto-coerces to float."
        ),
        examples=[29.01, 9.66, 0.0],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description=(
            "Cumulative traded volume in shares for the session. Length 12."
        ),
        examples=[48087, 142226],
    )
    offerrem: int = Field(
        default=0,
        title="매도잔량 (Best ask quantity)",
        description=(
            "Remaining ask (sell) quantity at the best ask price in shares. "
            "Length 12."
        ),
        examples=[504, 3009],
    )
    offerho: int = Field(
        default=0,
        title="매도호가 (Best ask price)",
        description=(
            "Best (level-1) ask price. Decimal scale and currency unit not "
            "declared in available source. Length 8."
        ),
        examples=[5870, 1636],
    )
    bidho: int = Field(
        default=0,
        title="매수호가 (Best bid price)",
        description=(
            "Best (level-1) bid price. Decimal scale and currency unit not "
            "declared in available source. Length 8."
        ),
        examples=[5860, 1635],
    )
    bidrem: int = Field(
        default=0,
        title="매수잔량 (Best bid quantity)",
        description=(
            "Remaining bid (buy) quantity at the best bid price in shares. "
            "Length 12."
        ),
        examples=[19, 2924],
    )
    cnt: int = Field(
        default=0,
        title="연속일수 (Consecutive-day count)",
        description=(
            "Consecutive-day count reported by LS. Counting window and "
            "criteria (e.g., consecutive days hitting the ranked side) "
            "are not declared in available source — consume as returned "
            "by LS. Length 4."
        ),
        examples=[1, 5],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["203690", "007460"],
    )
    jkrate: str = Field(
        default="",
        title="증거금율 (Margin rate)",
        description=(
            "Margin rate string as reported by LS (e.g., '100' for 100%). "
            "Length 3."
        ),
        examples=["100", "50"],
    )
    jnilvolume: int = Field(
        default=0,
        title="전일거래량 (Previous-day volume)",
        description=(
            "Previous trading day's traded volume in shares. Length 12."
        ),
        examples=[390674, 6923364],
    )


class T1488Response(BaseModel):
    """t1488 response envelope."""

    header: Optional[T1488ResponseHeader]
    cont_block: Optional[T1488OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1488OutBlock1] = Field(
        default_factory=list,
        title="예상체결가등락율상위 리스트 (Ranked expected-conclusion rows)",
        description=(
            "List of ranked expected-conclusion percent-change rows. Row "
            "ordering not declared in available source."
        ),
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code returned for the request.",
    )
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지 (Error message)",
        description="Error message when the request failed; ``None`` on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
