import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3190
from programgarden_core import pg_logger, pg_log
import asyncio

load_dotenv()


async def test_req_g3190():

    pg_log(logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    m_g3190 = ls.overseas_stock().시세().마스터상장종목조회(
        g3190.G3190InBlock(
            delaygb="R",
            natcode="US",
            exgubun="2",
            readcnt=500,
            cts_value=""
        )
    )

    await asyncio.sleep(1)
    await m_g3190.occurs_req_async(
        callback=lambda response, status: pg_logger.debug(f"Success: {status}, response: {len(response.block1) if response and hasattr(response, 'block1') else None}")
    )


if __name__ == "__main__":
    asyncio.run(test_req_g3190())
