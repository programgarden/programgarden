"""전일대비(change) 부호 정규화 — LS TR 별 부호 규칙 차이를 흡수한다.

실측 근거 (2026-07-13, 실 LS 키로 직접 TR 호출):
    g3101 (해외주식) NVDA   sign='5'  diff='2.4100'   rate=-1.14   → diff 는 절댓값
    t1102 (국내주식) 005930 sign='5'  change=30500    diff=-10.70  → change 는 절댓값
    o3105 (해외선물) HBIN26 YdiffSign='5' YdiffP=-105.0 Diff=-0.75 → YdiffP 는 이미 부호 포함

핵심 불변식: **change 의 부호와 change_pct(등락률)의 부호는 항상 같다.**
(등락률은 세 TR 모두 부호를 갖고 오므로, change 가 틀어지면 둘의 부호가 어긋난다.)
"""
import pytest

from programgarden.executor import _ls_signed_change


class TestAbsoluteMagnitudeGetsSign:
    """g3101 / t1102 — 크기가 절댓값이라 sign 을 적용해야 한다."""

    def test_g3101_down_makes_change_negative(self):
        # NVDA 실측: sign='5'(하락), diff='2.4100' (절댓값)
        assert _ls_signed_change("2.4100", "5") == -2.41

    def test_g3101_up_keeps_change_positive(self):
        # AAPL 실측: sign='2'(상승), diff='5.1400'
        assert _ls_signed_change("5.1400", "2") == 5.14

    def test_t1102_down_makes_change_negative(self):
        # 삼성전자 실측: sign='5', change=30500 (절댓값)
        assert _ls_signed_change(30500, "5") == -30500.0

    @pytest.mark.parametrize("sign", ["4", "5", "-"])
    def test_all_down_codes_force_negative(self, sign):
        assert _ls_signed_change(10, sign) == -10.0

    @pytest.mark.parametrize("sign", ["1", "2", "+"])
    def test_all_up_codes_force_positive(self, sign):
        assert _ls_signed_change(10, sign) == 10.0


class TestAlreadySignedMagnitudeIsPreserved:
    """o3105 — 이미 부호가 실려 오므로 뒤집으면 안 된다 (멱등)."""

    def test_o3105_signed_negative_stays_negative(self):
        # HBIN26 실측: YdiffSign='5', YdiffP=-105.0 (이미 음수)
        assert _ls_signed_change(-105.0, "5") == -105.0

    def test_o3105_signed_positive_stays_positive(self):
        assert _ls_signed_change(0.0052, "2") == 0.0052

    def test_idempotent(self):
        once = _ls_signed_change(-105.0, "5")
        twice = _ls_signed_change(once, "5")
        assert once == twice == -105.0


class TestUnknownSignDoesNotCorrupt:
    """방향 코드가 없거나 알 수 없으면 원값의 부호를 신뢰한다 (멋대로 양수화 금지)."""

    @pytest.mark.parametrize("sign", ["", None, "9", "  "])
    def test_unknown_sign_passes_value_through(self, sign):
        assert _ls_signed_change(-105.0, sign) == -105.0
        assert _ls_signed_change(105.0, sign) == 105.0

    def test_flat_sign_zero(self):
        # 3 = 보합 → 값이 0 이라 통과시켜도 무해
        assert _ls_signed_change(0, "3") == 0.0


class TestMalformedInput:
    def test_none_magnitude(self):
        assert _ls_signed_change(None, "5") == 0.0

    def test_empty_string_magnitude(self):
        assert _ls_signed_change("", "5") == 0.0

    def test_garbage_magnitude(self):
        assert _ls_signed_change("N/A", "5") == 0.0


class TestSignInvariant:
    """이 결함의 본질 — change 와 change_pct 의 부호는 항상 같아야 한다."""

    @pytest.mark.parametrize(
        "magnitude,sign,rate",
        [
            ("2.4100", "5", -1.14),   # g3101 NVDA (절댓값 + 하락)
            ("5.1400", "2", 1.63),    # g3101 AAPL (절댓값 + 상승)
            (30500, "5", -10.70),     # t1102 삼성전자 (절댓값 + 하락)
            (-105.0, "5", -0.75),     # o3105 HBIN26 (이미 부호 + 하락)
            (0.0052, "2", 0.08),      # o3105 CUSQ26 (이미 부호 + 상승)
        ],
    )
    def test_change_and_pct_agree_in_sign(self, magnitude, sign, rate):
        change = _ls_signed_change(magnitude, sign)
        assert change != 0
        assert (change < 0) == (rate < 0), (
            f"change={change} 와 등락률={rate} 의 부호가 어긋났다 "
            f"(magnitude={magnitude!r}, sign={sign!r})"
        )
