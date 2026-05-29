"""HKEX 예제 81 L4 모의주문 E2E 트리거 (host-only · 사용자 직접 발사).

목적
----
예제 81 (HKEX 다종목 RSI+Bollinger) 의 주문 라이프사이클을 실 LS **모의(paper)**
계좌에 대해 단 1건만 검증한다:

    market_data(현재가) → new_order(limit BUY, 미체결용 deep price) →
    open_orders(미체결 확인) → cancel_order(취소) → open_orders(취소 확인)

NodeRunner 로 개별 노드를 단독 실행한다 (워크플로우 DAG 불필요). 브로커
connection 은 credential 전달 시 NodeRunner 가 자동 주입한다.

⚠️  이 스크립트는 **실제 모의계좌에 진짜 주문을 제출**한다 (paper 이지만 LS
    서버로 실제 TR 전송). 그래서 `--confirm` 플래그(또는 env `L4_CONFIRM=1`)
    없이는 실행을 거부한다. **주문 발사는 사용자가 직접** 한다 (Claude 직접 발사
    금지 — 프로젝트 정책).

체결 방지 설계
-------------
BUY limit 을 현재가보다 한참 **아래**(기본 -5%)에 깔면, 시장이 그만큼 급락하지
않는 한 체결되지 않고 호가창에 미체결로 남는다 → 즉시 cancel. 시세를 못 읽으면
(장 마감/데이터 없음) 가격을 추정하지 않고 중단한다 (`--price` 로 수동 지정 가능).

A-4 idempotency 에 대한 주의 (중요)
-----------------------------------
A-4 주문 idempotency 가드(`enable_order_idempotency`)는 **paper_trading 에서
설계상 우회**된다 (`executor.py::_is_order_idempotency_enabled` — "모의투자는 중복
위험 없음"). HKEX 모의투자가 LS 의 유일한 모의 환경이므로, **이 라이브 스크립트로는
A-4 중복차단을 시연할 수 없다.** A-4 검증은 `enable_order_idempotency=True` +
`paper_trading=False` 조합의 단위/통합 테스트 영역이다 (실거래 키 없이 mock 으로 검증).

실행
----
호스트에서 (실 .env 가 있는 환경):
    cd src/programgarden
    poetry run python examples/programmer_example/test_hkex_81_l4_order.py --confirm

옵션:
    --symbol HMHM26       대상 월물 (기본: HMHM26, Mini Hang Seng 6월물)
    --exchange HKEX       거래소 (기본: HKEX)
    --discount 0.05       현재가 대비 BUY limit 할인율 (기본 0.05 = -5%)
    --price 22000         시세 무시하고 limit 가격 직접 지정 (정수 틱)
    --quantity 1          계약 수 (기본 1)
    --no-cancel           cancel 단계 생략 (미체결 잔존 — 권장 안 함)

필요 .env 키
------------
- APPKEY_FUTURE_FAKE / APPSECRET_FUTURE_FAKE  (LS 해외선물 모의)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
from pathlib import Path


project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root / "src" / "programgarden"))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "community"))


env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


from programgarden import NodeRunner  # noqa: E402


CRED_ID = "futures_cred"


def _build_credentials() -> list | None:
    appkey = os.environ.get("APPKEY_FUTURE_FAKE")
    appsecret = os.environ.get("APPSECRET_FUTURE_FAKE")
    if not (appkey and appsecret):
        print("❌ .env 에 APPKEY_FUTURE_FAKE / APPSECRET_FUTURE_FAKE 가 없습니다.")
        return None
    return [
        {
            "credential_id": CRED_ID,
            "type": "broker_ls_overseas_futures",
            "data": [
                {"key": "appkey", "value": appkey},
                {"key": "appsecret", "value": appsecret},
                {"key": "paper_trading", "value": True},
            ],
        }
    ]


def _dump(label: str, obj) -> None:
    text = json.dumps(obj, ensure_ascii=False, default=str)
    if len(text) > 600:
        text = text[:600] + " …(truncated)"
    print(f"  {label}: {text}")


async def _read_price(runner: NodeRunner, symbol: str, exchange: str) -> float | None:
    md = await runner.run(
        "OverseasFuturesMarketDataNode",
        credential_id=CRED_ID,
        symbols=[{"symbol": symbol, "exchange": exchange}],
    )
    _dump("market_data", md)
    values = (md or {}).get("values") or []
    if not values:
        return None
    price = values[0].get("price") or values[0].get("close") or 0
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None


async def main() -> int:
    parser = argparse.ArgumentParser(description="HKEX 81 L4 모의주문 E2E (사용자 직접 발사)")
    parser.add_argument("--confirm", action="store_true",
                        help="실 모의주문 제출 확인 (없으면 실행 거부)")
    parser.add_argument("--symbol", default="HMHM26")
    parser.add_argument("--exchange", default="HKEX")
    parser.add_argument("--discount", type=float, default=0.05,
                        help="현재가 대비 BUY limit 할인율 (기본 0.05)")
    parser.add_argument("--price", type=float, default=None,
                        help="limit 가격 직접 지정 (시세 무시)")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--no-cancel", action="store_true")
    args = parser.parse_args()

    print("=" * 64)
    print("🟠 HKEX 81 L4 모의주문 E2E — 실 paper 계좌에 진짜 주문 1건 제출")
    print("=" * 64)
    print(f"  symbol={args.symbol} exchange={args.exchange} qty={args.quantity}")
    print("  ⚠️  paper_trading=True 이지만 LS 서버로 실제 주문 TR 이 전송됩니다.")
    print("  ⚠️  A-4 idempotency 는 paper 에서 우회됨 → 이 스크립트로는 미검증.")

    if not (args.confirm or os.environ.get("L4_CONFIRM") == "1"):
        print("\n❌ 실행 거부: 실 모의주문을 제출하려면 `--confirm` (또는 env L4_CONFIRM=1) 필요.")
        print("   주문 발사는 사용자가 직접 합니다 (Claude 직접 발사 금지 — 정책).")
        return 3

    credentials = _build_credentials()
    if credentials is None:
        return 2

    async with NodeRunner(credentials=credentials, raise_on_error=False) as runner:
        # === 1. 현재가 읽기 → 미체결용 deep limit 가격 산정 ===
        print("\n[1] 현재가 조회")
        if args.price is not None:
            limit_price = float(args.price)
            print(f"  --price 지정 → limit_price={limit_price}")
        else:
            price = await _read_price(runner, args.symbol, args.exchange)
            if price is None:
                print("❌ 현재가를 읽지 못했습니다 (장 마감/데이터 없음?). "
                      "`--price` 로 직접 지정하거나 장중에 재시도하세요. (주문 미제출)")
                return 1
            # BUY limit 을 현재가보다 discount 만큼 아래로 → 미체결 유도. 정수 틱.
            limit_price = float(math.floor(price * (1.0 - args.discount)))
            print(f"  현재가={price} → BUY limit={limit_price} (-{args.discount:.0%}, 미체결 유도)")

        order_dict = {
            "symbol": args.symbol,
            "exchange": args.exchange,
            "quantity": args.quantity,
            "price": limit_price,
        }

        # === 2. 신규주문 (limit BUY) ===
        print("\n[2] 신규주문 제출 (limit BUY)")
        new_order = await runner.run(
            "OverseasFuturesNewOrderNode",
            credential_id=CRED_ID,
            side="buy",
            order_type="limit",
            order=order_dict,
        )
        _dump("new_order", new_order)
        order_result = (new_order or {}).get("order_result") or {}
        order_id = (new_order or {}).get("order_id") or ""
        if not order_result.get("success") or not order_id:
            print(f"❌ 주문 실패 또는 주문번호 없음 → cancel 불가. "
                  f"error={order_result.get('error')!r}")
            return 1
        print(f"  ✅ 주문 접수: order_id={order_id}")

        # === 3. 미체결 조회 (주문이 호가창에 남아있는지) ===
        print("\n[3] 미체결 조회")
        open1 = await runner.run("OverseasFuturesOpenOrdersNode", credential_id=CRED_ID)
        _dump("open_orders", open1)
        open_list = (open1 or {}).get("open_orders") or []
        present = any(str(o.get("order_id") or o.get("order_no") or "") == str(order_id)
                      for o in open_list if isinstance(o, dict))
        print(f"  미체결 {len(open_list)}건, 우리 주문 포함={present}")

        # === 4. 취소 ===
        if args.no_cancel:
            print("\n[4] --no-cancel → 취소 생략. ⚠️ 미체결 잔존, 수동 취소 필요.")
            return 0

        print("\n[4] 취소주문")
        cancel = await runner.run(
            "OverseasFuturesCancelOrderNode",
            credential_id=CRED_ID,
            original_order_id=order_id,
            symbol=args.symbol,
            exchange=args.exchange,
        )
        _dump("cancel", cancel)
        cancel_result = (cancel or {}).get("cancel_result") or {}
        if not cancel_result.get("success"):
            print(f"❌ 취소 실패: error={cancel_result.get('error')!r} "
                  f"→ ⚠️ 미체결 잔존 가능, 직접 확인/취소 필요.")
            return 1
        print(f"  ✅ 취소 완료: order_id={order_id}")

        # === 5. 취소 후 미체결 재확인 ===
        print("\n[5] 취소 후 미체결 재확인")
        open2 = await runner.run("OverseasFuturesOpenOrdersNode", credential_id=CRED_ID)
        _dump("open_orders_after", open2)
        open_list2 = (open2 or {}).get("open_orders") or []
        still = any(str(o.get("order_id") or o.get("order_no") or "") == str(order_id)
                    for o in open_list2 if isinstance(o, dict))
        print(f"  미체결 {len(open_list2)}건, 우리 주문 잔존={still}")

        print("\n" + "=" * 64)
        ok = not still
        print("✅ L4 PASS — 제출→미체결→취소→확인 라이프사이클 정상" if ok
              else "⚠️  취소 후에도 주문이 미체결에 남아있음 — 수동 확인 필요")
        print("=" * 64)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
