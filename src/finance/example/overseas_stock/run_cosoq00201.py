import logging
from dotenv import load_dotenv
import os
import asyncio
from programgarden_finance import LS, COSOQ00201
from programgarden_core import pg_logger, pg_log

from programgarden_finance.ls.models import SetupOptions

load_dotenv()


async def test_req_cosaq00201():

    pg_log(logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    cosoq00201 = ls.overseas_stock().계좌().cosoq00201(
        COSOQ00201.COSOQ00201InBlock1(
            RecCnt=1,
            BaseDt="20231020",
            CrcyCode="ALL",
            AstkBalTpCode="00"
        ),
        options=SetupOptions(
            on_rate_limit="wait"
        )
    )

    await cosoq00201.req_async()


if __name__ == "__main__":
    asyncio.run(test_req_cosaq00201())
