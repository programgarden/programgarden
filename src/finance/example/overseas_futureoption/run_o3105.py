import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3105
from programgarden_core import pg_logger, pg_log

load_dotenv()


async def test_req_o3105():

    pg_log(logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE"),
        paper_trading=True
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().o3105(
        body=o3105.O3105InBlock(
            symbol="ESZ25"
        )
    )

    result = await req.req_async()
    print(result)

    # while True:
    #     await asyncio.sleep(1)

    # await req.retry_req_async(
    #     callback=lambda resp, status: pg_logger.info(f"o3105 요청 상태: {status}, 응답: {resp}"),
    #     max_retries=5,
    #     delay=1
    # )

if __name__ == "__main__":
    asyncio.run(test_req_o3105())
