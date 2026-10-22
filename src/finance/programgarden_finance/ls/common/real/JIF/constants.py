"""JIF constants — jangubun (market) and jstatus (session state) labels.

EN:
    These mappings are used by the AI agent layer, by logs, and by
    technical dashboards. Labels are kept in English only (no i18n split)
    since they are not consumer-facing UI text — platform UI receives its
    translations via the core ``i18n/locales`` files, not via these
    constants.

KO:
    AI/로그/기술 테이블 용도의 영문 단일 label 사전. 사용자 UI 다국어
    대상이 아니므로 i18n 분리하지 않으며, 플랫폼 한국어 UI 는 core
    패키지의 ``i18n/locales`` 에서 처리합니다.
"""

from typing import Dict, List


# ---------------------------------------------------------------------------
# JANGUBUN — 12 supported markets
# ---------------------------------------------------------------------------

JANGUBUN_LABELS: Dict[str, Dict[str, str]] = {
    "1": {"market": "KOSPI",        "label": "KOSPI (Korea)"},
    "2": {"market": "KOSDAQ",       "label": "KOSDAQ (Korea)"},
    "5": {"market": "KRX_FUTURES",  "label": "KRX Futures/Options"},
    "6": {"market": "NXT",          "label": "NXT Exclusive"},
    "8": {"market": "KRX_NIGHT",    "label": "KRX Night Derivatives"},
    "9": {"market": "US",           "label": "US Stock"},
    "A": {"market": "CN_AM",        "label": "China Stock AM"},
    "B": {"market": "CN_PM",        "label": "China Stock PM"},
    "C": {"market": "HK_AM",        "label": "HK Stock AM"},
    "D": {"market": "HK_PM",        "label": "HK Stock PM"},
    "E": {"market": "JP_AM",        "label": "Japan Stock AM"},
    "F": {"market": "JP_PM",        "label": "Japan Stock PM"},
}


SUPPORTED_MARKETS: List[str] = [info["market"] for info in JANGUBUN_LABELS.values()]


MARKET_TO_JANGUBUN: Dict[str, str] = {
    info["market"]: code for code, info in JANGUBUN_LABELS.items()
}


def resolve_market(jangubun: str) -> str:
    """Translate a jangubun code to a canonical market key.

    EN:
        Returns the 12 canonical keys (KOSPI, US, HK_AM, etc.) or the raw
        jangubun code when unknown. Callers should compare against
        ``SUPPORTED_MARKETS`` before trusting the mapping.

    KO:
        jangubun 코드를 12개 canonical market 키로 변환합니다. 알 수 없는
        코드는 원본 jangubun 문자열을 그대로 반환하므로, 호출 측은
        ``SUPPORTED_MARKETS`` 로 유효성을 검증해야 합니다.
    """
    info = JANGUBUN_LABELS.get(jangubun)
    if info is None:
        return jangubun
    return info["market"]


# ---------------------------------------------------------------------------
# JSTATUS — session state codes
# ---------------------------------------------------------------------------
#
# Labels are broker-provided English descriptions. ``is_regular_open``
# indicates whether regular trading is live (strict gate for order entry).
# ``is_extended_open`` includes pre-market / after-hours sessions so
# display nodes can surface "market is busy" states.
#
# Coverage target per plan: 40+ codes (common + KOSPI/KOSDAQ-specific +
# futures/options-specific). Entries may be extended as live traffic
# reveals additional codes.

JSTATUS_LABELS: Dict[str, Dict[str, object]] = {
    # ── Common: pre-open / opening sequence (11, 21~25) ──
    "11": {"label": "Pre-open auction started",         "is_regular_open": False, "is_extended_open": False},
    "21": {"label": "Market open",                      "is_regular_open": True,  "is_extended_open": True},
    "22": {"label": "Market open in 10 minutes",        "is_regular_open": False, "is_extended_open": False},
    "23": {"label": "Market open in 5 minutes",         "is_regular_open": False, "is_extended_open": False},
    "24": {"label": "Market open in 1 minute",          "is_regular_open": False, "is_extended_open": False},
    "25": {"label": "Market open in 10 seconds",        "is_regular_open": False, "is_extended_open": False},

    # ── Common: closing sequence (31, 41~44) ──
    "31": {"label": "Market close imminent",            "is_regular_open": True,  "is_extended_open": True},
    "41": {"label": "Market closed",                    "is_regular_open": False, "is_extended_open": False},
    "42": {"label": "Market closes in 10 minutes",      "is_regular_open": True,  "is_extended_open": True},
    "43": {"label": "Market closes in 5 minutes",       "is_regular_open": True,  "is_extended_open": True},
    "44": {"label": "Market closes in 1 minute",        "is_regular_open": True,  "is_extended_open": True},

    # ── Common: after-hours / pre-market (51~58) ──
    "51": {"label": "After-hours session opened (closing price)",    "is_regular_open": False, "is_extended_open": True},
    "52": {"label": "After-hours single-price session opened",       "is_regular_open": False, "is_extended_open": True},
    "54": {"label": "After-hours session closed (closing price)",    "is_regular_open": False, "is_extended_open": False},
    "55": {"label": "Pre-market opened",                             "is_regular_open": False, "is_extended_open": True},
    "56": {"label": "After-market opened",                           "is_regular_open": False, "is_extended_open": True},
    "57": {"label": "Pre-market closed",                             "is_regular_open": False, "is_extended_open": False},
    "58": {"label": "After-market closed",                           "is_regular_open": False, "is_extended_open": False},

    # ── KOSPI/KOSDAQ-specific: circuit breakers / sidecar / VI (61~71) ──
    "61": {"label": "Circuit breaker level 1",          "is_regular_open": False, "is_extended_open": False},
    "62": {"label": "Circuit breaker level 2",          "is_regular_open": False, "is_extended_open": False},
    "63": {"label": "Circuit breaker level 3",          "is_regular_open": False, "is_extended_open": False},
    "64": {"label": "Sidecar buy triggered",            "is_regular_open": True,  "is_extended_open": True},
    "65": {"label": "Sidecar sell triggered",           "is_regular_open": True,  "is_extended_open": True},
    "66": {"label": "Sidecar released",                 "is_regular_open": True,  "is_extended_open": True},
    "67": {"label": "VI (volatility interruption) triggered", "is_regular_open": True, "is_extended_open": True},
    "68": {"label": "VI released",                      "is_regular_open": True,  "is_extended_open": True},
    "71": {"label": "Trading halt",                     "is_regular_open": False, "is_extended_open": False},

    # ── Futures/options-specific (70, 72~77) ──
    "70": {"label": "Futures/options intraday extension", "is_regular_open": True,  "is_extended_open": True},
    "72": {"label": "Futures circuit breaker triggered",  "is_regular_open": False, "is_extended_open": False},
    "73": {"label": "Futures circuit breaker released",   "is_regular_open": True,  "is_extended_open": True},
    "74": {"label": "Derivatives dynamic VI triggered",   "is_regular_open": True,  "is_extended_open": True},
    "75": {"label": "Derivatives dynamic VI released",    "is_regular_open": True,  "is_extended_open": True},
    "76": {"label": "Derivatives static VI triggered",    "is_regular_open": True,  "is_extended_open": True},
    "77": {"label": "Derivatives static VI released",     "is_regular_open": True,  "is_extended_open": True},

    # ── Extended-hours session boundaries (A2~A5 / B2~B5 / C2~C5 / D2~D5) ──
    "A2": {"label": "Pre-market opens in 10 minutes",   "is_regular_open": False, "is_extended_open": False},
    "A3": {"label": "Pre-market opens in 5 minutes",    "is_regular_open": False, "is_extended_open": False},
    "A4": {"label": "Pre-market opens in 1 minute",     "is_regular_open": False, "is_extended_open": False},
    "A5": {"label": "Pre-market opens in 10 seconds",   "is_regular_open": False, "is_extended_open": False},
    "B2": {"label": "Pre-market closes in 10 minutes",  "is_regular_open": False, "is_extended_open": True},
    "B3": {"label": "Pre-market closes in 5 minutes",   "is_regular_open": False, "is_extended_open": True},
    "B4": {"label": "Pre-market closes in 1 minute",    "is_regular_open": False, "is_extended_open": True},
    "B5": {"label": "Pre-market closes in 10 seconds",  "is_regular_open": False, "is_extended_open": True},
    "C2": {"label": "After-market opens in 10 minutes", "is_regular_open": False, "is_extended_open": False},
    "C3": {"label": "After-market opens in 5 minutes",  "is_regular_open": False, "is_extended_open": False},
    "C4": {"label": "After-market opens in 1 minute",   "is_regular_open": False, "is_extended_open": False},
    "C5": {"label": "After-market opens in 10 seconds", "is_regular_open": False, "is_extended_open": False},
    "D2": {"label": "After-market closes in 10 minutes", "is_regular_open": False, "is_extended_open": True},
    "D3": {"label": "After-market closes in 5 minutes",  "is_regular_open": False, "is_extended_open": True},
    "D4": {"label": "After-market closes in 1 minute",   "is_regular_open": False, "is_extended_open": True},
    "D5": {"label": "After-market closes in 10 seconds", "is_regular_open": False, "is_extended_open": True},
}


def resolve_jstatus(jstatus: str) -> Dict[str, object]:
    """Return label + open flags for a jstatus code.

    EN:
        Unknown codes resolve to a generic "Unknown status ({code})"
        entry with both open flags set to ``False`` so callers default
        to the safe (closed) interpretation.

    KO:
        매핑되지 않은 코드는 안전 기본값(닫힘)으로 반환합니다. 매핑 누락
        감지 시 후속 릴리스에서 표에 추가 보강합니다.
    """
    entry = JSTATUS_LABELS.get(jstatus)
    if entry is None:
        return {
            "label": f"Unknown status ({jstatus})",
            "is_regular_open": False,
            "is_extended_open": False,
        }
    return entry


__all__ = [
    "JANGUBUN_LABELS",
    "JSTATUS_LABELS",
    "SUPPORTED_MARKETS",
    "MARKET_TO_JANGUBUN",
    "resolve_market",
    "resolve_jstatus",
]
