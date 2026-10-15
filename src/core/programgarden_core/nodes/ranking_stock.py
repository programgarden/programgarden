"""
ProgramGarden Core - Overseas Stock Ranking Node

해외주식 순위 조회:
- OverseasStockRankingNode: 미국 주식 등락률·거래량·거래대금·회전율·시가총액·52주 신고가/신저가 순위 (LS g3112)
"""

from typing import Any, ClassVar, Dict, List, Literal, Optional, TYPE_CHECKING

from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    BrokerProvider,
    InputPort,
    NodeCategory,
    OVERSEAS_STOCK_RANKING_FIELDS,
    OVERSEAS_STOCK_RANKING_SYMBOL_FIELDS,
    OutputPort,
    ProductScope,
)
from programgarden_core.nodes.ranking_korea_stock import RANKING_LIMIT_MAX, RANKING_LIMIT_MIN, ranking_engine_required


# Node enum → g3112 rankgubun (LS guide: 0 상승률, 1 하락률, 2 거래량, 3 거래대금, 4 회전율,
# 5 시가총액, 6 52주신고가, 7 52주신저가). '8' 상한가 / '9' 하한가 are intentionally not exposed.
OVERSEAS_RANKING_TYPES = [
    "change_rate_up", "change_rate_down", "volume", "trading_value",
    "turnover", "market_cap", "high_52w", "low_52w",
]
# Node enum → g3112 exgubun (LS guide: 1 전체, 2 뉴욕, 3 나스닥, 4 ETF).
OVERSEAS_RANKING_MARKETS = ["all", "NYSE", "NASDAQ", "ETF"]


_BROKER_CREDENTIAL = {
    "credential_id": "broker_cred",
    "type": "broker_ls_overseas_stock",
    "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
    ],
}


class OverseasStockRankingNode(BaseNode):
    """
    해외주식 순위 노드

    미국 주식의 등락률·거래량·거래대금·회전율·시가총액·52주 신고가/신저가 순위를
    LS g3112(해외주식API시세순위)로 조회합니다. 읽기 전용이며 주문을 내지 않습니다.
    """

    type: Literal["OverseasStockRankingNode"] = "OverseasStockRankingNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockRankingNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    ranking_type: str = Field(
        default="change_rate_up",
        description="Ranking: change_rate_up, change_rate_down, volume, trading_value, turnover, market_cap, high_52w, low_52w",
    )
    market: str = Field(
        default="all",
        description="US segment: all, NYSE, NASDAQ, ETF",
    )
    limit: int = Field(
        default=20,
        ge=RANKING_LIMIT_MIN,
        le=RANKING_LIMIT_MAX,
        description="Maximum number of ranked rows (1-100)",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Pick today's top US gainers, losers, most traded, largest or 52-week-high stocks as a candidate list",
            "Start a US screen from the whole market or one segment (NYSE, NASDAQ, ETF) instead of a fixed watchlist",
        ],
        "when_not_to_use": [
            "For the full listed US universe — use OverseasStockSymbolQueryNode",
            "For domestic stocks — use KoreaStockRankingNode",
            "For overseas futures — there is no LS ranking query; pick a contract with FuturesContractNode",
        ],
        "typical_scenarios": [
            "OverseasStockRankingNode(volume) → CodeNode (filter) → OverseasStockMarketDataNode",
            "OverseasStockRankingNode(high_52w, NASDAQ) → TableDisplayNode",
            "OverseasStockRankingNode.symbols → SplitNode → OverseasStockHistoricalDataNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "LS g3112 (해외주식API시세순위), US only; ranking types map to the LS rank codes 0-7",
        "Outputs `rankings` (full rows), `symbols` (OverseasStock symbol list) and `count`",
        "Exchange comes from the LS key symbol prefix (81 NYSE/AMEX shown as NYSE, 82 NASDAQ); rows without it keep exchange=null and are left out of `symbols`",
        "Numbers are parsed exactly from LS strings; units of trading value and market cap are not declared by LS and are not converted",
        "Pages with cts_value up to `limit` rows, at most 5 requests at 1 request per second",
        "Read-only; overseas stock has no paper trading. Deep validation and dry runs return 3 synthetic rows and make no broker call",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Wiring `symbols` or `rankings` straight into OverseasStockNewOrderNode",
            "reason": "A ranking is a moving market snapshot, not a trading decision; top movers include thin or halted-adjacent issues.",
            "alternative": "Filter in a CodeNode or ConditionNode (price, change, holdings, budget) and order at most the chosen symbol.",
        },
        {
            "pattern": "Treating a row with exchange=null as NYSE or NASDAQ",
            "reason": "The exchange could not be read from the LS key symbol; guessing routes orders to the wrong market.",
            "alternative": "Use the `symbols` output, which keeps only rows with a known exchange.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Top 20 US gainers",
            "description": "List today's 20 biggest US gainers across all segments.",
            "workflow_snippet": {
                "id": "overseas_stock_ranking_gainers",
                "name": "US Top Gainers",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "ranking", "type": "OverseasStockRankingNode", "ranking_type": "change_rate_up", "market": "all", "limit": 20},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.ranking.rankings }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "ranking"},
                    {"from": "ranking", "to": "display"},
                ],
                "credentials": [_BROKER_CREDENTIAL],
            },
            "expected_output": "rankings: [{rank, symbol, exchange, name, price, change_pct, volume, ...}] (up to 20 rows).",
        },
        {
            "title": "NASDAQ volume leaders to quotes",
            "description": "Take the 10 most traded NASDAQ stocks and read their current quotes.",
            "workflow_snippet": {
                "id": "overseas_stock_ranking_volume",
                "name": "NASDAQ Volume Leaders",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "ranking", "type": "OverseasStockRankingNode", "ranking_type": "volume", "market": "NASDAQ", "limit": 10},
                    {"id": "quotes", "type": "OverseasStockMarketDataNode", "symbols": "{{ nodes.ranking.symbols }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.quotes.values }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "ranking"},
                    {"from": "ranking", "to": "quotes"},
                    {"from": "quotes", "to": "display"},
                ],
                "credentials": [_BROKER_CREDENTIAL],
            },
            "expected_output": "quotes.values: current quotes for up to 10 NASDAQ volume leaders.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "No symbol input. Choose ranking_type (change_rate_up, change_rate_down, volume, trading_value, turnover, "
            "market_cap, high_52w, low_52w), market (all, NYSE, NASDAQ, ETF) and limit (1-100). "
            "A connected OverseasStockBrokerNode supplies the connection automatically."
        ),
        "output_consumption": (
            "`rankings` rows: rank, symbol, exchange (NYSE/NASDAQ or null), exchange_source (keysymbol/unavailable), "
            "name (Korean name), exchange_name, keysymbol, price, sign (raw), change and change_pct (signed), volume, "
            "trading_value + trading_value_unit (as_returned), turnover, market_cap + market_cap_unit (as_returned), "
            "high_52w, low_52w, product (overseas_stock), source_tr (g3112). Empty LS strings become null. "
            "`symbols` items: {exchange, symbol, name, product} for rows with a known exchange. `count`: number of rankings rows. "
            "Deep validation and dry runs emit 3 synthetic rows (AAPL, MSFT, NVDA) with this exact shape and no broker call."
        ),
        "common_combinations": [
            "OverseasStockRankingNode.symbols → OverseasStockMarketDataNode",
            "OverseasStockRankingNode.rankings → CodeNode (decision)",
            "OverseasStockRankingNode.rankings → TableDisplayNode",
        ],
        "pitfalls": [
            "The exchange code 81 covers both NYSE and AMEX; it is shown as NYSE",
            "Trading value and market cap units are not declared by LS; compare only within one result",
            "LS failures raise with the TR code first (e.g. 'g3112: <code> <message>')",
        ],
    }

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="rankings", type="array", description="i18n:ports.rankings", fields=OVERSEAS_STOCK_RANKING_FIELDS),
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=OVERSEAS_STOCK_RANKING_SYMBOL_FIELDS),
        OutputPort(name="count", type="integer", description="i18n:ports.count"),
    ]

    _version: ClassVar[str] = "1.0.0"
    _updated_at: ClassVar[str] = "2026-10-15"
    _change_note: ClassVar[Optional[str]] = "New: US stock rankings by change, volume, value, turnover, market cap, 52-week (LS g3112)."

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import ExpressionMode, FieldCategory, FieldSchema, FieldType
        return {
            "ranking_type": FieldSchema(
                name="ranking_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockRankingNode.ranking_type",
                default="change_rate_up",
                enum_values=list(OVERSEAS_RANKING_TYPES),
                enum_labels={value: f"i18n:enums.ranking_type.{value}" for value in OVERSEAS_RANKING_TYPES},
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="change_rate_up",
                expected_type="str",
            ),
            "market": FieldSchema(
                name="market",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockRankingNode.market",
                default="all",
                enum_values=list(OVERSEAS_RANKING_MARKETS),
                enum_labels={value: f"i18n:enums.us_ranking_market.{value}" for value in OVERSEAS_RANKING_MARKETS},
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="all",
                expected_type="str",
            ),
            "limit": FieldSchema(
                name="limit",
                type=FieldType.INTEGER,
                description="i18n:fields.OverseasStockRankingNode.limit",
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

        programgarden 2.6.6+ executes this node with its ranking executor and
        never calls this method (see ``ranking_korea_stock.RANKING_MIN_ENGINE``).
        """
        raise ranking_engine_required(self.type)
