import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, COSAQ01400
from programgarden_core import pg_logger, pg_log
import asyncio

load_dotenv()


async def test_req_cosoq01400():
    pg_log(logging.DEBUG)

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    csoaq01400 = ls.overseas_stock().accno().cosaq01400(
        COSAQ01400.COSAQ01400InBlock1(
            RecCnt=1,
            QryTpCode="1",
            CntryCode="001",
            SrtDt="20250401",
            EndDt="20250426",
            BnsTpCode="0",
            RsvOrdCndiCode="00",
            RsvOrdStatCode="1"
        ),
    )

    await csoaq01400.retry_req_async(
        callback=lambda x, status: pg_logger.debug(f"Response: {x}, Status: {status}"),
    )


if __name__ == "__main__":
    asyncio.run(test_req_cosoq01400())
