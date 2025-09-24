import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3101
from programgarden_core import pg_logger, pg_log

load_dotenv()


async def test_req_o3101():

    pg_log(logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    test1 = ls.overseas_futureoption().market().해외선물마스터조회(
        body=o3101.O3101InBlock(
            gubun="1"
        )
    )
    print(await test1.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_o3101())
