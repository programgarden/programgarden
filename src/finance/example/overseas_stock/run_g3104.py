import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3104
from programgarden_core import pg_logger, pg_log
import asyncio


load_dotenv()


async def test_req_g3104():

    pg_log(logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    m_g3104 = ls.overseas_stock().market().종목정보조회(
        g3104.G3104InBlock(
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA"
        )
    )
    result = m_g3104.req()
    pg_logger.debug(f"Response: {result}, Status: {result.header}")

    await asyncio.sleep(1)
    await m_g3104.retry_req_async(
        callback=lambda response, status: pg_logger.debug(f"Success: {status}, response: {response.block if response and hasattr(response, 'block') else None}")
    )


if __name__ == "__main__":
    asyncio.run(test_req_g3104())
