import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, CIDBQ01800
from programgarden_core import pg_logger, pg_log

load_dotenv()


async def test_req_CIDBQ01800():

    pg_log(logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().accno().CIDBQ01800(
        body=CIDBQ01800.CIDBQ01800InBlock1(
            RecCnt=1,
            IsuCodeVal="ADM23",
            OrdDt="20230609",
            ThdayTpCode="",
            OrdStatCode="0",
            BnsTpCode="0",
            QryTpCode="2",
            OrdPtnCode="00",
            OvrsDrvtFnoTpCode="A"
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_CIDBQ01800())
