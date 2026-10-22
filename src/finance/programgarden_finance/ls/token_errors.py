"""LS 응답을 '토큰 실패'로 분류하는 단일 판정기.

LS OpenAPI 는 죽은 토큰을 한 가지 모양으로 알려주지 않는다.

- ``401`` / ``403`` 을 주는 경로
- **HTTP 500 + ``rsp_msg``** 만 주는 경로 — 국내 만료 토큰, 해외선물 시세 ``o3101``
  (``HTTP 500: 유효하지 않은 token 입니다``) 이 여기 속한다. 상태코드만 보면 서버 장애와
  구분이 안 되고, 기존 401/403 분기에는 걸리지 않아 **죽은 토큰을 계속 재사용**했다.
- ``error_msg`` 는 빈 문자열이고 ``rsp_cd`` 에만 원인이 담기는 주문/취소 경로

만료(expired)와 무효(invalid)는 나누지 않는다 — 둘 다 "이 토큰으로는 더 못 쓴다"이고
대응이 같기 때문이다. 대신 아래 둘만 가른다.

``TOKEN_INVALID``
    응답이 **토큰 문제라고 말해 준** 경우. 기다린다고 낫지 않으므로 **재시도하지 않고
    즉시 재발급**한다.
``TRANSIENT``
    토큰인지 알 수 없는 일시 실패(5xx·429·타임아웃). 간격을 두고 재시도하고,
    끝까지 안 되면 그때 재발급을 한 번 시도한다.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class TokenFailureKind(str, Enum):
    """응답 하나에 대한 판정 결과."""

    NONE = "none"                    # 토큰과 무관 (정상이거나 재시도해도 소용없는 실패)
    TOKEN_INVALID = "token_invalid"  # 토큰이 죽었다고 응답이 말해 줌 → 즉시 재발급
    TRANSIENT = "transient"          # 일시 실패로 보임 → 간격 재시도


# 소문자로 정규화한 응답 메시지에서 찾는 '토큰이 죽었다'는 문구.
# LS 는 같은 뜻을 여러 문구로 돌려주므로 확인된 것을 모두 등재한다.
# 새 문구를 만나면 여기에만 추가하면 전 TR 경로에 반영된다.
TOKEN_MESSAGE_PATTERNS = (
    "유효하지 않은 token",     # o3101 등 (HTTP 500 로 옴)
    "기간이 만료된 token",     # 국내 만료 토큰 (HTTP 500 로 옴)
    "token 만료",
    "잘못된 token",
    "token expired",
    "expired token",
    "invalid token",
    "invalid access token",
    "unauthorized",
)

# rsp_cd 만으로 토큰 실패가 확정되는 코드.
#
# 2026-08-19 이전에는 라이브 실측값 `IGW00121` 하나뿐이었다 — LS 개발자센터가 로그인
# 뒤에 있어 공식 코드표를 볼 수 없었고, 추측 코드를 넣으면 주문 거부를 토큰 문제로
# 오판해 불필요한 재발급을 부르기 때문이다.
#
# 2026-08-19 확장: DB증권 Open API 공개 오류코드표를 확보했고, 그 표가 우리가 LS 에서
# 실제로 관측한 3건과 **코드·메시지 모두 일치**했다 —
#   IGW00121 유효하지 않은 token 입니다.      (엔진 라이브 실측)
#   IGW00201 호출 거래건수를 초과하였습니다.   (prod/dev Cloud Logging 실측)
#   IGW40013 데이터 조회에 실패 했습니다.      (prod Cloud Logging 실측)
# 즉 `IGW` 게이트웨이 코드표를 LS 도 그대로 쓴다고 볼 근거가 생겼다. 그래서 토큰 계열
# 형제 코드까지 등재한다. (같은 시점에 받은 NH 표는 토큰·쿼터 번호가 달라 1/3만
# 맞았으므로 채택하지 않았다 — 게이트웨이 제품은 같아도 번호는 브로커마다 갈린다.)
#
# 만료(expired)와 무효(invalid)를 나누지 않는 건 이 모듈의 기존 방침 그대로다 —
# 둘 다 "이 토큰으로는 더 못 쓴다"이고 대응이 재발급으로 같다.
#   IGW00121 유효하지 않은 token / IGW00122 token을 찾을 수 없음 / IGW00123 기간 만료
#   IGW00124~126 은 session_key 3형제(같은 인가 축)
# ⚠️ 호출 한도(IGW00201)는 여기 넣지 않는다 — 재발급이 아니라 백오프가 답이다.
TOKEN_RSP_CODES: frozenset[str] = frozenset({
    "IGW00121",  # 유효하지 않은 token 입니다.  (라이브 실측)
    "IGW00122",  # token을 찾을 수 없습니다.
    "IGW00123",  # 기간이 만료된 token 입니다.
    "IGW00124",  # 유효하지 않은 session_key 입니다.
    "IGW00125",  # session_key를 찾을 수 없습니다.
    "IGW00126",  # 기간이 만료된 session_key 입니다.
})

# 토큰 문구가 없을 때 '일시 실패'로 볼 상태코드.
_TRANSIENT_STATUSES = frozenset({408, 425, 429})


def _extract_message(resp_json: Optional[Dict[str, Any]]) -> str:
    """응답 본문에서 사람이 읽는 오류 문구를 모아 소문자로 돌려준다.

    LS 는 경로마다 담는 자리가 다르다 — ``rsp_msg`` 만 있는 경로, ``error_msg`` 만 있는
    경로, ``message``/``msg_cd`` 를 쓰는 OAuth 경로가 섞여 있다. 하나만 보면 놓친다.
    """
    if not isinstance(resp_json, dict):
        return ""
    parts = [
        resp_json.get("rsp_msg"),
        resp_json.get("error_msg"),
        resp_json.get("message"),
        resp_json.get("error_description"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def extract_status_code(resp: Optional[object]) -> Optional[int]:
    """aiohttp(``status``) / requests(``status_code``) 어느 쪽이든 상태코드를 꺼낸다."""
    if resp is None:
        return None
    return getattr(resp, "status", getattr(resp, "status_code", None))


def classify_token_failure(
    resp: Optional[object],
    resp_json: Optional[Dict[str, Any]],
    exc: Optional[BaseException] = None,
) -> TokenFailureKind:
    """응답(또는 예외) 하나를 :class:`TokenFailureKind` 로 분류한다.

    Args:
        resp: aiohttp/requests 응답 객체 (없으면 ``None``).
        resp_json: 파싱된 본문 (없으면 ``None``).
        exc: 요청이 예외로 끝났다면 그 예외.

    Returns:
        TokenFailureKind: 판정 결과.
    """
    message = _extract_message(resp_json)

    # ① 본문이 토큰 문제라고 말해 주면 상태코드와 무관하게 확정이다.
    #    HTTP 200 으로 오는 경로가 있어 상태코드를 먼저 거르면 놓친다.
    if any(pattern in message for pattern in TOKEN_MESSAGE_PATTERNS):
        return TokenFailureKind.TOKEN_INVALID

    if isinstance(resp_json, dict):
        rsp_cd = str(resp_json.get("rsp_cd") or "")
        if rsp_cd and rsp_cd in TOKEN_RSP_CODES:
            return TokenFailureKind.TOKEN_INVALID

    # ② 네트워크 예외 — 토큰 여부를 알 수 없으니 일시 실패로 본다.
    if exc is not None:
        return TokenFailureKind.TRANSIENT

    status = extract_status_code(resp)
    if status is None or status < 400:
        return TokenFailureKind.NONE

    # ③ 인증 거부는 문구가 없어도 토큰 문제로 확정한다.
    if status in (401, 403):
        return TokenFailureKind.TOKEN_INVALID

    if status in _TRANSIENT_STATUSES or 500 <= status < 600:
        return TokenFailureKind.TRANSIENT

    # 400/404 같은 요청 자체의 문제는 재시도도 재발급도 의미가 없다.
    return TokenFailureKind.NONE




class TokenReissueLimitExceeded(RuntimeError):
    """강제 재발급 상한을 넘었을 때 올린다.

    상한이 없으면 '재발급 → 여전히 실패 → 재발급' 이 무한히 돌면서 LS 에 발급 폭풍을
    내고, 같은 앱키를 쓰는 다른 실행까지 계속 무효화한다. 상한에 걸리면 조용히
    ``False``/``None`` 을 돌려주지 않고 **사유를 담아 실패**시킨다.
    """


__all__ = [
    "TokenFailureKind",
    "TokenReissueLimitExceeded",
    "TOKEN_MESSAGE_PATTERNS",
    "TOKEN_RSP_CODES",
    "classify_token_failure",
    "extract_status_code",
]
