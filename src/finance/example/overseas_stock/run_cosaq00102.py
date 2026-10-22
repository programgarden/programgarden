import logging
from dotenv import load_dotenv
import os
import asyncio
from programgarden_finance import LS, COSAQ00102
import logging
logger = logging.getLogger(__name__)

from programgarden_finance.ls.models import SetupOptions

load_dotenv()


async def test_req_cosaq00102():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    cosaq00102 = ls.overseas_stock().계좌().cosaq00102(
        COSAQ00102.COSAQ00102InBlock1(
            RecCnt=1,
            QryTpCode="1",
            BkseqTpCode="1",
            OrdMktCode="81",
            BnsTpCode="0",
            IsuNo="",
            SrtOrdNo=999999999,
            OrdDt="20260122",
            ExecYn="1",
            CrcyCode="000",
            ThdayBnsAppYn="0",
            LoanBalHldYn="0"
        ),
        options=SetupOptions(
            on_rate_limit="wait"
        )
    )

    data = await cosaq00102.req_async()
    print(data)


if __name__ == "__main__":
    asyncio.run(test_req_cosaq00102())
