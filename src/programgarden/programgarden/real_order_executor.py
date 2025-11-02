"""Real-time order websocket integration for Programgarden.

EN:
        Bridges LS finance websocket callbacks to community plugins and the global
        :mod:`programgarden.pg_listener`. Incoming events are normalized into
        unified order types and routed to plugin instances or queued until the
        instance registers itself.

KR:
        LS 금융 웹소켓 콜백을 커뮤니티 플러그인과 글로벌
        :mod:`programgarden.pg_listener`로 연결합니다. 수신한 이벤트를 일관된 주문
        유형으로 변환한 뒤 플러그인 인스턴스로 전달하거나 등록 대기 큐에 보관합니다.
"""

import asyncio
import threading
from typing import Any, Dict, List, Optional, Union
from programgarden_finance import LS, AS0, AS1, AS2, AS3, AS4, TC1, TC2, TC3
from programgarden_core import (
    OrderRealResponseType, SystemType, order_logger,
    BaseOrderOverseasStock, BaseOrderOverseasFutures,
)
from programgarden.pg_listener import pg_listener


class RealOrderExecutor:
    """Consume real-time order events and notify registered listeners.

    EN:
        Connects to LS websocket channels, keeps track of plugin instances that
        originated orders, and delivers streaming updates back to them.

    KR:
        LS 웹소켓 채널에 연결하여 주문을 생성한 플러그인 인스턴스를 추적하고, 실시간
        업데이트를 다시 전달합니다.
    """

    def __init__(self):
        # EN: Map order numbers to originating plugin instances for callbacks.
        # KR: 주문 번호별로 원본 플러그인 인스턴스를 기록해 콜백에 사용합니다.
        self._order_community_instance_map: Dict[str, Any] = {}
        # EN: Pending messages buffered until an instance registers.
        # KR: 인스턴스 등록 전 대기 중인 메시지를 버퍼링합니다.
        self._pending_order_messages: Dict[str, List[Dict[Any, Any]]] = {}
        # EN: Protect maps because LS callbacks may run on non-async threads.
        # KR: LS 콜백이 비동기 외부 스레드에서 실행될 수 있어 락으로 보호합니다.
        self._lock = threading.Lock()

    async def real_order_websockets(
        self,
        system: SystemType,
    ):
        """Establish websocket subscriptions for the given system.

        EN:
            Chooses the appropriate LS real-time client based on product type,
            wires message handlers, and blocks until ``stop`` is invoked.

        KR:
            상품 유형에 따라 LS 실시간 클라이언트를 선택하고 메시지 핸들러를 연결한 뒤
            ``stop`` 호출 전까지 대기합니다.
        """

        securities = system.get("securities", {})
        company = securities.get("company", None)
        product = securities.get("product", "overseas_stock")
        if len(system.get("orders", [])) > 0 and company == "ls":
            if product == "overseas_stock":
                self.buy_sell_order_real = LS.get_instance().overseas_stock().real()
            elif product == "overseas_futures":
                self.buy_sell_order_real = LS.get_instance().overseas_futureoption().real()
            else:
                order_logger.warning(f"Unsupported product for real order websocket: {product}")
                return

            await self.buy_sell_order_real.connect()

            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None

            if product == "overseas_stock":
                self.buy_sell_order_real.AS0().on_as0_message(listener=self._as0_message_dispatcher)
                self.buy_sell_order_real.AS1().on_as1_message(listener=self._as1_message_dispatcher)
                self.buy_sell_order_real.AS2().on_as2_message(listener=self._as2_message_dispatcher)
                self.buy_sell_order_real.AS3().on_as3_message(listener=self._as3_message_dispatcher)
                self.buy_sell_order_real.AS4().on_as4_message(listener=self._as4_message_dispatcher)
            else:
                self.buy_sell_order_real.TC1().on_tc1_message(listener=self._tc1_message_dispatcher)
                self.buy_sell_order_real.TC2().on_tc2_message(listener=self._tc2_message_dispatcher)
                self.buy_sell_order_real.TC3().on_tc3_message(listener=self._tc3_message_dispatcher)

            self._stop_event = asyncio.Event()
            await self._stop_event.wait()

    def _as0_message_dispatcher(
        self,
        response: AS0.AS0RealResponse
    ):
        """Handle AS0 (order submission) messages from LS.

        EN:
            Normalizes the response into Programgarden order types, forwards to
            registered plugins, and emits through :mod:`pg_listener`.

        KR:
            실시간 주문 응답이며, 응답을 Programgarden 주문 유형으로 정규화하여 플러그인과
            :mod:`pg_listener`에 전달합니다.
        """
        try:
            ordNo = response.body.sOrdNo
            if ordNo is None:
                return

            ord_key = str(ordNo)
            payload = response.model_dump()

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 접수 완료",
                "response": payload,
            })

        except Exception as e:
            order_logger.error(e)

    def _as1_message_dispatcher(
        self,
        response: AS1.AS1RealResponse
    ) -> None:
        """Handle AS1 (fill) messages and clear completed orders.

        EN:
            Removes order registrations once unexecuted quantity reaches zero and
            emits both plugin callbacks and global listener notifications.

        KR:
            미체결 수량이 0이 되면 등록 정보를 정리하고, 플러그인 콜백 및 글로벌
            리스너 알림을 전송합니다.
        """
        try:
            ordNo = response.body.sOrdNo
            if ordNo is None:
                return

            ord_key = str(ordNo)
            payload = response.model_dump()

            if response.body.sUnercQty == 0:
                # 주문이 모두 체결되었으므로 더 이상 메시지를 받을 필요가 없음
                self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 체결 완료",
                "response": payload,
            })

        except Exception:
            order_logger.exception("Error in AS1 dispatcher")

    def _as2_message_dispatcher(
        self,
        response: AS2.AS2RealResponse
    ) -> None:
        """Handle AS2 (modification) messages and notify listeners.

        EN:
            Converts modification responses into unified order types and forwards
            them to registered callbacks and listeners.

        KR:
            정정 응답을 일관된 주문 유형으로 변환하여 등록된 콜백과 리스너에 전달합니다.
        """
        try:
            sOrdNo = response.body.sOrdNo
            if sOrdNo is None:
                return

            ord_key = str(sOrdNo)
            payload = response.model_dump()

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 정정 완료",
                "response": payload,
            })

        except Exception:
            order_logger.exception("Error in AS2 dispatcher")

    def _as3_message_dispatcher(
        self,
        response: AS3.AS3RealResponse
    ) -> None:
        """Handle AS3 (cancellation completion) messages and clean registrations.

        EN:
            Removes the associated plugin instance and broadcasts cancellation
            completion to observers.

        KR:
            관련 플러그인 인스턴스를 제거하고 취소 완료를 옵저버에 전파합니다.
        """
        try:
            ordNo = response.body.sOrdNo
            if ordNo is None:
                return

            ord_key = str(ordNo)

            payload = response.model_dump()

            self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 취소 완료",
                "response": payload,
            })

        except Exception:
            order_logger.exception("Error in AS3 dispatcher")

    def _as4_message_dispatcher(
        self,
        response: AS4.AS4RealResponse
    ) -> None:
        """Handle AS4 (rejection) messages and drop stale registrations.

        EN:
            Processes rejection payloads, cleans the instance cache, and emits a
            rejection event for UI/log consumers.

        KR:
            거절 페이로드를 처리하고 인스턴스 캐시를 정리한 뒤 UI/로그 소비자를 위한
            거절 이벤트를 발행합니다.
        """
        try:
            ordNo = response.body.sOrdNo
            if ordNo is None:
                return

            ord_key = str(ordNo)
            # pass a dict (model_dump) so the dispatcher can treat the
            # response uniformly (it expects a dict-like object)
            payload = response.model_dump()

            self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 거부됨",
                "response": payload,
            })
        except Exception:
            order_logger.exception("Error in AS4 dispatcher")

    def _tc1_message_dispatcher(
        self,
        response: TC1.TC1RealResponse
    ) -> None:
        """Handle TC1 (futures submission) real-time messages.

        EN:
            Dispatches futures submission notifications to plugin callbacks and the
            listener bridge.

        KR:
            선물 주문 접수 알림을 플러그인 콜백과 리스너 브리지로 전달합니다.
        """
        try:
            if response.body is None:
                return

            ord_no = getattr(response.body, "ordr_no", None)
            ord_key = str(ord_no) if ord_no else None
            payload = response.model_dump()

            order_type = self._futures_order_type("TC1", payload.get("body", {}))

            if ord_key:
                self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)

            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": payload.get("rsp_msg") or self._order_message_from_type(order_type),
                "response": payload,
            })

        except Exception:
            order_logger.exception("Error in TC1 dispatcher")

    def _tc2_message_dispatcher(
        self,
        response: TC2.TC2RealResponse
    ) -> None:
        """Handle TC2 (futures modification/rejection) messages.

        EN:
            Determines whether the payload represents a modification or rejection,
            updates registrations accordingly, and emits structured events.

        KR:
            페이로드가 정정인지 거절인지 판별해 등록 상태를 갱신하고 구조화된 이벤트를
            발행합니다.
        """
        try:
            if response.body is None:
                return

            ord_no = getattr(response.body, "ordr_no", None)
            ord_key = str(ord_no) if ord_no else None
            payload = response.model_dump()

            order_type = self._futures_order_type("TC2", payload.get("body", {}))

            if ord_key:
                self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
                if order_type in {"reject_buy", "reject_sell"}:
                    self._order_community_instance_map.pop(ord_key, None)

            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": payload.get("rsp_msg") or self._order_message_from_type(order_type),
                "response": payload,
            })

        except Exception:
            order_logger.exception("Error in TC2 dispatcher")

    def _tc3_message_dispatcher(
        self,
        response: TC3.TC3RealResponse
    ) -> None:
        """Handle TC3 (futures fill/cancel completion) messages.

        EN:
            Cleans cached instances after fills or cancel completions and forwards
            standardized payloads to observers.

        KR:
            체결/취소 완료 이후 캐시된 인스턴스를 정리하고 표준화된 페이로드를 옵저버에
            전달합니다.
        """
        try:
            if response.body is None:
                return

            ord_no = getattr(response.body, "ordr_no", None)
            ord_key = str(ord_no) if ord_no else None
            payload = response.model_dump()

            order_type = self._futures_order_type("TC3", payload.get("body", {}))

            if ord_key:
                self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
                if order_type in {"filled_new_buy", "filled_new_sell", "cancel_complete_buy", "cancel_complete_sell"}:
                    self._order_community_instance_map.pop(ord_key, None)

            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": payload.get("rsp_msg") or self._order_message_from_type(order_type),
                "response": payload,
            })

        except Exception:
            order_logger.exception("Error in TC3 dispatcher")

    async def send_data_community_instance(
        self,
        ordNo: str,
        community_instance: Optional[Union[BaseOrderOverseasStock, BaseOrderOverseasFutures]],
    ) -> None:
        """Register an instance and flush queued order messages.

        EN:
            Associates the given order number with the plugin instance and replays
            buffered messages in FIFO order, invoking synchronous or asynchronous
            handlers accordingly.

        KR:
            전달된 주문 번호를 플러그인 인스턴스와 연결하고, 대기 중인 메시지를 FIFO
            순서로 재생하여 동기/비동기 핸들러를 알맞게 호출합니다.
        """
        if ordNo:
            # register the community instance (may be None)
            with self._lock:
                self._order_community_instance_map[ordNo] = community_instance

                # peek pending messages for this ordNo. Only remove (pop)
                # them if we're actually going to deliver them. If the
                # community_instance is None we should keep queued messages
                # for later registration instead of dropping them.
                pending = None
                if community_instance is not None:
                    # remove pending list so future dispatches won't re-append
                    pending = self._pending_order_messages.pop(ordNo, None)

            if pending and community_instance is not None:
                for real_order_response in pending:
                    # compute order type from the pending message and deliver
                    order_type = self._determine_order_type_from_payload(real_order_response)
                    handler = getattr(community_instance, "on_real_order_receive", None)
                    if handler:
                        # asyncio.iscoroutinefunction returns False for bound
                        # instance methods in some Python versions, so check
                        # the underlying function if present.
                        func_to_check = getattr(handler, "__func__", handler)
                        if asyncio.iscoroutinefunction(func_to_check):
                            await handler(order_type, real_order_response)
                        else:
                            await asyncio.to_thread(handler, order_type, real_order_response)

    def __dispatch_real_order_message(
        self,
        ord_key: str,
        response: Dict[str, Any],
        order_type: Optional[OrderRealResponseType] = None,
    ) -> None:
        """Dispatch or queue order responses based on registration state.

        EN:
            Delivers payloads to registered plugin callbacks using the preserved
            event loop when possible. Unregistered orders accumulate in a pending
            queue until the instance calls ``send_data_community_instance``.

        KR:
            등록된 플러그인 콜백이 있으면 저장된 이벤트 루프를 활용해 페이로드를 전달하고,
            아직 등록되지 않은 주문은 ``send_data_community_instance`` 호출 전까지 대기
            큐에 적재합니다.
        """

        if order_type is None:
            order_type = self._determine_order_type_from_payload(response)

        instance = self._order_community_instance_map.get(ord_key)
        if instance:
            handler = getattr(instance, "on_real_order_receive", None)

            if handler:
                loop: Optional[asyncio.AbstractEventLoop] = getattr(self, "_loop", None)
                # handle bound coroutine methods by checking __func__ fallback
                func_to_check = getattr(handler, "__func__", handler)
                if asyncio.iscoroutinefunction(func_to_check):
                    coro = handler(order_type, response)

                    if loop is not None and getattr(loop, "is_running", lambda: False)():
                        try:
                            asyncio.run_coroutine_threadsafe(coro, loop)
                        except Exception:
                            order_logger.exception("Failed to schedule coroutine with run_coroutine_threadsafe")
                    else:
                        # try to create task on current running loop (if any)
                        try:
                            asyncio.create_task(coro)
                        except RuntimeError:
                            # no running loop at all; run the coroutine in a new thread
                            import threading

                            def _run_coro_in_thread(c):
                                try:
                                    asyncio.run(c)
                                except Exception:
                                    order_logger.exception("Error running coroutine in fallback thread")

                            threading.Thread(target=_run_coro_in_thread, args=(coro,), daemon=True).start()
                else:
                    # synchronous handler: run in thread, prefer scheduling via loop
                    if loop is not None and getattr(loop, "is_running", lambda: False)():
                        try:
                            # schedule creation of a background task that runs the sync handler
                            loop.call_soon_threadsafe(asyncio.create_task, asyncio.to_thread(handler, order_type, response))
                        except Exception:
                            order_logger.exception("Failed to schedule sync handler on loop; running in thread")
                            import threading

                            threading.Thread(target=handler, args=(order_type, response), daemon=True).start()
                    else:
                        # no loop available, run handler in its own thread
                        import threading

                        threading.Thread(target=handler, args=(order_type, response), daemon=True).start()
        else:
            # queue message until instance is registered
            self._pending_order_messages.setdefault(ord_key, []).append(response)

    def _order_type_from_response(self, bns_tp: str, ord_xct_ptn_code: str) -> Optional[OrderRealResponseType]:
        """Derive a unified order type from AS-series stock responses.

        EN:
            Maps LS buy/sell codes into Programgarden's normalized order type strings
            to keep downstream processing consistent.

        KR:
            LS 매수/매도 코드를 Programgarden의 표준화된 주문 유형 문자열로 변환하여
            후속 처리를 일관되게 유지합니다.
        """
        try:
            order_category_type: Optional[OrderRealResponseType] = None
            if bns_tp == "2":
                if ord_xct_ptn_code == "01":
                    order_category_type = "submitted_new_buy"
                elif ord_xct_ptn_code == "11":
                    order_category_type = "filled_new_buy"
                elif ord_xct_ptn_code == "03":
                    order_category_type = "cancel_request_buy"
                elif ord_xct_ptn_code == "12":
                    order_category_type = "modify_buy"
                elif ord_xct_ptn_code == "13":
                    order_category_type = "cancel_complete_buy"
                elif ord_xct_ptn_code == "14":
                    order_category_type = "reject_buy"
            elif bns_tp == "1":
                if ord_xct_ptn_code == "01":
                    order_category_type = "submitted_new_sell"
                elif ord_xct_ptn_code == "11":
                    order_category_type = "filled_new_sell"
                elif ord_xct_ptn_code == "03":
                    order_category_type = "cancel_request_sell"
                elif ord_xct_ptn_code == "12":
                    order_category_type = "modify_sell"
                elif ord_xct_ptn_code == "13":
                    order_category_type = "cancel_complete_sell"
                elif ord_xct_ptn_code == "14":
                    order_category_type = "reject_sell"
            return order_category_type
        except Exception:
            order_logger.exception("Error computing order_category_type from response")
            return None

    def _futures_order_type(self, tr_cd: Optional[str], body: Dict[str, Any]) -> Optional[OrderRealResponseType]:
        """Map overseas futures payloads to unified order type values.

        EN:
            Normalizes futures transaction codes and side codes into the same order
            type vocabulary used for equities.

        KR:
            선물 거래 코드와 매수/매도 코드를 주식과 동일한 주문 유형 어휘로 정규화합니다.
        """

        if not body:
            return None

        side_code = str(body.get("s_b_ccd", "") or "").strip()
        is_buy = side_code == "2"

        def choose(buy: OrderRealResponseType, sell: OrderRealResponseType) -> OrderRealResponseType:
            return buy if is_buy else sell

        order_code = str(body.get("ordr_ccd", "") or "").strip()
        tr_cd = (tr_cd or "").upper().strip()

        if tr_cd == "TC1":
            return choose("submitted_new_buy", "submitted_new_sell")

        if tr_cd == "TC2":
            reject_code = str(body.get("rfsl_cd", "") or "").strip()
            if reject_code and reject_code not in {"0", "00"}:
                return choose("reject_buy", "reject_sell")

            if order_code in {"1", "01"}:
                return choose("modify_buy", "modify_sell")
            if order_code in {"2", "02"}:
                return choose("cancel_buy", "cancel_sell")
            return choose("submitted_new_buy", "submitted_new_sell")

        if tr_cd == "TC3":
            if order_code in {"2", "02"}:
                return choose("cancel_complete_buy", "cancel_complete_sell")
            return choose("filled_new_buy", "filled_new_sell")

        return None

    def _determine_order_type_from_payload(self, payload: Dict[str, Any]) -> Optional[OrderRealResponseType]:
        """Infer order type from generic real-time payloads.

        EN:
            Inspects TR codes and body fields to detect whether the payload
            originates from stock or futures streams and delegates to the
            appropriate mapper.

        KR:
            TR 코드와 바디 필드를 검사해 페이로드가 주식 또는 선물 스트림에서 온 것인지
            판별하고, 알맞은 매퍼로 위임합니다.
        """

        if not payload:
            return None

        body: Dict[str, Any] = payload.get("body") or {}
        header: Dict[str, Any] = payload.get("header") or {}
        tr_cd = header.get("tr_cd")

        if tr_cd and str(tr_cd).upper().startswith("AS"):
            return self._order_type_from_response(
                bns_tp=body.get("sBnsTp", ""),
                ord_xct_ptn_code=body.get("sOrdxctPtnCode", ""),
            )

        if tr_cd and str(tr_cd).upper().startswith("TC"):
            return self._futures_order_type(tr_cd, body)

        if "sBnsTp" in body or "sOrdxctPtnCode" in body:
            return self._order_type_from_response(
                bns_tp=body.get("sBnsTp", ""),
                ord_xct_ptn_code=body.get("sOrdxctPtnCode", ""),
            )

        if "s_b_ccd" in body:
            return self._futures_order_type(tr_cd, body)

        return None

    def _order_message_from_type(self, order_type: Optional[OrderRealResponseType]) -> str:
        """Provide human-friendly fallback messages for emitted order events.

        EN:
            Supplies localized defaults for real-order emissions when the upstream
            payload lacks a user-facing message.

        KR:
            상위 페이로드에 사용자 메시지가 없을 때 실시간 주문 이벤트에 사용할 기본
            메시지를 제공합니다.
        """

        message_map = {
            "submitted_new_buy": "주문 접수 완료",
            "submitted_new_sell": "주문 접수 완료",
            "filled_new_buy": "주문 체결 완료",
            "filled_new_sell": "주문 체결 완료",
            "cancel_request_buy": "주문 취소 접수",
            "cancel_request_sell": "주문 취소 접수",
            "modify_buy": "주문 정정 완료",
            "modify_sell": "주문 정정 완료",
            "cancel_complete_buy": "주문 취소 완료",
            "cancel_complete_sell": "주문 취소 완료",
            "reject_buy": "주문 거부됨",
            "reject_sell": "주문 거부됨",
        }

        return message_map.get(order_type, "주문 이벤트")
