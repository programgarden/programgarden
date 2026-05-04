"""Pydantic models for LS Securities OpenAPI t1640 (Korean Stock Program Trading Comprehensive Query — Mini).

t1640 returns a single snapshot of program-trading aggregates for one
combination of market (거래소 vs 코스닥) and arbitrage breakdown
(전체 / 차익 / 비차익) selected by ``gubun``:
    - Buy / sell / net-buy quantity and amount.
    - Day-over-day changes (``*diff`` / ``*valdiff``) for each axis.
    - Basis (KP200 future vs spot) ratio.

Unlike t1631 (which returns a summary block + program-trading row array)
or t1636 / t1637 (per-symbol queries), t1640 returns exactly one
``t1640OutBlock`` object — there is **no continuation paging** and no
list block.

Field descriptions follow LS official spec wording verbatim. Korean
field labels (한글명) are appended in parentheses so AI chatbots can map
between English descriptions and Korean LS documentation. Inferred
formulas, units, baselines for ``*diff`` / ``*valdiff``, or the meaning
of ``volume`` / ``value`` beyond LS-published wording are intentionally
omitted — consume every value as reported by LS.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1640RequestHeader(BlockRequestHeader):
    """t1640 request header. Inherits the standard LS request header schema."""
    pass


class T1640ResponseHeader(BlockResponseHeader):
    """t1640 response header. No continuation flags — t1640 returns a single snapshot."""
    pass


class T1640InBlock(BaseModel):
    """t1640InBlock — input block for Korean stock program-trading mini snapshot.

    Selects the combined market + arbitrage breakdown via ``gubun`` and
    the exchange filter via ``exchgubun``. No date / time / cursor inputs
    — t1640 always returns the most-recent snapshot.

    WARNING: ``gubun`` encoding is COMPLETELY DIFFERENT from every
    sibling program TR. t1640 uses 2-digit codes that combine the
    market dimension and the arbitrage dimension into a single field
    ('11'/'12'/'13' for 거래소 total/arbitrage/non-arbitrage,
    '21'/'22'/'23' for KOSDAQ total/arbitrage/non-arbitrage). Do NOT
    copy-paste ``gubun`` from t1631 ('1'/'2'), t1632 / t1633 / t1636 /
    t1637 ('0'/'1') — they will be rejected as invalid by the Literal.
    """

    gubun: Literal["11", "12", "13", "21", "22", "23"] = Field(
        ...,
        title="구분 (Market + arbitrage division)",
        description=(
            "Combined market and arbitrage division. "
            "'11' = Exchange total (거래소전체), "
            "'12' = Exchange arbitrage (거래소차익), "
            "'13' = Exchange non-arbitrage (거래소비차익), "
            "'21' = KOSDAQ total (코스닥전체), "
            "'22' = KOSDAQ arbitrage (코스닥차익), "
            "'23' = KOSDAQ non-arbitrage (코스닥비차익). Required. Length 2. "
            "WARNING: this 2-digit encoding is unique to t1640 — sibling "
            "TRs (t1631 '1'/'2', t1632 / t1633 / t1636 / t1637 '0'/'1') "
            "use different ``gubun`` domains."
        ),
        examples=["11", "12", "21"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = unified KRX+NXT. "
            "Per LS spec, any other value is treated as KRX server-side. Length 1."
        ),
        examples=["K", "N", "U"],
    )


class T1640Request(BaseModel):
    """t1640 full request envelope (header + body + setup options)."""

    header: T1640RequestHeader = T1640RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1640",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t1640InBlock"], T1640InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1640",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T1640OutBlock(BaseModel):
    """t1640OutBlock — single program-trading snapshot.

    Returns one row of buy / sell / net-buy quantity, amount, and their
    day-over-day changes for the selected market + arbitrage combination
    (``T1640InBlock.gubun``), plus the basis (KP200 future vs spot) ratio.

    NOTE: ``sundiff`` (Length 8) and ``sunvaldiff`` (Length 12) share the
    same LS Korean label (순매수증감) per the LS public spec. They are
    distinct fields with distinct lengths — consume both as reported.
    The relationship between them is not published by LS; do not derive
    one from the other.

    LS may serialize numeric fields as zero-padded strings (e.g.,
    ``"000000786684"`` for 786684.0, ``"-00000000100"`` for -100.0,
    ``"000.01"`` for 0.01). Pydantic auto-coerces these per the field
    type (int for long-typed fields, float for double / float-typed fields).

    xingAPI FUNCTION_MAP type/length mapping (ground truth):
        - long, 8  → int  : offervolume, bidvolume, volume, offerdiff, biddiff, sundiff
        - float, 6.2 → float : basis
        - double, 12.0 → float : offervalue, bidvalue, value, offervaldiff, bidvaldiff, sunvaldiff

    NOTE on sibling-TR divergence: t1631 / t1636 declare the same
    Korean labels (매도금액 / 매수금액 / 순매수금액) as ``long`` (int);
    t1640 declares them as ``double`` (float). Do not copy-paste type
    annotations from t1631 / t1636 ``*value`` fields — they will silently
    mismatch the LS spec for t1640.
    """

    offervolume: int = Field(
        default=0,
        title="매도수량 (Sell quantity)",
        description=(
            "Sell quantity for the selected market + arbitrage combination. "
            "Length 8. Unit conventions are not documented in the LS public spec. "
            "LS may serialize this value as a string; Pydantic auto-coerces to int."
        ),
        examples=[36452, 0],
    )
    bidvolume: int = Field(
        default=0,
        title="매수수량 (Buy quantity)",
        description=(
            "Buy quantity for the selected market + arbitrage combination. "
            "Length 8. Unit conventions are not documented in the LS public spec. "
            "LS may serialize this value as a string; Pydantic auto-coerces to int."
        ),
        examples=[39833, 0],
    )
    volume: int = Field(
        default=0,
        title="순매수수량 (Net-buy quantity)",
        description=(
            "Net-buy quantity for the selected market + arbitrage combination. "
            "Length 8. Server-computed by LS — formula not published in the LS "
            "public spec; consume as returned. "
            "LS may serialize this value as a string; Pydantic auto-coerces to int."
        ),
        examples=[3381, 0],
    )
    offerdiff: int = Field(
        default=0,
        title="매도증감 (Sell change)",
        description=(
            "Sell-quantity change versus the previous day, in the same units as "
            "``offervolume``. Length 8. The exact LS server-side baseline beyond "
            "the published label '증감' (change) is not documented in the public "
            "spec. LS may serialize this value as a string; Pydantic auto-coerces "
            "to int."
        ),
        examples=[10, -5, 0],
    )
    biddiff: int = Field(
        default=0,
        title="매수증감 (Buy change)",
        description=(
            "Buy-quantity change versus the previous day, in the same units as "
            "``bidvolume``. Length 8. Baseline beyond LS '증감' wording not "
            "documented. LS may serialize this value as a string; Pydantic "
            "auto-coerces to int."
        ),
        examples=[16, -3, 0],
    )
    sundiff: int = Field(
        default=0,
        title="순매수증감 (Net-buy change)",
        description=(
            "Net-buy-quantity change versus the previous day, in the same units "
            "as ``volume``. Length 8. Baseline beyond LS '증감' wording not "
            "documented. Distinct from ``sunvaldiff`` (Length 12, monetary axis) "
            "— LS shares the Korean label between the two but they are separate "
            "fields. LS may serialize this value as a string; Pydantic auto-coerces "
            "to int."
        ),
        examples=[6, -2, 0],
    )
    basis: float = Field(
        default=0.0,
        title="베이시스 (Basis)",
        description=(
            "Basis between the KP200 future and its spot index (LS scale 6.2). "
            "Unit conventions beyond the LS scale are not published in the public "
            "spec. LS may serialize this value as a string (e.g., '000.01' for 0.01); "
            "Pydantic auto-coerces to float."
        ),
        examples=[0.01, -1.20, 0.0],
    )
    offervalue: float = Field(
        default=0.0,
        title="매도금액 (Sell amount)",
        description=(
            "Sell amount for the selected market + arbitrage combination. "
            "Length 12.0 (LS xingAPI type: double). Unit conventions are not "
            "documented in the LS public spec. LS may serialize this value as "
            "a string (e.g., '000000758788' for 758788.0); Pydantic auto-coerces "
            "to float. NOTE: t1631 / t1636 sibling TRs declare the same Korean "
            "label '매도금액' as long (int) — t1640 differs (double / float)."
        ),
        examples=[758788.0, 0.0],
    )
    bidvalue: float = Field(
        default=0.0,
        title="매수금액 (Buy amount)",
        description=(
            "Buy amount for the selected market + arbitrage combination. "
            "Length 12.0 (LS xingAPI type: double). Unit conventions are not "
            "documented in the LS public spec. LS may serialize this value as "
            "a string (e.g., '000000786684' for 786684.0); Pydantic auto-coerces "
            "to float."
        ),
        examples=[786684.0, 0.0],
    )
    value: float = Field(
        default=0.0,
        title="순매수금액 (Net-buy amount)",
        description=(
            "Net-buy amount for the selected market + arbitrage combination. "
            "Length 12.0 (LS xingAPI type: double). Server-computed by LS — "
            "formula not published in the LS public spec; consume as returned. "
            "LS may serialize this value as a string (e.g., '000000027896' for "
            "27896.0); Pydantic auto-coerces to float."
        ),
        examples=[27896.0, 0.0],
    )
    offervaldiff: float = Field(
        default=0.0,
        title="매도금액증감 (Sell amount change)",
        description=(
            "Sell-amount change versus the previous day, in the same units as "
            "``offervalue``. Length 12.0 (LS xingAPI type: double). Baseline "
            "beyond LS '증감' wording not documented. LS may serialize this "
            "value as a string (e.g., '000000000350' for 350.0); Pydantic "
            "auto-coerces to float."
        ),
        examples=[350.0, -100.0, 0.0],
    )
    bidvaldiff: float = Field(
        default=0.0,
        title="매수금액증감 (Buy amount change)",
        description=(
            "Buy-amount change versus the previous day, in the same units as "
            "``bidvalue``. Length 12.0 (LS xingAPI type: double). Baseline "
            "beyond LS '증감' wording not documented. LS may serialize this "
            "value as a string (e.g., '000000000250' for 250.0); Pydantic "
            "auto-coerces to float."
        ),
        examples=[250.0, -50.0, 0.0],
    )
    sunvaldiff: float = Field(
        default=0.0,
        title="순매수증감 (Net-buy change)",
        description=(
            "Net-buy amount change versus the previous day, in the same units "
            "as ``value``. Length 12.0 (LS xingAPI type: double). The LS public "
            "spec labels this field with the Korean string '순매수증감' — "
            "identical to the label used for ``sundiff`` (Length 8, long / int). "
            "Treat the two as distinct fields per LS spec; baseline beyond "
            "'증감' wording not documented. LS may serialize this value as a "
            "string (e.g., '-00000000100' for -100.0); Pydantic auto-coerces "
            "to float."
        ),
        examples=[-100.0, 250.0, 0.0],
    )


class T1640Response(BaseModel):
    """t1640 full API response envelope."""

    header: Optional[T1640ResponseHeader] = None
    block: Optional[T1640OutBlock] = Field(
        default=None,
        title="t1640OutBlock (Single program-trading snapshot)",
        description=(
            "Single snapshot for the selected market + arbitrage combination. "
            "No continuation, no array — exactly one object or absent."
        ),
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
