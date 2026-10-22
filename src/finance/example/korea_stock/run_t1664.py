import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1664

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1664():
    """t1664 투자자매매종합(차트) 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(1) 수량(1) 일별(1) 최근 20건 조회
    m = ls.국내주식().투자자().투자자매매종합차트(
        t1664.T1664InBlock(mgubun="1", vagubun="1", bdgubun="1", cnt=20)
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'일자':>10} {'개인':>12} {'외인계':>12} {'기관계':>12}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.sv_08:>12,} {item.sv_17:>12,} {item.sv_18:>12,}"
        )


if __name__ == "__main__":
    test_req_t1664()
