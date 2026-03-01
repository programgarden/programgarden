import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1617

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1617():
    """t1617 투자자매매종합2 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(1) 수량(1) 일별(1) 조회
    m = ls.국내주식().투자자().투자자매매종합(
        t1617.T1617InBlock(gubun1="1", gubun2="1", gubun3="1")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(cts_date): {response.cont_block.cts_date}, cts_time: {response.cont_block.cts_time}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'일자':>10} {'개인':>12} {'외인계':>12} {'기관계':>12}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.sv_08:>12,} {item.sv_17:>12,} {item.sv_18:>12,}"
        )


if __name__ == "__main__":
    test_req_t1617()
