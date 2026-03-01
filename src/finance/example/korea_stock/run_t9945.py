import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t9945

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t9945():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # KOSPI 종목 조회
    m_t9945 = ls.국내주식().시세().주식마스터조회(
        t9945.T9945InBlock(gubun="1")
    )

    response = m_t9945.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    logger.info(f"KOSPI 종목 수: {len(response.block)}")

    for item in response.block[:5]:
        logger.info(f"  {item.hname} ({item.shcode}) - 확장코드: {item.expcode}, ETF: {item.etfchk}")

    # KOSDAQ 종목 조회
    m_t9945_kosdaq = ls.국내주식().시세().주식마스터조회(
        t9945.T9945InBlock(gubun="2")
    )

    response_kosdaq = m_t9945_kosdaq.req()

    if response_kosdaq.error_msg:
        logger.error(f"KOSDAQ 요청 실패: {response_kosdaq.error_msg}")
        return

    logger.info(f"KOSDAQ 종목 수: {len(response_kosdaq.block)}")

    for item in response_kosdaq.block[:5]:
        logger.info(f"  {item.hname} ({item.shcode}) - 확장코드: {item.expcode}, ETF: {item.etfchk}")


if __name__ == "__main__":
    test_req_t9945()
