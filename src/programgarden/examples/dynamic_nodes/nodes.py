"""
Dynamic Node 예제 10종 — 노드 클래스 + 스키마 정의

사용법:
    from programgarden import WorkflowExecutor
    from examples.dynamic_nodes.nodes import ALL_SCHEMAS, ALL_NODE_CLASSES

    executor = WorkflowExecutor()
    executor.register_dynamic_schemas(ALL_SCHEMAS)
    executor.inject_node_classes(ALL_NODE_CLASSES)
"""

import csv
import io
import math
import statistics
from typing import Any, ClassVar, Dict, List, Optional, Set

from programgarden_core.nodes.base import (
    BaseNode,
    InputPort,
    NodeCategory,
    OutputPort,
)


# ═══════════════════════════════════════════════════════════════
# 1. Dynamic_SimpleRSI (condition)
#    종가 배열로 RSI(Relative Strength Index) 계산.
#    과매수(overbought)/과매도(oversold) 구간 판단.
# ═══════════════════════════════════════════════════════════════

class DynamicSimpleRSINode(BaseNode):
    """
    간단한 RSI 지표 계산 노드.

    입력: 종가(close) 배열
    설정: period(기간, 기본 14), overbought(과매수 기준, 기본 70),
          oversold(과매도 기준, 기본 30)
    출력: rsi 값, 신호(overbought/oversold/neutral), 트리거 여부
    """

    type: str = "Dynamic_SimpleRSI"
    category: NodeCategory = NodeCategory.CONDITION

    closes: List[float] = []
    period: int = 14
    overbought: float = 70.0
    oversold: float = 30.0

    _inputs: List[InputPort] = [
        InputPort(name="closes", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="rsi", type="number"),
        OutputPort(name="signal", type="string"),
        OutputPort(name="is_triggered", type="boolean"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        data = self.closes
        if len(data) < self.period + 1:
            return {"rsi": 50.0, "signal": "neutral", "is_triggered": False}

        gains, losses = [], []
        for i in range(1, len(data)):
            diff = data[i] - data[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        # Wilder's smoothing (최근 period 구간)
        avg_gain = statistics.mean(gains[-self.period :])
        avg_loss = statistics.mean(losses[-self.period :])

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi = round(rsi, 2)
        if rsi >= self.overbought:
            signal = "overbought"
        elif rsi <= self.oversold:
            signal = "oversold"
        else:
            signal = "neutral"

        return {
            "rsi": rsi,
            "signal": signal,
            "is_triggered": signal != "neutral",
        }


# ═══════════════════════════════════════════════════════════════
# 2. Dynamic_MACross (condition)
#    단기/장기 이동평균 교차(Golden Cross / Death Cross) 감지.
#    추세 전환 시점 포착에 활용.
# ═══════════════════════════════════════════════════════════════

class DynamicMACrossNode(BaseNode):
    """
    이동평균 교차 감지 노드.

    입력: 종가(close) 배열
    설정: fast_period(단기, 기본 5), slow_period(장기, 기본 20)
    출력: 단기/장기 MA 값, 교차 신호, 교차 여부
    """

    type: str = "Dynamic_MACross"
    category: NodeCategory = NodeCategory.CONDITION

    closes: List[float] = []
    fast_period: int = 5
    slow_period: int = 20

    _inputs: List[InputPort] = [
        InputPort(name="closes", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="fast_ma", type="number"),
        OutputPort(name="slow_ma", type="number"),
        OutputPort(name="signal", type="string"),
        OutputPort(name="crossed", type="boolean"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        data = self.closes
        if len(data) < self.slow_period + 1:
            return {
                "fast_ma": 0.0,
                "slow_ma": 0.0,
                "signal": "insufficient_data",
                "crossed": False,
            }

        def sma(values, period):
            return statistics.mean(values[-period:])

        fast_ma = round(sma(data, self.fast_period), 4)
        slow_ma = round(sma(data, self.slow_period), 4)

        # 이전 바 기준 교차 확인
        prev_fast = round(sma(data[:-1], self.fast_period), 4)
        prev_slow = round(sma(data[:-1], self.slow_period), 4)

        crossed = False
        signal = "none"
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            signal = "golden_cross"
            crossed = True
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            signal = "death_cross"
            crossed = True

        return {
            "fast_ma": fast_ma,
            "slow_ma": slow_ma,
            "signal": signal,
            "crossed": crossed,
        }


# ═══════════════════════════════════════════════════════════════
# 3. Dynamic_PriceAlert (condition)
#    현재가가 목표가에 도달했는지 감지.
#    지정가 주문 트리거, 손절/익절 알림 등에 활용.
# ═══════════════════════════════════════════════════════════════

class DynamicPriceAlertNode(BaseNode):
    """
    가격 알림 노드.

    설정: current_price(현재가), target_price(목표가),
          direction("above"/"below", 기본 "above")
    출력: 트리거 여부, 방향, 목표까지 거리(%)
    """

    type: str = "Dynamic_PriceAlert"
    category: NodeCategory = NodeCategory.CONDITION

    current_price: float = 0.0
    target_price: float = 0.0
    direction: str = "above"  # "above" or "below"

    _outputs: List[OutputPort] = [
        OutputPort(name="triggered", type="boolean"),
        OutputPort(name="direction", type="string"),
        OutputPort(name="distance_pct", type="number"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        if self.target_price == 0:
            return {"triggered": False, "direction": self.direction, "distance_pct": 0.0}

        distance_pct = round(
            ((self.current_price - self.target_price) / self.target_price) * 100, 2
        )

        if self.direction == "above":
            triggered = self.current_price >= self.target_price
        else:
            triggered = self.current_price <= self.target_price

        return {
            "triggered": triggered,
            "direction": self.direction,
            "distance_pct": distance_pct,
        }


# ═══════════════════════════════════════════════════════════════
# 4. Dynamic_SignalAggregator (condition)
#    여러 boolean 신호를 종합하여 최종 판단.
#    AND(모두 참), OR(하나라도 참), MAJORITY(과반수) 모드 지원.
# ═══════════════════════════════════════════════════════════════

class DynamicSignalAggregatorNode(BaseNode):
    """
    다중 신호 종합 판단 노드.

    입력: signals (boolean 배열)
    설정: method ("and"/"or"/"majority", 기본 "majority")
    출력: 최종 신호, 참 개수, 전체 개수, 사용 방식
    """

    type: str = "Dynamic_SignalAggregator"
    category: NodeCategory = NodeCategory.CONDITION

    signals: List[bool] = []
    method: str = "majority"  # "and", "or", "majority"

    _inputs: List[InputPort] = [
        InputPort(name="signals", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="final_signal", type="boolean"),
        OutputPort(name="true_count", type="number"),
        OutputPort(name="total_count", type="number"),
        OutputPort(name="method", type="string"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        sigs = self.signals
        true_count = sum(1 for s in sigs if s)
        total = len(sigs)

        if total == 0:
            final = False
        elif self.method == "and":
            final = true_count == total
        elif self.method == "or":
            final = true_count > 0
        else:  # majority
            final = true_count > total / 2

        return {
            "final_signal": final,
            "true_count": true_count,
            "total_count": total,
            "method": self.method,
        }


# ═══════════════════════════════════════════════════════════════
# 5. Dynamic_DataNormalizer (data)
#    숫자 배열을 min-max 정규화(0~1 범위).
#    ML 전처리, 지표 비교 등에 활용.
# ═══════════════════════════════════════════════════════════════

class DynamicDataNormalizerNode(BaseNode):
    """
    데이터 정규화 노드.

    입력: values (숫자 배열)
    설정: method ("minmax"/"zscore", 기본 "minmax")
    출력: 정규화된 배열, 최솟값, 최댓값, 통계 정보
    """

    type: str = "Dynamic_DataNormalizer"
    category: NodeCategory = NodeCategory.DATA

    values: List[float] = []
    method: str = "minmax"  # "minmax" or "zscore"

    _inputs: List[InputPort] = [
        InputPort(name="values", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="normalized", type="array"),
        OutputPort(name="min_val", type="number"),
        OutputPort(name="max_val", type="number"),
        OutputPort(name="stats", type="object"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        data = self.values
        if not data:
            return {
                "normalized": [],
                "min_val": 0.0,
                "max_val": 0.0,
                "stats": {},
            }

        min_val = min(data)
        max_val = max(data)
        mean_val = statistics.mean(data)

        if self.method == "zscore" and len(data) >= 2:
            std = statistics.stdev(data)
            if std > 0:
                normalized = [round((v - mean_val) / std, 4) for v in data]
            else:
                normalized = [0.0] * len(data)
        else:
            # minmax
            range_val = max_val - min_val
            if range_val > 0:
                normalized = [round((v - min_val) / range_val, 4) for v in data]
            else:
                normalized = [0.0] * len(data)

        return {
            "normalized": normalized,
            "min_val": round(min_val, 4),
            "max_val": round(max_val, 4),
            "stats": {
                "mean": round(mean_val, 4),
                "stdev": round(statistics.stdev(data), 4) if len(data) >= 2 else 0.0,
                "count": len(data),
                "method": self.method,
            },
        }


# ═══════════════════════════════════════════════════════════════
# 6. Dynamic_CSVParser (data)
#    CSV 문자열을 딕셔너리 배열로 변환.
#    외부 데이터 연동, HTTPRequestNode 결과 파싱 등에 활용.
# ═══════════════════════════════════════════════════════════════

class DynamicCSVParserNode(BaseNode):
    """
    CSV 파싱 노드.

    입력: csv_text (CSV 문자열, 첫 행 = 헤더)
    설정: delimiter (구분자, 기본 ",")
    출력: records (딕셔너리 배열), columns (컬럼명 배열), row_count
    """

    type: str = "Dynamic_CSVParser"
    category: NodeCategory = NodeCategory.DATA

    csv_text: str = ""
    delimiter: str = ","

    _inputs: List[InputPort] = [
        InputPort(name="csv_text", type="string", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="records", type="array"),
        OutputPort(name="columns", type="array"),
        OutputPort(name="row_count", type="number"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        if not self.csv_text.strip():
            return {"records": [], "columns": [], "row_count": 0}

        reader = csv.DictReader(
            io.StringIO(self.csv_text.strip()),
            delimiter=self.delimiter,
        )
        records = []
        for row in reader:
            # 숫자 자동 변환
            parsed = {}
            for k, v in row.items():
                try:
                    parsed[k] = float(v) if "." in v else int(v)
                except (ValueError, TypeError):
                    parsed[k] = v
            records.append(parsed)

        columns = list(reader.fieldnames) if reader.fieldnames else []
        return {
            "records": records,
            "columns": columns,
            "row_count": len(records),
        }


# ═══════════════════════════════════════════════════════════════
# 7. Dynamic_PositionSizer (order)
#    계좌 잔고, 리스크 비율, 손절가로 적정 매수 수량 계산.
#    리스크 관리 기반 포지션 사이징에 활용.
# ═══════════════════════════════════════════════════════════════

class DynamicPositionSizerNode(BaseNode):
    """
    포지션 크기 계산 노드.

    설정: balance(계좌 잔고), risk_pct(리스크 비율 %, 기본 2),
          entry_price(진입가), stop_price(손절가)
    출력: 매수 수량, 리스크 금액, 포지션 가치
    """

    type: str = "Dynamic_PositionSizer"
    category: NodeCategory = NodeCategory.ORDER

    balance: float = 0.0
    risk_pct: float = 2.0
    entry_price: float = 0.0
    stop_price: float = 0.0

    _outputs: List[OutputPort] = [
        OutputPort(name="quantity", type="number"),
        OutputPort(name="risk_amount", type="number"),
        OutputPort(name="position_value", type="number"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        if self.entry_price <= 0 or self.balance <= 0:
            return {"quantity": 0, "risk_amount": 0.0, "position_value": 0.0}

        risk_amount = round(self.balance * (self.risk_pct / 100), 2)
        risk_per_share = abs(self.entry_price - self.stop_price)

        if risk_per_share <= 0:
            return {"quantity": 0, "risk_amount": risk_amount, "position_value": 0.0}

        quantity = int(risk_amount / risk_per_share)
        position_value = round(quantity * self.entry_price, 2)

        return {
            "quantity": quantity,
            "risk_amount": risk_amount,
            "position_value": position_value,
        }


# ═══════════════════════════════════════════════════════════════
# 8. Dynamic_ProfitTaker (order)
#    현재 수익률이 목표에 도달하면 매도 수량 결정.
#    분할 익절(partial take-profit) 전략에 활용.
# ═══════════════════════════════════════════════════════════════

class DynamicProfitTakerNode(BaseNode):
    """
    수익 실현 판단 노드.

    설정: entry_price(진입가), current_price(현재가),
          holding_qty(보유 수량), target_pnl_pct(목표 수익률 %, 기본 10),
          sell_ratio(매도 비율, 기본 0.5 = 50%)
    출력: 매도 여부, 매도 수량, 현재 수익률
    """

    type: str = "Dynamic_ProfitTaker"
    category: NodeCategory = NodeCategory.ORDER

    entry_price: float = 0.0
    current_price: float = 0.0
    holding_qty: int = 0
    target_pnl_pct: float = 10.0
    sell_ratio: float = 0.5

    _outputs: List[OutputPort] = [
        OutputPort(name="should_sell", type="boolean"),
        OutputPort(name="sell_quantity", type="number"),
        OutputPort(name="current_pnl_pct", type="number"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        if self.entry_price <= 0 or self.holding_qty <= 0:
            return {"should_sell": False, "sell_quantity": 0, "current_pnl_pct": 0.0}

        pnl_pct = round(
            ((self.current_price - self.entry_price) / self.entry_price) * 100, 2
        )
        should_sell = pnl_pct >= self.target_pnl_pct
        sell_quantity = max(1, int(self.holding_qty * self.sell_ratio)) if should_sell else 0

        return {
            "should_sell": should_sell,
            "sell_quantity": sell_quantity,
            "current_pnl_pct": pnl_pct,
        }


# ═══════════════════════════════════════════════════════════════
# 9. Dynamic_RiskScorer (risk)
#    변동성, drawdown, 집중도를 종합하여 0~100 리스크 점수 산출.
#    포트폴리오 위험 수준 모니터링에 활용.
# ═══════════════════════════════════════════════════════════════

class DynamicRiskScorerNode(BaseNode):
    """
    종합 리스크 점수 계산 노드.

    설정: volatility(변동성 %, 기본 0), drawdown(현재 낙폭 %, 기본 0),
          concentration(최대 종목 비중 %, 기본 0)
    출력: 점수(0~100), 등급(A/B/C/D/F), 개별 팩터 점수
    """

    type: str = "Dynamic_RiskScorer"
    category: NodeCategory = NodeCategory.RISK

    volatility: float = 0.0
    drawdown: float = 0.0
    concentration: float = 0.0

    _outputs: List[OutputPort] = [
        OutputPort(name="score", type="number"),
        OutputPort(name="grade", type="string"),
        OutputPort(name="factors", type="object"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        # 각 팩터 0~100 점수화 (높을수록 위험)
        vol_score = min(100, self.volatility * 2)       # 50% vol → 100점
        dd_score = min(100, abs(self.drawdown) * 4)     # 25% dd → 100점
        conc_score = min(100, self.concentration)        # 100% 집중 → 100점

        # 가중 합산
        score = round(vol_score * 0.4 + dd_score * 0.35 + conc_score * 0.25, 1)

        if score <= 20:
            grade = "A"
        elif score <= 40:
            grade = "B"
        elif score <= 60:
            grade = "C"
        elif score <= 80:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": score,
            "grade": grade,
            "factors": {
                "volatility_score": round(vol_score, 1),
                "drawdown_score": round(dd_score, 1),
                "concentration_score": round(conc_score, 1),
            },
        }


# ═══════════════════════════════════════════════════════════════
# 10. Dynamic_PerformanceTracker (analysis)
#     수익률 시계열에서 성과 지표 계산 (총수익률, Sharpe, MDD).
#     백테스트 결과 분석, 실시간 성과 모니터링에 활용.
# ═══════════════════════════════════════════════════════════════

class DynamicPerformanceTrackerNode(BaseNode):
    """
    성과 지표 계산 노드.

    입력: returns (일별 수익률 배열, 예: [0.01, -0.02, 0.03])
    설정: risk_free_rate(무위험 수익률, 연율, 기본 0.04)
    출력: 총수익률, Sharpe Ratio, 최대낙폭(MDD), 통계 정보
    """

    type: str = "Dynamic_PerformanceTracker"
    category: NodeCategory = NodeCategory.ANALYSIS

    returns: List[float] = []
    risk_free_rate: float = 0.04  # 연 4%

    _inputs: List[InputPort] = [
        InputPort(name="returns", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="total_return", type="number"),
        OutputPort(name="sharpe_ratio", type="number"),
        OutputPort(name="max_drawdown", type="number"),
        OutputPort(name="stats", type="object"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        rets = self.returns
        if not rets:
            return {
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "stats": {},
            }

        # 총수익률 (복리)
        cumulative = 1.0
        for r in rets:
            cumulative *= 1 + r
        total_return = round((cumulative - 1) * 100, 2)

        # MDD
        peak = 1.0
        equity = 1.0
        max_dd = 0.0
        for r in rets:
            equity *= 1 + r
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
        max_drawdown = round(max_dd * 100, 2)

        # Sharpe Ratio (annualized)
        if len(rets) >= 2:
            daily_rf = self.risk_free_rate / 252
            excess = [r - daily_rf for r in rets]
            mean_excess = statistics.mean(excess)
            std_excess = statistics.stdev(excess)
            sharpe = round(
                (mean_excess / std_excess) * math.sqrt(252), 2
            ) if std_excess > 0 else 0.0
        else:
            sharpe = 0.0

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "stats": {
                "trading_days": len(rets),
                "positive_days": sum(1 for r in rets if r > 0),
                "negative_days": sum(1 for r in rets if r < 0),
                "win_rate": round(
                    sum(1 for r in rets if r > 0) / len(rets) * 100, 1
                ),
                "avg_return": round(statistics.mean(rets) * 100, 4),
            },
        }


# ═══════════════════════════════════════════════════════════════
# 스키마 & 클래스 맵 (일괄 등록용)
# ═══════════════════════════════════════════════════════════════

ALL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "node_type": "Dynamic_SimpleRSI",
        "category": "condition",
        "description": "종가 배열로 RSI 계산, 과매수/과매도 판단",
        "inputs": [{"name": "closes", "type": "array", "required": True}],
        "outputs": [
            {"name": "rsi", "type": "number"},
            {"name": "signal", "type": "string"},
            {"name": "is_triggered", "type": "boolean"},
        ],
        "config_schema": {
            "period": {"type": "integer", "default": 14},
            "overbought": {"type": "number", "default": 70},
            "oversold": {"type": "number", "default": 30},
        },
    },
    {
        "node_type": "Dynamic_MACross",
        "category": "condition",
        "description": "단기/장기 이동평균 교차(골든크로스/데드크로스) 감지",
        "inputs": [{"name": "closes", "type": "array", "required": True}],
        "outputs": [
            {"name": "fast_ma", "type": "number"},
            {"name": "slow_ma", "type": "number"},
            {"name": "signal", "type": "string"},
            {"name": "crossed", "type": "boolean"},
        ],
        "config_schema": {
            "fast_period": {"type": "integer", "default": 5},
            "slow_period": {"type": "integer", "default": 20},
        },
    },
    {
        "node_type": "Dynamic_PriceAlert",
        "category": "condition",
        "description": "현재가 목표가 도달 감지 (손절/익절 알림)",
        "outputs": [
            {"name": "triggered", "type": "boolean"},
            {"name": "direction", "type": "string"},
            {"name": "distance_pct", "type": "number"},
        ],
        "config_schema": {
            "current_price": {"type": "number"},
            "target_price": {"type": "number"},
            "direction": {"type": "string", "default": "above", "enum": ["above", "below"]},
        },
    },
    {
        "node_type": "Dynamic_SignalAggregator",
        "category": "condition",
        "description": "다중 boolean 신호 종합 판단 (AND/OR/MAJORITY)",
        "inputs": [{"name": "signals", "type": "array", "required": True}],
        "outputs": [
            {"name": "final_signal", "type": "boolean"},
            {"name": "true_count", "type": "number"},
            {"name": "total_count", "type": "number"},
            {"name": "method", "type": "string"},
        ],
        "config_schema": {
            "method": {"type": "string", "default": "majority", "enum": ["and", "or", "majority"]},
        },
    },
    {
        "node_type": "Dynamic_DataNormalizer",
        "category": "data",
        "description": "숫자 배열 min-max / z-score 정규화",
        "inputs": [{"name": "values", "type": "array", "required": True}],
        "outputs": [
            {"name": "normalized", "type": "array"},
            {"name": "min_val", "type": "number"},
            {"name": "max_val", "type": "number"},
            {"name": "stats", "type": "object"},
        ],
        "config_schema": {
            "method": {"type": "string", "default": "minmax", "enum": ["minmax", "zscore"]},
        },
    },
    {
        "node_type": "Dynamic_CSVParser",
        "category": "data",
        "description": "CSV 문자열 → 딕셔너리 배열 변환",
        "inputs": [{"name": "csv_text", "type": "string", "required": True}],
        "outputs": [
            {"name": "records", "type": "array"},
            {"name": "columns", "type": "array"},
            {"name": "row_count", "type": "number"},
        ],
        "config_schema": {
            "delimiter": {"type": "string", "default": ","},
        },
    },
    {
        "node_type": "Dynamic_PositionSizer",
        "category": "order",
        "description": "리스크 비율 기반 적정 매수 수량 계산",
        "outputs": [
            {"name": "quantity", "type": "number"},
            {"name": "risk_amount", "type": "number"},
            {"name": "position_value", "type": "number"},
        ],
        "config_schema": {
            "balance": {"type": "number"},
            "risk_pct": {"type": "number", "default": 2.0},
            "entry_price": {"type": "number"},
            "stop_price": {"type": "number"},
        },
    },
    {
        "node_type": "Dynamic_ProfitTaker",
        "category": "order",
        "description": "목표 수익률 도달 시 분할 매도 수량 결정",
        "outputs": [
            {"name": "should_sell", "type": "boolean"},
            {"name": "sell_quantity", "type": "number"},
            {"name": "current_pnl_pct", "type": "number"},
        ],
        "config_schema": {
            "entry_price": {"type": "number"},
            "current_price": {"type": "number"},
            "holding_qty": {"type": "integer"},
            "target_pnl_pct": {"type": "number", "default": 10.0},
            "sell_ratio": {"type": "number", "default": 0.5},
        },
    },
    {
        "node_type": "Dynamic_RiskScorer",
        "category": "risk",
        "description": "변동성/낙폭/집중도 종합 리스크 점수 (0~100, A~F)",
        "outputs": [
            {"name": "score", "type": "number"},
            {"name": "grade", "type": "string"},
            {"name": "factors", "type": "object"},
        ],
        "config_schema": {
            "volatility": {"type": "number", "default": 0},
            "drawdown": {"type": "number", "default": 0},
            "concentration": {"type": "number", "default": 0},
        },
    },
    {
        "node_type": "Dynamic_PerformanceTracker",
        "category": "analysis",
        "description": "수익률 시계열 성과 지표 (총수익률, Sharpe, MDD)",
        "inputs": [{"name": "returns", "type": "array", "required": True}],
        "outputs": [
            {"name": "total_return", "type": "number"},
            {"name": "sharpe_ratio", "type": "number"},
            {"name": "max_drawdown", "type": "number"},
            {"name": "stats", "type": "object"},
        ],
        "config_schema": {
            "risk_free_rate": {"type": "number", "default": 0.04},
        },
    },
]


ALL_NODE_CLASSES: Dict[str, type] = {
    "Dynamic_SimpleRSI": DynamicSimpleRSINode,
    "Dynamic_MACross": DynamicMACrossNode,
    "Dynamic_PriceAlert": DynamicPriceAlertNode,
    "Dynamic_SignalAggregator": DynamicSignalAggregatorNode,
    "Dynamic_DataNormalizer": DynamicDataNormalizerNode,
    "Dynamic_CSVParser": DynamicCSVParserNode,
    "Dynamic_PositionSizer": DynamicPositionSizerNode,
    "Dynamic_ProfitTaker": DynamicProfitTakerNode,
    "Dynamic_RiskScorer": DynamicRiskScorerNode,
    "Dynamic_PerformanceTracker": DynamicPerformanceTrackerNode,
}
