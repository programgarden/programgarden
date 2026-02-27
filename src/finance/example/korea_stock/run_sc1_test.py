"""SC1 자동 갱신 버그 수정 실전 검증

[검증 포인트]
- _on_order_event() -> _schedule_coroutine() -> _delayed_refresh() -> _fetch_all_data() 정상 동작
- "no running event loop" 에러가 더 이상 발생하지 않는지
- 주문 체결 후 3초 대기 -> 자동으로 보유종목/예수금/미체결 재조회가 되는지

[실행 방법]
1. 장중 (09:00~15:20): 시장가 주문 (OrdprcPtnCode="03")
   -> BUY_PRICE=0, ORDER_TYPE="market" 으로 실행
2. 시간외 단일가 (15:20~15:30): 지정가 주문 (OrdprcPtnCode="82")
   -> BUY_PRICE=0 (자동 조회), ORDER_TYPE="after_hours" 으로 실행

[시간외 단일가 주의사항]
- 운영시간: 15:20 ~ 15:30 접수, 15:40 단일가 체결
- 지정가로만 주문 가능 (OrdprcPtnCode="82")
- 가격: 전일 종가 기준으로 +-10% 범위 내
- LS증권 시간외 단일가는 실제 15:20~15:30 사이에만 접수 가능

[종목 선택]
- HLB이노베이션(024850): KOSDAQ 저가주, 1주 소액 테스트용
"""
import asyncio
import os
import logging
import time
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

# ===== 테스트 설정 =====
TEST_SYMBOL = "A024850"      # 주문용 (A+종목코드)
TEST_SYMBOL_CODE = "024850"  # 조회용 (6자리)
TEST_SYMBOL_NAME = "HLB이노베이션"

# 주문 방식: "market" = 장중 시장가, "after_hours" = 시간외 단일가
# 장중(09:00~15:20): ORDER_TYPE = "market"
# 시간외 단일가(15:20~15:30): ORDER_TYPE = "after_hours"
ORDER_TYPE = "after_hours"

# 주문가: 0이면 t8450 호가 조회로 자동 설정 (시장가는 무시됨)
BUY_PRICE = 0

# SC1 체결 후 자동갱신 대기 시간 (tracker 내부: 3초 + 조회시간 약 8초 = 11초)
AUTO_REFRESH_WAIT = 15   # 15초 대기 (여유 있게)


async def get_current_price(ls) -> int:
    """t8450 호가 조회로 현재 매수/매도호가 확인"""
    try:
        from programgarden_finance import t8450
        market_client = ls.국내주식().시세()
        tr = market_client.t8450(
            t8450.T8450InBlock(
                shcode=TEST_SYMBOL_CODE,
                gubun="0",
            )
        )
        resp = tr.req()
        if resp.error_msg is None and resp.block:
            b = resp.block
            # 매도1호가 (현재 팔 수 있는 가격)
            if hasattr(b, 'offerho1') and b.offerho1 > 0:
                logger.info(f"  매도1호가: {b.offerho1:,}원 / 매수1호가: {b.bidho1:,}원")
                return b.offerho1
            # 단일가 참조가
            if hasattr(b, 'price') and b.price > 0:
                logger.info(f"  현재가: {b.price:,}원")
                return b.price
    except Exception as e:
        logger.warning(f"  호가 조회 실패: {e}")
    return 0


async def run_test():
    """SC1 자동 갱신 버그 수정 실전 검증"""

    ls = LS.get_instance()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )
    if login_result is False:
        logger.error("로그인 실패")
        return

    logger.info("로그인 성공")
    logger.info("=" * 60)
    logger.info("SC1 자동 갱신 버그 수정 실전 검증 (시간외 단일가)")
    logger.info(f"테스트 종목: {TEST_SYMBOL_NAME} ({TEST_SYMBOL_CODE})")
    logger.info("=" * 60)

    # 1. 호가 조회로 주문가 확인
    logger.info("\n[Step 1] 현재 호가 확인...")
    buy_price = BUY_PRICE

    if ORDER_TYPE == "market":
        # 시장가는 주문가 불필요
        logger.info("  주문 방식: 장중 시장가 (OrdprcPtnCode=03)")
        buy_price = 0
        ordprc_ptn = "03"
    else:
        # 시간외 단일가는 지정가 필수
        logger.info("  주문 방식: 시간외 단일가 (OrdprcPtnCode=82)")
        ordprc_ptn = "82"
        if buy_price == 0:
            buy_price = await get_current_price(ls)
            if buy_price == 0:
                logger.error("호가 조회 실패. BUY_PRICE를 수동으로 설정하세요.")
                return
            logger.info(f"  자동 설정된 주문가: {buy_price:,}원")
        else:
            logger.info(f"  수동 설정된 주문가: {buy_price:,}원")

    # 2. WebSocket 연결 + 계좌 추적기 시작
    logger.info("\n[Step 2] WebSocket 연결 및 계좌 추적기 시작...")
    real = ls.국내주식().실시간()
    await real.connect()
    logger.info("  WebSocket 연결 성공")

    accno = ls.국내주식().계좌()
    tracker = accno.계좌추적기(real_client=real)

    # 검증용 이벤트 로그
    events = []
    refresh_count = {"value": 0}  # SC1 트리거 자동갱신 횟수 추적
    sc1_events = []               # SC1 체결 이벤트 로그

    def on_positions(positions):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        count = len(positions)
        if TEST_SYMBOL_CODE in positions:
            p = positions[TEST_SYMBOL_CODE]
            msg = f"[{ts}] [보유종목변경] {TEST_SYMBOL_NAME} {p.quantity}주 현재가:{p.current_price:,}"
            events.append(msg)
            logger.info(f"  >>> {msg}")
        else:
            msg = f"[{ts}] [보유종목변경] 총 {count}종목 ({TEST_SYMBOL_NAME} 없음)"
            events.append(msg)
            logger.info(f"  >>> {msg}")

    def on_balance(balance):
        if balance:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            msg = f"[{ts}] [예수금변경] 주문가능:{balance.orderable_amount:,}"
            events.append(msg)
            logger.info(f"  >>> {msg}")
            refresh_count["value"] += 1  # 예수금 갱신 = _fetch_all_data 호출 완료

    def on_orders(orders):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = f"[{ts}] [미체결변경] {len(orders)}건"
        events.append(msg)
        logger.info(f"  >>> {msg}")

    def on_pnl(pnl):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.info(
            f"  >>> [{ts}] [계좌수익률] {float(pnl.account_pnl_rate):.2f}% "
            f"평가:{pnl.total_eval_amount:,} 종목수:{pnl.position_count}"
        )

    # SC1 원본 이벤트 직접 캡처 (tracker를 우회해서 SC1이 실제로 수신되는지 확인)
    def on_sc1_raw(resp):
        """SC1 원본 이벤트 핸들러 - tracker와 별개로 등록"""
        try:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            if resp and hasattr(resp, 'body') and resp.body:
                body = resp.body
                event_type = getattr(body, 'ordxctptncode', '??')
                symbol = getattr(body, 'shtnIsuno', '??')
                exec_qty = getattr(body, 'execqty', '0')
                exec_prc = getattr(body, 'execprc', '0')
                order_type = getattr(body, 'bnstp', '?')
                type_names = {
                    '01': '주문접수', '02': '정정', '03': '취소',
                    '11': '체결', '12': '정정확인', '13': '취소확인', '14': '거부'
                }
                type_name = type_names.get(event_type, f'코드:{event_type}')
                buy_sell = "매수" if order_type == "2" else "매도" if order_type == "1" else f"({order_type})"
                msg = (
                    f"[{ts}] [SC1 RAW] {type_name} | {buy_sell} | 종목:{symbol} | "
                    f"체결가:{exec_prc} 체결수:{exec_qty}"
                )
                sc1_events.append(msg)
                logger.info(f"  *** {msg}")
        except Exception as e:
            logger.error(f"SC1 RAW 핸들러 오류: {e}")

    tracker.on_position_change(on_positions)
    tracker.on_balance_change(on_balance)
    tracker.on_open_orders_change(on_orders)
    tracker.on_account_pnl_change(on_pnl)

    logger.info("  계좌 추적기 시작...")
    await tracker.start()

    # SC1 원본 핸들러 추가 등록 (tracker.start() 이후에 등록해야 WebSocket이 연결된 상태)
    try:
        sc1_client = real.SC1()
        sc1_client.on_sc1_message(on_sc1_raw)
        logger.info("  SC1 원본 핸들러 등록 완료")
    except Exception as e:
        logger.warning(f"  SC1 원본 핸들러 등록 실패: {e}")

    # 초기 상태 확인
    await asyncio.sleep(1)
    positions_before = tracker.get_positions()
    target_before = positions_before.get(TEST_SYMBOL_CODE)
    qty_before = target_before.quantity if target_before else 0
    balance_before = tracker.get_balance()
    orderable_before = balance_before.orderable_amount if balance_before else 0

    logger.info(f"\n[초기 상태]")
    logger.info(f"  {TEST_SYMBOL_NAME} 보유: {qty_before}주")
    logger.info(f"  주문가능금액: {orderable_before:,}원")
    logger.info(f"  구독 종목: {tracker.subscribed_symbols}")
    errors = tracker.get_last_errors()
    if errors:
        logger.warning(f"  초기 에러: {errors}")
    else:
        logger.info("  초기 에러: 없음")

    refresh_count_before_buy = refresh_count["value"]
    await asyncio.sleep(2)

    # 3. 시간외 단일가 매수 주문 (OrdprcPtnCode="82")
    logger.info("\n" + "=" * 60)
    logger.info(f"[Step 3] 매수 주문")
    logger.info(f"  종목: {TEST_SYMBOL_NAME} ({TEST_SYMBOL})")
    if ORDER_TYPE == "market":
        logger.info(f"  주문가: 시장가 | 수량: 1주 | 호가유형: 03(시장가)")
    else:
        logger.info(f"  주문가: {buy_price:,}원 | 수량: 1주 | 호가유형: 82(시간외단일가)")

    order_client = ls.국내주식().주문()

    buy_tr = order_client.현물주문(
        CSPAT00601.CSPAT00601InBlock1(
            IsuNo=TEST_SYMBOL,
            OrdQty=1,
            OrdPrc=float(buy_price),
            BnsTpCode="2",        # 매수
            OrdprcPtnCode=ordprc_ptn,
            MgntrnCode="000",
            LoanDt="",
            OrdCndiTpCode="0",
        )
    )
    buy_resp = await buy_tr.req_async()

    logger.info(f"  매수 응답: rsp_cd={buy_resp.rsp_cd} | rsp_msg={buy_resp.rsp_msg}")
    buy_order_no = None
    if buy_resp.block2:
        buy_order_no = buy_resp.block2.OrdNo
        logger.info(
            f"  주문번호: {buy_order_no} | "
            f"시각: {buy_resp.block2.OrdTime} | "
            f"금액: {buy_resp.block2.OrdAmt:,}원"
        )
    if buy_resp.error_msg or (buy_resp.rsp_cd not in ("00040", "00000", "00001")):
        logger.error(f"  매수 에러: {buy_resp.error_msg}")
        if ORDER_TYPE == "after_hours":
            logger.error("  시간외 단일가 접수 시간(15:20~15:30) 내에 실행하세요.")
        logger.error("  주문 실패로 테스트 중단.")
        await tracker.stop()
        return

    # 4. SC1 체결 이벤트 + 자동 갱신 대기
    logger.info(f"\n[Step 4] SC1 체결 이벤트 및 자동 갱신 대기 ({AUTO_REFRESH_WAIT}초)...")
    logger.info("  시간외 단일가는 15:40까지 체결됩니다. 체결 후 SC1 이벤트가 수신되어야 합니다.")

    wait_start = time.time()
    for i in range(AUTO_REFRESH_WAIT):
        await asyncio.sleep(1)
        elapsed = time.time() - wait_start
        if sc1_events:
            logger.info(f"  [{elapsed:.1f}s] SC1 이벤트 수신 확인됨 ({len(sc1_events)}건)")
        if refresh_count["value"] > refresh_count_before_buy:
            logger.info(f"  [{elapsed:.1f}s] 자동 갱신 감지! (총 {refresh_count['value']}회)")

    # 매수 후 상태 확인
    positions_after_buy = tracker.get_positions()
    target_after_buy = positions_after_buy.get(TEST_SYMBOL_CODE)
    qty_after_buy = target_after_buy.quantity if target_after_buy else 0
    balance_after_buy = tracker.get_balance()
    orderable_after_buy = balance_after_buy.orderable_amount if balance_after_buy else 0

    auto_refresh_triggered = refresh_count["value"] > refresh_count_before_buy
    buy_reflected = qty_after_buy > qty_before

    logger.info(f"\n[매수 결과]")
    logger.info(f"  {TEST_SYMBOL_NAME} 보유: {qty_before}주 -> {qty_after_buy}주")
    logger.info(f"  주문가능금액: {orderable_before:,} -> {orderable_after_buy:,}")
    logger.info(f"  SC1 이벤트 수신: {len(sc1_events)}건")
    logger.info(f"  자동 갱신 발동: {'YES' if auto_refresh_triggered else 'NO'}")
    logger.info(f"  잔고 반영: {'YES' if buy_reflected else 'NO (미체결 상태일 수 있음)'}")

    if not buy_reflected:
        logger.warning("  잔고 미반영 - 수동 갱신 시도...")
        await tracker.refresh_now()
        await asyncio.sleep(8)
        positions_manual = tracker.get_positions()
        target_manual = positions_manual.get(TEST_SYMBOL_CODE)
        qty_after_buy = target_manual.quantity if target_manual else 0
        buy_reflected = qty_after_buy > qty_before
        logger.info(f"  수동 갱신 후: {qty_after_buy}주 ({'반영됨' if buy_reflected else '미반영 - 아직 미체결'})")

    if qty_after_buy == 0:
        logger.warning(
            f"\n  [주의] {TEST_SYMBOL_NAME} 매수 주문이 아직 미체결 상태입니다."
            "\n  시간외 단일가는 15:40에 단일가 체결됩니다."
            "\n  지금 SC1 수신 여부만 확인하고, 매도는 체결 후 진행하세요."
        )

    # 매수 체결 여부와 관계없이 매도 가능 여부 확인 후 매도
    await asyncio.sleep(2)
    positions_current = tracker.get_positions()
    target_current = positions_current.get(TEST_SYMBOL_CODE)
    qty_current = target_current.quantity if target_current else 0

    if qty_current < 1:
        logger.info(f"\n  매도 가능 수량: {qty_current}주 (매수 미체결 상태로 매도 스킵)")
        logger.info("  체결 후 수동으로 매도하거나 미체결 취소를 진행하세요.")

        # 미체결 주문 확인
        open_orders = tracker.get_open_orders()
        if open_orders:
            logger.info(f"\n[미체결 주문 목록]")
            for ono, order in open_orders.items():
                logger.info(
                    f"  주문번호:{ono} {order.symbol} {order.order_type} "
                    f"{order.order_qty}주@{order.order_price:,}원 "
                    f"미체결:{order.remaining_qty}주"
                )
    else:
        # 5. 매도 주문 (시간외 단일가)
        logger.info(f"\n[Step 5] 시간외 단일가 매도 주문")
        logger.info(f"  종목: {TEST_SYMBOL_NAME} | 주문가: {buy_price:,}원 | 수량: 1주")

        refresh_count_before_sell = refresh_count["value"]

        sell_tr = order_client.현물주문(
            CSPAT00601.CSPAT00601InBlock1(
                IsuNo=TEST_SYMBOL,
                OrdQty=1,
                OrdPrc=float(buy_price),
                BnsTpCode="1",        # 매도
                OrdprcPtnCode=ordprc_ptn,
                MgntrnCode="000",
                LoanDt="",
                OrdCndiTpCode="0",
            )
        )
        sell_resp = await sell_tr.req_async()

        logger.info(f"  매도 응답: rsp_cd={sell_resp.rsp_cd} | rsp_msg={sell_resp.rsp_msg}")
        sell_order_no = None
        if sell_resp.block2:
            sell_order_no = sell_resp.block2.OrdNo
            logger.info(
                f"  주문번호: {sell_order_no} | "
                f"시각: {sell_resp.block2.OrdTime} | "
                f"금액: {sell_resp.block2.OrdAmt:,}원"
            )
        if sell_resp.error_msg:
            logger.error(f"  매도 에러: {sell_resp.error_msg}")

        # 6. 매도 SC1 이벤트 + 자동 갱신 대기
        logger.info(f"\n[Step 6] 매도 SC1 이벤트 및 자동 갱신 대기 ({AUTO_REFRESH_WAIT}초)...")

        for i in range(AUTO_REFRESH_WAIT):
            await asyncio.sleep(1)
            elapsed = (i + 1)
            if refresh_count["value"] > refresh_count_before_sell:
                logger.info(f"  [{elapsed}s] 매도 후 자동 갱신 감지!")

        positions_after_sell = tracker.get_positions()
        target_after_sell = positions_after_sell.get(TEST_SYMBOL_CODE)
        qty_after_sell = target_after_sell.quantity if target_after_sell else 0
        balance_after_sell = tracker.get_balance()
        orderable_after_sell = balance_after_sell.orderable_amount if balance_after_sell else 0

        sell_auto_refresh = refresh_count["value"] > refresh_count_before_sell
        sell_reflected = qty_after_sell < qty_current

        logger.info(f"\n[매도 결과]")
        logger.info(f"  {TEST_SYMBOL_NAME} 보유: {qty_current}주 -> {qty_after_sell}주")
        logger.info(f"  주문가능금액: {orderable_after_buy:,} -> {orderable_after_sell:,}")
        logger.info(f"  자동 갱신 발동: {'YES' if sell_auto_refresh else 'NO'}")
        logger.info(f"  잔고 반영: {'YES' if sell_reflected else 'NO'}")

    # 7. 최종 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("=== SC1 자동 갱신 버그 수정 검증 최종 결과 ===")
    logger.info(f"  SC1 원본 이벤트 수신: {len(sc1_events)}건")
    for ev in sc1_events:
        logger.info(f"    {ev}")
    logger.info(f"\n  자동 갱신 총 발동 횟수: {refresh_count['value']}회")
    logger.info(f"\n  이벤트 타임라인 ({len(events)}건):")
    for ev in events:
        logger.info(f"    {ev}")

    final_errors = tracker.get_last_errors()
    if final_errors:
        logger.error(f"\n  최종 에러: {final_errors}")
    else:
        logger.info("\n  최종 에러: 없음")

    # 핵심 판정
    logger.info("\n[핵심 검증 결과]")
    if sc1_events:
        logger.info("  SC1 이벤트 수신:       [OK] - WebSocket으로 체결 이벤트 수신됨")
    else:
        logger.warning("  SC1 이벤트 수신:       [WAIT] - 아직 체결 없음 (시간외 단일가 15:40 체결)")

    if refresh_count["value"] > 0:
        logger.info(f"  자동 갱신(_schedule_coroutine): [OK] - {refresh_count['value']}회 정상 발동")
    else:
        logger.warning("  자동 갱신(_schedule_coroutine): [PENDING] - SC1 체결 후 확인 필요")

    logger.info(
        "\n  [참고] 시간외 단일가는 15:40에 체결됩니다."
        "\n  체결 후 SC1 수신 -> _schedule_coroutine() -> _delayed_refresh() -> _fetch_all_data() 경로로 자동 갱신됩니다."
        "\n  'no running event loop' 에러가 발생하지 않으면 버그 수정 성공입니다."
    )

    await tracker.stop()
    logger.info("\n계좌 추적기 종료. 테스트 완료.")


if __name__ == "__main__":
    asyncio.run(run_test())
