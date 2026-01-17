"""
해외선물 계좌 추적기 빠른 테스트
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from programgarden_finance import LS

# DEBUG 레벨로 설정하여 상세 로그 확인
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
load_dotenv()


async def quick_test():
    """빠른 테스트: 로그인 → 추적기 시작 → 초기 데이터 확인"""
    
    ls = LS.get_instance()
    
    # 로그인
    login_result = ls.login(
        appkey=os.getenv('APPKEY_FUTURE_FAKE'),
        appsecretkey=os.getenv('APPSECRET_FUTURE_FAKE')
    )
    
    if not login_result:
        logger.error('❌ 로그인 실패')
        return
    
    logger.info('✅ 로그인 성공')
    
    # 클라이언트 준비
    futures = ls.overseas_futureoption()
    market = futures.market()
    real = futures.real()
    accno = futures.accno()
    
    # WebSocket 연결
    logger.info('🔌 WebSocket 연결 중...')
    await real.connect()
    logger.info('✅ WebSocket 연결 완료')
    
    # 계좌 추적기 생성
    logger.info('📊 계좌 추적기 생성 중...')
    tracker = accno.account_tracker(
        market_client=market,
        real_client=real,
        refresh_interval=60,
    )
    
    # 추적기 시작
    logger.info('🚀 추적기 시작 중...')
    await tracker.start()
    
    # 초기 데이터 확인
    positions = tracker.get_positions()
    balance = tracker.get_balance()
    orders = tracker.get_open_orders()
    
    print('\n' + '=' * 60)
    print('📊 초기 데이터 로드 완료')
    print('=' * 60)
    print(f'보유포지션: {len(positions)}개')
    print(f'예수금: {balance}')
    print(f'미체결주문: {len(orders)}개')
    
    # 포지션 상세 출력
    if positions:
        print('\n' + '=' * 60)
        print('포지션 상세:')
        print('=' * 60)
        for sym, pos in positions.items():
            print(f'\n종목: {sym}')
            print(f'  종목명: {pos.symbol_name}')
            print(f'  거래소: {pos.exchange_code}')  # ← 이 필드 확인
            print(f'  방향: {"LONG" if pos.is_long else "SHORT"}')  # ← 이 필드 확인
            print(f'  수량: {pos.quantity}계약')
            print(f'  진입가: ${pos.entry_price}')
            print(f'  현재가: ${pos.current_price}')
            print(f'  손익: ${pos.pnl_amount:.2f}')
            print(f'  손익률: {pos.pnl_rate:.2f}%')
    else:
        print('\n⚠️  보유포지션이 비어있습니다.')
        print('   - 모의투자 계좌에 미니항생 2계약이 있어야 합니다.')
        print('   - 주말/장 마감 시간일 수 있습니다.')
    
    # 미체결 주문 상세 출력
    if orders:
        print('\n' + '=' * 60)
        print('미체결 주문 상세:')
        print('=' * 60)
        for order_no, order in orders.items():
            print(f'\n주문번호: {order_no}')
            print(f'  종목: {order.symbol}')
            print(f'  거래소: {order.exchange_code}')  # ← 이 필드 확인
            print(f'  방향: {"LONG" if order.is_long else "SHORT"}')
            print(f'  주문가: ${order.order_price}')
            print(f'  주문수량: {order.order_qty}')
            print(f'  미체결: {order.remaining_qty}')
    
    # 정리
    await tracker.stop()
    await real.close()
    logger.info('✅ 테스트 완료')


if __name__ == '__main__':
    asyncio.run(quick_test())
