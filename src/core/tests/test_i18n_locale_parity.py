"""
i18n 로케일 키-parity 테스트 (ko ⇔ en).

한쪽 로케일에만 키가 존재하면 스키마 렌더 시 raw `i18n:` 텍스트가 leak 된다.
신규 노드(예: PerformanceReportNode 18키) 추가 시 한쪽 로케일 누락을 즉시 잡는다.
"""

import json
from pathlib import Path

import pytest

_LOCALE_DIR = Path(__file__).resolve().parents[1] / "programgarden_core" / "i18n" / "locales"


def _load(name: str) -> dict:
    with open(_LOCALE_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def locales():
    return _load("en.json"), _load("ko.json")


def test_full_key_parity(locales):
    """en.json 과 ko.json 의 키 집합이 완전히 동일해야 한다."""
    en, ko = locales
    only_en = set(en) - set(ko)
    only_ko = set(ko) - set(en)
    assert not only_en, f"{len(only_en)} key(s) only in en.json: {sorted(only_en)[:20]}"
    assert not only_ko, f"{len(only_ko)} key(s) only in ko.json: {sorted(only_ko)[:20]}"


def test_no_empty_values(locales):
    """빈 문자열 값은 렌더 시 사실상 leak — 금지 (_meta 제외)."""
    for locale_name, data in zip(("en", "ko"), locales):
        empties = [k for k, v in data.items() if isinstance(v, str) and not v.strip() and not k.startswith("_")]
        assert not empties, f"{locale_name}.json empty values: {empties[:20]}"


def test_performance_report_node_keys_present(locales):
    """PerformanceReportNode 18키가 양쪽 로케일에 모두 존재."""
    en, ko = locales
    expected = {
        "nodes.PerformanceReportNode.name",
        "nodes.PerformanceReportNode.description",
        "fields.PerformanceReportNode.data",
        "fields.PerformanceReportNode.data_kind",
        "fields.PerformanceReportNode.value_field",
        "fields.PerformanceReportNode.benchmark",
        "fields.PerformanceReportNode.periods_per_year",
        "fields.PerformanceReportNode.risk_free_rate",
        "fieldNames.PerformanceReportNode.data",
        "fieldNames.PerformanceReportNode.data_kind",
        "fieldNames.PerformanceReportNode.value_field",
        "fieldNames.PerformanceReportNode.benchmark",
        "fieldNames.PerformanceReportNode.periods_per_year",
        "fieldNames.PerformanceReportNode.risk_free_rate",
        "outputs.PerformanceReportNode.metrics",
        "outputs.PerformanceReportNode.report",
        "outputs.PerformanceReportNode.drawdown_series",
        "outputs.PerformanceReportNode.summary",
    }
    assert len(expected) == 18
    assert expected <= set(en), f"missing in en.json: {expected - set(en)}"
    assert expected <= set(ko), f"missing in ko.json: {expected - set(ko)}"
