"""
WorkflowPositionTracker - 워크플로우 포지션 FIFO 추적

워크플로우에서 발생한 주문과 수동 주문을 분리하여 추적하고,
FIFO 방식으로 포지션을 관리합니다.

주요 기능:
- 워크플로우 주문 기록 (매수/매도)
- FIFO 기반 포지션 청산 처리
- 실시간 평가 수익률 계산
- 이상 거래 감지 및 신뢰도 점수 계산

주문일자(order_date) 매칭 규약 — 왜 ±1일 창인가:
- 주문 기록의 order_date 와 체결의 order_date 는 **출처가 다르다**. 같은 주문이라도 두
  값이 하루 어긋날 수 있고, 어긋나는 방향은 **양쪽 다 이 저장소에 근거가 있다**:
  · **D-1**(주문 기록일 = 체결일자 − 1) — 설계상. 실시간 체결 프레임(AS1/SC1)에는
    주문일자 필드 자체가 없어 **수신 시각의 로컬 날짜**로 채운다(executor.py 의 AS1/SC1
    경로). 미국장은 KST 자정을 항상 관통하므로 23:5x 접수 → 00:0x 체결이면 주문 기록일이
    체결일자보다 하루 앞선다.
  · **D+1**(주문 기록일 = 체결일자 + 1) — 실측. LS 는 **야간 세션을 전 영업일로
    파일링**한다: 00:39:25 KST(로컬 20260910)에 접수된 주문이 CIDBQ02400 에서
    OrdDt/ExecDt **20260909** 로 돌아왔다(2026-09-10 실측 —
    tests/test_broker_business_date_window.py 헤더). record_order 는 접수 시점 **로컬**
    날짜를 쓰고 TC3 체결은 프레임의 ordr_dt(= 브로커 영업일)를 쓰므로(executor.py 의 TC3
    경로), 이때는 주문 기록일이 체결일자보다 하루 **뒤**가 된다.
  어느 쪽이든 정확일치만 보면 우리 주문인데도 매칭에 실패한다. 그러면 매체코드
  '40'(API) → 버퍼 → 타임아웃 후 **unknown_api** 로 굳어, 우리 체결이 workflow 집계에서
  통째로 빠진다.
- 그래서 **정확일치를 먼저** 보고, 실패했을 때만 **D-1·D+1 두 칸**을 훑는다
  (_order_date_window). D±2 이상은 어느 쪽으로도 보지 않는다.
- 넓힌 창은 '날짜가 한 칸 어긋났을 것' 이라는 **추론**이다. 그래서 수용 조건이 다섯이다:
  ① 후보가 **정확히 1건**일 것 — 우리 원장 안에서 같은 주문번호가 재사용된 경우를 거른다.
  ② 후보의 **종목이 체결의 종목과 일치**할 것. ①만으로는 부족하다: 제3자(남의) 주문번호는
     정의상 우리 원장에 없으므로 후보가 늘 1건이라 ①을 항상 통과한다. 종목 대조가 없으면
     번호가 우연히 겹친 남의 체결(HTS 85 포함)이 workflow 로 흡수된다 — 2026-09-12 적대적
     검토 실측: 우리 D-1 AAPL buy #86382 기록 뒤 다음 날 TSLA sell 5@300 commda=85 체결이
     classification='workflow' 로 기록되고 FIFO 가 'Sell without enough position' 까지 냈다.
  ③ 양쪽에 매매구분이 있으면 **side 도 일치**할 것.
  ④ 프레임의 **매체코드가 사람 채널이 아닐 것**(_may_widen_for_media). 브로커 주문번호는
     **영업일마다 리셋**되므로 어제 우리 번호가 오늘 사용자 주문에 재발급될 수 있다 —
     2026-09-12 적대적 재검증 실측: 우리 D-1 AAPL buy #3 기록 뒤 다음 날 14:00 사용자 HTS
     매수 7@250(order_no '3', commda_code '85')이 종목·side 까지 같아 ①②③ 을 전부
     통과해 workflow 로 기록되고 workflow_position_lots 에 남의 로트가 생겼다. 프레임이
     "이건 사람이 낸 주문" 이라고 명시한 체결을 추론으로 삼키지 않는다.
  ⑤ **체결 수량이 주문 수량(workflow_orders.quantity)을 넘지 않을** 것
     (_accept_widened_match → _fill_quantity_within_order). 우리 주문의 체결(부분·전량)은
     주문 수량을 넘을 수 없으므로 이 가드는 우리 체결을 놓치지 않고(false-miss 없음),
     세션 시각에 의존하지도 않는다. ④가 못 막는 재발급(매체코드가 사람이 아닌 경로)이
     종목·side 까지 같아도 수량이 우리 주문보다 크면 여기서 걸린다(2026-09-12 재검증
     실측 형태: 우리 1주 주문 → 남의 7주 체결). 비교는 float(소수점 주식 0.847972 vs
     주문 1 → 통과). 원장 수량이 비었거나 0 이면 대조 불가이므로 추론 없이 거부한다.
  ⑥ 주문 기록 시각(workflow_orders.created_at)과 체결 수신 시각(PendingFill.received_at)의
     간격이 **_WIDENED_MATCH_MAX_GAP 이내**일 것(_accept_widened_match). 이건 세션 경계
     **사실이 아니라 휴리스틱(보조 가드)** 이다 — 미국주식은 KST 주간(09:00~, Blue Ocean
     주간거래)에도 거래되므로(저장소 메모리 관측 확정 2026-09-11: MARA 거래량 26→938)
     '다음 날 낮에 재발급된 번호' 는 우리 주문 몇 시간 뒤일 수 있어 시각만으로는 못
     가른다. 수량이 우리 주문 이하라 ⑤ 를 통과한 재발급이 임계 밖에서 오면 여기가
     마지막 방어다. 임계 근거는 상수 정의 주석 참조. created_at 이 비어 있는 옛 행은
     추론 없이 거부한다.
  하나라도 어긋나면 넓히기 전과 같이 미매칭(→ unknown_api) 쪽으로 남긴다.
  실질 방어는 ④(사람 매체코드 거부)·②③(종목/방향 일치)·⑤(체결수량≤주문수량)이고,
  ⑥(시각)은 보조다.
- ②③④⑤⑥ 은 **창 경로에만** 적용한다. 정확일치 경로의 의미는 건드리지 않는다 — 거기선
  (주문번호, 주문일자) 동시 일치가 더 강한 증거다. 또 국내 SC1 체결의 종목코드는
  'A005930' 처럼 접두가 붙어 주문 기록('005930')과 문자열이 다르므로, 정확일치 경로에
  종목 대조를 넣으면 지금 맞던 매칭이 깨진다.
- 넓히는 건 날짜뿐이다. product/provider/trading_mode/주문번호 스코프는 정확일치 조회와
  똑같이 유지한다.
- 분류 경로(_is_workflow_fill)와 식별자 조회 경로(lookup_order_identity)는 **같은 매칭
  함수**(_match_workflow_order)를 쓰되, **주문번호 대조 mode 는 호출부마다 다르다**:
  _is_workflow_fill 은 명시 체결번호가 없으면 'exact'(문자열 정확일치), 있으면
  'normalized'; lookup_order_identity 는 'exact_or_normalized'. 이유는 각 호출부의 종전
  의미를 그대로 보존하기 위해서다 — 분류는 처음부터 문자열 정확일치였고(느슨하게 바꾸면
  오분류 표면이 커진다), 조회는 주문 ACK 와 체결의 0 패딩 차이를 흡수해야 node_id 를 붙일
  수 있었다. mode 를 통일하면 둘 중 한쪽의 의미가 바뀌므로 통일하지 않는다. **날짜 규약과
  창 수용 조건은 두 경로가 공유한다** — 그게 갈리면 classification='workflow' 인데 node_id
  가 None 인 상태가 만들어지고, 하류 멱등 키(job_id:node_id:order_id:seq)의 node 축이 빈
  문자열로 접혀 같은 주문의 경계 전후 체결이 서로 다른 축을 갖는다.
"""

import sqlite3
import asyncio
import logging
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple, Callable, Awaitable
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 계약 승수(contract multiplier) 역산 안정화 파라미터 ──
# 브로커 pnl_amount 를 (현재가−평단)×수량 으로 나눠 승수를 역산할 때, 분모가
# 작으면(현재가≈평단) 반올림 오차가 증폭돼 mult 가 폭주한다. 아래 가드로 오염을
# 막고, 실패 시 심볼별 최근 성공값 캐시(없으면 1.0)로 폴백한다.
#
# _MULT_MIN_REL_GAP: |현재가−평단|/평단 이 이 값 미만이면 역산 생략. 0.1% 로 둔다 —
#   검증한 폭주 케이스(평단 8547.67, 현재가차 1.0 → 상대차 ≈0.0117%)를 잡아야 하므로
#   0.01% 는 부족(0.0117% > 0.01%)하고 0.1% 여야 확실히 걸린다.
# _MULT_MIN/_MULT_MAX: 표준 선물 승수는 0.5~수천 범위. 이 밴드 밖 역산값은 거부.
# _MULT_INT_SNAP_REL: 선물 승수는 정수 관행이라, 역산값이 최근접 정수와 상대오차
#   이 값 이내면 정수로 스냅(수수료 혼입/반올림 왜곡 완화).
_MULT_MIN_REL_GAP = Decimal("0.001")   # 0.1%
_MULT_MIN = Decimal("0.5")
_MULT_MAX = Decimal("10000")
_MULT_INT_SNAP_REL = Decimal("0.02")   # 2%

# ── 넓힌 주문일자 창(D±1)의 시각 근접 임계 — **휴리스틱(보조 가드)** ──
# 창은 '영업일/자정 경계가 한 칸 어긋난 같은 주문' 하나만 구제하려고 존재한다. 그런데
# 브로커 주문번호는 **영업일마다 리셋**되므로(저장소 기록), 어제 우리 주문번호가 오늘
# 사용자 주문에 재발급되고 종목·매매구분까지 같으면 후보 수·종목·side 가드를 전부
# 통과한다. 그래서 창 수용은 **주문 기록 시각(workflow_orders.created_at)과 체결 수신
# 시각(PendingFill.received_at)의 간격이 이 임계 이내** 일 때만 인정한다.
#
# 🔴 이 시각 가드는 세션 경계 **사실이 아니라 휴리스틱**이다. 미국주식은 KST 주간
# (09:00~, Blue Ocean 주간거래)에도 거래된다 — 저장소 메모리 관측 확정(2026-09-11
# 09:02~09:05 KST, g3101 반복 샘플링: MARA 거래량 26→938, NVDA 1,239→4,854). 우리
# 워크플로우의 ScheduleNode/TradingHoursFilterNode 가 그 구간을 막고 있을 뿐, 사용자는
# 그 시간에 거래한다. 따라서 '다음 날 낮에 재발급된 주문번호' 는 우리 주문 몇 시간 뒤일
# 수 있다(자정 직전 우리 주문 → 다음 날 10:00 남의 주문 = 10시간, 임계 안). 시각만으로는
# 재발급을 못 가른다. 실질 방어는 ① 사람 매체코드 거부(_may_widen_for_media)
# ② 종목/방향 일치 ③ 체결수량 ≤ 주문수량(_fill_quantity_within_order) 이고, 시각은
# 보조다.
#
# 값(12시간)을 유지하는 이유: 구제 대상(자정 관통·야간 세션 파일링)의 실제 간격은 미국
# 정규장 한 세션(KST 22:30~05:00, 6.5시간) 안이고, 22:35 접수 → 04:5x 체결(6.4시간)
# 지정가 체결이 실재한다. 더 줄이면 그 체결을 놓친다(false-miss). 더 늘리면 D±1 창 안에서
# '반대쪽 날의 같은 시간대' 가 들어온다. 12시간은 그 두 제약 사이의 값이지 재발급을 끊는
# 경계가 아니다.
_WIDENED_MATCH_MAX_GAP = timedelta(hours=12)


@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str
    exchange: str
    quantity: Decimal  # 소수점(fractional) 잔고 대응 — 가격류와의 Decimal 혼합 산술 안전
    avg_price: Decimal
    classification: str  # "workflow" | "manual" | "unknown_api"


@dataclass
class LotInfo:
    """FIFO 로트 정보"""
    id: int
    symbol: str
    exchange: str
    fill_datetime: str  # YYYYMMDD_HHMMSSsss
    buy_price: Decimal
    original_qty: int
    remaining_qty: int
    classification: str


@dataclass
class AnomalyResult:
    """이상 거래 감지 결과"""
    pattern: str  # "sell_without_buy" | "quantity_imbalance" | "unknown_api_ratio"
    symbol: str
    description: str
    severity: int  # 감점 점수


@dataclass
class PendingFill:
    """버퍼링된 체결 정보"""
    order_no: str
    order_date: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    price: float
    fill_time: str
    commda_code: str
    received_at: datetime
    execution_id: Optional[str | int] = None
    # Account average purchase price for this symbol at the moment of the fill,
    # read from the broker snapshot before it refreshes. Used only to estimate a
    # workflow sell's residual tail (see _process_sell_fifo); None → no estimate.
    account_avg_price: Optional[float] = None


class ExecutionIdentityError(ValueError):
    """A fill's execution/order identity could not be normalized into a key.

    ``_normalize_identifier`` / ``_execution_key`` 계열이 **이것만** 올린다 —
    "체결번호(또는 그 짝인 주문번호/주문일자)가 원장 중복방지 키로 쓸 수 없다" 는
    뜻이다. 전용 타입을 두는 이유: context.record_workflow_fill 의 폴백이
    "identity 축이 깨졌으면 체결번호를 떼고 한 번 더 기록한다" 를 수행하는데,
    그 폴백이 **모든 ValueError** 를 잡으면 identity 와 무관한 예외까지 삼켜
    체결번호 없이 재기록한다. 실제로 닿는 경로가 있다 —
    ``_execution_facts`` 의 유한성 가드
    (ValueError("Explicit execution quantity and price must be finite"))는
    수량/가격이 inf·nan 일 때 나는데, 그건 체결번호를 뗀다고 나아지지 않는
    **체결 사실 자체의 문제**다. 그래서 그 부류는 plain ValueError 로 남겨
    폴백이 잡지 않게 한다.
    """


class ExecutionIdentityConflictError(ValueError):
    """An explicit execution identity was replayed with different fill facts.

    ⚠️ 일부러 ``ExecutionIdentityError`` 의 서브클래스가 **아니다**. 이건 정규화
    실패가 아니라 "같은 체결번호가 이미 기록돼 있는데 체결 사실이 다르다" 는
    신호라, 체결번호를 떼고 재시도하면 같은 브로커 체결이 두 번 기록된다.
    context 의 폴백 대상에서 빠져 있어야 한다.
    """


# LS 통신매체코드(CommdaCode / MdaCode) — **상품 구분 없는 단일 합집합 표**.
# 값마다 출처가 다르다:
#  · 해외선물 TR 문서(src/finance/docs/cidbq02400_contract.md:74-77) — 00=지점, 22=iPhone,
#    23=Android, 41=API, 43=Robo API, 85=HTS, 96=최종결제, LP=로스컷, SK=CashCall,
#    SO=조건주문. 문서 예시에 나오는 40 은 이 표에 없다.
#  · '40' = 우리 OPEN API 주문이 실제로 받는 값(dev verified_fills 실측 4건 + 2026-09-12
#    해외주식 AS1 실측: 우리 매도 주문 244 → 40) — 표의 41/43 과 함께 API 묶음.
#  · 해외주식 AS1 라이브 실측(2026-09-12, 실계좌 NIO 1주씩): HTS → 85(표와 일치) ·
#    iPhone 투혼앱 → **51**(표의 22 아님) · 투혼 웹 → **03**(표에 없음).
#  · 국내(SC1) **50=MTS · 60=HTS** · 00=지점 · 40/41=오픈API — **오너 진술(2026-09-12),
#    라이브 미관측**. 저장소 SDK 에는 국내 매체코드 enum 이 선언돼 있지 않다.
#
# 왜 상품별로 쪼개지 않는가(2026-09-12 적대적 검토 지적 B3): tracker 는 워크플로우당 1개이고
# **가장 먼저 초기화된 브로커의 product 로 고정**된다(context.py 의 조기 return). 한 워크플로우에
# 해외+국내 브로커가 같이 있는 구성은 executor 가 이미 인정하는데, 표를 상품으로 가르면 국내가
# 먼저 뜬 워크플로우에서 **해외 체결이 국내 표로 판정**돼 85(HTS)가 other 로 떨어지고 43 은
# api→other 가 되어 버퍼를 건너뛰고 즉시 확정된다 — 표가 하나였을 때는 없던 회귀다.
# 두 표 사이에 **같은 코드가 서로 다른 채널을 뜻하는 사례는 현재까지 없어** 합집합이 안전하다.
# (해외 85=HTS / 국내 60=HTS 처럼 값이 다를 뿐, 같은 값이 한쪽은 사람 다른 쪽은 API 인 경우가
# 없다.) 충돌이 관측되면 그때 상품별로 쪼갠다.
MEDIA_CODES_HUMAN = frozenset({"85", "60", "22", "23", "50", "00", "51", "03"})
# 85=HTS(해외) · 60=HTS(국내, 오너 진술) · 22/23=앱(표) · 50=MTS(국내, 오너 진술) ·
# 00=지점 · 51=투혼앱(실측) · 03=투혼웹(실측)
MEDIA_CODES_API = frozenset({"40", "41", "43"})   # OPEN API(실측) · API · Robo API


def media_channel(commda_code: str | None) -> str:
    """Map a broker media code to "human" | "api" | "unknown" | "other".

    One table for every product — see MEDIA_CODES_* above for why splitting it
    by product regressed mixed (overseas + KRX) workflows.

    unknown = blank/None (the frame said nothing); other = a code the table does
    not attribute to a person or an API client (96/LP/SK/SO ...) or one it does
    not list at all. Neither is ever asserted to be a person.
    """
    code = str(commda_code or "").strip()
    if not code:
        return "unknown"
    if code in MEDIA_CODES_HUMAN:
        return "human"
    if code in MEDIA_CODES_API:
        return "api"
    return "other"


class WorkflowPositionTracker:
    """
    워크플로우 포지션 FIFO 추적기
    
    워크플로우 주문과 수동 주문을 분리하고 FIFO 방식으로 포지션을 관리합니다.
    """
    
    # 버퍼 타임아웃 (초)
    FILL_BUFFER_TIMEOUT = 2.0
    
    def __init__(
        self,
        db_path: str,
        job_id: str,
        broker_node_id: str,
        product: str = "overseas_stock",
        provider: str = "ls",
        trading_mode: str = "live",
    ):
        """
        Args:
            db_path: SQLite DB 경로
            job_id: Job ID
            broker_node_id: BrokerNode ID (로그용)
            product: 상품 유형 ("overseas_stock" | "overseas_futures")
            provider: 증권사 ("ls" | "kiwoom" | ...)
            trading_mode: 거래 모드 ("paper" | "live")
        """
        self.db_path = db_path
        self.job_id = job_id
        self.broker_node_id = broker_node_id  # 로그용으로 유지
        self.product = product
        self.provider = provider
        self.trading_mode = trading_mode

        # 체결 원장이 바뀔 때마다 증가한다. 읽는 쪽(개인 지표 캐시)이 "가격 틱은
        # 체결을 바꾸지 않는다"는 이유로 결과를 잠시 재사용하는데, 시간만 보고
        # 재사용하면 **막 들어온 체결을 놓친다**. 2026-09-10 실측: SNDL 체결이
        # 02:17:31.674 에 기록됐는데 봉투는 0.5초 전(02:17:31.189)에 계산된 값이
        # 그대로 굳어, 원장에 체결이 1건 있는데도 체결 주문 수가 0 으로 저장됐다.
        # 버퍼 처리처럼 컨텍스트를 거치지 않는 쓰기 경로까지 덮으려면 원장 자신이
        # 세는 게 맞다.
        self.fill_revision = 0

        # 체결 버퍼 (Race Condition 방어)
        # Every arrival without an execution ID remains a separate event. An
        # order can have multiple partial executions before its ACK is recorded.
        self._pending_fills: Dict[int, PendingFill] = {}
        self._next_pending_fill = 0
        self._buffer_lock = asyncio.Lock()

        # 심볼별 계약 승수(contract multiplier) 캐시.
        # 브로커 스냅샷의 pnl_amount 에서 역산한다(선물 승수 반영). 현재가≈평단이라
        # 역산 불가한 틱에서는 이 캐시(최근 성공값)로 폴백해 FIFO 산술을 스케일한다.
        self._multiplier_cache: Dict[str, Decimal] = {}

        # 체결 확정 콜백. 원장에 **새로** 기록된 체결마다 정확히 1회 발화한다 —
        # 즉시/버퍼/타임아웃 경로가 모두 _process_fill_internal 을 거치므로 한 곳에서
        # 부른다. 리플레이(동일 execution identity 재도착)는 그 앞에서 조기 반환하므로
        # 재발화하지 않는다. 컨텍스트가 이걸 on_order_fill 리스너로 연결한다.
        self._on_fill_classified: Optional[
            Callable[["PendingFill", str], Awaitable[None]]
        ] = None

        # DB 초기화
        self._init_db()

    def set_fill_classified_callback(
        self,
        callback: Optional[Callable[["PendingFill", str], Awaitable[None]]],
    ) -> None:
        """Register an async callback fired once per newly recorded fill.

        The callback receives ``(fill: PendingFill, classification: str)`` where
        classification is one of "workflow" | "manual" | "unknown_api" | "other".
        It must not mutate ledger state; exceptions raised by it are caught and
        logged so they never break FIFO recording.
        """
        self._on_fill_classified = callback

    def lookup_order_identity(
        self,
        order_no: str,
        order_date: str,
        *,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        commda_code: Optional[str] = None,
        received_at: Optional[datetime] = None,
        quantity: Optional[float] = None,
    ) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """Return ``(job_id, node_id)`` for a recorded workflow order, else None.

        Uses the same matcher as classification (``_match_workflow_order``), but
        **the order-number comparison mode differs per call site**: this path
        asks for "exact_or_normalized" while ``_is_workflow_fill`` asks for
        "exact" (no explicit execution id) or "normalized" (with one). That
        difference is deliberate — each call site keeps the meaning it had before
        the two matchers were merged: classification was always a plain string
        comparison, and this lookup had to absorb zero-padding differences
        between the order ACK and the fill in order to resolve a node_id at all.
        What the two paths DO share is the date rule and the widened-window
        accept guards — exact order date first, then the D±1 window under
        single-candidate + symbol/side + media-channel + fill-quantity-within-
        order-quantity + time-proximity (heuristic) guards.
        Sharing those is the contract: a fill classified "workflow" through the
        window must resolve its node_id here too, or the downstream idempotency
        key ``job_id:node_id:order_id:seq`` collapses its node axis to an empty
        string for exactly those boundary-straddling fills.

        ``symbol``/``side``/``commda_code``/``received_at``/``quantity`` describe
        the fill being resolved and are used only by the widened path. When a caller does
        not pass them, they are read back from this ledger's own trade_history
        row for that order (the fill row is committed before the classified
        callback fires) — never guessed. With no such row and no argument, the
        widened path has nothing to compare and is refused, which is the safe
        direction.

        Scoped to this ledger's product/provider/trading mode.
        """
        try:
            if (symbol is None or side is None or commda_code is None
                    or received_at is None or quantity is None):
                recorded = self._recorded_fill_identity(order_no, order_date)
                if recorded is not None:
                    if symbol is None:
                        symbol = recorded[0]
                    if side is None:
                        side = recorded[1]
                    if commda_code is None:
                        commda_code = recorded[2]
                    if received_at is None:
                        received_at = recorded[3]
                    if quantity is None:
                        quantity = recorded[4]
            match = self._match_workflow_order(
                order_no, order_date, mode="exact_or_normalized",
                symbol=symbol, side=side,
                commda_code=commda_code, received_at=received_at,
                quantity=quantity,
            )
        except Exception as e:
            logger.warning(f"lookup_order_identity failed: {e}")
            return None
        if match is None:
            return None
        _matched_date, job_id, node_id = match
        return (job_id, node_id)

    def _recorded_fill_identity(
        self, order_no: str, order_date: str
    ) -> Optional[Tuple[Optional[str], Optional[str], Optional[str], Optional[datetime],
                        Optional[float]]]:
        """This order's most recently recorded fill facts.

        Returns ``(symbol, side, commda_code, recorded_at, quantity)``. Facts only — the
        row was written by ``_process_fill_internal`` straight from the broker
        frame, and ``recorded_at`` is this ledger's own ``created_at`` for that
        row, i.e. when the fill was written (milliseconds after the arrival that
        ``PendingFill.received_at`` stamps). Returns None when no fill has been
        recorded for the order, and ``recorded_at`` is None when the stored
        timestamp is missing or unparseable (nothing is inferred; the caller then
        refuses to widen).
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT symbol, side, commda_code, created_at, quantity FROM trade_history
                WHERE product = ? AND provider = ? AND trading_mode = ?
                  AND order_date = ? AND order_no = ?
                ORDER BY id DESC LIMIT 1
                """,
                (self.product, self.provider, self.trading_mode, order_date, order_no),
            ).fetchone()
        if row is None:
            return None
        return (row[0], row[1], row[2], self._parse_recorded_timestamp(row[3]), row[4])
    
    def _init_db(self) -> None:
        """데이터베이스 테이블 초기화"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # WAL 모드: 멀티 워크플로우 동시 접근 시 SQLITE_BUSY 방지
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            # 워크플로우 주문 기록
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    order_no TEXT NOT NULL,
                    order_date TEXT NOT NULL,
                    symbol TEXT,
                    exchange TEXT,
                    side TEXT,
                    quantity INTEGER,
                    price REAL,
                    job_id TEXT,
                    node_id TEXT,
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    created_at TEXT,
                    UNIQUE(order_no, order_date)
                )
            """)

            # 워크플로우 포지션 로트 (FIFO용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_position_lots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    exchange TEXT,
                    fill_datetime TEXT,
                    buy_price REAL,
                    original_qty INTEGER,
                    remaining_qty INTEGER,
                    classification TEXT,
                    order_no TEXT,
                    order_date TEXT,
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    created_at TEXT
                )
            """)

            # 체결 내역
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    order_no TEXT,
                    order_date TEXT,
                    symbol TEXT,
                    exchange TEXT,
                    side TEXT,
                    quantity INTEGER,
                    price REAL,
                    fill_datetime TEXT,
                    classification TEXT,
                    commda_code TEXT,
                    realized_pnl REAL,
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    created_at TEXT,
                    execution_id TEXT,
                    normalized_order_no TEXT,
                    execution_payload TEXT
                )
            """)

            # 상품+증권사 메타데이터 (현재 거래 모드 추적용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broker_metadata (
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    paper_trading INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (product, provider)
                )
            """)

            # 인덱스 생성 (trading_mode 포함)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_fifo_v2 ON workflow_position_lots(trading_mode, symbol, fill_datetime)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_lookup_v2 ON workflow_orders(trading_mode, order_no, order_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_remaining_v2 ON workflow_position_lots(trading_mode, symbol, remaining_qty)")

            # Additive migration: old rows have no evidence of execution identity.
            # Never infer or backfill one from timestamps, prices, or quantities.
            columns = {row[1] for row in cursor.execute("PRAGMA table_info(trade_history)")}
            for column in ("execution_id", "normalized_order_no", "execution_payload"):
                if column not in columns:
                    cursor.execute(f"ALTER TABLE trade_history ADD COLUMN {column} TEXT")
            # Additive columns for the account-average-price sell estimate. A
            # workflow sell that empties the strategy's own lots and still has a
            # tail records that tail here (the residual quantity, the account
            # average purchase price it was estimated against, the source label,
            # and the estimated PnL). realized_pnl stays FIFO-matched only; these
            # never enter _execution_facts / conflict detection. NULL on every
            # row that carries no estimate (buys, fully matched sells, old rows).
            for column, coltype in (("unmatched_qty", "REAL"),
                                    ("estimate_basis_price", "REAL"),
                                    ("estimate_source", "TEXT"),
                                    ("estimated_pnl", "REAL")):
                if column not in columns:
                    cursor.execute(f"ALTER TABLE trade_history ADD COLUMN {column} {coltype}")
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_history_execution_v1
                ON trade_history(product, provider, trading_mode, order_date,
                                 normalized_order_no, execution_id)
                WHERE execution_id IS NOT NULL
            """)

            conn.commit()

    def update_trading_mode(self, trading_mode: str) -> None:
        """
        현재 거래 모드를 broker_metadata에 기록합니다.

        모의투자 ↔ 실전투자 전환 시 데이터를 초기화하지 않고,
        trading_mode 컬럼으로 분리 저장하여 각 모드의 수익률을 독립적으로 유지합니다.

        Args:
            trading_mode: 거래 모드 ("paper" | "live")
        """
        paper_trading_int = 1 if trading_mode == "paper" else 0
        identifier = f"{self.product}/{self.provider}"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT paper_trading FROM broker_metadata
                WHERE product = ? AND provider = ?
            """, (self.product, self.provider))

            row = cursor.fetchone()

            if row is None:
                cursor.execute("""
                    INSERT INTO broker_metadata (product, provider, paper_trading, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (self.product, self.provider, paper_trading_int, datetime.now().isoformat()))
                conn.commit()
                mode_label = "모의투자" if trading_mode == "paper" else "실전투자"
                logger.info(f"[{identifier}] Initial trading mode: {mode_label}")
                return

            prev_paper_trading = row[0]

            if prev_paper_trading != paper_trading_int:
                prev_mode = "모의투자" if prev_paper_trading == 1 else "실전투자"
                new_mode = "모의투자" if trading_mode == "paper" else "실전투자"

                cursor.execute("""
                    UPDATE broker_metadata
                    SET paper_trading = ?, updated_at = ?
                    WHERE product = ? AND provider = ?
                """, (paper_trading_int, datetime.now().isoformat(), self.product, self.provider))
                conn.commit()

                logger.info(f"[{identifier}] 거래 모드 전환: {prev_mode} → {new_mode} (데이터 보존)")

    def record_order(
        self,
        order_no: str,
        order_date: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        price: float,
        job_id: str,
        node_id: str,
    ) -> None:
        """
        워크플로우 주문 기록
        
        주문 API 응답 후 호출하여 주문번호를 기록합니다.
        나중에 체결 시 이 정보로 워크플로우 주문 여부를 판단합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            symbol: 종목코드
            exchange: 거래소
            side: 매매구분 ("buy" | "sell")
            quantity: 수량
            price: 가격
            job_id: Job ID
            node_id: Node ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO workflow_orders
                (product, provider, order_no, order_date, symbol, exchange, side, quantity, price, job_id, node_id, trading_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.product, self.provider,
                order_no, order_date, symbol, exchange, side, quantity, price,
                job_id, node_id, self.trading_mode, datetime.now().isoformat()
            ))
            conn.commit()
        
        # 버퍼에서 매칭되는 체결 확인 (이벤트 루프가 있는 경우에만)
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._process_buffered_fill(order_no, order_date))
        except RuntimeError:
            # 동기 환경에서는 버퍼 처리 생략 (체결이 먼저 올 일 없음)
            pass
        else:
            # 🔴 fire-and-forget 태스크의 예외는 **아무 데도 안 남는다**.
            # _process_buffered_fill 안에서는 _normalize_identifier 가
            # ExecutionIdentityError 를 올릴 수 있고(버퍼에 깨진 체결번호가
            # 섞였을 때), 그러면 그 체결은 버퍼에 남아 타임아웃 경로로
            # unknown_api 가 되면서 **원인 기록이 하나도 없다**. 아무도 await 하지
            # 않으므로 done 콜백으로 직접 로깅한다(취소는 정상 종료로 본다 —
            # 워크플로우 종료 시 루프가 태스크를 취소한다).
            task.add_done_callback(self._log_buffered_fill_task_error)
        
        logger.debug(f"Recorded workflow order: {order_no} ({symbol} {side} {quantity}@{price})")
    
    @staticmethod
    def _log_buffered_fill_task_error(task: "asyncio.Task") -> None:
        """record_order 가 띄운 버퍼 처리 태스크의 침묵 실패를 로그로 드러낸다."""
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "Buffered-fill processing task failed after record_order: %r",
                error, exc_info=error,
            )

    async def _process_buffered_fill(self, order_no: str, order_date: str) -> None:
        """Process all buffered partial fills after recording their order.

        버퍼에 있는 체결의 order_date 와 방금 기록한 주문의 order_date 는 출처가 달라
        하루 갈릴 수 있다(양방향 모두 — 자정 관통이면 주문이 하루 앞서고, LS 야간 세션
        영업일 파일링이면 주문이 하루 뒤다). 그래서 정확일치 먼저, 실패하면 **D±1** 후보를
        추가로 본다. 날짜가 갈린 후보는 _is_workflow_fill 로 창 수용 조건을 전부 다시
        확인한다. 모듈 상단 규약 참조.
        """
        notifications: list = []
        async with self._buffer_lock:
            for key, fill in list(self._pending_fills.items()):
                same_date = fill.order_date == order_date
                if not same_date and order_date not in self._order_date_window(fill.order_date):
                    continue
                matches = fill.order_no == order_no
                if self._normalize_identifier(fill.execution_id) is not None:
                    matches = self._normalize_identifier(fill.order_no) == self._normalize_identifier(order_no)
                if not matches:
                    continue
                if not same_date and not self._is_workflow_fill(fill):
                    # 날짜가 갈린 후보는 원장을 다시 조회해 창 수용 조건(후보 1건 + 종목/
                    # 매매구분 일치 + 사람 매체코드 아님 + 시각 근접)을 전부 확인한다 —
                    # 하나라도 어긋나면 여기서 거부되고, 기존대로 타임아웃 경로
                    # (unknown_api)로 간다.
                    continue
                await self._process_fill_internal(fill, "workflow", notifications)
                self._pending_fills.pop(key)
        await self._emit_fill_notifications(notifications)
    
    async def record_fill(
        self,
        order_no: str,
        order_date: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        price: float,
        fill_time: str,
        commda_code: str,
        *,
        execution_id: Optional[str | int] = None,
        account_avg_price: Optional[float] = None,
    ) -> str:
        """
        체결 기록 및 FIFO 처리
        
        체결 이벤트 수신 시 호출합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            symbol: 종목코드
            exchange: 거래소
            side: 매매구분 ("buy" | "sell")
            quantity: 수량
            price: 체결가
            fill_time: 체결시각 (HHMMSSsss)
            commda_code: 매체구분코드 (40=OPEN API). 프레임에서 온 값을 그대로
                받는다 — 우리 주문과 일치하면 매체코드와 무관하게 workflow 로,
                일치하지 않는 fill 만 매체코드로 manual(HTS)/unknown_api 를 가른다.
            account_avg_price: Optional account average purchase price for this
                symbol at fill time. Only a workflow sell whose own lots run out
                uses it, to estimate the residual tail. None → no estimate.
            execution_id: Optional broker execution identity. Positive numeric
                strings/integers ignore padding; opaque strings retain case.
                None, blank, and zero mean no identity and retain legacy replay
                behavior. Numeric floats/negative IDs are rejected. Never derive
                this value from order IDs, timestamps, quantities, or prices.

        Explicit identity is scoped to this ledger, product, provider, mode,
        order date and normalized order number. Exact replay returns the first
        stored classification without mutating FIFO/history. Changed symbol,
        exchange, side, quantity, price, fill time or source code raises
        ExecutionIdentityConflictError. Callers must supply consistent broker
        timestamp/field semantics; no timestamp or currency inference occurs.
        This is a persistence prerequisite, not broker-history/TC3 integration.
            
        Returns:
            분류 결과: "workflow" | "manual" | "unknown_api" | "other" | "pending"
        """
        fill = PendingFill(
            order_no=order_no, order_date=order_date, symbol=symbol,
            exchange=exchange, side=side, quantity=quantity, price=price,
            fill_time=fill_time, commda_code=commda_code, received_at=datetime.now(),
            execution_id=execution_id, account_avg_price=account_avg_price,
        )
        identity = self._execution_key(fill)
        notifications: list = []
        result: Optional[str] = None
        async with self._buffer_lock:
            if identity is not None:
                for pending in self._pending_fills.values():
                    if self._execution_key(pending) == identity:
                        self._assert_same_execution(pending, fill)
                        return "pending"
                with sqlite3.connect(self.db_path) as conn:
                    previous = self._find_execution(conn.cursor(), fill)
                if previous is not None:
                    return previous

            # A fill that matches one of our recorded workflow orders is ours,
            # whatever communication-media code the broker stamped on it — the
            # recorded order is the authoritative ownership signal, so it is
            # checked first. (Now that the real media code is forwarded instead
            # of a hardcoded '40', our own OPEN-API fills may not carry '40'; the
            # old media-first ordering would then misfile them as manual.)
            if self._is_workflow_fill(fill):
                result = await self._process_fill_internal(fill, "workflow", notifications)
            else:
                # No matching order. Classify by the published media table
                # (MEDIA_CODES_* above — one table for every product), never by
                # "not 40":
                #   human (85·60 HTS / 22·23 앱 / 50 MTS / 00 지점 / 51·03 실측) → "manual"
                #   other (96/LP/SK/SO or unlisted)                             → "other"
                #   api (40/41/43) or blank                                     → buffer below
                channel = media_channel(commda_code)
                if channel == "human":
                    result = await self._process_fill_internal(fill, "manual", notifications)
                elif channel == "other":
                    # A code the table does not attribute — more of these exist than
                    # we have measured (only 40/51/85/03 are live-observed so far).
                    # Log it so the table can grow from evidence, never from guesses.
                    logger.info("Unlisted media code %r on fill %s/%s — classified other",
                                commda_code, order_date, order_no)
                    result = await self._process_fill_internal(fill, "other", notifications)
                else:
                    # An API code or an empty media code ("medium unknown"): buffer to
                    # give a lagging order record a chance to arrive, then
                    # _process_timeout_fill files it as workflow (matched) or unknown_api
                    # (unmatched). An unknown medium is never asserted to be a person's
                    # HTS trade, so it floors to unknown_api rather than manual.
                    self._next_pending_fill += 1
                    key = self._next_pending_fill
                    self._pending_fills[key] = fill
        # Emit any confirmed-fill notifications now that _buffer_lock is released.
        if result is not None:
            await self._emit_fill_notifications(notifications)
            return result
        asyncio.create_task(self._process_timeout_fill(key))
        logger.debug(f"Buffered fill (waiting for order): {key}")
        return "pending"

    async def _process_timeout_fill(self, key: int) -> None:
        """Expire one arrival, without consuming a later partial's timeout."""
        await asyncio.sleep(self.FILL_BUFFER_TIMEOUT)
        notifications: list = []
        async with self._buffer_lock:
            if key in self._pending_fills:
                fill = self._pending_fills[key]
                classification = "workflow" if self._is_workflow_fill(fill) else "unknown_api"
                if classification == "unknown_api":
                    logger.warning("Fill expired before its order was recorded; classifying as unknown_api")
                await self._process_fill_internal(fill, classification, notifications)
                self._pending_fills.pop(key)
        await self._emit_fill_notifications(notifications)

    @staticmethod
    def _normalize_identifier(value: Optional[str | int]) -> Optional[str]:
        """Normalize proven IDs only; never invent an ID for missing/zero data."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ExecutionIdentityError("Execution/order identity must be a string or integer")
        text = str(value).strip()
        if not text:
            return None
        if re.fullmatch(r"[0-9]+", text):
            return text.lstrip("0") or None
        if re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", text):
            raise ExecutionIdentityError("Numeric execution/order identity must be a positive integer")
        return text

    def _execution_key(self, fill: PendingFill) -> Optional[Tuple[str, ...]]:
        execution_id = self._normalize_identifier(fill.execution_id)
        if execution_id is None:
            return None
        order_no = self._normalize_identifier(fill.order_no)
        if order_no is None or not fill.order_date:
            raise ExecutionIdentityError("Explicit execution identity requires an order number and date")
        return (self.product, self.provider, self.trading_mode, fill.order_date, order_no, execution_id)

    @staticmethod
    def _execution_facts(fill: PendingFill) -> Dict[str, Any]:
        # Decimal equality avoids false conflicts for quantity/price formatting,
        # while the first supplied values are retained in execution_payload.
        quantity, price = Decimal(str(fill.quantity)), Decimal(str(fill.price))
        if not quantity.is_finite() or not price.is_finite():
            # 🔴 일부러 **plain ValueError** 다 — ExecutionIdentityError 가 아니다.
            # 이건 identity 축이 아니라 체결 사실(수량/가격)이 inf·nan 이라는
            # 뜻이고, 체결번호를 떼고 다시 넣는다고 나아지지 않는다. 전용 타입으로
            # 올리면 context.record_workflow_fill 의 폴백이 이걸 삼켜
            # **체결번호 없이 비유한 값을 원장에 기록**한다. 타입을 바꾸지 말 것.
            raise ValueError("Explicit execution quantity and price must be finite")
        return {
            "symbol": fill.symbol, "exchange": fill.exchange, "side": fill.side,
            "quantity": quantity, "price": price, "fill_time": fill.fill_time,
            "commda_code": fill.commda_code,
        }

    def _assert_same_execution(self, previous: PendingFill, fill: PendingFill) -> None:
        if self._execution_facts(previous) != self._execution_facts(fill):
            raise ExecutionIdentityConflictError("Conflicting fill facts for an existing execution identity")

    def _find_execution(self, cursor: sqlite3.Cursor, fill: PendingFill) -> Optional[str]:
        identity = self._execution_key(fill)
        if identity is None:
            return None
        facts = self._execution_facts(fill)
        cursor.execute("""
            SELECT classification, execution_payload FROM trade_history
            WHERE product = ? AND provider = ? AND trading_mode = ?
              AND order_date = ? AND normalized_order_no = ? AND execution_id = ?
        """, identity)
        row = cursor.fetchone()
        if row is None:
            return None
        stored = json.loads(row[1])
        stored.pop("reported_execution_id")
        stored["quantity"] = Decimal(stored["quantity"])
        stored["price"] = Decimal(stored["price"])
        if stored != facts:
            raise ExecutionIdentityConflictError("Conflicting fill facts for an existing execution identity")
        return row[0]

    def _is_workflow_fill(self, fill: PendingFill) -> bool:
        """이 체결이 우리가 기록한 워크플로우 주문의 체결인가.

        주문번호 대조 방식은 종전 그대로다 — 명시 체결번호가 있으면 정규화된 주문번호로,
        없으면 문자열 정확일치로 본다. 날짜는 정확일치 → D±1 창이고, 창 경로는 이 체결의
        종목·매매구분·매체코드·수량·수신 시각까지 대조한 뒤에만 수용한다. 모듈 상단 규약
        참조.
        """
        identity = self._execution_key(fill)
        if identity is None:
            return self._check_workflow_order(
                fill.order_no, fill.order_date,
                symbol=fill.symbol, side=fill.side,
                commda_code=fill.commda_code, received_at=fill.received_at,
                quantity=fill.quantity,
            )
        return self._match_workflow_order(
            identity[4], fill.order_date, mode="normalized",
            symbol=fill.symbol, side=fill.side,
            commda_code=fill.commda_code, received_at=fill.received_at,
            quantity=fill.quantity,
        ) is not None

    async def _process_fill_internal(
        self, fill: PendingFill, classification: str, notifications: list
    ) -> str:
        """Gate explicit replay before atomically mutating FIFO and history.

        A newly confirmed fill is *queued* into ``notifications`` (a caller-owned
        list) instead of being emitted here — the caller emits it via
        ``_emit_fill_notifications`` AFTER releasing ``_buffer_lock``. Emitting
        under the lock would await the listener chain (a network POST in the
        pg-worker forwarder, ``request_timeout`` seconds) while holding
        ``_buffer_lock``, serializing every other broker fill push behind it.
        Replays return early and queue nothing (no re-fire)."""
        fill_datetime = f"{fill.order_date}_{fill.fill_time}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            previous = self._find_execution(cursor, fill)
            if previous is not None:
                return previous
            identity = self._execution_key(fill)
            payload = None
            if identity is not None:
                facts = self._execution_facts(fill)
                payload = json.dumps({
                    **facts, "quantity": str(fill.quantity), "price": str(fill.price),
                    "reported_execution_id": fill.execution_id,
                }, sort_keys=True)
            realized_pnl = 0.0
            estimate = None

            if fill.side == "buy":
                # 매수: 새 로트 생성
                cursor.execute("""
                    INSERT INTO workflow_position_lots
                    (product, provider, symbol, exchange, fill_datetime, buy_price, original_qty, remaining_qty,
                     classification, order_no, order_date, trading_mode, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.product, self.provider,
                    fill.symbol, fill.exchange, fill_datetime, fill.price,
                    fill.quantity, fill.quantity, classification,
                    fill.order_no, fill.order_date, self.trading_mode, datetime.now().isoformat()
                ))
            else:
                # 매도: FIFO 청산 (현재 trading_mode 내에서만)
                realized_pnl, estimate = self._process_sell_fifo(
                    cursor, fill.symbol, fill.quantity, fill.price, classification,
                    account_avg_price=fill.account_avg_price,
                )

            # 체결 내역 저장
            cursor.execute("""
                INSERT INTO trade_history
                (product, provider, order_no, order_date, symbol, exchange, side, quantity, price,
                 fill_datetime, classification, commda_code, realized_pnl, trading_mode, created_at,
                 execution_id, normalized_order_no, execution_payload,
                 unmatched_qty, estimate_basis_price, estimate_source, estimated_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.product, self.provider,
                fill.order_no, fill.order_date, fill.symbol, fill.exchange,
                fill.side, fill.quantity, fill.price, fill_datetime,
                classification, fill.commda_code, realized_pnl, self.trading_mode, datetime.now().isoformat(),
                identity[5] if identity else None, identity[4] if identity else None, payload,
                estimate["unmatched_qty"] if estimate else None,
                estimate["estimate_basis_price"] if estimate else None,
                estimate["estimate_source"] if estimate else None,
                estimate["estimated_pnl"] if estimate else None,
            ))

            conn.commit()

        # 원장이 실제로 바뀌었다 — 이 값을 캐시 키에 실은 소비자는 다음 읽기에서
        # 반드시 다시 계산한다.
        self.fill_revision += 1

        logger.debug(f"Processed fill: {fill.symbol} {fill.side} {fill.quantity}@{fill.price} [{classification}] ({self.trading_mode})")

        # 새 체결이 원장에 확정됐다 → on_order_fill 통지를 큐잉한다(1회 발화).
        # 실제 emit 은 caller 가 _buffer_lock 을 놓은 뒤 _emit_fill_notifications
        # 로 수행한다(락 안에서 리스너 network POST 를 await 하지 않기 위함).
        # 리플레이는 위에서 previous 반환으로 이미 걸러졌으므로 여기 오지 않는다.
        if self._on_fill_classified is not None:
            notifications.append((fill, classification))

        return classification

    async def _emit_fill_notifications(self, notifications: list) -> None:
        """Emit queued on_order_fill notifications OUTSIDE ``_buffer_lock``.

        Each caller collects confirmed fills into its own list under the lock
        (via ``_process_fill_internal``) and drains them here once the lock is
        released, so a slow listener never blocks other broker fill pushes.
        """
        if self._on_fill_classified is None:
            return
        for fill, classification in notifications:
            try:
                await self._on_fill_classified(fill, classification)
            except Exception as cb_err:
                logger.warning(f"Fill-classified callback error: {cb_err}")

    def _process_sell_fifo(
        self,
        cursor: sqlite3.Cursor,
        symbol: str,
        quantity: int,
        sell_price: float,
        classification: str,
        account_avg_price: Optional[float] = None,
    ) -> Tuple[float, Optional[Dict[str, Any]]]:
        """
        FIFO 매도 처리

        fill_datetime 순으로 정렬하여 선입선출 방식으로 청산합니다.

        classification 이 'workflow' 인 매도는 **workflow 로트만** 소진한다. 수동/타
        API 로트를 먹으면 이 전략이 열지 않은 포지션의 손익까지 실현한 셈이 되기
        때문이다. workflow 로트가 바닥난 뒤 남는 수량(remaining)은 이 전략이 여기서
        사지 않은 물량을 판 것이므로, 계좌 평균매입가(account_avg_price)가 주어지면
        그 잔량을 추정손익으로 매도 행에 기록한다(realized_pnl 은 FIFO 매칭분만 유지).
        non-workflow 매도는 종전과 동일하게 분류 무관 로트를 FIFO 소진한다.

        Args:
            cursor: DB 커서
            symbol: 종목코드
            quantity: 매도 수량
            sell_price: 매도가
            classification: 분류 ("workflow" 면 workflow 로트만 소진)
            account_avg_price: 계좌 평균매입가 (workflow 매도의 잔량 추정용, 없으면 추정 없음)

        Returns:
            (실현 손익 FIFO 매칭분, 추정 정보 dict 또는 None)
        """
        remaining_to_sell = quantity
        total_realized_pnl = 0.0

        # fill_datetime 순으로 정렬 (FIFO, 현재 trading_mode 내에서만).
        # workflow 매도는 workflow 로트로 소진 대상을 좁힌다.
        if classification == "workflow":
            cursor.execute("""
                SELECT id, buy_price, remaining_qty, classification
                FROM workflow_position_lots
                WHERE symbol = ? AND remaining_qty > 0 AND trading_mode = ?
                  AND classification = 'workflow'
                ORDER BY fill_datetime ASC
            """, (symbol, self.trading_mode))
        else:
            cursor.execute("""
                SELECT id, buy_price, remaining_qty, classification
                FROM workflow_position_lots
                WHERE symbol = ? AND remaining_qty > 0 AND trading_mode = ?
                ORDER BY fill_datetime ASC
            """, (symbol, self.trading_mode))

        lots = cursor.fetchall()

        for lot_id, buy_price, remaining_qty, lot_classification in lots:
            if remaining_to_sell <= 0:
                break

            sell_qty = min(remaining_to_sell, remaining_qty)
            new_remaining = remaining_qty - sell_qty

            # 로트 업데이트
            cursor.execute("""
                UPDATE workflow_position_lots
                SET remaining_qty = ?
                WHERE id = ?
            """, (new_remaining, lot_id))

            # 실현 손익 계산
            pnl = (sell_price - buy_price) * sell_qty
            total_realized_pnl += pnl

            remaining_to_sell -= sell_qty

            logger.debug(f"FIFO sell: lot {lot_id} ({lot_classification}), "
                        f"qty={sell_qty}, pnl={pnl:.2f}")

        estimate: Optional[Dict[str, Any]] = None
        if remaining_to_sell > 0:
            if (classification == "workflow" and account_avg_price is not None
                    and account_avg_price > 0):
                # 이 전략이 여기서 사지 않은 잔량 — 같은 종목을 계좌의 다른 경로로
                # 사둔 것으로 보고 계좌 평균매입가 기준 추정손익을 기록한다.
                # realized_pnl(FIFO 매칭분)에는 넣지 않고 별도 컬럼으로만 남긴다.
                estimated_pnl = (sell_price - account_avg_price) * remaining_to_sell
                estimate = {
                    "unmatched_qty": float(remaining_to_sell),
                    "estimate_basis_price": float(account_avg_price),
                    "estimate_source": "account_balance_avg_price",
                    "estimated_pnl": float(estimated_pnl),
                }
                logger.debug(f"Estimated sell tail: {symbol} qty={remaining_to_sell} "
                             f"@avg={account_avg_price} est_pnl={estimated_pnl:.2f}")
            else:
                logger.warning(f"Sell without enough position: {symbol} remaining={remaining_to_sell}")

        return total_realized_pnl, estimate
    
    @staticmethod
    def _order_date_window(order_date: Any) -> List[str]:
        """정확일치가 실패했을 때만 훑는 후보 날짜 — **D-1 과 D+1, 두 칸**.

        두 방향 모두 이 저장소에 근거가 있다(모듈 상단 규약 참조):
        · **D-1** = 실시간 체결 프레임(AS1/SC1)에 주문일자 필드가 없어 **수신 시각의
          로컬 날짜**로 채우기 때문이다(설계상 — executor.py 의 AS1/SC1 경로). 자정 직전
          접수 → 자정 직후 체결이면 주문 기록일이 체결일자보다 하루 앞선다.
        · **D+1** = LS 가 **야간 세션을 전 영업일로 파일링**하기 때문이다(2026-09-10
          실측: 00:39:25 KST 접수(로컬 20260910) → CIDBQ02400 OrdDt/ExecDt 20260909 —
          tests/test_broker_business_date_window.py 헤더). record_order 는 로컬 날짜를
          쓰고 TC3 체결은 프레임의 ordr_dt(브로커 영업일)를 쓰므로, 이때는 주문 기록일이
          체결일자보다 하루 뒤가 된다.
        월말·연말·윤년은 날짜 산술이 알아서 처리한다. 창을 넓힌다고 매칭되는 건 아니다 —
        수용 조건 여섯(_may_widen_for_media + _accept_widened_match)을 모두 통과해야 한다.

        날짜가 비었거나 YYYYMMDD 형식이 아니면 창을 넓히지 않는다 — 근거 없는 매칭을
        만들지 않기 위해서다. 문자열이 아닌 값(None/int/datetime 등)도 같은 경로로
        흡수한다: 예전에는 ``(order_date or "").strip()`` 이 AttributeError 를 던져
        record_fill 을 통째로 죽였다(2026-09-12 검토 지적 B5).
        """
        try:
            base = datetime.strptime(str(order_date or "").strip(), "%Y%m%d")
        except (TypeError, ValueError):
            return []
        return [
            (base - timedelta(days=1)).strftime("%Y%m%d"),
            (base + timedelta(days=1)).strftime("%Y%m%d"),
        ]

    @staticmethod
    def _normalize_symbol(value: Any) -> str:
        """종목 대조용 정규화 — 앞뒤 공백 제거 + 대문자. 비면 빈 문자열."""
        return str(value or "").strip().upper()

    @staticmethod
    def _may_widen_for_media(commda_code: Optional[str]) -> bool:
        """이 매체코드의 체결에 대해 주문일자 창을 넓혀도 되는가.

        창 매칭은 '날짜가 한 칸 어긋났을 것' 이라는 **추론**이다. 프레임이 "이건 사람이
        낸 주문" 이라고 명시한 체결(MEDIA_CODES_HUMAN — 85·60·22·23·50·00·51·03)을 그
        추론으로 삼켜서는 안 된다. 브로커 주문번호는 **영업일마다 리셋**되므로 어제 우리
        번호가 오늘 사용자 HTS 주문에 재발급될 수 있다(2026-09-12 적대적 재검증 실측:
        우리 D-1 AAPL buy #3 → 다음 날 14:00 HTS 매수 7@250, order_no '3', commda '85'
        가 종목·side 까지 같아 workflow 로 흡수).

        **정확일치 경로에는 적용하지 않는다** — 거기선 (주문번호, 주문일자) 동시 일치가
        더 강한 증거이고, 우리 OPEN API 주문이 항상 '40' 을 달고 오지도 않는다.
        blank('unknown')와 미분류('other')는 사람이라고 단정된 적이 없으므로 넓히기를
        막지 않는다.
        """
        return media_channel(commda_code) != "human"

    @staticmethod
    def _naive_local(value: Optional[datetime]) -> Optional[datetime]:
        """tz-aware 든 naive 든 **로컬 naive** 로 맞춘다(간격 계산용).

        원장에 적히는 시각은 ``datetime.now()``(로컬 naive)인데, 호출부가 aware 를 넘길
        수 있다. 섞이면 뺄셈이 TypeError 로 죽으므로 여기서 한쪽으로 모은다.
        """
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone().replace(tzinfo=None)
        return value

    @staticmethod
    def _parse_recorded_timestamp(value: Any) -> Optional[datetime]:
        """원장에 적힌 ISO 시각 문자열을 datetime 으로. 비었거나 해석 불가면 None.

        추론하지 않는다 — 해석 못 하면 None 을 돌려주고, 호출부가 '증거 없음' 으로
        취급한다(창 수용 거부).
        """
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _fill_quantity_within_order(fill_quantity: Any, order_quantity: Any) -> bool:
        """창 수용 조건 ⑤ — 체결 수량이 주문 수량 이하인가(float 비교).

        우리 주문의 체결(부분·전량)은 주문 수량을 넘을 수 없다. 소수점 주식(0.847972 vs
        주문 1)을 위해 float 로 비교한다. 원장 수량이 비었거나 0 이하거나 숫자가 아니면,
        또 체결 수량이 없거나 숫자가 아니거나 유한하지 않으면 **추론 없이 False** —
        호출부가 창 수용을 거부한다. 창 경로 전용이다(정확일치 경로는 타지 않는다).
        """
        try:
            order_qty = float(order_quantity)
            fill_qty = float(fill_quantity)
        except (TypeError, ValueError):
            return False
        if not (math.isfinite(order_qty) and math.isfinite(fill_qty)):
            return False
        if order_qty <= 0:
            return False
        return fill_qty <= order_qty

    def _accept_widened_match(
        self,
        candidates: List[Tuple],
        order_no: str,
        order_date: str,
        symbol: Optional[str],
        side: Optional[str],
        *,
        commda_code: Optional[str] = None,
        received_at: Optional[datetime] = None,
        quantity: Optional[float] = None,
    ) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        """D±1 창의 후보를 수용할지 판정한다. 수용하면 (주문일자, job_id, node_id).

        ① 후보가 **정확히 1건**일 때만 본다. 2건 이상이면(브로커/원장에서 같은 주문번호가
           다시 쓰인 경우) 모호하므로 거부하고 기존대로 미매칭 경로로 보낸다.
        ② 후보의 **종목이 이 체결의 종목과 같아야** 한다. ①은 *우리 원장 안의* 재사용만
           잡는다 — 제3자 주문번호는 정의상 원장에 없어 후보가 늘 1건이고, 종목 대조가
           없으면 번호가 우연히 겹친 남의 체결까지 workflow 로 흡수된다(2026-09-12 검토
           실측: D-1 AAPL buy #86382 뒤 다음 날 TSLA sell commda=85 가 workflow 로 기록).
           한쪽이라도 종목이 비어 있으면 대조 불가이므로 수용하지 않는다.
        ③ 양쪽에 매매구분이 있고 서로 다르면 거부한다(한쪽이 비면 대조하지 않는다).
        ⑤ **수량 상한** — 체결 수량이 후보 주문의 수량(workflow_orders.quantity)을 넘으면
           거부한다(_fill_quantity_within_order). 우리 주문의 체결(부분·전량)은 주문 수량을
           넘을 수 없으므로 우리 체결을 놓치는 일이 없고(false-miss 없음), 세션 시각에
           의존하지 않는다. 브로커 주문번호가 영업일마다 리셋되므로 ①②③④ 를 전부
           통과하는 재발급이 실제로 존재한다(2026-09-12 재검증 실측: 우리 1주 주문 → 남의
           7주 체결) — 그 형태를 여기서 잡는다. 비교는 float 로 한다(소수점 주식 0.847972
           vs 주문 1 → 통과). 원장 수량이 비었거나 0 이거나 숫자가 아니면, 또 체결 수량이
           없으면 **추론 없이 거부**한다.
        ⑥ **시각 근접(보조)** — 주문 기록 시각(workflow_orders.created_at)과 체결 수신 시각
           (PendingFill.received_at)의 간격이 _WIDENED_MATCH_MAX_GAP 이내여야 한다. 이건
           휴리스틱이다 — 미국주식은 KST 주간(09:00~)에도 거래되므로(저장소 메모리 관측
           확정) 다음 날 낮 재발급이 몇 시간 뒤일 수 있어 시각만으로는 못 가른다(상수 정의
           주석 참조). 수량이 우리 주문 이하라 ⑤ 를 통과한 재발급이 임계 밖에서 오면
           여기가 마지막 방어다. created_at 이 비어 있는 옛 행과 수신 시각이 없는 호출은
           **추론 없이 거부**한다.

        (④ 매체코드 가드 _may_widen_for_media 는 창을 조회하기 **전에**
         _match_workflow_order 가 건다 — 사람 채널 체결은 후보를 읽지도 않는다.)
        """
        if len(candidates) != 1:
            if candidates:
                logger.info(
                    "주문일자 ±1일 창 후보가 %d건이라 매칭 거부(주문번호=%s, 체결=%s, 후보=%s)",
                    len(candidates), order_no, order_date,
                    [row[1] for row in candidates],
                )
            return None
        row = candidates[0]
        cand_symbol = self._normalize_symbol(row[2])
        fill_symbol = self._normalize_symbol(symbol)
        if not cand_symbol or not fill_symbol or cand_symbol != fill_symbol:
            logger.info(
                "주문일자 ±1일 창 후보의 종목이 체결과 달라 매칭 거부"
                "(주문번호=%s, 체결=%s, 주문종목=%r, 체결종목=%r)",
                order_no, order_date, row[2], symbol,
            )
            return None
        cand_side = str(row[3] or "").strip().lower()
        fill_side = str(side or "").strip().lower()
        if cand_side and fill_side and cand_side != fill_side:
            logger.info(
                "주문일자 ±1일 창 후보의 매매구분이 체결과 달라 매칭 거부"
                "(주문번호=%s, 체결=%s, 주문=%s, 체결=%s)",
                order_no, order_date, cand_side, fill_side,
            )
            return None
        if not self._fill_quantity_within_order(quantity, row[7]):
            logger.info(
                "주문일자 ±1일 창 후보의 주문 수량을 체결 수량이 넘거나 대조 불가라 매칭 거부"
                "(주문번호=%s, 체결=%s, 주문수량=%r, 체결수량=%r)",
                order_no, order_date, row[7], quantity,
            )
            return None
        ordered_at = self._naive_local(self._parse_recorded_timestamp(row[6]))
        filled_at = self._naive_local(received_at)
        if ordered_at is None or filled_at is None:
            logger.info(
                "주문일자 ±1일 창 수용에 필요한 시각 증거가 없어 매칭 거부"
                "(주문번호=%s, 체결=%s, 주문기록시각=%r, 체결수신시각=%r)",
                order_no, order_date, row[6], received_at,
            )
            return None
        gap = abs(filled_at - ordered_at)
        if gap > _WIDENED_MATCH_MAX_GAP:
            logger.info(
                "주문일자 ±1일 창 후보가 체결과 %s 떨어져 있어 매칭 거부"
                "(임계=%s, 주문번호=%s, 체결=%s)",
                gap, _WIDENED_MATCH_MAX_GAP, order_no, order_date,
            )
            return None
        logger.info("주문일자 ±1일 창에서 매칭됨(D=%s, 체결=%s, 주문번호=%s, 종목=%s, "
                    "체결수량=%r/주문수량=%r, 간격=%s)",
                    row[1], order_date, order_no, cand_symbol, quantity, row[7], gap)
        return (row[1], row[4], row[5])

    def _order_no_matches(
        self,
        target: str,
        target_norm: Optional[str],
        row_value: Any,
        *,
        mode: str,
        strict: bool,
    ) -> bool:
        """저장된 주문번호가 대상 주문번호와 같은가.

        mode (호출부마다 종전 의미를 그대로 유지한다):
          - "exact"               : 문자열 정확일치만 (체결번호 없는 분류 경로)
          - "normalized"          : 0 패딩 정규화 일치만 (명시 체결번호 경로)
          - "exact_or_normalized" : 둘 중 하나 (lookup_order_identity)
        strict=True 에서는 정규화 불가한 저장값이 예외로 올라간다 — 그 날짜의 우리 주문
        기록이 깨졌다는 신호다. 이 의미는 **mode='normalized' 의 정확일치 날짜 조회에만**
        남겨 둔다(통합 전 그 경로가 그렇게 동작했다). 'exact_or_normalized'(조회 경로)는
        통합 전 깨진 행 하나를 ``except ValueError: continue`` 로 건너뛰었으므로 strict=
        False 로 그 행만 건너뛴다 — 안 그러면 깨진 행 하나가 lookup 전체를 죽인다.
        넓힌 창도 strict=False 다(이웃 날짜에 섞인 깨진 값 하나가 멀쩡한 체결 처리를 죽이지
        않게 — 넓히기 전보다 나빠지지 않도록).
        """
        if mode == "exact":
            return row_value == target
        if mode == "exact_or_normalized" and row_value == target:
            return True
        if target_norm is None:
            return False
        try:
            return self._normalize_identifier(row_value) == target_norm
        except ValueError:
            if strict:
                raise
            return False

    def _match_workflow_order(
        self,
        order_no: str,
        order_date: str,
        *,
        mode: str = "exact",
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        commda_code: Optional[str] = None,
        received_at: Optional[datetime] = None,
        quantity: Optional[float] = None,
    ) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        """워크플로우 주문 매칭 — (주문일자, job_id, node_id) 또는 None.

        분류(_is_workflow_fill)와 식별자 조회(lookup_order_identity)가 공유하는 **유일한**
        매칭 경로다. 주문번호 대조 mode 만 호출부마다 다르고(모듈 상단 규약 참조), 날짜
        규약과 창 수용 조건은 공유한다 — 그게 갈리면 classification='workflow' 인데
        node_id 가 None 인 상태가 생긴다.

        1) 같은 order_date 를 **SQL 등가조건(order_no 포함)** 으로 먼저 친다. 체결 핫패스인
           mode='exact' 는 여기서 끝나므로 그 날짜 행을 전부 읽어 파이썬에서 비교하지
           않는다. EXPLAIN QUERY PLAN 실측(2026-09-12): 이 형태는
           ``SEARCH ... USING INDEX sqlite_autoindex_workflow_orders_1 (order_no=? AND
           order_date=?)`` 로 UNIQUE(order_no, order_date) 를 등가 탐색하고, order_date 만
           걸면 ``SEARCH ... USING INDEX idx_orders_lookup_v2 (trading_mode=?)`` 가 되어 그
           모드의 행을 전부 훑는다. 0 패딩 정규화가 필요한 mode 만 **order_date 로 좁힌
           뒤** 파이썬 비교를 추가로 돈다. 이 경로의 의미는 종전 그대로이고 종목/매체/수량/
           시각 대조를 넣지 않는다(국내 SC1 체결 종목코드 'A005930' vs 주문 기록 '005930').
        2) 실패하면 D±1 창을 본다. 단 프레임이 사람 채널이라고 명시한 체결은 후보를
           **조회하지도 않고**(_may_widen_for_media), 나머지는 _accept_widened_match 의
           수용 조건을 모두 통과할 때만 매칭으로 인정한다.

        스코프는 product/provider/trading_mode 다. 통합 전 체결번호 없는 경로는
        trading_mode 로만 좁혔는데, record_order 가 언제나 이 tracker 의 product/provider
        로 행을 쓰므로 실제 매칭 결과는 달라지지 않는다(체결번호 있는 경로는 통합 전에도
        이 스코프였다).
        """
        try:
            target_norm = self._normalize_identifier(order_no)
        except ValueError:
            target_norm = None
        columns = "order_no, order_date, symbol, side, job_id, node_id, created_at, quantity"
        scope = (self.product, self.provider, self.trading_mode)
        with sqlite3.connect(self.db_path) as conn:
            # 1) 정확일치 — UNIQUE(order_no, order_date) 등가 탐색이라 최대 1행.
            hit = conn.execute(
                f"""
                SELECT {columns} FROM workflow_orders
                WHERE product = ? AND provider = ? AND trading_mode = ?
                  AND order_date = ? AND order_no = ?
                """,
                (*scope, order_date, order_no),
            ).fetchone()
            if hit is not None and mode != "normalized":
                # 'exact'/'exact_or_normalized' 는 문자열 정확일치를 그대로 수용한다.
                # 'normalized' 는 정규화 결과로만 판정하므로 아래 루프에 맡긴다
                # (예: 저장값 '000' 은 정규화하면 빈 값이라 매칭이 성립하지 않는다).
                return (hit[1], hit[4], hit[5])
            if mode != "exact":
                rows = conn.execute(
                    f"""
                    SELECT {columns} FROM workflow_orders
                    WHERE product = ? AND provider = ? AND trading_mode = ? AND order_date = ?
                    """,
                    (*scope, order_date),
                ).fetchall()
                for row in rows:
                    if self._order_no_matches(order_no, target_norm, row[0],
                                              mode=mode, strict=(mode == "normalized")):
                        return (row[1], row[4], row[5])

            if not self._may_widen_for_media(commda_code):
                # 사람 매체코드 체결이 우리 주문과 정확일치하지 않는 건 **정상**(사용자가
                # 손으로 낸 주문)이라 debug 다. 아래 거부 로그들(종목/side/시각 불일치)은
                # '거의 맞을 뻔한' 근접 사례라 info 로 남긴다.
                logger.debug(
                    "매체코드 %r 가 사람 채널이라 주문일자 창을 넓히지 않음"
                    "(주문번호=%s, 체결=%s)", commda_code, order_no, order_date,
                )
                return None
            window = self._order_date_window(order_date)
            if not window:
                return None
            rows = conn.execute(
                f"""
                SELECT {columns} FROM workflow_orders
                WHERE product = ? AND provider = ? AND trading_mode = ?
                  AND order_date IN ({",".join("?" * len(window))})
                """,
                (*scope, *window),
            ).fetchall()
        candidates = [row for row in rows
                      if self._order_no_matches(order_no, target_norm, row[0],
                                                mode=mode, strict=False)]
        return self._accept_widened_match(
            candidates, order_no, order_date, symbol, side,
            commda_code=commda_code, received_at=received_at, quantity=quantity,
        )

    def _check_workflow_order(
        self,
        order_no: str,
        order_date: str,
        *,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        commda_code: Optional[str] = None,
        received_at: Optional[datetime] = None,
        quantity: Optional[float] = None,
    ) -> bool:
        """워크플로우 주문 여부 (이 tracker 의 product/provider/trading_mode 기준,
        주문일자 D±1 창 포함).

        symbol/side/commda_code/received_at/quantity 는 넓힌 창에서만 쓰인다 — 없으면 창
        경로는 대조할 게 없어 거부되고 정확일치만 남는다(넓히기 전 동작).
        """
        return self._match_workflow_order(
            order_no, order_date, mode="exact", symbol=symbol, side=side,
            commda_code=commda_code, received_at=received_at, quantity=quantity,
        ) is not None

    def get_workflow_positions(
        self,
        start_date: Optional[str] = None,
    ) -> Dict[str, PositionInfo]:
        """
        현재 워크플로우 포지션 조회 (start_date 필터 지원)
        
        Args:
            start_date: 필터 시작일 (YYYYMMDD), None이면 전체 기간
        
        Returns:
            종목별 워크플로우 포지션 {symbol: PositionInfo}
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 날짜 필터 조건
            date_filter = ""
            params: list = [self.trading_mode]
            if start_date:
                # fill_datetime 형식: YYYYMMDD_HHMMSSsss
                date_filter = " AND fill_datetime >= ?"
                params.append(f"{start_date}_000000000")

            cursor.execute(f"""
                SELECT symbol, exchange, buy_price, remaining_qty, classification
                FROM workflow_position_lots
                WHERE remaining_qty > 0 AND classification = 'workflow' AND trading_mode = ?
                {date_filter}
            """, params)
            
            positions: Dict[str, PositionInfo] = {}
            
            for symbol, exchange, buy_price, remaining_qty, classification in cursor.fetchall():
                # SQLite 가 소수점 체결 lot 을 REAL 로 돌려줄 수 있어 Decimal 로
                # 통일한다 (Decimal * float 는 TypeError).
                lot_qty = Decimal(str(remaining_qty))
                if symbol in positions:
                    # 같은 종목: 평균단가 재계산
                    pos = positions[symbol]
                    total_qty = pos.quantity + lot_qty
                    total_cost = (pos.avg_price * pos.quantity) + (Decimal(str(buy_price)) * lot_qty)
                    pos.quantity = total_qty
                    pos.avg_price = total_cost / total_qty
                else:
                    positions[symbol] = PositionInfo(
                        symbol=symbol,
                        exchange=exchange or "",
                        quantity=lot_qty,
                        avg_price=Decimal(str(buy_price)),
                        classification=classification,
                    )
            
            return positions
    
    def get_other_positions(
        self,
        all_positions: Dict[str, Any],
    ) -> Dict[str, PositionInfo]:
        """
        워크플로우 제외 포지션 조회
        
        Args:
            all_positions: 전체 보유 포지션 (브로커 API에서 조회)
            
        Returns:
            워크플로우 제외 포지션 {symbol: PositionInfo}
        """
        workflow_positions = self.get_workflow_positions()
        other_positions: Dict[str, PositionInfo] = {}
        
        for symbol, pos_data in all_positions.items():
            total_qty = Decimal(str(pos_data.get("quantity", 0) or pos_data.get("qty", 0) or 0))
            avg_price = pos_data.get("avg_price", 0) or pos_data.get("buy_price", 0)
            exchange = pos_data.get("exchange", "")

            workflow_qty = workflow_positions.get(symbol, PositionInfo(symbol, "", Decimal(0), Decimal(0), "")).quantity
            other_qty = total_qty - workflow_qty
            
            if other_qty > 0:
                other_positions[symbol] = PositionInfo(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=other_qty,
                    avg_price=Decimal(str(avg_price)),
                    classification="other",
                )
        
        return other_positions
    
    def _infer_multipliers(
        self,
        all_positions: Dict[str, Any],
        prices: Dict[str, Decimal],
    ) -> Dict[str, Tuple[Decimal, Decimal]]:
        """브로커 스냅샷에서 심볼별 ``(계약 승수, 방향 부호)`` 를 역산한다.

        선물 평가손익은 ``mult × side_sign × qty × (현재가 − 평단)`` 이므로
        (side_sign: long=+1, short=−1), 브로커가 실은 승수 반영 ``pnl_amount`` 에서:

            mult = pnl_amount / ((current − avg) × qty × side_sign)

        - side_sign 은 스냅샷 방향 라벨(``direction`` 또는 ``side``)에서 항상 얻는다
          (역산 성공 여부와 무관). 호출부는 이 부호로 FIFO 롱-only 산식의 pnl 부호를
          보정한다 → 숏도 올바른 부호.
        - mult(양수 크기)는 아래 가드를 모두 통과할 때만 채택하고, 실패 시 심볼별
          최근 성공값 캐시(없으면 1.0)로 폴백한다:
            · pnl_amount 없/0(placeholder) → 역산 생략
            · |현재가−평단|/평단 < _MULT_MIN_REL_GAP → 분모가 작아 불안정 → 생략
            · mult 이 [_MULT_MIN, _MULT_MAX] 밖 → 거부 (라벨 오류로 부호가 뒤집혀
              음수가 나오는 경우도 여기서 거부됨)
            · 최근접 정수와 상대오차 ≤ _MULT_INT_SNAP_REL → 정수로 스냅
        주식(승수 1)은 자연히 1.0 으로 역산된다.
        """
        result: Dict[str, Tuple[Decimal, Decimal]] = {}
        for symbol, pos_data in (all_positions or {}).items():
            if not isinstance(pos_data, dict):
                continue

            # 방향 부호는 라벨에서 항상 결정 (역산 실패해도 유지)
            direction = str(
                pos_data.get("direction") or pos_data.get("side") or "long"
            ).lower()
            side_sign = Decimal(-1) if direction.startswith("short") else Decimal(1)

            mult: Optional[Decimal] = None
            pnl_raw = pos_data.get("pnl_amount")
            # 명시적 0.0 은 여러 빌더가 넣는 placeholder 이므로 역산에서 제외.
            if pnl_raw:
                try:
                    pnl_amount = Decimal(str(pnl_raw))
                    qty = pos_data.get("quantity", 0) or pos_data.get("qty", 0)
                    avg_raw = pos_data.get("avg_price", 0) or pos_data.get("buy_price", 0)
                    cur = prices.get(symbol)
                    if cur is None:
                        cur_raw = pos_data.get("current_price")
                        cur = Decimal(str(cur_raw)) if cur_raw is not None else None
                    if cur is not None and qty:
                        avg_d = Decimal(str(avg_raw))
                        qty_d = Decimal(str(qty))
                        cur_d = cur if isinstance(cur, Decimal) else Decimal(str(cur))
                        if avg_d > 0:
                            rel_gap = abs(cur_d - avg_d) / avg_d
                            if rel_gap >= _MULT_MIN_REL_GAP:
                                denom = (cur_d - avg_d) * qty_d * side_sign
                                if denom != 0:
                                    cand = pnl_amount / denom
                                    if _MULT_MIN <= cand <= _MULT_MAX:
                                        # 정수 근사 스냅 (선물 승수는 정수 관행)
                                        nearest = cand.to_integral_value(rounding=ROUND_HALF_UP)
                                        if nearest >= 1 and abs(cand - nearest) / nearest <= _MULT_INT_SNAP_REL:
                                            cand = Decimal(nearest)
                                        mult = cand
                                        self._multiplier_cache[symbol] = cand
                except (TypeError, ValueError, ArithmeticError):
                    pass  # 역산 실패 → 캐시/기본 폴백

            if mult is None:
                mult = self._multiplier_cache.get(symbol, Decimal(1))
            result[symbol] = (mult, side_sign)
        return result

    def calculate_pnl(
        self,
        current_prices: Dict[str, Any],  # Decimal 또는 float
        all_positions: Dict[str, Any],
        currency: str = "USD",
        start_date: Optional[str] = None,  # YYYYMMDD 필터
    ) -> Dict[str, Any]:
        """
        실시간 평가 수익률 계산

        Args:
            current_prices: 현재가 {symbol: price} (Decimal 또는 float)
            all_positions: 전체 보유 포지션
            currency: 통화
            start_date: 필터 시작일 (YYYYMMDD), None이면 전체 기간

        Returns:
            WorkflowPnLEvent 생성에 필요한 데이터 dict
        """
        from programgarden_core.bases import PositionDetail

        # float를 Decimal로 변환
        prices = {
            symbol: Decimal(str(price)) if not isinstance(price, Decimal) else price
            for symbol, price in current_prices.items()
        }

        # 브로커 스냅샷에서 심볼별 계약 승수 역산. FIFO lot 산술은 승수를 모르므로
        # (eval/buy/pnl 금액이 선물에서 1/N 로 축소) 여기서 얻은 승수로 스케일한다.
        # pnl_rate 는 eval/buy 비율이라 승수가 소거돼 영향 없음.
        multipliers = self._infer_multipliers(all_positions, prices)

        workflow_positions = self.get_workflow_positions(start_date=start_date)
        other_positions = self.get_other_positions(all_positions)

        # 워크플로우 포지션 계산.
        # eval/buy 는 양수 명목가(승수 스케일)로 유지하고, pnl 은 side_sign 으로
        # 부호를 보정해 별도 누적한다(FIFO 는 롱-only 산식이라 숏이면 eval−buy 의
        # 부호가 뒤집혀 있음). 롱은 side_sign=+1 이라 기존과 동일.
        wf_eval = Decimal(0)
        wf_buy = Decimal(0)
        wf_pnl = Decimal(0)
        wf_details: List[PositionDetail] = []
        # 증거 카운터 — 비율을 **발행해도 되는지** 를 결정한다(금액은 영향 없음).
        wf_unpriced = 0   # 현재가를 관측하지 못해 평단으로 대체한 종목 수
        wf_unbased = 0    # 평단이 0 이하라 매수근거가 없는 종목 수

        for symbol, pos in workflow_positions.items():
            observed_price = prices.get(symbol)
            if observed_price is None or observed_price <= 0:
                wf_unpriced += 1
            if pos.avg_price <= 0:
                wf_unbased += 1
            # 🔴 금액 계산은 **현행 그대로** 둔다(평단 폴백 포함) — 금액을 비우면 모니터링
            # KPI 합산이 통째로 접히고, 전량 청산한 날의 0 은 진짜 0 이다.
            # 달라지는 것은 "그 금액으로 비율을 발행할 자격이 있는가" 뿐이다.
            current_price = observed_price if (observed_price and observed_price > 0) else pos.avg_price
            mult, side_sign = multipliers.get(symbol, (Decimal(1), Decimal(1)))
            eval_amount = current_price * pos.quantity * mult
            buy_amount = pos.avg_price * pos.quantity * mult
            pnl_amount = (eval_amount - buy_amount) * side_sign
            pnl_rate = (pnl_amount / buy_amount * 100) if buy_amount else Decimal(0)

            wf_eval += eval_amount
            wf_buy += buy_amount
            wf_pnl += pnl_amount

            wf_details.append(PositionDetail(
                symbol=symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=current_price,
                pnl_amount=pnl_amount,
                pnl_rate=pnl_rate,
            ))

        # 🔴 계산할 수 없으면 0 이 아니라 **아무것도 발행하지 않는다**(None).
        #
        # 종전 `else Decimal(0)` 는 "아무것도 안 샀다" 를 **"0% 로 측정됐다"** 로 바꿔 발행했다.
        # 그러면 워크플로우를 시작만 해도 스냅샷이 생겨 공유 카드가 「참고 데이터」 배지 달린
        # 정직한 0.0% 에서 **배지 없는 "실측 0.0%"** 로 바뀐다(승률 0%·손익비 0.00 까지).
        # 선물은 이미 이 원칙으로 고쳐져 있다(`futures_pnl.unavailable_workflow_pnl`) —
        # 주식만 안 따라갔다.
        #
        # 한 종목이라도 현재가를 못 봤거나(`wf_unpriced`) 평단이 없으면(`wf_unbased`)
        # 합계 비율이 **부풀려진다**(분모만 줄거나 평가액이 매수액으로 눌린다). 그건 0 이
        # 아닌 채로 틀리므로 값 자체를 내지 않는다.
        wf_rate_reason: Optional[str] = None
        if not workflow_positions:
            wf_rate_reason = "no_workflow_positions"
        elif wf_unbased:
            wf_rate_reason = "basis_unreported"
        elif wf_unpriced:
            wf_rate_reason = "price_unreported"
        elif not wf_buy:
            wf_rate_reason = "no_workflow_positions"
        wf_rate = None if wf_rate_reason else (wf_pnl / wf_buy * 100)

        # 그 외 포지션 계산
        other_eval = Decimal(0)
        other_buy = Decimal(0)
        other_pnl = Decimal(0)
        other_details: List[PositionDetail] = []
        other_unpriced = 0
        other_unbased = 0

        for symbol, pos in other_positions.items():
            observed_price = prices.get(symbol)
            if observed_price is None or observed_price <= 0:
                other_unpriced += 1
            if pos.avg_price <= 0:
                other_unbased += 1
            current_price = observed_price if (observed_price and observed_price > 0) else pos.avg_price
            mult, side_sign = multipliers.get(symbol, (Decimal(1), Decimal(1)))
            eval_amount = current_price * pos.quantity * mult
            buy_amount = pos.avg_price * pos.quantity * mult
            pnl_amount = (eval_amount - buy_amount) * side_sign
            pnl_rate = (pnl_amount / buy_amount * 100) if buy_amount else Decimal(0)

            other_eval += eval_amount
            other_buy += buy_amount
            other_pnl += pnl_amount

            other_details.append(PositionDetail(
                symbol=symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=current_price,
                pnl_amount=pnl_amount,
                pnl_rate=pnl_rate,
            ))

        # wf_rate 와 같은 규율 — 근거가 없으면 비율을 발행하지 않는다.
        other_rate = (
            None
            if (not other_positions or other_unbased or other_unpriced or not other_buy)
            else (other_pnl / other_buy * 100)
        )

        # 전체 계산 — pnl 은 부호 보정된 per-position 합, eval/buy 는 명목가 합.
        total_eval = wf_eval + other_eval
        total_buy = wf_buy + other_buy
        total_pnl = wf_pnl + other_pnl
        # 전체 비율은 **양쪽 다 증거가 성립할 때만** 낸다. 한쪽이 모름이면 합계도 모름이다
        # (모르는 쪽을 0 으로 치고 더하면 없는 정확도를 만들어낸다).
        total_unpriced = wf_unpriced + other_unpriced
        total_unbased = wf_unbased + other_unbased
        total_rate = (
            None
            if (not total_buy or total_unbased or total_unpriced)
            else (total_pnl / total_buy * 100)
        )
        
        # 신뢰도 계산
        anomalies = self.detect_anomalies()
        trust_score = self.calculate_trust_score(anomalies)
        
        return {
            "job_id": self.job_id,
            "broker_node_id": self.broker_node_id,
            "product": self.product,
            
            "workflow_pnl_rate": wf_rate,
            # 비율을 못 낸 **이유**. 값을 비우는 것만으로는 "안 샀다" 와 "증권사가 평단을
            # 안 보냈다" 가 구분되지 않는다 — 서버는 이 사유를 raw_event 에 그대로 싣는다.
            # 어휘는 dsl-api `app/utils/pnl_rate_evidence.RATE_UNAVAILABLE_REASONS` 와 공용.
            "workflow_rate_unavailable_reason": wf_rate_reason,
            "workflow_eval_amount": wf_eval,
            "workflow_buy_amount": wf_buy,
            "workflow_pnl_amount": wf_pnl,
            
            "other_pnl_rate": other_rate,
            "other_eval_amount": other_eval,
            "other_buy_amount": other_buy,
            "other_pnl_amount": other_pnl,
            
            "total_pnl_rate": total_rate,
            "total_eval_amount": total_eval,
            "total_buy_amount": total_buy,
            "total_pnl_amount": total_pnl,
            
            "workflow_positions": wf_details,
            "other_positions": other_details,
            
            "trust_score": trust_score,
            "anomaly_count": len(anomalies),
            
            "currency": currency,
            "timestamp": datetime.now(),
        }

    def personal_metrics(self) -> Dict[str, Any]:
        """Read retained workflow executions without claiming account performance.

        Historical FIFO rows have no currency or fee evidence. Keep their amounts
        per symbol/exchange and reject mixed ownership or an incomplete FIFO basis.
        Futures FIFO is not a monetary ledger. No equity/MDD basis is inferred.

        Version 2 adds closed-trade outcomes. One closed trade = one sell fill,
        using its *stored* realized amount — the replay below only validates the
        basis and never replaces a stored value, so the outcome is read from the
        same number the ledger committed.

        A workflow sell now consumes only workflow lots (_process_sell_fifo), so
        the old ``mixed_fifo_ownership`` pre-check is gone: a workflow sell can
        no longer have realized a non-workflow lot, so there is nothing to guard
        against. Old ledger rows written under the previous (classification-blind)
        sell replay with ``stored != expected`` and are rejected below as
        ``incomplete_fifo_basis`` — the honest outcome for a basis we can no
        longer reconstruct.

        A workflow sell whose own lots run out leaves a residual. When that
        residual was recorded with an account-average-price estimate covering
        exactly it (``estimate_basis_price`` present and ``unmatched_qty`` equal
        to the residual), the group is not rejected: its status becomes
        ``estimated``, its basis ``fifo_with_account_avg_price_estimate``, and
        the sell scores on ``stored + estimated_pnl`` (the FIFO-matched amount
        plus the estimated tail). Any other residual is an incomplete basis.

        Counts aggregate across symbols because a count carries no currency.
        Amounts do not: with `currency` unproven per row, summing gross profit
        across symbols would invent the very unit this method refuses to claim.
        So gross amounts stay inside each group, and the top-level profit/loss
        ratio is published only when a single group carries the whole ledger —
        the one case where "the currency is the same" needs no evidence.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(
                "SELECT * FROM trade_history WHERE trading_mode=? ORDER BY id",
                (self.trading_mode,),
            )]
        selected = [row for row in rows if row["product"] == self.product
                    and row["provider"] == self.provider and row["classification"] == "workflow"]
        keys = set()
        invalid_count = False
        groups: Dict[Tuple[str, str], List[dict]] = {}
        for row in selected:
            try:
                quantity = Decimal(str(row["quantity"]))
                if not quantity.is_finite() or quantity < 0:
                    raise ValueError("Invalid execution quantity")
                if quantity == 0:
                    continue
                order_date = row["order_date"]
                if not isinstance(order_date, str) or not re.fullmatch(r"[0-9]{8}", order_date):
                    raise ValueError("Missing order date")
                datetime.strptime(order_date, "%Y%m%d")
                order_no = self._normalize_identifier(row["order_no"])
                if order_no is None:
                    raise ValueError("Missing order number")
                keys.add((order_date, order_no))
            except (ValueError, TypeError, ArithmeticError):
                invalid_count = True
            key = (row["symbol"] or "", row["exchange"] or "")
            groups.setdefault(key, []).append(row)

        realized = []
        for (symbol, exchange), fills in sorted(groups.items()):
            reason = None
            amount = None
            outcome = None
            # Whether this group's amount includes an account-avg-price estimate,
            # and how much quantity was estimated (Σ unmatched over its sells).
            group_estimated = False
            group_est_qty = Decimal(0)
            if self.product == "overseas_futures":
                reason = "futures_fifo_not_monetary"
            elif not symbol:
                reason = "missing_symbol"
            else:
                # The old mixed_fifo_ownership pre-check is gone: a workflow sell
                # now consumes only workflow lots, so it can never have realized a
                # non-workflow lot. Old rows written under the previous replay
                # fall out below as incomplete_fifo_basis (stored != expected).
                try:
                    lots = []
                    total = Decimal(0)
                    # NB: `closed` below is the matched lot quantity — do not
                    # reuse that name for a counter.
                    trades = wins = losses = evens = 0
                    gross_profit = Decimal(0)
                    gross_loss = Decimal(0)
                    for fill in fills:
                        quantity = Decimal(str(fill["quantity"]))
                        price = Decimal(str(fill["price"]))
                        stored = Decimal(str(fill["realized_pnl"]))
                        if not all(value.is_finite() for value in (quantity, price, stored)) or quantity <= 0:
                            raise ValueError("Invalid stored fill")
                        if fill["side"] == "buy":
                            if stored != 0:
                                raise ValueError("Unexpected opening PnL")
                            lots.append([fill["fill_datetime"] or "", fill["id"], quantity, price])
                            lots.sort(key=lambda lot: (lot[0], lot[1]))
                        elif fill["side"] == "sell":
                            remaining = quantity
                            expected = Decimal(0)
                            for lot in lots:
                                closed = min(remaining, lot[2])
                                expected += (price - lot[3]) * closed
                                lot[2] -= closed
                                remaining -= closed
                                if remaining == 0:
                                    break
                            tolerance = max(Decimal("0.000001"), abs(expected) * Decimal("0.000000001"))
                            # The FIFO-matched portion must reproduce the stored
                            # amount, whether or not a tail remains.
                            if abs(stored - expected) > tolerance:
                                raise ValueError("Inconsistent FIFO basis")
                            # trade_amount is what this one closed trade scores on;
                            # it starts as the stored (matched) value and grows by
                            # the recorded estimate when a tail remains.
                            trade_amount = stored
                            if remaining > 0:
                                # A residual after the workflow lots run out is
                                # accepted only as a recorded account-avg-price
                                # estimate covering exactly this residual; anything
                                # else is an incomplete basis.
                                est_basis = fill["estimate_basis_price"]
                                est_unmatched = fill["unmatched_qty"]
                                est_pnl = fill["estimated_pnl"]
                                if est_basis is None or est_unmatched is None or est_pnl is None:
                                    raise ValueError("Incomplete FIFO basis without estimate")
                                est_unmatched_d = Decimal(str(est_unmatched))
                                est_pnl_d = Decimal(str(est_pnl))
                                if est_unmatched_d != remaining or not est_pnl_d.is_finite():
                                    raise ValueError("Estimate does not cover the residual")
                                # Add (never replace) the stored estimate to the
                                # matched amount; one sell fill is still one trade.
                                trade_amount = stored + est_pnl_d
                                group_estimated = True
                                group_est_qty += remaining
                            total += trade_amount
                            trades += 1
                            if trade_amount > 0:
                                wins += 1
                                gross_profit += trade_amount
                            elif trade_amount < 0:
                                losses += 1
                                gross_loss += -trade_amount
                            else:
                                evens += 1
                        else:
                            raise ValueError("Unknown fill side")
                    amount = float(total)
                    if not Decimal(str(amount)).is_finite():
                        raise ValueError("Non-finite total")
                    gross_profit_f = float(gross_profit)
                    gross_loss_f = float(gross_loss)
                    if not all(Decimal(str(v)).is_finite() for v in (gross_profit_f, gross_loss_f)):
                        raise ValueError("Non-finite gross amount")
                    outcome = {"closed_trades": trades, "winning_trades": wins,
                               "losing_trades": losses, "breakeven_trades": evens,
                               "gross_profit": gross_profit_f, "gross_loss": gross_loss_f}
                except (ValueError, TypeError, ArithmeticError, OverflowError):
                    reason = "incomplete_fifo_basis"
                    outcome = None
                    group_estimated = False
                    group_est_qty = Decimal(0)
            if reason is not None:
                status = "unavailable"
                basis = None
                estimated_quantity = None
            elif group_estimated:
                status = "estimated"
                basis = "fifo_with_account_avg_price_estimate"
                estimated_quantity = float(group_est_qty)
            else:
                status = "available"
                basis = "fifo"
                estimated_quantity = 0
            entry = {"symbol": symbol, "exchange": exchange, "currency": None,
                     "amount": amount, "status": status, "reason": reason,
                     "basis": basis, "estimated_quantity": estimated_quantity}
            # A rejected group publishes no outcome: its trades are unknown, and
            # unknown trades must not be counted as zero of anything.
            entry.update(outcome or {"closed_trades": None, "winning_trades": None,
                                     "losing_trades": None, "breakeven_trades": None,
                                     "gross_profit": None, "gross_loss": None})
            realized.append(entry)
        # Counts carry no currency, so they aggregate across symbols. A group the
        # replay rejected is excluded and downgrades the status to "partial" —
        # "some of this strategy's trades are not in these numbers" is a different
        # claim from "these are all of them", and the caller must be able to tell.
        scored = [g for g in realized if g["closed_trades"] is not None]
        counted = [g for g in scored if g["closed_trades"] > 0]
        if not scored:
            trade_status, trade_reason = "unavailable", (
                "futures_fifo_not_monetary" if self.product == "overseas_futures"
                else "no_scorable_fifo_basis")
            closed_total = winning_total = losing_total = breakeven_total = None
        else:
            trade_status = "available" if len(scored) == len(realized) else "partial"
            trade_reason = None if trade_status == "available" else "some_groups_unscorable"
            closed_total = sum(g["closed_trades"] for g in scored)
            winning_total = sum(g["winning_trades"] for g in scored)
            losing_total = sum(g["losing_trades"] for g in scored)
            breakeven_total = sum(g["breakeven_trades"] for g in scored)

        # The ratio is money, and money needs a unit. One group means one symbol,
        # hence one currency — the only case where the unit is provable without
        # currency evidence. Anything else stays per group.
        ratio = None
        ratio_status = "unavailable"
        if len(counted) != 1:
            ratio_reason = ("no_closed_trades" if not counted
                            else "multi_symbol_currency_unknown")
        else:
            group = counted[0]
            if group["gross_loss"] > 0:
                candidate = group["gross_profit"] / group["gross_loss"]
                if Decimal(str(candidate)).is_finite():
                    ratio, ratio_status, ratio_reason = candidate, "available", None
                else:
                    ratio_reason = "non_finite_ratio"
            else:
                # No losing trade means no denominator. Publishing gross profit
                # here (the server's day-based metric does) reads as a ratio of
                # that size and overstates the strategy.
                ratio_reason = "no_losing_trades"

        # How many groups carry an account-avg-price estimate, and whether the
        # aggregated figures rest on any estimate. A count is null when it is
        # itself unavailable; otherwise it is "measured" unless a scored group
        # was estimated. The ratio comes from a single group, so its basis is
        # that one group's.
        estimated_group_count = sum(1 for g in realized if g["status"] == "estimated")
        if trade_status == "unavailable":
            closed_trade_basis = None
        else:
            closed_trade_basis = ("includes_estimates"
                                  if any(g["status"] == "estimated" for g in scored)
                                  else "measured")
        if ratio_status != "available":
            profit_loss_ratio_basis = None
        else:
            profit_loss_ratio_basis = ("includes_estimates"
                                       if counted[0]["status"] == "estimated"
                                       else "measured")

        # Fills on this same account placed outside this strategy, by classification:
        # manual (a person via HTS/app/branch) → hts, unknown_api (another API
        # client) → other_api, other (broker-side codes 96/LP/SK/SO or unlisted)
        # → other. Futures fill frames carry no communication-media field, so
        # the channels cannot be told apart for them — unavailable.
        if self.product == "overseas_futures":
            off_strategy_fills = {"hts": None, "other_api": None, "other": None, "other_codes": None,
                                  "status": "unavailable",
                                  "reason": "futures_fills_have_no_media_code"}
        else:
            in_scope = [r for r in rows if r["product"] == self.product
                        and r["provider"] == self.provider]
            off_strategy_fills = {
                "hts": sum(1 for r in in_scope if r["classification"] == "manual"),
                "other_api": sum(1 for r in in_scope if r["classification"] == "unknown_api"),
                "other": sum(1 for r in in_scope if r["classification"] == "other"),
                # Distinct unlisted codes behind "other" — the evidence trail for
                # extending MEDIA_CODES_* (consumers may ignore this key).
                "other_codes": sorted({str(r["commda_code"]) for r in in_scope
                                       if r["classification"] == "other" and r["commda_code"]}),
                "status": "available", "reason": None,
            }

        return {
            "version": 2,
            "scope": {"kind": "local_workflow_ledger", "product": self.product,
                      "provider": self.provider, "trading_mode": self.trading_mode},
            "as_of": datetime.now(timezone.utc).isoformat(),
            "basis": "stored_fifo_gross_excluding_fees",
            "executed_order_count": None if invalid_count else len(keys),
            "executed_order_count_status": "unavailable" if invalid_count else "available",
            "executed_order_count_reason": "invalid_execution_identity" if invalid_count else None,
            "realized_pnl": realized,
            "closed_trade_count": closed_total,
            "winning_trade_count": winning_total,
            "losing_trade_count": losing_total,
            "breakeven_trade_count": breakeven_total,
            "closed_trade_status": trade_status,
            "closed_trade_reason": trade_reason,
            "closed_trade_basis": closed_trade_basis,
            "estimated_group_count": estimated_group_count,
            "profit_loss_ratio": ratio,
            "profit_loss_ratio_status": ratio_status,
            "profit_loss_ratio_reason": ratio_reason,
            "profit_loss_ratio_basis": profit_loss_ratio_basis,
            "off_strategy_fills": off_strategy_fills,
            "max_drawdown": None,
            "max_drawdown_status": "unavailable",
            "max_drawdown_reason": "equity_history_unavailable",
        }
    
    def detect_anomalies(self) -> List[AnomalyResult]:
        """
        이상 거래 감지
        
        Returns:
            감지된 이상 거래 목록
        """
        anomalies: List[AnomalyResult] = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. sell_without_buy: 워크플로우 매수 없이 매도한 경우
            cursor.execute("""
                SELECT symbol, SUM(CASE WHEN side = 'buy' THEN quantity ELSE 0 END) as buy_qty,
                       SUM(CASE WHEN side = 'sell' THEN quantity ELSE 0 END) as sell_qty
                FROM trade_history
                WHERE classification = 'workflow' AND trading_mode = ?
                GROUP BY symbol
                HAVING sell_qty > buy_qty
            """, (self.trading_mode,))
            
            for symbol, buy_qty, sell_qty in cursor.fetchall():
                anomalies.append(AnomalyResult(
                    pattern="sell_without_buy",
                    symbol=symbol,
                    description=f"Sell qty ({sell_qty}) exceeds buy qty ({buy_qty})",
                    severity=10,
                ))
            
            # 2. unknown_api_ratio: 알 수 없는 API 주문 비율
            # 분모는 리터럴 '40' 이 아니라 **media_channel() 기준**으로 고른다 — 종전
            # SQL 은 `commda_code = '40'` 하드코딩이라 표(MEDIA_CODES_*)와 어긋났다:
            #  · TC3(해외선물) 프레임에는 통신매체코드 필드가 없어 이제 빈 문자열을
            #    싣는데, '40' 고정 분모는 그 행을 통째로 빼서 선물에서는 이 이상탐지가
            #    **영구히 0행**(절대 발화 안 함)이었다.
            #  · 41(API)·43(Robo API) 행도 분모에서 빠졌다.
            # 이제 channel 이 "api"(40/41/43) 또는 "unknown"(빈/미상 매체코드)인 행이
            # 분모다 = "사람·브로커 채널이 아니어서 API 경로일 수 있는 체결". 동작 변화는
            # 선물(빈 코드)이 다시 탐지 대상이 된다는 것 하나이고, 임계값(10%)과 감점
            # 폭(최대 20)은 종전 그대로다. (2026-09-12 적대적 검토 지적 B6)
            cursor.execute("""
                SELECT commda_code, classification FROM trade_history
                WHERE trading_mode = ?
            """, (self.trading_mode,))

            scoped = [(code, kind) for code, kind in cursor.fetchall()
                      if media_channel(code) in ("api", "unknown")]
            total_count = len(scoped)
            if total_count > 0:
                unknown_count = sum(1 for _, kind in scoped if kind == "unknown_api")
                ratio = unknown_count / total_count
                if ratio > 0.1:  # 10% 이상이면 이상
                    severity = min(int(ratio * 100), 20)  # 최대 20점 감점
                    anomalies.append(AnomalyResult(
                        pattern="unknown_api_ratio",
                        symbol="*",
                        description=f"Unknown API orders: {unknown_count}/{total_count} ({ratio*100:.1f}%)",
                        severity=severity,
                    ))
        
        return anomalies
    
    def calculate_trust_score(self, anomalies: Optional[List[AnomalyResult]] = None) -> int:
        """
        신뢰도 점수 계산

        워크플로우 거래가 없으면 0 (신뢰도 산정 불가),
        거래가 있으면 100에서 이상 거래 감지 시 감점.

        Args:
            anomalies: 이상 거래 목록 (없으면 자동 감지)

        Returns:
            신뢰도 점수 (0-100)
        """
        # 워크플로우 거래가 없으면 신뢰도 0
        if not self._has_workflow_orders():
            return 0

        if anomalies is None:
            anomalies = self.detect_anomalies()

        score = 100
        for anomaly in anomalies:
            score -= anomaly.severity

        return max(0, score)

    def _has_workflow_orders(self) -> bool:
        """워크플로우 주문이 존재하는지 확인 (현재 trading_mode 기준)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM workflow_orders WHERE trading_mode = ? LIMIT 1", (self.trading_mode,))
            return cursor.fetchone()[0] > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        통계 정보 조회 (현재 trading_mode 기준)

        Returns:
            주문/체결 통계
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 워크플로우 주문 수
            cursor.execute("SELECT COUNT(*) FROM workflow_orders WHERE trading_mode = ?", (self.trading_mode,))
            order_count = cursor.fetchone()[0]

            # 분류별 체결 수
            cursor.execute("""
                SELECT classification, COUNT(*), SUM(quantity)
                FROM trade_history
                WHERE trading_mode = ?
                GROUP BY classification
            """, (self.trading_mode,))
            fill_stats = {row[0]: {"count": row[1], "quantity": row[2]} for row in cursor.fetchall()}

            # 활성 로트 수
            cursor.execute("""
                SELECT classification, COUNT(*), SUM(remaining_qty)
                FROM workflow_position_lots
                WHERE remaining_qty > 0 AND trading_mode = ?
                GROUP BY classification
            """, (self.trading_mode,))
            lot_stats = {row[0]: {"count": row[1], "quantity": row[2]} for row in cursor.fetchall()}

            return {
                "trading_mode": self.trading_mode,
                "workflow_orders": order_count,
                "fills_by_classification": fill_stats,
                "active_lots_by_classification": lot_stats,
                "trust_score": self.calculate_trust_score(),
            }

    def update_order_fill_price(
        self,
        order_no: str,
        order_date: str,
        fill_price: float,
    ) -> bool:
        """
        시장가 주문의 체결 가격 업데이트
        
        시장가 주문은 주문 시점에 가격을 알 수 없으므로,
        체결 이벤트 수신 시 실제 체결 가격으로 업데이트합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            fill_price: 체결 가격
            
        Returns:
            업데이트 성공 여부
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 가격이 0인 주문만 업데이트 (시장가 주문)
            cursor.execute("""
                UPDATE workflow_orders
                SET price = ?
                WHERE order_no = ? AND order_date = ? AND trading_mode = ? AND (price = 0 OR price IS NULL)
            """, (fill_price, order_no, order_date, self.trading_mode))
            
            updated = cursor.rowcount > 0
            conn.commit()
            
            if updated:
                logger.debug(f"Updated order fill price: {order_no} @ {fill_price}")
            
            return updated

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """최근 미체결 가능성이 있는 주문 목록 (긴급 정지 시 사용).

        최근 60초 이내 기록된 주문을 반환합니다.
        체결 여부를 정확히 알 수 없으므로, HTS/MTS에서 직접 확인이 필요합니다.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT order_no, order_date, symbol, exchange, side, quantity, price, node_id
                    FROM workflow_orders
                    WHERE trading_mode = ?
                      AND created_at >= datetime('now', '-60 seconds')
                    ORDER BY created_at DESC
                """, (self.trading_mode,))
                return [
                    {
                        "order_no": row[0],
                        "order_date": row[1],
                        "symbol": row[2],
                        "exchange": row[3],
                        "side": row[4],
                        "quantity": row[5],
                        "price": row[6],
                        "node_id": row[7],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception:
            return []

    def get_orders_without_fill_price(self) -> List[Dict[str, Any]]:
        """
        체결 가격이 없는 주문 목록 조회
        
        연결 끊김 등으로 체결 이벤트를 놓친 경우,
        체결내역 조회로 가격을 복구하기 위한 메서드입니다.
        
        Returns:
            가격이 0인 주문 목록
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_no, order_date, symbol, exchange, side, quantity
                FROM workflow_orders
                WHERE trading_mode = ? AND (price = 0 OR price IS NULL)
                ORDER BY created_at DESC
            """, (self.trading_mode,))
            
            return [
                {
                    "order_no": row[0],
                    "order_date": row[1],
                    "symbol": row[2],
                    "exchange": row[3],
                    "side": row[4],
                    "quantity": row[5],
                }
                for row in cursor.fetchall()
            ]

    def sync_fill_prices_from_history(
        self,
        fill_history: List[Dict[str, Any]],
    ) -> int:
        """
        체결내역에서 주문 가격 동기화 (Fallback)
        
        연결 끊김 등으로 실시간 체결 이벤트를 놓친 경우,
        체결내역 API 응답으로 가격을 복구합니다.
        
        Args:
            fill_history: 체결내역 API 응답 리스트
                [{"order_no": "123", "order_date": "20260123", "fill_price": 2.82}, ...]
            
        Returns:
            업데이트된 주문 수
        """
        updated_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for fill in fill_history:
                order_no = fill.get("order_no", "")
                order_date = fill.get("order_date", "")
                fill_price = fill.get("fill_price", 0)
                
                if not order_no or not order_date or fill_price <= 0:
                    continue
                
                cursor.execute("""
                    UPDATE workflow_orders
                    SET price = ?
                    WHERE order_no = ? AND order_date = ? AND trading_mode = ? AND (price = 0 OR price IS NULL)
                """, (fill_price, order_no, order_date, self.trading_mode))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    logger.debug(f"Synced fill price from history: {order_no} @ {fill_price}")
            
            conn.commit()
        
        if updated_count > 0:
            logger.info(f"Synced {updated_count} order fill prices from history")
        
        return updated_count

    def cancel_order(
        self,
        order_no: str,
        order_date: str,
    ) -> bool:
        """
        주문 취소 처리
        
        취소 완료 이벤트('13') 수신 시 호출하여 주문을 삭제합니다.
        아직 체결되지 않은 주문만 취소 가능합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            
        Returns:
            취소 성공 여부
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # workflow_orders에서 삭제
            cursor.execute("""
                DELETE FROM workflow_orders
                WHERE order_no = ? AND order_date = ? AND trading_mode = ?
            """, (order_no, order_date, self.trading_mode))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                logger.info(f"Cancelled workflow order: {order_no}")
            else:
                logger.debug(f"Order not found for cancellation: {order_no}")
            
            return deleted

    def modify_order(
        self,
        order_no: str,
        order_date: str,
        new_quantity: Optional[int] = None,
        new_price: Optional[float] = None,
    ) -> bool:
        """
        주문 정정 처리
        
        정정 완료 이벤트('12') 수신 시 호출하여 주문 정보를 업데이트합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            new_quantity: 새 수량 (None이면 변경 안함)
            new_price: 새 가격 (None이면 변경 안함)
            
        Returns:
            정정 성공 여부
        """
        if new_quantity is None and new_price is None:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 동적 쿼리 생성
            updates = []
            params = []
            
            if new_quantity is not None:
                updates.append("quantity = ?")
                params.append(new_quantity)
            
            if new_price is not None:
                updates.append("price = ?")
                params.append(new_price)
            
            params.extend([order_no, order_date, self.trading_mode])

            cursor.execute(f"""
                UPDATE workflow_orders
                SET {", ".join(updates)}
                WHERE order_no = ? AND order_date = ? AND trading_mode = ?
            """, params)
            
            updated = cursor.rowcount > 0
            conn.commit()
            
            if updated:
                logger.info(f"Modified workflow order: {order_no} (qty={new_quantity}, price={new_price})")
            else:
                logger.debug(f"Order not found for modification: {order_no}")
            
            return updated

    def sync_fills_from_history(
        self,
        fill_history: List[Dict[str, Any]],
    ) -> int:
        """체결내역 기반 FIFO 복구 — **미구현(별도 작업 필요)**. 항상 0 을 반환한다.

        연결 끊김 등으로 실시간 체결을 놓쳤을 때 체결내역 API 응답으로 포지션을
        되살리려던 경로다. 그러나 이 함수는 **한 번도 동작한 적이 없다**:
        - 본문이 이 모듈에 존재하지 않는 ``FillEvent`` 를 import 해 호출 즉시
          ImportError 로 죽었고,
        - (동기 함수인데) async 인 ``record_fill`` 을 await 없이 위치인자 1개로 불렀고,
        - 매체코드를 '40' 으로 하드코딩해 브로커가 실제로 준 값을 버렸다.
        호출부(``context.sync_workflow_fills_from_history``)의 try/except 가 그 예외를
        삼켜 0 을 돌려줬기 때문에 실패가 조용했다 — 복구된 줄 알았는데 아무것도 안 됐다.

        제대로 고치려면 ``record_fill`` 을 await 해야 하고(=이 함수가 async 가 돼야 하고),
        그러면 동기 호출부인 context.py/executor.py 시그니처까지 함께 바뀌어야 한다.
        여기서 자체적으로 이벤트 루프를 돌리는 우회는 쓰지 않는다 — 호출부가 이미 실행
        중인 루프 안이라 중첩 루프/교착을 만든다. 그래서 지금은 **조용히 실패하지 않게만**
        만든다: 죽은 import 를 지우고, 즉시 error 로그를 남기고, 0 을 반환한다.

        Args:
            fill_history: 체결내역 API 응답 리스트 (현재 소비하지 않는다)

        Returns:
            처리된 체결 수 — 언제나 0
        """
        logger.error(
            "sync_fills_from_history 는 미구현이다 — 체결내역 %d건을 FIFO 원장에 반영하지 "
            "않고 건너뛴다. 실시간 체결을 놓친 구간은 워크플로우 집계에서 누락된 채로 "
            "남는다(복구 경로 없음). record_fill 의 async 호출 + 호출부 시그니처 변경이 "
            "필요한 별도 작업이다.",
            len(fill_history or []),
        )
        return 0
