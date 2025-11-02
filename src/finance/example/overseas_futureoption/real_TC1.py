import asyncio
import os
from programgarden_finance import LS, TC1
from programgarden_core import pg_logger
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
        pg_logger.error("로그인 실패")
        return

    def on_message(resp: TC1.TC1RealResponse):
        print(f"Received: {resp}")

    # 로그인 시 모의투자 모드를 지정했으므로 실시간도 자동으로 모의 WebSocket을 사용합니다.
    client = ls.overseas_futureoption().real()
    await client.connect()

    tc1 = client.TC1()
    tc1.on_tc1_message(on_message)

    await asyncio.sleep(240)

if __name__ == "__main__":
    asyncio.run(run_example())
