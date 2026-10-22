import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t8450

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t8450():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # S-Oil(010950) KRX 호가 조회
    m_t8450 = ls.국내주식().시세().주식현재가호가조회(
        t8450.T8450InBlock(shcode="010950", exchgubun="K")
    )

    response = m_t8450.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.block:
        b = response.block
        logger.info(f"종목: {b.hname} ({b.shcode})")
        logger.info(f"현재가: {b.price} | 전일대비: {b.change} ({b.diff}%)")
        logger.info(f"시가: {b.open} | 고가: {b.high} | 저가: {b.low}")
        logger.info(f"거래량: {b.volume}")
        logger.info(f"상한가: {b.uplmtprice} | 하한가: {b.dnlmtprice}")
        logger.info("--- 호가 ---")
        for i in range(1, 11):
            offer = getattr(b, f"offerho{i}")
            bid = getattr(b, f"bidho{i}")
            offer_rem = getattr(b, f"offerrem{i}")
            bid_rem = getattr(b, f"bidrem{i}")
            logger.info(f"  매도{i:2d}: {offer:>8,} ({offer_rem:>8,}) | 매수{i:2d}: {bid:>8,} ({bid_rem:>8,})")
        logger.info(f"  매도합: {b.offer:>8,} | 매수합: {b.bid:>8,}")


if __name__ == "__main__":
    test_req_t8450()
