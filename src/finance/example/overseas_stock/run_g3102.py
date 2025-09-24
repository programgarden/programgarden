import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3102
from programgarden_core import pg_logger, pg_log
import asyncio

load_dotenv()


async def test_req_g3102():

    pg_log(logging.DEBUG)

    ls = LS.get_instance()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    m_g3102 = ls.overseas_stock().market().시간대별조회(
        g3102.G3102InBlock(
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA",
            readcnt=30,
        )
    )
    await m_g3102.occurs_req_async(
        callback=lambda response, status: pg_logger.debug(f"Retrying request: {response.block.cts_seq if response is not None else 'None'}, status: {status}"),
    )

if __name__ == "__main__":
    asyncio.run(test_req_g3102())
