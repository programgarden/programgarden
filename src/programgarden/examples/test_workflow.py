#!/usr/bin/env python
"""
워크플로우 테스트 스크립트

Usage:
    cd src/programgarden
    poetry run python examples/test_workflow.py [workflow_file]

Example:
    poetry run python examples/test_workflow.py examples/workflows/20-data-http.json
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
project_root = current_dir.parents[2]
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "community"))

# .env 파일 로드 (프로젝트 루트)
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Credential store 설정 (python_server와 동일한 credentials.json 사용)
credential_store_path = current_dir / "python_server" / "credentials.json"
os.environ["PROGRAMGARDEN_CREDENTIAL_STORE"] = str(credential_store_path)


class TestListener:
    """테스트용 리스너 - 완료 시 이벤트 설정"""

    def __init__(self):
        self.completed = asyncio.Event()
        self.final_status = None
        self.node_states = {}

    async def on_node_state_change(self, event) -> None:
        from programgarden_core.bases.listener import NodeState

        state_emoji = {
            NodeState.PENDING: "⏳",
            NodeState.RUNNING: "🔄",
            NodeState.COMPLETED: "✅",
            NodeState.FAILED: "❌",
            NodeState.SKIPPED: "⏭️",
        }
        emoji = state_emoji.get(event.state, "❓")

        msg = f"{emoji} [{event.node_id}] {event.state.value}"
        if event.duration_ms:
            msg += f" ({event.duration_ms:.1f}ms)"
        if event.error:
            msg += f" - {event.error}"
        print(msg)

        # Save state
        self.node_states[event.node_id] = {
            "type": event.node_type,
            "status": event.state.value,
            "outputs": event.outputs,
            "error": event.error,
        }

    async def on_edge_state_change(self, event) -> None:
        pass

    async def on_log(self, event) -> None:
        level_color = {
            "debug": "\033[90m",
            "info": "\033[92m",
            "warning": "\033[93m",
            "error": "\033[91m",
        }
        reset = "\033[0m"
        color = level_color.get(event.level, "")

        node_tag = f"[{event.node_id}] " if event.node_id else ""
        print(f"{color}{event.level.upper():>7}{reset} {node_tag}{event.message}")

    async def on_job_state_change(self, event) -> None:
        state_emoji = {
            "pending": "⏳",
            "running": "🚀",
            "completed": "🎉",
            "failed": "💥",
            "cancelled": "🛑",
        }
        emoji = state_emoji.get(event.state, "❓")
        print(f"\n{emoji} Job [{event.job_id}] → {event.state}")

        # Set completion event when done
        if event.state in ("completed", "failed", "cancelled"):
            self.final_status = event.state
            self.completed.set()

    async def on_display_data(self, event) -> None:
        print(f"📊 Display [{event.node_id}]: {event.chart_type} - {event.title}")
        if event.data:
            data_str = json.dumps(event.data, ensure_ascii=False, indent=2)[:500]
            print(f"   Data: {data_str}")

    async def on_workflow_pnl_update(self, event) -> None:
        pass

    async def on_retry(self, event) -> None:
        yellow = "\033[93m"
        reset = "\033[0m"
        print(f"{yellow}⚠️  [{event.node_id}] {event.error_type.value} 발생, "
              f"재시도 중 ({event.attempt}/{event.max_retries})... "
              f"{event.next_retry_in:.1f}초 후{reset}")


def load_credentials_from_store(workflow: dict) -> list:
    """워크플로우의 credential ID 참조를 credential_store에서 조회하여 완전한 credential 리스트로 변환"""
    from programgarden_core.registry import get_credential_store

    # encryption 모듈 경로 추가 (python_server 디렉토리)
    encryption_path = current_dir / "python_server"
    if str(encryption_path) not in sys.path:
        sys.path.insert(0, str(encryption_path))
    from encryption import decrypt_data

    store = get_credential_store()
    credentials_list = []

    for cred_ref in workflow.get("credentials", []):
        cred_id = cred_ref.get("id")
        if not cred_id:
            continue

        stored = store.get(cred_id)
        if stored:
            # 암호화된 data를 복호화
            decrypted_data = decrypt_data(stored.data)
            credentials_list.append({
                "id": stored.id,
                "type": stored.credential_type,
                "name": stored.name,
                "data": decrypted_data,
            })
            print(f"🔑 Loaded credential: {cred_id} ({stored.name})")
        else:
            print(f"⚠️  Credential not found: {cred_id}")

    return credentials_list


async def test_workflow(workflow_path: str):
    """워크플로우 파일을 로드하고 실행"""
    from programgarden import ProgramGarden

    # Load workflow
    with open(workflow_path) as f:
        workflow = json.load(f)

    # Load credentials from store
    credentials_list = load_credentials_from_store(workflow)
    workflow["credentials"] = credentials_list

    print(f"\n{'='*60}")
    print(f"🧪 Testing Workflow: {workflow.get('name', 'Unknown')}")
    print(f"{'='*60}")
    print(f"📋 ID: {workflow.get('id')}")
    print(f"📝 Description: {workflow.get('description', 'N/A')}")
    print(f"📊 Nodes: {len(workflow.get('nodes', []))}")
    print(f"🔗 Edges: {len(workflow.get('edges', []))}")
    print(f"🔑 Credentials: {len(workflow.get('credentials', []))}")
    print(f"{'='*60}\n")

    # Create ProgramGarden instance
    pg = ProgramGarden()
    listener = TestListener()

    try:
        # Run workflow
        job = await pg.run_async(workflow, listeners=[listener])

        # Wait for completion with timeout
        print("\n⏳ Waiting for workflow to complete...")
        try:
            await asyncio.wait_for(listener.completed.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            print("⏱️  Timeout - stopping job...")
            await job.stop()
            return False

        # Print results
        print(f"\n{'='*60}")
        if listener.final_status == "completed":
            print(f"✅ Workflow completed!")
        else:
            print(f"❌ Workflow {listener.final_status}!")
        print(f"{'='*60}")

        # Print node results
        for node_id, node_state in listener.node_states.items():
            status = node_state.get("status", "unknown")
            status_emoji = "✅" if status == "completed" else "❌" if status == "failed" else "⏭️"
            print(f"\n{status_emoji} Node: {node_id}")
            print(f"   Type: {node_state.get('type', 'unknown')}")
            print(f"   Status: {status}")
            if node_state.get("error"):
                print(f"   Error: {node_state.get('error')}")
            if node_state.get("outputs"):
                outputs = node_state.get("outputs", {})
                for port, value in outputs.items():
                    if isinstance(value, (dict, list)):
                        value_str = json.dumps(value, ensure_ascii=False, indent=2)[:500]
                    else:
                        value_str = str(value)[:500]
                    print(f"   Output [{port}]: {value_str}")

        return listener.final_status == "completed"

    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # Default workflow
    default_workflow = "examples/workflows/20-data-http.json"

    if len(sys.argv) > 1:
        workflow_path = sys.argv[1]
    else:
        workflow_path = default_workflow

    # Make path absolute if relative
    if not Path(workflow_path).is_absolute():
        workflow_path = Path(__file__).parent.parent / workflow_path

    if not Path(workflow_path).exists():
        print(f"❌ Workflow file not found: {workflow_path}")
        sys.exit(1)

    # Run test
    success = asyncio.run(test_workflow(str(workflow_path)))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
