"""브로커 자격증명이 노드 출력으로 새지 않는지 검증.

근본 수정(2026-07-13): BrokerNode 는 자격증명을 **시크릿 저장소에만** 둔다.
예전엔 `connection` **출력**에 평문 appkey/appsecret 을 실었고, 노드 출력은
리스너(SSE→대시보드) · `get_state()` · 체크포인트로 외부에 나간다.
(실측: pg-test-9 LIVE 에서 broker 노드 output 에 실 앱키 평문 노출.)

하류는 `_resolve_broker_credentials(connection, context)` 로 저장소에서 꺼낸다.
저장소 슬롯은 **product 별**이다 — 단일 슬롯이면 브로커가 둘 이상인 워크플로우
(해외주식 + 국내주식)에서 뒤 브로커가 앞 자격증명을 덮어써 하류가 **다른 계좌 앱키**로
로그인한다.

마스킹(`_sanitize_outputs`)은 심층방어로 남긴다 — 다른 노드가 실수로 시크릿을 출력에
실어도 외부 경계에서 걸린다.
"""
import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import _resolve_broker_credentials, broker_credential_key


@pytest.fixture
def ctx():
    return ExecutionContext(job_id="test-cred", workflow_id="wf-cred")


OVERSEAS = {"appkey": "OVERSEAS-KEY", "appsecret": "OVERSEAS-SECRET", "paper_trading": False}
KOREA = {"appkey": "KOREA-KEY", "appsecret": "KOREA-SECRET", "paper_trading": True}


class TestCredentialsResolveFromSecretStore:
    def test_resolves_by_product(self, ctx):
        ctx.set_secret(broker_credential_key("overseas_stock"), OVERSEAS)
        conn = {"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False}

        appkey, appsecret, paper = _resolve_broker_credentials(conn, ctx)
        assert (appkey, appsecret, paper) == ("OVERSEAS-KEY", "OVERSEAS-SECRET", False)

    def test_two_brokers_do_not_collide(self, ctx):
        """단일 슬롯이면 국내가 해외를 덮어써 하류가 남의 계좌로 로그인한다."""
        ctx.set_secret(broker_credential_key("overseas_stock"), OVERSEAS)
        ctx.set_secret(broker_credential_key("korea_stock"), KOREA)

        ov = _resolve_broker_credentials({"product": "overseas_stock"}, ctx)
        kr = _resolve_broker_credentials({"product": "korea_stock"}, ctx)

        assert ov[0] == "OVERSEAS-KEY"
        assert kr[0] == "KOREA-KEY"
        assert kr[2] is True  # paper_trading 도 브로커별로 따라와야 한다

    def test_falls_back_to_legacy_single_slot(self, ctx):
        """product 슬롯이 없으면(구 저장 경로) 레거시 단일 슬롯으로 내려간다."""
        ctx.set_secret("credential_id", OVERSEAS)

        appkey, _, _ = _resolve_broker_credentials({"product": "overseas_stock"}, ctx)
        assert appkey == "OVERSEAS-KEY"

    def test_falls_back_to_plaintext_connection(self, ctx):
        """레거시 워크플로우·deep_validate 픽스처는 아직 connection 에 키를 싣는다."""
        conn = {"product": "overseas_stock", "appkey": "LEGACY", "appsecret": "LEGACY-S"}

        appkey, appsecret, _ = _resolve_broker_credentials(conn, ctx)
        assert (appkey, appsecret) == ("LEGACY", "LEGACY-S")

    def test_missing_everything_is_empty_not_crash(self, ctx):
        assert _resolve_broker_credentials(None, ctx) == ("", "", False)


class TestBrokerOutputCarriesNoSecrets:
    def test_connection_shape_has_no_credentials(self):
        """BrokerNodeExecutor 가 반환하는 `connection` dict 에 자격증명 키가 없어야 한다.

        (시크릿 저장소에 넣는 payload 에는 당연히 appkey 가 있으므로, 소스 전체 문자열
        검색이 아니라 **반환 dict 리터럴만** AST 로 집어서 본다.)
        """
        import ast
        import inspect
        import textwrap

        from programgarden.executor import BrokerNodeExecutor

        tree = ast.parse(textwrap.dedent(inspect.getsource(BrokerNodeExecutor)))

        checked = 0
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)):
                continue
            keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
            if "connection" not in keys:
                continue
            conn_node = node.value.values[keys.index("connection")]
            if not isinstance(conn_node, ast.Dict):
                continue
            conn_keys = {k.value for k in conn_node.keys if isinstance(k, ast.Constant)}
            checked += 1
            assert "appkey" not in conn_keys, f"connection 출력에 appkey 가 다시 실렸다: {conn_keys}"
            assert "appsecret" not in conn_keys, f"connection 출력에 appsecret 이 다시 실렸다: {conn_keys}"
            assert "product" in conn_keys, "하류가 자격증명을 찾으려면 product 가 필요하다"

        assert checked, "BrokerNodeExecutor 에서 connection 반환 dict 를 찾지 못했다"


class TestSanitizerDefenseInDepth:
    """근본 수정과 별개로, 출력 경계 마스킹은 남겨 둔다."""

    def test_masks_credentials_in_outputs(self, ctx):
        ctx.set_output("broker", "connection", {"provider": "ls", "appkey": "LEAK", "appsecret": "LEAK2"})

        safe = ctx.get_all_outputs_sanitized("broker")
        assert safe["connection"]["appkey"] == "[REDACTED]"
        assert safe["connection"]["appsecret"] == "[REDACTED]"
        assert safe["connection"]["provider"] == "ls"

    def test_internal_store_is_not_mutated(self, ctx):
        ctx.set_output("broker", "connection", {"appkey": "REAL"})

        ctx.get_all_outputs_sanitized("broker")
        assert ctx.get_all_outputs("broker")["connection"]["appkey"] == "REAL"

    def test_secrets_inside_a_list_are_masked(self, ctx):
        """기존 sanitizer 는 dict 만 재귀해 리스트 안의 dict 를 통과시켰다."""
        ctx.set_output("n", "credentials", [{"credential_id": "c1", "appkey": "LEAK"}])

        safe = ctx.get_all_outputs_sanitized("n")
        assert "LEAK" not in repr(safe)
        assert safe["credentials"][0]["credential_id"] == "c1"

    @pytest.mark.parametrize(
        "key", ["appkey", "appsecret", "api_key", "apikey", "token",
                "access_token", "password", "secret", "private_key"],
    )
    def test_each_sensitive_key_is_masked(self, ctx, key):
        ctx.set_output("n", "data", {key: "LEAK"})

        assert ctx.get_all_outputs_sanitized("n")["data"][key] == "[REDACTED]"

    def test_ordinary_keys_untouched(self, ctx):
        ctx.set_output("n", "data", {"symbol": "NVDA", "price": 209.0})

        assert ctx.get_all_outputs_sanitized("n")["data"] == {"symbol": "NVDA", "price": 209.0}
