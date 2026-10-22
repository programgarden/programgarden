import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, o3108
import logging
logger = logging.getLogger(__name__)
import asyncio

load_dotenv()


async def test_req_o3108():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    test1 = ls.overseas_futureoption().chart().o3108(
        o3108.O3108InBlock(
            shcode="ADZ25",
            gubun="0",
            qrycnt=20,
            sdate="20251031",
            edate="20251102",
            cts_date=""
        )

    )
    # result = test1.req()
    # logger.debug(f"Response: {result}, Status: {result.header}")

    await asyncio.sleep(1)
    await test1.occurs_req_async(
        callback=lambda response, status: logger.debug(f"Success: {status}, response: {len(response.block1) if response and hasattr(response, 'block1') else None}")
    )


if __name__ == "__main__":
    asyncio.run(test_req_o3108())
