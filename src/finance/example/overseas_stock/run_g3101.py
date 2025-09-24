import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3101
from programgarden_core import pg_logger, pg_log
import asyncio

load_dotenv()


async def test_req_g3101():

    pg_log(logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    m_g3101 = ls.overseas_stock().market().현재가조회(
        g3101.G3101InBlock(
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA"
        )
    )

    await m_g3101.retry_req_async(
        callback=lambda response, status: pg_logger.debug(f"Retrying request: {response}, status: {status}"),
    )


if __name__ == "__main__":
    asyncio.run(test_req_g3101())
