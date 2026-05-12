"""Pydantic models for LS Securities OpenAPI t1410 (초저유동성조회 /
Stock ultra-low-liquidity query).

t1410 returns ultra-low-liquidity stock rows for a Korean market scope
(전체 / 코스피 / 코스닥) — Korean stock name, current price, previous-day
direction code (LS-mapped — partial-evidence only, see policy below),
magnitude of change, percent change, day-aggregate trading volume
(LS label "누적거래량"), and short code. Pagination uses the
``cts_shcode`` cursor echoed back in ``T1410OutBlock``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``gubun`` enum mapping IS declared by LS
      ('0' = all (전체), '1' = KOSPI (코스피), '2' = KOSDAQ (코스닥));
      description embeds the mapping verbatim.
    - ``sign`` enum mapping is **NOT formally declared** by LS in the
      t1410 field specification table, but the LS official example
      response shipped with the t1410 spec carries enough evidence to
      partially identify the mapping: the example row with
      ``change=0`` / ``diff="000.00"`` (no change) carries ``sign="3"``,
      and the example row with ``diff="-00.88"`` (down) carries
      ``sign="5"`` — both consistent with the 1=상한 / 2=상승 /
      3=보합 / 4=하한 / 5=하락 convention published by sibling TRs
      (t1308 / t1422 / t1427 / t1449). Values ``"1"`` / ``"2"`` /
      ``"4"`` have not been observed in the available t1410 example
      response and are not independently declared for t1410.
      Description reflects this partial evidence; consume any sign
      value as returned by LS without glyph translation.
    - Sign convention of ``change`` (signed magnitude — example
      response carries non-negative values only; full sign domain
      unverified), the time-window of ``volume`` (LS labels it
      "누적거래량" — the cumulative aspect is declared but the exact
      window (intraday vs multi-day) is not), row ordering of
      ``OutBlock1`` rows (the LS example response shows price
      descending mixed with volume ascending — no single sort key
      declared), the currency unit and decimal scale of price fields,
      and the structure of the ``cts_shcode`` cursor are NOT declared
      in the source available to this codebase; consume as returned
      by LS.
    - ``diff`` (LS scale 6.2) is serialized as a zero-padded string by
      LS in example responses (e.g., ``"-00.88"``, ``"000.00"``);
      Pydantic coerces to float.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1410RequestHeader(BlockRequestHeader):
    """t1410 request header. Inherits the standard LS request header schema."""
    pass


class T1410ResponseHeader(BlockResponseHeader):
    """t1410 response header. Inherits the standard LS response header schema."""
    pass


class T1410InBlock(BaseModel):
    """t1410InBlock — input block for the ultra-low-liquidity query."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market scope)",
        description=(
            "Market scope selector. Length 1. "
            "'0' = all (전체), "
            "'1' = KOSPI (코스피), "
            "'2' = KOSDAQ (코스닥). Required."
        ),
        examples=["0", "1", "2"],
    )
    cts_shcode: str = Field(
        default="",
        title="종목코드_CTS (Short code continuation cursor)",
        description=(
            "Continuation cursor — empty string on the first request "
            "(LS spec text says 'Space'). On subsequent requests, echo "
            "back ``T1410OutBlock.cts_shcode`` from the previous "
            "response. Treat as opaque LS-defined token. Length 6."
        ),
        examples=["", "000545", "168490"],
    )


class T1410Request(BaseModel):
    """t1410 request envelope."""

    header: T1410RequestHeader = T1410RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1410",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1410InBlock"], T1410InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1410"
    )


class T1410OutBlock(BaseModel):
    """t1410OutBlock — continuation block carrying the ``cts_shcode`` cursor."""

    cts_shcode: str = Field(
        default="",
        title="종목코드_CTS (Short code continuation cursor)",
        description=(
            "Continuation cursor for the next paged request. Pass back "
            "as ``T1410InBlock.cts_shcode``. Empty when no further rows "
            "are available. Treat as opaque LS-defined token. Length 6."
        ),
        examples=["", "000545", "168490"],
    )


class T1410OutBlock1(BaseModel):
    """t1410OutBlock1 — one ultra-low-liquidity stock row.

    Row ordering of rows is NOT declared in the source available to
    this codebase — the LS example response shows price descending
    mixed with volume ascending, with no single declared sort key;
    consume as returned by LS.
    """

    hname: str = Field(
        default="",
        title="한글명 (Korean stock name)",
        description=(
            "Korean stock name as returned by LS. Length 20."
        ),
        examples=["흥국화재우", "한국패러랠", "삼성전자"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description=(
            "Current price for the symbol as returned by LS. Decimal "
            "scale and currency unit not declared in available LS "
            "source. Length 8."
        ),
        examples=[0, 5620, 2175],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Previous-day direction code. Length 1. LS does not "
            "declare the enum mapping in the t1410 field specification "
            "table, but the LS official example response for t1410 "
            "carries sign='3' on a row with change=0 / diff='000.00' "
            "(unchanged) and sign='5' on a row with diff='-00.88' "
            "(down) — consistent with the 1=상한 (limit up) / "
            "2=상승 (up) / 3=보합 (unchanged) / 4=하한 (lower limit) / "
            "5=하락 (down) convention published by sibling TRs "
            "(t1308, t1422, t1427, t1449). Values '1', '2', '4' have "
            "not been observed in the available t1410 example response "
            "and are not independently declared for t1410. Consume as "
            "returned by LS without glyph translation."
        ),
        examples=["3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of change versus previous close. Sign convention "
            "is not declared in available LS source — the t1410 example "
            "response carries non-negative values only and the full "
            "sign domain is unverified. Consume as returned by LS. "
            "Length 8."
        ),
        examples=[0, 50, -25],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a zero-padded string in the "
            "t1410 example response (e.g., ``'-00.88'`` or "
            "``'000.00'``); Pydantic auto-coerces to float."
        ),
        examples=[0.0, -0.88, 1.20],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Day-aggregate trading volume)",
        description=(
            "Day-aggregate trading volume in shares as labeled by LS "
            "(``누적거래량``). The cumulative aspect is declared by "
            "LS, but the exact window scope (intraday cumulative vs "
            "multi-day cumulative) is not formally declared in "
            "available LS source. Length 12."
        ),
        examples=[22, 140, 1500000],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description=(
            "6-digit Korean stock short code. Length 6."
        ),
        examples=["000545", "168490", "005930"],
    )


class T1410Response(BaseModel):
    """t1410 response envelope."""

    header: Optional[T1410ResponseHeader]
    cont_block: Optional[T1410OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description=(
            "Continuation cursor block for paged follow-up requests."
        ),
    )
    block: List[T1410OutBlock1] = Field(
        default_factory=list,
        title="초저유동성 종목 리스트 (Ultra-low-liquidity stock rows)",
        description=(
            "List of ultra-low-liquidity stock rows. Row ordering is "
            "not declared in available LS source — the LS example "
            "response shows price descending mixed with volume "
            "ascending, with no single declared sort key. Consume as "
            "returned by LS."
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
