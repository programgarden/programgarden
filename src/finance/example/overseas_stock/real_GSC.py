import asyncio
import os
from programgarden_finance import LS
from programgarden_core import pg_logger
from dotenv import load_dotenv

from programgarden_finance.ls.overseas_stock.real.GSC.blocks import GSCRealResponse

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

    def on_message(resp: GSCRealResponse):
        print(f"Received: {resp}")

    client = ls.overseas_stock().real()
    await client.connect()

    gsc = client.GSC()
    gsc.add_gsc_symbols(symbols=["81SOXL"])
    gsc.on_gsc_message(on_message)

    gsc = client.AS0()
    gsc.on_as0_message(on_message)


if __name__ == "__main__":
    asyncio.run(run_example())
