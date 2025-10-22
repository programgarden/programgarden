import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, CIDBT00900
from programgarden_core import pg_logger, pg_log
from datetime import datetime

load_dotenv()


async def test_req_CIDBT00900():

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

    req = ls.overseas_futureoption().order().CIDBT00900(
        body=CIDBT00900.CIDBT00900InBlock1(
            OrdDt=ord_dt,
            OvrsFutsOrgOrdNo="2250",
            IsuCodeVal="ADZ25",
            FutsOrdTpCode="2",
            BnsTpCode="2",
            FutsOrdPtnCode="2",
            OvrsDrvtOrdPrc=0.64935,
            CndiOrdPrc=0,
            OrdQty=1,
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_CIDBT00900())
