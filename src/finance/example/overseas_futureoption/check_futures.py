"""해외선물 종목 명세 조회"""
import asyncio
import os
from dotenv import load_dotenv
from programgarden_finance import LS, o3121

load_dotenv()

async def check():
    ls = LS.get_instance()
    ls.login(
        appkey=os.getenv('APPKEY_FUTURE'),
        appsecretkey=os.getenv('APPSECRET_FUTURE'),
    )
    
    # F: 선물
    req = ls.overseas_futureoption().market().해외선물옵션_마스터조회(
        body=o3121.O3121InBlock(
            MktGb="F",
            BscGdsCd=""
        )
    )
    result = await req.req_async()
    
    print("=" * 60)
    print(f"응답: {result.rsp_cd} - {result.rsp_msg}")
    print("=" * 60)
    
    if result.block:
        count = 0
        for item in result.block:
            symbol = getattr(item, 'Symbol', '')
            name = getattr(item, 'SymbolNm', '')
            bsc = getattr(item, 'BscGdsCd', '')
            tick = getattr(item, 'UntPrc', 0)
            tick_val = getattr(item, 'MnChgAmt', 0)
            margin = getattr(item, 'OpngMgn', 0)
            if symbol:  # Symbol이 있는 것만
                print(f"  {symbol}: {name} (기초: {bsc})")
                count += 1
                if count > 30:
                    print("  ... (생략)")
                    break
        
        print(f"\n총 {len(result.block)}개 종목")

asyncio.run(check())
