"""
해외주식 취소 주문 (COSAT00301, OrdPtnCode="08") 예시

해외주식에는 별도 취소 TR 이 없다. 신규 주문과 같은 COSAT00301 에 OrdPtnCode="08" 과
원주문번호(OrgOrdNo)를 실어 보낸다. `COSMT00300` 은 "해외증권 매도상환주문"이라 취소가 아니다.

필드 구성은 플랫폼에서 실계좌로 검증된 취소 요청과 같다.
- RecCnt=1, OrdPtnCode="08", OrgOrdNo=원주문번호, OrdMktCode(81 뉴욕 / 82 NASDAQ), IsuNo=종목
- OrdQty=0 → 남은 수량 전체 취소 (2026-08-19 실계좌 1주 주문으로 확인)
- OvrsOrdPrc=0.0, OrdprcPtnCode="00"

관측 (2026-08-19, 실계좌 1주 미체결 주문):
- 응답 rsp_cd="00156" "취소주문이 완료되었습니다." 와 함께 **취소 전용 새 주문번호**가 나온다.
- 거부되어도 OutBlock2 가 올 수 있고 이때 OrdNo 만 비어 있다. OrdNo 가 비었거나 0 이면
  접수되지 않은 것으로 본다.

⚠️ 실계좌에서 실제 취소가 나간다. 실행 전에 원주문번호·시장·종목을 다시 확인하세요.

사용법:
    APPKEY=... APPSECRET=... ORIGINAL_ORDER_NO=12345 SYMBOL=AAPL MARKET=82 \\
        python run_COSAT00301_cancel.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from programgarden_finance import LS, COSAT00301
from programgarden_finance.ls.models import SetupOptions

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()


async def cancel_order():
    original_order_no = os.getenv("ORIGINAL_ORDER_NO", "").strip()
    symbol = os.getenv("SYMBOL", "").strip().upper()
    market = os.getenv("MARKET", "").strip()  # 81: 뉴욕거래소, 82: NASDAQ

    if not original_order_no.isdigit() or not symbol or market not in {"81", "82"}:
        print("ORIGINAL_ORDER_NO(숫자), SYMBOL, MARKET(81 또는 82)을 환경 변수로 지정하세요.")
        return

    ls = LS()  # 새 인스턴스 (싱글톤 아님)
    if ls.login(appkey=os.getenv("APPKEY"), appsecretkey=os.getenv("APPSECRET")) is False:
        logger.error("로그인 실패")
        return

    print("=" * 50)
    print("📝 해외주식 취소 주문 정보")
    print(f"  원주문번호: {original_order_no}")
    print(f"  종목: {symbol} / 시장: {market}")
    print("  수량: 남은 수량 전체 (OrdQty=0)")
    print("=" * 50)

    if os.getenv("AUTO_CONFIRM") != "1":
        if input("\n취소 주문을 보내시겠습니까? (y/n): ").lower() != "y":
            print("보내지 않았습니다.")
            return

    tr = ls.overseas_stock().주문().cosat00301(
        COSAT00301.COSAT00301InBlock1(
            RecCnt=1,
            OrdPtnCode="08",              # 08: 취소
            OrgOrdNo=int(original_order_no),
            OrdMktCode=market,
            IsuNo=symbol,
            OrdQty=0,                     # 0: 남은 수량 전체 취소
            OvrsOrdPrc=0.0,               # 취소 시 가격 0
            OrdprcPtnCode="00",
        ),
        options=SetupOptions(on_rate_limit="wait"),
    )

    # 주문 TR 은 일시 실패를 자동 재시도하지 않는다 — 결과가 불분명하면 미체결 조회로 확인한다.
    result = await tr.req_async()

    print(f"\n응답 코드: {result.rsp_cd}")
    print(f"응답 메시지: {result.rsp_msg}")
    if result.error_msg:
        print(f"❌ 오류: {result.error_msg}")
        return

    order_no = str(getattr(result.block2, "OrdNo", "") or "").strip() if result.block2 else ""
    if not order_no or order_no == "0":
        print("❌ 취소가 접수되지 않았습니다 (주문번호 없음).")
        return
    print(f"✅ 취소 접수 — 취소 주문번호: {order_no}")


if __name__ == "__main__":
    asyncio.run(cancel_order())
