import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1109

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1109():
    """t1109 시간외체결량 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 시간외 체결 조회
    m_t1109 = ls.국내주식().시세().시간외체결량(
        t1109.T1109InBlock(shcode="005930")
    )

    response = m_t1109.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(
            f"연속조회 컨텍스트 — ctsshcode: {response.cont_block.ctsshcode}, "
            f"ctschetime: {response.cont_block.ctschetime}, idx: {response.cont_block.idx}"
        )

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(
        f"{'시간':>10} {'현재가':>10} {'전일대비':>10} {'등락률':>8} "
        f"{'체결량':>10} {'체결강도':>10} {'누적거래량':>12}"
    )
    logger.info("-" * 100)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.dan_sign, item.dan_sign)

        logger.info(
            f"{item.dan_chetime:>10} {item.dan_price:>10,} "
            f"{sign_str}{item.dan_change:>+9,} {item.diff:>+7.2f}% "
            f"{item.dan_cvolume:>10,} {item.chdegree:>10.2f} {item.dan_volume:>12,}"
        )


def test_occurs_req_t1109():
    """t1109 시간외체결량 연속조회 테스트 (전체 페이지 수집)"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1109 = ls.국내주식().시세().시간외체결량(
        t1109.T1109InBlock(shcode="005930")
    )

    responses = m_t1109.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)}, 총 체결 행: {total}건")


if __name__ == "__main__":
    test_req_t1109()
