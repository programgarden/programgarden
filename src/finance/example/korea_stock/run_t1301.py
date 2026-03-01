import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1301

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1301():
    """t1301 주식시간대별체결조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 시간대별 체결 조회
    m_t1301 = ls.국내주식().시세().주식시간대별체결조회(
        t1301.T1301InBlock(shcode="005930")
    )

    response = m_t1301.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(cts_time): {response.cont_block.cts_time}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'체결시간':>10} {'현재가':>10} {'전일대비':>10} {'등락률':>8} {'체결량':>10} {'매도체결':>10} {'매수체결':>10}")
    logger.info("-" * 100)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{item.chetime:>10} {item.price:>10,} {sign_str}{item.change:>+9,} {item.diff:>+7.2f}% "
            f"{item.cvolume:>10,} {item.mdvolume:>10,} {item.msvolume:>10,}"
        )


if __name__ == "__main__":
    test_req_t1301()
