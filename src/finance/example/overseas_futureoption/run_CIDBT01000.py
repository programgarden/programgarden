import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, CIDBT01000
from programgarden_core import pg_logger, pg_log
from datetime import datetime

load_dotenv()


async def test_req_CIDBT01000():

    pg_log(logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE"),
        paper_trading=True,
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    ord_dt = datetime.now().strftime("%Y%m%d")

    req = ls.overseas_futureoption().order().CIDBT01000(
        body=CIDBT01000.CIDBT01000InBlock1(
            OrdDt=ord_dt,
            OvrsFutsOrgOrdNo="2278",
            IsuCodeVal="ADZ25",
            FutsOrdTpCode="3",
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_CIDBT01000())
