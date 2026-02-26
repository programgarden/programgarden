import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CSPAQ12300

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CSPAQ12300():
    """CSPAQ12300 현물계좌 잔고내역 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 현물계좌 잔고내역 조회 (기본값)
    m_cspaq12300 = ls.국내주식().계좌().현물계좌잔고내역()

    response = m_cspaq12300.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.block2:
        b = response.block2
        logger.info(f"=== 계좌 요약 ===")
        logger.info(f"평가손익합계: {b.PnlSumAmt:,}원 | 총평가금액: {b.AsmtTotamt:,}원")

    if response.block3:
        logger.info(f"=== 보유 종목 ({len(response.block3)}건) ===")
        logger.info(f"{'종목명':<14} {'수량':>8} {'현재가':>10} {'평가금액':>14} {'손익금액':>12} {'수익률':>8}")
        logger.info("-" * 80)

        for item in response.block3:
            logger.info(
                f"{item.IsuNm:<14} {item.BalQty:>8,} {item.NowPrc:>10,} "
                f"{item.AsmtAmt:>14,} {item.PnlAmt:>12,} {item.Ernrat:>7.2f}%"
            )


if __name__ == "__main__":
    test_req_CSPAQ12300()
