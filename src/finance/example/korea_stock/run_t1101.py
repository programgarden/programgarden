import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1101

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1101():
    """t1101 주식현재가호가조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 현재가 호가 조회
    m_t1101 = ls.국내주식().시세().주식현재가호가(
        t1101.T1101InBlock(shcode="005930")
    )

    response = m_t1101.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.block:
        b = response.block
        sign_str = {
            "1": "상한", "2": "상승", "3": "보합", "4": "하한", "5": "하락"
        }.get(b.sign, b.sign)

        logger.info(f"종목: {b.hname} ({b.shcode})")
        logger.info(f"현재가: {b.price:,} ({sign_str} {b.change:,} / {b.diff}%)")
        logger.info(f"거래량: {b.volume:,} | 전일종가: {b.jnilclose:,}")
        logger.info(f"시가: {b.open:,} | 고가: {b.high:,} | 저가: {b.low:,}")
        logger.info(f"상한가: {b.uplmtprice:,} | 하한가: {b.dnlmtprice:,}")
        logger.info(f"수신시간: {b.hotime}")

        logger.info("--- 매도호가 (위→아래) ---")
        for i in range(10, 0, -1):
            ho = getattr(b, f"offerho{i}")
            rem = getattr(b, f"offerrem{i}")
            cha = getattr(b, f"preoffercha{i}")
            if ho > 0:
                logger.info(f"  매도{i:>2}: {ho:>8,} | 수량: {rem:>10,} | 대비: {cha:>+8,}")

        logger.info("--- 매수호가 (위→아래) ---")
        for i in range(1, 11):
            ho = getattr(b, f"bidho{i}")
            rem = getattr(b, f"bidrem{i}")
            cha = getattr(b, f"prebidcha{i}")
            if ho > 0:
                logger.info(f"  매수{i:>2}: {ho:>8,} | 수량: {rem:>10,} | 대비: {cha:>+8,}")

        logger.info(f"매도합: {b.offer:,} | 매수합: {b.bid:,}")

        if b.yeprice > 0:
            logger.info(f"예상체결: {b.yeprice:,} (수량: {b.yevolume:,})")


if __name__ == "__main__":
    test_req_t1101()
