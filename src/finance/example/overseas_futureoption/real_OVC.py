import asyncio
import os
from programgarden_finance import LS, OVC
from programgarden_core import pg_logger
from dotenv import load_dotenv

load_dotenv()


async def run_example():

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    def on_message(resp: OVC.OVCRealResponse):
        print(f"Received: {resp}")

    client = ls.overseas_futureoption().real()
    await client.connect()

    ovc = client.OVC()
    ovc.add_ovc_symbols(symbols=["ESU25   "])
    ovc.on_ovc_message(on_message)

    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_example())
