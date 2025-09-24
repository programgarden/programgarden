import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, CIDEQ00800
from programgarden_core import pg_logger, pg_log

load_dotenv()


async def test_req_CIDEQ00800():

    pg_log(logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().accno().CIDEQ00800(
        body=CIDEQ00800.CIDEQ00800InBlock1(
            RecCnt=1,
            TrdDt="20241004"
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_CIDEQ00800())
