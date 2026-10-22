import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1904

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1904():
    """t1904 ETF구성종목조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # KODEX 200 (069500) 구성종목 평가금액순(1) 조회
    m = ls.국내주식().ETF().ETF구성종목조회(
        t1904.T1904InBlock(shcode="069500", sgb="1")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    # 요약 정보
    summary = response.cont_block
    if summary is None:
        logger.info("데이터 없음 (해당 ETF 또는 일자에 구성종목 정보 없음)")
        return
    logger.info(f"ETF 운용사: {summary.opcom_nmk}")
    logger.info(f"NAV: {summary.nav:,.2f}, 순자산총액: {summary.etftotcap:,}")

    logger.info(f"\n구성종목: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'종목코드':>8} {'종목명':<14} {'현재가':>10} {'수량':>10} {'평가금액':>14} {'비중':>8}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.shcode:>8} {item.hname:<14} {item.price:>10,} "
            f"{item.volume:>10,} {item.pvalue:>14,} {item.weight:>7.2f}%"
        )


if __name__ == "__main__":
    test_req_t1904()
