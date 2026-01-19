"""
해외선물 모의투자 마이크로 금(MGC) 테스트
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def test_micro_gold():
    from programgarden_finance import LS, CIDBT00100
    from programgarden_finance.ls.models import SetupOptions
    from datetime import datetime
    
    ls = LS.get_instance()
    ls.login(
        appkey=os.getenv("APPKEY_FUTURE_FAKE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE_FAKE"),
        paper_trading=True
    )
    
    today = datetime.now().strftime("%Y%m%d")
    
    # 마이크로 골드 (MGC) 테스트
    print("Testing Micro Gold (MGCG25)...")
    try:
        response = ls.overseas_futureoption().order().CIDBT00100(
            CIDBT00100.CIDBT00100InBlock1(
                RecCnt=1,
                OrdDt=today,
                IsuCodeVal="MGCG25",
                FutsOrdTpCode="1",
                BnsTpCode="2",
                AbrdFutsOrdPtnCode="2",
                CrcyCode="USD",
                OvrsDrvtOrdPrc=2500.00,
                CndiOrdPrc=0,
                OrdQty=1,
                PrdtCode="000000",
                DueYymm="202502",
                ExchCode="CMX",
            ),
            options=SetupOptions(on_rate_limit="wait"),
        )
        result = await response.req_async()
        print(f"Response: rsp_cd={result.rsp_cd}, rsp_msg={result.rsp_msg}")
        if result.block1:
            print(f"Order Number: {result.block1.OrdNo}")
            return result.block1.OrdNo
    except Exception as e:
        print(f"Error: {e}")
    return None


if __name__ == "__main__":
    asyncio.run(test_micro_gold())
