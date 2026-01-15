#!/usr/bin/env python
"""SSE 이벤트 타이밍 테스트"""
import asyncio
import aiohttp
import time
import json
from datetime import datetime

async def test_sse_timing():
    """워크플로우 실행 시 SSE 이벤트 타이밍 측정"""
    
    workflow = {
        "id": "screener-example",
        "name": "조건으로 종목찾기 예제",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 100, "y": 200}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "position": {"x": 300, "y": 200},
             "provider": "ls-sec.co.kr", "product": "overseas_stock", 
             "credential_id": "7c5caa90-f013-44fd-855d-410437c86737"},
            {"id": "screener", "type": "ScreenerNode", "category": "market", "position": {"x": 500, "y": 200},
             "market_cap_min": 10000000000, "volume_min": 1000000, "sector": "Technology", 
             "exchange": "NASDAQ", "max_results": 20},
            {"id": "marketData", "type": "MarketDataNode", "category": "market", "position": {"x": 750, "y": 200},
             "connection": "{{ nodes.broker.connection }}", "symbols": "{{ nodes.screener.symbols }}",
             "fields": ["price", "volume"]}
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "screener"},
            {"from": "screener", "to": "marketData"}
        ],
        "credentials": [
            {"id": "7c5caa90-f013-44fd-855d-410437c86737", "type": "broker_ls", "name": "LS 해외주식",
             "data": {"appkey": "", "appsecret": "", "paper_trading": ""}}
        ]
    }
    
    base_url = "http://localhost:8766"
    start_time = time.time()
    events = []
    
    async with aiohttp.ClientSession() as session:
        # 1. SSE 연결 먼저
        print(f"[{elapsed(start_time)}] 🔌 SSE 연결 시작...")
        
        async def listen_sse():
            event_type = None
            async with session.get(f"{base_url}/events") as resp:
                print(f"[{elapsed(start_time)}] ✅ SSE 연결됨 (status: {resp.status})")
                
                buffer = ""
                async for chunk in resp.content.iter_any():
                    buffer += chunk.decode('utf-8')
                    
                    # SSE 이벤트 파싱 (이벤트는 \n\n으로 구분)
                    while '\n\n' in buffer:
                        event_text, buffer = buffer.split('\n\n', 1)
                        
                        event_type = None
                        event_data = None
                        
                        for line in event_text.split('\n'):
                            if line.startswith('event:'):
                                event_type = line[6:].strip()
                            elif line.startswith('data:'):
                                event_data = line[5:].strip()
                            elif line.startswith(':'):
                                # keepalive comment
                                continue
                        
                        if event_type and event_data:
                            try:
                                data = json.loads(event_data)
                                ts = elapsed(start_time)
                                
                                if event_type == 'node_state':
                                    node_id = data.get('node_id', 'unknown')
                                    state = data.get('state', 'unknown')
                                    events.append((ts, event_type, node_id, state))
                                    
                                    emoji = {'pending': '⏳', 'running': '🔄', 'completed': '✅', 'failed': '❌'}.get(state, '❓')
                                    print(f"[{ts}] {emoji} node_state: {node_id} → {state}")
                                    
                                elif event_type == 'job_state':
                                    status = data.get('status', 'unknown')
                                    events.append((ts, event_type, 'job', status))
                                    print(f"[{ts}] 🏁 job_state: {status}")
                                    
                                    if status in ['completed', 'failed']:
                                        return  # 종료
                                        
                            except json.JSONDecodeError as e:
                                print(f"[{elapsed(start_time)}] ⚠️ JSON 파싱 오류: {e}")
        
        # SSE 리스너 시작
        sse_task = asyncio.create_task(listen_sse())
        
        # SSE 연결 대기
        await asyncio.sleep(0.5)
        
        # 2. 워크플로우 실행
        print(f"[{elapsed(start_time)}] 🚀 워크플로우 실행 요청...")
        async with session.post(
            f"{base_url}/api/workflow/run-inline",
            json=workflow,
            headers={"Content-Type": "application/json"}
        ) as resp:
            result = await resp.json()
            print(f"[{elapsed(start_time)}] 📋 응답: {result}")
        
        # SSE 이벤트 대기 (최대 60초)
        try:
            await asyncio.wait_for(sse_task, timeout=60.0)
        except asyncio.TimeoutError:
            print(f"[{elapsed(start_time)}] ⏰ 타임아웃")
            sse_task.cancel()
    
    # 결과 분석
    print("\n" + "="*60)
    print("📊 이벤트 타이밍 분석")
    print("="*60)
    
    node_times = {}
    for ts, event_type, node_id, state in events:
        if event_type == 'node_state':
            if node_id not in node_times:
                node_times[node_id] = {}
            node_times[node_id][state] = ts
    
    for node_id in ['start', 'broker', 'screener', 'marketData']:
        times = node_times.get(node_id, {})
        pending = times.get('pending', '-')
        running = times.get('running', '-')
        completed = times.get('completed', '-')
        print(f"  {node_id:15} | pending: {pending:8} | running: {running:8} | completed: {completed:8}")

def elapsed(start):
    return f"{time.time() - start:.3f}s"

if __name__ == "__main__":
    asyncio.run(test_sse_timing())
