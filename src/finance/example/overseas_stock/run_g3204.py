import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3204
import logging
logger = logging.getLogger(__name__)
import asyncio


load_dotenv()


async def test_req_g3204():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS.get_instance()
    login_result = await ls.async_login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    test1 = ls.overseas_stock().차트().차트일주월년별조회(
        g3204.G3204InBlock(
            sujung="Y",
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA",
            gubun="2",
            qrycnt=500,
            comp_yn="N",
            sdate="20230203",
            edate="20250505"
        )
    )

    asyncio.create_task(test1.req_async())

    test2 = ls.overseas_stock().차트().차트일주월년별조회(
        g3204.G3204InBlock(
            sujung="Y",
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA",
            gubun="2",
            qrycnt=500,
            comp_yn="N",
            sdate="20230203",
            edate="20250505"
        )
    )

    asyncio.create_task(test2.req_async())

    # logger.debug(f"Response: {result}, Status: {result.header}")

    await asyncio.sleep(1)
    await test1.occurs_req_async(
        callback=lambda response, status: logger.debug(f"Success: {status}, response: {len(response.block1) if response and hasattr(response, 'block1') else None}")
    )


if __name__ == "__main__":
    asyncio.run(test_req_g3204())
