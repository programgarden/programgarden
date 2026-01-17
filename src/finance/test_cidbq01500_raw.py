"""
CIDBQ01500 (해외선물 잔고조회) 직접 테스트
raw 응답을 확인하여 문제 파악
"""

import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from programgarden_finance import LS

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
load_dotenv()


async def test_cidbq01500():
    """CIDBQ01500 직접 호출 테스트"""
    
    ls = LS.get_instance()
    
    login_result = ls.login(
        appkey=os.getenv('APPKEY_FUTURE_FAKE'),
        appsecretkey=os.getenv('APPSECRET_FUTURE_FAKE')
    )
    
    if not login_result:
        logger.error('❌ 로그인 실패')
        return
    
    logger.info('✅ 로그인 성공 (모의투자)')
    
    # CIDBQ01500 직접 호출
    from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01500.blocks import CIDBQ01500InBlock1
    
    futures = ls.overseas_futureoption()
    accno = futures.accno()
    
    query_date = datetime.now().strftime("%Y%m%d")
    logger.info(f"📅 조회일자: {query_date}")
    
    tr = accno.CIDBQ01500(
        body=CIDBQ01500InBlock1(
            RecCnt=1,
            AcntTpCode="1",  # 위탁
            QryDt=query_date,
            BalTpCode="1",   # 합산
            FcmAcntNo=""
        )
    )
    
    resp = await tr.req_async()
    
    print('\n' + '=' * 70)
    print('📊 CIDBQ01500 응답 분석')
    print('=' * 70)
    print(f'rsp_cd: {resp.rsp_cd}')
    print(f'rsp_msg: {getattr(resp, "rsp_msg", "")}')
    print(f'error_msg: {getattr(resp, "error_msg", None)}')
    
    # block1 확인
    if hasattr(resp, 'block1') and resp.block1:
        print(f'\nblock1: {resp.block1}')
    else:
        print('\nblock1: 없음')
    
    # block2 확인 (포지션 데이터)
    if hasattr(resp, 'block2') and resp.block2:
        print(f'\nblock2: {len(resp.block2)}개')
        for i, item in enumerate(resp.block2):
            print(f'\n  [{i}] 포지션:')
            print(f'      종목코드: {getattr(item, "IsuCodeVal", "")}')
            print(f'      종목명: {getattr(item, "IsuNm", "")}')
            print(f'      잔고수량: {getattr(item, "BalQty", 0)}')
            print(f'      매매구분: {getattr(item, "BnsTpCode", "")} (2=매수, 1=매도)')
            print(f'      매입가: {getattr(item, "PchsPrc", 0)}')
            print(f'      현재가: {getattr(item, "OvrsDrvtNowPrc", 0)}')
            print(f'      평가손익: {getattr(item, "AbrdFutsEvalPnlAmt", 0)}')
            print(f'      마진콜율: {getattr(item, "MgnclRat", "N/A")}')  # 이게 NaN이면 문제
    else:
        print('\nblock2: 없음 (포지션 데이터 없음)')
    
    print('\n' + '=' * 70)
    print('raw 응답 전체:')
    print('=' * 70)
    print(resp)


if __name__ == '__main__':
    asyncio.run(test_cidbq01500())
