import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3106
from programgarden_core import pg_logger, pg_log

load_dotenv()


async def test_req_o3106():

    pg_log(logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().해외선물_현재가호가조회(
        body=o3106.O3106InBlock(
            symbol="CUSU25"
        )
    )
    await req.retry_req_async(
        callback=lambda resp, status: pg_logger.info(f"o3106 요청 상태: {status}, 응답: {resp}"),
        max_retries=5,
        delay=1
    )

if __name__ == "__main__":
    asyncio.run(test_req_o3106())
