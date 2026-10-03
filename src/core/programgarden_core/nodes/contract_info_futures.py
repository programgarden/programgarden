"""Runtime contract metadata for an exact listed overseas futures symbol."""
from typing import ClassVar, Dict, List, Literal, Optional

from pydantic import Field

from programgarden_core.nodes.base import BaseNode, BrokerProvider, InputPort, NodeCategory, OutputPort, ProductScope
from programgarden_core.models.field_binding import ExpressionMode, FieldCategory, FieldSchema, FieldType


CONTRACT_INFO_FIELDS = [
    {"name": key, "type": "string", "description": description}
    for key, description in {
        "symbol": "Exact observed contract symbol.",
        "exchange": "Observed exchange code matching the request.",
        "symbol_name": "Observed contract name; null if absent.",
        "underlying_code": "Observed underlying product code; null if absent.",
        "currency": "Observed contract currency; null if absent.",
        "maturity_date": "LS MtrtDt, YYYY-MM-DD; null if missing or invalid.",
        "last_trading_date": "LS FnlDlDt, YYYY-MM-DD; distinct from maturity; null if unknown.",
        "first_notice_date": "LS FstTrsfrDt, YYYY-MM-DD; null if unknown or not supplied.",
        "master_received_date": "LS ApplDate, YYYY-MM-DD; not proof of future calendar coverage.",
        "korea_start_date": "LS DlDt date, YYYY-MM-DD.",
        "korea_start_time": "LS DlStrtTm time, HH:MM:SS; a reported session, not all trading windows.",
        "korea_end_time": "LS DlEndTm time, HH:MM:SS; no end date is inferred.",
        "local_start_date": "LS OvsStrDay date, YYYY-MM-DD.",
        "local_start_time": "LS OvsStrTm time, HH:MM:SS.",
        "local_end_date": "LS OvsEndDay date, YYYY-MM-DD.",
        "local_end_time": "LS OvsEndTm time, HH:MM:SS.",
        "trade_status_code": "Raw LS DlPsblCd; no undocumented enum interpretation.",
        "source_tr": "o3105.",
        "observed_at": "UTC time of this observation, ISO8601; not a broker data timestamp.",
    }.items()
] + [
    {"name": key, "type": "number", "description": description}
    for key, description in {
        "initial_margin": "Observed OpngMgn; null if absent/invalid. Not account order capacity.",
        "maintenance_margin": "Observed MntncMgn; null if absent/invalid.",
        "tick_size": "Observed positive UntPrc; null if unavailable.",
        "tick_value": "Observed positive MnChgAmt; null if unavailable.",
    }.items()
]


class OverseasFuturesContractInfoNode(BaseNode):
    type: Literal["OverseasFuturesContractInfoNode"] = "OverseasFuturesContractInfoNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesContractInfoNode.description"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS
    _version: ClassVar[str] = "1.0.0"
    _updated_at: ClassVar[str] = "2026-10-03"
    _change_note: ClassVar[str] = "Read native futures contract dates, margins and reported sessions without placing an order."

    symbol: Optional[Dict[str, str]] = Field(default=None, description="Exact listed contract identity: symbol and exchange.")
    _inputs: List[InputPort] = [InputPort(name="trigger", type="signal", required=False, description="Refresh after resolving the contract.")]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="object", fields=CONTRACT_INFO_FIELDS, description="Observed contract details; null when the query fails. Optional fields remain null."),
        OutputPort(name="verified", type="boolean", description="Successful response with matching symbol/exchange; not completeness of all optional fields."),
        OutputPort(name="missing_fields", type="array", description="Optional output fields absent or invalid in the broker response."),
        OutputPort(name="error", type="string", description="Safe failure reason; null for a matching successful response."),
    ]
    _usage: ClassVar[dict] = {
        "when_to_use": ["Inspect runtime maturity/last-trading/notice dates, margins, currency and reported session times for an exact futures contract."],
        "when_not_to_use": ["Selecting front/next months (FuturesContractNode), confirming fills, computing a holiday calendar or authorizing an order."],
        "typical_scenarios": ["FuturesContractNode → OverseasFuturesContractInfoNode → date guard; account-held symbol → detail → rollover eligibility."],
    }
    _features: ClassVar[list] = [
        "One read-only o3105 request; no model call, positive quote requirement or order submission.",
        "Always reads one explicit symbol object; upstream arrays do not repeat the request. Use SplitNode and bind nodes.split.item for an explicit batch.",
        "Missing dates/numbers remain null; source dates are never guessed from the contract month.",
        "Deep validation uses synthetic data; replay uses recorded SDK responses through the same parser.",
    ]
    _node_guide: ClassVar[dict] = {
        "input_handling": "Bind one {symbol, exchange} object, with an ordering edge from its producer and an upstream futures broker. Use the actual held contract for rollover, which may differ from today's front month.",
        "output_consumption": "Require verified=true and the specific non-null fields the decision needs. Dates use YYYY-MM-DD. Session times describe the returned session only; use an authoritative calendar for holidays/trading-day offsets. Confirm close fills before reopening.",
        "pitfalls": ["verified does not assert every optional field exists. Initial margin is not available account capacity. Neither dates nor raw trade status prove the exchange is currently open."],
        "common_combinations": ["FuturesContractNode, OverseasFuturesAccountNode, CodeNode, OverseasFuturesOrderableQuantityNode."],
    }
    _anti_patterns: ClassVar[list] = [{"pattern": "Guess missing expiry from weekdays or reopen on order ACK.", "reason": "A reported date and a broker-confirmed execution are separate inputs.", "alternative": "Require the authoritative date and correlated close fills; report unavailable evidence explicitly."}]
    _examples: ClassVar[list] = [{
        "title": "Inspect the current front contract",
        "description": "Read-only component; no order is submitted.",
        "expected_output": "value contains observed details; unsupported or missing fields stay null.",
        "workflow_snippet": {
            "id": "futures-contract-details", "name": "Inspect futures contract",
            "nodes": [{"id": "start", "type": "StartNode"},
                      {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": True},
                      {"id": "contract", "type": "FuturesContractNode", "base_products": ["HMH"], "contract_selection": "front"},
                      {"id": "detail", "type": "OverseasFuturesContractInfoNode", "symbol": "{{ nodes.contract.symbols[0] }}"}],
            "edges": [{"from": a, "to": b} for a, b in [("start", "broker"), ("broker", "contract"), ("contract", "detail")]],
            "credentials": [{"credential_id": "broker_cred", "type": "broker_ls_overseas_futures", "data": [{"key": "appkey", "value": ""}, {"key": "appsecret", "value": ""}]}],
        },
    }]

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    @classmethod
    def get_field_schema(cls) -> Dict[str, FieldSchema]:
        return {"symbol": FieldSchema(
            name="symbol", type=FieldType.OBJECT,
            display_name="i18n:fieldNames.OverseasFuturesContractInfoNode.symbol",
            description="Exact listed contract symbol and exchange; resolve at run time.",
            category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH, required=True,
            object_schema=[{"name": "symbol", "type": "STRING", "required": True}, {"name": "exchange", "type": "STRING", "required": True}],
            bindable_sources=["FuturesContractNode.symbols", "SplitNode.item"],
            example_binding="{{ nodes.contract.symbols[0] }}",
        )}
