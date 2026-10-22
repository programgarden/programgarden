import asyncio
import os
from programgarden_finance import LS, OVC
import logging
logger = logging.getLogger(__name__)
from dotenv import load_dotenv

load_dotenv()


async def run_example():

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE"),
        paper_trading=True,
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    def on_message(resp: OVC.OVCRealResponse):
        print(f"Received: {resp}")

    client = ls.overseas_futureoption().real()
    await client.connect()

    ovc = client.OVC()
    ovc.add_ovc_symbols(symbols=["ESZ25   "])
    ovc.on_ovc_message(on_message)

    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_example())
