import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1621

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1621():
    """t1621 업종별분별투자자매매동향 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(001) 당일(0) 조회
    m = ls.국내주식().투자자().업종별분별투자자매매동향(
        t1621.T1621InBlock(upcode="001", bgubun="0")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    # 요약 정보
    summary = response.cont_block
    logger.info(f"업종명: {summary.upname}, 코드: {summary.upcode}")

    logger.info(f"\n시간대별: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'시간':>10} {'개인':>12} {'외인계':>12} {'기관계':>12}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.time:>10} {item.sv_08:>12,} {item.sv_17:>12,} {item.sv_18:>12,}"
        )


if __name__ == "__main__":
    test_req_t1621()
