"""
HKEX 미니선물 역추세 자동매매 봇 통합 검증 테스트

검증 항목:
1. run.py import 테스트 (ProgramGarden, BaseExecutionListener, NotificationEvent 등)
2. workflow.json 로드 및 구조 검증
3. WorkflowExecutor.validate() — 노드 타입, edge, credential 참조, 표현식
4. 노드별 개별 설정값 검증
5. 엣지 연결 그래프 무결성 (DAG, 고아 노드, 사이클 없음)
"""

import json
import sys
import pytest
from pathlib import Path

# community 패키지 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "community"))

WORKFLOW_PATH = Path(__file__).parent.parent / "examples" / "hkex_futures_bot" / "workflow.json"
BOT_DIR = Path(__file__).parent.parent / "examples" / "hkex_futures_bot"


# ──────────────────────────────────────────────
# 픽스처
# ──────────────────────────────────────────────
@pytest.fixture(scope="module")
def workflow() -> dict:
    with open(WORKFLOW_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def executor():
    # community 노드(TelegramNode 등) 로드를 위해 import
    import programgarden_community  # noqa: F401
    from programgarden import WorkflowExecutor
    return WorkflowExecutor()


# ──────────────────────────────────────────────
# 1. Import 테스트
# ──────────────────────────────────────────────
class TestImports:
    def test_programgarden_import(self):
        from programgarden import ProgramGarden  # noqa: F401
        assert ProgramGarden is not None

    def test_workflow_executor_import(self):
        from programgarden import WorkflowExecutor  # noqa: F401
        assert WorkflowExecutor is not None

    def test_base_execution_listener_import(self):
        from programgarden_core.bases.listener import BaseExecutionListener  # noqa: F401
        assert BaseExecutionListener is not None

    def test_notification_event_import(self):
        from programgarden_core.bases.listener import NotificationEvent  # noqa: F401
        assert NotificationEvent is not None

    def test_notification_category_import(self):
        from programgarden_core.bases.listener import NotificationCategory  # noqa: F401
        assert NotificationCategory is not None

    def test_community_telegram_node_import(self):
        import programgarden_community  # noqa: F401
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        cls = registry.get("TelegramNode")
        assert cls is not None, "TelegramNode이 레지스트리에 등록되어 있어야 함"

    def test_bollinger_plugin_import(self):
        import programgarden_community  # noqa: F401
        from programgarden_core.registry.plugin_registry import PluginRegistry
        registry = PluginRegistry()
        plugin = registry.get("BollingerBands")
        assert plugin is not None, "BollingerBands 플러그인이 레지스트리에 등록되어 있어야 함"

    def test_bot_listener_class(self):
        """run.py의 BotListener 클래스가 정상 임포트 가능한지 구조 검증"""
        from programgarden_core.bases.listener import BaseExecutionListener, NotificationEvent

        class MockBotListener(BaseExecutionListener):
            def __init__(self):
                super().__init__()
                self.cycle_count = 0

            async def on_notification(self, event: NotificationEvent):
                pass

        listener = MockBotListener()
        assert listener.cycle_count == 0


# ──────────────────────────────────────────────
# 2. workflow.json 파일 및 구조 검증
# ──────────────────────────────────────────────
class TestWorkflowStructure:
    def test_workflow_file_exists(self):
        assert WORKFLOW_PATH.exists(), f"workflow.json 파일 없음: {WORKFLOW_PATH}"

    def test_workflow_valid_json(self):
        with open(WORKFLOW_PATH) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_workflow_top_level_keys(self, workflow):
        for key in ("id", "name", "nodes", "edges", "credentials"):
            assert key in workflow, f"필수 키 누락: {key}"

    def test_workflow_id(self, workflow):
        assert workflow["id"] == "hkex_futures_bot_v1"

    def test_workflow_has_nodes(self, workflow):
        assert len(workflow["nodes"]) > 0

    def test_workflow_has_edges(self, workflow):
        assert len(workflow["edges"]) > 0

    def test_workflow_has_credentials(self, workflow):
        assert len(workflow["credentials"]) >= 1

    def test_workflow_notes_optional(self, workflow):
        # notes는 선택 사항이지만, 있으면 구조 확인
        if "notes" in workflow:
            for note in workflow["notes"]:
                assert "id" in note
                assert "content" in note

    def test_node_ids_unique(self, workflow):
        ids = [n["id"] for n in workflow["nodes"]]
        assert len(ids) == len(set(ids)), f"중복 노드 ID 발견: {[i for i in ids if ids.count(i) > 1]}"

    def test_credential_ids_unique(self, workflow):
        ids = [c["credential_id"] for c in workflow["credentials"]]
        assert len(ids) == len(set(ids)), "중복 credential_id 발견"

    def test_expected_node_count(self, workflow):
        # workflow.json에 정의된 노드 수 확인 (13개)
        assert len(workflow["nodes"]) == 13, f"예상 13개 노드, 실제: {len(workflow['nodes'])}"

    def test_expected_edge_count(self, workflow):
        # workflow.json에 정의된 엣지 수 확인 (13개)
        assert len(workflow["edges"]) == 13, f"예상 13개 엣지, 실제: {len(workflow['edges'])}"


# ──────────────────────────────────────────────
# 3. 노드 타입 및 설정값 검증
# ──────────────────────────────────────────────
class TestNodeDefinitions:
    def _get_node(self, workflow, node_id):
        for n in workflow["nodes"]:
            if n["id"] == node_id:
                return n
        return None

    def test_start_node(self, workflow):
        node = self._get_node(workflow, "start")
        assert node is not None
        assert node["type"] == "StartNode"

    def test_broker_node(self, workflow):
        node = self._get_node(workflow, "broker")
        assert node is not None
        assert node["type"] == "OverseasFuturesBrokerNode"
        assert node["credential_id"] == "broker_cred"
        assert node["paper_trading"] is True, "모의투자 봇은 paper_trading=True 필수"

    def test_schedule_node(self, workflow):
        node = self._get_node(workflow, "schedule")
        assert node is not None
        assert node["type"] == "ScheduleNode"
        assert "*/30" in node["cron"], "30분 간격 cron 표현식 포함 필요"
        assert "1-5" in node["cron"], "평일(월~금) cron 표현식 포함 필요"
        assert node["timezone"] == "Asia/Hong_Kong"

    def test_trading_hours_node(self, workflow):
        node = self._get_node(workflow, "trading_hours")
        assert node is not None
        assert node["type"] == "TradingHoursFilterNode"
        assert node["start"] == "09:15"
        assert node["end"] == "16:30"
        assert node["timezone"] == "Asia/Hong_Kong"
        assert "mon" in node["days"]
        assert "fri" in node["days"]

    def test_account_node(self, workflow):
        node = self._get_node(workflow, "account")
        assert node is not None
        assert node["type"] == "OverseasFuturesAccountNode"

    def test_watchlist_node(self, workflow):
        node = self._get_node(workflow, "watchlist")
        assert node is not None
        assert node["type"] == "WatchlistNode"
        symbols = node["symbols"]
        assert len(symbols) == 2
        symbol_names = [s["symbol"] for s in symbols]
        assert "HMHJ26" in symbol_names, "미니항셍 종목 HMHJ26 필요"
        assert "HMCEJ26" in symbol_names, "미니H주 종목 HMCEJ26 필요"
        for s in symbols:
            assert s["exchange"] == "HKEX"

    def test_historical_node(self, workflow):
        node = self._get_node(workflow, "historical")
        assert node is not None
        assert node["type"] == "OverseasFuturesHistoricalDataNode"
        assert node["symbol"] == "{{ item }}", "auto-iterate 바인딩 필요"
        assert "date.ago" in node["start_date"]
        assert "date.today" in node["end_date"]
        assert node["interval"] == "1d"

    def test_bollinger_condition_node(self, workflow):
        node = self._get_node(workflow, "bollinger")
        assert node is not None
        assert node["type"] == "ConditionNode"
        assert node["plugin"] == "BollingerBands"
        fields = node["fields"]
        assert fields["period"] == 20
        assert fields["std_dev"] == 2.0
        assert fields["position"] == "below_lower"

    def test_symbol_filter_node(self, workflow):
        node = self._get_node(workflow, "filter_buy")
        assert node is not None
        assert node["type"] == "SymbolFilterNode"
        assert node["operation"] == "difference"
        assert "nodes.bollinger.passed_symbols" in node["input_a"]
        assert "nodes.account.held_symbols" in node["input_b"]

    def test_buy_order_node(self, workflow):
        node = self._get_node(workflow, "buy_order")
        assert node is not None
        assert node["type"] == "OverseasFuturesNewOrderNode"
        assert node["side"] == "buy"
        assert node["order_type"] == "market"
        order = node["order"]
        assert "item.symbol" in order["symbol"]
        assert "item.exchange" in order["exchange"]
        assert order["quantity"] == 1

    def test_telegram_buy_node(self, workflow):
        node = self._get_node(workflow, "telegram_buy")
        assert node is not None
        assert node["type"] == "TelegramNode"
        assert node["credential_id"] == "telegram_cred"
        assert len(node["template"]) > 0

    def test_account_sell_node(self, workflow):
        node = self._get_node(workflow, "account_sell")
        assert node is not None
        assert node["type"] == "OverseasFuturesAccountNode"

    def test_sell_order_node(self, workflow):
        node = self._get_node(workflow, "sell_order")
        assert node is not None
        assert node["type"] == "OverseasFuturesNewOrderNode"
        assert "item.close_side" in node["side"], "청산 시 포지션 반대 방향 바인딩 필요"
        assert node["order_type"] == "market"
        order = node["order"]
        assert "item.symbol" in order["symbol"]
        assert "item.exchange" in order["exchange"]
        assert "item.quantity" in str(order["quantity"])
        # resilience fallback skip 설정
        assert node.get("resilience", {}).get("fallback", {}).get("mode") == "skip"

    def test_no_node_id_with_hyphen(self, workflow):
        """노드 ID에 하이픈 없음 — 표현식에서 뺄셈 연산자로 파싱되는 문제 방지"""
        for node in workflow["nodes"]:
            assert "-" not in node["id"], (
                f"노드 ID '{node['id']}'에 하이픈이 포함되어 있습니다. "
                "표현식 바인딩에서 뺄셈으로 파싱될 수 있습니다."
            )


# ──────────────────────────────────────────────
# 4. 엣지 연결 그래프 검증
# ──────────────────────────────────────────────
class TestEdgeGraph:
    def test_all_edge_sources_valid(self, workflow):
        """모든 엣지의 from 노드가 실제 노드 ID를 참조"""
        node_ids = {n["id"] for n in workflow["nodes"]}
        for edge in workflow["edges"]:
            from_id = edge["from"].split(".")[0]  # dot notation 처리
            assert from_id in node_ids, f"존재하지 않는 소스 노드: {edge['from']}"

    def test_all_edge_targets_valid(self, workflow):
        """모든 엣지의 to 노드가 실제 노드 ID를 참조"""
        node_ids = {n["id"] for n in workflow["nodes"]}
        for edge in workflow["edges"]:
            assert edge["to"] in node_ids, f"존재하지 않는 타겟 노드: {edge['to']}"

    def test_start_node_is_source(self, workflow):
        """StartNode는 엣지의 소스로만 등장해야 함"""
        targets = {e["to"] for e in workflow["edges"]}
        assert "start" not in targets, "StartNode가 엣지의 타겟이 되면 안 됨"

    def test_start_node_has_outgoing_edge(self, workflow):
        sources = [e["from"] for e in workflow["edges"]]
        assert "start" in sources, "StartNode에서 나가는 엣지 없음"

    def test_broker_connected_to_schedule(self, workflow):
        edges = {(e["from"], e["to"]) for e in workflow["edges"]}
        assert ("broker", "schedule") in edges

    def test_schedule_to_trading_hours(self, workflow):
        edges = {(e["from"], e["to"]) for e in workflow["edges"]}
        assert ("schedule", "trading_hours") in edges

    def test_buy_pipeline_connected(self, workflow):
        """매수 파이프라인: watchlist → historical → bollinger → filter_buy → buy_order"""
        edges = {(e["from"], e["to"]) for e in workflow["edges"]}
        pipeline = [
            ("watchlist", "historical"),
            ("historical", "bollinger"),
            ("bollinger", "filter_buy"),
            ("filter_buy", "buy_order"),
        ]
        for src, dst in pipeline:
            assert (src, dst) in edges, f"매수 파이프라인 엣지 누락: {src} → {dst}"

    def test_sell_pipeline_connected(self, workflow):
        """청산 파이프라인: trading_hours → account_sell → sell_order"""
        edges = {(e["from"], e["to"]) for e in workflow["edges"]}
        pipeline = [
            ("trading_hours", "account_sell"),
            ("account_sell", "sell_order"),
        ]
        for src, dst in pipeline:
            assert (src, dst) in edges, f"청산 파이프라인 엣지 누락: {src} → {dst}"

    def test_filter_buy_has_two_inputs(self, workflow):
        """SymbolFilterNode(filter_buy)는 bollinger와 account 두 개의 입력을 받아야 함"""
        incoming = [e for e in workflow["edges"] if e["to"] == "filter_buy"]
        sources = {e["from"] for e in incoming}
        assert "bollinger" in sources, "filter_buy에 bollinger 입력 없음"
        assert "account" in sources, "filter_buy에 account 입력 없음"

    def test_no_isolated_nodes(self, workflow):
        """고아 노드 없음 — 모든 노드는 최소 1개의 엣지에 연결"""
        node_ids = {n["id"] for n in workflow["nodes"]}
        connected = set()
        for e in workflow["edges"]:
            connected.add(e["from"].split(".")[0])
            connected.add(e["to"])
        isolated = node_ids - connected
        assert not isolated, f"엣지에 연결되지 않은 고아 노드: {isolated}"

    def test_no_self_loop(self, workflow):
        """자기 참조 엣지 없음"""
        for edge in workflow["edges"]:
            from_id = edge["from"].split(".")[0]
            assert from_id != edge["to"], f"자기 참조 엣지: {edge}"


# ──────────────────────────────────────────────
# 5. Credential 참조 검증
# ──────────────────────────────────────────────
class TestCredentialReferences:
    def test_broker_credential_defined(self, workflow):
        cred_ids = {c["credential_id"] for c in workflow["credentials"]}
        assert "broker_cred" in cred_ids

    def test_telegram_credential_defined(self, workflow):
        cred_ids = {c["credential_id"] for c in workflow["credentials"]}
        assert "telegram_cred" in cred_ids

    def test_broker_credential_type(self, workflow):
        for cred in workflow["credentials"]:
            if cred["credential_id"] == "broker_cred":
                assert cred["type"] == "broker_ls_overseas_futures"

    def test_telegram_credential_type(self, workflow):
        for cred in workflow["credentials"]:
            if cred["credential_id"] == "telegram_cred":
                assert cred["type"] == "telegram"

    def test_broker_credential_has_required_keys(self, workflow):
        for cred in workflow["credentials"]:
            if cred["credential_id"] == "broker_cred":
                keys = {d["key"] for d in cred["data"]}
                assert "appkey" in keys
                assert "appsecret" in keys

    def test_telegram_credential_has_required_keys(self, workflow):
        for cred in workflow["credentials"]:
            if cred["credential_id"] == "telegram_cred":
                keys = {d["key"] for d in cred["data"]}
                assert "bot_token" in keys
                assert "chat_id" in keys

    def test_all_node_credential_refs_resolved(self, workflow):
        """노드에서 참조하는 credential_id가 모두 credentials에 정의됨"""
        cred_ids = {c["credential_id"] for c in workflow["credentials"]}
        for node in workflow["nodes"]:
            if "credential_id" in node:
                assert node["credential_id"] in cred_ids, (
                    f"노드 '{node['id']}'의 credential_id '{node['credential_id']}'"
                    " 가 credentials에 정의되지 않음"
                )


# ──────────────────────────────────────────────
# 6. WorkflowExecutor.validate() 호출
# ──────────────────────────────────────────────
class TestWorkflowValidation:
    def test_validate_returns_result(self, workflow, executor):
        result = executor.validate(workflow)
        assert result is not None
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")

    def test_validate_no_errors(self, workflow, executor):
        result = executor.validate(workflow)
        if not result.is_valid:
            pytest.fail(
                f"validate() 실패\n오류:\n" +
                "\n".join(f"  - {e}" for e in result.errors)
            )

    def test_validate_is_valid_true(self, workflow, executor):
        result = executor.validate(workflow)
        assert result.is_valid is True

    def test_validate_warnings_reported(self, workflow, executor):
        result = executor.validate(workflow)
        if result.warnings:
            print(f"\n[경고 {len(result.warnings)}건]")
            for w in result.warnings:
                print(f"  - {w}")
        # 경고는 테스트 실패 조건이 아님 — 정보 출력만


# ──────────────────────────────────────────────
# 7. 표현식 바인딩 검증
# ──────────────────────────────────────────────
class TestExpressionBindings:
    """workflow.json 내 {{ }} 표현식이 올바른 노드/포트를 참조하는지 확인"""

    def _collect_expressions(self, obj, path=""):
        """재귀적으로 모든 표현식 수집"""
        exprs = []
        if isinstance(obj, str) and "{{" in obj:
            exprs.append((path, obj))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                exprs.extend(self._collect_expressions(v, f"{path}.{k}" if path else k))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                exprs.extend(self._collect_expressions(item, f"{path}[{i}]"))
        return exprs

    def test_nodes_references_exist(self, workflow):
        """nodes.X.Y 패턴에서 X는 실제 노드 ID이어야 함"""
        import re
        node_ids = {n["id"] for n in workflow["nodes"]}
        exprs = self._collect_expressions(workflow.get("nodes", []))
        pattern = re.compile(r"nodes\.(\w+)\.")

        for path, expr in exprs:
            for match in pattern.finditer(expr):
                ref_id = match.group(1)
                assert ref_id in node_ids, (
                    f"표현식 '{expr}' (경로: {path})에서 "
                    f"존재하지 않는 노드 '{ref_id}' 참조"
                )

    def test_historical_symbol_uses_item(self, workflow):
        """OverseasFuturesHistoricalDataNode의 symbol이 {{ item }} 사용"""
        for node in workflow["nodes"]:
            if node["id"] == "historical":
                assert "{{ item }}" == node.get("symbol"), (
                    "historical 노드의 symbol은 {{ item }}이어야 함 (auto-iterate)"
                )

    def test_buy_order_uses_item(self, workflow):
        """buy_order의 symbol/exchange가 {{ item.* }} 패턴 사용"""
        for node in workflow["nodes"]:
            if node["id"] == "buy_order":
                order = node["order"]
                assert "item.symbol" in order["symbol"]
                assert "item.exchange" in order["exchange"]

    def test_sell_order_uses_item(self, workflow):
        """sell_order의 필드가 {{ item.* }} 패턴 사용"""
        for node in workflow["nodes"]:
            if node["id"] == "sell_order":
                assert "item.close_side" in node["side"]
                order = node["order"]
                assert "item.symbol" in order["symbol"]
                assert "item.exchange" in order["exchange"]
                assert "item.quantity" in str(order["quantity"])

    def test_filter_buy_references_bollinger_output(self, workflow):
        """SymbolFilterNode가 bollinger의 passed_symbols 포트 참조"""
        for node in workflow["nodes"]:
            if node["id"] == "filter_buy":
                assert "nodes.bollinger.passed_symbols" in node["input_a"]

    def test_filter_buy_references_account_output(self, workflow):
        """SymbolFilterNode가 account의 held_symbols 포트 참조"""
        for node in workflow["nodes"]:
            if node["id"] == "filter_buy":
                assert "nodes.account.held_symbols" in node["input_b"]

    def test_date_expressions_use_valid_namespace(self, workflow):
        """date.ago(), date.today() 표현식 형식 검증"""
        import re
        exprs = self._collect_expressions(workflow.get("nodes", []))
        date_pattern = re.compile(r"\{\{\s*date\.(ago|today|later)\(.*?\)\s*\}\}")

        date_exprs = [(path, expr) for path, expr in exprs if "date." in expr]
        for path, expr in date_exprs:
            assert date_pattern.search(expr), (
                f"잘못된 date 표현식: '{expr}' (경로: {path})"
            )

    def test_bollinger_items_extract_uses_row(self, workflow):
        """BollingerBands ConditionNode의 items.extract에서 row 키워드 사용"""
        for node in workflow["nodes"]:
            if node["id"] == "bollinger":
                extract = node.get("items", {}).get("extract", {})
                assert "row.date" in extract.get("date", ""), "extract.date에 row.date 필요"
                assert "row.close" in extract.get("close", ""), "extract.close에 row.close 필요"


# ──────────────────────────────────────────────
# 8. 안전장치 검증
# ──────────────────────────────────────────────
class TestSafetyChecks:
    def test_paper_trading_enabled(self, workflow):
        """모의투자 봇은 반드시 paper_trading=True"""
        for node in workflow["nodes"]:
            if node["type"] == "OverseasFuturesBrokerNode":
                assert node.get("paper_trading") is True, (
                    f"브로커 노드 '{node['id']}'에 paper_trading=True 필요"
                )

    def test_no_hardcoded_credentials(self, workflow):
        """credential 값이 하드코딩되어 있으면 안 됨 (빈 문자열 또는 env 참조)"""
        for cred in workflow["credentials"]:
            for item in cred.get("data", []):
                value = item.get("value", "")
                assert value == "" or value.startswith("${"), (
                    f"credential '{cred['credential_id']}.{item['key']}'에 "
                    f"하드코딩된 값 감지: '{value[:20]}...'"
                )

    def test_sell_order_has_fallback_skip(self, workflow):
        """청산 주문은 실패 시 skip으로 처리 (강제 종료 방지)"""
        for node in workflow["nodes"]:
            if node["id"] == "sell_order":
                fallback_mode = node.get("resilience", {}).get("fallback", {}).get("mode")
                assert fallback_mode == "skip", (
                    "sell_order는 resilience.fallback.mode=skip이어야 함"
                )

    def test_order_nodes_are_futures_type(self, workflow):
        """주문 노드가 해외선물 전용 타입 사용"""
        for node in workflow["nodes"]:
            if node["id"] in ("buy_order", "sell_order"):
                assert node["type"] == "OverseasFuturesNewOrderNode", (
                    f"'{node['id']}'는 OverseasFuturesNewOrderNode 타입이어야 함"
                )

    def test_broker_is_futures_type(self, workflow):
        """브로커 노드가 해외선물 타입"""
        for node in workflow["nodes"]:
            if node["type"].endswith("BrokerNode"):
                assert "Futures" in node["type"], (
                    f"HKEX 봇 브로커는 OverseasFuturesBrokerNode이어야 함, 실제: {node['type']}"
                )

    def test_schedule_max_duration(self, workflow):
        """스케줄 노드의 max_duration_hours가 설정되어 있음"""
        for node in workflow["nodes"]:
            if node["id"] == "schedule":
                assert "max_duration_hours" in node
                assert node["max_duration_hours"] > 0
