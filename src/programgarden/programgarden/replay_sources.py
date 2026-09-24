"""Replay raw I/O observations through native parsers and selection logic.

These records are scenario assumptions, not evidence of provider availability.
The independent suite owns the inputs. No adapter reads a live file or transport.
"""
from copy import deepcopy
from pathlib import PurePosixPath

from programgarden.replay_contracts import ContractViolation, check_contract
from programgarden.replay_external import external_record
from programgarden.replay_triggers import fixture_instant

SOURCE_NODES = frozenset({"FileReaderNode", "FearGreedIndexNode", "MarketUniverseNode",
    "FuturesContractNode", "ScreenerNode", "OverseasFuturesOrderableQuantityNode"})


def source_contract_catalog():
    """Describe parser inputs to private scenario authors without running I/O.

    SDK schemas document available fields, not a promise that a live response
    fills them. This catalog is not an expected node result or a PASS receipt.
    The parser and independently written assertions remain authoritative.
    """
    from programgarden_finance.ls.overseas_futureoption.market.o3101.blocks import O3101OutBlock
    from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01400.blocks import CIDBQ01400Response
    from programgarden_finance.ls.overseas_stock.market.g3101.blocks import G3101OutBlock
    from programgarden.executor import MarketUniverseNodeExecutor
    stock = {"type": "object", "properties": {
        "symbol": {"type": "string"}, "name": {"type": "string"}, "symbols": {
            "type": "array", "items": {"type": "object", "properties": {
                "google": {"type": "string"}, "currency": {"type": "string"}}}}}}
    return {
        "FearGreedIndexNode": {"source_schema": {"type": "object", "required": ["fear_and_greed"],
            "properties": {"fear_and_greed": {"type": "object", "required": ["score"], "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "previous_close": {"type": "number"}}}}},
            "notes": "Native parser maps score to value/label and reads previous_close. Synthetic inputs only."},
        "FileReaderNode": {"source_schema": {"type": "object", "properties": {"files": {
            "type": "object", "additionalProperties": {"type": "string"}}}},
            "notes": "files maps each requested relative upload path to base64 encoded bytes. The native "
                     "format parser reads those bytes; do not supply parsed data. Inline file_data uses "
                     "native configuration. Absolute paths and parent traversal are forbidden."},
        "MarketUniverseNode": {"source_schema": {"type": "object", "required": ["index", "stocks"],
            "properties": {"index": {"type": "string"}, "stocks": {"type": "array", "items": stock}}},
            "index_mapping": dict(MarketUniverseNodeExecutor.INDEX_MAPPING),
            "notes": "index must match the resolved universe. rows are pytickersymbols provider records; "
                     "symbols[].google uses VENUE:TICKER and currency identifies the USD listing."},
        "FuturesContractNode": {"source_schema": {"type": "object", "required": ["rows"],
            "properties": {"rows": {"type": "array", "items": O3101OutBlock.model_json_schema()}}},
            "required_row_fields": ["Symbol", "BscGdsCd", "ExchCd", "LstngYr", "LstngM"],
            "notes": "Supply raw o3101 model fields, including explicit contract identity/month. "
                     "Native expiry/exchange/front-next selection runs at as_of; do not preselect results."},
        "OverseasFuturesOrderableQuantityNode": {"source_schema": CIDBQ01400Response.model_json_schema(),
            "notes": "Use the SDK response envelope (block1, block2, status_code, rsp_cd, error_msg), "
                     "not LS wire block names. status_code=200, error_msg absent and rsp_cd=00000 or00136 "
                     "are supported success evidence. block1 must explicitly echo every generated request "
                     "field with matching values; the echoed price is a decimal string. "
                     "block2.OrdAbleQty must be explicitly provided, integer and nonnegative."},
        "ScreenerNode": {"source_schema": {"type": "object", "properties": {
            "quotes": {"type": "object", "additionalProperties": {"type": "object", "properties": {
                **{key: {"type": "number"} for key in ("regularMarketPrice", "currentPrice", "previousClose",
                    "marketCap", "averageVolume")},
                **{key: {"type": "string"} for key in ("sector", "exchange", "shortName", "longName")}}}},
            "g3101": {"type": "object", "additionalProperties": G3101OutBlock.model_json_schema()},
            "index": {"type": "string"}, "stocks": {"type": "array", "items": stock}}},
            "notes": "For yfinance, quotes is keyed by actual lookup ticker (domestic .KS/.KQ suffix), "
                     "with native info field names. For LS, g3101 is keyed by keysymbol; raw rows require "
                     "symbol, keysymbol, exchcd, price and volume. Explicit watchlists need all lookups; "
                     "market search additionally needs index=S&P 500 and raw stocks rows. LS quotes do "
                     "not provide market cap/sector: those filters need independently supplied upstream "
                     "evidence, otherwise validation must fail. Native filtering/sorting must run."},
    }


class _ComputationContext:
    """Use live computation guards while the worker retains its kernel boundary."""
    is_dry_run = False
    is_deep_validate = False

    def __init__(self, context):
        self.context = context

    def __getattr__(self, name):
        return getattr(self.context, name)


async def execute_source(node, config, fixture, context):
    record = external_record(fixture, node.id, node.type, config, context)
    if record.get("kind") != "raw_source" or "source" not in record or "source_contract" not in record:
        raise ContractViolation(node.id, "Raw provider/file source required", "REPLAY_FIXTURE_REQUIRED")
    check_contract(record["source"], record["source_contract"], node.id + ".source")
    source = deepcopy(record["source"])
    if not isinstance(source, dict):
        raise ContractViolation(node.id, "Source envelope must be an object")
    if node.type == "FearGreedIndexNode":
        check_contract(source, {"type": "object", "required": ["fear_and_greed"], "properties": {
            "fear_and_greed": {"type": "object", "required": ["score"], "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100}}}}}, node.id)
        return node.parse_response(source)
    if node.type == "FileReaderNode":
        # Materialize the exact recorded bytes through the native base64 path.
        # Preserve format/name selection; never read /app/data or a host path.
        paths, data, names = node._normalize_inputs()
        files = source.get("files", {})
        for index, path in enumerate(paths):
            if not path:
                continue
            parsed = PurePosixPath(path)
            if parsed.is_absolute() or ".." in parsed.parts:
                raise ContractViolation(node.id, "Replay file paths must stay relative to the upload directory")
            if path not in files or not isinstance(files[path], str):
                raise ContractViolation(node.id, "Requested file has no recorded bytes", "REPLAY_FIXTURE_REQUIRED")
            while len(data) <= index:
                data.append("")
            while len(names) <= index:
                names.append("")
            data[index] = files[path]
            names[index] = names[index] or PurePosixPath(path).name
        local = node.model_copy(update={"file_paths": [], "file_path": None,
            "file_data_list": data, "file_data": None, "file_names": names, "file_name": None})
        return await local.execute(context)
    if node.type == "MarketUniverseNode":
        from programgarden.executor import MarketUniverseNodeExecutor
        executor = MarketUniverseNodeExecutor()
        index = executor.INDEX_MAPPING.get(node.universe, node.universe)
        if source.get("index") != index or not isinstance(source.get("stocks"), list):
            raise ContractViolation(node.id, "Constituent source index does not match the request")
        symbols = executor.parse_constituents(source["stocks"], index)
        return {"symbols": symbols, "count": len(symbols)}
    if node.type == "FuturesContractNode":
        from programgarden.executor import FuturesContractNodeExecutor, SymbolQueryNodeExecutor
        from programgarden_finance.ls.overseas_futureoption.market.o3101.blocks import O3101OutBlock
        required = {"Symbol", "BscGdsCd", "ExchCd", "LstngYr", "LstngM"}
        records = source.get("rows")
        if not isinstance(records, list) or not records or any(not required <= r.keys() for r in records):
            raise ContractViolation(node.id, "Complete master-row identities are required")
        rows = [O3101OutBlock.model_validate(r, strict=True) for r in records]
        exchange = (node.futures_exchange or "").strip().upper()
        exchange = SymbolQueryNodeExecutor.FUTURES_EXCHANGE_CODES.get(exchange, exchange)
        if exchange in ("1", "ALL"):
            exchange = ""
        return FuturesContractNodeExecutor().select_recorded_master(rows,
            [p.strip().upper() for p in node.base_products], node.contract_selection, exchange,
            context, node.id, as_of=fixture_instant(context, node.id))
    if node.type == "OverseasFuturesOrderableQuantityNode":
        from programgarden.futures_orderable import build_orderable_request, read_orderable_quantity
        from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01400.blocks import CIDBQ01400Response
        response = CIDBQ01400Response.model_validate(source, strict=True)
        quantity = read_orderable_quantity(response, build_orderable_request(config))
        return {"quantity": quantity, "verified": True, "error": None}
    if node.type == "ScreenerNode":
        from programgarden.executor import ScreenerNodeExecutor

        class RecordedScreener(ScreenerNodeExecutor):
            missing = False

            def quote_info(self, ticker):
                rows = source.get("quotes", {})
                if ticker not in rows:
                    self.missing = True
                    raise ContractViolation(node.id, "Missing per-symbol quote", "REPLAY_FIXTURE_REQUIRED")
                return deepcopy(rows[ticker])

            def _stock_quote_client(self, *args, **kwargs):
                return None

            async def _read_stock_quote(self, client, request):
                from programgarden_finance.ls.overseas_stock.market.g3101.blocks import G3101OutBlock
                value = source.get("g3101", {}).get(request.keysymbol)
                if not isinstance(value, dict) or not {"symbol", "keysymbol", "exchcd", "price", "volume"} <= value.keys():
                    self.missing = True
                    raise ContractViolation(node.id, "Raw g3101 identity, price and volume required",
                                            "REPLAY_FIXTURE_REQUIRED")
                return G3101OutBlock.model_validate(value, strict=True)

            async def _search_market(self, *args):
                from programgarden.executor import MarketUniverseNodeExecutor
                if source.get("index") != "S&P 500" or not isinstance(source.get("stocks"), list):
                    raise ContractViolation(node.id, "Recorded S&P 500 universe required", "REPLAY_FIXTURE_REQUIRED")
                symbols = MarketUniverseNodeExecutor().parse_constituents(source["stocks"], "S&P 500")
                return await self._filter_symbols(symbols, *args)

        executor = RecordedScreener()
        output = await executor.execute(node.id, node.type, config, _ComputationContext(context))
        if executor.missing:
            raise ContractViolation(node.id, "At least one requested quote was missing", "REPLAY_FIXTURE_REQUIRED")
        return output
    raise ContractViolation(node.id, "Unsupported source parser", "REPLAY_CAPABILITY_BLOCKED")
