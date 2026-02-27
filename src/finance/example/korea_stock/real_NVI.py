"""NXT VI발동해제(NVI) 실시간 예제

NXT(넥스트거래소) VI(변동성완화장치) 발동/해제 이벤트를 실시간으로 수신합니다.
NVI는 종목코드 없이 '*'로 전체 종목을 구독합니다.
tr_key는 10자리로 패딩됩니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.NVI.blocks import NVIRealResponse

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

    def on_message(resp: NVIRealResponse):
        if resp.body:
            b = resp.body
            vi_type = {"1": "정적VI발동", "2": "동적VI발동", "3": "정적VI해제", "4": "동적VI해제"}.get(b.vi_gubun, b.vi_gubun)
            print(f"[NVI NXT_VI] {b.shcode}({b.ref_shcode}) | {vi_type} "
                  f"정적기준가:{b.svi_recprice} 동적기준가:{b.dvi_recprice} "
                  f"VI발동가:{b.vi_trgprice} 시간:{b.time}")
        else:
            print(f"[NVI] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")

    client = ls.korea_stock().real()
    await client.connect()

    nvi = client.NVI()
    nvi.add_nvi_symbols(symbols=["*"])
    nvi.on_nvi_message(on_message)

    print("NVI NXT VI발동해제 실시간 수신 대기 중... (Ctrl+C로 종료)")
    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
