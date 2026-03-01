import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1516

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1516():
    """t1516 업종별종목시세 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 반도체(042) 업종 등락률순(1) 조회
    m = ls.국내주식().업종테마().업종별종목시세(
        t1516.T1516InBlock(upcode="042", gubun="1")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(shcode): {response.cont_block.shcode}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'종목명':<14} {'현재가':>10} {'전일대비':>10} {'등락률':>8} {'거래량':>12}")
    logger.info("-" * 100)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{item.hname:<14} {item.price:>10,} {sign_str}{item.change:>+9,} "
            f"{item.diff:>+7.2f}% {item.volume:>12,}"
        )


if __name__ == "__main__":
    test_req_t1516()
