"""
ProgramGarden Core - Futures Symbol Query Node

해외선물 전체종목조회:
- OverseasFuturesSymbolQueryNode: 해외선물 전체 거래 가능 종목 조회 (o3101 API)
"""

from typing import Any, Optional, List, Literal, Dict, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ProductScope,
    BrokerProvider,
    SYMBOL_LIST_FIELDS,
)


class OverseasFuturesSymbolQueryNode(BaseNode):
    """
    해외선물 전체종목조회 노드

    해외선물 전체 거래 가능 종목을 조회합니다.
    o3101 API (해외선물마스터조회) 사용.
    """

    type: Literal["OverseasFuturesSymbolQueryNode"] = "OverseasFuturesSymbolQueryNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesSymbolQueryNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    futures_exchange: Optional[str] = Field(
        default=None,
        description="Exchange for overseas_futures: 1(all), 2(CME), 3(SGX), etc.",
    )
    futures_contract_month: Optional[str] = Field(
        default=None,
        description="Contract month filter for overseas_futures: F, 2026F, front, next",
    )
    max_results: int = Field(
        default=500,
        description="Maximum number of symbols to retrieve per request",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Retrieve the full list of tradeable overseas futures contracts from LS Securities (CME, EUREX, SGX, HKEX, ICE, OSE)",
            "Discover available contract months before wiring specific symbols into downstream market data or order nodes",
            "Bootstrap a futures universe for a screener or multi-contract strategy",
        ],
        "when_not_to_use": [
            "For overseas stock symbol lookup — use OverseasStockSymbolQueryNode",
            "For Korean domestic stock symbols — use KoreaStockSymbolQueryNode",
            "When you already know the exact contract symbols — hardcode them in WatchlistNode or SplitNode items",
        ],
        "typical_scenarios": [
            "OverseasFuturesSymbolQueryNode → SplitNode → OverseasFuturesMarketDataNode (universe price scan)",
            "OverseasFuturesSymbolQueryNode → ScreenerNode (filter by volume/open_interest criteria)",
            "OverseasFuturesSymbolQueryNode → SplitNode → OverseasFuturesHistoricalDataNode (history for each contract)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Queries o3101 API (overseas futures master) — returns [{symbol, exchange, name, contract_month, currency, ...}] list",
        "Filter by futures_exchange (1=all, 2=CME, 3=SGX, 4=EUREX, 5=ICE, 6=HKEX, 7=OSE) and futures_contract_month (front/next/F/2026F)",
        "Contract month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec",
        "max_results cap (100–10000) prevents runaway API calls; uses continuation query under the hood",
        "Outputs `symbols` (list) and `count` (int) ports",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using futures_contract_month=None to fetch all contract months across all exchanges",
            "reason": "This can return thousands of contracts (spot, weekly, monthly, quarterly) that are irrelevant to most strategies.",
            "alternative": "Set futures_contract_month='front' or 'next' to get the near-month and far-month liquid contracts only.",
        },
        {
            "pattern": "Connecting symbols output directly to OverseasFuturesNewOrderNode without a screener or filter",
            "reason": "An unfiltered exchange master can have illiquid or expired contracts — blindly ordering them will fail or create unintended positions.",
            "alternative": "Route through ScreenerNode or SymbolFilterNode to validate liquidity before passing to order nodes.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "List all front-month CME contracts",
            "description": "Fetch near-month CME futures contracts and display the full list.",
            "workflow_snippet": {
                "id": "overseas_futures_symbol_query_cme",
                "name": "CME Front Month Contracts",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "symbols", "type": "OverseasFuturesSymbolQueryNode", "futures_exchange": "2", "futures_contract_month": "front", "max_results": 100},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.symbols.symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "symbols"},
                    {"from": "symbols", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "symbols port: [{symbol, exchange, name, contract_month, currency}, ...]. count port: total count.",
        },
        {
            "title": "HKEX mini-futures symbol query for multi-contract strategy",
            "description": "Fetch near-month HKEX futures, split by contract, and scan prices for each.",
            "workflow_snippet": {
                "id": "overseas_futures_symbol_query_hkex",
                "name": "HKEX Contract Scan",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "symbols", "type": "OverseasFuturesSymbolQueryNode", "futures_exchange": "6", "futures_contract_month": "front", "max_results": 50},
                    {"id": "split", "type": "SplitNode", "items": "{{ nodes.symbols.symbols }}"},
                    {"id": "market", "type": "OverseasFuturesMarketDataNode", "symbol": "{{ nodes.split.item }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.market.value }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "symbols"},
                    {"from": "symbols", "to": "split"},
                    {"from": "split", "to": "market"},
                    {"from": "broker", "to": "market"},
                    {"from": "market", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "Each HKEX front-month contract's price data is fetched and displayed in a table.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "No symbol input required — this node generates the futures universe. "
            "Set futures_exchange (2=CME, 3=SGX, 4=EUREX, 5=ICE, 6=HKEX, 7=OSE, 1=all). "
            "Use futures_contract_month='front' or 'next' to get liquid near-month contracts only."
        ),
        "output_consumption": (
            "The `symbols` port emits list[dict] with fields: symbol, exchange, name, contract_month, currency. "
            "Wire to SplitNode for per-contract downstream processing. "
            "The `count` port emits the total number of contracts returned (int)."
        ),
        "common_combinations": [
            "OverseasFuturesSymbolQueryNode.symbols → SplitNode → OverseasFuturesMarketDataNode (universe price scan)",
            "OverseasFuturesSymbolQueryNode.symbols → ScreenerNode (volume/open_interest filter)",
            "OverseasFuturesSymbolQueryNode.symbols → SymbolFilterNode (exclude specific contracts)",
        ],
        "pitfalls": [
            "Omitting futures_contract_month returns all contract months — filter to 'front'/'next' for most strategies",
            "Contract symbols expire — update futures_contract_month monthly or use 'front'/'next' to auto-select near-month",
            "Use OverseasFuturesBrokerNode (not OverseasStockBrokerNode) as the upstream broker",
        ],
    }

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="Total symbol count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "futures_exchange": FieldSchema(
                name="futures_exchange",
                type=FieldType.ENUM,
                description="거래소 구분. 1: 전체, 2: CME, 3: SGX, 4: EUREX, 5: ICE, 6: HKEX, 7: OSE",
                enum_values=["1", "2", "3", "4", "5", "6", "7"],
                enum_labels={
                    "1": "i18n:enums.futures_exchange.1",
                    "2": "i18n:enums.futures_exchange.2",
                    "3": "i18n:enums.futures_exchange.3",
                    "4": "i18n:enums.futures_exchange.4",
                    "5": "i18n:enums.futures_exchange.5",
                    "6": "i18n:enums.futures_exchange.6",
                    "7": "i18n:enums.futures_exchange.7",
                },
                default="1",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="1",
                expected_type="str",
            ),
            "futures_contract_month": FieldSchema(
                name="futures_contract_month",
                type=FieldType.STRING,
                description="월물 필터. 예: 'F' (1월), '2026F' (2026년 1월), 'front' (근월물), 'next' (차월물). 월물코드: F=1월, G=2월, H=3월, J=4월, K=5월, M=6월, N=7월, Q=8월, U=9월, V=10월, X=11월, Z=12월",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="front",
                expected_type="str",
                placeholder="front, next, F, 2026F",
            ),
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 조회 건수. 연속 조회로 전체 데이터를 가져옵니다.",
                default=500,
                min_value=100,
                max_value=10000,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=500,
                expected_type="int",
            ),
        }
