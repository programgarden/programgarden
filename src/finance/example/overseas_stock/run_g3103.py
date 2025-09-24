import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3103
from programgarden_core import pg_logger, pg_log
import asyncio

load_dotenv()


async def test_req_g3103():

    pg_log(logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    m_g3103 = ls.overseas_stock().chart().일주월조회(
        g3103.G3103InBlock(
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA",
            gubun="4",
            date="20250120"
        )
    )
    result = await m_g3103.req_async()
    pg_logger.debug(f"Response: {result}, Status: {result.header}")


if __name__ == "__main__":
    asyncio.run(test_req_g3103())
