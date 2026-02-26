import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t0424

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t0424():
    """t0424 주식잔고2 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 주식잔고2 조회 (BEP단가, 체결기준잔고)
    m_t0424 = ls.국내주식().계좌().주식잔고2(
        t0424.T0424InBlock(prcgb="2", chegb="2", dangb="0", charge="1")
    )

    response = m_t0424.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(cts_expcode): {response.cont_block.cts_expcode}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 120)
    logger.info(f"{'종목명':<14} {'잔고수량':>8} {'현재가':>10} {'매입가':>10} {'평가금액':>14} {'손익금액':>12} {'수익률':>8}")
    logger.info("-" * 120)

    for item in response.block:
        logger.info(
            f"{item.hname:<14} {item.janqty:>8,} {item.price:>10,} {item.pamt:>10,} "
            f"{item.appamt:>14,} {item.dtsunik:>12,} {item.sunikrt:>7.2f}%"
        )


if __name__ == "__main__":
    test_req_t0424()
