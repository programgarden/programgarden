"""The diagnostic example must not retry, issue tokens or leak raw evidence."""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import stat
import sys
from types import SimpleNamespace

import pytest
import requests


@pytest.fixture
def example():
    path = Path(__file__).parents[1] / "example/korea_stock/run_CDPCQ04700.py"
    spec = importlib.util.spec_from_file_location("cdpcq_capture_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def private_token(tmp_path):
    path = tmp_path / "token.json"
    path.write_text(json.dumps({"access_token": "fixture-private-token",
                               "expires_at": (datetime.now(timezone.utc)
                                              + timedelta(hours=1)).isoformat()}))
    path.chmod(0o600)
    return path


def install_transport(monkeypatch, example, outcome):
    calls = []

    class SingleSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(example.requests, "Session", SingleSession)
    return calls


def argv(monkeypatch, token, output):
    monkeypatch.setattr(sys, "argv", ["capture", "--start-date", "20260722",
                                     "--end-date", "20260722", "--asset-class", "00",
                                     "--token-file", str(token), "--output", str(output)])


@pytest.mark.parametrize("status", [200, 429, 500])
def test_one_attempt_preserves_private_evidence_without_following_redirects(
    example, private_token, tmp_path, monkeypatch, capsys, status,
):
    raw = {"rsp_cd": "fixture", "rsp_msg": "private broker message",
           "CDPCQ04700OutBlock3": [{"CrcyCode": "USD", "FcurrDps": "1.25",
                                    "OppAcntNo": "private fixture account"}]}
    response = SimpleNamespace(status_code=status, json=lambda: raw,
                               headers={"tr_cont": "Y", "tr_cont_key": "private-cursor",
                                        "Authorization": "must-not-capture"})
    calls = install_transport(monkeypatch, example, response)
    output = tmp_path / "capture.json"
    argv(monkeypatch, private_token, output)
    example.main()
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "https://openapi.ls-sec.co.kr:8080/stock/accno"
    assert request["allow_redirects"] is False and request["timeout"] == 10
    assert request["json"] == {"CDPCQ04700InBlock1": {
        "RecCnt": 1, "QryTp": "1", "QrySrtDt": "20260722", "QryEndDt": "20260722",
        "SrtNo": 0, "PdptnCode": "01", "IsuLgclssCode": "00", "IsuNo": "",
    }}
    capture = json.loads(output.read_text())
    assert capture["raw_payload"] == raw
    assert capture["headers"] == {"tr_cont": "Y", "tr_cont_key": "private-cursor"}
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert "fixture-private-token" not in output.read_text()
    console = capsys.readouterr()
    assert "private" not in console.out.replace(str(output), "")
    assert "private" not in console.err


def test_network_failure_is_recorded_once_without_exception_text(
    example, private_token, tmp_path, monkeypatch, capsys,
):
    calls = install_transport(monkeypatch, example, requests.Timeout("private token details"))
    output = tmp_path / "capture.json"
    argv(monkeypatch, private_token, output)
    example.main()
    assert len(calls) == 1
    assert json.loads(output.read_text())["transport_error"] == "Timeout"
    assert "private token details" not in output.read_text() + capsys.readouterr().out


def test_existing_capture_is_never_overwritten_or_sent_again(
    example, private_token, tmp_path, monkeypatch,
):
    calls = install_transport(monkeypatch, example, AssertionError("No request expected"))
    output = tmp_path / "capture.json"
    output.write_text("prior evidence")
    argv(monkeypatch, private_token, output)
    with pytest.raises(FileExistsError):
        example.main()
    assert calls == [] and output.read_text() == "prior evidence"


def test_public_or_expired_token_cannot_trigger_request(example, private_token):
    private_token.chmod(0o644)
    with pytest.raises(ValueError, match="private regular"):
        example.load_token(private_token)
    private_token.chmod(0o600)
    private_token.write_text(json.dumps({"access_token": "fixture",
                                       "expires_at": "2020-01-01T00:00:00+00:00"}))
    with pytest.raises(ValueError, match="expired"):
        example.load_token(private_token)


def test_dry_run_does_not_open_session_or_token_file(example, monkeypatch, capsys):
    calls = install_transport(monkeypatch, example, AssertionError("No request expected"))
    monkeypatch.setattr(sys, "argv", ["capture", "--dry-run", "--asset-class", "05"])
    example.main()
    assert calls == []
    assert json.loads(capsys.readouterr().out)["request"]["IsuLgclssCode"] == "05"
