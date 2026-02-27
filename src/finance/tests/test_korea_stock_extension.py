"""
국내주식 Extension 모듈 단위 테스트.

models.py, calculator.py, subscription_manager.py, tracker.py의
핵심 로직을 검증합니다.
"""

from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from programgarden_finance.ls.korea_stock.extension.models import (
    KrAccountPnLInfo,
    KrCommissionConfig,
    KrStockBalanceInfo,
    KrStockOpenOrder,
    KrStockPnLResult,
    KrStockPositionItem,
    KrStockTradeInput,
)
from programgarden_finance.ls.korea_stock.extension.calculator import (
    KrStockPnLCalculator,
    calculate_kr_stock_pnl,
)
from programgarden_finance.ls.korea_stock.extension.subscription_manager import (
    SubscriptionManager,
)
from programgarden_finance.ls.korea_stock.extension.tracker import (
    KrStockAccountTracker,
    _is_kospi_market,
    _is_no_data_response,
    _is_success_response,
)


# =============================================================
# Phase 1: models.py 테스트
# =============================================================


class TestKrCommissionConfig:
    """KrCommissionConfig 모델 테스트."""

    def test_default_values(self):
        """기본값 확인."""
        config = KrCommissionConfig()
        assert config.commission_rate == Decimal("0.00015")
        assert config.kospi_tax_rate == Decimal("0.0003")
        assert config.kospi_rural_tax_rate == Decimal("0.0015")
        assert config.kosdaq_tax_rate == Decimal("0.0018")
        assert config.kosdaq_rural_tax_rate == Decimal("0")

    def test_get_sell_tax_rate_kospi_string(self):
        """KOSPI 문자열 '1' 기준 세금률 반환."""
        config = KrCommissionConfig()
        rate = config.get_sell_tax_rate("1")
        assert rate == Decimal("0.0003") + Decimal("0.0015")
        assert rate == Decimal("0.0018")

    def test_get_sell_tax_rate_kospi_string_10(self):
        """KOSPI 문자열 '10' 기준 세금률 반환."""
        config = KrCommissionConfig()
        rate = config.get_sell_tax_rate("10")
        assert rate == Decimal("0.0018")

    def test_get_sell_tax_rate_kospi_label(self):
        """KOSPI 레이블 기준 세금률 반환."""
        config = KrCommissionConfig()
        rate = config.get_sell_tax_rate("KOSPI")
        # 거래세 0.03% + 농특세 0.15% = 0.18%
        assert rate == Decimal("0.0018")

    def test_get_sell_tax_rate_kosdaq_string(self):
        """KOSDAQ 문자열 '2' 기준 세금률 반환 (농특세 없음)."""
        config = KrCommissionConfig()
        rate = config.get_sell_tax_rate("2")
        # 거래세 0.18% + 농특세 0%
        assert rate == Decimal("0.0018")

    def test_get_sell_tax_rate_kosdaq_string_20(self):
        """KOSDAQ 문자열 '20' 기준 세금률 반환."""
        config = KrCommissionConfig()
        rate = config.get_sell_tax_rate("20")
        assert rate == Decimal("0.0018")

    def test_get_sell_tax_rate_kosdaq_label(self):
        """KOSDAQ 레이블 기준 세금률 반환."""
        config = KrCommissionConfig()
        rate = config.get_sell_tax_rate("KOSDAQ")
        assert rate == Decimal("0.0018")

    def test_get_sell_tax_rate_unknown_market(self):
        """알 수 없는 시장은 KOSDAQ 거래세만 반환."""
        config = KrCommissionConfig()
        rate = config.get_sell_tax_rate("KONEX")
        # 기타 시장은 kosdaq_tax_rate만 반환
        assert rate == Decimal("0.0018")

    def test_kospi_vs_kosdaq_rural_tax_difference(self):
        """KOSPI 농특세 있음, KOSDAQ 농특세 없음 구분."""
        config = KrCommissionConfig()
        kospi_rate = config.get_sell_tax_rate("KOSPI")
        kosdaq_rate = config.get_sell_tax_rate("KOSDAQ")
        # KOSPI: 거래세 + 농특세, KOSDAQ: 거래세만
        # 세율이 다름 - KOSPI는 농특세 추가분만큼 높아야 함
        assert kospi_rate > config.kospi_tax_rate
        assert kosdaq_rate == config.kosdaq_tax_rate


class TestKrStockTradeInput:
    """KrStockTradeInput 모델 테스트."""

    def test_basic_creation(self):
        """기본 생성 확인."""
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
        )
        assert trade.ticker == "005930"
        assert trade.qty == 10
        assert trade.buy_price == 70000
        assert trade.sell_price == 75000
        assert trade.market == "KOSPI"  # 기본값
        assert trade.fee_rate is None   # 기본값

    def test_custom_market(self):
        """KOSDAQ 시장 설정."""
        trade = KrStockTradeInput(
            ticker="247540",
            qty=100,
            buy_price=5000,
            sell_price=5500,
            market="KOSDAQ",
        )
        assert trade.market == "KOSDAQ"

    def test_custom_fee_rate(self):
        """수수료율 커스텀 설정."""
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
            fee_rate=Decimal("0.0001"),
        )
        assert trade.fee_rate == Decimal("0.0001")


class TestKrStockPnLResult:
    """KrStockPnLResult 모델 테스트."""

    def test_basic_creation(self):
        """기본 생성 확인."""
        result = KrStockPnLResult(
            gross_profit=50000,
            net_profit=48432,
            total_fee=1568,
            buy_fee=105,
            sell_fee=113,
            transaction_tax=225,
            rural_tax=1125,
            return_rate_percent=Decimal("6.92"),
            market="KOSPI",
        )
        assert result.gross_profit == 50000
        assert result.net_profit == 48432
        assert result.total_fee == 1568

    def test_default_tax_values(self):
        """거래세/농특세 기본값 0."""
        result = KrStockPnLResult(
            gross_profit=0,
            net_profit=0,
            total_fee=0,
            buy_fee=0,
            sell_fee=0,
            return_rate_percent=Decimal("0"),
        )
        assert result.transaction_tax == 0
        assert result.rural_tax == 0
        assert result.market == "KOSPI"  # 기본값


class TestKrStockPositionItem:
    """KrStockPositionItem 모델 테스트."""

    def test_basic_creation_with_required_field(self):
        """필수 필드(symbol)만으로 생성."""
        pos = KrStockPositionItem(symbol="005930")
        assert pos.symbol == "005930"
        assert pos.symbol_name == ""
        assert pos.quantity == 0
        assert pos.current_price == 0
        assert pos.market == ""
        assert pos.realtime_pnl is None
        assert pos.last_updated is None

    def test_creation_with_market_field(self):
        """market 필드 포함 생성."""
        pos = KrStockPositionItem(
            symbol="005930",
            symbol_name="삼성전자",
            quantity=10,
            buy_price=70000,
            current_price=75000,
            market="1",
        )
        assert pos.market == "1"
        assert pos.symbol_name == "삼성전자"


class TestKrStockBalanceInfo:
    """KrStockBalanceInfo 모델 테스트."""

    def test_default_values(self):
        """기본값 확인."""
        info = KrStockBalanceInfo()
        assert info.deposit == 0
        assert info.d1_deposit == 0
        assert info.d2_deposit == 0
        assert info.orderable_amount == 0
        assert info.last_updated is None

    def test_creation_with_values(self):
        """값을 포함한 생성."""
        info = KrStockBalanceInfo(
            deposit=1000000,
            d1_deposit=900000,
            orderable_amount=800000,
        )
        assert info.deposit == 1000000
        assert info.orderable_amount == 800000


class TestKrStockOpenOrder:
    """KrStockOpenOrder 모델 테스트."""

    def test_basic_creation(self):
        """필수 필드로 생성."""
        order = KrStockOpenOrder(order_no=12345, symbol="005930")
        assert order.order_no == 12345
        assert order.symbol == "005930"
        assert order.order_qty == 0
        assert order.order_price == 0
        assert order.remaining_qty == 0

    def test_creation_with_all_fields(self):
        """전체 필드 생성."""
        order = KrStockOpenOrder(
            order_no=99999,
            symbol="247540",
            order_type="매수",
            order_qty=100,
            order_price=5000,
            executed_qty=50,
            remaining_qty=50,
        )
        assert order.order_type == "매수"
        assert order.executed_qty == 50
        assert order.remaining_qty == 50


class TestKrAccountPnLInfo:
    """KrAccountPnLInfo 모델 테스트."""

    def test_default_values(self):
        """기본값 확인."""
        info = KrAccountPnLInfo()
        assert info.account_pnl_rate == Decimal("0")
        assert info.total_eval_amount == 0
        assert info.position_count == 0
        assert info.last_updated is None


# =============================================================
# Phase 2: calculator.py 테스트
# =============================================================


class TestCalculateKrStockPnL:
    """calculate_kr_stock_pnl() 함수 테스트."""

    def test_kospi_basic_calculation(self):
        """KOSPI 10주: 매수 70,000 -> 매도 75,000 손익 계산.

        수동 검증:
        - 매수금액: 700,000원
        - 매도금액: 750,000원
        - 매수수수료: 700,000 * 0.00015 = 105원
        - 매도수수료: 750,000 * 0.00015 = 113원 (ROUND_HALF_UP)
        - 거래세: 750,000 * 0.0003 = 225원
        - 농특세: 750,000 * 0.0015 = 1,125원
        - 총 제비용: 105 + 113 + 225 + 1,125 = 1,568원
        - 세전손익: 750,000 - 700,000 = 50,000원
        - 세후손익: 50,000 - 1,568 = 48,432원
        - 수익률: 48,432 / (700,000 + 105) * 100 ≈ 6.92%
        """
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
            market="KOSPI",
        )
        result = calculate_kr_stock_pnl(trade)

        assert result.gross_profit == 50000
        assert result.buy_fee == 105
        assert result.sell_fee == 113
        assert result.transaction_tax == 225
        assert result.rural_tax == 1125
        assert result.total_fee == 1568
        assert result.net_profit == 48432
        assert result.return_rate_percent == Decimal("6.92")
        assert result.market == "KOSPI"

    def test_kosdaq_basic_calculation(self):
        """KOSDAQ 100주: 매수 5,000 -> 매도 5,500 손익 계산.

        수동 검증:
        - 매수금액: 500,000원
        - 매도금액: 550,000원
        - 매수수수료: 500,000 * 0.00015 = 75원
        - 매도수수료: 550,000 * 0.00015 = 83원 (ROUND_HALF_UP)
        - 거래세: 550,000 * 0.0018 = 990원
        - 농특세: 0원 (KOSDAQ 없음)
        - 총 제비용: 75 + 83 + 990 + 0 = 1,148원
        - 세전손익: 550,000 - 500,000 = 50,000원
        - 세후손익: 50,000 - 1,148 = 48,852원
        - 수익률: 48,852 / (500,000 + 75) * 100 ≈ 9.77%
        """
        trade = KrStockTradeInput(
            ticker="247540",
            qty=100,
            buy_price=5000,
            sell_price=5500,
            market="KOSDAQ",
        )
        result = calculate_kr_stock_pnl(trade)

        assert result.gross_profit == 50000
        assert result.buy_fee == 75
        assert result.sell_fee == 83
        assert result.transaction_tax == 990
        assert result.rural_tax == 0
        assert result.total_fee == 1148
        assert result.net_profit == 48852
        assert result.return_rate_percent == Decimal("9.77")
        assert result.market == "KOSDAQ"

    def test_zero_quantity(self):
        """0수량인 경우 손익 0."""
        trade = KrStockTradeInput(
            ticker="005930",
            qty=0,
            buy_price=70000,
            sell_price=75000,
        )
        result = calculate_kr_stock_pnl(trade)

        assert result.gross_profit == 0
        assert result.net_profit == 0
        assert result.total_fee == 0
        assert result.return_rate_percent == Decimal("0")

    def test_buy_equals_sell_price(self):
        """매수가 = 매도가인 경우 (수수료/세금으로 인해 손실)."""
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=70000,
        )
        result = calculate_kr_stock_pnl(trade)

        assert result.gross_profit == 0
        # 수수료+세금이 있으므로 net_profit은 음수
        assert result.net_profit < 0
        assert result.total_fee > 0

    def test_custom_fee_rate(self):
        """수수료율 커스텀 설정 테스트."""
        trade_default = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
        )
        trade_custom = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
            fee_rate=Decimal("0.0001"),  # 기본값(0.00015)보다 낮음
        )
        result_default = calculate_kr_stock_pnl(trade_default)
        result_custom = calculate_kr_stock_pnl(trade_custom)

        # 수수료율이 낮으면 세후손익이 더 높아야 함
        assert result_custom.net_profit > result_default.net_profit

    def test_custom_commission_config(self):
        """KrCommissionConfig 커스텀 설정으로 계산."""
        config = KrCommissionConfig(commission_rate=Decimal("0.0002"))
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
        )
        result = calculate_kr_stock_pnl(trade, commission_config=config)

        # 수수료율이 높으면 수수료가 더 많아야 함
        assert result.buy_fee == 140   # 700,000 * 0.0002
        assert result.sell_fee == 150  # 750,000 * 0.0002

    def test_loss_case(self):
        """손실 케이스 (매도가 < 매수가)."""
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=75000,
            sell_price=70000,
        )
        result = calculate_kr_stock_pnl(trade)

        assert result.gross_profit == -50000
        assert result.net_profit < result.gross_profit  # 세금/수수료로 더 손실
        assert result.return_rate_percent < Decimal("0")

    def test_default_config_used_when_none(self):
        """commission_config=None 시 기본값 사용."""
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
        )
        result_explicit = calculate_kr_stock_pnl(trade, commission_config=KrCommissionConfig())
        result_default = calculate_kr_stock_pnl(trade, commission_config=None)

        assert result_explicit.net_profit == result_default.net_profit

    def test_kospi_market_code_1(self):
        """시장코드 '1'로 KOSPI 계산."""
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
            market="1",
        )
        result = calculate_kr_stock_pnl(trade)
        # KOSPI이므로 농특세 있어야 함
        assert result.rural_tax > 0

    def test_kosdaq_market_code_2(self):
        """시장코드 '2'로 KOSDAQ 계산."""
        trade = KrStockTradeInput(
            ticker="247540",
            qty=100,
            buy_price=5000,
            sell_price=5500,
            market="2",
        )
        result = calculate_kr_stock_pnl(trade)
        # KOSDAQ이므로 농특세 없어야 함
        assert result.rural_tax == 0


class TestKrStockPnLCalculator:
    """KrStockPnLCalculator 클래스 테스트."""

    def test_basic_creation(self):
        """기본 생성 확인."""
        calculator = KrStockPnLCalculator()
        assert calculator.commission_config is not None
        assert calculator.commission_config.commission_rate == Decimal("0.00015")

    def test_creation_with_custom_config(self):
        """커스텀 설정으로 생성."""
        config = KrCommissionConfig(commission_rate=Decimal("0.0002"))
        calculator = KrStockPnLCalculator(commission_config=config)
        assert calculator.commission_config.commission_rate == Decimal("0.0002")

    def test_calculate_method(self):
        """calculate() 메서드 테스트."""
        calculator = KrStockPnLCalculator()
        trade = KrStockTradeInput(
            ticker="005930",
            qty=10,
            buy_price=70000,
            sell_price=75000,
        )
        result = calculator.calculate(trade)
        assert result.net_profit == 48432

    def test_update_config(self):
        """설정 업데이트 테스트."""
        calculator = KrStockPnLCalculator()
        new_config = KrCommissionConfig(commission_rate=Decimal("0.0002"))
        calculator.update_config(new_config)
        assert calculator.commission_config.commission_rate == Decimal("0.0002")

    def test_calculate_realtime_pnl_kospi(self):
        """KOSPI 실시간 손익 계산."""
        calculator = KrStockPnLCalculator()
        result = calculator.calculate_realtime_pnl(
            symbol="005930",
            quantity=10,
            buy_price=70000,
            current_price=75000,
            market="KOSPI",
        )
        assert result.gross_profit == 50000
        assert result.net_profit == 48432
        assert result.rural_tax == 1125  # KOSPI 농특세 있음

    def test_calculate_realtime_pnl_kosdaq(self):
        """KOSDAQ 실시간 손익 계산."""
        calculator = KrStockPnLCalculator()
        result = calculator.calculate_realtime_pnl(
            symbol="247540",
            quantity=100,
            buy_price=5000,
            current_price=5500,
            market="KOSDAQ",
        )
        assert result.gross_profit == 50000
        assert result.net_profit == 48852
        assert result.rural_tax == 0  # KOSDAQ 농특세 없음

    def test_calculate_realtime_pnl_default_market(self):
        """기본 market 인자(KOSPI) 사용 확인."""
        calculator = KrStockPnLCalculator()
        result = calculator.calculate_realtime_pnl(
            symbol="005930",
            quantity=10,
            buy_price=70000,
            current_price=75000,
        )
        assert result.market == "KOSPI"
        assert result.rural_tax > 0

    def test_calculate_realtime_pnl_zero_quantity(self):
        """0수량 실시간 손익."""
        calculator = KrStockPnLCalculator()
        result = calculator.calculate_realtime_pnl(
            symbol="005930",
            quantity=0,
            buy_price=70000,
            current_price=75000,
        )
        assert result.gross_profit == 0
        assert result.net_profit == 0


# =============================================================
# Phase 3: subscription_manager.py 테스트
# =============================================================


class TestSubscriptionManager:
    """SubscriptionManager 클래스 테스트."""

    @pytest.mark.asyncio
    async def test_subscribe_new_symbol(self):
        """새 종목 구독 성공."""
        manager = SubscriptionManager()
        called_with = []

        async def mock_sub(symbol):
            called_with.append(symbol)

        result = await manager.subscribe("005930", mock_sub)
        assert result is True
        assert "005930" in manager.subscribed_symbols
        assert called_with == ["005930"]

    @pytest.mark.asyncio
    async def test_subscribe_duplicate_prevention(self):
        """중복 구독 방지."""
        manager = SubscriptionManager()
        call_count = 0

        async def mock_sub(symbol):
            nonlocal call_count
            call_count += 1

        await manager.subscribe("005930", mock_sub)
        result = await manager.subscribe("005930", mock_sub)

        assert result is False
        assert call_count == 1  # 두 번째 구독 함수 미호출

    @pytest.mark.asyncio
    async def test_subscribe_sync_function(self):
        """동기 함수로 구독."""
        manager = SubscriptionManager()
        called_with = []

        def mock_sub(symbol):
            called_with.append(symbol)

        result = await manager.subscribe("005930", mock_sub)
        assert result is True
        assert called_with == ["005930"]

    @pytest.mark.asyncio
    async def test_unsubscribe_existing_symbol(self):
        """구독 중인 종목 해제."""
        manager = SubscriptionManager()
        called_with = []

        async def mock_sub(symbol):
            pass

        async def mock_unsub(symbol):
            called_with.append(symbol)

        await manager.subscribe("005930", mock_sub)
        result = await manager.unsubscribe("005930", mock_unsub)

        assert result is True
        assert "005930" not in manager.subscribed_symbols
        assert called_with == ["005930"]

    @pytest.mark.asyncio
    async def test_unsubscribe_not_subscribed(self):
        """구독하지 않은 종목 해제 시도."""
        manager = SubscriptionManager()
        call_count = 0

        async def mock_unsub(symbol):
            nonlocal call_count
            call_count += 1

        result = await manager.unsubscribe("005930", mock_unsub)

        assert result is False
        assert call_count == 0

    @pytest.mark.asyncio
    async def test_sync_subscriptions_add_and_remove(self):
        """sync_subscriptions: 추가 및 제거 동기화."""
        manager = SubscriptionManager()
        subscribed = []
        unsubscribed = []

        async def mock_sub(symbol):
            subscribed.append(symbol)

        async def mock_unsub(symbol):
            unsubscribed.append(symbol)

        # 초기 구독: A, B
        await manager.sync_subscriptions({"A", "B"}, mock_sub, mock_unsub)
        assert manager.subscribed_symbols == {"A", "B"}
        assert sorted(subscribed) == ["A", "B"]
        assert unsubscribed == []

        # 동기화: B, C로 변경 → A 제거, C 추가
        subscribed.clear()
        unsubscribed.clear()

        await manager.sync_subscriptions({"B", "C"}, mock_sub, mock_unsub)
        assert manager.subscribed_symbols == {"B", "C"}
        assert subscribed == ["C"]
        assert unsubscribed == ["A"]

    @pytest.mark.asyncio
    async def test_sync_subscriptions_empty_target(self):
        """sync_subscriptions: 빈 목표 집합 → 모두 해제."""
        manager = SubscriptionManager()
        unsubscribed = []

        async def mock_sub(symbol):
            pass

        async def mock_unsub(symbol):
            unsubscribed.append(symbol)

        await manager.sync_subscriptions({"A", "B"}, mock_sub, mock_unsub)
        unsubscribed.clear()

        await manager.sync_subscriptions(set(), mock_sub, mock_unsub)
        assert manager.subscribed_symbols == set()
        assert sorted(unsubscribed) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_is_subscribed(self):
        """is_subscribed() 확인."""
        manager = SubscriptionManager()

        async def mock_sub(symbol):
            pass

        assert manager.is_subscribed("005930") is False
        await manager.subscribe("005930", mock_sub)
        assert manager.is_subscribed("005930") is True

    @pytest.mark.asyncio
    async def test_subscription_count(self):
        """subscription_count 확인."""
        manager = SubscriptionManager()

        async def mock_sub(symbol):
            pass

        assert manager.subscription_count == 0
        await manager.subscribe("A", mock_sub)
        await manager.subscribe("B", mock_sub)
        assert manager.subscription_count == 2

    @pytest.mark.asyncio
    async def test_clear_all_without_callback(self):
        """clear_all(): 콜백 없이 모두 해제."""
        manager = SubscriptionManager()

        async def mock_sub(symbol):
            pass

        await manager.subscribe("A", mock_sub)
        await manager.subscribe("B", mock_sub)
        await manager.clear_all()

        assert manager.subscription_count == 0
        assert manager.subscribed_symbols == set()

    @pytest.mark.asyncio
    async def test_clear_all_with_callback(self):
        """clear_all(): 콜백 함수 호출 확인."""
        manager = SubscriptionManager()
        unsubscribed = []

        async def mock_sub(symbol):
            pass

        async def mock_unsub(symbol):
            unsubscribed.append(symbol)

        await manager.subscribe("A", mock_sub)
        await manager.subscribe("B", mock_sub)
        await manager.clear_all(mock_unsub)

        assert manager.subscription_count == 0
        assert sorted(unsubscribed) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_subscribed_symbols_returns_copy(self):
        """subscribed_symbols 반환값이 복사본임 확인 (원본 불변)."""
        manager = SubscriptionManager()

        async def mock_sub(symbol):
            pass

        await manager.subscribe("A", mock_sub)
        symbols_copy = manager.subscribed_symbols
        symbols_copy.add("FAKE")  # 복사본 수정

        # 원본은 변경되지 않아야 함
        assert "FAKE" not in manager.subscribed_symbols


# =============================================================
# Phase 4: tracker.py 테스트
# =============================================================


class TestTrackerHelperFunctions:
    """tracker.py 헬퍼 함수 테스트."""

    # ===== _is_success_response() =====

    def test_is_success_response_code_00000(self):
        """성공 코드 '00000'."""
        assert _is_success_response("00000", "") is True

    def test_is_success_response_code_00001(self):
        """성공 코드 '00001'."""
        assert _is_success_response("00001", "") is True

    def test_is_success_response_code_00136(self):
        """성공 코드 '00136'."""
        assert _is_success_response("00136", "") is True

    def test_is_success_response_success_message(self):
        """성공 코드 아니어도 성공 메시지면 True."""
        assert _is_success_response("99999", "조회가 완료되었습니다") is True

    def test_is_success_response_jeongseong_message(self):
        """'정상' 메시지 포함 시 True."""
        assert _is_success_response("UNKNOWN", "정상 처리되었습니다") is True

    def test_is_success_response_failure(self):
        """실패 코드 및 실패 메시지."""
        assert _is_success_response("10001", "오류가 발생했습니다") is False

    def test_is_success_response_empty_code(self):
        """빈 코드 및 빈 메시지."""
        assert _is_success_response("", "") is False

    def test_is_success_response_none_msg(self):
        """rsp_msg가 None-like일 때 처리."""
        # msg = (rsp_msg or "") 처리로 None 대비
        assert _is_success_response("99999", None) is False

    # ===== _is_no_data_response() =====

    def test_is_no_data_response_success_code(self):
        """성공 코드면 데이터 없음 아님."""
        assert _is_no_data_response("00000", "없습니다") is False

    def test_is_no_data_response_no_data_message(self):
        """'없습니다' 메시지 포함 시 True."""
        assert _is_no_data_response("10001", "조회결과가 없습니다") is True

    def test_is_no_data_response_noeunnm(self):
        """'없음' 메시지 포함 시 True."""
        assert _is_no_data_response("10001", "데이터 없음") is True

    def test_is_no_data_response_no_data_english(self):
        """영문 'no data' 메시지."""
        assert _is_no_data_response("10001", "No Data Found") is True

    def test_is_no_data_response_not_found(self):
        """'not found' 메시지."""
        assert _is_no_data_response("10001", "Record not found") is True

    def test_is_no_data_response_jocheong_msg(self):
        """'조회내역' 메시지."""
        assert _is_no_data_response("10001", "조회내역이 없습니다") is True

    def test_is_no_data_response_other_error(self):
        """일반 에러 메시지 (데이터 없음이 아님)."""
        assert _is_no_data_response("10001", "시스템 오류입니다") is False

    def test_is_no_data_response_none_msg(self):
        """rsp_msg가 None-like일 때."""
        assert _is_no_data_response("10001", None) is False

    # ===== _is_kospi_market() =====

    def test_is_kospi_market_code_1(self):
        """시장코드 '1' -> KOSPI."""
        assert _is_kospi_market("1") is True

    def test_is_kospi_market_code_10(self):
        """시장코드 '10' -> KOSPI."""
        assert _is_kospi_market("10") is True

    def test_is_kospi_market_code_2(self):
        """시장코드 '2' -> KOSDAQ (False)."""
        assert _is_kospi_market("2") is False

    def test_is_kospi_market_empty(self):
        """빈 문자열 -> False."""
        assert _is_kospi_market("") is False

    def test_is_kospi_market_kospi_label(self):
        """'KOSPI' 레이블은 해당 없음 (코드 기준)."""
        assert _is_kospi_market("KOSPI") is False

    def test_is_kospi_market_kosdaq_code_20(self):
        """시장코드 '20' -> KOSDAQ (False)."""
        assert _is_kospi_market("20") is False


class TestKrStockAccountTrackerCreation:
    """KrStockAccountTracker 생성 테스트."""

    def _make_accno_client(self):
        """테스트용 mock accno_client 생성."""
        client = MagicMock()
        return client

    def test_basic_creation(self):
        """기본 생성 확인."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)

        assert tracker._accno_client is accno_client
        assert tracker._real_client is None
        assert tracker._refresh_interval == KrStockAccountTracker.DEFAULT_REFRESH_INTERVAL
        assert tracker._is_running is False

    def test_creation_with_real_client(self):
        """real_client 포함 생성."""
        accno_client = self._make_accno_client()
        real_client = MagicMock()
        tracker = KrStockAccountTracker(
            accno_client=accno_client,
            real_client=real_client,
        )
        assert tracker._real_client is real_client

    def test_creation_with_custom_refresh_interval(self):
        """커스텀 갱신 주기 설정."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(
            accno_client=accno_client,
            refresh_interval=30,
        )
        assert tracker._refresh_interval == 30

    def test_creation_with_custom_commission_rate(self):
        """커스텀 수수료율 설정."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(
            accno_client=accno_client,
            commission_rate=Decimal("0.0002"),
        )
        assert tracker._commission_config.commission_rate == Decimal("0.0002")

    def test_initial_state_is_empty(self):
        """초기 상태 확인 (빈 데이터)."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)

        assert tracker.get_positions() == {}
        assert tracker.get_balance() is None
        assert tracker.get_open_orders() == {}
        assert tracker.get_account_pnl() is None
        assert tracker.get_last_errors() == {}

    def test_subscribed_symbols_empty_initially(self):
        """초기 구독 종목 없음."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)
        assert tracker.subscribed_symbols == set()

    def test_commission_config_property(self):
        """commission_config 프로퍼티 접근."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)
        config = tracker.commission_config
        assert isinstance(config, KrCommissionConfig)

    def test_update_commission_config(self):
        """수수료율 업데이트."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)
        tracker.update_commission_config(commission_rate=Decimal("0.0003"))
        assert tracker._commission_config.commission_rate == Decimal("0.0003")

    def test_update_commission_config_none_does_nothing(self):
        """None으로 업데이트 시 변경 없음."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)
        original_rate = tracker._commission_config.commission_rate
        tracker.update_commission_config(commission_rate=None)
        assert tracker._commission_config.commission_rate == original_rate

    def test_on_position_change_callback_registration(self):
        """보유종목 변경 콜백 등록."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)
        callback = MagicMock()
        tracker.on_position_change(callback)
        assert callback in tracker._on_position_change_callbacks

    def test_on_balance_change_callback_registration(self):
        """예수금 변경 콜백 등록."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)
        callback = MagicMock()
        tracker.on_balance_change(callback)
        assert callback in tracker._on_balance_change_callbacks

    def test_get_current_price_not_set(self):
        """현재가 미설정 시 None 반환."""
        accno_client = self._make_accno_client()
        tracker = KrStockAccountTracker(accno_client=accno_client)
        assert tracker.get_current_price("005930") is None


class TestKrStockAccountTrackerOnTickReceived:
    """_on_tick_received() 메서드 테스트."""

    def _make_tracker(self):
        """테스트용 tracker 생성."""
        accno_client = MagicMock()
        tracker = KrStockAccountTracker(accno_client=accno_client)
        return tracker

    def _make_tick_resp(self, shcode: str, price: int):
        """mock 틱 데이터 생성."""
        resp = MagicMock()
        resp.body = MagicMock()
        resp.body.shcode = shcode
        resp.body.price = price
        return resp

    def test_tick_updates_current_price(self):
        """틱 수신 시 current_price 업데이트."""
        tracker = self._make_tracker()
        resp = self._make_tick_resp("005930", 75000)

        tracker._on_tick_received(resp)

        assert tracker.get_current_price("005930") == 75000

    def test_tick_updates_position_price(self):
        """틱 수신 시 보유종목 현재가 업데이트."""
        tracker = self._make_tracker()

        # 초기 포지션 설정
        tracker._positions["005930"] = KrStockPositionItem(
            symbol="005930",
            quantity=10,
            buy_price=70000,
            current_price=70000,
            buy_amount=700000,
            eval_amount=700000,
            market="1",
        )
        resp = self._make_tick_resp("005930", 75000)

        tracker._on_tick_received(resp)

        pos = tracker._positions["005930"]
        assert pos.current_price == 75000

    def test_tick_recalculates_eval_amount(self):
        """틱 수신 시 평가금액 재계산."""
        tracker = self._make_tracker()

        tracker._positions["005930"] = KrStockPositionItem(
            symbol="005930",
            quantity=10,
            buy_price=70000,
            current_price=70000,
            buy_amount=700000,
            eval_amount=700000,
            market="1",
        )
        resp = self._make_tick_resp("005930", 75000)

        tracker._on_tick_received(resp)

        pos = tracker._positions["005930"]
        assert pos.eval_amount == 750000  # 75000 * 10

    def test_tick_recalculates_pnl_amount(self):
        """틱 수신 시 평가손익 재계산."""
        tracker = self._make_tracker()

        tracker._positions["005930"] = KrStockPositionItem(
            symbol="005930",
            quantity=10,
            buy_price=70000,
            current_price=70000,
            buy_amount=700000,
            eval_amount=700000,
            market="1",
        )
        resp = self._make_tick_resp("005930", 75000)

        tracker._on_tick_received(resp)

        pos = tracker._positions["005930"]
        assert pos.pnl_amount == 50000  # 750000 - 700000

    def test_tick_sets_realtime_pnl(self):
        """틱 수신 시 realtime_pnl 설정 (수수료/세금 반영)."""
        tracker = self._make_tracker()

        tracker._positions["005930"] = KrStockPositionItem(
            symbol="005930",
            quantity=10,
            buy_price=70000,
            current_price=70000,
            buy_amount=700000,
            eval_amount=700000,
            market="1",
        )
        resp = self._make_tick_resp("005930", 75000)

        tracker._on_tick_received(resp)

        pos = tracker._positions["005930"]
        assert pos.realtime_pnl is not None
        assert pos.realtime_pnl.net_profit == 48432  # KOSPI 기준 수동 검증값

    def test_tick_updates_pnl_rate(self):
        """틱 수신 시 손익률 업데이트."""
        tracker = self._make_tracker()

        tracker._positions["005930"] = KrStockPositionItem(
            symbol="005930",
            quantity=10,
            buy_price=70000,
            current_price=70000,
            buy_amount=700000,
            eval_amount=700000,
            market="1",
        )
        resp = self._make_tick_resp("005930", 75000)

        tracker._on_tick_received(resp)

        pos = tracker._positions["005930"]
        assert pos.pnl_rate == pytest.approx(6.92, abs=0.01)

    def test_tick_non_position_symbol_only_updates_price(self):
        """포지션 없는 종목 틱 수신 시 current_price만 업데이트."""
        tracker = self._make_tracker()
        resp = self._make_tick_resp("999999", 10000)

        tracker._on_tick_received(resp)

        assert tracker.get_current_price("999999") == 10000
        assert "999999" not in tracker._positions

    def test_tick_none_resp_ignored(self):
        """None 응답은 무시."""
        tracker = self._make_tracker()
        # 예외 없이 정상 처리되어야 함
        tracker._on_tick_received(None)

    def test_tick_missing_body_ignored(self):
        """body 없는 응답은 무시."""
        tracker = self._make_tracker()
        resp = MagicMock()
        resp.body = None

        tracker._on_tick_received(resp)
        assert tracker.get_current_price("005930") is None

    def test_tick_missing_shcode_ignored(self):
        """shcode 없는 body는 무시."""
        tracker = self._make_tracker()
        resp = MagicMock()
        resp.body = MagicMock(spec=[])  # shcode, price 속성 없음

        tracker._on_tick_received(resp)
        assert len(tracker._current_prices) == 0

    def test_tick_calls_position_change_callback(self):
        """틱 수신 시 포지션 변경 콜백 호출."""
        tracker = self._make_tracker()
        callback = MagicMock()
        tracker.on_position_change(callback)

        tracker._positions["005930"] = KrStockPositionItem(
            symbol="005930",
            quantity=10,
            buy_price=70000,
            current_price=70000,
            buy_amount=700000,
            eval_amount=700000,
            market="1",
        )
        resp = self._make_tick_resp("005930", 75000)

        tracker._on_tick_received(resp)

        callback.assert_called_once()

    def test_tick_kosdaq_position_no_rural_tax(self):
        """KOSDAQ 종목 틱 수신 시 농특세 없음 확인."""
        tracker = self._make_tracker()

        tracker._positions["247540"] = KrStockPositionItem(
            symbol="247540",
            quantity=100,
            buy_price=5000,
            current_price=5000,
            buy_amount=500000,
            eval_amount=500000,
            market="2",  # KOSDAQ
        )
        resp = self._make_tick_resp("247540", 5500)

        tracker._on_tick_received(resp)

        pos = tracker._positions["247540"]
        assert pos.realtime_pnl is not None
        assert pos.realtime_pnl.rural_tax == 0
        assert pos.realtime_pnl.net_profit == 48852
