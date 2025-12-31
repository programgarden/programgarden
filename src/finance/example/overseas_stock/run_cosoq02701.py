import logging
from dotenv import load_dotenv
import os
from programgarden_finance import COSOQ02701, LS
import logging
logger = logging.getLogger(__name__)
import asyncio

load_dotenv()


async def test_req_cosoq02701():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS.get_instance()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    cosoq02701 = ls.overseas_stock().accno().cosoq02701(
        COSOQ02701.COSOQ02701InBlock1(
            RecCnt=1,
            CrcyCode="USD",
        ),
    )

    result = await cosoq02701.req_async()
    logger.debug(f"Result: {result}")

    # await cosoq02701.retry_req_async(
    #     callback=lambda x, status: logger.debug(f"Response: {x}, Status: {status}"),
    # )


if __name__ == "__main__":
    asyncio.run(test_req_cosoq02701())
