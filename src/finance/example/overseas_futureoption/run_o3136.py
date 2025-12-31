import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3136
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_o3136():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        logger.error("로그인 실패")
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
        callback=lambda response, status: logger.debug(f"Retrying request: {response.block1 if response is not None else 'None'}, status: {status}"),
    )

if __name__ == "__main__":
    asyncio.run(test_req_o3136())
