"""WebSocket 싱글톤 패턴 단위 테스트.

real() 메서드의 싱글톤 캐시, connect() 가드, close() 참조 카운트,
캐시 정리 로직을 검증합니다.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from programgarden_finance.ls.overseas_stock import OverseasStock
from programgarden_finance.ls.overseas_futureoption import OverseasFutureoption
from programgarden_finance.ls.real_base import RealRequestAbstract


@pytest.fixture(autouse=True)
def clear_singleton_caches():
    """각 테스트 전후로 싱글톤 캐시 초기화."""
    OverseasStock._clear_all_real_instances()
    OverseasFutureoption._clear_all_real_instances()
    yield
    OverseasStock._clear_all_real_instances()
    OverseasFutureoption._clear_all_real_instances()


def _make_token_manager():
    """테스트용 mock TokenManager 생성."""
    tm = MagicMock()
    tm.access_token = "test-token"
    tm.wss_url = "wss://test.example.com"
    return tm


# =============================================================
# Phase 1: real() 싱글톤 캐시
# =============================================================


class TestRealSingleton:
    """real() 메서드 싱글톤 캐시 테스트."""

    def test_real_returns_same_instance(self):
        """같은 token_manager로 real() 호출 시 동일 인스턴스 반환."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)

        real1 = stock.real()
        real2 = stock.real()

        assert real1 is real2

    def test_real_returns_same_instance_different_stock_objects(self):
        """다른 OverseasStock 객체라도 같은 token_manager면 동일 Real 반환."""
        tm = _make_token_manager()
        stock1 = OverseasStock(token_manager=tm)
        stock2 = OverseasStock(token_manager=tm)

        real1 = stock1.real()
        real2 = stock2.real()

        assert real1 is real2

    def test_real_different_token_managers(self):
        """다른 token_manager → 다른 Real 인스턴스."""
        tm1 = _make_token_manager()
        tm2 = _make_token_manager()
        stock1 = OverseasStock(token_manager=tm1)
        stock2 = OverseasStock(token_manager=tm2)

        real1 = stock1.real()
        real2 = stock2.real()

        assert real1 is not real2

    def test_futures_real_returns_same_instance(self):
        """해외선물도 같은 token_manager → 싱글톤."""
        tm = _make_token_manager()
        fut = OverseasFutureoption(token_manager=tm)

        real1 = fut.real()
        real2 = fut.real()

        assert real1 is real2

    def test_stock_and_futures_separate_caches(self):
        """주식과 선물은 별도 캐시 → 같은 token_manager라도 다른 인스턴스."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        fut = OverseasFutureoption(token_manager=tm)

        stock_real = stock.real()
        fut_real = fut.real()

        assert stock_real is not fut_real

    def test_clear_real_instances(self):
        """캐시 초기화 후 real() 호출 시 새 인스턴스 생성."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)

        real1 = stock.real()
        OverseasStock._clear_all_real_instances()
        real2 = stock.real()

        assert real1 is not real2

    def test_clear_specific_instance(self):
        """특정 token_manager의 캐시만 제거."""
        tm1 = _make_token_manager()
        tm2 = _make_token_manager()
        stock1 = OverseasStock(token_manager=tm1)
        stock2 = OverseasStock(token_manager=tm2)

        real1 = stock1.real()
        real2 = stock2.real()

        OverseasStock._clear_real_instance(id(tm1))

        real1_new = stock1.real()
        real2_same = stock2.real()

        assert real1 is not real1_new
        assert real2 is real2_same


# =============================================================
# Phase 2: connect() 가드
# =============================================================


class TestConnectGuard:
    """connect() 중복 호출 방지 가드 테스트."""

    @pytest.mark.asyncio
    async def test_connect_guard_already_connected(self):
        """이미 연결된 상태에서 connect() 재호출 시 중복 task 생성 안함."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real = stock.real()

        # 연결된 상태 시뮬레이션
        real._connected_event.set()
        real._listen_task = MagicMock()
        real._listen_task.done.return_value = False

        initial_ref_count = real._ref_count

        # connect 호출해도 새 task 안 만들어야 함
        await real.connect(wait=False)

        assert real._ref_count == initial_ref_count + 1
        # _listen_task가 교체되지 않았어야 함 (create_task 호출 안됨)
        assert real._listen_task is not None

    @pytest.mark.asyncio
    async def test_connect_guard_connecting_in_progress(self):
        """연결 시도 중일 때 connect() 호출 시 wait만 수행."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real = stock.real()

        # 연결 시도 중 시뮬레이션: event는 미설정, task는 진행 중
        real._connected_event.clear()
        mock_task = MagicMock()
        mock_task.done.return_value = False
        real._listen_task = mock_task

        # wait=False로 호출 시 바로 반환
        await real.connect(wait=False)

        assert real._ref_count == 1
        # 기존 task가 유지되어야 함
        assert real._listen_task is mock_task

    @pytest.mark.asyncio
    async def test_ref_count_increments_on_each_connect(self):
        """connect() 호출마다 ref_count 증가."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real = stock.real()

        # 연결된 상태 시뮬레이션
        real._connected_event.set()

        await real.connect(wait=False)
        await real.connect(wait=False)
        await real.connect(wait=False)

        assert real._ref_count == 3


# =============================================================
# Phase 3: close() 참조 카운트
# =============================================================


class TestCloseRefCount:
    """close() 참조 카운트 기반 안전한 종료 테스트."""

    @pytest.mark.asyncio
    async def test_close_ref_count_prevents_close(self):
        """ref_count > 0이면 실제 close하지 않음."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real = stock.real()

        real._ref_count = 3
        real._connected_event.set()

        await real.close()

        assert real._ref_count == 2
        # 연결이 유지되어야 함
        assert real._connected_event.is_set()

    @pytest.mark.asyncio
    async def test_close_at_zero_ref_count(self):
        """ref_count가 0이 되면 실제 종료."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real = stock.real()

        real._ref_count = 1
        real._connected_event.set()
        real._listen_task = None
        real._ws = None

        await real.close()

        assert real._ref_count == 0
        assert not real._connected_event.is_set()

    @pytest.mark.asyncio
    async def test_close_force(self):
        """force=True면 ref_count 무시하고 즉시 종료."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real = stock.real()

        real._ref_count = 5
        real._connected_event.set()
        real._listen_task = None
        real._ws = None

        await real.close(force=True)

        assert real._ref_count == 0
        assert not real._connected_event.is_set()

    @pytest.mark.asyncio
    async def test_close_cancels_listen_task(self):
        """close가 listen_task를 cancel함."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real = stock.real()

        real._ref_count = 1
        real._connected_event.set()
        real._ws = None

        # 실제 asyncio.Task처럼 동작하는 mock: cancel 가능, await 시 CancelledError
        cancelled = False

        async def _fake_task():
            await asyncio.sleep(100)

        task = asyncio.create_task(_fake_task())
        real._listen_task = task

        await real.close()

        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_close_ref_count_not_below_zero(self):
        """ref_count가 0 이하로 내려가지 않음."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real = stock.real()

        real._ref_count = 0
        real._listen_task = None
        real._ws = None

        await real.close()

        assert real._ref_count == 0


# =============================================================
# Phase 4: 싱글톤 캐시 정리
# =============================================================


class TestCacheCleanup:
    """close 후 싱글톤 캐시 정리 테스트."""

    @pytest.mark.asyncio
    async def test_close_force_removes_from_stock_cache(self):
        """force close 후 stock 캐시에서 제거 → 새 인스턴스 생성."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real1 = stock.real()

        real1._listen_task = None
        real1._ws = None

        await real1.close(force=True)

        assert id(tm) not in OverseasStock._real_instances
        real2 = stock.real()
        assert real1 is not real2

    @pytest.mark.asyncio
    async def test_close_force_removes_from_futures_cache(self):
        """force close 후 futures 캐시에서 제거."""
        tm = _make_token_manager()
        fut = OverseasFutureoption(token_manager=tm)
        real1 = fut.real()

        real1._listen_task = None
        real1._ws = None

        await real1.close(force=True)

        assert id(tm) not in OverseasFutureoption._real_instances
        real2 = fut.real()
        assert real1 is not real2

    @pytest.mark.asyncio
    async def test_normal_close_at_zero_also_cleans_cache(self):
        """일반 close도 ref_count=0이면 캐시 정리."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real1 = stock.real()

        real1._ref_count = 1
        real1._listen_task = None
        real1._ws = None

        await real1.close()

        assert id(tm) not in OverseasStock._real_instances

    @pytest.mark.asyncio
    async def test_partial_close_keeps_cache(self):
        """ref_count > 0이면 캐시 유지."""
        tm = _make_token_manager()
        stock = OverseasStock(token_manager=tm)
        real1 = stock.real()

        real1._ref_count = 2

        await real1.close()

        assert id(tm) in OverseasStock._real_instances
        assert stock.real() is real1
