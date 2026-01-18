"""HistoricalDataNode 테스트 스크립트"""
import asyncio
import json
import os
import sys
from pathlib import Path

# 경로 설정
root_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "src" / "programgarden"))
sys.path.insert(0, str(root_dir / "src" / "core"))
sys.path.insert(0, str(root_dir / "src" / "finance"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from programgarden import ProgramGarden


def test_historical(product_type: str = "stock"):
    """HistoricalDataNode 테스트"""
    
    # 워크플로우 파일 선택
    workflows_dir = Path(__file__).parent / "workflows"
    
    if product_type == "stock":
        workflow_file = workflows_dir / "historical-data-stock.json"
        appkey = os.getenv("APPKEY")
        appsecret = os.getenv("APPSECRET")
        paper_trading = False
    else:
        workflow_file = workflows_dir / "historical-data-futures.json"
        appkey = os.getenv("APPKEY_FUTURE_FAKE")
        appsecret = os.getenv("APPSECRET_FUTURE_FAKE")
        paper_trading = True
    
    with open(workflow_file, "r") as f:
        workflow = json.load(f)
    
    # 실제 credential 주입
    for cred in workflow.get("credentials", []):
        cred["data"]["appkey"] = appkey
        cred["data"]["appsecret"] = appsecret
        cred["data"]["paper_trading"] = paper_trading
    
    print(f"\n{'='*60}")
    print(f"HistoricalDataNode 테스트 - {product_type.upper()}")
    print(f"{'='*60}")
    
    # 워크플로우 실행 (동기)
    pg = ProgramGarden()
    result = pg.run(workflow)
    
    # 결과 출력
    if result and "history" in result:
        history_output = result["history"]
        ohlcv_data = history_output.get("ohlcv_data", {})
        
        print(f"\n조회 기간: {history_output.get('period', 'N/A')}")
        print(f"간격: {history_output.get('interval', 'N/A')}")
        print(f"종목 수: {len(ohlcv_data)}")
        
        for symbol, bars in ohlcv_data.items():
            if bars:
                print(f"\n[{symbol}] {len(bars)}개 봉 데이터")
                print(f"  첫 번째 봉: {bars[0]}")
                print(f"  마지막 봉: {bars[-1]}")
            else:
                print(f"\n[{symbol}] 데이터 없음")
    else:
        print(f"\n결과: {result}")


if __name__ == "__main__":
    product = sys.argv[1] if len(sys.argv) > 1 else "stock"
    test_historical(product)
