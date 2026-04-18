"""Mock JIF WebSocket server for offline verification.

EN:
    Spawns a local WebSocket server that speaks the JIF (Market Status)
    TR protocol well enough for the ``RealJIF`` client to connect,
    subscribe (``tr_type="3"``), receive simulated ``JIFRealResponse``
    payloads, and unsubscribe (``tr_type="4"``). The goal is to verify
    the Phase 1–3 pipeline without waiting for a weekday KST daytime
    window — the request/response schema is fully specified by LS
    Securities docs, so scripted payloads are sufficient.

KO:
    JIF(장운영정보) 실시간 TR 프로토콜을 모사하는 로컬 WebSocket 서버.
    `RealJIF` 클라이언트가 정상 구독/해제 흐름을 타고, 시뮬레이션된
    `JIFRealResponse` payload 를 수신할 수 있도록 설계. Phase 1~3
    파이프라인을 **주말/장외 시간에도 검증**할 수 있게 합니다.

Protocol handshake summary
--------------------------
1. Client sends a JIFRealRequest (tr_type="3", tr_key="0").
2. Server immediately responds with an ACK (no body, rsp_cd="00000").
3. Server then pushes per-scenario JIFRealResponse payloads:
   ``{"header": {"tr_cd": "JIF", "rsp_cd": "00000"},
     "body": {"jangubun": <code>, "jstatus": <code>}}``
4. Client eventually sends a JIFRealRequest with tr_type="4"
   (unsubscribe). Server cancels the scenario task and emits an ACK.

Usage
-----

.. code-block:: python

    async with MockJIFServer(scenario_weekday_us_open_kr_close) as srv:
        tm = TokenManager(access_token="stub", wss_url=srv.wss_url)
        common = Common(token_manager=tm)
        real = common.real()
        await real.connect()
        jif = real.JIF()
        jif.on_jif_message(lambda resp: ...)
        await asyncio.sleep(0.5)  # let scenario play out
        snapshot = jif.get_snapshot()
        jif.on_remove_jif_message()
        await real.close()
"""

from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable, List, Optional

from websockets.asyncio.server import Server, ServerConnection, serve

ScenarioFn = Callable[[ServerConnection], Awaitable[None]]


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


class MockJIFServer:
    """Lightweight asynchronous JIF WebSocket mock.

    EN:
        Binds to an ephemeral port on ``host`` (default ``localhost``) so
        concurrent tests do not collide. Access the chosen port through
        the ``wss_url`` property after the async context manager opens.

    KO:
        ``host`` 의 임시 포트에 바인딩하여 동시 실행 테스트 간 포트
        충돌을 방지합니다. 열린 뒤 ``wss_url`` 속성으로 클라이언트에
        전달할 URL 을 얻을 수 있습니다.
    """

    def __init__(
        self,
        scenario: Optional[ScenarioFn] = None,
        host: str = "localhost",
    ) -> None:
        self.scenario: ScenarioFn = scenario or scenario_timeout
        self.host = host
        self.port: Optional[int] = None

        self._server: Optional[Server] = None
        self._scenario_tasks: List[asyncio.Task] = []
        self._received_messages: List[dict] = []

    # ---- lifecycle ----

    async def __aenter__(self) -> "MockJIFServer":
        self._server = await serve(self._handle, self.host, 0)
        # First socket's port is the listening port.
        sock_info = next(iter(self._server.sockets)).getsockname()
        self.port = sock_info[1]
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def close(self) -> None:
        for task in self._scenario_tasks:
            if not task.done():
                task.cancel()
        for task in self._scenario_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._scenario_tasks.clear()

        if self._server is not None:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:
                pass
            self._server = None

    # ---- public inspection ----

    @property
    def wss_url(self) -> str:
        if self.port is None:
            raise RuntimeError("MockJIFServer not started — port unknown.")
        return f"ws://{self.host}:{self.port}"

    @property
    def received_messages(self) -> List[dict]:
        """Request payloads the server has observed so far.

        EN:
            Useful for asserting that the client sent the correct
            ``tr_type="3"`` subscribe followed by ``tr_type="4"``
            unsubscribe messages.

        KO:
            클라이언트가 구독/해제 순서대로 메시지를 보냈는지 확인하는
            용도로 사용합니다.
        """

        return list(self._received_messages)

    # ---- server-side handler ----

    async def _handle(self, ws: ServerConnection) -> None:
        scenario_task: Optional[asyncio.Task] = None
        try:
            async for raw_msg in ws:
                if isinstance(raw_msg, bytes):
                    raw_msg = raw_msg.decode("utf-8", errors="replace")
                try:
                    msg = json.loads(raw_msg)
                except json.JSONDecodeError:
                    continue

                self._received_messages.append(msg)

                header = msg.get("header", {}) or {}
                body = msg.get("body", {}) or {}
                tr_cd = body.get("tr_cd") or header.get("tr_cd", "")
                tr_type = header.get("tr_type", "")
                tr_key = body.get("tr_key", "")

                # Always ACK — matches the real server behaviour.
                await ws.send(
                    json.dumps(
                        {
                            "header": {
                                "tr_cd": tr_cd or "JIF",
                                "tr_key": tr_key,
                                "tr_type": tr_type,
                                "rsp_cd": "00000",
                                "rsp_msg": "정상처리되었습니다",
                            },
                            "body": None,
                        }
                    )
                )

                if tr_cd == "JIF" and tr_type == "3":
                    # Start streaming scenario events.
                    scenario_task = asyncio.create_task(self.scenario(ws))
                    self._scenario_tasks.append(scenario_task)
                elif tr_cd == "JIF" and tr_type == "4":
                    # Cancel streaming on unsubscribe.
                    if scenario_task is not None and not scenario_task.done():
                        scenario_task.cancel()
        except Exception:
            # connection closed / reset — normal shutdown
            pass


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


async def _send_event(
    ws: ServerConnection,
    jangubun: str,
    jstatus: str,
    *,
    delay: float = 0.03,
) -> None:
    """Emit a JIFRealResponse payload after ``delay`` seconds."""

    await asyncio.sleep(delay)
    payload = {
        "header": {
            "tr_cd": "JIF",
            "tr_key": "0",
            "tr_type": "3",
            "rsp_cd": "00000",
            "rsp_msg": "정상처리되었습니다",
        },
        "body": {"jangubun": jangubun, "jstatus": jstatus},
    }
    await ws.send(json.dumps(payload))


async def scenario_weekday_us_open_kr_close(ws: ServerConnection) -> None:
    """KST 저녁(22:30경) 시뮬레이션: 미국 정규장 개장 + 한국 장 마감."""

    for jangubun, jstatus in (
        ("9", "21"),  # US Market open
        ("1", "41"),  # KOSPI closed
        ("2", "41"),  # KOSDAQ closed
        ("5", "41"),  # KRX_FUTURES closed
        ("C", "21"),  # HK_AM still open (late afternoon edge)
    ):
        await _send_event(ws, jangubun, jstatus)


async def scenario_kr_opening_sequence(ws: ServerConnection) -> None:
    """KOSPI 09:00 개장 카운트다운: 장시작전 → 10분/5분/1분/10초 → open."""

    for jangubun, jstatus in (
        ("1", "11"),  # Pre-open auction started
        ("1", "22"),  # 10 min before open
        ("1", "23"),  # 5 min before open
        ("1", "24"),  # 1 min before open
        ("1", "25"),  # 10 sec before open
        ("1", "21"),  # Market open
    ):
        await _send_event(ws, jangubun, jstatus)


async def scenario_circuit_breaker(ws: ServerConnection) -> None:
    """KOSPI 정규장 중 CB level 1 발동 시뮬레이션."""

    await _send_event(ws, "1", "21")   # Open
    await _send_event(ws, "1", "61", delay=0.08)  # CB level 1 (regular_open=False)


async def scenario_extended_hours(ws: ServerConnection) -> None:
    """미국 시장 프리마켓 → 정규장 전이 시뮬레이션."""

    await _send_event(ws, "9", "41")               # Closed
    await _send_event(ws, "9", "55", delay=0.06)   # Pre-market opened
    await _send_event(ws, "9", "21", delay=0.06)   # Regular market open


async def scenario_timeout(ws: ServerConnection) -> None:
    """아무 이벤트도 보내지 않는 비활성 시나리오 (timeout 경로 검증용)."""

    try:
        await asyncio.sleep(60)
    except asyncio.CancelledError:
        raise
