"""Explicit external recordings with real provider normalization and no transport."""
from copy import deepcopy
from urllib.parse import parse_qsl, urlsplit

from programgarden.replay_contracts import ContractViolation, check_contract


def external_record(fixture, node_id, node_type, context):
    record = fixture.get("nodes", {}).get(node_id)
    if not isinstance(record, dict):
        raise ContractViolation(node_id, "An explicit external recording is required", "REPLAY_FIXTURE_REQUIRED")
    if context._iteration_total:
        item = context._iteration_item
        if not isinstance(item, dict) or not isinstance(item.get("symbol"), str) or not item["symbol"]:
            raise ContractViolation(node_id, "An iterated recording requires symbol identity", "REPLAY_FIXTURE_REQUIRED")
        exchange = item.get("exchange")
        if not exchange and node_type.startswith("KoreaStock"):
            # The actual domestic schemas accept {symbol} without exchange.
            exchange = "KRX"
        if not isinstance(exchange, str) or not exchange:
            raise ContractViolation(node_id, "An overseas recording requires exchange identity", "REPLAY_FIXTURE_REQUIRED")
        record = record.get("items", {}).get(exchange + ":" + item["symbol"])
    if not isinstance(record, dict):
        raise ContractViolation(node_id, "No matching per-item recording", "REPLAY_FIXTURE_REQUIRED")
    return record


async def replay_fundamental(node_id, config, context, record):
    """Run the real FMP node while replacing only its HTTP response boundary.

    These are reviewed scenario assumptions, not proof of provider availability,
    API-key validity or subscription access. A fixture cannot override normalized
    output, bypass input validation or silently answer an unrelated request.
    """
    from programgarden_community.nodes.market.fmp import FundamentalDataNode

    requests = record.get("requests")
    if not isinstance(requests, list) or not 1 <= len(requests) <= 64:
        raise ContractViolation(node_id, "An explicit bounded request recording is required", "REPLAY_FIXTURE_REQUIRED")
    pending = deepcopy(requests)

    class RecordedFundamental(FundamentalDataNode):
        async def _fetch_api(self, url, timeout):
            if not pending:
                raise ContractViolation(node_id, "Provider request exceeds the recorded scenario")
            response = pending.pop(0)
            if not isinstance(response, dict) or set(response) != {"request", "response", "contract"}:
                raise ContractViolation(node_id, "A recording requires exact request, response and contract", "REPLAY_FIXTURE_REQUIRED")
            parsed = urlsplit(url)
            query = dict(parse_qsl(parsed.query))
            key = query.pop("apikey", None)
            if (parsed.scheme != "https" or parsed.netloc != "financialmodelingprep.com"
                    or key != "offline-replay" or parsed.fragment
                    or response["request"] != {"path": parsed.path, "query": query}):
                raise ContractViolation(node_id, "Provider request does not match the recorded endpoint, symbols or parameters")
            check_contract(response["response"], response["contract"], node_id + ".provider_response")
            return deepcopy(response["response"])

    node = RecordedFundamental(**{**config, "id": node_id, "api_key": "offline-replay"})
    output = await node.execute(context)
    if pending:
        raise ContractViolation(node_id, "Not all expected provider requests were observed")
    return output
