import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3202
from programgarden_core import pg_logger, pg_log
import asyncio

load_dotenv()


async def test_req_g3202():

    pg_log(logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    m_g3202 = ls.overseas_stock().chart().차트N틱조회(
        g3202.G3202InBlock(
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA",
            ncnt=100,
            qrycnt=500,
            sdate="20231001",
            edate="",
        )
    )
    result = m_g3202.req()
    pg_logger.debug(f"Response: {result}, Status: {result.header}")

    await asyncio.sleep(1)
    await m_g3202.occurs_req_async(
        callback=lambda response, status: pg_logger.debug(f"Success: {status}, response: {response.block1[0].loctime if response and hasattr(response, 'block') else None}")
    )


if __name__ == "__main__":
    asyncio.run(test_req_g3202())
