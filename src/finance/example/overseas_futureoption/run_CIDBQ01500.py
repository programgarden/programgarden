import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, CIDBQ01500
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_CIDBQ01500():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    """
    {'CIDBQ01500InBlock1': {'RecCnt': 1, 'AcntTpCode': '1', 'QryDt': '20251101', 'BalTpCode': '2', 'FcmAcntNo': ''}}
    """
    req = ls.overseas_futureoption().accno().CIDBQ01500(
        body=CIDBQ01500.CIDBQ01500InBlock1(
            RecCnt="1",
            AcntTpCode="1",
            FcmAcntNo="",
            QryDt="20251101",
            BalTpCode="2"
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_CIDBQ01500())
