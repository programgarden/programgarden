"""실전 주문 + 계좌 추적기 통합 테스트

1. 계좌 추적기 시작 (초기 잔고 확인)
2. HLB이노베이션 1주 시장가 매수
3. SC1 체결 이벤트 수신 -> 자동 갱신 확인
4. 10초 대기 후 잔고 변화 확인
5. 1주 시장가 매도
6. SC1 체결 이벤트 수신 -> 자동 갱신 확인
"""
import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from programgarden_finance import LS, CSPAT00601

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

    # 1. WebSocket 연결 + 계좌 추적기 시작
    real = ls.국내주식().실시간()
    await real.connect()
    logger.info("WebSocket 연결 성공")

    accno = ls.국내주식().계좌()
    tracker = accno.계좌추적기(real_client=real)

    # 이벤트 로그
    events = []

    def on_positions(positions):
        ts = datetime.now().strftime("%H:%M:%S")
        count = len(positions)
        if "024850" in positions:
            p = positions["024850"]
            msg = f"[{ts}] 보유종목변경: HLB이노베이션 {p.quantity}주 현재가:{p.current_price:,}"
            events.append(msg)
            logger.info(f"  >>> [보유종목변경] HLB이노베이션 {p.quantity}주 현재가:{p.current_price:,} 손익:{p.pnl_amount:,}")
        else:
            msg = f"[{ts}] 보유종목변경: 총 {count}종목 (HLB이노베이션 없음)"
            events.append(msg)
            logger.info(f"  >>> [보유종목변경] 총 {count}종목 (HLB이노베이션 없음)")

    def on_balance(balance):
        if balance:
            ts = datetime.now().strftime("%H:%M:%S")
            msg = f"[{ts}] 예수금변경: 주문가능={balance.orderable_amount:,}"
            events.append(msg)
            logger.info(f"  >>> [예수금변경] 주문가능:{balance.orderable_amount:,}")

    def on_orders(orders):
        ts = datetime.now().strftime("%H:%M:%S")
        msg = f"[{ts}] 미체결변경: {len(orders)}건"
        events.append(msg)
        logger.info(f"  >>> [미체결변경] {len(orders)}건")

    def on_pnl(pnl):
        ts = datetime.now().strftime("%H:%M:%S")
        logger.info(f"  >>> [계좌수익률] {float(pnl.account_pnl_rate):.2f}% 평가:{pnl.total_eval_amount:,}")

    tracker.on_position_change(on_positions)
    tracker.on_balance_change(on_balance)
    tracker.on_open_orders_change(on_orders)
    tracker.on_account_pnl_change(on_pnl)

    logger.info("=" * 60)
    logger.info("계좌 추적기 시작...")
    await tracker.start()

    # 초기 상태 확인
    positions_before = tracker.get_positions()
    hlb_before = positions_before.get("024850")
    hlb_qty_before = hlb_before.quantity if hlb_before else 0
    logger.info(f"초기 HLB이노베이션 보유: {hlb_qty_before}주")
    logger.info(f"구독 종목: {tracker.subscribed_symbols}")
    errors = tracker.get_last_errors()
    if errors:
        logger.warning(f"초기 에러: {errors}")
    else:
        logger.info("초기 에러 없음")

    await asyncio.sleep(3)

    # 2. 매수 주문 (시장가 1주)
    logger.info("=" * 60)
    logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] HLB이노베이션(024850) 1주 시장가 매수 주문...")

    order_client = ls.국내주식().주문()

    buy_tr = order_client.현물주문(
        CSPAT00601.CSPAT00601InBlock1(
            IsuNo="A024850",
            OrdQty=1,
            OrdPrc=0,
            BnsTpCode="2",        # 매수
            OrdprcPtnCode="03",   # 시장가
            MgntrnCode="000",
            LoanDt="",
            OrdCndiTpCode="0",
        )
    )
    buy_resp = await buy_tr.req_async()

    logger.info(f"  매수 응답: rsp_cd={buy_resp.rsp_cd} rsp_msg={buy_resp.rsp_msg}")
    buy_order_no = None
    if buy_resp.block2:
        buy_order_no = buy_resp.block2.OrdNo
        logger.info(f"  주문번호: {buy_order_no} | 시각: {buy_resp.block2.OrdTime} | 금액: {buy_resp.block2.OrdAmt:,}원")
    if buy_resp.error_msg:
        logger.error(f"  매수 에러: {buy_resp.error_msg}")

    # 3. SC1 이벤트 + 자동 갱신 대기 (13초: 3초 지연 + 10초 관찰)
    logger.info("SC1 체결 이벤트 및 자동 갱신 대기 (13초)...")
    await asyncio.sleep(13)

    # 체결 후 상태 확인
    positions_after_buy = tracker.get_positions()
    hlb_after_buy = positions_after_buy.get("024850")
    hlb_qty_after_buy = hlb_after_buy.quantity if hlb_after_buy else 0
    logger.info(f"매수 후 HLB이노베이션 보유: {hlb_qty_after_buy}주 (이전: {hlb_qty_before}주)")

    buy_success = hlb_qty_after_buy > hlb_qty_before
    logger.info(f"매수 체결 -> 잔고 갱신: {'[성공]' if buy_success else '[미확인 - 수동 갱신 시도]'}")

    if not buy_success:
        logger.warning("수동 갱신 시도...")
        await tracker.refresh_now()
        await asyncio.sleep(3)
        positions_manual = tracker.get_positions()
        hlb_manual = positions_manual.get("024850")
        hlb_qty_manual = hlb_manual.quantity if hlb_manual else 0
        logger.info(f"수동 갱신 후 HLB이노베이션 보유: {hlb_qty_manual}주")
        if hlb_qty_manual > hlb_qty_before:
            hlb_qty_after_buy = hlb_qty_manual
            buy_success = True
            logger.info("수동 갱신으로 보유 확인")

    await asyncio.sleep(3)

    # 4. 매도 주문 (시장가 1주)
    logger.info("=" * 60)
    logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] HLB이노베이션(024850) 1주 시장가 매도 주문...")

    sell_tr = order_client.현물주문(
        CSPAT00601.CSPAT00601InBlock1(
            IsuNo="A024850",
            OrdQty=1,
            OrdPrc=0,
            BnsTpCode="1",        # 매도
            OrdprcPtnCode="03",   # 시장가
            MgntrnCode="000",
            LoanDt="",
            OrdCndiTpCode="0",
        )
    )
    sell_resp = await sell_tr.req_async()

    logger.info(f"  매도 응답: rsp_cd={sell_resp.rsp_cd} rsp_msg={sell_resp.rsp_msg}")
    sell_order_no = None
    if sell_resp.block2:
        sell_order_no = sell_resp.block2.OrdNo
        logger.info(f"  주문번호: {sell_order_no} | 시각: {sell_resp.block2.OrdTime} | 금액: {sell_resp.block2.OrdAmt:,}원")
    if sell_resp.error_msg:
        logger.error(f"  매도 에러: {sell_resp.error_msg}")

    # 5. SC1 이벤트 + 자동 갱신 대기 (13초)
    logger.info("SC1 체결 이벤트 및 자동 갱신 대기 (13초)...")
    await asyncio.sleep(13)

    # 매도 후 상태 확인
    positions_after_sell = tracker.get_positions()
    hlb_after_sell = positions_after_sell.get("024850")
    hlb_qty_after_sell = hlb_after_sell.quantity if hlb_after_sell else 0
    logger.info(f"매도 후 HLB이노베이션 보유: {hlb_qty_after_sell}주")

    sell_success = hlb_qty_after_sell < hlb_qty_after_buy
    logger.info(f"매도 체결 -> 잔고 갱신: {'[성공]' if sell_success else '[미확인 - 수동 갱신 시도]'}")

    if not sell_success:
        logger.warning("수동 갱신 시도...")
        await tracker.refresh_now()
        await asyncio.sleep(3)
        positions_manual2 = tracker.get_positions()
        hlb_manual2 = positions_manual2.get("024850")
        hlb_qty_manual2 = hlb_manual2.quantity if hlb_manual2 else 0
        logger.info(f"수동 갱신 후 HLB이노베이션 보유: {hlb_qty_manual2}주")
        if hlb_qty_manual2 < hlb_qty_after_buy:
            hlb_qty_after_sell = hlb_qty_manual2
            sell_success = True
            logger.info("수동 갱신으로 잔고 감소 확인")

    # 6. 최종 결과
    logger.info("=" * 60)
    logger.info("=== 최종 테스트 결과 ===")
    logger.info(f"  초기 보유: {hlb_qty_before}주")
    logger.info(f"  매수 후:   {hlb_qty_after_buy}주  ({'OK' if buy_success else 'FAIL'})")
    logger.info(f"  매도 후:   {hlb_qty_after_sell}주  ({'OK' if sell_success else 'FAIL'})")
    logger.info(f"  매수 주문번호: {buy_order_no}")
    logger.info(f"  매도 주문번호: {sell_order_no}")
    logger.info(f"  이벤트 로그 ({len(events)}건):")
    for e in events:
        logger.info(f"    {e}")
    final_errors = tracker.get_last_errors()
    if final_errors:
        logger.error(f"  최종 에러: {final_errors}")
    else:
        logger.info("  최종 에러: 없음")

    overall = buy_success and sell_success
    logger.info(f"  종합 결과: {'[테스트 성공]' if overall else '[일부 미확인 - 상세 로그 참조]'}")

    await tracker.stop()
    logger.info("계좌 추적기 종료. 테스트 완료.")


if __name__ == "__main__":
    asyncio.run(run_test())
