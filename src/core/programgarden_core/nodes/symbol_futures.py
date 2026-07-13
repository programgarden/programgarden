"""
ProgramGarden Core - Futures Symbol Nodes

해외선물 종목 관련:
- OverseasFuturesSymbolQueryNode: 해외선물 전체 거래 가능 종목 조회 (o3101 API)
- FuturesContractNode: 기초자산의 **현재 상장 월물**을 실행 시점에 해소 (o3101 API)
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
    OVERSEAS_FUTURES_SYMBOL_QUERY_FIELDS,
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
        "Overseas-futures entitlement is per exchange — a test account typically only carries HKEX and LME. Picking an exchange the account does not carry fails loudly with the list LS actually returns (never a silent empty universe)",
        "Expired contract months are dropped — LS serves neither bars nor quotes for them, and reports no error",
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
            "title": "List every front-month contract the account can trade",
            "description": "Fetch the near-month contract of each listed product and display the full list.",
            "workflow_snippet": {
                "id": "overseas_futures_symbol_query_all",
                "name": "Front Month Contracts",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "symbols", "type": "OverseasFuturesSymbolQueryNode", "futures_exchange": "1", "futures_contract_month": "front", "max_results": 100},
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
            "To trade one known underlying (Mini Hang Seng, …), use FuturesContractNode instead — this node browses the whole universe",
            "futures_exchange is limited by the account's per-exchange entitlement; an exchange the account does not carry fails loudly (it is not silently empty)",
            "Use OverseasFuturesBrokerNode (not OverseasStockBrokerNode) as the upstream broker",
        ],
    }

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=OVERSEAS_FUTURES_SYMBOL_QUERY_FIELDS),
        OutputPort(name="count", type="integer", description="Total symbol count"),
    ]

    _version: ClassVar[str] = "1.0.0"
    _updated_at: ClassVar[str] = "2026-05-19"
    _change_note: ClassVar[Optional[str]] = None

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


class FuturesContractNode(BaseNode):
    """
    해외선물 월물 해소 노드

    기초자산(예: HMH=미니항셍)의 **현재 상장된 월물**을 실행 시점에 조회해
    실제 종목코드(예: HMHN26)로 해소합니다. o3101 API (해외선물마스터조회) 사용.

    워크플로우에 월물 코드를 하드코딩하면 만기가 지나는 순간 조용히 죽습니다
    (LS 는 만기 경과 종목에 과거봉도 현재가도 주지 않고, 에러도 내지 않습니다).
    이 노드는 저작 시점이 아니라 **실행 시점**에 월물을 고르므로 시간이 지나면
    자동으로 다음 월물로 넘어갑니다.
    """

    type: Literal["FuturesContractNode"] = "FuturesContractNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.FuturesContractNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    base_products: List[str] = Field(
        default_factory=list,
        description=(
            "Underlying product codes to resolve (LS BscGdsCd). "
            "e.g. ['HMH'] = Mini Hang Seng, ['HMCE'] = Mini H-Shares. "
            "One contract is emitted per code, in the given order."
        ),
    )
    contract_selection: Literal["front", "next", "quarterly"] = Field(
        default="front",
        description=(
            "Which listed contract to pick per underlying: "
            "'front' = nearest expiry (most liquid), "
            "'next' = second nearest (roll target), "
            "'quarterly' = nearest Mar/Jun/Sep/Dec contract."
        ),
    )
    futures_exchange: Optional[str] = Field(
        default=None,
        description="Optional exchange filter by LS exchange code (ExchCd), e.g. 'HKEX'. Omit for all exchanges.",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Any futures workflow that must keep working after the current contract expires — this is the default way to name a futures instrument",
            "Trading/backtesting an index future by its underlying (Mini Hang Seng, Mini H-Shares) rather than a specific month",
            "Rolling strategies that need the front month now and the next month as the roll target",
        ],
        "when_not_to_use": [
            "For stocks — use WatchlistNode (stock symbols do not expire)",
            "When the user explicitly pins one historical contract month for a fixed-period study (then hardcode it in WatchlistNode and accept it will expire)",
            "To browse the whole futures universe — use OverseasFuturesSymbolQueryNode",
        ],
        "typical_scenarios": [
            "FuturesContractNode → OverseasFuturesHistoricalDataNode → ConditionNode → OverseasFuturesNewOrderNode",
            "FuturesContractNode → OverseasFuturesMarketDataNode (current price of the front month)",
            "FuturesContractNode → OverseasFuturesRealMarketDataNode (realtime tick subscription)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Resolves underlying product codes to the **currently listed** contract symbols at execution time (o3101 master query)",
        "Expired months are never returned — LS drops them from the master, and the node additionally filters out any month before the current one",
        "`symbols` output has the exact same shape as WatchlistNode ([{exchange, symbol}]), so every downstream futures node wires unchanged",
        "contract_selection: front (nearest) / next (roll target) / quarterly (nearest Mar-Jun-Sep-Dec)",
        "Fails loudly with the list of available underlying codes when base_products contains an unknown code — never returns a silent empty list",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hardcoding a contract month such as WatchlistNode symbols=[{'symbol': 'HMHU26'}]",
            "reason": "The workflow dies silently the moment that month expires — LS returns empty bars and no error, so the strategy simply stops trading.",
            "alternative": "Use FuturesContractNode with base_products=['HMH'] so the live month is resolved on every run.",
        },
        {
            "pattern": "Putting a full contract symbol (HMHN26) into base_products",
            "reason": "base_products expects the underlying product code (BscGdsCd), not the month-coded contract symbol.",
            "alternative": "Use base_products=['HMH'] — the node appends the month code itself.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Front-month Mini Hang Seng price (never expires)",
            "description": "Resolve the currently listed Mini Hang Seng front month and fetch its price.",
            "workflow_snippet": {
                "id": "futures_contract_front_month",
                "name": "Mini Hang Seng Front Month",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "contract", "type": "FuturesContractNode", "base_products": ["HMH"], "contract_selection": "front"},
                    {"id": "market", "type": "OverseasFuturesMarketDataNode", "symbol": "{{ item }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.market.values }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "contract"},
                    {"from": "contract", "to": "market"},
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
            "expected_output": "symbols port: [{'exchange': 'HKEX', 'symbol': 'HMHN26'}] — the month code follows whatever LS currently lists.",
        },
        {
            "title": "Two underlyings, front month each",
            "description": "Resolve Mini Hang Seng and Mini H-Shares front months and run RSI on both.",
            "workflow_snippet": {
                "id": "futures_contract_two_underlyings",
                "name": "HKEX Mini Futures RSI",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "contract", "type": "FuturesContractNode", "base_products": ["HMH", "HMCE"], "contract_selection": "front"},
                    {"id": "historical", "type": "OverseasFuturesHistoricalDataNode", "symbol": "{{ item }}", "interval": "1d"},
                    {"id": "rsi", "type": "ConditionNode", "conditions": [{"indicator": "rsi", "operator": "<", "value": 30}]},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "contract"},
                    {"from": "contract", "to": "historical"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "rsi"},
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
            "expected_output": "symbols port: [{'exchange': 'HKEX', 'symbol': 'HMHN26'}, {'exchange': 'HKEX', 'symbol': 'HMCEN26'}]",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "No symbol input — this node *produces* the symbol list. Requires an upstream "
            "OverseasFuturesBrokerNode (the LS master query needs a session). "
            "Set base_products to the underlying codes: HMH (Mini Hang Seng), HMCE (Mini H-Shares), "
            "HSI (Hang Seng), HTI (Hang Seng TECH), HCEI (H-Share), MCA (MSCI China A50)."
        ),
        "output_consumption": (
            "The `symbols` port emits [{exchange, symbol}] — identical to WatchlistNode. "
            "Wire it into OverseasFuturesHistoricalDataNode / OverseasFuturesMarketDataNode / "
            "OverseasFuturesRealMarketDataNode with `symbol: \"{{ item }}\"` (the engine auto-iterates one contract at a time). "
            "The `contracts` port carries the full detail ({symbol, exchange, base_product, name, contract_month}) "
            "when you need the month or product name for a report."
        ),
        "common_combinations": [
            "FuturesContractNode.symbols → OverseasFuturesHistoricalDataNode (symbol: {{ item }}) → ConditionNode",
            "FuturesContractNode.symbols → OverseasFuturesMarketDataNode (symbol: {{ item }})",
            "FuturesContractNode.symbols → SymbolFilterNode → PositionSizingNode → OverseasFuturesNewOrderNode",
        ],
        "pitfalls": [
            "base_products takes the underlying code (HMH), not the contract symbol (HMHN26)",
            "Requires OverseasFuturesBrokerNode upstream — the o3101 master query needs an LS session",
            "contract_selection='next' fails loudly if the underlying has only one listed month",
        ],
    }

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
            fields=SYMBOL_LIST_FIELDS,
            example=[{"exchange": "HKEX", "symbol": "HMHN26"}],
        ),
        OutputPort(
            name="contracts",
            type="array",
            description="Resolved contract details",
            fields=[
                {"name": "symbol", "type": "string", "description": "계약 종목코드 (예: HMHN26)"},
                {"name": "exchange", "type": "string", "description": "거래소 코드 (예: HKEX)"},
                {"name": "base_product", "type": "string", "description": "기초자산 코드 (예: HMH)"},
                {"name": "base_product_name", "type": "string", "description": "기초자산명 (예: Mini Hang Seng)"},
                {"name": "name", "type": "string", "description": "종목명 (예: Mini Hang Seng(2026.07))"},
                {"name": "contract_month", "type": "string", "description": "월물 (예: 2026-07)"},
            ],
            example=[{
                "symbol": "HMHN26", "exchange": "HKEX", "base_product": "HMH",
                "base_product_name": "Mini Hang Seng", "name": "Mini Hang Seng(2026.07)",
                "contract_month": "2026-07",
            }],
        ),
        OutputPort(name="count", type="integer", description="Resolved contract count"),
    ]

    _version: ClassVar[str] = "1.0.0"
    _updated_at: ClassVar[str] = "2026-07-13"
    _change_note: ClassVar[Optional[str]] = "신규 — 만기 하드코딩 제거(실행 시점 월물 해소)"

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "base_products": FieldSchema(
                name="base_products",
                type=FieldType.ARRAY,
                description=(
                    "기초자산 코드 목록. 코드마다 월물 1건씩 해소된다. "
                    "HMH=미니 항셍, HMCE=미니 H주(HSCEI), HSI=항셍, HTI=항셍테크, "
                    "HCEI=H주, MCA=MSCI 중국A50, HBI=항셍바이오텍"
                ),
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=["HMH", "HMCE"],
                expected_type="list[str]",
                placeholder="HMH, HMCE",
            ),
            "contract_selection": FieldSchema(
                name="contract_selection",
                type=FieldType.ENUM,
                description="월물 선택 방식. front=근월물(유동성 최대), next=차월물(롤오버 대상), quarterly=분기월물(3/6/9/12월 중 최근접)",
                enum_values=["front", "next", "quarterly"],
                enum_labels={
                    "front": "i18n:enums.contract_selection.front",
                    "next": "i18n:enums.contract_selection.next",
                    "quarterly": "i18n:enums.contract_selection.quarterly",
                },
                default="front",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="front",
                expected_type="str",
            ),
            "futures_exchange": FieldSchema(
                name="futures_exchange",
                type=FieldType.STRING,
                description="거래소 코드(ExchCd) 필터. 예: HKEX, LME. 비우면 전체 거래소에서 기초자산 코드로 찾는다.",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="HKEX",
                expected_type="str",
                placeholder="HKEX",
            ),
        }
