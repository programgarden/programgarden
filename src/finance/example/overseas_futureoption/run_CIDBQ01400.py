import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, CIDBQ01400
from programgarden_core import pg_logger, pg_log

load_dotenv()


async def test_req_CIDBQ01400():

    pg_log(logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().accno().CIDBQ01400(
        body=CIDBQ01400.CIDBQ01400InBlock1(
            RecCnt=1,
            QryTpCode="1",
            IsuCodeVal="ADM23",
            BnsTpCode="2",
            OvrsDrvtOrdPrc=1.0,
            AbrdFutsOrdPtnCode="1"
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_CIDBQ01400())
