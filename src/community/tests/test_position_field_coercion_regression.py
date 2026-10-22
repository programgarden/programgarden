"""
positions 기반 플러그인 **전수** 회귀 테스트 — pos_data 원값이 산술/비교에 그대로 들어가 죽는 부류.

배경 (2026-09-12 실측)
--------------------
``pos_data.get("current_price")`` / ``.get("qty")`` / ``.get("pnl_rate")`` 원값을
coerce 없이 ``*``·``<=``·``round()``·``float()`` 에 넣는 코드가 여러 플러그인에 흩어져
있었다. 'n/a'·None 이면 TypeError, 그리고 ``max_position_limit`` 은 **정상 숫자
문자열** ``'150.0'`` 로도 죽었다(``'150.0' * 100`` 이 문자열 반복이 되고 뒤따르는
``float()`` 에서 ValueError). 5차 스캔이 qty 키만 훑고 current_price 를 빼먹어 두
플러그인이 남았던 것이 이 파일의 동기다.

이 파일이 잠그는 계약 (키 종류 무관)
-------------------------------
positions 를 받는 모든 플러그인에 대해, 포지션의 **모든 숫자 필드**에 각각
``'n/a'`` / ``None`` / 숫자 문자열을 넣어 호출했을 때:

1. 예외가 나지 않는다.
2. 종목이 조용히 사라지지 않는다(passed 또는 failed 에 있고 symbol_results 에 항목이 있다).
3. 못 읽은 값을 **0 으로 지어내지 않는다**(해당 필드의 echo 가 0/0.0 이 아니다).
4. 못 읽은 값 때문에 판정/출력이 정상 실행과 달라졌다면, 그 항목에 **어느 필드가 어떤
   원값이었는지**를 담은 사유(``reason`` / ``*_reason``)가 남는다. 필드를 쓰지 않는
   플러그인이면 판정이 같아야 하고 사유는 요구하지 않는다.
5. 숫자 문자열은 그 숫자와 **완전히 같은 결과**를 낸다(판정·출력·passed 항목 모두).

플러그인 목록은 하드코딩하지 않는다 — ``plugins/`` 디렉토리에서 발견한다. 시그니처에
``positions`` 가 있거나 스키마 ``required_data`` 에 ``"positions"`` 가 있으면 대상이다.
신규 플러그인은 자동으로 포함되고, 기본 실행이 positions 루프에 도달하지 못하면(데이터
부족 등) 테스트가 **명시적으로 실패**한다 — 조용히 초록이 되지 않도록.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

import programgarden_community.plugins as plugins_pkg

# 선물 월물 코드 형식(roll_management 의 만기 파싱을 통과)이면서 다른 플러그인에는 무해한 심볼.
SYMBOL = "ESZ30"
MARKET_SYMBOL = "SPY"  # beta_hedge 기본 market_symbol / correlation_guard 의 두 번째 종목

# 실행기(AccountNode/RealAccountNode)가 싣는 모양을 따른다: qty 와 quantity 를 같이 싣는다.
BASE_POSITION: Dict[str, Any] = {
    "symbol": SYMBOL, "exchange": "NASDAQ", "market_code": "82", "close_side": "sell",
    "current_price": 150.0, "avg_price": 140.0, "pnl_rate": 7.14,
    "qty": 100, "quantity": 100,
}
# market_value 는 기본 포지션에 **넣지 않는다** — max_position_limit 의
# ``current_price × qty`` 경로(정상 숫자 문자열로도 죽던 경로)가 기본 실행에서 돌게 한다.
EXTRA_FIELDS: Dict[str, Any] = {"market_value": 15000.0}

# 논리 필드 → 실제로 주입할 키들. qty 는 두 별칭에 같이 넣는다(플러그인마다 읽는 별칭이 다르다).
FIELD_KEYS: Dict[str, Tuple[str, ...]] = {
    "current_price": ("current_price",),
    "avg_price": ("avg_price",),
    "pnl_rate": ("pnl_rate",),
    "qty": ("qty", "quantity"),
    "market_value": ("market_value",),
}
UNREADABLE_RAWS = ("n/a", None)


# ---------------------------------------------------------------------------
# 발견 (디렉토리 기반)
# ---------------------------------------------------------------------------

def _discover_position_plugins() -> List[Tuple[str, Callable[..., Any], Any]]:
    found = []
    for mod in pkgutil.iter_modules(plugins_pkg.__path__):
        if not mod.ispkg or mod.name.startswith("_"):
            continue
        module = importlib.import_module(f"{plugins_pkg.__name__}.{mod.name}")
        exported = getattr(module, "__all__", None) or dir(module)
        fn = None
        schema = None
        for name in exported:
            obj = getattr(module, name, None)
            if name.endswith("_condition") and callable(obj):
                fn = obj
            elif name.endswith("_SCHEMA"):
                schema = obj
        if fn is None:
            continue
        params = inspect.signature(fn).parameters
        by_signature = "positions" in params
        by_schema = "positions" in list(getattr(schema, "required_data", []) or [])
        if by_signature or by_schema:
            found.append((mod.name, fn, schema))
    return sorted(found, key=lambda t: t[0])


DISCOVERED = _discover_position_plugins()
PLUGIN_PARAMS = [pytest.param(fn, id=name) for name, fn, _ in DISCOVERED]


# ---------------------------------------------------------------------------
# 입력 빌더
# ---------------------------------------------------------------------------

def _bars(n: int = 130) -> List[Dict[str, Any]]:
    """모든 data 의존 플러그인이 positions 루프까지 도달하게 하는 공용 시계열.

    SYMBOL 과 MARKET_SYMBOL 두 종목, close/high/low/open/volume/date 포함.
    (beta_hedge lookback 기본 120 · var_cvar/correlation_guard 기본 60 · dynamic_stop_loss ATR 14)
    """
    rows: List[Dict[str, Any]] = []
    spy, px = 450.0, 150.0
    for i in range(n):
        move = 0.005 if i % 3 < 2 else -0.003
        spy *= (1 + move)
        px *= (1 + move * 2.0 + 0.001)
        date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
        for sym, p in ((MARKET_SYMBOL, spy), (SYMBOL, px)):
            c = round(p, 2)
            rows.append({
                "symbol": sym, "exchange": "NASDAQ", "date": date,
                "open": c, "high": round(c * 1.01, 2), "low": round(c * 0.99, 2),
                "close": c, "volume": 1000,
            })
    return rows


def _position_with(field: Optional[str] = None, raw: Any = None) -> Dict[str, Any]:
    pos = dict(BASE_POSITION)
    if field is not None:
        for key in FIELD_KEYS[field]:
            pos[key] = raw
    return pos


async def _run(fn: Callable[..., Any], positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await fn(data=_bars(), positions=positions, fields={})


# ---------------------------------------------------------------------------
# 결과 읽기
# ---------------------------------------------------------------------------

def _entry(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return next(
        (sr for sr in result.get("symbol_results", []) if isinstance(sr, dict) and sr.get("symbol") == SYMBOL),
        None,
    )


def _membership(result: Dict[str, Any]) -> str:
    if any(isinstance(p, dict) and p.get("symbol") == SYMBOL for p in result.get("passed_symbols", [])):
        return "passed"
    if any(isinstance(p, dict) and p.get("symbol") == SYMBOL for p in result.get("failed_symbols", [])):
        return "failed"
    return "absent"


def _passed_entry(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return next(
        (p for p in result.get("passed_symbols", []) if isinstance(p, dict) and p.get("symbol") == SYMBOL),
        None,
    )


def _is_reason_key(key: str) -> bool:
    return key == "reason" or key.endswith("_reason")


def _reasons(entry: Dict[str, Any]) -> List[str]:
    return [v for k, v in entry.items() if _is_reason_key(k) and isinstance(v, str)]


def _strip(entry: Dict[str, Any], injected_keys: Tuple[str, ...]) -> Dict[str, Any]:
    """사유 키와 주입 필드의 echo 를 뺀 '판정·출력' 부분."""
    return {k: v for k, v in entry.items() if not _is_reason_key(k) and k not in injected_keys}


def _fabricated_zero(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0


def _baseline(fn: Callable[..., Any], result: Dict[str, Any]) -> Dict[str, Any]:
    entry = _entry(result)
    if entry is None or _membership(result) == "absent":
        pytest.fail(
            f"{fn.__name__}: 기본 실행이 positions 루프에 도달하지 못했다 "
            f"(symbol_results={result.get('symbol_results')!r}, analysis={result.get('analysis')!r}). "
            "이 테스트가 이 플러그인을 실제로 검증하려면 _bars()/BASE_POSITION 을 확장해야 한다 — "
            "조용히 초록으로 두지 않는다."
        )
    return entry


# ---------------------------------------------------------------------------
# 테스트
# ---------------------------------------------------------------------------

def test_discovery_covers_positions_plugins():
    """디렉토리 발견이 실제로 동작하는지 — 바닥선. (목록 하드코딩이 아니라 하한만 잠근다.)"""
    names = [name for name, _, _ in DISCOVERED]
    by_schema = [name for name, _, schema in DISCOVERED
                 if "positions" in list(getattr(schema, "required_data", []) or [])]
    assert len(by_schema) >= 8, f"required_data=positions 플러그인이 8개 미만으로 발견됨: {by_schema}"
    assert len(names) >= len(by_schema)


@pytest.mark.asyncio
@pytest.mark.parametrize("fn", PLUGIN_PARAMS)
async def test_baseline_reaches_positions_loop(fn):
    """기본 입력으로 종목이 평가되고(passed/failed 어딘가에 있고) 항목이 남는다."""
    result = await _run(fn, [_position_with()])
    _baseline(fn, result)


@pytest.mark.asyncio
@pytest.mark.parametrize("fn", PLUGIN_PARAMS)
@pytest.mark.parametrize("field", sorted(FIELD_KEYS))
@pytest.mark.parametrize("raw", UNREADABLE_RAWS, ids=lambda r: repr(r))
async def test_unreadable_position_field_never_crashes_and_leaves_reason(fn, field, raw):
    injected_keys = FIELD_KEYS[field]

    base_result = await _run(fn, [_position_with()])
    base_entry = _baseline(fn, base_result)

    # 1. 예외가 나지 않는다 (여기서 TypeError/ValueError 가 나면 그게 곧 회귀다).
    result = await _run(fn, [_position_with(field, raw)])

    # 2. 종목이 조용히 사라지지 않는다.
    assert isinstance(result.get("passed_symbols"), list)
    assert isinstance(result.get("failed_symbols"), list)
    assert isinstance(result.get("symbol_results"), list)
    where = _membership(result)
    assert where != "absent", f"{fn.__name__}: {field}={raw!r} 에서 종목이 passed/failed 어디에도 없다"
    entry = _entry(result)
    assert entry is not None, f"{fn.__name__}: {field}={raw!r} 에서 symbol_results 항목이 없다"

    # 3. 못 읽은 값을 0 으로 지어내지 않는다.
    for key in injected_keys:
        assert not _fabricated_zero(entry.get(key)), (
            f"{fn.__name__}: {key}={raw!r} 를 0 으로 뭉갰다 (symbol_results={entry!r})"
        )
    passed_entry = _passed_entry(result)
    if passed_entry is not None:
        for key in injected_keys:
            assert not _fabricated_zero(passed_entry.get(key)), (
                f"{fn.__name__}: passed_symbols 의 {key} 가 0 으로 지어졌다 ({passed_entry!r})"
            )

    # 4. 판정/출력이 달라졌으면 사유가 남아야 하고, 사유는 필드명과 원값을 담아야 한다.
    changed = (
        _strip(entry, injected_keys) != _strip(base_entry, injected_keys)
        or where != _membership(base_result)
    )
    if changed:
        reasons = _reasons(entry)
        assert reasons, (
            f"{fn.__name__}: {field}={raw!r} 로 판정/출력이 달라졌는데 사유가 없다 "
            f"(base={base_entry!r}, got={entry!r})"
        )
        names_ok = any(any(k in r for k in injected_keys) for r in reasons)
        raw_ok = any(repr(raw) in r for r in reasons)
        assert names_ok and raw_ok, (
            f"{fn.__name__}: 사유에 필드명({injected_keys})과 원값({raw!r})이 없다: {reasons!r}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("fn", PLUGIN_PARAMS)
@pytest.mark.parametrize("field", sorted(FIELD_KEYS))
async def test_numeric_string_position_field_behaves_like_number(fn, field):
    """'150.0' 은 150.0 과 완전히 같아야 한다 — 문자열 반복(‘150.0150.0…’)으로 죽던 경로의 잠금."""
    numeric = EXTRA_FIELDS[field] if field in EXTRA_FIELDS else BASE_POSITION[FIELD_KEYS[field][0]]

    base_result = await _run(fn, [_position_with(field, numeric)])
    base_entry = _baseline(fn, base_result)

    result = await _run(fn, [_position_with(field, str(numeric))])

    entry = _entry(result)
    assert entry is not None, f"{fn.__name__}: {field}={str(numeric)!r} 에서 항목이 없다"
    assert entry == base_entry, (
        f"{fn.__name__}: 숫자 문자열 {field}={str(numeric)!r} 이 숫자와 다른 결과를 냈다 "
        f"(number={base_entry!r}, string={entry!r})"
    )
    assert _membership(result) == _membership(base_result)
    assert _passed_entry(result) == _passed_entry(base_result)
