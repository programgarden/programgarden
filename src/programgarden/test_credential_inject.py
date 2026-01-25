#!/usr/bin/env python3
"""Credential 주입 및 리스너 감지 테스트"""

import asyncio
from programgarden import ProgramGarden
from programgarden_core.bases import BaseExecutionListener

# 테스트 워크플로우
workflow = {
    'id': 'test-credential-workflow',
    'name': 'Test Credential Injection',
    'nodes': [
        {'id': 'start', 'type': 'StartNode'},
        {
            'id': 'broker',
            'type': 'BrokerNode',
            'provider': 'ls-sec.co.kr',
            'product': 'overseas_stock',
            'credential_id': 'broker-cred'
        }
    ],
    'edges': [
        {'from': 'start', 'to': 'broker'}
    ],
    'credentials': [
        {
            'id': 'broker-cred',
            'type': 'broker_ls',
            'name': 'Test LS',
            'data': {
                'appkey': 'test_appkey_12345',
                'appsecret': 'test_appsecret_67890',
                'paper_trading': False
            }
        }
    ]
}


class TestListener(BaseExecutionListener):
    """on_workflow_pnl_update를 구현한 테스트 리스너"""
    
    async def on_workflow_pnl_update(self, event):
        print(f'[Listener] PnL Event received: {event}')
    
    async def on_log(self, event):
        print(f'[LOG] [{event.level.upper()}] {event.node_id}: {event.message}')


async def main():
    print("=" * 60)
    print("Credential 주입 및 리스너 감지 테스트")
    print("=" * 60)
    
    pg = ProgramGarden()
    
    print("\n[1] 워크플로우 실행 (with TestListener)")
    job = await pg.run_async(workflow, listeners=[TestListener()])
    
    print(f"\n[2] Job ID: {job.job_id}")
    print(f"[3] Job Status: {job.status}")
    
    # 잠시 대기 후 종료
    await asyncio.sleep(2)
    
    print("\n[4] 테스트 완료")
    
    # Job 종료
    await job.stop()


if __name__ == "__main__":
    asyncio.run(main())
