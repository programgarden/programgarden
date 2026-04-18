"""Unit tests for MarketStatusNode + JIF constants/derivations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Set

import pytest
from pydantic import ValidationError

from programgarden_core.nodes.market_status import (
    JANGUBUN_TO_MARKET,
    JSTATUS_EXTENDED_CLOSED,
    JSTATUS_EXTENDED_OPEN,
    JSTATUS_REGULAR_CLOSED,
    JSTATUS_REGULAR_OPEN,
    MARKET_TO_JANGUBUN,
    MarketStatusNode,
    SUPPORTED_MARKETS,
    is_extended_open,
    is_open,
    is_regular_open,
)


# ---------------------------------------------------------------------------
# Constant mapping coverage
# ---------------------------------------------------------------------------


class TestJangubunMapping:
    def test_twelve_jangubun_codes_covered(self):
        # 12 markets only — matches the JIF-supported universe.
        expected = {"1", "2", "5", "6", "8", "9", "A", "B", "C", "D", "E", "F"}
        assert set(JANGUBUN_TO_MARKET.keys()) == expected

    def test_market_to_jangubun_is_inverse(self):
        assert all(
            MARKET_TO_JANGUBUN[market] == code
            for code, market in JANGUBUN_TO_MARKET.items()
        )

    def test_supported_markets_matches_mapping(self):
        assert set(SUPPORTED_MARKETS) == set(JANGUBUN_TO_MARKET.values())
        assert len(SUPPORTED_MARKETS) == 12

    @pytest.mark.parametrize(
        "jangubun,expected",
        [
            ("1", "KOSPI"),
            ("2", "KOSDAQ"),
            ("5", "KRX_FUTURES"),
            ("6", "NXT"),
            ("8", "KRX_NIGHT"),
            ("9", "US"),
            ("A", "CN_AM"),
            ("B", "CN_PM"),
            ("C", "HK_AM"),
            ("D", "HK_PM"),
            ("E", "JP_AM"),
            ("F", "JP_PM"),
        ],
    )
    def test_jangubun_translation(self, jangubun: str, expected: str):
        assert JANGUBUN_TO_MARKET[jangubun] == expected


class TestJStatusDerivation:
    def test_disjoint_regular_sets(self):
        # A code cannot be both regular-open and regular-closed.
        assert JSTATUS_REGULAR_OPEN.isdisjoint(JSTATUS_REGULAR_CLOSED)

    def test_disjoint_extended_sets(self):
        assert JSTATUS_EXTENDED_OPEN.isdisjoint(JSTATUS_EXTENDED_CLOSED)

    def test_regular_open_is_subset_of_extended_open(self):
        # Any regular-hours session is automatically an extended-hours session.
        assert JSTATUS_REGULAR_OPEN.issubset(JSTATUS_EXTENDED_OPEN)

    @pytest.mark.parametrize(
        "jstatus", sorted(JSTATUS_REGULAR_OPEN)
    )
    def test_is_regular_open_positive(self, jstatus: str):
        assert is_regular_open(jstatus) is True
        assert is_open(jstatus, include_extended=False) is True

    @pytest.mark.parametrize(
        "jstatus", sorted(JSTATUS_REGULAR_CLOSED)
    )
    def test_is_regular_open_negative(self, jstatus: str):
        assert is_regular_open(jstatus) is False
        assert is_open(jstatus, include_extended=False) is False

    @pytest.mark.parametrize(
        "jstatus", sorted(JSTATUS_EXTENDED_OPEN)
    )
    def test_is_extended_open_positive(self, jstatus: str):
        assert is_extended_open(jstatus) is True
        assert is_open(jstatus, include_extended=True) is True

    def test_total_code_coverage(self):
        # Plan target: 40+ status codes across regular + extended sets.
        total = JSTATUS_REGULAR_OPEN | JSTATUS_REGULAR_CLOSED
        total |= JSTATUS_EXTENDED_OPEN | JSTATUS_EXTENDED_CLOSED
        assert len(total) >= 40, (
            f"Expected ≥40 unique jstatus codes across all sets, got {len(total)}"
        )

    def test_unknown_jstatus_is_closed(self):
        # Unknown codes MUST default to closed for safety.
        assert is_regular_open("99") is False
        assert is_extended_open("99") is False
        assert is_open("99", include_extended=False) is False
        assert is_open("99", include_extended=True) is False


# ---------------------------------------------------------------------------
# Node configuration & Literal validation
# ---------------------------------------------------------------------------


class TestMarketStatusNodeConfig:
    def test_defaults(self):
        node = MarketStatusNode(id="ms-1")
        assert node.markets == []
        assert node.stay_connected is True
        assert node.include_extended_hours is False

    def test_is_tool_enabled(self):
        assert MarketStatusNode.is_tool_enabled() is True

    @pytest.mark.parametrize(
        "markets",
        [
            ["US"],
            ["KOSPI", "KOSDAQ"],
            ["HK_AM", "HK_PM"],
            ["CN_AM", "CN_PM", "JP_AM", "JP_PM"],
            ["KOSPI", "KOSDAQ", "KRX_FUTURES", "NXT", "KRX_NIGHT",
             "US", "CN_AM", "CN_PM", "HK_AM", "HK_PM", "JP_AM", "JP_PM"],
            [],
        ],
    )
    def test_valid_markets(self, markets):
        node = MarketStatusNode(id="ms-1", markets=markets)
        assert node.markets == markets

    @pytest.mark.parametrize(
        "bad_value",
        ["CME", "FTSE", "SGX", "HKEX_FUTURES", "NASDAQ", "DAX", "TSE"],
    )
    def test_unsupported_market_raises(self, bad_value: str):
        with pytest.raises(ValidationError):
            MarketStatusNode(id="ms-1", markets=[bad_value])

    def test_mixed_valid_invalid_raises(self):
        with pytest.raises(ValidationError):
            MarketStatusNode(id="ms-1", markets=["US", "CME"])


class TestOutputPorts:
    def test_port_names_cover_all_convenience_booleans(self):
        node = MarketStatusNode(id="ms-1")
        port_names = {port.name for port in node._outputs}
        expected = {
            "statuses",
            "event",
            "us_is_open",
            "kospi_is_open",
            "kosdaq_is_open",
            "krx_futures_is_open",
            "hk_is_open",
            "cn_is_open",
            "jp_is_open",
        }
        assert expected.issubset(port_names)

    def test_all_ports_have_i18n_description(self):
        node = MarketStatusNode(id="ms-1")
        for port in node._outputs:
            assert port.description.startswith("i18n:"), (
                f"Port {port.name} must use i18n key"
            )


class TestFieldSchema:
    def test_field_schema_includes_all_fields(self):
        schema = MarketStatusNode.get_field_schema()
        assert set(schema.keys()) == {
            "markets",
            "stay_connected",
            "include_extended_hours",
        }

    def test_markets_schema_multi_select(self):
        schema = MarketStatusNode.get_field_schema()
        markets_schema = schema["markets"]
        assert markets_schema.ui_options is not None
        assert set(markets_schema.ui_options["options"]) == set(SUPPORTED_MARKETS)
        assert markets_schema.ui_options.get("multiple") is True


# ---------------------------------------------------------------------------
# i18n keys
# ---------------------------------------------------------------------------


CORE_ROOT = Path(__file__).resolve().parent.parent / "programgarden_core"


def _load_locale(locale: str) -> Dict[str, str]:
    path = CORE_ROOT / "i18n" / "locales" / f"{locale}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _market_status_keys(data: Dict[str, str]) -> Set[str]:
    return {k for k in data.keys() if "MarketStatusNode" in k}


class TestI18nKeys:
    def test_ko_en_have_same_market_status_keys(self):
        ko = _load_locale("ko")
        en = _load_locale("en")
        ko_keys = _market_status_keys(ko)
        en_keys = _market_status_keys(en)
        assert ko_keys == en_keys, (
            f"ko/en MarketStatusNode keys differ: "
            f"only in ko={ko_keys - en_keys}, only in en={en_keys - ko_keys}"
        )

    def test_ko_en_have_required_key_count(self):
        ko = _load_locale("ko")
        en = _load_locale("en")
        ko_keys = _market_status_keys(ko)
        assert len(ko_keys) >= 18, (
            f"Expected ≥18 MarketStatusNode i18n keys, got {len(ko_keys)}"
        )
        assert len(ko_keys) == len(_market_status_keys(en))

    @pytest.mark.parametrize(
        "key",
        [
            "nodes.MarketStatusNode.name",
            "nodes.MarketStatusNode.description",
            "fields.MarketStatusNode.markets",
            "fields.MarketStatusNode.markets.help_text",
            "fields.MarketStatusNode.stay_connected",
            "fields.MarketStatusNode.stay_connected.help_text",
            "fields.MarketStatusNode.include_extended_hours",
            "fields.MarketStatusNode.include_extended_hours.help_text",
            "fieldNames.MarketStatusNode.markets",
            "fieldNames.MarketStatusNode.stay_connected",
            "fieldNames.MarketStatusNode.include_extended_hours",
            "outputs.MarketStatusNode.statuses",
            "outputs.MarketStatusNode.event",
            "outputs.MarketStatusNode.us_is_open",
            "outputs.MarketStatusNode.kospi_is_open",
            "outputs.MarketStatusNode.kosdaq_is_open",
            "outputs.MarketStatusNode.krx_futures_is_open",
            "outputs.MarketStatusNode.hk_is_open",
            "outputs.MarketStatusNode.cn_is_open",
            "outputs.MarketStatusNode.jp_is_open",
        ],
    )
    def test_required_key_present_both_locales(self, key: str):
        ko = _load_locale("ko")
        en = _load_locale("en")
        assert key in ko, f"Missing in ko.json: {key}"
        assert key in en, f"Missing in en.json: {key}"
        assert ko[key].strip()
        assert en[key].strip()


# ---------------------------------------------------------------------------
# Finance constants symmetry — verify core derivations mirror finance data
# ---------------------------------------------------------------------------


class TestFinanceSymmetry:
    def test_finance_constants_import_same_jangubun(self):
        # The finance layer maintains the canonical raw LS codes; the core
        # layer must mirror them so executors can cross-reference.
        try:
            from programgarden_finance.ls.common.real.JIF.constants import (
                JANGUBUN_LABELS,
            )
        except ImportError:
            pytest.skip("programgarden_finance not installed in test env")
        for code, info in JANGUBUN_LABELS.items():
            assert code in JANGUBUN_TO_MARKET, (
                f"Finance jangubun {code} missing from core JANGUBUN_TO_MARKET"
            )
            assert JANGUBUN_TO_MARKET[code] == info["market"], (
                f"Core/finance market key mismatch for jangubun {code}"
            )

    def test_finance_labels_are_english_only(self):
        # Plan v4 decision: constants.py labels are English-only so the AI/
        # logs layer has a single stable technical label. Reject any Hangul
        # leaking into finance constants.
        try:
            from programgarden_finance.ls.common.real.JIF.constants import (
                JANGUBUN_LABELS,
                JSTATUS_LABELS,
            )
        except ImportError:
            pytest.skip("programgarden_finance not installed in test env")
        hangul = re.compile(r"[가-힣]")
        for code, info in JANGUBUN_LABELS.items():
            label = info["label"]
            assert not hangul.search(label), (
                f"Hangul found in JANGUBUN_LABELS[{code}].label: {label!r}"
            )
        for code, info in JSTATUS_LABELS.items():
            label = info["label"]
            assert not hangul.search(label), (
                f"Hangul found in JSTATUS_LABELS[{code}].label: {label!r}"
            )
