
from typing import Optional, Callable, Dict, Any, List

from ....tr_helpers import DEFAULT_OCCURS_MAX_PAGES, GenericTR

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    COSAQ00102InBlock1,
    COSAQ00102OutBlock1,
    COSAQ00102OutBlock2,
    COSAQ00102OutBlock3,
    COSAQ00102Request,
    COSAQ00102Response,
    COSAQ00102ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRAccnoAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS
import logging

logger = logging.getLogger("programgarden.ls.overseas_stock.accno.COSAQ00102")


class TrCOSAQ00102(TRAccnoAbstract, OccursReqAbstract):
    """LS증권 OpenAPI의 COSAQ00102 계좌 주문 내역 조회를 위한 클래스입니다.

    This class is structured to use GenericTR similar to COSAQ01400 for
    consistent request/response handling.
    """

    def __init__(self, request_data: COSAQ00102Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSAQ00102Request):
            raise TrRequestDataNotFoundException()

        # generic helper
        self._generic: GenericTR[COSAQ00102Response] = GenericTR(self.request_data, self._build_response, url=URLS.ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSAQ00102Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("COSAQ00102OutBlock1")
        block2_data = resp_json.get("COSAQ00102OutBlock2")
        block3_data = resp_json.get("COSAQ00102OutBlock3", [])
        malformed_detail = not isinstance(block3_data, list)

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = COSAQ00102ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2 = None
        parsed_block3: list[COSAQ00102OutBlock3] = []
        if exc is None and not is_error_status:
            if block1_data is not None:
                parsed_block1 = COSAQ00102OutBlock1.model_validate(block1_data)
            if block2_data is not None:
                parsed_block2 = COSAQ00102OutBlock2.model_validate(block2_data)
            if not malformed_detail:
                parsed_block3 = [COSAQ00102OutBlock3.model_validate(item) for item in block3_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"COSAQ00102 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"COSAQ00102 request failed with status: {error_msg}")
        elif malformed_detail:
            error_msg = "COSAQ00102OutBlock3 must be an array"

        result = COSAQ00102Response(
            header=header,
            block1=parsed_block1,
            block2=parsed_block2,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
            # Preserve detail-block presence while retaining the public [] default.
            **({"block3": parsed_block3} if "COSAQ00102OutBlock3" in resp_json else {}),
        )
        if resp is not None:
            result.raw_data = resp
        return result

    async def req_async(self) -> COSAQ00102Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session) -> COSAQ00102Response:
        # kept for backward compatibility
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def req(self) -> COSAQ00102Response:
        return self._generic.req()

    async def retry_req_async(self, callback: Callable[[Optional[COSAQ00102Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[COSAQ00102Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> COSAQ00102Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)

    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[COSAQ00102Response], RequestStatus], None]] = None,
        delay: int = 1,
        *,
        max_pages: int = DEFAULT_OCCURS_MAX_PAGES,
    ) -> List[COSAQ00102Response]:
        """해외주식 계좌주문체결내역 전체 페이지를 동기 방식으로 연속조회합니다.

        다음 페이지는 같은 본문에 요청 헤더 ``tr_cont="Y"`` 와 직전 응답의
        ``tr_cont_key`` 를 실어 다시 보냅니다(가이드 공통 헤더). ``SrtOrdNo`` 는 가이드에
        시작값(역순 999999999 / 정순 0)만 정의돼 있어 페이지 사이에 바꾸지 않습니다. 페이지마다 이 TR 의
        rate limit 을 지키고, 페이지 사이에 ``delay`` 초를 쉽니다.

        Returns:
            List[COSAQ00102Response]: 페이지별 응답(행을 합치지 않음). 실패한 페이지는 마지막
            원소로 남고, 키가 비었거나 반복되거나 ``max_pages`` 에 닿으면 마지막
            성공 페이지(여전히 ``tr_cont="Y"``)에서 멈춥니다. 전부 받았는지는
            ``programgarden_finance.ls.tr_helpers.occurs_complete(pages)`` 로 확인하세요.
        """
        return self._generic.header_occurs_req(callback=callback, delay=delay, max_pages=max_pages)

    async def occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[COSAQ00102Response], RequestStatus], None]] = None,
        delay: int = 1,
        *,
        max_pages: int = DEFAULT_OCCURS_MAX_PAGES,
    ) -> List[COSAQ00102Response]:
        """해외주식 계좌주문체결내역 전체 페이지를 비동기 방식으로 연속조회합니다 (``occurs_req`` 와 같은 규칙)."""
        return await self._generic.header_occurs_req_async(callback=callback, delay=delay, max_pages=max_pages)


__all__ = [
    TrCOSAQ00102,
    COSAQ00102InBlock1,
    COSAQ00102OutBlock1,
    COSAQ00102OutBlock2,
    COSAQ00102OutBlock3,
    COSAQ00102Request,
    COSAQ00102Response,
    COSAQ00102ResponseHeader
]
