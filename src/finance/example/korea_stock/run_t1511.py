import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1511

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1511():
    """t1511 업종현재가 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(001) 업종현재가 조회
    m = ls.국내주식().업종테마().업종현재가(
        t1511.T1511InBlock(upcode="001")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    item = response.block
    sign_str = {
        "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
    }.get(item.sign, item.sign)

    logger.info("=" * 60)
    logger.info(f"업종명: {item.hname}")
    logger.info(f"현재지수: {item.pricejisu:,.2f} ({sign_str}{item.change:+,.2f}, {item.diff:+.2f}%)")
    logger.info(f"거래량: {item.volume:,}")
    logger.info(f"거래대금: {item.value:,}")
    logger.info(f"상승: {item.upjisu}  보합: {item.ssjisu}  하락: {item.dnjisu}")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_req_t1511()
