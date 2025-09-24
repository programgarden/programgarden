import logging
from dotenv import dotenv_values
import os
from programgarden_finance import LS, g3106
from programgarden_core import pg_logger, pg_log
import asyncio


config = dotenv_values(".env")


async def test_req_g3106():

    pg_log(logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    m_g3106 = ls.overseas_stock().market().현재가호가조회(
        g3106.G3106InBlock(
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA"
        )
    )
    await m_g3106.retry_req_async(
        callback=lambda response, status: pg_logger.debug(f"Retrying request: {response}, status: {status}"),
    )

if __name__ == "__main__":
    asyncio.run(test_req_g3106())
