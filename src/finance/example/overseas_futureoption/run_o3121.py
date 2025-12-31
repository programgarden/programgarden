import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, o3121
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_o3121():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().market().해외선물옵션_마스터조회(
        body=o3121.O3121InBlock(
            MktGb="O",
            BscGdsCd=""
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_o3121())
