#!/usr/bin/env python3
"""JSON 워크플로우 테스트 - values 출력 확인"""

import asyncio
import json
import os
import sys
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# .env 로드 (programgarden 폴더 기준)
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value
    logger.info(f"Loaded .env from {env_path}")

# 암호화 유틸리티
workflow_editor_path = Path(__file__).parent.parent / "examples" / "workflow_editor"
sys.path.insert(0, str(workflow_editor_path))
from encryption import decrypt_data

# 경로 설정
WORKFLOW_PATH = Path(__file__).parent / "workflows" / "condition" / "01-condition-rsi-historical-stock.json"

def load_credentials():
    """credentials.json 로드 및 복호화"""
    cred_path = workflow_editor_path / "credentials.json"
    
    with open(cred_path) as f:
        data = json.load(f)
    
    credentials = {}
    for cred in data.get("credentials", []):
        cred_id = cred["credential_id"]
        encrypted_data = cred.get("data", "{}")
        decrypted = decrypt_data(encrypted_data)
        credentials[cred_id] = {
            "type": cred["credential_type"],
            "name": cred["name"],
            **decrypted
        }
        logger.info(f"Loaded credential: {cred['name']} (id: {cred_id})")
    
    return credentials

async def main():
    # 워크플로우 JSON 로드
    with open(WORKFLOW_PATH, 'r') as f:
        workflow = json.load(f)
    
    logger.info(f"워크플로우 로드: {workflow['name']}")
    
    # credentials 로드
    creds = load_credentials()
    
    # credentials 섹션에 실제 값 주입
    for cred in workflow.get("credentials", []):
        cred_id = cred["credential_id"]
        if cred_id in creds:
            cred["data"]["appkey"] = creds[cred_id].get("appkey", "")
            cred["data"]["appsecret"] = creds[cred_id].get("appsecret", "")
            cred["data"]["paper_trading"] = creds[cred_id].get("paper_trading", False)
    
    # ProgramGarden 실행 (community 플러그인 로드)
    from programgarden import WorkflowExecutor
    import programgarden_community  # 플러그인 자동 등록
    
    executor = WorkflowExecutor()
    job = await executor.execute(workflow)
    
    # 완료 대기
    await asyncio.sleep(5)
    await job.stop()
    
    # 결과 출력
    logger.info("=" * 50)
    logger.info("워크플로우 실행 완료")
    logger.info("=" * 50)
    
    # context에서 노드 출력 확인
    for node_id in ["historicaldata_1", "rsiCondition"]:
        node_output = job.context.get_all_outputs(node_id)
        logger.info(f"\n[Node: {node_id}]")
        
        if isinstance(node_output, dict):
            for key, value in node_output.items():
                if key == "values":
                    logger.info(f"  {key}:")
                    if isinstance(value, list):
                        for item in value:
                            symbol = item.get("symbol", "unknown")
                            ts = item.get("time_series", [])
                            if isinstance(ts, list):
                                logger.info(f"    {symbol}: {len(ts)} entries")
                                if ts:
                                    logger.info(f"      첫 번째: {ts[0]}")
                                    logger.info(f"      마지막: {ts[-1]}")
                            else:
                                logger.info(f"    {symbol}: {ts}")
                    else:
                        logger.info(f"    {value}")
                elif key == "symbol_results":
                    logger.info(f"  {key}: {value}")
                elif key == "passed_symbols":
                    logger.info(f"  {key}: {value}")
                elif key == "ohlcv_data":
                    logger.info(f"  {key}:")
                    # values 형식: [{symbol, exchange, time_series}, ...]
                    if isinstance(value, list):
                        for item in value:
                            symbol = item.get("symbol", "unknown")
                            ts = item.get("time_series", [])
                            if isinstance(ts, list):
                                logger.info(f"    {symbol}: {len(ts)} bars")
                            else:
                                logger.info(f"    {symbol}: {type(ts)}")
                    elif isinstance(value, dict):
                        for symbol, data in value.items():
                            if isinstance(data, list):
                                logger.info(f"    {symbol}: {len(data)} bars")
                            else:
                                logger.info(f"    {symbol}: {type(data)}")
                else:
                    # 길이가 긴 데이터는 요약
                    if isinstance(value, (list, dict)) and len(str(value)) > 200:
                        if isinstance(value, list):
                            logger.info(f"  {key}: (list, length={len(value)})")
                        else:
                            logger.info(f"  {key}: (dict, keys={list(value.keys())})")
                    else:
                        logger.info(f"  {key}: {value}")
        elif node_output:
            logger.info(f"  {node_output}")

if __name__ == "__main__":
    asyncio.run(main())
