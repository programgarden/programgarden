"""NS3 NXT trade ticks from the owner-supplied LS contract and observed wire.

All values in the supplied example and ten directly observed ticks were strings.
Preserve clocks and leading zeros. Missing values remain None, never a measured
zero. Source-required metadata is not a promise of future wire availability.
Do not copy S3_ sign/status enums, traded-value units or strength formulas: the
supplied NS3 contract does not state them. See docs/ns3_contract.md.
"""
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class NS3RealRequestHeader(BlockRealRequestHeader):
    """Standard LS subscription header; token is supplied at runtime."""


class NS3RealResponseHeader(BlockRealResponseHeader):
    """NS3 subscription acknowledgement or trade header."""


class NS3RealRequestBody(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    tr_cd: Literal["NS3"] = "NS3"
    tr_key: str = Field(
        ..., pattern=r"^N[0-9]{6} {3}$",
        description="N plus six symbol digits and three trailing spaces.",
        examples=["N010950   "],
    )

    @field_validator("tr_key", mode="before")
    @classmethod
    def pad_prefixed_symbol(cls, value: Any) -> Any:
        if isinstance(value, str) and len(value) == 7:
            return value + "   "
        return value


class NS3RealRequest(BaseModel):
    header: NS3RealRequestHeader = Field(default_factory=lambda: NS3RealRequestHeader(token="", tr_type="3"))
    body: NS3RealRequestBody


def _wire_field(label: str, source_type: str, length: str):
    return Field(
        default=None, title=label,
        description=label + ". Absent wire values remain unavailable.",
        json_schema_extra={
            "ls_source_type": source_type, "ls_source_length": length,
            "ls_source_required": source_type != "example",
        },
    )


class NS3RealResponseBody(BaseModel):
    """Raw tick values; retain unknown additions and inspect field presence."""
    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True)
    chetime: Optional[str] = _wire_field('Trade time', 'String', '6')
    sign: Optional[str] = _wire_field('Previous-day change flag', 'String', '1')
    change: Optional[str] = _wire_field('Previous-day price change', 'Number', '8')
    drate: Optional[str] = _wire_field('Change rate', 'Number', '6.2')
    price: Optional[str] = _wire_field('Current price', 'Number', '8')
    opentime: Optional[str] = _wire_field('Opening time', 'String', '6')
    open: Optional[str] = _wire_field('Opening price', 'Number', '8')
    hightime: Optional[str] = _wire_field('High time', 'Number', '8')
    high: Optional[str] = _wire_field('High price (source example and observed wire; absent from field table)', 'example', 'unknown')
    lowtime: Optional[str] = _wire_field('Low time', 'String', '6')
    low: Optional[str] = _wire_field('Low price', 'Number', '8')
    cgubun: Optional[str] = _wire_field('Trade side flag', 'String', '1')
    cvolume: Optional[str] = _wire_field('Trade volume', 'Number', '8')
    volume: Optional[str] = _wire_field('Cumulative volume', 'Number', '12')
    value: Optional[str] = _wire_field('Cumulative traded value; source does not declare a unit', 'Number', '12')
    mdvolume: Optional[str] = _wire_field('Cumulative sell volume', 'Number', '12')
    mdchecnt: Optional[str] = _wire_field('Sell trade count', 'Number', '8')
    msvolume: Optional[str] = _wire_field('Cumulative buy volume', 'Number', '12')
    mschecnt: Optional[str] = _wire_field('Buy trade count', 'Number', '8')
    cpower: Optional[str] = _wire_field('Trade strength; source does not declare its formula', 'Number', '9.2')
    w_avrg: Optional[str] = _wire_field('Weighted average price', 'Number', '8')
    offerho: Optional[str] = _wire_field('Ask price', 'Number', '8')
    bidho: Optional[str] = _wire_field('Bid price', 'Number', '8')
    status: Optional[str] = _wire_field('Market status; preserve raw code, do not infer an enum', 'String', '2')
    jnilvolume: Optional[str] = _wire_field('Previous-day volume at the same time', 'Number', '12')
    shcode: Optional[str] = _wire_field('Short symbol', 'String', '9')
    exchname: Optional[str] = _wire_field('Quote venue; not the venue of an account execution', 'String', '3')
    ex_shcode: Optional[str] = _wire_field('Venue-prefixed symbol', 'String', '10')


class NS3RealResponse(BaseModel):
    header: Optional[NS3RealResponseHeader] = None
    body: Optional[NS3RealResponseBody] = None
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = None
    _raw_data: Any = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Any:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, value: Any) -> None:
        self._raw_data = value
