"""Public skeleton of the broker startup-evidence gate. Performs the generic checks
only: transport success, a complete (not continued) response, and a standard success
response code. The platform's hardened evidence checks and its special-case handling of
edge responses are not part of the open-source build; such responses fall back to the
generic startup-evidence error."""
import inspect

PAPER_FUTURES_NO_RESULT_MESSAGES = frozenset()
ORDDT_ECHO_WINDOW_DAYS = 7
_SUCCESS_CODES = frozenset({"00000", "00136"})


class StartupEvidenceUnavailable(RuntimeError):
    pass


class StartupQueryDateMismatch(StartupEvidenceUnavailable):
    pass


def broker_message(value):
    return "" if value is None else str(value)[:80]


def unverified_response_code(tr, code, message):
    return f"{tr}: unverified_response_code {code} {broker_message(message)}".rstrip()


def _header_matches(tr, tr_cd):
    tr_cd = str(tr_cd or "")
    return tr_cd == tr or (len(tr_cd) >= 5 and tr.startswith(tr_cd))


async def checked_body(response, tr, request=None, *, paper_trading=False):
    if getattr(response, "status_code", None) != 200 or getattr(response, "error_msg", None):
        raise StartupEvidenceUnavailable(f"{tr}: transport_failure")
    header = getattr(response, "header", None)
    if (header is None or not _header_matches(tr, getattr(header, "tr_cd", None))
            or getattr(header, "tr_cont", None) not in {"N", "0"}
            or str(getattr(header, "tr_cont_key", "") or "").strip()):
        raise StartupEvidenceUnavailable(f"{tr}: incomplete_continuation")
    raw = getattr(response, "raw_data", None)
    body = raw.json() if raw is not None else None
    if inspect.isawaitable(body):
        body = await body
    if not isinstance(body, dict):
        raise StartupEvidenceUnavailable(f"{tr}: missing_response_blocks")
    code = getattr(response, "rsp_cd", None)
    if code not in _SUCCESS_CODES:
        raise StartupEvidenceUnavailable(
            unverified_response_code(tr, code, getattr(response, "rsp_msg", None)))
    return body
