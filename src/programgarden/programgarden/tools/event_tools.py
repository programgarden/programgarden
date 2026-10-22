"""
ProgramGarden - Event Tools

Event history query and analysis tools
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

# In-memory event storage (use DB in actual implementation)
_events: List[Dict[str, Any]] = []


def get_events(
    job_id: str,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get event history

    Args:
        job_id: Job ID
        event_type: Event type filter (order_filled, condition_passed, etc.)
        limit: Maximum number of results

    Returns:
        List of events

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
    Get Job execution summary (aggregated statistics)

    Args:
        job_id: Job ID

    Returns:
        Execution summary statistics

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
        # TODO: Actual trading statistics
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
    Generate performance analysis report

    Args:
        job_id: Job ID

    Returns:
        Performance analysis report

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
    """Calculate runtime (seconds)"""
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
    """Build trade history"""
    # TODO: Implement actual trade history build
    return []


def _calculate_daily_returns(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate daily returns"""
    # TODO: Implement actual daily returns calculation
    return []


def _calculate_risk_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate risk metrics"""
    # TODO: Implement actual risk metrics (Sharpe, Sortino, Max Drawdown, etc.)
    return {
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "max_drawdown": None,
        "max_drawdown_duration": None,
        "var_95": None,
    }


# === Internal event recording functions ===

def _record_event(
    job_id: str,
    event_type: str,
    node_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> str:
    """Record event (internal use)"""
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
