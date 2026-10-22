"""Order and account TR rate defaults never exceed the LS guide (SPEC K4).

The fixture copies ``transactionPerSec`` for the order/account TRs used by the
board order window from the LS OpenAPI TR guide (version in the fixture).
COSAT00400 used to default to 10/s while the guide says 1/s.
"""

import importlib
import json
from pathlib import Path

import pytest

import programgarden_finance.ls as ls_root

FIXTURE = json.loads((Path(__file__).parent / "fixtures/ls_guide_order_account_rates.json").read_text())
LS_ROOT = Path(ls_root.__file__).parent


def default_options(code):
    blocks, = [p for p in LS_ROOT.rglob(f"{code}/blocks.py")]
    module_name = "programgarden_finance.ls." + ".".join(blocks.relative_to(LS_ROOT).with_suffix("").parts)
    module = importlib.import_module(module_name)
    return getattr(module, f"{code}Request").model_fields["options"].default


@pytest.mark.parametrize("row", FIXTURE["transactions"], ids=[r["code"] for r in FIXTURE["transactions"]])
def test_default_rate_within_guide(row):
    options = default_options(row["code"])
    assert options.on_rate_limit == "wait"
    assert options.rate_limit_key == row["code"]
    assert options.rate_limit_count / options.rate_limit_seconds <= row["transactionPerSec"]


def test_cosat00400_matches_guide_exactly():
    options = default_options("COSAT00400")
    assert (options.rate_limit_count, options.rate_limit_seconds) == (1, 1)


def test_fixture_is_scoped_to_the_board_order_trs():
    codes = {row["code"] for row in FIXTURE["transactions"]}
    assert {"COSAT00301", "COSAT00311", "COSAT00400", "CSPAT00601", "CIDBT00100",
            "CSPAQ13700", "COSAQ00102", "COSOQ00201", "CIDBQ01500", "CIDBQ01800",
            "CIDBQ02400"} <= codes
    assert FIXTURE["guide_version"] == "20261012053652748"
