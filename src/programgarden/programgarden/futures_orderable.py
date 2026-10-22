"""Strict CIDBQ01400 request and response boundary, based on the SDK example."""

from decimal import Decimal, InvalidOperation
import math

from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01400.blocks import (
    CIDBQ01400InBlock1,
)


class FuturesCapacityEvidenceError(ValueError):
    """A broker-independent, safe-to-display evidence failure."""


def build_orderable_request(config):
    identity = config.get("symbol")
    if not isinstance(identity, dict) or not all(
        isinstance(identity.get(k), str) and identity[k].strip()
        for k in ("symbol", "exchange")
    ):
        raise FuturesCapacityEvidenceError(
            "A current futures contract symbol and exchange are required"
        )
    side = config.get("side", "buy")
    order_type = config.get("order_type", "limit")
    query = config.get("query_type", "new")
    if (
        side not in ("buy", "sell")
        or order_type not in ("limit", "market")
        or query not in ("new", "close", "total")
    ):
        raise FuturesCapacityEvidenceError(
            "Invalid orderable quantity query parameters"
        )
    price = config.get("price") if order_type == "limit" else 0.0
    if (
        isinstance(price, bool)
        or not isinstance(price, (int, float))
        or not math.isfinite(price)
        or (order_type == "limit" and price <= 0)
    ):
        raise FuturesCapacityEvidenceError("A finite positive limit price is required")
    return CIDBQ01400InBlock1(
        RecCnt=1,
        QryTpCode={"new": "1", "close": "2", "total": "3"}[query],
        IsuCodeVal=identity["symbol"].strip(),
        BnsTpCode="2" if side == "buy" else "1",
        OvrsDrvtOrdPrc=price,
        AbrdFutsOrdPtnCode="2" if order_type == "limit" else "1",
    )


def read_orderable_quantity(response, request):
    if (
        response.status_code != 200
        or response.error_msg
        or response.rsp_cd not in ("00000", "00136")
    ):
        raise FuturesCapacityEvidenceError(
            "CIDBQ01400 did not return a complete successful query"
        )
    echo, result = response.block1, response.block2
    required = set(request.model_dump())
    if echo is None or not required <= echo.model_fields_set:
        raise FuturesCapacityEvidenceError("CIDBQ01400 request echo is incomplete")
    for field, expected in request.model_dump().items():
        observed = getattr(echo, field)
        if field == "OvrsDrvtOrdPrc":
            # The actual response echoes price as a decimal string, not float.
            try:
                matches = Decimal(str(observed)) == Decimal(str(expected))
            except InvalidOperation:
                matches = False
        else:
            matches = observed == expected
        if not matches:
            raise FuturesCapacityEvidenceError(
                f"CIDBQ01400 query echo mismatch: {field}"
            )
    if result is None or "OrdAbleQty" not in result.model_fields_set:
        raise FuturesCapacityEvidenceError(
            "CIDBQ01400 orderable quantity was not provided"
        )
    quantity = result.OrdAbleQty
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        raise FuturesCapacityEvidenceError("CIDBQ01400 orderable quantity is invalid")
    return quantity
