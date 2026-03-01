import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1601

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1601():
    """t1601 투자자별종합 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 주식금액(1) 옵션금액(1) 선물금액(1) 조회
    m = ls.국내주식().투자자().투자자별종합(
        t1601.T1601InBlock(gubun1="1", gubun2="1", gubun4="1")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    # 코스피(block1) 주요 투자자 출력
    b = response.block1
    if b:
        logger.info("\n[코스피 투자자별 매매 현황]")
        logger.info("=" * 60)
        logger.info(f"{'투자자':>10} {'매수':>14} {'매도':>14} {'순매수':>14}")
        logger.info("-" * 60)
        logger.info(f"{'개인':>10} {b.ms_08:>14,} {b.md_08:>14,} {b.svolume_08:>14,}")
        logger.info(f"{'외국인계':>10} {b.ms_17:>14,} {b.md_17:>14,} {b.svolume_17:>14,}")
        logger.info(f"{'기관계':>10} {b.ms_18:>14,} {b.md_18:>14,} {b.svolume_18:>14,}")
        logger.info("=" * 60)


if __name__ == "__main__":
    test_req_t1601()
