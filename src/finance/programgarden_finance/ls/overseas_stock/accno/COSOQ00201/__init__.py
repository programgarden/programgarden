
from typing import Optional, Callable, Dict, Any

from ....tr_helpers import GenericTR

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    COSOQ00201InBlock1,
    COSOQ00201OutBlock1,
    COSOQ00201OutBlock2,
    COSOQ00201OutBlock3,
    COSOQ00201OutBlock4,
    COSOQ00201Request,
    COSOQ00201Response,
    COSOQ00201ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS
import logging

logger = logging.getLogger("programgarden.ls.overseas_stock.accno.COSOQ00201")


class TrCOSOQ00201(TRAccnoAbstract):
    """LS openAPI의 COSOQ00201 해외주식 종합잔고평가를 조회하는 클래스입니다.

    Uses GenericTR to standardize request/response flow.
    """

    def __init__(self, request_data: COSOQ00201Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSOQ00201Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[COSOQ00201Response] = GenericTR(self.request_data, self._build_response, url=URLS.ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSOQ00201Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("COSOQ00201OutBlock1")
        block2_data = resp_json.get("COSOQ00201OutBlock2")
        block3_data = resp_json.get("COSOQ00201OutBlock3", [])
        block4_data = resp_json.get("COSOQ00201OutBlock4", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = COSOQ00201ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2 = None
        parsed_block3: list[COSOQ00201OutBlock3] = []
        parsed_block4: list[COSOQ00201OutBlock4] = []
        parse_failures: list[str] = []

        def _parse_rows(model, rows, block_name):
            # One malformed row must not wipe out the whole balance response
            # (prod 2026-08-24: a single fractional row killed every position).
            parsed = []
            for idx, item in enumerate(rows or []):
                try:
                    parsed.append(model.model_validate(item))
                except Exception as row_exc:
                    parse_failures.append(f"{block_name}[{idx}]: {row_exc}")
                    logger.error(
                        f"COSOQ00201 {block_name} row {idx} parse failed — skipping row: {row_exc}; raw={item}"
                    )
            return parsed

        if exc is None and not is_error_status:
            if block1_data is not None:
                try:
                    parsed_block1 = COSOQ00201OutBlock1.model_validate(block1_data)
                except Exception as blk_exc:
                    parse_failures.append(f"OutBlock1: {blk_exc}")
                    logger.error(f"COSOQ00201 OutBlock1 parse failed — dropping block: {blk_exc}")
            if block2_data is not None:
                try:
                    parsed_block2 = COSOQ00201OutBlock2.model_validate(block2_data)
                except Exception as blk_exc:
                    parse_failures.append(f"OutBlock2: {blk_exc}")
                    logger.error(f"COSOQ00201 OutBlock2 parse failed — dropping block: {blk_exc}")
            parsed_block3 = _parse_rows(COSOQ00201OutBlock3, block3_data, "OutBlock3")
            parsed_block4 = _parse_rows(COSOQ00201OutBlock4, block4_data, "OutBlock4")

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"COSOQ00201 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"COSOQ00201 request failed with status: {error_msg}")
        else:
            # A block that had data but lost every row is a real failure; a few
            # skipped rows among survivors stays a warning carried on
            # ``parse_warnings`` (error_msg on a partially parsed response would
            # make consumers treat it as total failure).
            for block_name, raw_rows, parsed_rows in (
                ("OutBlock3", block3_data, parsed_block3),
                ("OutBlock4", block4_data, parsed_block4),
            ):
                if raw_rows and not parsed_rows:
                    error_msg = (
                        f"response parse error: every {block_name} row failed to parse "
                        f"({len(raw_rows)} rows) — first: {parse_failures[0] if parse_failures else 'unknown'}"
                    )
                    logger.error(f"COSOQ00201 {error_msg}")
                    break
            # OutBlock2(잔고 요약)가 있었는데 통째로 잃었으면 진짜 실패다 — 무음
            # 처리하면 예수금/평가금이 0 원으로 조용히 나간다(적대 리뷰 #2).
            # OutBlock1 은 입력 에코라 소실돼도 로그로 충분하다.
            if error_msg is None and block2_data is not None and parsed_block2 is None:
                error_msg = (
                    "response parse error: OutBlock2 (balance summary) failed to "
                    f"parse — {parse_failures[0] if parse_failures else 'unknown'}"
                )
                logger.error(f"COSOQ00201 {error_msg}")

        result = COSOQ00201Response(
            header=header,
            block1=parsed_block1,
            block2=parsed_block2,
            block3=parsed_block3,
            block4=parsed_block4,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
            parse_warnings=parse_failures,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    async def req_async(self) -> COSOQ00201Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session) -> COSOQ00201Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def req(self) -> COSOQ00201Response:
        return self._generic.req()

    async def retry_req_async(self, callback: Callable[[Optional[COSOQ00201Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[COSOQ00201Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> COSOQ00201Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCOSOQ00201,
    COSOQ00201InBlock1,
    COSOQ00201OutBlock1,
    COSOQ00201OutBlock2,
    COSOQ00201Request,
    COSOQ00201Response,
    COSOQ00201ResponseHeader
]
