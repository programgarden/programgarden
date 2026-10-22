"""Pydantic models for LS Securities OpenAPI t1427 (상/하한가직전 / Issues approaching daily upper- or lower-limit).

t1427 returns Korean stock issues whose latest quote is approaching the
daily price limit (상한 / 하한). Filters include market division
(KOSPI / KOSDAQ), direction (approaching upper / approaching lower),
percent-change threshold (``diff``), a target-exclusion bitmask
(``jc_num``), price and volume bounds, and an opaque pagination cursor
(``idx``). Pagination uses the ``idx`` value echoed back in
``t1427OutBlock``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``signgubun`` (input direction filter) enum mapping IS declared
      by LS for t1427 (1=상한직전 / 2=하한직전).
    - ``gubun`` (input market division) enum mapping IS declared by LS
      for t1427 (0=전체 / 1=코스피 / 2=코스닥).
    - ``jc_num`` (target-exclusion bitmask) — bit values listed in the
      LS source are mirrored verbatim; LS publishes the bit layout for
      this TR (e.g., ``0x00000080`` = 관리종목).
    - ``jshex`` (전일상하한제외) — LS source declares 'c' or 'C' as the
      activation token; other values do not activate the filter.
    - ``sign`` (output direction code) enum mapping IS declared by LS
      for t1427's ``OutBlock1.sign``
      (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락); the description
      embeds the mapping.
    - Sign convention of ``change``, currency unit of ``price`` /
      ``lmtprice`` / ``open`` / ``high`` / ``low``, decimal scale of
      ``price``, row ordering within ``OutBlock1``, and the precise
      meaning of ``lmtdaycnt`` (연속) counting window and ``rate``
      (대비율) reference base are NOT declared in available source —
      consume as returned by LS.
    - ``diff`` (LS scale 6.2), ``diff_vol`` (LS scale 10.2), and
      ``rate`` (LS scale 12.2) are serialized as JSON strings by LS in
      the example response (e.g., ``"026.34"``, ``"0001456.56"``,
      ``"-00000002.80"``); Pydantic coerces to float.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
      LS spec lists ``idx`` as Number length 4 in the response.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1427RequestHeader(BlockRequestHeader):
    """t1427 request header. Inherits the standard LS request header schema."""
    pass


class T1427ResponseHeader(BlockResponseHeader):
    """t1427 response header. Inherits the standard LS response header schema."""
    pass


class T1427InBlock(BaseModel):
    """t1427InBlock — input block for the approaching-limit screen."""

    qrygb: str = Field(
        ...,
        title="조회구분 (Query mode)",
        description=(
            "Query mode. Length 1. "
            "'1' = paged 20-row mode (20종목씩 조회), "
            "any other value = full-list mode (전체조회)."
        ),
        examples=["1", "0"],
    )
    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description=(
            "Market division. Length 1. "
            "'0' = all (전체), "
            "'1' = KOSPI (코스피), "
            "'2' = KOSDAQ (코스닥)."
        ),
        examples=["0", "1", "2"],
    )
    signgubun: Literal["1", "2"] = Field(
        ...,
        title="상하한가구분 (Approaching-limit direction)",
        description=(
            "Approaching-limit direction. Length 1. "
            "'1' = approaching upper limit (상한직전), "
            "'2' = approaching lower limit (하한직전)."
        ),
        examples=["1", "2"],
    )
    diff: int = Field(
        default=0,
        title="등락율 (Percent-change threshold)",
        description=(
            "Percent-change threshold. Length 3. "
            "When ``signgubun`` is '1' (approaching upper), rows satisfy "
            "percent change >= ``diff``. "
            "When ``signgubun`` is '2' (approaching lower), rows satisfy "
            "percent change <= ``-diff``. "
            "Pass a non-negative integer; 0 means no threshold filter."
        ),
        examples=[0, 5, 10],
    )
    jc_num: int = Field(
        default=0,
        title="대상제외 (Target-exclusion bitmask)",
        description=(
            "Target-exclusion bitmask. Length 12. Combine LS-declared bits "
            "with bitwise OR and pass the integer value (the LS setting is "
            "persisted server-side). LS-declared bits: "
            "0x00000080 (128) 관리종목, "
            "0x00000100 (256) 시장경보, "
            "0x00000200 (512) 거래정지, "
            "0x00004000 (16384) 우선주, "
            "0x00200000 (2097152) 증거금50/100, "
            "0x00400000 (4194304) 증거금50, "
            "0x00800000 (8388608) 증거금100, "
            "0x01000000 (16777216) 정리매매, "
            "0x04000000 (67108864) 투자유의, "
            "0x80000000 (2147483648) 불성실공시. "
            "Example: exclude 관리종목 + 시장경보 → 384 (= 128 + 256). "
            "0 means no exclusion."
        ),
        examples=[0, 128, 384],
    )
    sprice: int = Field(
        default=0,
        title="시작가격 (Current-price lower bound)",
        description=(
            "Inclusive lower bound for current price. Rows satisfy "
            "``현재가 >= sprice``. 0 means no lower bound. Decimal scale "
            "and currency unit not declared in available source. Length 8."
        ),
        examples=[0, 1000],
    )
    eprice: int = Field(
        default=0,
        title="종료가격 (Current-price upper bound)",
        description=(
            "Inclusive upper bound for current price. Rows satisfy "
            "``현재가 <= eprice``. 0 means no upper bound. Length 8."
        ),
        examples=[0, 100000],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Cumulative volume threshold)",
        description=(
            "Inclusive lower bound for cumulative traded volume in shares. "
            "Rows satisfy ``거래량 >= volume``. 0 means no minimum. "
            "Length 12."
        ),
        examples=[0, 10000, 1000000],
    )
    idx: int = Field(
        default=0,
        title="IDX (Pagination cursor)",
        description=(
            "Pagination cursor (LS spec: Space on first request, then echo "
            "back ``T1427OutBlock.idx`` from the previous response). "
            "Treat as opaque LS-defined token; this client serializes 0 "
            "on the first request, which LS accepts per the official "
            "example. Length 4."
        ),
        examples=[0, 20],
    )
    jshex: str = Field(
        default="",
        title="전일상하한제외 (Exclude previous-day limit hits)",
        description=(
            "Exclude rows that hit the daily upper/lower limit on the "
            "previous trading day. Length 1. "
            "Pass 'c' or 'C' to activate the filter; any other value (e.g., "
            "empty string) leaves the filter inactive."
        ),
        examples=["c", "C", ""],
    )


class T1427Request(BaseModel):
    """t1427 request envelope."""

    header: T1427RequestHeader = T1427RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1427",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1427InBlock"], T1427InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1427"
    )


class T1427OutBlock(BaseModel):
    """t1427OutBlock — continuation block carrying the result count and ``idx`` paging cursor."""

    cnt: int = Field(
        default=0,
        title="CNT (Total result count)",
        description=(
            "Total result count returned for the query as reported by LS. "
            "Length 4."
        ),
        examples=[0, 2447],
    )
    idx: int = Field(
        ...,
        title="IDX (Pagination cursor)",
        description=(
            "Pagination cursor for the next paged request. Pass back as "
            "``T1427InBlock.idx``. Treat as opaque LS-defined token. "
            "Length 4."
        ),
        examples=[0, 20],
    )


class T1427OutBlock1(BaseModel):
    """t1427OutBlock1 — one approaching-limit row.

    Row ordering within the list is NOT declared in the source available to
    this codebase; consume as returned by LS.
    """

    hname: str = Field(
        default="",
        title="한글명 (Korean name)",
        description="Korean issue name as reported by LS. Length 20.",
        examples=["솔트웨어", "삼성스팩4호"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description=(
            "Current price as reported by LS. Decimal scale and currency "
            "unit not declared in available source. Length 8."
        ),
        examples=[1530, 4330, 0],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus previous close. Length 1. "
            "'1' = upper limit (상한), "
            "'2' = up (상승), "
            "'3' = unchanged (보합), "
            "'4' = lower limit (하한), "
            "'5' = down (하락). Enum mapping is declared by LS for t1427."
        ),
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of price change versus previous close. Sign "
            "convention is not declared in available LS source — consume "
            "as returned by LS. Length 8."
        ),
        examples=[319, 295, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '026.34' or "
            "'007.31'); Pydantic auto-coerces to float."
        ),
        examples=[26.34, 7.31, 0.0],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description=(
            "Cumulative traded volume in shares for the session. Length 12."
        ),
        examples=[30556301, 202798, 0],
    )
    diff_vol: float = Field(
        default=0.0,
        title="거래증가율 (Volume growth rate)",
        description=(
            "Volume growth rate versus previous trading day in % (LS scale "
            "10.2). Reference base (e.g., ``volume / jnilvolume`` or "
            "another formula) is not declared in available source — consume "
            "as returned by LS. LS may serialize this value as a string "
            "(e.g., '0001456.56'); Pydantic auto-coerces to float."
        ),
        examples=[1456.56, 101.36, 0.0],
    )
    lmtprice: int = Field(
        default=0,
        title="상한가/하한가 (Daily limit price)",
        description=(
            "Daily upper- or lower-limit price corresponding to the "
            "``signgubun`` filter (upper limit when ``signgubun=1``, lower "
            "limit when ``signgubun=2``). Decimal scale and currency unit "
            "not declared in available source. Length 8."
        ),
        examples=[1574, 5240, 0],
    )
    rate: float = Field(
        default=0.0,
        title="대비율 (Comparison rate)",
        description=(
            "Comparison rate as reported by LS in the ``rate`` field "
            "(LS label '대비율', scale 12.2). Reference base is not "
            "declared in available source — consume as returned by LS. "
            "LS may serialize this value as a string (e.g., "
            "'-00000002.80' or '-00000017.37'); Pydantic auto-coerces to "
            "float."
        ),
        examples=[-2.80, -17.37, 0.0],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["328380", "377630"],
    )
    jnilvolume: int = Field(
        default=0,
        title="전일거래량 (Previous-day volume)",
        description=(
            "Previous trading day's traded volume in shares. Length 12."
        ),
        examples=[1963072, 100713, 0],
    )
    open: int = Field(
        default=0,
        title="시가 (Open price)",
        description=(
            "Session open price as reported by LS. Decimal scale and "
            "currency unit not declared in available source. Length 8."
        ),
        examples=[1251, 4100, 0],
    )
    high: int = Field(
        default=0,
        title="고가 (High price)",
        description=(
            "Session high price as reported by LS. Decimal scale and "
            "currency unit not declared in available source. Length 8."
        ),
        examples=[1572, 4330, 0],
    )
    low: int = Field(
        default=0,
        title="저가 (Low price)",
        description=(
            "Session low price as reported by LS. Decimal scale and "
            "currency unit not declared in available source. Length 8."
        ),
        examples=[1251, 4030, 0],
    )
    lmtdaycnt: int = Field(
        default=0,
        title="연속 (Consecutive-day count)",
        description=(
            "Consecutive-day count reported by LS in the ``lmtdaycnt`` "
            "field (LS label '연속'). Counting window and criteria (e.g., "
            "consecutive days approaching the limit on the same side) are "
            "not declared in available source — consume as returned by LS. "
            "Length 8."
        ),
        examples=[0, 1, 5],
    )
    value: int = Field(
        default=0,
        title="거래대금 (Trading value)",
        description=(
            "Cumulative traded value as reported by LS. Currency unit and "
            "scaling (e.g., raw value vs. million-unit) are not declared "
            "in available source — consume as returned by LS. Length 12."
        ),
        examples=[44062, 855, 0],
    )
    total: int = Field(
        default=0,
        title="시가총액 (Market capitalization)",
        description=(
            "Market capitalization as reported by LS. Currency unit and "
            "scaling (e.g., raw value vs. 억-won unit) are not declared in "
            "available source — consume as returned by LS. Length 12."
        ),
        examples=[524, 174, 0],
    )


class T1427Response(BaseModel):
    """t1427 response envelope."""

    header: Optional[T1427ResponseHeader]
    cont_block: Optional[T1427OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description=(
            "Continuation cursor block for paged follow-up requests "
            "(carries total result count and the ``idx`` cursor)."
        ),
    )
    block: List[T1427OutBlock1] = Field(
        default_factory=list,
        title="상하한가직전 리스트 (Approaching-limit rows)",
        description=(
            "List of approaching-limit rows. Row ordering not declared in "
            "available LS source — consume as returned by LS."
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
