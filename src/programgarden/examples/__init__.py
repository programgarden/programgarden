"""
ProgramGarden Examples - Node-Based DSL

워크플로우 예제 목록 (계획서 Phase 4)

Note: 숫자로 시작하는 파일은 직접 import 불가능하므로, 
동적 import 또는 get_example() 함수를 통해 로드합니다.
"""

from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING
import importlib.util

if TYPE_CHECKING:
    from programgarden_core.models import WorkflowDefinition


# 예제 목록 (lazy loading)
# format: (파일명, 변수명)
EXAMPLE_FILES = {
    "01_start_only": ("01_start_only.py", "START_ONLY"),
    "02_start_schedule": ("02_start_schedule.py", "START_SCHEDULE"),
    "03_start_schedule_trading_hours": ("03_start_schedule_trading_hours.py", "START_SCHEDULE_TRADING_HOURS"),
    "04_broker_connection": ("04_broker_connection.py", "BROKER_CONNECTION"),
    "05_watchlist_realmarket": ("05_watchlist_realmarket.py", "WATCHLIST_REALMARKET"),
    "06_single_condition": ("06_single_condition.py", "SINGLE_CONDITION"),
    "07_multi_condition": ("07_multi_condition.py", "MULTI_CONDITION"),
    "08_weighted_condition": ("08_weighted_condition.py", "WEIGHTED_CONDITION"),
    "09_at_least_condition": ("09_at_least_condition.py", "AT_LEAST_CONDITION"),
    "10_nested_logic": ("10_nested_logic.py", "NESTED_LOGIC"),
    "11_market_order": ("11_market_order.py", "MARKET_ORDER"),
    "12_limit_order": ("12_limit_order.py", "LIMIT_ORDER"),
    "13_position_sizing": ("13_position_sizing.py", "POSITION_SIZING"),
    "14_modify_order": ("14_modify_order.py", "MODIFY_ORDER"),
    "15_cancel_order": ("15_cancel_order.py", "CANCEL_ORDER"),
    "16_buy_sell_basic": ("16_buy_sell_basic.py", "BUY_SELL_BASIC"),
    "17_screener_to_order": ("17_screener_to_order.py", "SCREENER_TO_ORDER"),
    "18_event_handler": ("18_event_handler.py", "EVENT_HANDLER"),
    "19_error_handler": ("19_error_handler.py", "ERROR_HANDLER"),
    "20_risk_guard": ("20_risk_guard.py", "RISK_GUARD"),
    "21_group_node": ("21_group_node.py", "GROUP_NODE"),
    "22_trading_hours": ("22_trading_hours.py", "TRADING_HOURS"),
    "23_pause_resume": ("23_pause_resume.py", "PAUSE_RESUME"),
    "24_state_snapshot": ("24_state_snapshot.py", "STATE_SNAPSHOT"),
    "25_multi_market": ("25_multi_market.py", "MULTI_MARKET"),
    "26_long_running": ("26_long_running.py", "LONG_RUNNING"),
    "27_24h_full_autonomous": ("27_24h_full_autonomous.py", "FULL_AUTONOMOUS_24H"),
    "28_backtest_simple": ("28_backtest_simple.py", "BACKTEST_SIMPLE"),
    "29_backtest_with_deploy": ("29_backtest_with_deploy.py", "BACKTEST_WITH_DEPLOY"),
    "30_scheduled_backtest_job_control": ("30_scheduled_backtest_job_control.py", "SCHEDULED_BACKTEST_JOB_CONTROL"),
}


_EXAMPLES_DIR = Path(__file__).parent
_cached_examples: Dict[str, dict] = {}


def get_example(name: str) -> Optional[dict]:
    """예제 워크플로우 조회 (lazy loading)
    
    Returns:
        워크플로우 dict (JSON 형태)
    """
    if name in _cached_examples:
        return _cached_examples[name]
    
    entry = EXAMPLE_FILES.get(name)
    if not entry:
        return None
    
    filename, var_name = entry
    filepath = _EXAMPLES_DIR / filename
    if not filepath.exists():
        return None
    
    # Dynamic import
    spec = importlib.util.spec_from_file_location(f"example_{name}", filepath)
    if spec is None or spec.loader is None:
        return None
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # 변수명으로 워크플로우 dict 가져오기
    workflow = getattr(module, var_name, None)
    if workflow:
        _cached_examples[name] = workflow
    
    return workflow


def list_examples() -> list:
    """모든 예제 목록 조회"""
    return list(EXAMPLE_FILES.keys())


__all__ = [
    "get_example",
    "list_examples",
    "EXAMPLE_FILES",
]
