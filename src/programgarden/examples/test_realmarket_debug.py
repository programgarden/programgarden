"""
RealMarketDataNode 디버그 테스트
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("realmarket_debug")

from programgarden.executor import WorkflowExecutor


async def test_stock_workflow():
    """10번 해외주식 워크플로우 테스트"""
    
    workflow_path = Path(__file__).parent / "workflows" / "10.realmarket-stock.json"
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)
    
    # credentials 주입
    for cred in workflow.get('credentials', []):
        if cred['id'] == 'broker-stock':
            cred['data']['appkey'] = os.getenv("APPKEY")
            cred['data']['appsecret'] = os.getenv("APPSECRET")
    
    logger.info("="*60)
    logger.info("테스트: 10번 해외주식 실시간 시세 (GSC)")
    logger.info("="*60)
    
    try:
        executor = WorkflowExecutor()
        
        logger.info("워크플로우 실행 시작...")
        job = await executor.execute(workflow)
        
        context = job.context
        
        logger.info("⏳ 20초 동안 실시간 데이터 수신 대기...")
        await asyncio.sleep(20)
        
        broker_outputs = context.get_all_outputs("broker")
        watchlist_outputs = context.get_all_outputs("watchlist")
        realmarket_outputs = context.get_all_outputs("realMarket")
        
        logger.info(f"\n📊 broker 출력: connected={broker_outputs.get('connected')}, product={broker_outputs.get('connection', {}).get('product')}")
        logger.info(f"📊 watchlist 출력: {len(watchlist_outputs.get('symbols', []))} 종목")
        logger.info(f"📊 realMarket 가격: {realmarket_outputs.get('price', {})}")
        logger.info(f"📊 Job 상태: {job.status}")
        
        logger.info("✅ 해외주식 테스트 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_futures_workflow():
    """9번 해외선물 워크플로우 테스트"""
    
    workflow_path = Path(__file__).parent / "workflows" / "9.realmarket-futures.json"
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)
    
    # credentials 주입
    for cred in workflow.get('credentials', []):
        if cred['id'] == 'broker-futures':
            cred['data']['appkey'] = os.getenv("APPKEY_FUTURE_FAKE")
            cred['data']['appsecret'] = os.getenv("APPSECRET_FUTURE_FAKE")
    
    logger.info("="*60)
    logger.info("테스트: 9번 해외선물 실시간 시세 (OVC, 모의투자)")
    logger.info("="*60)
    
    try:
        executor = WorkflowExecutor()
        
        logger.info("워크플로우 실행 시작...")
        job = await executor.execute(workflow)
        
        context = job.context
        
        logger.info("⏳ 20초 동안 실시간 데이터 수신 대기...")
        await asyncio.sleep(20)
        
        broker_outputs = context.get_all_outputs("broker")
        watchlist_outputs = context.get_all_outputs("watchlist")
        realmarket_outputs = context.get_all_outputs("realMarket")
        
        logger.info(f"\n📊 broker 출력: connected={broker_outputs.get('connected')}, product={broker_outputs.get('connection', {}).get('product')}")
        logger.info(f"📊 watchlist 출력: {len(watchlist_outputs.get('symbols', []))} 종목")
        logger.info(f"📊 realMarket 가격: {realmarket_outputs.get('price', {})}")
        logger.info(f"📊 Job 상태: {job.status}")
        
        logger.info("✅ 해외선물 테스트 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    await test_stock_workflow()
    
    logger.info("\n⏳ 3초 후 해외선물 테스트...")
    await asyncio.sleep(3)
    
    await test_futures_workflow()
    
    logger.info("\n✅ 모든 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
