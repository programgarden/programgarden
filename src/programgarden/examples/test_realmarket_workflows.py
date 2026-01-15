"""
RealMarketDataNode 워크플로우 테스트 (9번, 10번)
- 9번: 해외선물 모의투자 (OVC WebSocket)
- 10번: 해외주식 실계좌 (GSC WebSocket)
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("realmarket_test")

from programgarden.executor import WorkflowExecutor
from programgarden.context import ExecutionContext


async def test_workflow(workflow_path: str, credentials: dict, duration: int = 10):
    """워크플로우 테스트 실행"""
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)
    
    # credentials 주입
    for cred in workflow.get('credentials', []):
        if cred['id'] in credentials:
            cred['data'].update(credentials[cred['id']])
    
    logger.info(f"\n{'='*60}")
    logger.info(f"테스트: {workflow.get('name', workflow_path)}")
    logger.info(f"설명: {workflow.get('description', '')}")
    logger.info(f"{'='*60}")
    
    try:
        executor = WorkflowExecutor()
        
        # ExecutionContext 생성
        job_id = str(uuid.uuid4())
        workflow_id = workflow.get('id', 'test-workflow')
        context = ExecutionContext(
            job_id=job_id,
            workflow_id=workflow_id,
            workflow_credentials=workflow.get('credentials', []),
        )
        
        # 워크플로우 실행
        logger.info("워크플로우 실행 시작...")
        result = await executor.execute(workflow, context)
        
        logger.info(f"\n📊 실행 결과:")
        for node_id, output in result.items():
            if isinstance(output, dict) and 'price' in output:
                logger.info(f"  - {node_id}: 가격 데이터 {output.get('price', {})}")
            else:
                logger.info(f"  - {node_id}: {output}")
        
        # 실시간 노드는 stay_connected=True면 계속 연결 유지됨
        if duration > 0:
            logger.info(f"\n⏳ {duration}초 대기 (실시간 데이터 확인)...")
            await asyncio.sleep(duration)
        
        logger.info("✅ 워크플로우 완료!")
        return result
        
    except Exception as e:
        logger.error(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    workflows_dir = Path(__file__).parent / "workflows"
    
    # 10번: 해외주식 실계좌 테스트
    logger.info("\n" + "="*70)
    logger.info("📈 10번 워크플로우: 해외주식 실시간 시세 (GSC)")
    logger.info("="*70)
    
    stock_credentials = {
        "broker-stock": {
            "appkey": os.getenv("APPKEY"),
            "appsecret": os.getenv("APPSECRET"),
            "paper_trading": False
        }
    }
    
    await test_workflow(
        str(workflows_dir / "10.realmarket-stock.json"),
        stock_credentials,
        duration=10
    )
    
    # 잠시 대기 후 다음 테스트
    logger.info("\n⏳ 3초 후 해외선물 테스트 시작...")
    await asyncio.sleep(3)
    
    # 9번: 해외선물 모의투자 테스트
    logger.info("\n" + "="*70)
    logger.info("📊 9번 워크플로우: 해외선물 실시간 시세 (OVC, 모의투자)")
    logger.info("="*70)
    
    futures_credentials = {
        "broker-futures": {
            "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
            "appsecret": os.getenv("APPSECRET_FUTURE_FAKE"),
            "paper_trading": True
        }
    }
    
    await test_workflow(
        str(workflows_dir / "9.realmarket-futures.json"),
        futures_credentials,
        duration=10
    )
    
    logger.info("\n✅ 모든 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
