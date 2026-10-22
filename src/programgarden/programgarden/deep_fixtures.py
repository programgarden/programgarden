"""Public fixture helpers for dry-run. Deep validation is platform-only; this module
provides only minimal, generic, shape-correct placeholder data so a public dry-run
completes without broker calls. It contains no recorded broker responses and no
curated fixture content."""


def apply_override(default, override=None):
    merged = dict(default or {})
    if isinstance(override, dict):
        merged.update(override)
    return merged


def futures_contract_fixture(config, *, now=None):
    cfg = config or {}
    exchange = str(cfg.get("exchange") or "")
    contracts = []
    for product in cfg.get("base_products") or []:
        code = str(product)
        if code:
            contracts.append({"symbol": code, "exchange": exchange, "base_product": code,
                              "base_product_name": code, "name": code, "contract_month": ""})
    return {"symbols": [{"exchange": c["exchange"], "symbol": c["symbol"]} for c in contracts],
            "contracts": contracts, "count": len(contracts)}


def _placeholder(schema):
    if not isinstance(schema, dict):
        return None
    kind = schema.get("type")
    if kind == "object":
        return {key: _placeholder(sub) for key, sub in (schema.get("properties") or {}).items()}
    return {"array": [], "string": "", "integer": 0, "number": 0.0, "boolean": False}.get(kind)


def ai_agent_fixture(config):
    cfg = config or {}
    if cfg.get("output_format") == "structured":
        return {"response": _placeholder(cfg.get("output_schema")) or {}}
    return {"response": ""}


def __getattr__(name):
    def _unavailable(*args, **kwargs):
        raise NotImplementedError("Deep validation runs on the ProgramGarden platform only.")
    return _unavailable
