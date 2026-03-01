import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CSPAQ13700

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CSPAQ13700():
    """CSPAQ13700 현물계좌 주문체결내역 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 전체시장(00) 전체매매(0) 당일 주문체결내역 조회
    m = ls.국내주식().계좌().현물계좌주문체결내역()

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    # 요약
    summary = response.block2
    logger.info(f"매도체결금액: {summary.SellExecAmt:,}, 매수체결금액: {summary.BuyExecAmt:,}")

    logger.info(f"\n주문내역: {len(response.block3)}건")
    if not response.block3:
        logger.info("당일 주문내역 없음")
        return

    logger.info("=" * 120)
    logger.info(f"{'주문번호':>10} {'종목명':<14} {'매매구분':>8} {'주문수량':>8} {'주문단가':>10} {'체결수량':>8} {'체결단가':>10} {'주문시각':>10}")
    logger.info("-" * 120)

    for item in response.block3:
        logger.info(
            f"{item.OrdNo:>10} {item.IsuNm:<14} {item.BnsTpNm:>8} "
            f"{item.OrdQty:>8,} {item.OrdPrc:>10,.0f} {item.ExecQty:>8,} "
            f"{item.ExecPrc:>10,.0f} {item.OrdTime:>10}"
        )


if __name__ == "__main__":
    test_req_CSPAQ13700()
