from programgarden_core.expression.evaluator import ExpressionContext, ExpressionEvaluator


def _evaluator():
    ctx = ExpressionContext(node_outputs={
        "open_orders": {"open_orders": [{"symbol": "PLUG", "order_id": "300"}], "count": 1},
        "stats": {"sum": 12.5, "first": "a", "last": "z", "map": {"k": 1}, "filter": [1, 2]},
    })
    return ExpressionEvaluator(ctx)


def test_output_port_named_count_wins_over_the_proxy_helper():
    assert _evaluator().evaluate("{{ nodes.open_orders.count }}") == 1


def test_helper_methods_still_work_on_list_ports():
    assert _evaluator().evaluate("{{ nodes.open_orders.open_orders.count() }}") == 1
    assert _evaluator().evaluate("{{ nodes.open_orders.open_orders.first().symbol }}") == "PLUG"


def test_every_helper_name_used_as_a_port_resolves_to_the_port():
    ev = _evaluator()
    assert ev.evaluate("{{ nodes.stats.sum }}") == 12.5
    assert ev.evaluate("{{ nodes.stats.first }}") == "a"
    assert ev.evaluate("{{ nodes.stats.last }}") == "z"
    assert ev.evaluate("{{ nodes.stats.map.k }}") == 1
    assert list(ev.evaluate("{{ nodes.stats.filter }}")) == [1, 2]


def test_resolved_port_values_are_json_serializable():
    import json
    value = _evaluator().evaluate("{{ nodes.open_orders.count }}")
    assert json.dumps({"open_count": value}) == '{"open_count": 1}'
