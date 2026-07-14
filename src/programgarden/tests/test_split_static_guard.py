"""SplitNode 정적가드 — 다중 배열 상류 + array 무바인딩을 빌드 시점에 잡는다.

2026-07-14 결함1 확장: 엔진이 런타임에 raise 하던 "계좌→Split 무바인딩(모호)"을
resolver 가 build-time error 로 승격한다. 챗봇 self-correct 루프가 실행 전에 본다.
코퍼스(예제 102 + Supabase workflow_examples + 저장 DSL) 오탐 0 재검증 완료.
"""
import copy
import pytest

from programgarden import WorkflowExecutor


def _cred():
    return [{
        "credential_id": "c", "type": "broker_ls_overseas_stock",
        "data": [
            {"key": "appkey", "value": "x", "type": "password", "label": "App Key"},
            {"key": "appsecret", "value": "y", "type": "password", "label": "App Secret"},
        ],
    }]


ACCOUNT_SPLIT = {
    "id": "acct-split-test",
    "name": "Account Split Test",
    "version": "1.0.0",
    "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c"},
        {"id": "acct", "type": "OverseasStockRealAccountNode"},
        {"id": "split", "type": "SplitNode"},
        {"id": "rm", "type": "OverseasStockRealMarketDataNode", "symbol": "{{ nodes.split.item }}"},
        {"id": "agg", "type": "AggregateNode", "mode": "collect"},
    ],
    "edges": [
        {"from": "start", "to": "broker"}, {"from": "broker", "to": "acct"},
        {"from": "acct", "to": "split"}, {"from": "split", "to": "rm"}, {"from": "rm", "to": "agg"},
    ],
    "credentials": _cred(),
}


def _split_array_errors(wf):
    r = WorkflowExecutor().validate(wf)
    return [str(e) for e in r.errors
            if "SplitNode" in str(e) and ("array" in str(e) or "배열" in str(e))]


def test_account_split_without_binding_is_flagged():
    """다중 배열 상류(계좌)인데 array 바인딩이 없으면 build-time error."""
    errs = _split_array_errors(copy.deepcopy(ACCOUNT_SPLIT))
    assert errs, "계좌→Split 무바인딩이 정적으로 안 걸렸다(런타임까지 새면 안 됨)"


def test_account_split_with_binding_is_not_flagged():
    """array 를 명시 바인딩하면 통과(오탐 아님)."""
    wf = copy.deepcopy(ACCOUNT_SPLIT)
    for n in wf["nodes"]:
        if n["id"] == "split":
            n["array"] = "{{ nodes.acct.held_symbols }}"
    assert _split_array_errors(wf) == [], f"바인딩된 계좌→Split 를 오탐 반려: {_split_array_errors(wf)}"


def _rt_symbol_errors(wf):
    r = WorkflowExecutor().validate(wf)
    return [str(e) for e in r.errors
            if "RealMarketDataNode" in str(e) and ("symbol" in str(e) or "종목별" in str(e))]


def test_split_realtime_market_without_symbol_is_flagged():
    """계좌→Split→RealMarketData 인데 symbol 미바인딩 → Split fan-out 이 장식 → build-time error."""
    wf = copy.deepcopy(ACCOUNT_SPLIT)
    # array 바인딩은 채워 (2) 가드는 통과시키고, rm 의 symbol 만 제거해 (3) 가드만 격리
    for n in wf["nodes"]:
        if n["id"] == "split":
            n["array"] = "{{ nodes.acct.held_symbols }}"
        if n["id"] == "rm":
            n.pop("symbol", None)
    assert _rt_symbol_errors(wf), "split→RealMarketData 무 symbol 바인딩이 정적으로 안 걸렸다"


def test_split_realtime_market_with_symbol_is_not_flagged():
    """symbol 바인딩되면 통과(오탐 아님)."""
    wf = copy.deepcopy(ACCOUNT_SPLIT)
    for n in wf["nodes"]:
        if n["id"] == "split":
            n["array"] = "{{ nodes.acct.held_symbols }}"
    assert _rt_symbol_errors(wf) == [], f"symbol 바인딩된 흐름을 오탐 반려: {_rt_symbol_errors(wf)}"


def test_realtime_market_without_split_is_not_flagged():
    """Split 없이 계좌→RealMarketData 자동 iterate 는 symbol 없어도 정상(폴백) → 무플래그."""
    wf = {
        "id": "acct-rm-autoiter", "name": "x", "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c"},
            {"id": "acct", "type": "OverseasStockRealAccountNode"},
            {"id": "rm", "type": "OverseasStockRealMarketDataNode"},
        ],
        "edges": [
            {"from": "start", "to": "broker"}, {"from": "broker", "to": "acct"},
            {"from": "acct", "to": "rm"},
        ],
        "credentials": _cred(),
    }
    assert _rt_symbol_errors(wf) == [], f"Split 없는 자동 iterate 를 오탐 반려: {_rt_symbol_errors(wf)}"


def test_single_array_upstream_without_binding_is_not_flagged():
    """단일 배열 상류(Watchlist→symbols)는 바인딩 없이도 통과(무회귀)."""
    wf = {
        "id": "wl-split-test",
        "name": "Watchlist Split Test",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c"},
            {"id": "wl", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
            {"id": "split", "type": "SplitNode"},
            {"id": "fund", "type": "OverseasStockFundamentalNode", "symbol": "{{ nodes.split.item }}"},
            {"id": "agg", "type": "AggregateNode", "mode": "collect"},
        ],
        "edges": [
            {"from": "start", "to": "broker"}, {"from": "broker", "to": "wl"},
            {"from": "wl", "to": "split"}, {"from": "split", "to": "fund"}, {"from": "fund", "to": "agg"},
        ],
        "credentials": _cred(),
    }
    assert _split_array_errors(wf) == [], f"Watchlist→Split 를 오탐 반려: {_split_array_errors(wf)}"
