"""하드 실패 경로는 조용히 완주하지 않고 시끄럽게(raise → node/job failed) 실패한다.

배경(sweep 리워크): 노드의 하드 실패(자격증명·설정 오류·API·리소스·필수입력 부재 등)를
`{"...port": None, "error": ...}` 에러-dict 로 돌려주면, 하류가 침묵의 None 을 먹고
워크플로우가 `completed` 로 굴러 silent garbage 를 낸다(deep_validate 의 sole-error
승격 안전망도 키가 여럿이면 발동 안 함). 그래서 하드 실패는 **raise** 로 전환했다.

이 스위트는 **실제 에러 경로**(executor 를 patch 하지 않고 실 ExecutionContext 로 구동)로
'하드 실패 = 시끄럽다' 와 '정상 0건 = 스키마 지킨 조용한 빈 값' 을 동시에 못박는다.
"""
import asyncio
import os

import pytest

from programgarden import ProgramGarden
from programgarden.executor import (
    ExecutionContext,
    BrokerNodeExecutor,
    AIAgentNodeExecutor,
    ConditionNodeExecutor,
)
from programgarden_core.exceptions import ValidationError, ExecutionError


def _ctx(tmp_path):
    return ExecutionContext(job_id="j", workflow_id="w", storage_dir=str(tmp_path))


# ── 1. executor 레벨: 하드 실패는 raise (에러-dict 반환 아님) ──────────────────

@pytest.mark.asyncio
async def test_broker_paper_trading_raises(tmp_path):
    """overseas_stock + paper_trading 은 지원 안 됨 → 조용한 에러-dict 아니라 raise."""
    with pytest.raises(ValidationError) as ei:
        await BrokerNodeExecutor().execute(
            "broker", "OverseasStockBrokerNode",
            {"paper_trading": True, "product": "overseas_stock", "credential_id": "c"},
            _ctx(tmp_path),
        )
    assert "paper_trading" in str(ei.value)


@pytest.mark.asyncio
async def test_aiagent_no_llm_model_raises(tmp_path):
    """AIAgentNode 에 LLM 모델 미연결(설정 오류) → raise."""
    with pytest.raises(ValidationError) as ei:
        # workflow kwarg 없음 = ai_model 엣지/워크플로우 컨텍스트 부재
        await AIAgentNodeExecutor().execute(
            "agent", "AIAgentNode", {"user_prompt": "hi"}, _ctx(tmp_path),
        )
    # no-workflow 또는 no-LLM-model — 어느 쪽이든 설정 오류로 raise 되어야 한다
    assert "workflow" in str(ei.value).lower() or "llm" in str(ei.value).lower()


@pytest.mark.asyncio
async def test_condition_missing_items_raises(tmp_path):
    """지표 플러그인 ConditionNode 에 items 미배선(필수입력 부재) → raise."""
    with pytest.raises(ValidationError) as ei:
        await ConditionNodeExecutor().execute(
            "cond", "ConditionNode", {"plugin": "RSI", "fields": {"period": 14}},
            _ctx(tmp_path),
        )
    assert "items" in str(ei.value)


# ── 2. 정상 0건은 raise 하지 않고 선언 스키마 그대로 빈 값 ───────────────────

@pytest.mark.asyncio
async def test_condition_empty_positions_is_normal_zero(tmp_path):
    """포지션 플러그인인데 positions 가 빈 리스트(무보유) = 정상 0건 → raise 안 함.

    (positions 바인딩 자체가 없는 config 오류는 static validate 가 잡는다.)
    """
    out = await ConditionNodeExecutor().execute(
        "cond", "ConditionNode",
        {"plugin": "StopLoss", "positions": [], "fields": {"stop_loss_pct": 5}},
        _ctx(tmp_path),
    )
    assert isinstance(out, dict)
    assert out.get("is_condition_met") is False
    assert out.get("passed_symbols") == []
    # 정상 0건이므로 error 키가 없어야 한다(하드 실패로 위장 금지)
    assert "error" not in out


# ── 3. 엔진 레벨: 하드 실패 노드는 job 을 failed 로 만든다(조용히 completed 아님) ─

def test_hard_failure_fails_the_job(tmp_path):
    """실 엔진 실행: Broker paper-trading 하드 실패 → job status=failed + 사유 노출."""
    dsl = {
        "id": "hardfail", "name": "hardfail", "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode",
             "paper_trading": True, "credential_id": "c"},
        ],
        "edges": [{"from": "start", "to": "broker"}],
        "credentials": [{
            "credential_id": "c", "type": "broker_ls_overseas_stock",
            "data": [
                {"key": "appkey", "value": "x", "type": "password", "label": "k"},
                {"key": "appsecret", "value": "y", "type": "password", "label": "s"},
            ],
        }],
    }
    res = ProgramGarden().run(dsl, storage_dir=str(tmp_path), wait=True, timeout=60)
    assert res.get("status") == "failed"
    assert res.get("stats", {}).get("errors_count", 0) >= 1
    assert "paper_trading" in str(res.get("stats", {}).get("last_error", ""))
