"""
Test DAG-based ancestor propagation in ExecutionContext.

Tests for find_parent_outputs() and find_parent_output() methods
which enable BrokerNode information propagation through the DAG.
"""

import pytest
from programgarden.context import ExecutionContext


class TestFindParentOutputs:
    """Tests for find_parent_outputs() - returns all ancestors"""

    def test_direct_connection(self):
        """Direct connection: BrokerNode → WatchlistNode"""
        edges = [{"from": "broker", "to": "watchlist"}]
        nodes = {
            "broker": {"type": "BrokerNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        # Set BrokerNode output
        ctx.set_output("broker", "product", "overseas_stock")
        ctx.set_output("broker", "company", "ls")
        
        # Find ancestor BrokerNode from WatchlistNode
        results = ctx.find_parent_outputs("watchlist", "BrokerNode")
        
        assert len(results) == 1
        node_id, distance, outputs = results[0]
        assert node_id == "broker"
        assert distance == 1
        assert outputs.get("product") == "overseas_stock"
        assert outputs.get("company") == "ls"

    def test_indirect_connection(self):
        """Indirect connection: BrokerNode → ScheduleNode → WatchlistNode"""
        edges = [
            {"from": "broker", "to": "schedule"},
            {"from": "schedule", "to": "watchlist"},
        ]
        nodes = {
            "broker": {"type": "BrokerNode"},
            "schedule": {"type": "ScheduleNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        ctx.set_output("broker", "product", "overseas_futures")
        
        # Should find BrokerNode through ScheduleNode
        results = ctx.find_parent_outputs("watchlist", "BrokerNode")
        
        assert len(results) == 1
        node_id, distance, outputs = results[0]
        assert node_id == "broker"
        assert distance == 2  # Through schedule
        assert outputs.get("product") == "overseas_futures"

    def test_multiple_brokers_same_distance(self):
        """Multiple brokers at same distance: return all"""
        #   [broker_us]    [broker_kr]
        #        ↓              ↓
        #        └──────┬───────┘
        #               ↓
        #           [merge]
        #               ↓
        #         [watchlist]
        edges = [
            {"from": "broker_us", "to": "merge"},
            {"from": "broker_kr", "to": "merge"},
            {"from": "merge", "to": "watchlist"},
        ]
        nodes = {
            "broker_us": {"type": "BrokerNode"},
            "broker_kr": {"type": "BrokerNode"},
            "merge": {"type": "LogicNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        ctx.set_output("broker_us", "product", "overseas_stock")
        ctx.set_output("broker_us", "company", "ls")
        ctx.set_output("broker_kr", "product", "domestic_stock")
        ctx.set_output("broker_kr", "company", "ls")
        
        # Should return both brokers at same distance
        results = ctx.find_parent_outputs("watchlist", "BrokerNode")
        
        assert len(results) == 2
        # Both at distance 2
        assert all(dist == 2 for _, dist, _ in results)
        # Both brokers included
        broker_ids = {r[0] for r in results}
        assert broker_ids == {"broker_us", "broker_kr"}

    def test_multiple_brokers_different_distance(self):
        """Brokers at different distances: sorted by distance"""
        #     broker_far → schedule → broker_near → watchlist
        edges = [
            {"from": "broker_far", "to": "schedule"},
            {"from": "schedule", "to": "broker_near"},
            {"from": "broker_near", "to": "watchlist"},
        ]
        nodes = {
            "broker_far": {"type": "BrokerNode"},
            "schedule": {"type": "ScheduleNode"},
            "broker_near": {"type": "BrokerNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        ctx.set_output("broker_far", "product", "domestic_stock")
        ctx.set_output("broker_near", "product", "overseas_stock")
        
        # Should return sorted by distance
        results = ctx.find_parent_outputs("watchlist", "BrokerNode")
        
        assert len(results) == 2
        # Nearest first
        assert results[0][0] == "broker_near"
        assert results[0][1] == 1
        assert results[0][2].get("product") == "overseas_stock"
        # Farther second
        assert results[1][0] == "broker_far"
        assert results[1][1] == 3
        assert results[1][2].get("product") == "domestic_stock"

    def test_no_broker_returns_empty_list(self):
        """No BrokerNode in ancestors"""
        edges = [{"from": "start", "to": "watchlist"}]
        nodes = {
            "start": {"type": "StartNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        results = ctx.find_parent_outputs("watchlist", "BrokerNode")
        
        assert results == []

    def test_broker_without_output_not_included(self):
        """BrokerNode exists but has no output set"""
        edges = [{"from": "broker", "to": "watchlist"}]
        nodes = {
            "broker": {"type": "BrokerNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        # Don't set any output for broker
        results = ctx.find_parent_outputs("watchlist", "BrokerNode")
        
        # Should return empty because no outputs
        assert results == []

    def test_fallback_when_no_dag_info(self):
        """Fallback to legacy method when no DAG info"""
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            # No workflow_edges, workflow_nodes
        )
        
        ctx.set_output("broker", "product", "overseas_stock")
        
        # Should use legacy get_upstream_output fallback
        results = ctx.find_parent_outputs("watchlist", "BrokerNode")
        
        assert len(results) == 1
        assert results[0][0] == "unknown"  # Node ID unknown in fallback
        assert results[0][2].get("product") == "overseas_stock"

    def test_complex_dag_with_multiple_paths(self):
        """Complex DAG with multiple paths to same BrokerNode"""
        #          [broker]
        #          ↓      ↓
        #     [path_a]  [path_b]
        #          ↓      ↓
        #          └──────┘
        #              ↓
        #         [watchlist]
        edges = [
            {"from": "broker", "to": "path_a"},
            {"from": "broker", "to": "path_b"},
            {"from": "path_a", "to": "watchlist"},
            {"from": "path_b", "to": "watchlist"},
        ]
        nodes = {
            "broker": {"type": "BrokerNode"},
            "path_a": {"type": "ConditionNode"},
            "path_b": {"type": "ConditionNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        ctx.set_output("broker", "product", "overseas_stock")
        
        # Should find broker only once (visited tracking)
        results = ctx.find_parent_outputs("watchlist", "BrokerNode")
        
        assert len(results) == 1
        assert results[0][0] == "broker"
        assert results[0][1] == 2


class TestFindParentOutput:
    """Tests for find_parent_output() - convenience method returning closest"""

    def test_returns_closest_broker(self):
        """Returns closest BrokerNode output"""
        edges = [
            {"from": "broker_far", "to": "broker_near"},
            {"from": "broker_near", "to": "watchlist"},
        ]
        nodes = {
            "broker_far": {"type": "BrokerNode"},
            "broker_near": {"type": "BrokerNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        ctx.set_output("broker_far", "product", "domestic_stock")
        ctx.set_output("broker_near", "product", "overseas_stock")
        
        # Convenience method returns only the closest one
        result = ctx.find_parent_output("watchlist", "BrokerNode")
        
        assert result is not None
        assert result.get("product") == "overseas_stock"

    def test_returns_none_when_not_found(self):
        """Returns None when no matching ancestor"""
        edges = [{"from": "start", "to": "watchlist"}]
        nodes = {
            "start": {"type": "StartNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        result = ctx.find_parent_output("watchlist", "BrokerNode")
        
        assert result is None

    def test_returns_first_when_same_distance(self):
        """Returns first broker when multiple at same distance"""
        edges = [
            {"from": "broker_a", "to": "watchlist"},
            {"from": "broker_b", "to": "watchlist"},
        ]
        nodes = {
            "broker_a": {"type": "BrokerNode"},
            "broker_b": {"type": "BrokerNode"},
            "watchlist": {"type": "WatchlistNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        ctx.set_output("broker_a", "product", "product_a")
        ctx.set_output("broker_b", "product", "product_b")
        
        # Returns one of them (deterministic based on order)
        result = ctx.find_parent_output("watchlist", "BrokerNode")
        
        assert result is not None
        assert result.get("product") in ["product_a", "product_b"]


class TestDagIndexBuilding:
    """Tests for _build_dag_index() method"""

    def test_handles_resolved_edge_objects(self):
        """Works with ResolvedEdge-like objects"""
        class MockResolvedEdge:
            def __init__(self, from_id: str, to_id: str):
                self.from_node_id = from_id
                self.to_node_id = to_id
        
        class MockResolvedNode:
            def __init__(self, node_type: str):
                self.node_type = node_type
        
        edges = [MockResolvedEdge("broker", "watchlist")]
        nodes = {
            "broker": MockResolvedNode("BrokerNode"),
            "watchlist": MockResolvedNode("WatchlistNode"),
        }
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        # Verify DAG index is built correctly
        assert "watchlist" in ctx._reverse_adj
        assert "broker" in ctx._reverse_adj["watchlist"]
        assert ctx._node_types.get("broker") == "BrokerNode"

    def test_handles_dict_edges(self):
        """Works with dict edges using 'from'/'to' keys"""
        edges = [{"from": "broker", "to": "watchlist"}]
        nodes = {"broker": {"type": "BrokerNode"}}
        
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        assert "watchlist" in ctx._reverse_adj
        assert "broker" in ctx._reverse_adj["watchlist"]

    def test_handles_none_edges(self):
        """Works when edges is None"""
        ctx = ExecutionContext(
            job_id="test",
            workflow_id="test",
            workflow_edges=None,
            workflow_nodes=None,
        )
        
        assert ctx._reverse_adj == {}
        assert ctx._node_types == {}
