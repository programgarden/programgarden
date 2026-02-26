"""
24개 국내주식 TR 코드 자동 생성기
가이드 파일을 파싱하여 blocks.py와 __init__.py를 생성합니다.
"""
import os
import re
from pathlib import Path

GUIDE_DIR = Path("ls_finance_korea_stock_guide")
BASE_DIR = Path("programgarden_finance/ls/korea_stock")

# TR → (category, url_const, rate_limit_count, rate_limit_seconds)
TR_CONFIG = {
    "t1482": ("ranking", "KOREA_STOCK_HIGH_ITEM_URL", 1, 1),
    "t1511": ("market", "KOREA_STOCK_MARKET_URL", 10, 1),
    "t1516": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1531": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1532": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1537": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1601": ("market", "KOREA_STOCK_MARKET_URL", 2, 1),
    "t1602": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1603": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1617": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1621": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1638": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1664": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1665": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1702": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1901": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1903": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1904": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1927": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t1941": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t8407": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
    "t8452": ("chart", "KOREA_STOCK_CHART_URL", 1, 1),
    "t8453": ("chart", "KOREA_STOCK_CHART_URL", 1, 1),
    "t8454": ("market", "KOREA_STOCK_MARKET_URL", 1, 1),
}


def find_guide_file(tr_code):
    """Find the openAPI guide file for a TR code."""
    for f in GUIDE_DIR.iterdir():
        if f.name.startswith(tr_code) and "openAPI" in f.name:
            return f
    return None


def parse_guide(filepath):
    """Parse a guide file and extract block structures."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    # Extract TR name from first line
    tr_name = lines[0].split("\t")[0].strip() if lines else ""

    # Find blocks
    blocks = {}
    current_block = None
    in_response = False

    for line in lines:
        line_stripped = line.strip()

        if line_stripped == "응답":
            in_response = True
            continue

        if not in_response:
            # Parse request InBlock
            if "InBlock" in line_stripped and "Object" in line_stripped:
                block_name = line_stripped.split("\t")[0].strip()
                current_block = block_name
                blocks[current_block] = {"fields": [], "is_array": "Array" in line_stripped, "is_request": True}
                continue
            if current_block and current_block.endswith("InBlock") and line_stripped.startswith("-"):
                _parse_field(line_stripped, blocks[current_block])
                continue
            if current_block and not line_stripped.startswith("-") and not line_stripped.startswith("  -"):
                if "InBlock" not in line_stripped:
                    current_block = None

        if in_response:
            if "OutBlock" in line_stripped and ("Object" in line_stripped):
                parts = line_stripped.split("\t")
                block_name = parts[0].strip()
                is_array = "Array" in line_stripped
                current_block = block_name
                blocks[current_block] = {"fields": [], "is_array": is_array, "is_request": False}
                continue

            if current_block and line_stripped.startswith("-"):
                _parse_field(line_stripped, blocks[current_block])
                continue

            if line_stripped.startswith("Example") or line_stripped.startswith("Request"):
                current_block = None

    return tr_name, blocks


def _parse_field(line, block):
    """Parse a field line like '  -fieldname\t한글명\ttype\tY\tLength\tDescription'"""
    line = line.lstrip("- ")
    parts = line.split("\t")
    if len(parts) < 4:
        return

    field_name = parts[0].strip()
    korean_name = parts[1].strip() if len(parts) > 1 else ""
    field_type = parts[2].strip() if len(parts) > 2 else "String"
    length = parts[4].strip() if len(parts) > 4 else ""

    # Determine Python type
    if field_type == "Number":
        if "." in length:
            py_type = "float"
            default = "0.0"
        else:
            py_type = "int"
            default = "0"
    elif field_type == "Object":
        py_type = "int"
        default = "0"
    else:
        py_type = "str"
        default = '""'

    block["fields"].append({
        "name": field_name,
        "korean": korean_name,
        "type": py_type,
        "default": default,
    })


def generate_blocks_py(tr_code, tr_name, blocks, config):
    """Generate blocks.py content."""
    TR = tr_code.upper() if tr_code.startswith("t") else tr_code
    TR_cap = tr_code[0].upper() + tr_code[1:] if tr_code[0].islower() else tr_code
    # Use actual case: T1482, T1511, etc.
    class_prefix = tr_code[0].upper() + tr_code[1:]

    # Find block names
    inblock_name = None
    outblocks = {}
    for bname, bdata in blocks.items():
        if "InBlock" in bname:
            inblock_name = bname
        elif "OutBlock" in bname:
            outblocks[bname] = bdata

    lines = []
    lines.append('from typing import Literal, Optional')
    lines.append('')
    lines.append('from pydantic import BaseModel, PrivateAttr, Field')
    lines.append('from requests import Response')
    lines.append('')
    lines.append('from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions')
    lines.append('')
    lines.append('')

    # RequestHeader
    lines.append(f'class {class_prefix}RequestHeader(BlockRequestHeader):')
    lines.append(f'    """{class_prefix} 요청용 Header"""')
    lines.append('    pass')
    lines.append('')
    lines.append('')

    # ResponseHeader
    lines.append(f'class {class_prefix}ResponseHeader(BlockResponseHeader):')
    lines.append(f'    """{class_prefix} 응답용 Header"""')
    lines.append('    pass')
    lines.append('')
    lines.append('')

    # InBlock
    if inblock_name and inblock_name in blocks:
        inblock = blocks[inblock_name]
        real_inblock_name = inblock_name.replace(tr_code, class_prefix)
        lines.append(f'class {real_inblock_name}(BaseModel):')
        lines.append(f'    """{tr_name} 입력 블록"""')
        for field in inblock["fields"]:
            lines.append(f'    {field["name"]}: {field["type"]} = Field(default={field["default"]}, description="{field["korean"]}")')
        lines.append('')
        lines.append('')

    # OutBlocks
    for bname, bdata in sorted(outblocks.items()):
        real_bname = bname.replace(tr_code, class_prefix)
        lines.append(f'class {real_bname}(BaseModel):')
        lines.append(f'    """{tr_name} 출력 블록 - {bname}"""')
        if not bdata["fields"]:
            lines.append('    pass')
        else:
            for field in bdata["fields"]:
                lines.append(f'    {field["name"]}: {field["type"]} = Field(default={field["default"]}, description="{field["korean"]}")')
        lines.append('')
        lines.append('')

    # Request model
    rate_count = config[2]
    rate_seconds = config[3]
    real_inblock_name_for_req = inblock_name.replace(tr_code, class_prefix) if inblock_name else f"{class_prefix}InBlock"
    lines.append(f'class {class_prefix}Request(BaseModel):')
    lines.append(f'    """{tr_name} 요청 모델"""')
    lines.append(f'    header: {class_prefix}RequestHeader = {class_prefix}RequestHeader()')
    lines.append(f'    body: dict = {{}}')
    lines.append(f'    options: SetupOptions = SetupOptions(rate_limit_count={rate_count}, rate_limit_seconds={rate_seconds})')
    lines.append(f'    _raw_data: Optional[Response] = PrivateAttr(default=None)')
    lines.append('')
    lines.append('')

    # Response model
    sorted_outblock_names = sorted(outblocks.keys())
    lines.append(f'class {class_prefix}Response(BaseModel):')
    lines.append(f'    """{tr_name} 응답 모델"""')
    lines.append(f'    header: Optional[{class_prefix}ResponseHeader] = None')

    for bname in sorted_outblock_names:
        bdata = outblocks[bname]
        real_bname = bname.replace(tr_code, class_prefix)
        suffix = bname.replace(f"{tr_code}OutBlock", "")

        if bdata["is_array"]:
            field_name = "block" if (suffix == "1" or (suffix == "" and len(sorted_outblock_names) == 1)) else f"block{suffix}"
            if suffix == "" and len(sorted_outblock_names) > 1:
                field_name = "cont_block"  # Single OutBlock with OutBlock1 = continuation
            lines.append(f'    {field_name}: list[{real_bname}] = []')
        else:
            if suffix == "" and len(sorted_outblock_names) > 1:
                field_name = "cont_block"
            elif suffix == "":
                field_name = "block"
            else:
                field_name = f"block{suffix}"
            if suffix == "" and len(sorted_outblock_names) > 1:
                lines.append(f'    {field_name}: Optional[{real_bname}] = None')
            else:
                lines.append(f'    {field_name}: Optional[{real_bname}] = None')

    lines.append(f'    rsp_cd: str = ""')
    lines.append(f'    rsp_msg: str = ""')
    lines.append(f'    status_code: Optional[int] = None')
    lines.append(f'    error_msg: Optional[str] = None')
    lines.append(f'    raw_data: Optional[object] = None')
    lines.append('')
    lines.append('')

    # __all__
    all_names = [f'{class_prefix}RequestHeader', f'{class_prefix}ResponseHeader']
    if inblock_name:
        all_names.append(inblock_name.replace(tr_code, class_prefix))
    for bname in sorted_outblock_names:
        all_names.append(bname.replace(tr_code, class_prefix))
    all_names.extend([f'{class_prefix}Request', f'{class_prefix}Response'])

    lines.append('__all__ = [')
    for name in all_names:
        lines.append(f'    "{name}",')
    lines.append(']')
    lines.append('')

    return "\n".join(lines)


def generate_init_py(tr_code, tr_name, blocks, config):
    """Generate __init__.py content."""
    class_prefix = tr_code[0].upper() + tr_code[1:]
    category = config[0]
    url_const = config[1]

    # Determine block structure
    outblocks = {k: v for k, v in blocks.items() if "OutBlock" in k and "InBlock" not in k}
    sorted_outblock_names = sorted(outblocks.keys())

    inblock_name = None
    for bname in blocks:
        if "InBlock" in bname:
            inblock_name = bname
    real_inblock_name = inblock_name.replace(tr_code, class_prefix) if inblock_name else f"{class_prefix}InBlock"

    # Determine if it has continuation (OccursReq)
    has_continuation = False
    cont_key_field = None
    cont_block_fields = []

    if len(sorted_outblock_names) >= 2:
        # OutBlock (no number suffix) + OutBlock1 = continuation pattern
        base_outblock = f"{tr_code}OutBlock"
        if base_outblock in outblocks and not outblocks[base_outblock]["is_array"]:
            has_continuation = True
            cont_block_fields = outblocks[base_outblock]["fields"]
            # Find the continuation key field
            for f in cont_block_fields:
                if f["name"] in ("idx", "cts_shcode", "cts_time", "cts_date", "shcode", "cts_idx"):
                    cont_key_field = f["name"]
                    break
            if not cont_key_field and cont_block_fields:
                cont_key_field = cont_block_fields[0]["name"]

    # Build imports
    import_names = [real_inblock_name]
    for bname in sorted_outblock_names:
        import_names.append(bname.replace(tr_code, class_prefix))
    import_names.extend([f'{class_prefix}Request', f'{class_prefix}Response', f'{class_prefix}ResponseHeader'])

    lines = []
    lines.append('from typing import Callable, Optional, Dict, Any')
    lines.append('')
    lines.append('import aiohttp')
    lines.append('')
    lines.append('from programgarden_core.exceptions import TrRequestDataNotFoundException')
    lines.append('import logging')
    lines.append('')
    lines.append(f'logger = logging.getLogger("programgarden.ls.korea_stock.{category}.{tr_code}")')
    lines.append('from .blocks import (')
    for name in import_names:
        lines.append(f'    {name},')
    lines.append(')')

    if has_continuation:
        lines.append('from ....tr_base import OccursReqAbstract, TRRequestAbstract')
    else:
        lines.append('from ....tr_base import TRRequestAbstract')

    lines.append('from ....tr_helpers import GenericTR')
    lines.append('from programgarden_finance.ls.config import URLS')
    if has_continuation:
        lines.append('from programgarden_finance.ls.status import RequestStatus')
    lines.append('')
    lines.append('')

    # Class
    base_classes = "TRRequestAbstract, OccursReqAbstract" if has_continuation else "TRRequestAbstract"
    lines.append(f'class Tr{class_prefix}({base_classes}):')
    lines.append(f'    """')
    lines.append(f'    LS증권 OpenAPI {tr_code} {tr_name} 클래스입니다.')
    lines.append(f'    """')
    lines.append('')
    lines.append(f'    def __init__(self, request_data: {class_prefix}Request):')
    lines.append(f'        super().__init__(')
    lines.append(f'            rate_limit_count=request_data.options.rate_limit_count,')
    lines.append(f'            rate_limit_seconds=request_data.options.rate_limit_seconds,')
    lines.append(f'            on_rate_limit=request_data.options.on_rate_limit,')
    lines.append(f'            rate_limit_key=request_data.options.rate_limit_key,')
    lines.append(f'        )')
    lines.append(f'        self.request_data = request_data')
    lines.append(f'        if not isinstance(self.request_data, {class_prefix}Request):')
    lines.append(f'            raise TrRequestDataNotFoundException()')
    lines.append(f'        self._generic: GenericTR[{class_prefix}Response] = GenericTR[{class_prefix}Response](self.request_data, self._build_response, url=URLS.{url_const})')
    lines.append('')

    # _build_response
    lines.append(f'    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> {class_prefix}Response:')
    lines.append(f'        resp_json = resp_json or {{}}')

    # Parse each outblock from response
    for bname in sorted_outblock_names:
        bdata = outblocks[bname]
        suffix = bname.replace(f"{tr_code}OutBlock", "")
        if bdata["is_array"]:
            lines.append(f'        {bname}_data = resp_json.get("{bname}", [])')
        else:
            lines.append(f'        {bname}_data = resp_json.get("{bname}", None)')

    lines.append('')
    lines.append(f'        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None')
    lines.append(f'        is_error_status = status is not None and status >= 400')
    lines.append('')
    lines.append(f'        header = None')
    lines.append(f'        if exc is None and resp_headers and not is_error_status:')
    lines.append(f'            header = {class_prefix}ResponseHeader.model_validate(resp_headers)')
    lines.append('')

    # Parse each block
    for bname in sorted_outblock_names:
        bdata = outblocks[bname]
        real_bname = bname.replace(tr_code, class_prefix)
        suffix = bname.replace(f"{tr_code}OutBlock", "")

        if bdata["is_array"]:
            var_name = f"parsed_{bname}"
            lines.append(f'        {var_name}: list[{real_bname}] = []')
            lines.append(f'        if exc is None and not is_error_status:')
            lines.append(f'            {var_name} = [{real_bname}.model_validate(item) for item in {bname}_data]')
        else:
            var_name = f"parsed_{bname}"
            lines.append(f'        {var_name}: Optional[{real_bname}] = None')
            lines.append(f'        if exc is None and not is_error_status and {bname}_data:')
            lines.append(f'            {var_name} = {real_bname}.model_validate({bname}_data)')
        lines.append('')

    # Error handling
    lines.append(f'        error_msg: Optional[str] = None')
    lines.append(f'        if exc is not None:')
    lines.append(f'            error_msg = str(exc)')
    lines.append(f'            logger.error(f"{tr_code} request failed: {{exc}}")')
    lines.append(f'        elif is_error_status:')
    lines.append(f'            error_msg = f"HTTP {{status}}"')
    lines.append(f'            if resp_json.get("rsp_msg"):')
    lines.append(f"""            error_msg = f"{{error_msg}}: {{resp_json['rsp_msg']}}" """.rstrip())
    lines.append(f'            logger.error(f"{tr_code} request failed with status: {{error_msg}}")')
    lines.append('')

    # Build result
    lines.append(f'        result = {class_prefix}Response(')
    lines.append(f'            header=header,')

    for bname in sorted_outblock_names:
        bdata = outblocks[bname]
        suffix = bname.replace(f"{tr_code}OutBlock", "")
        var_name = f"parsed_{bname}"

        if bdata["is_array"]:
            field_name = "block" if (suffix == "1" or (suffix == "" and len(sorted_outblock_names) == 1)) else f"block{suffix}"
            if suffix == "" and len(sorted_outblock_names) > 1:
                field_name = "cont_block"
        else:
            if suffix == "" and len(sorted_outblock_names) > 1:
                field_name = "cont_block"
            elif suffix == "":
                field_name = "block"
            else:
                field_name = f"block{suffix}"

        lines.append(f'            {field_name}={var_name},')

    lines.append(f'            rsp_cd=resp_json.get("rsp_cd", ""),')
    lines.append(f'            rsp_msg=resp_json.get("rsp_msg", ""),')
    lines.append(f'            status_code=status,')
    lines.append(f'            error_msg=error_msg,')
    lines.append(f'        )')
    lines.append(f'        if resp is not None:')
    lines.append(f'            result.raw_data = resp')
    lines.append(f'        return result')
    lines.append('')

    # req methods
    lines.append(f'    def req(self) -> {class_prefix}Response:')
    lines.append(f'        return self._generic.req()')
    lines.append('')
    lines.append(f'    async def req_async(self) -> {class_prefix}Response:')
    lines.append(f'        return await self._generic.req_async()')
    lines.append('')
    lines.append(f'    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> {class_prefix}Response:')
    lines.append(f'        if hasattr(self._generic, "_req_async_with_session"):')
    lines.append(f'            return await self._generic._req_async_with_session(session)')
    lines.append(f'        return await self._generic.req_async()')
    lines.append('')

    # occurs_req methods (if has continuation)
    if has_continuation:
        # Find continuation update fields
        update_lines = []
        for f in cont_block_fields:
            fname = f["name"]
            update_lines.append(f'            req_data.body["{inblock_name}"].{fname} = resp.cont_block.{fname}')

        lines.append(f'    def occurs_req(self, callback: Optional[Callable[[Optional[{class_prefix}Response], RequestStatus], None]] = None, delay: int = 1) -> list[{class_prefix}Response]:')
        lines.append(f'        """동기 방식으로 {tr_name} 전체를 연속조회합니다."""')
        lines.append(f'        def _updater(req_data, resp: {class_prefix}Response):')
        lines.append(f'            if resp.header is None or resp.cont_block is None:')
        lines.append(f'                raise ValueError("{tr_code} response missing continuation data")')
        lines.append(f'            req_data.header.tr_cont_key = resp.header.tr_cont_key')
        lines.append(f'            req_data.header.tr_cont = resp.header.tr_cont')
        for ul in update_lines:
            lines.append(ul)
        lines.append(f'        return self._generic.occurs_req(_updater, callback=callback, delay=delay)')
        lines.append('')
        lines.append(f'    async def occurs_req_async(self, callback: Optional[Callable[[Optional[{class_prefix}Response], RequestStatus], None]] = None, delay: int = 1) -> list[{class_prefix}Response]:')
        lines.append(f'        """비동기 방식으로 {tr_name} 전체를 연속조회합니다."""')
        lines.append(f'        def _updater(req_data, resp: {class_prefix}Response):')
        lines.append(f'            if resp.header is None or resp.cont_block is None:')
        lines.append(f'                raise ValueError("{tr_code} response missing continuation data")')
        lines.append(f'            req_data.header.tr_cont_key = resp.header.tr_cont_key')
        lines.append(f'            req_data.header.tr_cont = resp.header.tr_cont')
        for ul in update_lines:
            lines.append(ul)
        lines.append(f'        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)')
        lines.append('')

    lines.append('')

    # __all__
    all_exports = [f'Tr{class_prefix}'] + import_names
    lines.append('__all__ = [')
    for name in all_exports:
        lines.append(f'    {name},')
    lines.append(']')
    lines.append('')

    return "\n".join(lines)


def main():
    created = 0
    errors = []

    for tr_code, config in sorted(TR_CONFIG.items()):
        guide_file = find_guide_file(tr_code)
        if not guide_file:
            errors.append(f"{tr_code}: guide file not found")
            continue

        tr_name, blocks = parse_guide(guide_file)
        if not blocks:
            errors.append(f"{tr_code}: no blocks parsed from {guide_file.name}")
            continue

        category = config[0]
        tr_dir = BASE_DIR / category / tr_code
        tr_dir.mkdir(parents=True, exist_ok=True)

        # Generate blocks.py
        blocks_content = generate_blocks_py(tr_code, tr_name, blocks, config)
        (tr_dir / "blocks.py").write_text(blocks_content, encoding="utf-8")

        # Generate __init__.py
        init_content = generate_init_py(tr_code, tr_name, blocks, config)
        (tr_dir / "__init__.py").write_text(init_content, encoding="utf-8")

        print(f"✓ {tr_code} ({tr_name}) → {category}/{tr_code}/")
        created += 1

    print(f"\n생성 완료: {created}개 TR ({created*2}개 파일)")
    if errors:
        print(f"오류: {len(errors)}건")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
