import asyncio
import os
from programgarden_finance import LS, TC3
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

    def on_message(resp: TC3.TC3RealResponse):
        # 해외선물 체결(CH01). LS 모의(2026-10-15) 관측: ccls_no 는 0 채운 10자리, ccls_tm 은
        # HHMMSSmmm, fcm_fee 는 체결 뒤 남은 포지션 수량, 청산이면 clr_q·clr_pl_amt 가 채워진다.
        # 프레임의 user/userid 에는 LS 로그인 ID 가 들어 있으니 로그로 남기지 마세요.
        body = resp.body
        if body is not None:
            print(f"체결 주문번호 {body.ordr_no} · {body.is_cd} · {body.ccls_q}계약 @ {body.ccls_prc}")

    # 로그인 시 모의투자 모드를 지정했으므로 실시간도 자동으로 모의 WebSocket을 사용합니다.
    client = ls.overseas_futureoption().real()
    await client.connect()

    tc3 = client.TC3()
    tc3.on_tc3_message(on_message)

    await asyncio.sleep(240)

if __name__ == "__main__":
    asyncio.run(run_example())
