import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3107
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_o3107():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().해외선물_관심종목조회(
        body=o3107.O3107InBlock(
            symbol="CUSU25"
        )
    )
    print(req.req())

if __name__ == "__main__":
    asyncio.run(test_req_o3107())
