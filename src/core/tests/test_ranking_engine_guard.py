"""Ranking node classes fail closed when an engine without the ranking executor runs them.

The programgarden engine executes KoreaStockRankingNode and OverseasStockRankingNode
with its own executor from 2.6.6. An older engine paired with this core falls back to
its generic executor, which calls the node's execute(); the classes raise a clear
engine-version error there instead of reporting success with no rankings.
"""

import asyncio

import pytest

from programgarden_core.nodes.ranking_korea_stock import (
    RANKING_MIN_ENGINE,
    KoreaStockRankingNode,
    ranking_engine_required,
)
from programgarden_core.nodes.ranking_stock import OverseasStockRankingNode


def test_minimum_engine_is_2_6_6():
    assert RANKING_MIN_ENGINE == "2.6.6"


@pytest.mark.parametrize("cls", [KoreaStockRankingNode, OverseasStockRankingNode])
def test_execute_raises_engine_version_error(cls):
    node = cls(id="ranking")
    with pytest.raises(RuntimeError) as raised:
        asyncio.run(node.execute(None))
    message = str(raised.value)
    assert message.startswith(f"{cls.__name__} requires the programgarden engine 2.6.6 or later")
    assert "no ranking was read" in message


def test_error_names_the_node_type():
    assert str(ranking_engine_required("X")).startswith("X requires the programgarden engine 2.6.6")
