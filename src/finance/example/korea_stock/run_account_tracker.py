"""국내주식 계좌 추적기 예제

보유종목, 예수금, 미체결 주문을 실시간으로 추적합니다.
S3_(KOSPI)/K3_(KOSDAQ) 체결 데이터로 손익을 실시간 재계산하고,
SC1 주문체결 이벤트 수신 시 자동으로 데이터를 갱신합니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS

logger = logging.getLogger(__name__)
load_dotenv()


async def run_example():
    ls = LS.get_instance()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )
    if login_result is False:
        logger.error("로그인 실패")
        return

    # 1. WebSocket 연결
    real = ls.국내주식().실시간()
    await real.connect()

    # 2. 계좌 추적기 생성
    accno = ls.국내주식().계좌()
    tracker = accno.계좌추적기(real_client=real)

    # 3. 콜백 등록
    def on_positions(positions):
        print(f"\n{'='*60}")
        print(f"[보유종목 변경] 총 {len(positions)}종목")
        for sym, pos in positions.items():
            market_name = "KOSPI" if pos.market in ("1", "10") else "KOSDAQ"
            pnl_str = f"+{pos.pnl_amount:,}" if pos.pnl_amount >= 0 else f"{pos.pnl_amount:,}"
            rt_info = ""
            if pos.realtime_pnl:
                rt = pos.realtime_pnl
                rt_pnl = f"+{rt.net_profit:,}" if rt.net_profit >= 0 else f"{rt.net_profit:,}"
                rt_info = f" | 실시간손익(세후):{rt_pnl} 수수료:{rt.buy_fee+rt.sell_fee:,} 세금:{rt.transaction_tax+rt.rural_tax:,}"
            print(
                f"  {pos.symbol_name}({sym}) [{market_name}] "
                f"보유:{pos.quantity}주 매입가:{pos.buy_price:,} "
                f"현재가:{pos.current_price:,} "
                f"평가손익:{pnl_str} ({pos.pnl_rate:.2f}%)"
                f"{rt_info}"
            )

    def on_balance(balance):
        if balance:
            print(f"\n[예수금] 예수금:{balance.deposit:,} "
                  f"D1:{balance.d1_deposit:,} D2:{balance.d2_deposit:,} "
                  f"주문가능:{balance.orderable_amount:,}")

    def on_open_orders(orders):
        print(f"\n[미체결] 총 {len(orders)}건")
        for ono, order in orders.items():
            print(f"  주문번호:{ono} {order.symbol} {order.order_type} "
                  f"주문:{order.order_qty}주@{order.order_price:,} "
                  f"미체결:{order.remaining_qty}주 상태:{order.order_status}")

    def on_account_pnl(pnl):
        pnl_str = f"+{pnl.total_pnl_amount:,}" if pnl.total_pnl_amount >= 0 else f"{pnl.total_pnl_amount:,}"
        print(f"[계좌수익률] {pnl.account_pnl_rate:.2f}% "
              f"평가:{pnl.total_eval_amount:,} 매입:{pnl.total_buy_amount:,} "
              f"손익:{pnl_str} 종목수:{pnl.position_count} "
              f"추정순자산:{pnl.estimated_asset:,}")

    tracker.on_position_change(on_positions)
    tracker.on_balance_change(on_balance)
    tracker.on_open_orders_change(on_open_orders)
    tracker.on_account_pnl_change(on_account_pnl)

    # 4. 추적 시작
    print("계좌 추적기 시작...")
    await tracker.start()

    print(f"\n구독 종목: {tracker.subscribed_symbols}")
    print(f"실시간 추적 중... (Ctrl+C로 종료)\n")

    # 5. 실시간 모니터링 (5분)
    try:
        await asyncio.sleep(300)
    except asyncio.CancelledError:
        pass

    # 6. 종료
    await tracker.stop()
    print("\n계좌 추적기 종료")


if __name__ == "__main__":
    asyncio.run(run_example())
