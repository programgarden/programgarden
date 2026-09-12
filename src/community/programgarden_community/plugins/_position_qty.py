"""
Shared position-quantity helpers for the position/risk plugins (stdlib only).

Leading-underscore module name → not a plugin package; ``register_all_plugins``
imports concrete ``<name>/__init__.py`` packages by an explicit list, so this
module is never registered as a plugin (same convention as ``_ta_common.py``).

왜 공용인가
----------
청산·축소 수량을 만드는 플러그인들이 **같은 식을 각자 복사**해 갖고 있었고, 그
식이 동시에 두 가지로 깨졌다:

1. ``int(qty)`` 절단 — LS 는 해외주식 소수점 주식을 지원한다(출처: 오너 진술
   2026-09-12). 0.532주 포지션에서 ``int(0.532) = 0`` 이라 수량이 0 으로 접히고,
   포지션 금액(``current_price * int(qty)``)도 0.0 으로 보고된다.
2. 바닥 올림 ``max(1, ...)`` — 0 으로 접힌 값을 1 로 되살려 **보유량을 초과하는
   1주 매도**를 실어 보낸다(0.532 보유 → 1주 매도).

그래서 절단·바닥올림을 없앤 계산을 여기 한 곳에 두고, 각 플러그인은 이 함수만
쓴다.

정수화는 여기서 하지 않는다
--------------------------
브로커 송신부 ``NewOrderNodeExecutor._normalize_order``
(``programgarden/executor.py``) 가 이미 명시적 규약을 갖고 있다: 정수부만
주문하고 잘린 잔량을 ``fractional_remainder`` 로 결과에 남기며, 정수부가 0 인
소수-only 주문은 ``EmptyOrderReason.FRACTIONAL_ONLY`` 로 사유를 밝힌다.
플러그인이 먼저 잘라 버리면 그 진단이 통째로 사라지므로 원값을 넘긴다.

Decimal 을 그대로 싣지 않는 이유는 ``passed_symbols`` 가 JSON 직렬화/템플릿
바인딩을 거치기 때문이다. 정수로 떨어지는 값은 ``int`` 로 돌려 직렬화 모양을
유지한다.

No-silent-failure 규약
---------------------
'값이 0' 과 '값을 못 읽음' 을 구분한다. 못 읽으면 ``None`` 을 돌려주고, 호출부는
수량을 지어내는 대신 **왜 못 실었는지**를 결과에 남긴다
("안 보낸 필드는 안 보냈다고 표시" 규약).
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Optional, Union

Qty = Union[int, float]

__all__ = [
    "Qty",
    "coerce_qty",
    "coerce_number",
    "preserve_qty",
    "half_position_qty",
    "partial_sell_qty",
    "below_broker_lot",
]


def coerce_qty(value: Any) -> Optional[float]:
    """수량/비율 값을 유한 float 로 읽는다. 읽을 수 없으면 ``None`` ('0' 과 구분).

    ``Decimal`` 을 따로 받는 이유: HWM 트래커의 ``position_qty`` 와 strategy_state
    복원값이 ``Decimal`` 이고(``workflow_risk_tracker._to_qty_decimal`` /
    ``_deserialize_state_value``), ``Decimal * float`` 는 ``TypeError`` 다.
    """
    if isinstance(value, Decimal):
        return float(value) if value.is_finite() else None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def coerce_number(value: Any) -> Optional[float]:
    """가격·수익률·금액 등 **수량이 아닌** 숫자 필드를 유한 float 로 읽는다. 못 읽으면 ``None``.

    규약은 ``coerce_qty`` 와 같다(Decimal 허용, NaN/inf/문자열 쓰레기/None → ``None``,
    '0' 과 '못 읽음' 을 구분). 이름을 따로 두는 이유는 호출부에서 '이 값은 수량이
    아니라 가격/비율' 임을 드러내기 위해서다 — 수량 규약(절단 금지·정수화는 송신부)이
    가격에까지 적용되는 것으로 오독되지 않게 한다.

    숫자 문자열('150.0')은 그 숫자로 읽는다. 문자열 원값을 그대로 곱셈에 넣으면
    ``'150.0' * 100`` 이 문자열 반복이 되어 뒤따르는 ``float()`` 에서 ValueError 로
    죽는다 — 정상값으로도 죽는 경로였다(max_position_limit, 관측 2026-09-12).
    """
    return coerce_qty(value)


def preserve_qty(value: Any) -> Optional[Qty]:
    """수량을 절단 없이 정규화한다 — 정수면 ``int``, 소수면 ``float``, 못 읽으면 ``None``.

    부호·0 은 거르지 않는다(그건 호출부의 도메인 판단이다).
    """
    f = coerce_qty(value)
    if f is None:
        return None
    return int(f) if f.is_integer() else f


def half_position_qty(value: Any) -> Optional[Qty]:
    """보유 수량의 **절반**을 절단·바닥올림 없이 계산한다. 읽을 수 없거나 0 이하면 ``None``.

    구 코드는 ``max(1, int(qty) // 2)`` 였다. 0.532주 보유에서
    ``int(0.532) // 2 = 0`` → ``max(1, 0) = 1`` 이라 보유량을 초과한 1주 매도가
    나갔고, 1주 보유에서도 1 이 나와 '절반 축소' 가 사실상 전량 매도가 됐다.

    상한은 ``min(half, qty)`` 로 명시해 어떤 입력에서도 보유량을 넘지 않게 한다.
    """
    qty = coerce_qty(value)
    if qty is None or qty <= 0:
        return None
    half = min(qty / 2, qty)  # 상한: 보유량 초과 금지
    return int(half) if half.is_integer() else half


def partial_sell_qty(
    original_qty: Any, sell_pct: Any, held_qty: Any
) -> Optional[Qty]:
    """부분 익절 수량(기준 수량 × 비율, 보유량 상한)을 절단 없이 계산한다.

    읽을 수 없으면 ``None``, 계산 결과가 0 이하면 ``0`` — 둘은 다른 사건이다.

    구 코드는 ``int(original_qty * sell_pct / 100)`` 이라 소수 포지션에서 수량이
    0 으로 잘렸고(0.532주 × 50% = 0.266 → 0), 그 값이 ``if sell_quantity > 0``
    게이트에 걸려 단계가 통째로 건너뛰어졌다.
    """
    base = coerce_qty(original_qty)
    pct = coerce_qty(sell_pct)
    held = coerce_qty(held_qty)
    if base is None or pct is None or held is None:
        return None

    qty = min(base * pct / 100, held)  # 보유량 초과 방지
    if qty <= 0:
        return 0
    return int(qty) if float(qty).is_integer() else qty


def below_broker_lot(value: Any) -> bool:
    """이 수량이 **주문으로 이어지지 못하는** 구간(0 < qty < 1)인가.

    주문 송신부 ``NewOrderNodeExecutor._normalize_order``
    (``programgarden/executor.py``) 는 ``quantity = int(raw_quantity)`` 로 정수부만
    주문하고, 정수부가 0 이면 ``return None`` 으로 **주문 자체를 만들지 않는다**
    (관측: executor.py 의 해당 블록 — ``if quantity <= 0: ... return None``,
    2026-09-12). 즉 0 < qty < 1 인 수량은 조용히 아무 일도 일으키지 않는다.

    이 함수는 그 사실을 **판정만** 한다 — 수량을 바꾸거나 올림하지 않는다. 호출부는
    이 값이 True 일 때 결과에 사유를 남겨 '조용한 무동작' 을 드러낸다.

    읽을 수 없는 값(``None``)은 여기서 False 다 — 그건 별개의 사건이고 호출부가
    이미 '수량을 못 읽었다' 사유로 따로 보고한다.
    """
    f = coerce_qty(value)
    if f is None:
        return False
    return 0 < f < 1
