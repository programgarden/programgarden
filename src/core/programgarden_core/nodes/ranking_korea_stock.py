"""
ProgramGarden Core - Korea Stock Ranking Node

국내주식 순위 조회:
- KoreaStockRankingNode: 등락률·거래량·거래대금·시가총액 상위 종목 (LS t1441 / t1452 / t1463 / t1444)
"""

from typing import Any, ClassVar, Dict, List, Literal, Optional, TYPE_CHECKING

from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    BrokerProvider,
    InputPort,
    KOREA_STOCK_RANKING_FIELDS,
    KOREA_STOCK_RANKING_SYMBOL_FIELDS,
    NodeCategory,
    OutputPort,
    ProductScope,
)


KOREA_RANKING_TYPES = ["change_rate_up", "change_rate_down", "volume", "trading_value", "market_cap"]
KOREA_RANKING_MARKETS = ["all", "KOSPI", "KOSDAQ"]
RANKING_LIMIT_MIN = 1
RANKING_LIMIT_MAX = 100

# The programgarden engine runs both ranking nodes with its own executor from this
# version. An older engine paired with this core falls back to its generic executor,
# which calls the node's ``execute``; without the method below it would report the
# node as executed with no rankings and no error.
RANKING_MIN_ENGINE = "2.6.6"


def ranking_engine_required(node_type: str) -> RuntimeError:
    """Error raised when an engine without the ranking executor runs a ranking node."""
    return RuntimeError(
        f"{node_type} requires the programgarden engine {RANKING_MIN_ENGINE} or later; "
        "this engine has no ranking executor, so no ranking was read. "
        "Update the programgarden package (updating programgarden-core alone is not enough)."
    )


_BROKER_CREDENTIAL = {
    "credential_id": "broker_cred",
    "type": "broker_ls_korea_stock",
    "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
    ],
}


class KoreaStockRankingNode(BaseNode):
    """
    국내주식 순위 노드

    KOSPI/KOSDAQ 의 등락률·거래량·거래대금·시가총액 상위 종목을 조회합니다.
    LS t1441(등락율상위) / t1452(거래량상위) / t1463(거래대금상위) / t1444(시가총액상위).
    읽기 전용 노드이며 주문을 내지 않습니다.
    """

    type: Literal["KoreaStockRankingNode"] = "KoreaStockRankingNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.KoreaStockRankingNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    ranking_type: str = Field(
        default="change_rate_up",
        description="Ranking: change_rate_up, change_rate_down, volume, trading_value, market_cap",
    )
    market: str = Field(
        default="all",
        description="Market: all, KOSPI, KOSDAQ (market_cap needs KOSPI or KOSDAQ)",
    )
    limit: int = Field(
        default=20,
        ge=RANKING_LIMIT_MIN,
        le=RANKING_LIMIT_MAX,
        description="Maximum number of ranked rows (1-100)",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Pick today's top domestic gainers, losers, most traded or largest stocks as a candidate list",
            "Start an intraday screen from the whole KOSPI/KOSDAQ market instead of a fixed watchlist",
        ],
        "when_not_to_use": [
            "For the full listed universe — use KoreaStockSymbolQueryNode",
            "For overseas stocks — use OverseasStockRankingNode",
            "For a fixed list of symbols — use WatchlistNode",
        ],
        "typical_scenarios": [
            "KoreaStockRankingNode(change_rate_up) → CodeNode (filter and pick) → KoreaStockMarketDataNode → order decision",
            "KoreaStockRankingNode(trading_value) → TableDisplayNode (market overview)",
            "KoreaStockRankingNode.symbols → SplitNode → KoreaStockHistoricalDataNode (per-symbol history)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "One node, four LS ranking TRs: change_rate_up/change_rate_down → t1441, volume → t1452, trading_value → t1463, market_cap → t1444",
        "Outputs `rankings` (full rows), `symbols` (KoreaStock symbol list) and `count`",
        "Change and change percent are signed from the LS sign code; units are named (trading_value_unit, market_cap_unit) and never converted",
        "Pages with the LS cursor up to `limit` rows, at most 5 requests per run, at the SDK rate limit of each TR",
        "Read-only and real-account only — KoreaStock has no paper trading; no order is ever placed",
        "Deep validation and dry runs return 3 synthetic rows with the same shape and make no broker call",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Wiring `symbols` or `rankings` straight into KoreaStockNewOrderNode",
            "reason": "A ranking is a moving market snapshot, not a trading decision. Top gainers often include limit-up, halted-adjacent or illiquid issues.",
            "alternative": "Filter in a CodeNode or ConditionNode (price, change range, holdings, open orders, budget) and order at most the chosen symbol.",
        },
        {
            "pattern": "Adding the five TRs together or comparing trading_value across ranking types",
            "reason": "Each TR reports in its own unit (as_returned, KRW_million, KRW_100million).",
            "alternative": "Read trading_value_unit / market_cap_unit before comparing values.",
        },
        {
            "pattern": "Using market_cap with market='all'",
            "reason": "t1444 ranks one market index at a time (001 KOSPI, 301 KOSDAQ).",
            "alternative": "Choose market='KOSPI' or market='KOSDAQ', or use two nodes.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Top 30 domestic gainers",
            "description": "List today's 30 biggest gainers across KOSPI and KOSDAQ.",
            "workflow_snippet": {
                "id": "korea_stock_ranking_gainers",
                "name": "Domestic Top Gainers",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "ranking", "type": "KoreaStockRankingNode", "ranking_type": "change_rate_up", "market": "all", "limit": 30},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.ranking.rankings }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "ranking"},
                    {"from": "ranking", "to": "display"},
                ],
                "credentials": [_BROKER_CREDENTIAL],
            },
            "expected_output": "rankings: [{rank, symbol, name, price, change_pct, volume, ...}] (30 rows); count: 30.",
        },
        {
            "title": "KOSPI market-cap leaders into a screen",
            "description": "Take the 20 largest KOSPI issues and pass the symbol list to a CodeNode for screening.",
            "workflow_snippet": {
                "id": "korea_stock_ranking_market_cap",
                "name": "KOSPI Market Cap Leaders",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "ranking", "type": "KoreaStockRankingNode", "ranking_type": "market_cap", "market": "KOSPI", "limit": 20},
                    {
                        "id": "screen",
                        "type": "CodeNode",
                        "data": "{{ nodes.ranking.rankings }}",
                        "code": (
                            "async def execute(data, params, context):\n"
                            "    rows = [r for r in (data or []) if (r.get('change_pct') or 0) > 0]\n"
                            "    return {'picked': rows[:5]}"
                        ),
                        "outputs": [{"name": "picked", "type": "array"}],
                    },
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "ranking"},
                    {"from": "ranking", "to": "screen"},
                ],
                "credentials": [_BROKER_CREDENTIAL],
            },
            "expected_output": "screen.picked: up to 5 KOSPI market-cap leaders that are up today.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "No symbol input. Choose ranking_type (change_rate_up, change_rate_down, volume, trading_value, market_cap), "
            "market (all, KOSPI, KOSDAQ; market_cap needs KOSPI or KOSDAQ) and limit (1-100). "
            "A connected KoreaStockBrokerNode supplies the real-account connection automatically."
        ),
        "output_consumption": (
            "`rankings` rows: rank, symbol (6 digits), exchange (KRX), market (KOSPI/KOSDAQ or null for all), name, price, "
            "open/high/low (t1441 only, else null), sign (raw code), change and change_pct (signed), volume, "
            "trading_value + trading_value_unit, market_cap + market_cap_unit, product (korea_stock), source_tr. "
            "`symbols` items: {exchange, market, symbol, name, product} — the KoreaStock symbol-list shape. "
            "`count`: number of rows. An empty successful result is valid (rankings=[], count=0). "
            "Deep validation and dry runs emit 3 synthetic rows (005930, 000660, 035420) with this exact shape and no broker call."
        ),
        "common_combinations": [
            "KoreaStockRankingNode.rankings → CodeNode (decision) → KoreaStockNewOrderNode",
            "KoreaStockRankingNode.symbols → SplitNode → KoreaStockMarketDataNode",
            "KoreaStockRankingNode.rankings → TableDisplayNode",
        ],
        "pitfalls": [
            "Rankings move every second; re-check price and holdings right before ordering",
            "Units differ by ranking type — read trading_value_unit / market_cap_unit",
            "LS failures raise with the TR code first (e.g. 't1441: <code> <message>'); missing credentials fail the node",
            "KoreaStock is real-account only",
        ],
    }

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="rankings", type="array", description="i18n:ports.rankings", fields=KOREA_STOCK_RANKING_FIELDS),
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=KOREA_STOCK_RANKING_SYMBOL_FIELDS),
        OutputPort(name="count", type="integer", description="i18n:ports.count"),
    ]

    _version: ClassVar[str] = "1.0.0"
    _updated_at: ClassVar[str] = "2026-10-15"
    _change_note: ClassVar[Optional[str]] = "New: domestic gainers/losers/volume/trading value/market cap rankings (LS)."

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import ExpressionMode, FieldCategory, FieldSchema, FieldType
        return {
            "ranking_type": FieldSchema(
                name="ranking_type",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockRankingNode.ranking_type",
                default="change_rate_up",
                enum_values=list(KOREA_RANKING_TYPES),
                enum_labels={value: f"i18n:enums.ranking_type.{value}" for value in KOREA_RANKING_TYPES},
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="change_rate_up",
                expected_type="str",
            ),
            "market": FieldSchema(
                name="market",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockRankingNode.market",
                default="all",
                enum_values=list(KOREA_RANKING_MARKETS),
                enum_labels={
                    "all": "i18n:enums.kr_market.all",
                    "KOSPI": "i18n:enums.kr_market.KOSPI",
                    "KOSDAQ": "i18n:enums.kr_market.KOSDAQ",
                },
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="all",
                expected_type="str",
            ),
            "limit": FieldSchema(
                name="limit",
                type=FieldType.INTEGER,
                description="i18n:fields.KoreaStockRankingNode.limit",
                default=20,
                min_value=RANKING_LIMIT_MIN,
                max_value=RANKING_LIMIT_MAX,
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=20,
                expected_type="int",
            ),
        }

    async def execute(self, context: Any) -> Dict[str, Any]:
        """Fail closed on an engine without the ranking executor.

        programgarden 2.6.6+ executes this node with its ranking
        executor and never calls this method (see ``RANKING_MIN_ENGINE``).
        """
        raise ranking_engine_required(self.type)
