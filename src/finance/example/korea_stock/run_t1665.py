import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1665

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1665():
    """t1665 기간별투자자매매추이 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(1) 수치(1) 일별(1) 최근 1개월 조회
    m = ls.국내주식().차트().기간별투자자매매추이(
        t1665.T1665InBlock(market="1", gubun2="1", gubun3="1", from_date="20260201", to_date="20260228")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'일자':>10} {'개인':>12} {'외인계':>12} {'기관계':>12} {'지수':>10}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.sv_08:>12,} {item.sv_17:>12,} "
            f"{item.sv_18:>12,} {item.jisu:>10.2f}"
        )


if __name__ == "__main__":
    test_req_t1665()
