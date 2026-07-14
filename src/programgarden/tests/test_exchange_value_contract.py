"""거래소 표기 **값** 계약 — 2026-07-14 결함3.

기존 test_output_schema_contract 는 **키**만 본다(AST). 그래서 47 passed 인데도 라이브에서
같은 종목의 exchange 가 REST='NASDAQ'(이름) vs tracker='82'(코드)로 갈렸다. 이 테스트는
**값 표현까지** 단언한다:
- 정규화 헬퍼가 코드·영문·한글·yfinance 를 (영문 표시명, LS 코드)로 결정적 변환.
- REST/tracker 두 producer 갈래가 같은 소스에서 **같은 값**을 낸다.
- 구독 소비자는 미매핑 거래소를 조용히 기본값으로 떨구지 않고 종목·거래소 명시하며 raise.
"""
import inspect
import pytest

from programgarden.executor import (
    normalize_overseas_stock_exchange,
    overseas_stock_exchange_pair,
    RealAccountNodeExecutor,
    RealMarketDataNodeExecutor,
)


class TestExchangeNormalization:
    @pytest.mark.parametrize("raw,name,code", [
        ("82", "NASDAQ", "82"),
        ("81", "NYSE", "81"),
        ("NASDAQ", "NASDAQ", "82"),
        ("NYSE", "NYSE", "81"),
        ("AMEX", "AMEX", "81"),          # ⚠️ AMEX 코드는 81 (83 은 유령)
        ("나스닥", "NASDAQ", "82"),
        ("뉴욕", "NYSE", "81"),
        ("아멕스", "AMEX", "81"),
        ("NMS", "NASDAQ", "82"),
        ("NYQ", "NYSE", "81"),
        ("ASE", "AMEX", "81"),
    ])
    def test_known_values_map_to_english_name_and_ls_code(self, raw, name, code):
        assert normalize_overseas_stock_exchange(raw) == (name, code)

    def test_83_is_a_phantom_code(self):
        """LS 는 AMEX 를 81 로 준다. 83 은 반환/수용하지 않는 유령 코드다."""
        assert normalize_overseas_stock_exchange("83") == (None, None)

    def test_no_korean_leaks_into_data(self):
        """정규화 결과의 표시명은 항상 영문(한글 입력이어도)."""
        name, _ = normalize_overseas_stock_exchange("나스닥")
        assert name == "NASDAQ"
        assert not any("가" <= ch <= "힣" for ch in name)  # 한글 없음

    def test_unmappable_producer_preserves_code_never_korean(self):
        # 미지 LS 코드 → 코드 보존, 한글 아님
        assert overseas_stock_exchange_pair("85") == ("85", "85")
        # 이름형 미지(도쿄) → 데이터에 안 박음(빈 값)
        assert overseas_stock_exchange_pair("도쿄") == ("", "")


class TestProducerBranchesAgreeOnValue:
    def test_rest_and_tracker_derive_exchange_from_same_helper(self):
        """REST 스냅샷·tracker 두 갈래가 **같은 정규화 헬퍼**로 exchange 를 만든다 —
        같은 market_code 면 값이 갈릴 수 없다(라이브에서 갈렸던 그 결함의 재발 방지)."""
        for method in ("_get_overseas_stock_tracker_data", "_ls_stock_with_tracker"):
            src = inspect.getsource(getattr(RealAccountNodeExecutor, method))
            assert "overseas_stock_exchange_pair(" in src, (
                f"{method} 가 공통 정규화 헬퍼를 쓰지 않는다 — 값 드리프트 위험"
            )

    def test_tracker_positions_value_representation(self):
        """tracker 갈래: market_code '82' → exchange='NASDAQ', exchange_code='82'."""
        class _Pos:
            quantity = 10
            current_price = 100.0
            buy_price = 90.0
            pnl_rate = 5.0
            pnl_amount = 100.0
            eval_amount = 1000.0
            market_code = "82"
            symbol_name = "AUID"
            currency_code = "USD"

        class _Tracker:
            def get_positions(self):
                return {"AUID": _Pos()}
            def get_balances(self):
                return {}
            def get_open_orders(self):
                return {}

        out = RealAccountNodeExecutor()._get_overseas_stock_tracker_data(_Tracker())
        pos = out["positions"][0]
        assert pos["exchange"] == "NASDAQ"
        assert pos["exchange_code"] == "82"
        held = out["held_symbols"][0]
        assert held["exchange"] == "NASDAQ" and held["exchange_code"] == "82"


class TestSubscriptionConsumerRaisesOnUnmappable:
    def test_name_and_code_both_resolve_to_ls_code(self):
        r = RealMarketDataNodeExecutor()
        assert r._get_stock_exchange_code("NASDAQ", "", "AUID") == "82"
        assert r._get_stock_exchange_code("", "82", "AUID") == "82"
        assert r._get_stock_exchange_code("AMEX", "", "X") == "81"  # AMEX→81

    def test_empty_defaults_to_nasdaq(self):
        assert RealMarketDataNodeExecutor()._get_stock_exchange_code("", "", "X") == "82"

    def test_unmappable_raises_with_symbol_and_exchange(self):
        r = RealMarketDataNodeExecutor()
        with pytest.raises(RuntimeError) as ei:
            r._get_stock_exchange_code("도쿄", "", "7203")
        msg = str(ei.value)
        assert "7203" in msg and "도쿄" in msg  # 종목·거래소 명시(뭉뚱그림 금지)
