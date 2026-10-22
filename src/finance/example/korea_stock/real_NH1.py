"""NXT 호가잔량(NH1) 실시간 예제

NXT(넥스트거래소) 종목의 실시간 10단계 호가잔량 데이터를 수신합니다.
tr_key는 10자리로 패딩됩니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.NH1.blocks import NH1RealResponse

logger = logging.getLogger(__name__)
load_dotenv()


async def run_example():
    ls = LS.get_instance()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )
    if login_result is False:
        logger.error("로그인 실패")
        return

    def on_message(resp: NH1RealResponse):
        if resp.body:
            b = resp.body
            print(f"[NH1 NXT호가] {b.shcode} | 시간:{b.hotime} "
                  f"매도1:{b.offerho1}({b.offerrem1}) 매수1:{b.bidho1}({b.bidrem1}) "
                  f"총매도잔량:{b.totofferrem} 총매수잔량:{b.totbidrem}")
        else:
            print(f"[NH1] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")

    client = ls.korea_stock().real()
    await client.connect()

    nh1 = client.NH1()
    nh1.add_nh1_symbols(symbols=["005930"])
    nh1.on_nh1_message(on_message)

    print("NH1 NXT 호가잔량 실시간 수신 대기 중... (Ctrl+C로 종료)")
    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
