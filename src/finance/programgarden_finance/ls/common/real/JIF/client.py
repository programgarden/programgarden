"""JIF (Market Status) real-time subscription client.

Supported markets: KR/US/CN/HK/JP stocks + KRX futures/options.
Overseas futures (CME, HKEx Futures, SGX, etc.) are NOT supported.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable, Dict, Optional

from .blocks import JIFRealResponse
from .constants import JANGUBUN_LABELS, JSTATUS_LABELS, resolve_jstatus, resolve_market

if TYPE_CHECKING:
    from programgarden_finance.ls.common.real import Real


class RealJIF:
    """Per-parent accessor for the JIF real-time stream.

    EN:
        Registers a listener on the parent ``Real`` WebSocket and
        maintains an in-memory snapshot keyed by ``jangubun`` so callers
        can inspect the latest session state for each of the 12
        supported markets without re-subscribing.

    KO:
        부모 ``Real`` WebSocket 에 리스너를 등록하고, jangubun 별 최신
        장운영상태 스냅샷을 메모리에 유지합니다. 호출 측은 재구독 없이
        12개 지원 시장의 현재 상태를 즉시 조회할 수 있습니다.
    """

    # shared snapshot across RealJIF instances that wrap the same parent
    # Real — callers should typically only create a single RealJIF per
    # parent, but the class-level cache keyed by id(parent) makes the
    # behaviour deterministic when multiple accessors are constructed.
    _snapshots: Dict[int, Dict[str, Dict[str, object]]] = {}

    def __init__(self, parent: "Real"):
        self._parent = parent
        self._snapshot_key = id(parent)
        RealJIF._snapshots.setdefault(self._snapshot_key, {})
        self._user_listener: Optional[Callable[[JIFRealResponse], None]] = None

    # ------------------------------------------------------------------
    # Snapshot API
    # ------------------------------------------------------------------

    def get_snapshot(self) -> Dict[str, Dict[str, object]]:
        """Return a shallow copy of the current jangubun → state map.

        EN:
            Each entry is ``{"jstatus": str, "market": str, "label": str,
            "is_regular_open": bool, "is_extended_open": bool,
            "updated_at": float}``. Unknown codes fall back to
            ``resolve_jstatus`` defaults.

        KO:
            각 항목 shape: ``{jstatus, market, label, is_regular_open,
            is_extended_open, updated_at}``. 미매핑 코드는 안전 기본값
            (닫힘) 으로 채워집니다.
        """
        return dict(RealJIF._snapshots.get(self._snapshot_key, {}))

    def get_market_state(self, market: str) -> Optional[Dict[str, object]]:
        """Look up the snapshot entry for a canonical market key.

        EN:
            ``market`` must be one of the 12 canonical keys (see
            ``SUPPORTED_MARKETS``).

        KO:
            ``market`` 은 12 개 canonical 키 중 하나여야 합니다.
        """
        for entry in RealJIF._snapshots.get(self._snapshot_key, {}).values():
            if entry.get("market") == market:
                return dict(entry)
        return None

    # ------------------------------------------------------------------
    # Subscription lifecycle
    # ------------------------------------------------------------------

    def on_jif_message(self, listener: Callable[[JIFRealResponse], None]):
        """Register a listener and start the JIF subscription.

        EN:
            Sends a ``tr_type=3`` registration with ``tr_key="0"``.
            Incoming payloads update the internal snapshot before being
            forwarded to ``listener``.

        KO:
            ``tr_type=3``, ``tr_key="0"`` 로 JIF 구독을 시작하고 리스너를
            등록합니다. 수신 payload 는 내부 스냅샷을 갱신한 뒤 사용자
            리스너로 전달됩니다.
        """
        self._user_listener = listener
        self._parent._on_message("JIF", self._dispatch)
        self._parent._add_message_symbols(["0"], "JIF")

    def on_remove_jif_message(self):
        """Unsubscribe and drop the registered listener.

        EN:
            Sends a ``tr_type=4`` deregistration with ``tr_key="0"`` and
            removes the listener. The snapshot cache is preserved so
            recent state remains inspectable.

        KO:
            ``tr_type=4`` 해제 전송 후 리스너를 제거합니다. 스냅샷은
            유지하여 마지막 상태를 계속 조회 가능하도록 둡니다.
        """
        try:
            self._parent._remove_message_symbols(["0"], "JIF")
        finally:
            self._parent._on_remove_message("JIF")
            self._user_listener = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _dispatch(self, resp: JIFRealResponse) -> None:
        """Update snapshot + forward to user listener."""
        try:
            body = getattr(resp, "body", None)
            if body is not None:
                jangubun = str(getattr(body, "jangubun", "") or "")
                jstatus = str(getattr(body, "jstatus", "") or "")
                if jangubun:
                    status_info = resolve_jstatus(jstatus)
                    snap = RealJIF._snapshots.setdefault(self._snapshot_key, {})
                    snap[jangubun] = {
                        "jangubun": jangubun,
                        "market": resolve_market(jangubun),
                        "jstatus": jstatus,
                        "label": status_info["label"],
                        "is_regular_open": status_info["is_regular_open"],
                        "is_extended_open": status_info["is_extended_open"],
                        "updated_at": time.time(),
                    }
        except Exception:
            # never let snapshot bookkeeping break message delivery
            pass

        if self._user_listener is None:
            return
        try:
            self._user_listener(resp)
        except Exception:
            # user listener exceptions should not tear down the recv loop
            pass


__all__ = [
    "RealJIF",
    "JANGUBUN_LABELS",
    "JSTATUS_LABELS",
]
