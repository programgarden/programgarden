"""
ProgramGarden Community - Analysis 노드

성과·리스크 분석 노드 (quantstats 등 heavy optional deps 사용).
heavy import 는 각 노드 execute() 내부 lazy — base(no-extras) 격리 유지.
"""

from programgarden_community.nodes.analysis.performance_report import PerformanceReportNode

__all__ = ["PerformanceReportNode"]
