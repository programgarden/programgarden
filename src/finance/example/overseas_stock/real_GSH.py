import asyncio
import os
from programgarden_finance import LS
from programgarden_core import pg_logger
from dotenv import load_dotenv

from programgarden_finance.ls.overseas_stock.real.GSH import GSHRealResponse

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

    def on_message(resp: GSHRealResponse):
        print(f"Received: {resp}")

    client = ls.overseas_stock().real()
    await client.connect()

    gsh = client.GSH()
    gsh.add_gsh_symbols(symbols=["81SOXL"])
    gsh.on_gsh_message(on_message)

    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
