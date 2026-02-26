import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t0425

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t0425():
    """t0425 주식체결/미체결 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 전체 종목, 전체 구분 주문 체결/미체결 조회
    m_t0425 = ls.국내주식().계좌().주식체결미체결(
        t0425.T0425InBlock(expcode="", chegb="0", medosu="0", sortgb="1")
    )

    response = m_t0425.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(cts_ordno): {response.cont_block.cts_ordno}")

    logger.info(f"조회 건수: {len(response.block)}건")

    if not response.block:
        logger.info("체결/미체결 내역이 없습니다.")
        return

    logger.info("=" * 130)
    logger.info(f"{'주문번호':>10} {'종목명':<14} {'매매':>4} {'주문가':>10} {'주문수량':>8} {'체결수량':>8} {'미체결':>8} {'상태':<10}")
    logger.info("-" * 130)

    for item in response.block:
        medosu_str = {"1": "매도", "2": "매수"}.get(item.medosu, item.medosu)
        logger.info(
            f"{item.ordno:>10} {item.hname:<14} {medosu_str:>4} {item.price:>10,} "
            f"{item.qty:>8,} {item.cheqty:>8,} {item.ordrem:>8,} {item.status:<10}"
        )


if __name__ == "__main__":
    test_req_t0425()
