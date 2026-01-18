"""
RealMarketDataNode 테스트 - 해외주식 실시간 시세

WebSocket GSC를 통한 실시간 체결가 수신 테스트
"""
import asyncio
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# .env 파일 경로를 프로젝트 루트로 지정
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
load_dotenv(env_path)


async def test_realmarket_stock():
    """해외주식 RealMarketDataNode 테스트"""
    from programgarden import ProgramGarden
    
    # 워크플로우 로드
    workflow_path = Path(__file__).parent / "workflows" / "realmarket-stock.json"
    with open(workflow_path, "r") as f:
        workflow = json.load(f)
    
    # Credential 주입
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    if not appkey or not appsecret:
        logger.error("APPKEY, APPSECRET 환경변수가 필요합니다.")
        return
    
    # credentials 섹션에 실제 값 주입
    for cred in workflow.get("credentials", []):
        if cred["id"] == "broker-stock":
            cred["data"]["appkey"] = appkey
            cred["data"]["appsecret"] = appsecret
    
    logger.info("=" * 60)
    logger.info("RealMarketDataNode 해외주식 테스트 시작")
    logger.info("=" * 60)
    
    # 워크플로우 실행
    pg = ProgramGarden()
    job = None
    
    try:
        # run_async는 Job을 반환하고 백그라운드에서 노드 실행
        job = await pg.run_async(workflow)
        
        # 실시간 데이터 수신 대기 (최대 15초)
        logger.info("⏳ 실시간 데이터 수신 대기 중... (최대 15초)")
        
        for i in range(15):
            await asyncio.sleep(1)
            
            # realMarket 노드의 모든 출력 확인
            realmarket_outputs = job.context.get_all_outputs("realMarket")
            prices = realmarket_outputs.get('price', {}) if realmarket_outputs else {}
            
            if prices:
                logger.info(f"  {i+1}초 후 데이터 수신 완료!")
                break
            
            logger.info(f"  {i+1}초 경과... (outputs: {list(realmarket_outputs.keys()) if realmarket_outputs else 'None'})")
        
        # 결과 확인
        logger.info("-" * 40)
        logger.info("테스트 결과:")
        
        realmarket_outputs = job.context.get_all_outputs("realMarket")
        if realmarket_outputs:
            logger.info(f"  symbols: {realmarket_outputs.get('symbols')}")
            logger.info(f"  prices: {realmarket_outputs.get('price')}")
            logger.info(f"  volumes: {realmarket_outputs.get('volume')}")
            
            prices = realmarket_outputs.get('price', {})
            if prices:
                logger.info("✅ 실시간 시세 수신 성공!")
                for symbol, price in prices.items():
                    logger.info(f"    {symbol}: ${price}")
            else:
                logger.warning("⚠️ 가격 데이터 없음 (장 시간 외일 수 있음)")
        else:
            logger.error("❌ realMarket 노드 출력 없음")
            # 모든 노드 출력 확인
            logger.info("현재 노드 출력 상태:")
            for node_id in ["start", "broker", "watchlist", "realMarket"]:
                output = job.context.get_all_outputs(node_id)
                logger.info(f"  {node_id}: {output}")
            
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Job 취소 (리소스 정리)
        if job:
            try:
                await job.cancel()
                logger.info("Job 취소 완료")
            except Exception as e:
                logger.warning(f"Job 취소 중 에러: {e}")


async def test_realmarket_futures():
    """해외선물 RealMarketDataNode 테스트 (모의투자)"""
    from programgarden import ProgramGarden
    
    # 워크플로우 로드
    workflow_path = Path(__file__).parent / "workflows" / "realmarket-futures.json"
    with open(workflow_path, "r") as f:
        workflow = json.load(f)
    
    # Credential 주입 (해외선물 모의투자용)
    appkey = os.getenv("APPKEY_FUTURE_FAKE")
    appsecret = os.getenv("APPSECRET_FUTURE_FAKE")
    
    if not appkey or not appsecret:
        logger.error("APPKEY_FUTURE_FAKE, APPSECRET_FUTURE_FAKE 환경변수가 필요합니다.")
        return
    
    # credentials 섹션에 실제 값 주입
    for cred in workflow.get("credentials", []):
        if cred["id"] == "broker-futures":
            cred["data"]["appkey"] = appkey
            cred["data"]["appsecret"] = appsecret
    
    logger.info("=" * 60)
    logger.info("RealMarketDataNode 해외선물 테스트 시작 (모의투자)")
    logger.info("=" * 60)
    
    # 워크플로우 실행
    pg = ProgramGarden()
    job = None
    
    try:
        job = await pg.run_async(workflow)
        
        # 실시간 데이터 수신 대기 (최대 15초)
        logger.info("⏳ 실시간 데이터 수신 대기 중... (최대 15초)")
        
        for i in range(15):
            await asyncio.sleep(1)
            
            # realMarket 노드의 모든 출력 확인
            realmarket_outputs = job.context.get_all_outputs("realMarket")
            prices = realmarket_outputs.get('price', {}) if realmarket_outputs else {}
            
            if prices:
                logger.info(f"  {i+1}초 후 데이터 수신 완료!")
                break
            
            logger.info(f"  {i+1}초 경과... (outputs: {list(realmarket_outputs.keys()) if realmarket_outputs else 'None'})")
        
        # 결과 확인
        logger.info("-" * 40)
        logger.info("테스트 결과:")
        
        realmarket_outputs = job.context.get_all_outputs("realMarket")
        if realmarket_outputs:
            logger.info(f"  symbols: {realmarket_outputs.get('symbols')}")
            logger.info(f"  prices: {realmarket_outputs.get('price')}")
            logger.info(f"  volumes: {realmarket_outputs.get('volume')}")
            
            prices = realmarket_outputs.get('price', {})
            if prices:
                logger.info("✅ 실시간 시세 수신 성공!")
                for symbol, price in prices.items():
                    logger.info(f"    {symbol}: {price}")
            else:
                logger.warning("⚠️ 가격 데이터 없음 (장 시간 외일 수 있음)")
        else:
            logger.error("❌ realMarket 노드 출력 없음")
            # 모든 노드 출력 확인
            logger.info("현재 노드 출력 상태:")
            for node_id in ["start", "broker", "watchlist", "realMarket"]:
                output = job.context.get_all_outputs(node_id)
                logger.info(f"  {node_id}: {output}")
            
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Job 취소 (리소스 정리)
        if job:
            try:
                await job.cancel()
                logger.info("Job 취소 완료")
            except Exception as e:
                logger.warning(f"Job 취소 중 에러: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "futures":
        asyncio.run(test_realmarket_futures())
    else:
        # 기본: 해외주식 테스트
        asyncio.run(test_realmarket_stock())
