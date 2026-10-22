import logging
import os
from dotenv import load_dotenv
import asyncio
from programgarden_finance import LS, CIDBQ03000
import logging
logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_CIDBQ03000(trading_date: str = ""):
    """Read the current balance or an explicit YYYYMMDD trading date.

    Date queries use the owner's documented TrdDt field. Consumers must verify
    that both the input echo and each balance row contain the requested date;
    a blank date does not establish the broker's business-day boundary.
    """

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE"),
        paper_trading=True
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    req = ls.overseas_futureoption().accno().CIDBQ03000(
        body=CIDBQ03000.CIDBQ03000InBlock1(
            RecCnt=1,
            AcntTpCode="1",
            TrdDt=trading_date
        )
    )
    print(await req.req_async())

if __name__ == "__main__":
    asyncio.run(test_req_CIDBQ03000())
