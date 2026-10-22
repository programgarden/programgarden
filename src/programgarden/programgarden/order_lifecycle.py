"""Synchronous local order journaling, independent of DSL and checkpoints.

Handlers must perform local disk operations only. A prepared operation whose
outcome is unknown must raise on replay; it must never authorize another send.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
from typing import Any, Mapping, Protocol


FUTURES_PRODUCTS = frozenset({"overseas_futures", "overseas_futureoption"})


@dataclass(frozen=True)
class OrderLifecycleMetadata:
    operation_key: str
    job_id: str
    workflow_id: str
    node_id: str
    cycle: int
    iteration_index: int
    invocation_id: str
    broker_node_id: str
    credential_id: str
    product: str
    paper_trading: bool
    symbol: str
    exchange: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal
    broker_order_date: date
    order_date_basis: str = "CIDBT00100_request_OrdDt"


class OrderLifecycleHandler(Protocol):
    def prepare(self, metadata: OrderLifecycleMetadata) -> Mapping[str, Any] | None:
        """Durably prepare, return a prior accepted inner result, or raise."""
        ...

    def accepted(self, metadata: OrderLifecycleMetadata, result: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Durably record acceptance and return additive parent/status fields."""
        ...

    def rejected(self, metadata: OrderLifecycleMetadata, result: Mapping[str, Any]) -> None:
        """Record only a definitive broker rejection, never transport ambiguity."""
        ...


def operation_key(job_id: str, node_id: str, cycle: int, iteration_index: int, invocation_id: str) -> str:
    """Identify an invocation, not its order facts; changed facts must conflict."""
    payload = [job_id, node_id, cycle, iteration_index, invocation_id]
    return "order-v1:" + hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def exact_futures_credential(connection: Mapping[str, Any], context: Any) -> dict[str, Any]:
    """Resolve only the declared broker and credential; never a product slot."""
    broker_id, credential_id = connection.get("broker_node_id"), connection.get("credential_id")
    if not isinstance(broker_id, str) or not broker_id or not isinstance(credential_id, str) or not credential_id:
        raise ValueError("Futures connection requires broker_node_id and credential_id")
    if connection.get("product") not in FUTURES_PRODUCTS or type(connection.get("paper_trading")) is not bool:
        raise ValueError("Futures connection requires explicit product and paper_trading")
    nodes = context._workflow_nodes_map
    if nodes:
        broker = nodes.get(broker_id)
        if broker is None or not broker.node_type.endswith("BrokerNode") or broker.product_scope not in FUTURES_PRODUCTS:
            raise ValueError("Futures connection does not identify a compatible workflow broker")
        if broker.config.get("credential_id") != credential_id:
            raise ValueError("Futures connection credential differs from its workflow broker")
    references = [ref for ref in context._workflow_credentials if ref.get("credential_id") == credential_id]
    if len(references) > 1:
        raise ValueError("Futures credential reference is ambiguous")
    if references:
        credential_type = references[0].get("type") or references[0].get("credential_type")
        if credential_type and credential_type != "broker_ls_overseas_futures":
            raise ValueError("Futures connection references an incompatible credential type")
    registered = context.get_all_outputs(broker_id).get("connection")
    if registered:
        fields = ("broker_node_id", "credential_id", "product", "paper_trading")
        if any(registered.get(key) != connection.get(key) for key in fields):
            raise ValueError("Futures connection does not match its broker output")
    # A restored broker output can resolve its exact workflow credential without
    # reusing a credential from another broker's most recent execution.
    credential = context.get_workflow_credential(credential_id)
    if not credential:
        credential = context.get_credential(f"broker_credentials:{broker_id}:{credential_id}")
    if not credential:
        raise ValueError("Exact futures broker credential is unavailable")
    if "paper_trading" in credential and credential["paper_trading"] != connection["paper_trading"]:
        raise ValueError("Futures credential mode does not match its connection")
    return credential


def inject_futures_connection(node: Any, config: dict[str, Any], workflow: Any, context: Any) -> dict[str, Any]:
    """Preserve an explicit route, or require exactly one compatible broker."""
    if config.get("connection") is not None:
        return config
    candidates = []
    for broker_id, broker in workflow.nodes.items():
        if broker.product_scope != node.product_scope:
            continue
        if node.broker_provider != "all" and broker.broker_provider != "all" and node.broker_provider != broker.broker_provider:
            continue
        outputs = context.get_all_outputs(broker_id)
        if "connection" in outputs or getattr(broker, "node_type", "").endswith("BrokerNode"):
            candidates.append(outputs.get("connection"))
    if len(candidates) > 1:
        raise ValueError("Multiple compatible futures brokers require an explicit connection")
    if len(candidates) == 1 and candidates[0] is not None:
        return {**config, "connection": candidates[0]}
    return config
