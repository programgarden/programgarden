import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3123
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_o3123():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().해외선물옵션_차트분봉조회(
        body=o3123.O3123InBlock(
            mktgb="F",
            shcode="ADZ25",
            ncnt=1,
            readcnt=20,
            cts_date="",
            cts_time=""
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_o3123())
