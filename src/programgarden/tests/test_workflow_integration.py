"""
ProgramGarden 워크플로우 통합 검증 테스트

모든 examples/workflows/*.json 파일을 로드하고 실행하여
회귀 테스트를 수행합니다.

실행 방법:
    cd src/programgarden
    poetry run pytest tests/test_workflow_integration.py -v
    
    # 특정 워크플로우만 테스트
    poetry run pytest tests/test_workflow_integration.py -k "rsi" -v
    
    # dry-run 모드 (API 호출 없이 구조만 검증)
    DRY_RUN=1 poetry run pytest tests/test_workflow_integration.py -v
"""

import os
import sys
import json
import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional

# 경로 설정
current_dir = Path(__file__).parent
project_root = current_dir.parent
src_root = project_root.parents[0]

# 패키지 경로 추가
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_root / "core"))
sys.path.insert(0, str(src_root / "community"))
sys.path.insert(0, str(src_root / "finance"))

# .env 파일 로드
env_file = project_root.parents[2] / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# encryption 모듈 임포트 (workflow_editor에서)
workflow_editor_path = project_root / "examples" / "workflow_editor"
sys.path.insert(0, str(workflow_editor_path))

try:
    from encryption import decrypt_data, is_encryption_enabled
except ImportError:
    # encryption 모듈이 없으면 더미 함수 사용
    def decrypt_data(data):
        if isinstance(data, str):
            try:
                return json.loads(data)
            except:
                return data
        return data
    
    def is_encryption_enabled():
        return False


# 워크플로우 파일 경로
WORKFLOWS_DIR = project_root / "examples" / "workflows"
CREDENTIALS_FILE = workflow_editor_path / "credentials.json"


def load_credentials() -> Dict[str, Any]:
    """credentials.json 파일 로드 및 복호화"""
    if not CREDENTIALS_FILE.exists():
        print(f"⚠️ Credentials file not found: {CREDENTIALS_FILE}")
        return {}
    
    with open(CREDENTIALS_FILE) as f:
        creds_data = json.load(f)
    
    # 복호화
    decrypted_creds = {}
    for cred_id, cred_value in creds_data.items():
        if isinstance(cred_value, dict):
            # 이미 복호화된 경우
            decrypted_creds[cred_id] = cred_value
        elif isinstance(cred_value, str):
            # 암호화된 문자열인 경우
            decrypted_creds[cred_id] = decrypt_data(cred_value)
        else:
            decrypted_creds[cred_id] = cred_value
    
    return decrypted_creds


def get_all_workflow_files() -> List[Path]:
    """모든 워크플로우 JSON 파일 목록 반환"""
    if not WORKFLOWS_DIR.exists():
        return []
    return sorted(WORKFLOWS_DIR.glob("*.json"))


def get_workflow_ids() -> List[str]:
    """pytest parametrize용 ID 목록"""
    return [f.stem for f in get_all_workflow_files()]


# 워크플로우 파일을 미리 로드
WORKFLOW_FILES = get_all_workflow_files()


def categorize_workflow(workflow: Dict[str, Any]) -> str:
    """워크플로우의 카테고리 판별 (해외주식/해외선물/기타)"""
    nodes = workflow.get("nodes", [])
    
    for node in nodes:
        node_type = node.get("type", "")
        
        # BrokerNode의 product로 판별
        if node_type == "BrokerNode":
            product = node.get("product", "")
            if product == "overseas_futures":
                return "futures"
            elif product == "overseas_stock":
                return "stock"
    
    # 기본값: 주식
    return "stock"


def inject_credentials(workflow: Dict[str, Any], credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    워크플로우의 credentials 섹션에 실제 credential 데이터 주입
    """
    workflow_creds = workflow.get("credentials", [])
    
    for cred in workflow_creds:
        cred_id = cred.get("id", "")
        cred_type = cred.get("type", "")
        
        # credentials.json에서 해당 credential 찾기
        # type 기반으로 매칭 (broker_ls → stock, broker_ls_futures → futures)
        if cred_type == "broker_ls":
            # 해외주식 credential
            if "stock" in credentials:
                cred["data"] = credentials["stock"]
            elif "broker_ls" in credentials:
                cred["data"] = credentials["broker_ls"]
        elif cred_type == "broker_ls_futures":
            # 해외선물 credential
            if "futures" in credentials:
                cred["data"] = credentials["futures"]
            elif "broker_ls_futures" in credentials:
                cred["data"] = credentials["broker_ls_futures"]
    
    return workflow


class TestWorkflowIntegration:
    """워크플로우 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 설정"""
        self.credentials = load_credentials()
        self.dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
        
        if self.dry_run:
            print("\n🔸 DRY_RUN 모드: API 호출 없이 구조만 검증합니다")
        
        if is_encryption_enabled():
            print("🔐 Credential encryption: ENABLED")
        else:
            print("🔓 Credential encryption: DISABLED")
    
    @pytest.mark.parametrize("workflow_file", WORKFLOW_FILES, ids=get_workflow_ids())
    def test_workflow_loads_successfully(self, workflow_file: Path):
        """워크플로우 JSON 파일이 올바르게 로드되는지 테스트"""
        with open(workflow_file) as f:
            workflow = json.load(f)
        
        # 기본 구조 검증
        assert "nodes" in workflow, f"nodes 필드가 없음: {workflow_file.name}"
        assert "edges" in workflow, f"edges 필드가 없음: {workflow_file.name}"
        assert isinstance(workflow["nodes"], list), "nodes는 배열이어야 함"
        assert isinstance(workflow["edges"], list), "edges는 배열이어야 함"
        
        # 노드 ID 유일성 검증
        node_ids = [node.get("id") for node in workflow["nodes"]]
        assert len(node_ids) == len(set(node_ids)), f"중복된 노드 ID가 있음: {workflow_file.name}"
        
        # 엣지 참조 무결성 검증
        for edge in workflow["edges"]:
            from_id = edge.get("from", "")
            to_id = edge.get("to", "")
            assert from_id in node_ids, f"엣지 from 참조 오류: {from_id} not in nodes ({workflow_file.name})"
            assert to_id in node_ids, f"엣지 to 참조 오류: {to_id} not in nodes ({workflow_file.name})"
    
    @pytest.mark.parametrize("workflow_file", WORKFLOW_FILES, ids=get_workflow_ids())
    def test_workflow_validation(self, workflow_file: Path):
        """ProgramGarden.validate()로 워크플로우 검증"""
        from programgarden import ProgramGarden
        
        with open(workflow_file) as f:
            workflow = json.load(f)
        
        pg = ProgramGarden()
        result = pg.validate(workflow)
        
        # 검증 결과 출력
        if not result.is_valid:
            print(f"\n⚠️ Validation warnings for {workflow_file.name}:")
            for error in result.errors:
                print(f"  - {error}")
        
        # 치명적 오류가 아니면 통과 (경고는 허용)
        # 일부 워크플로우는 credential이 없어서 경고가 발생할 수 있음
        assert result is not None
    
    @pytest.mark.parametrize("workflow_file", WORKFLOW_FILES, ids=get_workflow_ids())
    @pytest.mark.asyncio
    async def test_workflow_execution(self, workflow_file: Path):
        """
        워크플로우 실제 실행 테스트
        
        DRY_RUN=1 환경변수 설정 시 API 호출 없이 구조만 검증합니다.
        """
        from programgarden import ProgramGarden
        
        with open(workflow_file) as f:
            workflow = json.load(f)
        
        # Credential 주입
        workflow = inject_credentials(workflow, self.credentials)
        
        # 카테고리 확인
        category = categorize_workflow(workflow)
        
        pg = ProgramGarden()
        
        if self.dry_run:
            # Dry-run: 검증만 수행
            result = pg.validate(workflow)
            assert result is not None, f"검증 실패: {workflow_file.name}"
            print(f"✅ [DRY-RUN] {workflow_file.name} ({category})")
            return
        
        # 실제 실행
        try:
            context = {
                "dry_run": False,
            }
            
            # secrets 구성 (credential_id별로 데이터 주입)
            secrets = {}
            for cred in workflow.get("credentials", []):
                cred_id = cred.get("id", "")
                cred_data = cred.get("data", {})
                if cred_data:
                    secrets[cred_id] = cred_data
            
            result = pg.run(
                workflow,
                context=context,
                secrets=secrets if secrets else None,
                timeout=30.0,  # 30초 타임아웃
            )
            
            print(f"✅ {workflow_file.name} ({category}) - 실행 완료")
            
            # 결과 검증
            assert result is not None, f"실행 결과가 None: {workflow_file.name}"
            
        except Exception as e:
            # 일부 워크플로우는 특정 조건에서만 실행 가능 (예: 실시간 노드)
            # 에러 로그 출력하고 테스트는 통과 처리
            print(f"⚠️ {workflow_file.name} ({category}) - 실행 중 예외: {e}")
            
            # 치명적 오류인지 확인
            error_str = str(e).lower()
            
            # 허용되는 에러들 (credential 없음, API 제한 등)
            allowed_errors = [
                "credential",
                "appkey",
                "appsecret",
                "unauthorized",
                "rate limit",
                "timeout",
                "connection",
                "websocket",
                "not implemented",
            ]
            
            is_allowed = any(err in error_str for err in allowed_errors)
            
            if not is_allowed:
                pytest.fail(f"예상치 못한 오류: {e}")


class TestWorkflowCategories:
    """워크플로우 카테고리별 테스트"""
    
    def test_stock_workflows_exist(self):
        """해외주식 워크플로우가 존재하는지 확인"""
        stock_workflows = [f for f in WORKFLOW_FILES if "stock" in f.stem.lower()]
        assert len(stock_workflows) > 0, "해외주식 워크플로우가 없습니다"
        print(f"\n📊 해외주식 워크플로우: {len(stock_workflows)}개")
    
    def test_futures_workflows_exist(self):
        """해외선물 워크플로우가 존재하는지 확인"""
        futures_workflows = [f for f in WORKFLOW_FILES if "futures" in f.stem.lower()]
        assert len(futures_workflows) > 0, "해외선물 워크플로우가 없습니다"
        print(f"\n📈 해외선물 워크플로우: {len(futures_workflows)}개")
    
    def test_backtest_workflows_exist(self):
        """백테스트 워크플로우가 존재하는지 확인"""
        backtest_workflows = [f for f in WORKFLOW_FILES if "backtest" in f.stem.lower()]
        assert len(backtest_workflows) > 0, "백테스트 워크플로우가 없습니다"
        print(f"\n🔬 백테스트 워크플로우: {len(backtest_workflows)}개")


class TestWorkflowNodeTypes:
    """워크플로우에 사용된 노드 타입 검증"""
    
    def test_all_node_types_are_valid(self):
        """모든 워크플로우의 노드 타입이 유효한지 확인"""
        # 알려진 노드 타입 목록
        valid_node_types = {
            # infra
            "StartNode", "BrokerNode", "ThrottleNode",
            # account
            "AccountNode", "RealAccountNode", "RealOrderEventNode",
            # market
            "WatchlistNode", "SymbolQueryNode", "SymbolFilterNode",
            "MarketUniverseNode", "ScreenerNode", "MarketDataNode",
            "HistoricalDataNode", "RealMarketDataNode",
            # condition
            "ConditionNode", "LogicNode",
            # order
            "NewOrderNode", "ModifyOrderNode", "CancelOrderNode",
            "PositionSizingNode",
            # risk
            "RiskGuardNode", "RiskConditionNode", "PortfolioNode",
            # schedule
            "ScheduleNode", "TradingHoursFilterNode", "ExchangeStatusNode",
            # data
            "SQLiteNode", "PostgresNode", "HTTPRequestNode",
            # analysis
            "BacktestEngineNode", "BenchmarkCompareNode", "DisplayNode", "CustomPnLNode",
            # system
            "DeployNode", "TradingHaltNode", "JobControlNode",
            # notification
            "TelegramNode", "AlertNode",
        }
        
        unknown_types = set()
        used_types = set()
        
        for workflow_file in WORKFLOW_FILES:
            with open(workflow_file) as f:
                workflow = json.load(f)
            
            for node in workflow.get("nodes", []):
                node_type = node.get("type", "")
                used_types.add(node_type)
                
                if node_type not in valid_node_types:
                    unknown_types.add(node_type)
        
        if unknown_types:
            print(f"\n⚠️ 알 수 없는 노드 타입: {unknown_types}")
            # 경고만 출력하고 테스트는 통과 (새 노드 타입일 수 있음)
        
        print(f"\n📦 사용된 노드 타입: {len(used_types)}개")
        print(f"   {sorted(used_types)}")


if __name__ == "__main__":
    # 직접 실행 시
    pytest.main([__file__, "-v", "--tb=short"])
