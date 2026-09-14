"""체결 재조정 — 좁은 확인 창에서 놓친 체결을 뒤늦게 원장에 맞춰 넣는다.

## 왜 필요한가

로트(`workflow_position_lots`)와 체결내역(`trade_history`)은 **체결 이벤트로만** 생긴다
(`WorkflowPositionTracker._process_fill_internal` 이 유일한 입구). 그런데 주문 접수 직후의
인라인 확인은 4회 × 2초, 실질 6초밖에 열리지 않는다. 지정가가 몇 분 뒤에 체결되면 그
사실이 원장에 **영영 도착하지 않았고**, 되찾을 경로가 없었다.

prod 실측(2026-09-14, 공유 전략 b9f837e0): MARA 매수(09-11)·NIO 매도(09-14)가 둘 다 실제로
체결됐는데 `trade_history` 0건 · 로트 0건이었다. 그래서 `workflow_buy_amount` 가 0 이 되고,
분모가 0 이라 `workflow_pnl_rate` 가 NULL 로 발행되어 **커뮤니티 수익률이 통째로 비었다.**

## 대칭 — 네 경우를 모두 다룬다

오너 지시(2026-09-14): *"자동매매로 산 게 아닐 수도 맞을 수도 있고, 자동매매로 판 게 아닐
수도 맞을 수도 있으니깐 대응되어서 사용자에게도 추정치라도 확인되어야지."*

| 매수 | 매도 | 처리 |
|---|---|---|
| 자동매매 | 자동매매 | FIFO 실현손익 (정상 경로) |
| 자동매매 밖 | 자동매매 | 매수 기준이 없다 → 계좌 평균매입가로 **추정** |
| 자동매매 | 자동매매 밖 | 로트가 남는다 → **유령 포지션**, 밖에서 팔린 것으로 **추정** |
| 자동매매 밖 | 자동매매 밖 | 전략 성과가 아니다 — off_strategy 로만 집계 |

두 갈래 모두 **추정임을 밝혀서** 기록하고, 확정 실현손익과 섞지 않는다.

## 이 모듈의 경계

브로커를 모른다. 체결 조회는 호출자가 주입한 콜러블로 하고, 계좌 잔고도 인자로 받는다.
그래서 실행기 생명주기 없이 단위 테스트할 수 있다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

#: 잔고를 못 읽었을 때 쓰는 표식. **빈 dict 를 쓰면 안 된다** — "보유 0" 과 구분되지 않아
#: 멀쩡한 로트를 전부 유령으로 보고하고, 실제로 들고 있는 포지션을 밖에서 팔린 것으로
#: 기록해 버린다. 조회 실패는 반드시 이 값으로 넘겨 재조정을 **건너뛰게** 한다.
ACCOUNT_UNAVAILABLE: Optional[Dict[str, Any]] = None

#: 유령 판정에 쓰는 수량 허용오차. 소수점 보유(분할매수 등)에서 부동소수 오차로
#: 0.0000001 주가 "사라진" 것으로 잡히는 것을 막는다.
_QTY_EPSILON = 1e-6


@dataclass
class ReconcileReport:
    """한 번의 재조정 결과. 수치는 전부 '무엇을 했는가' 이고 판정이 아니다."""

    checked_orders: int = 0
    recorded_fills: int = 0
    still_unfilled: int = 0
    mismatched_symbol: int = 0
    phantom_positions: int = 0
    phantom_quantity: float = 0.0
    skipped_no_account: bool = False
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "checked_orders": self.checked_orders,
            "recorded_fills": self.recorded_fills,
            "still_unfilled": self.still_unfilled,
            "mismatched_symbol": self.mismatched_symbol,
            "phantom_positions": self.phantom_positions,
            "phantom_quantity": self.phantom_quantity,
            "skipped_no_account": self.skipped_no_account,
            "errors": list(self.errors),
        }


def _normalize(symbol: str) -> str:
    """종목코드 비교용 정규화 — 표기 차이(공백·대소문자)로 오탐하지 않게."""
    return str(symbol or "").strip().upper()


def _account_avg_price(account_positions: Dict[str, Any], symbol: str) -> Optional[float]:
    pos = account_positions.get(symbol)
    if not isinstance(pos, dict):
        return None
    raw = pos.get("avg_price")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _account_quantities(account_positions: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for symbol, pos in account_positions.items():
        if not isinstance(pos, dict):
            continue
        try:
            out[symbol] = float(pos.get("quantity") or 0)
        except (TypeError, ValueError):
            out[symbol] = 0.0
    return out


async def reconcile_workflow_fills(
    tracker: Any,
    *,
    fetch_fills_by_date: Callable[[str], Awaitable[Dict[str, Dict[str, Any]]]],
    account_positions: Optional[Dict[str, Any]],
    min_age_seconds: float = 60.0,
    limit: int = 50,
    record_phantom: bool = True,
) -> ReconcileReport:
    """미확정 주문을 브로커에 확인해 원장에 넣고, 유령 포지션을 보고한다.

    Args:
        tracker: ``WorkflowPositionTracker``.
        fetch_fills_by_date: ``async (order_date) -> {주문번호: {filled_qty, avg_price,
            fill_time, ...}}``. 조회 실패는 **빈 dict** 를 돌려준다 — 그래서 이 함수는
            "응답에 없음" 을 "체결 안 됨" 으로 단정하지 않고 미확정으로 남겨 둔다.
        account_positions: ``{종목코드: {"quantity": float, "avg_price": float}}``.
            잔고를 못 읽었으면 반드시 ``None``(=``ACCOUNT_UNAVAILABLE``) — 빈 dict 가
            아니다. ``None`` 이면 유령 갈래를 통째로 건너뛴다.
        min_age_seconds: 접수 직후 인라인 확인 창과 겹치지 않게 두는 유예.
        limit: 한 주기에 처리할 최대 주문 수.
        record_phantom: 유령 포지션을 보고만 할지(False) 여부. 현재는 보고만 한다 —
            로트 정리는 사용자에게 보이는 수치를 바꾸므로 별도 결정이 필요하다.

    Returns:
        ``ReconcileReport``. 아무것도 못 했으면 0 이 담긴 보고서이고 예외는 던지지 않는다.
    """
    report = ReconcileReport()

    # ── ① 주문 갈래: 우리가 낸 주문인데 체결이 원장에 없는 것 ────────────────
    try:
        pending = tracker.get_unconfirmed_workflow_orders(
            min_age_seconds=min_age_seconds, limit=limit
        )
    except Exception as exc:  # 원장 조회 실패는 재조정 전체를 막지 않는다
        report.errors.append(f"unconfirmed_query_failed: {exc}")
        pending = []

    report.checked_orders = len(pending)

    # 날짜별로 묶어 브로커 호출을 날짜 수만큼으로 줄인다(앱키당 2초 1회 제한).
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for order in pending:
        by_date.setdefault(str(order.get("order_date") or ""), []).append(order)

    for order_date, orders in by_date.items():
        if not order_date:
            report.errors.append("order_without_date_skipped")
            continue
        try:
            fills = await fetch_fills_by_date(order_date)
        except Exception as exc:
            report.errors.append(f"fill_query_failed[{order_date}]: {exc}")
            continue
        if not isinstance(fills, dict):
            report.errors.append(f"fill_query_bad_shape[{order_date}]")
            continue

        # 주문번호는 앞자리 0 을 떼고 맞춘다 — 브로커 응답과 우리 원장의 표기가 갈린다.
        normalized = {str(k).lstrip("0") or str(k): v for k, v in fills.items()}

        for order in orders:
            order_no = str(order.get("order_no") or "")
            hit = fills.get(order_no) or normalized.get(order_no.lstrip("0") or order_no)
            if not hit:
                # 응답에 없다 = 아직 미체결이거나, 조회가 실패했거나, 취소됐다.
                # 셋을 구분할 수 없으므로 아무것도 기록하지 않고 다음 주기로 넘긴다.
                report.still_unfilled += 1
                continue
            try:
                filled_qty = float(hit.get("filled_qty") or 0)
                fill_price = float(hit.get("avg_price") or 0)
            except (TypeError, ValueError):
                report.errors.append(f"fill_row_unparsable[{order_no}]")
                continue
            if filled_qty <= 0 or fill_price <= 0:
                report.still_unfilled += 1
                continue

            symbol = str(order.get("symbol") or hit.get("symbol") or "")
            side = str(order.get("side") or "")
            if not symbol or side not in ("buy", "sell"):
                report.errors.append(f"order_missing_symbol_or_side[{order_no}]")
                continue

            # 🔴 주문번호만 믿으면 안 된다. 주문번호는 계좌 안에서만 유일하고, 원장에는
            #    **계좌를 바꾸기 전 주문이 그대로 남아 있다**(workflow_orders 에 계좌 컬럼이
            #    없다). 새 계좌에서 같은 날 같은 번호가 나오면 남의 체결을 우리 주문으로
            #    기록하게 된다. 브로커 응답이 종목을 실어 줄 때는 반드시 대조한다.
            hit_symbol = str(hit.get("symbol") or "").strip()
            if hit_symbol and _normalize(hit_symbol) != _normalize(symbol):
                report.mismatched_symbol += 1
                logger.warning(
                    "fill_reconcile_symbol_mismatch | order=%s date=%s ledger=%s broker=%s "
                    "— 같은 주문번호의 다른 종목이라 기록하지 않는다(계좌 교체 흔적일 수 있다)",
                    order_no, order_date, symbol, hit_symbol,
                )
                continue

            # 🔴 매도 잔량 추정의 전제 — 계좌 평균매입가를 반드시 같이 넘긴다.
            #    없으면 "자동매매가 사지 않은 물량을 팔았다" 가 추정으로 기록되지 않고
            #    'Sell without enough position' 경고만 남고 조용히 사라진다.
            avg_price = (
                _account_avg_price(account_positions, symbol)
                if isinstance(account_positions, dict) else None
            )

            try:
                classification = await tracker.record_fill(
                    order_no=order_no,
                    order_date=order_date,
                    symbol=symbol,
                    exchange=str(order.get("exchange") or ""),
                    side=side,
                    quantity=int(filled_qty),
                    price=fill_price,
                    fill_time=str(hit.get("fill_time") or ""),
                    # 재조정은 우리 주문 원장에서 출발하므로 매체코드를 추측하지 않는다.
                    # 빈 값이면 트래커가 '우리 주문과 일치하는가' 로만 분류한다.
                    commda_code="",
                    account_avg_price=avg_price,
                    currency=hit.get("currency"),
                )
            except Exception as exc:
                report.errors.append(f"record_fill_failed[{order_no}]: {exc}")
                continue

            report.recorded_fills += 1
            logger.info(
                "fill_reconciled | order=%s date=%s %s %s x%s @%s class=%s avg_basis=%s",
                order_no, order_date, symbol, side, int(filled_qty), fill_price,
                classification, avg_price,
            )

    # ── ② 잔고 갈래: 로트는 남았는데 계좌엔 없는 것(밖에서 팔린 것으로 추정) ──
    if account_positions is None:
        # 잔고를 못 읽었다. 빈 잔고로 간주하면 보유 중인 로트를 전부 유령으로 보고한다.
        report.skipped_no_account = True
        return report

    try:
        phantoms = tracker.get_phantom_workflow_positions(_account_quantities(account_positions))
    except Exception as exc:
        report.errors.append(f"phantom_query_failed: {exc}")
        return report

    for p in phantoms:
        missing = float(p.get("missing_quantity") or 0)
        if missing <= _QTY_EPSILON:
            continue
        report.phantom_positions += 1
        report.phantom_quantity += missing
        if record_phantom:
            # 지금은 보고만 한다. 사라진 이유는 밖에서 매도 / 잔고 반영 지연 /
            # 종목코드 표기 차이 중 어느 것인지 구분할 수 없으므로 **추정**이고,
            # 로트를 자동으로 지우면 사용자 수치가 근거 없이 바뀐다.
            logger.warning(
                "phantom_workflow_position | symbol=%s lot_qty=%s account_qty=%s "
                "missing=%s avg_buy=%s — 자동매매 밖에서 매도된 것으로 추정됩니다",
                p.get("symbol"), p.get("lot_quantity"), p.get("account_quantity"),
                missing, p.get("avg_buy_price"),
            )

    return report
