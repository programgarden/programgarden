"""ProgramGarden Core - Market Status Node

LS Securities JIF (Market Status) real-time TR wrapper. Exposes 12
supported markets (KOSPI, KOSDAQ, KRX_FUTURES, NXT, KRX_NIGHT, US,
CN_AM, CN_PM, HK_AM, HK_PM, JP_AM, JP_PM) as a credential-agnostic
market-open/close monitor. Overseas futures markets (CME, HKEx Futures,
SGX) are outside JIF scope and cannot be queried through this node.

Runtime subscription is handled by the programgarden executor — this
module defines the schema (field metadata, output ports, Literal
validation) plus helper constants shared between the core layer and the
executor.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Literal, Optional, Set, TYPE_CHECKING

from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    InputPort,
    NodeCategory,
    OutputPort,
    ProductScope,
)

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema


# ---------------------------------------------------------------------------
# Literal markets (12 JIF-supported)
# ---------------------------------------------------------------------------

MarketKey = Literal[
    "KOSPI",
    "KOSDAQ",
    "KRX_FUTURES",
    "NXT",
    "KRX_NIGHT",
    "US",
    "CN_AM",
    "CN_PM",
    "HK_AM",
    "HK_PM",
    "JP_AM",
    "JP_PM",
]


SUPPORTED_MARKETS: List[str] = [
    "KOSPI",
    "KOSDAQ",
    "KRX_FUTURES",
    "NXT",
    "KRX_NIGHT",
    "US",
    "CN_AM",
    "CN_PM",
    "HK_AM",
    "HK_PM",
    "JP_AM",
    "JP_PM",
]


# ---------------------------------------------------------------------------
# Core-layer mappings (symmetric with finance constants.py)
# ---------------------------------------------------------------------------

JANGUBUN_TO_MARKET: Dict[str, str] = {
    "1": "KOSPI",
    "2": "KOSDAQ",
    "5": "KRX_FUTURES",
    "6": "NXT",
    "8": "KRX_NIGHT",
    "9": "US",
    "A": "CN_AM",
    "B": "CN_PM",
    "C": "HK_AM",
    "D": "HK_PM",
    "E": "JP_AM",
    "F": "JP_PM",
}

MARKET_TO_JANGUBUN: Dict[str, str] = {v: k for k, v in JANGUBUN_TO_MARKET.items()}


# ``is_regular_open`` / ``is_extended_open`` derivation rules.
#
# These sets are the authoritative source for the node-layer convenience
# ``*_is_open`` ports. Keep in sync with the finance-layer
# ``JSTATUS_LABELS`` table in
# ``programgarden_finance.ls.common.real.JIF.constants`` — each status
# code's ``is_regular_open`` / ``is_extended_open`` flag over there
# mirrors these sets.

JSTATUS_REGULAR_OPEN: Set[str] = {
    "21",  # Market open
    "31",  # Market close imminent (still open)
    "42",  # Market closes in 10 minutes
    "43",  # Market closes in 5 minutes
    "44",  # Market closes in 1 minute
    "52",  # After-hours single-price session opened
    "64",  # Sidecar buy triggered (trading continues)
    "65",  # Sidecar sell triggered (trading continues)
    "66",  # Sidecar released
    "67",  # VI triggered (still tradeable)
    "68",  # VI released
    "70",  # Futures/options intraday extension
    "73",  # Futures circuit breaker released
    "74",  # Derivatives dynamic VI triggered
    "75",  # Derivatives dynamic VI released
    "76",  # Derivatives static VI triggered
    "77",  # Derivatives static VI released
}

JSTATUS_REGULAR_CLOSED: Set[str] = {
    "11",  # Pre-open auction started (not yet open)
    "22",  # Market open in 10 minutes
    "23",  # Market open in 5 minutes
    "24",  # Market open in 1 minute
    "25",  # Market open in 10 seconds
    "41",  # Market closed
    "51",  # After-hours session opened (closing price)
    "54",  # After-hours session closed (closing price)
    "55",  # Pre-market opened
    "56",  # After-market opened
    "57",  # Pre-market closed
    "58",  # After-market closed
    "61",  # Circuit breaker level 1
    "62",  # Circuit breaker level 2
    "63",  # Circuit breaker level 3
    "71",  # Trading halt
    "72",  # Futures circuit breaker triggered
}

JSTATUS_EXTENDED_OPEN: Set[str] = {
    "21", "31", "42", "43", "44",     # regular hours
    "51", "52", "55", "56",            # pre/after-market / single-price
    "64", "65", "66", "67", "68",
    "70", "73", "74", "75", "76", "77",
    "B2", "B3", "B4", "B5",            # pre-market closing countdown (still open)
    "D2", "D3", "D4", "D5",            # after-market closing countdown (still open)
}

JSTATUS_EXTENDED_CLOSED: Set[str] = {
    "11", "22", "23", "24", "25",
    "41", "54", "57", "58",
    "61", "62", "63", "71", "72",
    "A2", "A3", "A4", "A5",            # pre-market opening countdown (not yet open)
    "C2", "C3", "C4", "C5",            # after-market opening countdown (not yet open)
}


def is_regular_open(jstatus: str) -> bool:
    """Regular-hours trading session check for a raw JIF status code."""

    return jstatus in JSTATUS_REGULAR_OPEN


def is_extended_open(jstatus: str) -> bool:
    """Extended-hours trading session check (pre/after-market included)."""

    return jstatus in JSTATUS_EXTENDED_OPEN


def is_open(jstatus: str, include_extended: bool = False) -> bool:
    """Unified open-state check honouring the ``include_extended`` flag."""

    if include_extended:
        return is_extended_open(jstatus)
    return is_regular_open(jstatus)


# ---------------------------------------------------------------------------
# Node definition
# ---------------------------------------------------------------------------


class MarketStatusNode(BaseNode):
    """Real-time market-status monitor backed by LS Securities JIF TR.

    Subscribes to the broker-agnostic JIF WebSocket stream and exposes
    per-market open/close state. Register as an AI Agent Tool to answer
    natural-language queries such as "Is the US market open now?" or
    "Did KOSPI close today?".
    """

    type: Literal["MarketStatusNode"] = "MarketStatusNode"
    category: NodeCategory = NodeCategory.MARKET
    product_scope: ProductScope = ProductScope.ALL
    description: str = "i18n:nodes.MarketStatusNode.description"

    # `markets`: strict Literal list — unsupported values raise Pydantic
    # ValidationError (the plan explicitly forbids passing keys like
    # "CME" or "SGX" since JIF does not cover overseas futures).
    markets: List[MarketKey] = Field(
        default_factory=list,
        description=(
            "Subscribe filter. Empty list subscribes to all 12 JIF markets. "
            "Use a subset like ['US'] or ['KOSPI', 'KOSDAQ'] to narrow scope."
        ),
    )

    stay_connected: bool = Field(
        default=True,
        description=(
            "Keep the JIF subscription alive for the workflow lifetime. "
            "Set False for one-shot snapshot queries from AI Agent Tool calls."
        ),
    )

    include_extended_hours: bool = Field(
        default=False,
        description=(
            "When True, pre-market / after-market / single-price sessions "
            "count as open for the convenience *_is_open ports."
        ),
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]

    _outputs: List[OutputPort] = [
        OutputPort(
            name="statuses",
            type="array",
            description="i18n:outputs.MarketStatusNode.statuses",
            example=[
                {
                    "market": "US",
                    "jangubun": "9",
                    "jstatus": "21",
                    "jstatus_label": "Market open",
                    "is_open": True,
                    "is_regular_open": True,
                    "is_extended_open": True,
                    "updated_at": "2026-04-18T22:30:00",
                }
            ],
        ),
        OutputPort(
            name="event",
            type="object",
            description="i18n:outputs.MarketStatusNode.event",
            example={
                "market": "US",
                "jstatus": "21",
                "jstatus_label": "Market open",
                "prev_jstatus": "11",
                "prev_jstatus_label": "Pre-open auction started",
                "transitioned_at": "2026-04-18T22:30:00",
            },
        ),
        OutputPort(
            name="us_is_open",
            type="boolean",
            description="i18n:outputs.MarketStatusNode.us_is_open",
            example=True,
        ),
        OutputPort(
            name="kospi_is_open",
            type="boolean",
            description="i18n:outputs.MarketStatusNode.kospi_is_open",
            example=False,
        ),
        OutputPort(
            name="kosdaq_is_open",
            type="boolean",
            description="i18n:outputs.MarketStatusNode.kosdaq_is_open",
            example=False,
        ),
        OutputPort(
            name="krx_futures_is_open",
            type="boolean",
            description="i18n:outputs.MarketStatusNode.krx_futures_is_open",
            example=False,
        ),
        OutputPort(
            name="hk_is_open",
            type="boolean",
            description="i18n:outputs.MarketStatusNode.hk_is_open",
            example=False,
        ),
        OutputPort(
            name="cn_is_open",
            type="boolean",
            description="i18n:outputs.MarketStatusNode.cn_is_open",
            example=False,
        ),
        OutputPort(
            name="jp_is_open",
            type="boolean",
            description="i18n:outputs.MarketStatusNode.jp_is_open",
            example=False,
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            ExpressionMode,
            FieldCategory,
            FieldSchema,
            FieldType,
        )

        return {
            "markets": FieldSchema(
                name="markets",
                type=FieldType.ARRAY,
                array_item_type=FieldType.STRING,
                description="i18n:fields.MarketStatusNode.markets",
                default=[],
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_options={
                    "multiple": True,
                    "options": list(SUPPORTED_MARKETS),
                },
                help_text="i18n:fields.MarketStatusNode.markets.help_text",
                example=[["US"], ["KOSPI", "KOSDAQ"], []],
                expected_type="list[str]",
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.MarketStatusNode.stay_connected",
                default=True,
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                help_text="i18n:fields.MarketStatusNode.stay_connected.help_text",
                example=True,
                expected_type="bool",
            ),
            "include_extended_hours": FieldSchema(
                name="include_extended_hours",
                type=FieldType.BOOLEAN,
                description="i18n:fields.MarketStatusNode.include_extended_hours",
                default=False,
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                help_text="i18n:fields.MarketStatusNode.include_extended_hours.help_text",
                example=False,
                expected_type="bool",
            ),
        }

    async def execute(self, context: Any) -> Dict[str, Any]:
        """Fallback execution — the programgarden executor injects a
        runtime-aware implementation that subscribes to the JIF stream.

        Standalone execution (without the main executor) returns an empty
        snapshot so downstream nodes can still traverse the DAG without
        crashing.
        """

        empty_snapshot: Dict[str, Any] = {
            "statuses": [],
            "event": None,
            "us_is_open": False,
            "kospi_is_open": False,
            "kosdaq_is_open": False,
            "krx_futures_is_open": False,
            "hk_is_open": False,
            "cn_is_open": False,
            "jp_is_open": False,
        }
        return empty_snapshot


__all__ = [
    "MarketStatusNode",
    "MarketKey",
    "SUPPORTED_MARKETS",
    "JANGUBUN_TO_MARKET",
    "MARKET_TO_JANGUBUN",
    "JSTATUS_REGULAR_OPEN",
    "JSTATUS_REGULAR_CLOSED",
    "JSTATUS_EXTENDED_OPEN",
    "JSTATUS_EXTENDED_CLOSED",
    "is_regular_open",
    "is_extended_open",
    "is_open",
]
