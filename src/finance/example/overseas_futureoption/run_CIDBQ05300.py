import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, CIDBQ05300
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_CIDBQ05300():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().accno().CIDBQ05300(
        body=CIDBQ05300.CIDBQ05300InBlock1(
            RecCnt=1,
            OvrsAcntTpCode="1",
            CrcyCode="ALL"
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_CIDBQ05300())
