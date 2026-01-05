"""
ProgramGarden - Event Tools

이벤트 히스토리 조회 및 분석 도구
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

# 인메모리 이벤트 저장소 (실제 구현에서는 DB 사용)
_events: List[Dict[str, Any]] = []


def get_events(
    job_id: str,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    이벤트 히스토리 조회

    Args:
        job_id: Job ID
        event_type: 이벤트 유형 필터 (order_filled, condition_passed 등)
        limit: 최대 결과 수

    Returns:
        이벤트 목록

    Example:
        >>> get_events("job-abc123", event_type="order_filled")
        [{"event_id": "evt-001", "type": "order_filled", "data": {...}}, ...]
    """
    result = []

    for event in _events:
        if event.get("job_id") != job_id:
            continue
        if event_type and event.get("type") != event_type:
            continue

        result.append(event)

        if len(result) >= limit:
            break

    return result


def get_job_summary(job_id: str) -> Dict[str, Any]:
    """
    Job 실행 요약 (집계된 통계)

    Args:
        job_id: Job ID

    Returns:
        실행 요약 통계

    Example:
        >>> get_job_summary("job-abc123")
        {
            "total_trades": 10,
            "winning_trades": 7,
            "win_rate": 0.7,
            "total_pnl": 1250.50,
            ...
        }
    """
    from programgarden.tools.job_tools import get_job

    job = get_job(job_id)
    if not job:
        return {}

    stats = job.get("stats", {})

    return {
        "job_id": job_id,
        "workflow_id": job.get("workflow_id"),
        "status": job.get("status"),
        "started_at": job.get("started_at"),
        "runtime_seconds": _calculate_runtime(job),
        "conditions_evaluated": stats.get("conditions_evaluated", 0),
        "orders_placed": stats.get("orders_placed", 0),
        "orders_filled": stats.get("orders_filled", 0),
        "orders_cancelled": stats.get("orders_cancelled", 0),
        "errors_count": stats.get("errors_count", 0),
        # TODO: 실제 트레이딩 통계
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 0.0,
        "total_pnl": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
    }


def analyze_performance(job_id: str) -> Dict[str, Any]:
    """
    성과 분석 리포트 생성

    Args:
        job_id: Job ID

    Returns:
        성과 분석 리포트

    Example:
        >>> analyze_performance("job-abc123")
        {
            "summary": {...},
            "daily_returns": [...],
            "trade_history": [...],
            "risk_metrics": {...}
        }
    """
    summary = get_job_summary(job_id)
    events = get_events(job_id, event_type="order_filled", limit=1000)

    return {
        "job_id": job_id,
        "summary": summary,
        "trade_history": _build_trade_history(events),
        "daily_returns": _calculate_daily_returns(events),
        "risk_metrics": _calculate_risk_metrics(events),
        "analysis": {
            "best_trade": None,
            "worst_trade": None,
            "avg_holding_period": None,
            "most_traded_symbol": None,
        },
    }


def _calculate_runtime(job: Dict[str, Any]) -> Optional[int]:
    """실행 시간 계산 (초)"""
    started = job.get("started_at")
    if not started:
        return None

    if isinstance(started, str):
        started = datetime.fromisoformat(started.replace("Z", "+00:00"))

    completed = job.get("completed_at")
    if completed:
        if isinstance(completed, str):
            completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))
    else:
        completed = datetime.utcnow()

    return int((completed - started).total_seconds())


def _build_trade_history(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """거래 히스토리 생성"""
    # TODO: 실제 거래 히스토리 빌드
    return []


def _calculate_daily_returns(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """일별 수익률 계산"""
    # TODO: 실제 일별 수익률 계산
    return []


def _calculate_risk_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """리스크 메트릭 계산"""
    # TODO: 실제 리스크 메트릭 (Sharpe, Sortino, Max Drawdown 등)
    return {
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "max_drawdown": None,
        "max_drawdown_duration": None,
        "var_95": None,
    }


# === 내부용 이벤트 기록 함수 ===

def _record_event(
    job_id: str,
    event_type: str,
    node_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> str:
    """이벤트 기록 (내부용)"""
    import uuid

    event_id = f"evt-{uuid.uuid4().hex[:8]}"
    event = {
        "event_id": event_id,
        "job_id": job_id,
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        "node_id": node_id,
        "data": data or {},
    }
    _events.append(event)
    return event_id
