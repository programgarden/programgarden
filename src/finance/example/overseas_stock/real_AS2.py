import asyncio
import os
from programgarden_finance import LS, AS2
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

    def on_message(resp: AS2.AS2RealResponse):
        print(f"Received: {resp}")

    client = ls.overseas_stock().real()
    await client.connect()

    as2 = client.AS2()
    as2.on_message_listener(on_message)

    await as2.add_register()
    await asyncio.sleep(120)


if __name__ == "__main__":
    asyncio.run(run_example())
