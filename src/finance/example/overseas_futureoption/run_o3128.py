import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3128
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_o3128():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().해외선물옵션_차트일주월조회(
        o3128.O3128InBlock(
            mktgb="F",
            shcode="ADM23",
            gubun="1",
            qrycnt=20,
            sdate="20230525",
            edate="20230609",
            cts_date=""
        ),
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_o3128())
