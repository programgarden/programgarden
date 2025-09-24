import asyncio
import os
from programgarden_finance import LS, AS1
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

    def on_message(resp: AS1.AS1RealResponse):
        print(f"Received: {resp}")

    client = ls.overseas_stock().real()
    await client.connect()

    as1 = client.AS1()
    as1.on_as1_message(on_message)

    await asyncio.sleep(50)

if __name__ == "__main__":
    asyncio.run(run_example())
