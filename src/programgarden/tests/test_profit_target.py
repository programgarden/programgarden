"""
ProfitTarget 플러그인 테스트

positions 기반 플러그인 테스트
"""

import asyncio
import json
import os
from pathlib import Path


def load_env():
    """상위 .env 파일 로드"""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    print(f"🔍 Looking for .env at: {env_path}")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
        print(f"✅ Loaded .env")
    else:
        print(f"⚠️ .env not found")


async def test_profit_target():
    """ProfitTarget 워크플로우 테스트"""
    from programgarden import WorkflowExecutor
    
    # 워크플로우 로드
    workflow_path = Path(__file__).parent / "workflows/condition/05-profittarget-stock.json"
    with open(workflow_path) as f:
        workflow = json.load(f)
    
    # credential 주입
    workflow['credentials'][0]['data']['appkey'] = os.getenv('APPKEY', '')
    workflow['credentials'][0]['data']['appsecret'] = os.getenv('APPSECRET', '')
    
    print("\n" + "="*60)
    print("🧪 TEST: ProfitTarget 플러그인 (positions 기반)")
    print("="*60)
    
    executor = WorkflowExecutor()
    job = await executor.execute(workflow)
    
    # 완료 대기
    print("\n⏳ 데이터 수신 대기 중...")
    await asyncio.sleep(8)
    await job.stop()
    
    # 결과 확인
    print("\n=== RealAccountNode 출력 ===")
    account_result = job.context.get_all_outputs('realAccount')
    print(json.dumps(account_result, indent=2, ensure_ascii=False, default=str))
    
    print("\n=== ConditionNode (ProfitTarget) 출력 ===")
    profit_result = job.context.get_all_outputs('profitCondition')
    print(json.dumps(profit_result, indent=2, ensure_ascii=False, default=str))
    
    print("\n=== DisplayNode 출력 ===")
    display_result = job.context.get_all_outputs('display')
    print(json.dumps(display_result, indent=2, ensure_ascii=False, default=str))


async def test_stop_loss():
    """StopLoss 워크플로우 테스트"""
    from programgarden import WorkflowExecutor
    
    # 워크플로우 로드
    workflow_path = Path(__file__).parent / "workflows/condition/06-stoploss-stock.json"
    with open(workflow_path) as f:
        workflow = json.load(f)
    
    # credential 주입
    workflow['credentials'][0]['data']['appkey'] = os.getenv('APPKEY', '')
    workflow['credentials'][0]['data']['appsecret'] = os.getenv('APPSECRET', '')
    
    print("\n" + "="*60)
    print("🧪 TEST: StopLoss 플러그인 (positions 기반)")
    print("="*60)
    
    executor = WorkflowExecutor()
    job = await executor.execute(workflow)
    
    # 완료 대기
    print("\n⏳ 데이터 수신 대기 중...")
    await asyncio.sleep(8)
    await job.stop()
    
    # 결과 확인
    print("\n=== RealAccountNode 출력 ===")
    account_result = job.context.get_all_outputs('realAccount')
    print(json.dumps(account_result, indent=2, ensure_ascii=False, default=str))
    
    print("\n=== ConditionNode (StopLoss) 출력 ===")
    stoploss_result = job.context.get_all_outputs('stoplossCondition')
    print(json.dumps(stoploss_result, indent=2, ensure_ascii=False, default=str))
    
    print("\n=== DisplayNode 출력 ===")
    display_result = job.context.get_all_outputs('display')
    print(json.dumps(display_result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    load_env()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stoploss":
        asyncio.run(test_stop_loss())
    else:
        asyncio.run(test_profit_target())
