"""
ProgramGarden Community - 실전 전략 모음

완성된 워크플로우(nodes + edges) 형태의 실전 전략을 제공합니다.
플러그인을 조합하여 만든 바로 실행 가능한 전략들입니다.

사용법:
    from programgarden_community.strategies import get_strategy, list_strategies
    
    # 전략 목록 조회
    all_strategies = list_strategies()
    # {"overseas_stock": ["penny_stock_rsi", "backtest_to_live", ...]}
    
    # 특정 전략 조회
    strategy = get_strategy("overseas_stock", "penny_stock_rsi")
    
    # 실행
    from programgarden import ProgramGarden
    pg = ProgramGarden()
    job = pg.run(strategy)
"""

from typing import Optional, Dict, List


def get_strategy(product: str, name: str) -> Optional[dict]:
    """
    전략 워크플로우 조회
    
    Args:
        product: 상품 유형 (overseas_stock, overseas_futures)
        name: 전략 이름 (penny_stock_rsi, backtest_to_live 등)
    
    Returns:
        워크플로우 dict 또는 None
    """
    if product == "overseas_stock":
        from . import overseas_stock
        return overseas_stock.get_strategy(name)
    elif product == "overseas_futures":
        from . import overseas_futures
        return overseas_futures.get_strategy(name)
    return None


def list_strategies(product: Optional[str] = None) -> Dict[str, List[str]]:
    """
    전략 목록 조회
    
    Args:
        product: 특정 상품만 조회 (None이면 전체)
    
    Returns:
        상품별 전략 이름 목록
    """
    from . import overseas_stock
    from . import overseas_futures
    
    all_strategies = {
        "overseas_stock": overseas_stock.list_strategies(),
        "overseas_futures": overseas_futures.list_strategies(),
    }
    
    if product:
        return {product: all_strategies.get(product, [])}
    return all_strategies


__all__ = ["get_strategy", "list_strategies"]
