import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, o3139
from programgarden_core import pg_logger, pg_log
import asyncio

load_dotenv()


async def test_req_o3139():

    pg_log(logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    test1 = ls.overseas_futureoption().chart().o3139(
        o3139.O3139InBlock(
            mktgb="F",
            shcode="CUSU25",
            ncnt=1,
            qrycnt=20,
            cts_seq="",
            cts_daygb=""
        )

    )
    # result = test1.req()
    # pg_logger.debug(f"Response: {result}, Status: {result.header}")

    await asyncio.sleep(1)
    await test1.occurs_req_async(
        callback=lambda response, status: pg_logger.debug(f"Success: {status}, response: {len(response.block1) if response and hasattr(response, 'block1') else None}")
    )


if __name__ == "__main__":
    asyncio.run(test_req_o3139())
