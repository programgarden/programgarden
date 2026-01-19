"""해외선물 마스터에서 HMHF26 정보 확인"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def check_futures_master():
    from programgarden_finance import LS, o3101
    
    appkey = os.getenv('APPKEY_FUTURE_FAKE')
    appsecret = os.getenv('APPSECRET_FUTURE_FAKE')
    
    ls = LS.get_instance()
    ls.login(appkey=appkey, appsecretkey=appsecret, paper_trading=True)
    
    # 해외선물 마스터 조회
    result = ls.overseas_futureoption().market().해외선물마스터조회(
        body=o3101.O3101InBlock(gubun="1")
    )
    response = await result.req_async()
    
    print('🔍 HMHF26 종목 정보:')
    if response and hasattr(response, 'block1') and response.block1:
        for item in response.block1:
            if hasattr(item, 'Symbol') and 'HMH' in str(item.Symbol):
                print(f'  Symbol: {item.Symbol}')
                print(f'  SymbolNm: {item.SymbolNm if hasattr(item, "SymbolNm") else "N/A"}')
                print(f'  Globex: {item.Globex if hasattr(item, "Globex") else "N/A"}')
                print(f'  ExchCode: {item.ExchCode if hasattr(item, "ExchCode") else "N/A"}')
                print(f'  ExchCd: {item.ExchCd if hasattr(item, "ExchCd") else "N/A"}')
                print(f'  LstngYm: {item.LstngYm if hasattr(item, "LstngYm") else "N/A"}')
                print(f'  ---')

if __name__ == "__main__":
    asyncio.run(check_futures_master())
