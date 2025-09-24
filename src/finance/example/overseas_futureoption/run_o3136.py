import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3136
from programgarden_core import pg_logger, pg_log

load_dotenv()


async def test_req_o3136():

    pg_log(logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().해외선물옵션_시간대별Tick체결조회(
        body=o3136.O3136InBlock(
            gubun="0",
            mktgb="F",
            shcode="",
            readcnt=20,
            cts_seq=0
        )
    )
    await req.occurs_req_async(
        callback=lambda response, status: pg_logger.debug(f"Retrying request: {response.block1 if response is not None else 'None'}, status: {status}"),
    )

if __name__ == "__main__":
    asyncio.run(test_req_o3136())
