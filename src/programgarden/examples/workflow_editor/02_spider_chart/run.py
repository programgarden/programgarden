#!/usr/bin/env python
"""
Spider Chart Example Runner

레이더(스파이더) 차트 예제를 실행하는 스크립트입니다.
웹 UI를 통해 시각화하려면 01_flow_visualizer/server.py를 사용하세요.

Usage:
    cd src/programgarden
    poetry run python examples/workflow_editor/02_spider_chart/run.py
    
    # Mock 데이터 테스트
    poetry run python examples/workflow_editor/02_spider_chart/run.py --mock
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add paths for imports
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root))


async def main(use_mock: bool = False):
    """Run spider chart workflow."""
    from workflow import get_spider_chart_workflow, get_mock_spider_data
    
    print("=" * 60)
    print("🕸️  Spider Chart Portfolio Analysis")
    print("=" * 60)
    
    try:
        from programgarden import ProgramGarden
        
        pg = ProgramGarden()
        
        if use_mock:
            print("\n📋 Using Mock Data workflow...")
            workflow = get_mock_spider_data()
        else:
            print("\n📋 Loading Spider Chart workflow...")
            workflow = get_spider_chart_workflow()
        
        print(f"   Workflow: {workflow.get('name', 'unknown')}")
        print(f"   Nodes: {len(workflow.get('nodes', []))}")
        print(f"   Edges: {len(workflow.get('edges', []))}")
        
        print("\n🚀 Starting workflow execution...")
        print("-" * 60)
        
        job = await pg.run_async(workflow)
        
        print("-" * 60)
        print(f"✅ Job completed: {job.job_id}")
        print(f"   Status: {job.status}")
        
        # Print display outputs if available
        state = job.get_state()
        if state and "node_outputs" in state:
            outputs = state["node_outputs"]
            if "spiderChart" in outputs:
                print("\n📊 Spider Chart Data:")
                chart_data = outputs["spiderChart"]
                if isinstance(chart_data, dict) and "data" in chart_data:
                    for item in chart_data["data"]:
                        symbol = item.get("symbol", "?")
                        values = item.get("values", [])
                        print(f"   {symbol}: {values}")
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("   Please set APPKEY and APPSECRET in your .env file")
        sys.exit(1)
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("   Make sure programgarden package is installed:")
        print("   cd src/programgarden && poetry install")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Spider Chart workflow")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of real API calls",
    )
    args = parser.parse_args()
    
    asyncio.run(main(use_mock=args.mock))
