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

from programgarden.executor import MarketDataNodeExecutor


def _runtime_keys(cls, method_name: str) -> Set[str]:
    """executor 메서드 안의 ``values.append({...})`` dict 리터럴 키를 뽑는다."""
    src = inspect.getsource(getattr(cls, method_name))
    tree = ast.parse(inspect.cleandoc(src) if not src.startswith("    ") else _dedent(src))

    keys: Set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "append"):
            continue
        if not (isinstance(func.value, ast.Name) and func.value.id == "values"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                keys |= {k.value for k in arg.keys if isinstance(k, ast.Constant)}
    return keys


def _dedent(src: str) -> str:
    import textwrap
    return textwrap.dedent(src)


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


# (노드 타입, executor 메서드, 검사할 출력 포트)
CASES = [
    ("OverseasStockMarketDataNode", "_fetch_overseas_stock", "value"),
    ("OverseasFuturesMarketDataNode", "_fetch_overseas_futures", "value"),
    ("KoreaStockMarketDataNode", "_fetch_korea_stock", "value"),
]


@pytest.mark.parametrize("node_type,method,port", CASES)
def test_declared_fields_match_runtime(node_type, method, port):
    runtime = _runtime_keys(MarketDataNodeExecutor, method)
    assert runtime, f"{method} 에서 런타임 키를 못 뽑았다 (테스트가 낡았다)"

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


def test_price_and_change_names_are_consistent_across_markets():
    """같은 개념을 시장마다 다른 이름으로 부르면 챗봇이 반드시 헷갈린다."""
    names = {}
    for node_type, method, port in CASES:
        declared = _declared_fields(node_type, port)
        names[node_type] = declared

    for node_type, declared in names.items():
        assert "price" in declared, f"{node_type}: 현재가는 'price' 로 통일한다 (실측 런타임 이름)"
        assert "change_pct" in declared, f"{node_type}: 등락률은 'change_pct' 로 통일한다"
        assert "current_price" not in declared, f"{node_type}: 'current_price' 는 런타임에 없다"
        assert "change_percent" not in declared, f"{node_type}: 'change_percent' 는 런타임에 없다"
