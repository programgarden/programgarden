"""해외선물 종목 마스터 조회"""
import asyncio
import os
from dotenv import load_dotenv
from programgarden_finance import LS, o3101

load_dotenv()

async def check():
    ls = LS.get_instance()
    ls.login(
        appkey=os.getenv('APPKEY_FUTURE'),
        appsecretkey=os.getenv('APPSECRET_FUTURE'),
    )
    
    req = ls.overseas_futureoption().market().o3101(
        body=o3101.O3101InBlock(gubun='1')
    )
    result = await req.req_async()
    
    print("=" * 60)
    print("주요 선물 종목 목록")
    print("=" * 60)
    
    if result.block:
        # NQ, ES, MNQ, MES, CL, GC 관련 종목만 출력
        for item in result.block:
            symbol = getattr(item, 'Symbol', '')
            keywords = ['NQ', 'ES', 'MNQ', 'MES', 'CLF', 'CLG', 'CLH', 'GCF', 'GCG', 'GCH']
            if any(symbol.startswith(x) for x in keywords):
                name = getattr(item, 'SymbolNm', '')
                close = getattr(item, 'Close', '')
                print(f"  {symbol}: {name} - 현재가: {close}")

asyncio.run(check())
