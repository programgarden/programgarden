"""Stateful reservation setup is executed, never simulated as an empty write."""
import pytest
from programgarden.incremental_build import BuildWorkspace
from programgarden.validation_replay import replay


def sql(node_id, query, db_name="reservations.db"):
    return {"id":node_id,"type":"SQLiteNode","db_name":db_name,
            "operation":"execute_query","query":query}


def graph(*nodes):
    nodes=[{"id":"start","type":"StartNode"},*nodes]
    return {"id":"reservation","name":"Reservation", "nodes":nodes,
            "edges":[{"from":a["id"],"to":b["id"]} for a,b in zip(nodes,nodes[1:])]}


@pytest.mark.asyncio
async def test_node_checks_preserve_setup_state_and_each_chain_starts_fresh():
    ws=BuildWorkspace("reservation-task",1,{"id":"reservation","name":"Reservation","nodes":[],"edges":[]},[{"expected":{"check":{
        "type":"object","required":["rows"],"properties":{"rows":{"type":"array","const":[{"count":1}]}}}}}])
    for node in [
        {"id":"start","type":"StartNode"},
        sql("create","CREATE TABLE reservations (symbol TEXT PRIMARY KEY)"),
        sql("reserve","INSERT INTO reservations VALUES ('NASDAQ:AAPL')"),
        sql("duplicate","INSERT OR IGNORE INTO reservations VALUES ('NASDAQ:AAPL')"),
        sql("check","SELECT COUNT(*) AS count FROM reservations"),
    ]:
        previous=list(ws.states)[-1] if ws.states else None
        ws.add_node(node,[] if previous is None else [{"from":previous,"to":node["id"]}],expected_revision=ws.revision)
        evidence=await ws.run_pending(node["id"],expected_revision=ws.revision)
        assert evidence["passed"],evidence["errors"]
        standalone,chain=evidence["runs"]
        assert standalone["executed"]==[node["id"]]
        assert chain["executed"]==list(ws.states)
    assert standalone["outputs"]["check"]["rows"]==[{"count":1}]
    assert chain["outputs"]["duplicate"]["affected_count"]==0
    final=await ws.finalize(expected_revision=ws.revision)
    assert final["passed"],final


@pytest.mark.asyncio
@pytest.mark.parametrize("query,name",[
    ("SELECT 1","../escape.db"),
    ("SELECT 1","/tmp/escape.db"),
    ("ATTACH DATABASE '/tmp/escape.db' AS escaped","state.db"),
    ("PRAGMA writable_schema=1","state.db"),
    ("SELECT load_extension('/tmp/plugin.so')","state.db"),
])
async def test_sql_cannot_escape_its_disposable_database(query,name):
    result=await replay(graph(sql("unsafe",query,name)),{})
    assert not result.passed and result.errors


@pytest.mark.asyncio
async def test_uninitialized_reservation_fails_instead_of_becoming_a_fake_empty_write():
    result=await replay(graph(sql("reserve","INSERT INTO absent VALUES ('AAPL')")),{})
    assert not result.passed and "reserve" in result.executed
