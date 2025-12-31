"""
해외주식 보유종목 실시간 수익률 모니터링

테스트 항목:
1. 보유종목 조회 (COSOQ00201)
2. 실시간 시세 구독 (GSC) → 수익률 자동 계산
3. 예수금/미체결 주문 조회

사용법:
  python run_account_tracker.py
"""

import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.models import SetupOptions

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
)

load_dotenv()


# ===== 콜백 핸들러 =====

def on_position_change(positions):
    """보유종목 변경 시 호출"""
    print("\n" + "=" * 60)
    print(f"📊 보유종목 [{datetime.now().strftime('%H:%M:%S')}]")
    print("=" * 60)
    
    if not positions:
        print("  (보유종목 없음)")
        return
    
    total_pnl = 0
    total_value = 0
    
    for symbol, pos in positions.items():
        pnl_sign = "+" if pos.pnl_amount >= 0 else ""
        pnl_color = "🟢" if pos.pnl_amount >= 0 else "🔴"
        
        print(f"\n  {pnl_color} {pos.symbol}")
        print(f"     수량: {pos.quantity}주")
        print(f"     현재가: ${pos.current_price:,.2f}")
        print(f"     매입가: ${pos.buy_price:,.2f}")
        print(f"     평가금액: ${pos.current_price * pos.quantity:,.2f}")
        print(f"     손익: {pnl_sign}${pos.pnl_amount:,.2f} ({pnl_sign}{pos.pnl_rate:.2f}%)")
        
        total_pnl += pos.pnl_amount
        total_value += pos.current_price * pos.quantity
    
    print("\n" + "-" * 60)
    total_sign = "+" if total_pnl >= 0 else ""
    print(f"  💼 총 평가금액: ${total_value:,.2f}")
    print(f"  💰 총 손익: {total_sign}${total_pnl:,.2f}")
    print("=" * 60)


def on_balance_change(balance):
    """예수금 변경 시 호출"""
    print("\n" + "-" * 40)
    print(f"💵 예수금 [{datetime.now().strftime('%H:%M:%S')}]")
    print("-" * 40)
    for currency, bal in balance.items():
        print(f"  [{currency}] 예수금: ${bal.deposit:,.2f} | 주문가능: ${bal.orderable_amount:,.2f}")


def on_open_orders_change(orders):
    """미체결 주문 변경 시 호출"""
    if not orders:
        return
    
    print("\n" + "-" * 40)
    print(f"📋 미체결 주문 [{datetime.now().strftime('%H:%M:%S')}]")
    print("-" * 40)
    
    for order_no, order in orders.items():
        side = "매수" if order.order_type == "02" else "매도"
        print(f"  #{order.order_no}: {order.symbol} {side} {order.order_qty}주 @ ${order.order_price}")


# ===== 메인 함수 =====

async def run_example():
    """보유종목 실시간 수익률 모니터링"""
    
    print("\n" + "=" * 60)
    print("📈 해외주식 실시간 수익률 모니터링")
    print("=" * 60)
    
    ls = LS.get_instance()
    
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )
    
    if login_result is False:
        logger.error("로그인 실패")
        return
    
    print("✅ 로그인 성공")
    
    # 클라이언트 준비
    stock = ls.overseas_stock()
    real = stock.real()
    accno = stock.accno()
    
    # WebSocket 연결
    print("🔌 WebSocket 연결 중...")
    await real.connect()
    print("✅ WebSocket 연결 완료")
    
    # 계좌 추적기 생성
    tracker = accno.account_tracker(
        real_client=real,
        refresh_interval=60,  # 60초마다 새로고침
    )
    
    # 콜백 등록
    tracker.on_position_change(on_position_change)
    tracker.on_balance_change(on_balance_change)
    tracker.on_open_orders_change(on_open_orders_change)
    
    # 추적 시작
    print("🚀 실시간 추적 시작...\n")
    await tracker.start()
    
    print("\n⏳ 실시간 모니터링 중... (Ctrl+C로 종료)")
    print("   - 시세 변동 시 자동으로 수익률 업데이트")
    print("   - 60초마다 전체 데이터 새로고침")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    
    # 종료
    print("\n\n⏹️  종료 중...")
    await tracker.stop()
    await real.close()
    print("✅ 종료 완료")


if __name__ == "__main__":
    asyncio.run(run_example())
