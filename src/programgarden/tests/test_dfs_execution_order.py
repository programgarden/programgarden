"""
DFS 실행 순서 검증 테스트

이 테스트는 워크플로우 노드들이 깊이 우선 탐색(DFS) 순서로 실행되는지 검증합니다.

핵심 원칙: "부모 노드(이전 단계)가 데이터를 줘야, 자식 노드(다음 단계)가 일할 수 있다"

NOTE: 이 테스트는 실행 순서만 검증합니다.
      노드 검증을 우회하기 위해 _topological_sort 메서드를 직접 테스트합니다.
"""

from programgarden.resolver import WorkflowResolver, ResolvedNode, ResolvedEdge


def create_resolved_nodes(node_defs: list) -> dict:
    """테스트용 ResolvedNode 딕셔너리 생성"""
    return {
        n["id"]: ResolvedNode(
            node_id=n["id"],
            node_type=n["type"],
            category="test",
            config={},
        )
        for n in node_defs
    }


def create_resolved_edges(edge_defs: list) -> list:
    """테스트용 ResolvedEdge 리스트 생성"""
    return [
        ResolvedEdge(from_node_id=e["from"], to_node_id=e["to"])
        for e in edge_defs
    ]


class TestDFSExecutionOrder:
    """DFS 기반 토폴로지 정렬 테스트"""

    def test_linear_workflow_order(self):
        """선형 워크플로우: A → B → C"""
        nodes = [
            {"id": "a", "type": "StartNode"},
            {"id": "b", "type": "OverseasStockBrokerNode"},
            {"id": "c", "type": "WatchlistNode"},
        ]
        edges = [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "c"},
        ]

        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )

        assert order == ["a", "b", "c"]

    def test_dfs_branching_workflow_order(self):
        """
        분기 워크플로우 (DFS 검증):

        broker ─→ watchlist ─→ condition
              └─→ display

        BFS 결과: broker → watchlist → display → condition
        DFS 결과: broker → watchlist → condition → display
        """
        nodes = [
            {"id": "broker", "type": "StartNode"},
            {"id": "watchlist", "type": "WatchlistNode"},
            {"id": "condition", "type": "ConditionNode"},
            {"id": "display", "type": "DisplayNode"},
        ]
        edges = [
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "condition"},
            {"from": "broker", "to": "display"},
        ]

        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )

        assert order[0] == "broker"
        assert order.index("watchlist") < order.index("condition")
        assert order.index("condition") < order.index("display"), (
            f"DFS에서는 condition이 display보다 먼저 실행되어야 함. 실제 순서: {order}"
        )


class TestParentBeforeChild:
    """부모 노드가 자식보다 먼저 실행되는지 검증 (핵심 원칙)"""

    def test_parent_before_child_data_flow(self):
        """
        부모 노드가 자식보다 먼저 실행되어 데이터를 제공하는지 검증
        
        start → broker → watchlist → historical → condition
        
        이 순서가 깨지면:
        - ConditionNode가 데이터 없이 실행 → 에러
        """
        nodes = [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode"},
            {"id": "watchlist", "type": "WatchlistNode"},
            {"id": "historical", "type": "HistoricalDataNode"},
            {"id": "condition", "type": "ConditionNode"},
        ]
        edges = [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "historical"},
            {"from": "historical", "to": "condition"},
        ]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # 핵심 검증: 각 노드가 의존 노드보다 뒤에 위치
        assert order.index("start") < order.index("broker"), \
            f"start must execute before broker. Order: {order}"
        assert order.index("broker") < order.index("watchlist"), \
            f"broker must execute before watchlist. Order: {order}"
        assert order.index("watchlist") < order.index("historical"), \
            f"watchlist must execute before historical. Order: {order}"
        assert order.index("historical") < order.index("condition"), \
            f"historical must execute before condition. Order: {order}"

    def test_diamond_dependency_pre_order(self):
        """
        다이아몬드 의존성에서 DFS 전위 순회 검증
        
            A
           / \\
          B   C
           \\ /
            D
        
        핵심: D는 반드시 B와 C 모두 실행 후에 실행
        """
        nodes = [
            {"id": "a", "type": "StartNode"},
            {"id": "b", "type": "WatchlistNode"},
            {"id": "c", "type": "DisplayNode"},
            {"id": "d", "type": "ConditionNode"},
        ]
        edges = [
            {"from": "a", "to": "b"},
            {"from": "a", "to": "c"},
            {"from": "b", "to": "d"},
            {"from": "c", "to": "d"},
        ]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # D는 B와 C 모두 뒤에 위치해야 함
        assert order.index("b") < order.index("d"), \
            f"B must execute before D. Order: {order}"
        assert order.index("c") < order.index("d"), \
            f"C must execute before D. Order: {order}"
        assert order.index("a") == 0, \
            f"A must be first (root node). Order: {order}"


class TestComplexWorkflows:
    """깊고 복잡한 워크플로우 테스트"""

    def test_deep_chain_workflow(self):
        """
        깊은 체인 워크플로우 (깊이 8)
        
        start → broker → watchlist → historical → condition → logic → order → display
        
        실제 트레이딩 워크플로우와 유사한 깊은 체인
        """
        nodes = [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode"},
            {"id": "watchlist", "type": "WatchlistNode"},
            {"id": "historical", "type": "HistoricalDataNode"},
            {"id": "condition", "type": "ConditionNode"},
            {"id": "logic", "type": "LogicNode"},
            {"id": "order", "type": "NewOrderNode"},
            {"id": "display", "type": "DisplayNode"},
        ]
        edges = [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "historical"},
            {"from": "historical", "to": "condition"},
            {"from": "condition", "to": "logic"},
            {"from": "logic", "to": "order"},
            {"from": "order", "to": "display"},
        ]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # 정확한 순서 검증 (체인이므로 순서가 고정)
        expected = ["start", "broker", "watchlist", "historical", "condition", "logic", "order", "display"]
        assert order == expected, f"Expected {expected}, got {order}"

    def test_multi_branch_deep_workflow(self):
        """
        다중 분기 + 깊은 워크플로우
        
                    start
                      │
                   broker
                   /    \\
            watchlist   account
                │          │
           historical   positions
                │          │
              rsi      profitTarget
                \\        /
                 \\      /
                  logic
                    │
                  order
                    │
                 display
        
        핵심: logic은 rsi와 profitTarget 모두 실행 후에 실행
        """
        nodes = [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode"},
            {"id": "watchlist", "type": "WatchlistNode"},
            {"id": "account", "type": "DisplayNode"},
            {"id": "historical", "type": "HistoricalDataNode"},
            {"id": "positions", "type": "DisplayNode"},
            {"id": "rsi", "type": "ConditionNode"},
            {"id": "profitTarget", "type": "ConditionNode"},
            {"id": "logic", "type": "LogicNode"},
            {"id": "order", "type": "NewOrderNode"},
            {"id": "display", "type": "DisplayNode"},
        ]
        edges = [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "broker", "to": "account"},
            {"from": "watchlist", "to": "historical"},
            {"from": "account", "to": "positions"},
            {"from": "historical", "to": "rsi"},
            {"from": "positions", "to": "profitTarget"},
            {"from": "rsi", "to": "logic"},
            {"from": "profitTarget", "to": "logic"},
            {"from": "logic", "to": "order"},
            {"from": "order", "to": "display"},
        ]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # 의존성 검증
        assert order.index("start") == 0
        assert order.index("start") < order.index("broker")
        assert order.index("broker") < order.index("watchlist")
        assert order.index("broker") < order.index("account")
        assert order.index("watchlist") < order.index("historical")
        assert order.index("account") < order.index("positions")
        assert order.index("historical") < order.index("rsi")
        assert order.index("positions") < order.index("profitTarget")
        
        # 핵심: logic은 rsi와 profitTarget 모두 뒤에
        assert order.index("rsi") < order.index("logic"), \
            f"rsi must execute before logic. Order: {order}"
        assert order.index("profitTarget") < order.index("logic"), \
            f"profitTarget must execute before logic. Order: {order}"
        
        # logic → order → display 순서
        assert order.index("logic") < order.index("order")
        assert order.index("order") < order.index("display")

    def test_triple_merge_workflow(self):
        """
        세 개의 경로가 하나로 합쳐지는 워크플로우
        
             start
            /  |  \\
           A   B   C
            \\  |  /
             merge
               │
             end
        
        핵심: merge는 A, B, C 모두 실행 후에 실행
        """
        nodes = [
            {"id": "start", "type": "StartNode"},
            {"id": "a", "type": "WatchlistNode"},
            {"id": "b", "type": "DisplayNode"},
            {"id": "c", "type": "HistoricalDataNode"},
            {"id": "merge", "type": "LogicNode"},
            {"id": "end", "type": "DisplayNode"},
        ]
        edges = [
            {"from": "start", "to": "a"},
            {"from": "start", "to": "b"},
            {"from": "start", "to": "c"},
            {"from": "a", "to": "merge"},
            {"from": "b", "to": "merge"},
            {"from": "c", "to": "merge"},
            {"from": "merge", "to": "end"},
        ]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # start가 첫 번째
        assert order.index("start") == 0
        
        # A, B, C 모두 merge보다 먼저
        assert order.index("a") < order.index("merge"), \
            f"a must execute before merge. Order: {order}"
        assert order.index("b") < order.index("merge"), \
            f"b must execute before merge. Order: {order}"
        assert order.index("c") < order.index("merge"), \
            f"c must execute before merge. Order: {order}"
        
        # merge → end
        assert order.index("merge") < order.index("end")

    def test_parallel_chains_workflow(self):
        """
        병렬 체인 워크플로우
        
            start
              │
           broker
           /    \\
        chain1  chain2
          │       │
        cond1   cond2
          │       │
        order1  order2
           \\    /
          summary
        
        두 개의 독립적인 전략이 병렬로 실행되고 마지막에 합쳐짐
        """
        nodes = [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode"},
            {"id": "chain1", "type": "WatchlistNode"},
            {"id": "chain2", "type": "WatchlistNode"},
            {"id": "cond1", "type": "ConditionNode"},
            {"id": "cond2", "type": "ConditionNode"},
            {"id": "order1", "type": "NewOrderNode"},
            {"id": "order2", "type": "NewOrderNode"},
            {"id": "summary", "type": "DisplayNode"},
        ]
        edges = [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "chain1"},
            {"from": "broker", "to": "chain2"},
            {"from": "chain1", "to": "cond1"},
            {"from": "chain2", "to": "cond2"},
            {"from": "cond1", "to": "order1"},
            {"from": "cond2", "to": "order2"},
            {"from": "order1", "to": "summary"},
            {"from": "order2", "to": "summary"},
        ]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # 기본 순서
        assert order.index("start") == 0
        assert order.index("start") < order.index("broker")
        
        # 체인1 의존성
        assert order.index("broker") < order.index("chain1")
        assert order.index("chain1") < order.index("cond1")
        assert order.index("cond1") < order.index("order1")
        
        # 체인2 의존성
        assert order.index("broker") < order.index("chain2")
        assert order.index("chain2") < order.index("cond2")
        assert order.index("cond2") < order.index("order2")
        
        # summary는 두 order 모두 뒤에
        assert order.index("order1") < order.index("summary"), \
            f"order1 must execute before summary. Order: {order}"
        assert order.index("order2") < order.index("summary"), \
            f"order2 must execute before summary. Order: {order}"

    def test_complex_real_trading_workflow(self):
        """
        실제 트레이딩과 유사한 복잡한 워크플로우
        
                        start
                          │
                       broker
                      /   |   \\
               watchlist market schedule
                  │       │       │
             historical positions tradingHours
                  │       │       │
                 rsi   stopLoss    │
                  │       │       /
                  └───logic───────
                        │
                    riskGuard
                        │
                      order
                        │
                     display
        
        - 3개의 데이터 소스 (시세, 계좌, 스케줄)
        - 2개의 조건 (RSI, StopLoss)
        - 리스크 관리 노드
        """
        nodes = [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode"},
            {"id": "watchlist", "type": "WatchlistNode"},
            {"id": "market", "type": "DisplayNode"},
            {"id": "schedule", "type": "ScheduleNode"},
            {"id": "historical", "type": "HistoricalDataNode"},
            {"id": "positions", "type": "DisplayNode"},
            {"id": "tradingHours", "type": "TradingHoursFilterNode"},
            {"id": "rsi", "type": "ConditionNode"},
            {"id": "stopLoss", "type": "ConditionNode"},
            {"id": "logic", "type": "LogicNode"},
            {"id": "sizing", "type": "PositionSizingNode"},
            {"id": "order", "type": "NewOrderNode"},
            {"id": "display", "type": "DisplayNode"},
        ]
        edges = [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "broker", "to": "market"},
            {"from": "broker", "to": "schedule"},
            {"from": "watchlist", "to": "historical"},
            {"from": "market", "to": "positions"},
            {"from": "schedule", "to": "tradingHours"},
            {"from": "historical", "to": "rsi"},
            {"from": "positions", "to": "stopLoss"},
            {"from": "rsi", "to": "logic"},
            {"from": "stopLoss", "to": "logic"},
            {"from": "tradingHours", "to": "logic"},
            {"from": "logic", "to": "sizing"},
            {"from": "sizing", "to": "order"},
            {"from": "order", "to": "display"},
        ]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # 루트 검증
        assert order.index("start") == 0
        
        # 3개 브랜치 모두 broker 뒤에
        assert order.index("broker") < order.index("watchlist")
        assert order.index("broker") < order.index("market")
        assert order.index("broker") < order.index("schedule")
        
        # 각 브랜치 내부 순서
        assert order.index("watchlist") < order.index("historical")
        assert order.index("historical") < order.index("rsi")
        
        assert order.index("market") < order.index("positions")
        assert order.index("positions") < order.index("stopLoss")
        
        assert order.index("schedule") < order.index("tradingHours")
        
        # 핵심: logic은 세 조건 모두 뒤에
        assert order.index("rsi") < order.index("logic"), \
            f"rsi must execute before logic. Order: {order}"
        assert order.index("stopLoss") < order.index("logic"), \
            f"stopLoss must execute before logic. Order: {order}"
        assert order.index("tradingHours") < order.index("logic"), \
            f"tradingHours must execute before logic. Order: {order}"
        
        # 최종 체인
        assert order.index("logic") < order.index("sizing")
        assert order.index("sizing") < order.index("order")
        assert order.index("order") < order.index("display")

    def test_very_deep_workflow_depth_10(self):
        """
        매우 깊은 워크플로우 (깊이 10)
        
        n1 → n2 → n3 → n4 → n5 → n6 → n7 → n8 → n9 → n10
        
        깊이가 깊어도 DFS 전위 순회가 올바르게 동작하는지 검증
        """
        nodes = [{"id": f"n{i}", "type": "DisplayNode"} for i in range(1, 11)]
        nodes[0]["type"] = "StartNode"  # 첫 번째는 StartNode
        
        edges = [{"from": f"n{i}", "to": f"n{i+1}"} for i in range(1, 10)]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # 정확한 순서 검증
        expected = [f"n{i}" for i in range(1, 11)]
        assert order == expected, f"Expected {expected}, got {order}"

    def test_wide_workflow_many_branches(self):
        """
        넓은 워크플로우 (분기 10개)
        
               start
           /  /  |  \\  \\
          b1 b2 b3 ... b10
           \\  \\  |  /  /
              merge
        
        많은 분기가 있어도 DFS 전위 순회가 올바르게 동작하는지 검증
        """
        branch_count = 10
        
        nodes = [{"id": "start", "type": "StartNode"}]
        nodes += [{"id": f"b{i}", "type": "DisplayNode"} for i in range(1, branch_count + 1)]
        nodes.append({"id": "merge", "type": "LogicNode"})
        
        edges = [{"from": "start", "to": f"b{i}"} for i in range(1, branch_count + 1)]
        edges += [{"from": f"b{i}", "to": "merge"} for i in range(1, branch_count + 1)]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # start가 첫 번째
        assert order.index("start") == 0
        
        # 모든 분기가 merge보다 먼저
        for i in range(1, branch_count + 1):
            assert order.index(f"b{i}") < order.index("merge"), \
                f"b{i} must execute before merge. Order: {order}"

    def test_complex_diamond_with_multiple_merges(self):
        """
        복잡한 다이아몬드 + 다중 합류점
        
                start
                  │
                  A
                 / \\
                B   C
               / \\ / \\
              D   E   F
               \\ | /
                merge1
                  │
                  G
                 / \\
                H   I
                 \\ /
               merge2
        
        다중 합류점에서도 DFS 전위 순회가 올바르게 동작하는지 검증
        """
        nodes = [
            {"id": "start", "type": "StartNode"},
            {"id": "a", "type": "OverseasStockBrokerNode"},
            {"id": "b", "type": "WatchlistNode"},
            {"id": "c", "type": "WatchlistNode"},
            {"id": "d", "type": "DisplayNode"},
            {"id": "e", "type": "DisplayNode"},
            {"id": "f", "type": "DisplayNode"},
            {"id": "merge1", "type": "LogicNode"},
            {"id": "g", "type": "DisplayNode"},
            {"id": "h", "type": "DisplayNode"},
            {"id": "i", "type": "DisplayNode"},
            {"id": "merge2", "type": "DisplayNode"},
        ]
        edges = [
            {"from": "start", "to": "a"},
            {"from": "a", "to": "b"},
            {"from": "a", "to": "c"},
            {"from": "b", "to": "d"},
            {"from": "b", "to": "e"},
            {"from": "c", "to": "e"},
            {"from": "c", "to": "f"},
            {"from": "d", "to": "merge1"},
            {"from": "e", "to": "merge1"},
            {"from": "f", "to": "merge1"},
            {"from": "merge1", "to": "g"},
            {"from": "g", "to": "h"},
            {"from": "g", "to": "i"},
            {"from": "h", "to": "merge2"},
            {"from": "i", "to": "merge2"},
        ]
        
        resolver = WorkflowResolver()
        order = resolver._topological_sort(
            create_resolved_nodes(nodes),
            create_resolved_edges(edges),
        )
        
        # 의존성 검증
        assert order.index("start") == 0
        assert order.index("start") < order.index("a")
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        
        # D, E, F 모두 merge1보다 먼저
        assert order.index("d") < order.index("merge1")
        assert order.index("e") < order.index("merge1")
        assert order.index("f") < order.index("merge1")
        
        # merge1 → G → H, I → merge2
        assert order.index("merge1") < order.index("g")
        assert order.index("g") < order.index("h")
        assert order.index("g") < order.index("i")
        assert order.index("h") < order.index("merge2")
        assert order.index("i") < order.index("merge2")


class TestDFSDocstringConsistency:
    """DFS 관련 docstring이 올바르게 작성되었는지 검증"""

    def test_topological_sort_docstring(self):
        """_topological_sort 함수의 docstring이 DFS를 설명하는지 확인"""
        docstring = WorkflowResolver._topological_sort.__doc__
        assert docstring is not None
        assert "DFS" in docstring or "depth-first" in docstring.lower(), (
            "_topological_sort docstring에 DFS 설명이 없습니다"
        )
