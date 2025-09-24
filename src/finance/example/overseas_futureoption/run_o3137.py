import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3137
from programgarden_core import pg_logger, pg_log

load_dotenv()


async def test_req_o3137():

    pg_log(logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().해외선물옵션_차트NTick체결조회(
        body=o3137.O3137InBlock(
            mktgb="F",
            shcode="ADM23",
            ncnt=1,
            qrycnt=20,
            cts_seq="",
            cts_daygb=""
        )
    )
    await req.occurs_req_async(
        callback=lambda response, status: pg_logger.debug(f"Retrying request: {response.block1 if response is not None else 'None'}, status: {status}"),
    )

if __name__ == "__main__":
    asyncio.run(test_req_o3137())
