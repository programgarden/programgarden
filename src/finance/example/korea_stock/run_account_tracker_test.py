"""국내주식 계좌 추적기 실전 테스트 (30초 버전)

개별 TR 테스트 완료 후 통합 동작을 검증합니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)
load_dotenv()


async def run_test():
    ls = LS.get_instance()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )
    if login_result is False:
        logger.error("로그인 실패")
        return

    logger.info("로그인 성공")

    # 1. WebSocket 연결
    real = ls.국내주식().실시간()
    await real.connect()
    logger.info("WebSocket 연결 성공")

    # 2. 계좌 추적기 생성
    accno = ls.국내주식().계좌()
    tracker = accno.계좌추적기(real_client=real)

    # 3. 콜백 등록
    def on_positions(positions):
        logger.info(f"[보유종목] 총 {len(positions)}종목")
        for sym, pos in positions.items():
            market_name = "KOSPI" if pos.market in ("1", "10") else "KOSDAQ"
            pnl_sign = "+" if pos.pnl_amount >= 0 else ""
            logger.info(
                f"  {pos.symbol_name}({sym}) [{market_name}] "
                f"보유:{pos.quantity}주 매입가:{pos.buy_price:,} "
                f"현재가:{pos.current_price:,} "
                f"손익:{pnl_sign}{pos.pnl_amount:,} ({pos.pnl_rate:.2f}%)"
            )

    def on_balance(balance):
        if balance:
            logger.info(
                f"[예수금] {balance.deposit:,}원 "
                f"D1:{balance.d1_deposit:,} D2:{balance.d2_deposit:,} "
                f"주문가능:{balance.orderable_amount:,}"
            )

    def on_open_orders(orders):
        logger.info(f"[미체결] 총 {len(orders)}건")
        for ono, order in orders.items():
            logger.info(
                f"  주문번호:{ono} {order.symbol} {order.order_type} "
                f"주문:{order.order_qty}주@{order.order_price:,} "
                f"미체결:{order.remaining_qty}주 상태:{order.order_status}"
            )

    def on_account_pnl(pnl):
        pnl_sign = "+" if pnl.total_pnl_amount >= 0 else ""
        logger.info(
            f"[계좌수익률] {pnl.account_pnl_rate:.2f}% "
            f"평가:{pnl.total_eval_amount:,} 매입:{pnl.total_buy_amount:,} "
            f"손익:{pnl_sign}{pnl.total_pnl_amount:,} 종목수:{pnl.position_count} "
            f"추정순자산:{pnl.estimated_asset:,}"
        )

    tracker.on_position_change(on_positions)
    tracker.on_balance_change(on_balance)
    tracker.on_open_orders_change(on_open_orders)
    tracker.on_account_pnl_change(on_account_pnl)

    # 4. 추적 시작
    logger.info("계좌 추적기 시작...")
    await tracker.start()

    # 5. 초기 데이터 확인
    logger.info(f"\n[검증] 구독 종목: {tracker.subscribed_symbols}")

    positions = tracker.get_positions()
    logger.info(f"[검증] 보유종목 수: {len(positions)}")

    balance = tracker.get_balance()
    if balance:
        logger.info(f"[검증] 예수금 정상: {balance.deposit:,}원")
    else:
        logger.warning("[검증] 예수금 데이터 없음")

    open_orders = tracker.get_open_orders()
    logger.info(f"[검증] 미체결 주문: {len(open_orders)}건")

    errors = tracker.get_last_errors()
    if errors:
        logger.error(f"[검증] 에러 발생: {errors}")
    else:
        logger.info("[검증] 에러 없음 - 정상")

    # 6. 실시간 수신 대기 (30초)
    logger.info("\n실시간 수신 대기 30초...")
    await asyncio.sleep(30)

    # 7. 종료
    await tracker.stop()
    logger.info("계좌 추적기 종료")

    # 8. 최종 에러 상태 확인
    final_errors = tracker.get_last_errors()
    if final_errors:
        logger.error(f"최종 에러 상태: {final_errors}")
    else:
        logger.info("최종 에러 없음 - 테스트 성공")


if __name__ == "__main__":
    asyncio.run(run_test())
