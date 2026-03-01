import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1603

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1603():
    """t1603 시간대별투자자매매추이상세 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(1) 외국인(8) 당일(0) 조회
    m = ls.국내주식().투자자().시간대별투자자매매추이상세(
        t1603.T1603InBlock(market="1", gubun1="8", gubun2="0")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(cts_time): {response.cont_block.cts_time}, cts_idx: {response.cont_block.cts_idx}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'시간':>10} {'매수':>12} {'매도':>12} {'순매수':>12}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.time:>10} {item.buy:>12,} {item.sell:>12,} {item.sum:>12,}"
        )


if __name__ == "__main__":
    test_req_t1603()
