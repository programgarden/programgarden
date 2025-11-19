import logging
from dotenv import load_dotenv
import os
import asyncio
from programgarden_finance import LS, COSAT00311
from programgarden_core import pg_logger, pg_log

from programgarden_finance.ls.models import SetupOptions

load_dotenv()


async def test_req_cosat00311():

    pg_log(logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    cosat00311 = ls.overseas_stock().주문().cosat00311(
        COSAT00311.COSAT00311InBlock1(
            RecCnt=1,
            OrdPtnCode="07",
            OrgOrdNo=231,
            OrdMktCode="82",
            IsuNo="ESPR",
            OrdQty=1,
            OvrsOrdPrc=2.62,
            OrdprcPtnCode="00",
        ),
        options=SetupOptions(
            on_rate_limit="wait"
        )
    )

    await cosat00311.req_async()


if __name__ == "__main__":
    asyncio.run(test_req_cosat00311())
