import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3116
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_o3116():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().해외선물_시간대별Tick체결조회(
        body=o3116.O3116InBlock(
            gubun="0",
            shcode="CUSU25",
            readcnt=100,
            cts_seq=12426
        )
    )
    await req.occurs_req_async(
        callback=lambda response, status: logger.debug(f"Retrying request: {response.block1[0].ovstime if response is not None else 'None'}, status: {status}"),
    )

if __name__ == "__main__":
    asyncio.run(test_req_o3116())
