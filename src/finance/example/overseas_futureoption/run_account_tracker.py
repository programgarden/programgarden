"""
해외선물 계좌 추적기 (Account Tracker) 예시

실시간으로 보유포지션, 예수금, 미체결 주문을 추적하고
틱 데이터를 기반으로 손익을 계산합니다.

주요 기능:
- o3121 API 기반 동적 종목 명세 관리 (Tick Size/Value)
- 1분 주기 API 갱신 (rate limit 회피)
- 실시간 틱 데이터로 손익 계산
- 주문 체결 시 즉시 갱신
- 콜백 기반 이벤트 처리
"""

import asyncio
import os
import logging
from decimal import Decimal
from dotenv import load_dotenv

from programgarden_finance import LS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()


async def run_example():
    """계좌 추적기 기본 사용 예시"""
    
    ls = LS.get_instance()
    
    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE"),
        paper_trading=True,  # 모의투자
    )
    
    if login_result is False:
        logger.error("로그인 실패")
        return
    
    # 1. 클라이언트 준비
    futures = ls.overseas_futureoption()
    market = futures.market()  # o3121 종목 명세 조회에 필요
    real = futures.real()
    accno = futures.accno()
    
    # 2. WebSocket 연결
    await real.connect()
    
    # 3. 계좌 추적기 생성
    tracker = accno.account_tracker(
        market_client=market,
        real_client=real,
        refresh_interval=60,      # 1분마다 API 갱신
        spec_refresh_hours=6,     # 6시간마다 종목 명세 갱신
    )
    
    # 4. 콜백 등록
    def on_position_change(positions):
        """보유포지션 변경 시 호출"""
        print("\n" + "=" * 50)
        print("📊 보유포지션 업데이트")
        print("=" * 50)
        
        if not positions:
            print("보유포지션 없음")
            return
        
        for symbol, pos in positions.items():
            side = "매수(LONG)" if pos.is_long else "매도(SHORT)"
            print(f"\n종목: {pos.symbol} ({pos.symbol_name})")
            print(f"  포지션: {side}")
            print(f"  수량: {pos.quantity}계약")
            print(f"  진입가: ${pos.entry_price}")
            print(f"  현재가: ${pos.current_price}")
            print(f"  평가손익: ${pos.pnl_amount:.2f}")
            print(f"  손익률: {pos.pnl_rate:.2f}%")
            print(f"  개시증거금: ${pos.opening_margin:.2f}")
            print(f"  유지증거금: ${pos.maintenance_margin:.2f}")
            
            # 실시간 손익 (수수료 반영)
            if pos.realtime_pnl:
                pnl = pos.realtime_pnl
                print(f"\n  [실시간 손익 - 수수료 반영]")
                print(f"  획득 틱수: {pnl.total_ticks}")
                print(f"  Tick Size: {pnl.tick_size_used}")
                print(f"  Tick Value: ${pnl.tick_value_used}")
                print(f"  총손익(USD): ${pnl.gross_pl_usd:.2f}")
                print(f"  수수료: ${pnl.total_fees_usd:.2f}")
                print(f"  순손익(USD): ${pnl.net_pl_usd:.2f}")
                print(f"  순손익(KRW): ₩{pnl.net_pl_krw:,.0f}")
                
                if pnl.is_safety_margin_applied:
                    print(f"  ⚠️  Safety Margin 적용됨")
    
    def on_balance_change(balance):
        """예수금/증거금 변경 시 호출"""
        if not balance:
            return
        
        print("\n" + "=" * 50)
        print("💰 예수금/증거금 업데이트")
        print("=" * 50)
        print(f"  해외선물예수금: ${balance.deposit:,.2f}")
        print(f"  위탁증거금: ${balance.total_margin:,.2f}")
        print(f"  주문가능금액: ${balance.orderable_amount:,.2f}")
        print(f"  인출가능금액: ${balance.withdrawable_amount:,.2f}")
        print(f"  평가손익: ${balance.pnl_amount:,.2f}")
        print(f"  실현손익: ${balance.realized_pnl:,.2f}")
    
    def on_open_orders_change(orders):
        """미체결 주문 변경 시 호출"""
        print("\n" + "=" * 50)
        print("📋 미체결 주문 업데이트")
        print("=" * 50)
        
        if not orders:
            print("미체결 주문 없음")
            return
        
        for order_no, order in orders.items():
            side = "매수" if order.is_long else "매도"
            print(f"\n주문번호: {order.order_no}")
            print(f"  종목: {order.symbol} ({order.symbol_name})")
            print(f"  구분: {side}")
            print(f"  주문가: ${order.order_price}")
            print(f"  주문수량: {order.order_qty}계약")
            print(f"  체결수량: {order.executed_qty}계약")
            print(f"  미체결수량: {order.remaining_qty}계약")
    
    def on_account_pnl_change(pnl_info):
        """계좌 전체 수익률 변경 시 호출 (신규 추가)"""
        pnl_rate = float(pnl_info.account_pnl_rate)
        emoji = "📈" if pnl_rate >= 0 else "📉"
        sign = "+" if pnl_rate >= 0 else ""
        
        print(f"\n{emoji} 계좌 수익률: {sign}{pnl_rate:.2f}% | "
              f"평가액: ${float(pnl_info.total_eval_amount):,.2f} | "
              f"증거금: ${float(pnl_info.total_margin_used):,.2f} | "
              f"손익: ${float(pnl_info.total_pnl_amount):,.2f} | "
              f"포지션수: {pnl_info.position_count}")
    
    # 콜백 등록
    tracker.on_position_change(on_position_change)
    tracker.on_balance_change(on_balance_change)
    tracker.on_open_orders_change(on_open_orders_change)
    tracker.on_account_pnl_change(on_account_pnl_change)  # 계좌 수익률 콜백 추가
    
    # 5. 추적 시작 (o3121로 종목 명세 로드됨)
    print("🚀 계좌 추적 시작...")
    await tracker.start()
    
    # 종목 명세 확인
    print(f"\n📋 로드된 종목 수: {tracker.spec_manager.spec_count}")
    print(f"📋 기초상품 목록: {tracker.available_base_products[:10]}...")
    
    # 특정 종목 명세 조회 예시
    spec = tracker.get_symbol_spec("NQH25")
    if spec:
        print(f"\n[NQH25 종목 명세]")
        print(f"  종목명: {spec.symbol_name}")
        print(f"  Tick Size: {spec.tick_size}")
        print(f"  Tick Value: ${spec.tick_value}")
        print(f"  통화: {spec.currency}")
        print(f"  개시증거금: ${spec.opening_margin}")
        print(f"  유지증거금: ${spec.maintenance_margin}")
    
    # 6. 실행 유지 (Ctrl+C로 종료)
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  종료 중...")
    finally:
        await tracker.stop()
        await real.close()
        print("✅ 종료 완료")


async def run_symbol_spec_only():
    """종목 명세만 조회하는 예시 (추적 없이)"""
    
    ls = LS.get_instance()
    
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )
    
    if login_result is False:
        logger.error("로그인 실패")
        return
    
    from programgarden_finance.ls.overseas_futureoption.extension import SymbolSpecManager
    
    futures = ls.overseas_futureoption()
    market = futures.market()
    
    # 종목 명세 관리자 생성
    spec_manager = SymbolSpecManager(market, refresh_hours=6)
    
    # 초기화 (o3121 호출)
    print("📋 종목 명세 로딩 중...")
    await spec_manager.initialize()
    
    print(f"\n총 {spec_manager.spec_count}개 종목 로드됨")
    print(f"기초상품 목록: {spec_manager.available_base_products}")
    
    # 주요 종목 명세 출력
    major_symbols = ["NQH25", "ESH25", "CLH25", "GCH25", "6EH25"]
    
    print("\n" + "=" * 60)
    print("주요 종목 명세")
    print("=" * 60)
    
    for symbol in major_symbols:
        spec = spec_manager.get_spec(symbol)
        if spec:
            print(f"\n{spec.symbol} ({spec.symbol_name})")
            print(f"  거래소: {spec.exchange_code}")
            print(f"  Tick Size: {spec.tick_size}")
            print(f"  Tick Value: ${spec.tick_value}")
            print(f"  계약당금액: ${spec.contract_amount}")
            print(f"  소수점자리: {spec.decimal_places}")
            print(f"  통화: {spec.currency}")
            print(f"  개시증거금: ${spec.opening_margin:,.0f}")
            print(f"  유지증거금: ${spec.maintenance_margin:,.0f}")
    
    # 정리
    await spec_manager.stop()


async def run_calculator_only():
    """손익 계산기만 사용하는 예시 (API 호출 없이)"""
    
    from programgarden_finance.ls.overseas_futureoption.extension import (
        FuturesPnLCalculator,
        FuturesTradeInput,
        SymbolSpec,
    )
    
    # 종목 명세 (수동 입력)
    nq_spec = SymbolSpec(
        symbol="NQH25",
        symbol_name="E-mini NASDAQ 100",
        tick_size=Decimal("0.25"),
        tick_value=Decimal("5.00"),
        currency="USD",
    )
    
    calculator = FuturesPnLCalculator(default_fee_per_contract=Decimal("7.5"))
    
    # 거래 입력 (LONG 포지션)
    trade = FuturesTradeInput(
        symbol="NQH25",
        buy_price=Decimal("21500.00"),
        sell_price=Decimal("21525.00"),
        qty=2,
        is_long=True,
        exchange_rate=Decimal("1380"),
        manual_tick_size=nq_spec.tick_size,
        manual_tick_value=nq_spec.tick_value,
    )
    
    # 손익 계산
    from programgarden_finance.ls.overseas_futureoption.extension import calculate_futures_pnl
    result = calculate_futures_pnl(trade, nq_spec)
    
    print("=" * 50)
    print("📈 해외선물 손익 계산 결과")
    print("=" * 50)
    print(f"종목: {trade.symbol}")
    print(f"포지션: {'LONG' if trade.is_long else 'SHORT'}")
    print(f"진입가: ${trade.buy_price}")
    print(f"청산가: ${trade.sell_price}")
    print(f"수량: {trade.qty}계약")
    print()
    print(f"Tick Size: {result.tick_size_used}")
    print(f"Tick Value: ${result.tick_value_used}")
    print(f"획득 틱수: {result.total_ticks}")
    print()
    print(f"총손익(USD): ${result.gross_pl_usd:.2f}")
    print(f"수수료(왕복): ${result.total_fees_usd:.2f}")
    print(f"순손익(USD): ${result.net_pl_usd:.2f}")
    print(f"순손익(KRW): ₩{result.net_pl_krw:,.0f}")
    print(f"예상 양도세(11%): ₩{result.estimated_tax_krw:,.0f}")
    
    if result.is_safety_margin_applied:
        print("\n⚠️  Safety Margin 적용됨 (보수적 비용 추정)")
    
    # SHORT 포지션 예시
    print("\n" + "=" * 50)
    print("📉 SHORT 포지션 손익 계산")
    print("=" * 50)
    
    short_trade = FuturesTradeInput(
        symbol="ESH25",
        buy_price=Decimal("6000.00"),
        sell_price=Decimal("5975.00"),
        qty=1,
        is_long=False,  # SHORT
        exchange_rate=Decimal("1380"),
        manual_tick_size=Decimal("0.25"),
        manual_tick_value=Decimal("12.50"),  # E-mini S&P 500
    )
    
    es_spec = SymbolSpec(
        symbol="ESH25",
        tick_size=Decimal("0.25"),
        tick_value=Decimal("12.50"),
    )
    
    result = calculate_futures_pnl(short_trade, es_spec)
    
    print(f"종목: {short_trade.symbol}")
    print(f"포지션: SHORT (매도 후 매수)")
    print(f"진입가(매도): ${short_trade.sell_price}")
    print(f"청산가(매수): ${short_trade.buy_price}")
    print(f"수량: {short_trade.qty}계약")
    print()
    print(f"획득 틱수: {result.total_ticks}")
    print(f"순손익(USD): ${result.net_pl_usd:.2f}")


if __name__ == "__main__":
    # 기본 예시 실행
    asyncio.run(run_example())
    
    # 또는 다른 예시 실행
    # asyncio.run(run_symbol_spec_only())
    # asyncio.run(run_calculator_only())
