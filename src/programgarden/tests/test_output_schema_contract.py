"""출력 스키마 계약 — 노드가 **선언한 필드**와 **런타임이 실제로 내보내는 키**가 같아야 한다.

왜 필요한가 (2026-07-13 라이브에서 확진):
resolver 는 선언된 `fields` 로 **필드 존재를 정적 검증**한다. 그래서 선언이 런타임과 어긋나면
검증이 **양방향으로 다 틀린다**:

    실제 있는 필드를 바인딩  → INVALID_EXPRESSION_REF 로 **거부**   (동작하는 워크플로우를 막음)
    실제 없는 필드를 바인딩  → **통과** 시킨 뒤 런타임에 조용히 None (표에 '-' 만 찍힘)

실측: 시세 노드 선언이 `current_price` / `change_percent` 였는데 런타임은 `price` / `change_pct`.
챗봇은 선언(카탈로그)을 보고 저작하므로, 라이브러리가 **틀린 이름을 쓰도록 강제**하고 있었다.

이 테스트는 executor 의 런타임 dict 리터럴을 AST 로 뽑아 선언과 대조한다.
런타임을 바꾸면서 선언을 안 고치면(또는 그 반대) 여기서 깨진다.
"""
import ast
import inspect
from typing import Dict, Set

import pytest

from programgarden.executor import (
    AccountNodeExecutor,
    MarketDataNodeExecutor,
    MarketUniverseNodeExecutor,
    RealAccountNodeExecutor,
    RealMarketDataNodeExecutor,
    ScreenerNodeExecutor,
    SymbolQueryNodeExecutor,
    WatchlistNodeExecutor,
)


def _runtime_keys(cls, method_name: str, var: str = "values") -> Set[str]:
    """executor 메서드 안의 ``<var>.append({...})`` dict 리터럴 키를 뽑는다."""
    src = inspect.getsource(getattr(cls, method_name))
    tree = ast.parse(inspect.cleandoc(src) if not src.startswith("    ") else _dedent(src))

    keys: Set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "append"):
            continue
        if not (isinstance(func.value, ast.Name) and func.value.id == var):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                keys |= {k.value for k in arg.keys if isinstance(k, ast.Constant)}
    return keys


def _runtime_keys_of_assigned_dict(cls, method_name: str, var: str) -> Set[str]:
    """``<var>[...] = {...}`` 형태로 만들어지는 dict 리터럴 키를 뽑는다.

    실시간 시세 노드의 봉(bar)이 이 모양이다: ``ohlcv_bars[symbol] = {...}``.
    """
    src = inspect.getsource(getattr(cls, method_name))
    tree = ast.parse(_dedent(src))

    keys: Set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        for tgt in node.targets:
            if (
                isinstance(tgt, ast.Subscript)
                and isinstance(tgt.value, ast.Name)
                and tgt.value.id == var
            ):
                keys |= {
                    k.value for k in node.value.keys if isinstance(k, ast.Constant)
                }
    return keys


def _dedent(src: str) -> str:
    import textwrap
    return textwrap.dedent(src)


def _listcomp_dict_keys(cls, method_name: str, var: str) -> Set[str]:
    """``<var> = [{...} for x in ...]`` 또는 ``return {"<var>": [{...} for ...]}`` 의 키를 뽑는다.

    held_symbols 는 append 가 아니라 리스트 컴프리헨션으로 만들어진다.
    """
    src = inspect.getsource(getattr(cls, method_name))
    tree = ast.parse(_dedent(src))

    def _elt_keys(node) -> Set[str]:
        if isinstance(node, ast.ListComp) and isinstance(node.elt, ast.Dict):
            return {k.value for k in node.elt.keys if isinstance(k, ast.Constant)}
        return set()

    keys: Set[str] = set()
    for node in ast.walk(tree):
        # <var> = [{...} for ...]
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == var:
                    keys |= _elt_keys(node.value)
        # return {"<var>": [{...} for ...], ...}
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            for k, v in zip(node.value.keys, node.value.values):
                if isinstance(k, ast.Constant) and k.value == var:
                    keys |= _elt_keys(v)
    return keys


def _port_runtime_keys(producers) -> Dict[str, Set[str]]:
    """포트 하나를 만드는 **모든 갈래**의 런타임 키를 갈래별로 돌려준다.

    같은 포트인데 갈래(REST 스냅샷 / WebSocket tracker / LS / yfinance)마다 키가 다르면
    출력 모양이 시점마다 바뀐다 — 선언이 어느 쪽을 적든 반대 갈래에서 거짓말이 된다.
    """
    out: Dict[str, Set[str]] = {}
    for cls, method, var, kind in producers:
        if kind == "append":
            keys = _runtime_keys(cls, method, var)
        elif kind == "listcomp":
            keys = _listcomp_dict_keys(cls, method, var)
        elif kind == "subscript":
            keys = _runtime_keys_of_assigned_dict(cls, method, var)
        else:  # pragma: no cover
            raise AssertionError(f"unknown producer kind: {kind}")
        out[f"{cls.__name__}.{method}"] = keys
    return out


def _declared_fields(node_type: str, port: str) -> Set[str]:
    from programgarden_core import NodeTypeRegistry

    schema = NodeTypeRegistry().get_schema(node_type)
    assert schema is not None, f"{node_type} 스키마를 레지스트리에서 못 찾았다"
    for out in schema.outputs or []:
        name = out.get("name") if isinstance(out, dict) else getattr(out, "name", None)
        if name != port:
            continue
        fields = out.get("fields") if isinstance(out, dict) else getattr(out, "fields", None)
        return {
            (f.get("name") if isinstance(f, dict) else getattr(f, "name", None))
            for f in (fields or [])
        } - {None}
    pytest.fail(f"{node_type} 에 '{port}' 출력 포트 선언이 없다")


# (노드 타입, 출력 포트, [런타임을 만드는 갈래들])
#   갈래 = (executor 클래스, 메서드, 누적 변수, 추출 방식)
# 한 포트를 여러 갈래가 만들면 **전부** 적는다 — 갈래끼리 키가 어긋나는 것도 결함이다.
M = MarketDataNodeExecutor
CASES = [
    ("OverseasStockMarketDataNode", "value", [(M, "_fetch_overseas_stock", "values", "append")]),
    ("OverseasFuturesMarketDataNode", "value", [(M, "_fetch_overseas_futures", "values", "append")]),
    ("KoreaStockMarketDataNode", "value", [(M, "_fetch_korea_stock", "values", "append")]),

    # ── 종목 리스트 ──
    ("WatchlistNode", "symbols", [(WatchlistNodeExecutor, "execute", "processed_symbols", "append")]),
    ("MarketUniverseNode", "symbols", [(MarketUniverseNodeExecutor, "_fetch_index_constituents", "symbols", "append")]),
    ("ScreenerNode", "symbols", [
        (ScreenerNodeExecutor, "_filter_via_ls_overseas_stock", "prefilter", "append"),  # LS 분기
        (ScreenerNodeExecutor, "_filter_symbols", "filtered", "append"),                 # yfinance 분기
    ]),
    ("OverseasStockSymbolQueryNode", "symbols", [(SymbolQueryNodeExecutor, "_execute_stock_master", "all_symbols", "append")]),
    ("KoreaStockSymbolQueryNode", "symbols", [(SymbolQueryNodeExecutor, "_execute_korea_stock_master", "all_symbols", "append")]),
    ("OverseasFuturesSymbolQueryNode", "symbols", [(SymbolQueryNodeExecutor, "_execute_futures_master", "all_symbols", "append")]),

    # ── 계좌 (REST) ──
    ("OverseasStockAccountNode", "positions", [(AccountNodeExecutor, "_ls_overseas_stock", "positions", "append")]),
    ("KoreaStockAccountNode", "positions", [(AccountNodeExecutor, "_ls_korea_stock", "positions", "append")]),
    ("OverseasFuturesAccountNode", "positions", [(AccountNodeExecutor, "_ls_overseas_futureoption", "positions", "append")]),
    ("OverseasStockAccountNode", "held_symbols", [(AccountNodeExecutor, "_ls_overseas_stock", "held_symbols", "listcomp")]),
    ("KoreaStockAccountNode", "held_symbols", [(AccountNodeExecutor, "_ls_korea_stock", "held_symbols", "listcomp")]),
    ("OverseasFuturesAccountNode", "held_symbols", [(AccountNodeExecutor, "_ls_overseas_futureoption", "held_symbols", "append")]),

    # ── 계좌 (실시간) — REST 스냅샷 갈래와 WebSocket tracker 갈래가 같은 포트를 만든다 ──
    ("OverseasStockRealAccountNode", "positions", [
        (RealAccountNodeExecutor, "_get_overseas_stock_tracker_data", "positions", "append"),
        (RealAccountNodeExecutor, "_ls_stock_with_tracker", "serialized_positions", "append"),
    ]),
    ("KoreaStockRealAccountNode", "positions", [
        (RealAccountNodeExecutor, "_get_korea_stock_tracker_data", "positions", "append"),
        (RealAccountNodeExecutor, "_ls_korea_stock_with_tracker", "serialized_positions", "append"),
    ]),
    ("OverseasFuturesRealAccountNode", "positions", [
        (RealAccountNodeExecutor, "_get_overseas_futures_tracker_data", "positions", "append"),
        (RealAccountNodeExecutor, "_ls_futureoption_with_tracker", "serialized_positions", "append"),
    ]),
    ("OverseasStockRealAccountNode", "held_symbols", [(RealAccountNodeExecutor, "_get_overseas_stock_tracker_data", "held_symbols", "listcomp")]),
    ("KoreaStockRealAccountNode", "held_symbols", [(RealAccountNodeExecutor, "_get_korea_stock_tracker_data", "held_symbols", "listcomp")]),
    ("OverseasFuturesRealAccountNode", "held_symbols", [(RealAccountNodeExecutor, "_get_overseas_futures_tracker_data", "held_symbols", "listcomp")]),

    # ── 실시간 시세: ohlcv_data / data 는 **같은 객체**(별칭) — 봉(bar) 한 줄의 키를 검사한다 ──
    ("OverseasStockRealMarketDataNode", "ohlcv_data", [(RealMarketDataNodeExecutor, "_execute_stock", "ohlcv_bars", "subscript")]),
    ("OverseasStockRealMarketDataNode", "data", [(RealMarketDataNodeExecutor, "_execute_stock", "ohlcv_bars", "subscript")]),
    ("OverseasFuturesRealMarketDataNode", "ohlcv_data", [(RealMarketDataNodeExecutor, "_execute_futures", "ohlcv_bars", "subscript")]),
    ("OverseasFuturesRealMarketDataNode", "data", [(RealMarketDataNodeExecutor, "_execute_futures", "ohlcv_bars", "subscript")]),
    ("KoreaStockRealMarketDataNode", "ohlcv_data", [(RealMarketDataNodeExecutor, "_execute_korea_stock", "ohlcv_bars", "subscript")]),
    ("KoreaStockRealMarketDataNode", "data", [(RealMarketDataNodeExecutor, "_execute_korea_stock", "ohlcv_bars", "subscript")]),
]


@pytest.mark.parametrize(
    "node_type,port,producers",
    CASES,
    ids=[f"{n}.{p}" for n, p, _ in CASES],
)
def test_producers_of_one_port_agree(node_type, port, producers):
    """한 포트를 만드는 갈래가 여럿이면 **키 집합이 같아야** 한다.

    실측(2026-07-14): 실시간 계좌의 tracker 갈래는 `qty`/`market_code` 를, REST 스냅샷 갈래는
    `exchange`/`quantity`/`price` 를 내보냈다. 같은 포트인데 **시점마다 모양이 달랐다** —
    주문 노드는 `exchange`/`quantity` 를 읽으므로 실시간 틱이 오는 순간 조용히 깨진다.
    """
    by_branch = _port_runtime_keys(producers)
    if len(by_branch) < 2:
        pytest.skip("갈래가 하나뿐 — 대조할 상대가 없다")

    branches = list(by_branch.items())
    base_name, base_keys = branches[0]
    for other_name, other_keys in branches[1:]:
        assert base_keys == other_keys, (
            f"{node_type}.{port}: 갈래마다 키가 다르다 — "
            f"{base_name} 에만 {sorted(base_keys - other_keys)}, "
            f"{other_name} 에만 {sorted(other_keys - base_keys)}"
        )


@pytest.mark.parametrize(
    "node_type,port,producers",
    CASES,
    ids=[f"{n}.{p}" for n, p, _ in CASES],
)
def test_declared_fields_match_runtime(node_type, port, producers):
    by_branch = _port_runtime_keys(producers)
    runtime: Set[str] = set()
    for keys in by_branch.values():
        runtime |= keys
    assert runtime, (
        f"{node_type}.{port}: 런타임 키를 못 뽑았다 — executor 가 바뀌었고 "
        f"이 테스트가 낡았다 (producers={[(c.__name__, m) for c, m, _, _ in producers]})"
    )

    declared = _declared_fields(node_type, port)

    only_declared = declared - runtime   # 선언만 있고 런타임엔 없음 → 검증 통과 후 조용히 None
    only_runtime = runtime - declared    # 런타임엔 있는데 선언에 없음 → 바인딩하면 부당하게 거부

    assert not only_declared, (
        f"{node_type}: 선언에만 있는 필드 {sorted(only_declared)} — "
        f"바인딩하면 정적검증은 통과하고 런타임엔 None 이 된다(조용한 실패)."
    )
    assert not only_runtime, (
        f"{node_type}: 런타임에만 있는 필드 {sorted(only_runtime)} — "
        f"바인딩하면 INVALID_EXPRESSION_REF 로 부당하게 거부된다."
    )


MARKET_DATA_NODES = [
    "OverseasStockMarketDataNode",
    "OverseasFuturesMarketDataNode",
    "KoreaStockMarketDataNode",
]


def test_price_and_change_names_are_consistent_across_markets():
    """같은 개념을 시장마다 다른 이름으로 부르면 챗봇이 반드시 헷갈린다."""
    names = {nt: _declared_fields(nt, "value") for nt in MARKET_DATA_NODES}

    for node_type, declared in names.items():
        assert "price" in declared, f"{node_type}: 현재가는 'price' 로 통일한다 (실측 런타임 이름)"
        assert "change_pct" in declared, f"{node_type}: 등락률은 'change_pct' 로 통일한다"
        assert "current_price" not in declared, f"{node_type}: 'current_price' 는 런타임에 없다"
        assert "change_percent" not in declared, f"{node_type}: 'change_percent' 는 런타임에 없다"


# ─────────────────────────────────────────────────────────────────────────────
# 선언한 포트를 런타임이 **실제로 반환하는가**
#
# 위의 계약 검사는 dict 의 *모양*만 본다. 그런데 2026-07-14 실측에서 드러난 최대 결함은
# 모양이 아니라 **반환 자체가 없는 것**이었다:
#   계좌 노드 6종이 전부 `held_symbols` 출력 포트를 선언했는데, executor 는 그 값을 계산만
#   하고 **반환 dict 에 싣지 않았다**(죽은 지역변수). 그래서 바인딩하면 정적 검증은 통과하고
#   런타임엔 늘 비어 있었다 — "내가 보유한 종목을 실시간 감시" 워크플로우가 조용히 아무것도
#   구독하지 않았다.
# ─────────────────────────────────────────────────────────────────────────────

def _returned_keys(cls, method_name: str) -> Set[str]:
    """메서드가 반환하는 dict 의 키를 모은다.

    ``return {...}`` 직접 리터럴과 ``result = {...}`` → ``return result`` 두 형태를 모두 읽는다.
    """
    src = inspect.getsource(getattr(cls, method_name))
    tree = ast.parse(_dedent(src))

    # 이름 → dict 리터럴 키 (result: Dict[str, Any] = {...} 형태 포함)
    assigned: Dict[str, Set[str]] = {}
    for node in ast.walk(tree):
        target = value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and isinstance(value, ast.Dict):
            assigned.setdefault(target.id, set()).update(
                k.value for k in value.keys if isinstance(k, ast.Constant)
            )

    keys: Set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        if isinstance(node.value, ast.Dict):
            keys |= {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
        elif isinstance(node.value, ast.Name):
            keys |= assigned.get(node.value.id, set())

    # 실시간 노드는 선언 포트를 **return 이 아니라 콜백에서 set_output** 으로 방출한다
    # (틱 도착 시). pending 시엔 데이터형 포트를 안 내야 하류가 빈 행을 그리지 않으므로
    # (2026-07-14 결함2-pending), 그 포트들은 return 에 없다. context.set_output(node_id,
    # "PORT", ...) 로 **자기 노드에** 세팅하는 포트도 방출로 인정한다(_input_<id> 는 제외).
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr == "set_output"):
            continue
        if len(node.args) < 2:
            continue
        tgt, port = node.args[0], node.args[1]
        # 첫 인자가 node_id(자기 노드)일 때만 — _input_<id>(입력) 은 제외
        if isinstance(tgt, ast.Name) and tgt.id == "node_id" and isinstance(port, ast.Constant):
            keys.add(port.value)
    return keys


# (executor, 노드 출력 dict 을 반환하는 메서드, 반드시 실려야 하는 키)
RETURN_CASES = [
    (AccountNodeExecutor, "_ls_overseas_stock", {"held_symbols", "positions", "balance"}),
    (AccountNodeExecutor, "_ls_korea_stock", {"held_symbols", "positions", "balance"}),
    (AccountNodeExecutor, "_ls_overseas_futureoption", {"held_symbols", "positions", "balance"}),
    (AccountNodeExecutor, "_empty_result", {"held_symbols", "positions", "balance"}),
    (RealAccountNodeExecutor, "_get_overseas_stock_tracker_data", {"held_symbols", "positions", "balance", "open_orders"}),
    (RealAccountNodeExecutor, "_get_overseas_futures_tracker_data", {"held_symbols", "positions", "balance", "open_orders"}),
    (RealAccountNodeExecutor, "_get_korea_stock_tracker_data", {"held_symbols", "positions", "balance", "open_orders"}),
    (RealAccountNodeExecutor, "_empty_result", {"held_symbols", "positions", "balance"}),
    (ScreenerNodeExecutor, "execute", {"symbols", "count"}),
    (SymbolQueryNodeExecutor, "_execute_stock_master", {"symbols", "count"}),
    (SymbolQueryNodeExecutor, "_execute_korea_stock_master", {"symbols", "count"}),
    (SymbolQueryNodeExecutor, "_execute_futures_master", {"symbols", "count"}),
    (RealMarketDataNodeExecutor, "_execute_stock", {"symbols", "ohlcv_data", "data"}),
    (RealMarketDataNodeExecutor, "_execute_futures", {"symbols", "ohlcv_data", "data"}),
    (RealMarketDataNodeExecutor, "_execute_korea_stock", {"symbols", "ohlcv_data", "data"}),
]


@pytest.mark.parametrize(
    "cls,method,required",
    RETURN_CASES,
    ids=[f"{c.__name__}.{m}" for c, m, _ in RETURN_CASES],
)
def test_declared_ports_are_actually_returned(cls, method, required):
    returned = _returned_keys(cls, method)
    missing = required - returned
    assert not missing, (
        f"{cls.__name__}.{method}: 선언된 출력 포트 {sorted(missing)} 를 **반환하지 않는다**. "
        f"바인딩하면 정적 검증은 통과하고 런타임엔 값이 없다(조용한 실패). "
        f"실제 반환 키: {sorted(returned)}"
    )
