"""Strict o3105 detail projection shared by live nodes and offline replay.

Request fields follow finance/example/overseas_futureoption/run_o3105.py.
No current quote is needed to read valid static contract metadata.
"""
from datetime import UTC, datetime
import math

from programgarden_finance.ls.overseas_futureoption.market.o3105.blocks import O3105InBlock


TEXT_FIELDS = {
    "symbol_name": "SymbolNm", "underlying_code": "BscGdsCd", "currency": "CrncyCd",
    "trade_status_code": "DlPsblCd",
}
DATE_FIELDS = {
    "maturity_date": "MtrtDt", "last_trading_date": "FnlDlDt", "first_notice_date": "FstTrsfrDt",
    "master_received_date": "ApplDate", "korea_start_date": "DlDt",
    "local_start_date": "OvsStrDay", "local_end_date": "OvsEndDay",
}
TIME_FIELDS = {"korea_start_time": "DlStrtTm", "korea_end_time": "DlEndTm",
               "local_start_time": "OvsStrTm", "local_end_time": "OvsEndTm"}
NUMBER_FIELDS = {"initial_margin": "OpngMgn", "maintenance_margin": "MntncMgn",
                 "tick_size": "UntPrc", "tick_value": "MnChgAmt"}


class FuturesContractEvidenceError(ValueError):
    """Safe-to-display contract evidence error without broker payloads or secrets."""


def build_contract_info_request(config):
    identity = config.get("symbol")
    if not isinstance(identity, dict) or not all(
        isinstance(identity.get(key), str) and identity[key].strip() for key in ("symbol", "exchange")
    ):
        raise FuturesContractEvidenceError("An exact futures contract symbol and exchange are required")
    return O3105InBlock(symbol=identity["symbol"].strip())


def _text(block, field):
    value = getattr(block, field) if field in block.model_fields_set else None
    return value.strip() or None if isinstance(value, str) else None


def _date_or_time(block, field, *, date):
    value = _text(block, field)
    if not value or len(value) != (8 if date else 6) or not value.isascii() or not value.isdigit():
        return None
    try:
        parsed = datetime.strptime(value, "%Y%m%d" if date else "%H%M%S")
    except ValueError:
        return None
    return parsed.date().isoformat() if date else parsed.time().isoformat()


def read_contract_info(response, config, *, observed_at=None):
    request = build_contract_info_request(config)
    if response.status_code != 200 or response.error_msg or response.rsp_cd != "00000" or response.block is None:
        raise FuturesContractEvidenceError("o3105 did not return a successful contract detail response")
    block = response.block
    if not {"Symbol", "ExchCd"} <= block.model_fields_set or block.Symbol.strip() != request.symbol:
        raise FuturesContractEvidenceError("o3105 contract identity is absent or mismatched")
    exchange = block.ExchCd.strip()
    if exchange != config["symbol"]["exchange"].strip():
        raise FuturesContractEvidenceError("o3105 exchange identity is absent or mismatched")
    now = observed_at or datetime.now(UTC)
    if now.tzinfo is None:
        raise FuturesContractEvidenceError("Contract observation requires a timezone-aware timestamp")
    value = {"symbol": block.Symbol.strip(), "exchange": exchange,
             "source_tr": "o3105", "observed_at": now.astimezone(UTC).isoformat()}
    value.update({name: _text(block, field) for name, field in TEXT_FIELDS.items()})
    for fields, is_date in ((DATE_FIELDS, True), (TIME_FIELDS, False)):
        value.update({name: _date_or_time(block, field, date=is_date) for name, field in fields.items()})
    for name, field in NUMBER_FIELDS.items():
        observed = getattr(block, field) if field in block.model_fields_set else None
        valid = type(observed) in (int, float) and math.isfinite(observed) and observed >= 0
        if name in ("tick_size", "tick_value"):
            valid = valid and observed > 0
        value[name] = float(observed) if valid else None
    return {"value": value, "verified": True, "missing_fields": sorted(k for k, v in value.items() if v is None), "error": None}


def synthetic_contract_info(config, *, observed_at=None):
    """Legacy deep-check shape only; replay instead requires raw recorded evidence."""
    from programgarden_finance.ls.overseas_futureoption.market.o3105.blocks import O3105OutBlock, O3105Response
    request = build_contract_info_request(config)
    response = O3105Response(status_code=200, rsp_cd="00000", rsp_msg="Synthetic deep-check identity", block=O3105OutBlock(
        Symbol=request.symbol, ExchCd=config["symbol"]["exchange"].strip(),
    ))
    # Unknown dates/margins intentionally stay unknown; do not manufacture rollover permission.
    return read_contract_info(response, config, observed_at=observed_at)
