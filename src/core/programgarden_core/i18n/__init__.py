"""
ProgramGarden Core - Internationalization (i18n)

Provides translation support for user-facing texts such as node names,
descriptions, and error messages.

Usage:
    from programgarden_core.i18n import t, set_locale, get_locale

    # Set global locale
    set_locale("ko")

    # Translate a key
    t("nodes.WatchlistNode.description")  # → "사용자 정의 관심종목 리스트"

    # With locale parameter (overrides global)
    t("nodes.WatchlistNode.description", locale="en")  # → "User-defined watchlist"
"""

from programgarden_core.i18n.translator import (
    Translator,
    t,
    set_locale,
    get_locale,
    get_available_locales,
    translate_schema,
    translate_category,
)

__all__ = [
    "Translator",
    "t",
    "set_locale",
    "get_locale",
    "get_available_locales",
    "translate_schema",
    "translate_category",
]
