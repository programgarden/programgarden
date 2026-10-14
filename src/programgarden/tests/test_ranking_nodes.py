"""KoreaStockRankingNode (t1441/t1452/t1463/t1444) and OverseasStockRankingNode (g3112).

The broker boundary is replaced by real SDK TR objects whose responses are parsed
by the real ``_build_response`` from canned LS-shaped bodies. No network, no token.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

from programgarden import ranking_nodes as rn
from programgarden.context import ExecutionContext
from programgarden.executor import RankingNodeExecutor, WorkflowExecutor, WorkflowJob

HEADERS = {"Content-Type": "application/json; charset=utf-8", "tr_cont_key": ""}


class _Resp:
    status = 200


def _headers(tr_cd: str, more: bool, key: str = "") -> Dict[str, str]:
    return {**HEADERS, "tr_cd": tr_cd, "tr_cont": "Y" if more else "N", "tr_cont_key": key}


def korea_row(shcode: str, *, sign="2", change=100, diff=1.5, price=10000, **extra) -> Dict[str, Any]:
    row = {
        "hname": f"name-{shcode}", "price": price, "sign": sign, "change": change, "diff": diff,
        "volume": 1000, "offerrem1": 0, "offerho1": 0, "bidho1": 0, "bidrem1": 0, "updaycnt": 1,
        "jnildiff": 0.5, "shcode": shcode, "open": 9900, "high": 10100, "low": 9800, "voldiff": 1.0,
        "value": 555, "total": 777, "vol": 2.0, "jnilvolume": 900, "bef_diff": 10.0, "jnilvalue": 444,
        "vol_rate": 1.2, "rate": 0.3, "for_rate": 50.0,
    }
    row.update(extra)
    return row


def _korea_body(tr: str, rows: List[Dict[str, Any]], idx: int, code="00000", msg="정상적으로 조회가 완료되었습니다."):
    from importlib import import_module
    blocks = import_module(f"programgarden_finance.ls.korea_stock.ranking.{tr}.blocks")
    out1 = getattr(blocks, f"{tr.upper()}OutBlock1")
    fields = set(out1.model_fields)
    return {
        f"{tr}OutBlock": {"idx": idx},
        f"{tr}OutBlock1": [{k: v for k, v in r.items() if k in fields} for r in rows],
        "rsp_cd": code, "rsp_msg": msg,
    }


def us_row(symbol: str, *, prefix="82", sign="2", **extra) -> Dict[str, Any]:
    row = {
        "keysymbol": f"{prefix}{symbol}", "exsymbol": f"나스닥 {symbol}", "symbol": symbol, "korname": f"k-{symbol}",
        "price": "100.500000", "sign": sign, "diff": "1.250000", "rate": "1.26", "volume": "1000000",
        "amount": "100500", "trgt": "0.810000", "shareprc": "250000", "high52p": "120.000000", "low52p": "80.000000",
    }
    row.update(extra)
    return row


def _g3112_body(rows, cts="", code="00000", msg="조회완료"):
    return {
        "g3112OutBlock": {"delaygb": "R", "natcode": "US", "exgubun": "1", "rankgubun": "0",
                          "cts_value": cts, "rec_count": str(len(rows))},
        "g3112OutBlock1": rows,
        "rsp_cd": code, "rsp_msg": msg,
    }


class _FakeTR:
    """A real SDK TR whose single transport call returns a canned page."""

    def __init__(self, tr, tr_code: str, owner: "_FakeLS"):
        self._tr, self._code, self._owner = tr, tr_code, owner
        self.request_data = tr.request_data

    async def req_async(self):
        body = next(iter(self.request_data.body.values()))
        header = self.request_data.header
        self._owner.calls.append({
            "tr": self._code, "body": body.model_dump(),
            "tr_cont": header.tr_cont, "tr_cont_key": header.tr_cont_key,
            "rate_limit_key": self.request_data.options.rate_limit_key,
            "rate_limit_count": self.request_data.options.rate_limit_count,
        })
        if not self._owner.pages:
            raise AssertionError(f"unexpected extra {self._code} request")
        json_body, headers = self._owner.pages.pop(0)
        return self._tr._build_response(_Resp(), json_body, headers, None)


class _FakeLS:
    def __init__(self, pages: List[Tuple[Dict[str, Any], Dict[str, str]]]):
        self.pages = list(pages)
        self.calls: List[Dict[str, Any]] = []

    # LS().korea_stock().ranking().t1441(body=...)
    def korea_stock(self):
        return self

    def ranking(self):
        return self

    def overseas_stock(self):
        return self

    def market(self):
        return self

    def _make(self, tr_code: str, body):
        from importlib import import_module
        if tr_code == "g3112":
            mod = import_module("programgarden_finance.ls.overseas_stock.market.g3112")
        else:
            mod = import_module(f"programgarden_finance.ls.korea_stock.ranking.{tr_code}")
        request_cls = getattr(mod, f"{tr_code.upper()}Request")
        tr_cls = getattr(mod, f"Tr{tr_code.upper()}")
        tr = tr_cls(request_cls(body={f"{tr_code}InBlock": body}))
        return _FakeTR(tr, tr_code, self)

    def t1441(self, body, **_):
        return self._make("t1441", body)

    def t1452(self, body, **_):
        return self._make("t1452", body)

    def t1463(self, body, **_):
        return self._make("t1463", body)

    def t1444(self, body, **_):
        return self._make("t1444", body)

    def g3112(self, body, **_):
        return self._make("g3112", body)


def _context(params=None) -> ExecutionContext:
    return ExecutionContext(job_id="j", workflow_id="w", context_params=params or {})


async def _execute(monkeypatch, node_type, config, pages, *, params=None, paper=False):
    fake = _FakeLS(pages)
    logins = []
    import programgarden.executor as ex

    monkeypatch.setattr(ex, "_resolve_broker_credentials", lambda conn, ctx: ("key", "secret", paper))

    def _login(appkey, appsecret, paper_trading, context, node_id, product, caller_name=""):
        logins.append((product, paper_trading))
        return fake, True, None

    monkeypatch.setattr(ex, "ensure_ls_login", _login)
    product = "korea_stock" if node_type.startswith("Korea") else "overseas_stock"
    cfg = {"connection": {"product": product, "provider": "ls-sec.co.kr"}, **config}
    out = await RankingNodeExecutor().execute("rank", node_type, cfg, _context(params))
    return out, fake, logins


# ── request mapping (values copied from SDK examples / LS guide) ───────────────

@pytest.mark.parametrize("ranking_type,market,tr,expected", [
    ("change_rate_up", "all", "t1441", {"gubun1": "0", "gubun2": "0", "gubun3": "0", "idx": 0,
                                        "jc_num": 0, "sprice": 0, "eprice": 0, "volume": 0, "jc_num2": 0,
                                        "exchgubun": "K"}),
    ("change_rate_down", "KOSDAQ", "t1441", {"gubun1": "2", "gubun2": "1", "gubun3": "0"}),
    ("volume", "KOSPI", "t1452", {"gubun": "1", "jnilgubun": "1", "idx": 0}),
    ("trading_value", "all", "t1463", {"gubun": "0", "jnilgubun": "0", "idx": 0, "exchgubun": "K"}),
    ("market_cap", "KOSPI", "t1444", {"upcode": "001", "idx": 0}),
    ("market_cap", "KOSDAQ", "t1444", {"upcode": "301", "idx": 0}),
])
def test_korea_request_values(ranking_type, market, tr, expected):
    request = rn.korea_ranking_request({"ranking_type": ranking_type, "market": market, "limit": 10})
    assert request.tr_code == tr
    body = rn.korea_in_block(request).model_dump()
    for key, value in expected.items():
        assert body[key] == value, key


@pytest.mark.parametrize("ranking_type,code", list(rn.OVERSEAS_RANK_CODES.items()))
def test_overseas_rank_codes(ranking_type, code):
    request = rn.overseas_ranking_request({"ranking_type": ranking_type, "market": "NASDAQ"})
    body = rn.overseas_in_block(request).model_dump()
    assert body == {"delaygb": "R", "natcode": "US", "exgubun": "3", "rankgubun": code, "cts_value": ""}


def test_overseas_market_codes_and_hidden_limit_ranks():
    assert rn.OVERSEAS_MARKET_CODES == {"all": "1", "NYSE": "2", "NASDAQ": "3", "ETF": "4"}
    assert set(rn.OVERSEAS_RANK_CODES.values()) == {"0", "1", "2", "3", "4", "5", "6", "7"}


@pytest.mark.parametrize("config,prefix", [
    ({"ranking_type": "market_cap", "market": "all"}, "t1444: market_cap ranks one market"),
    ({"ranking_type": "nope"}, "t1441: unsupported ranking_type"),
    ({"market": "NYSE"}, "t1441: unsupported market"),
    ({"limit": 0}, "t1441: limit must be from 1 to 100"),
    ({"limit": 101}, "t1441: limit must be from 1 to 100"),
    ({"limit": "20"}, "t1441: limit must be a whole number"),
    ({"limit": True}, "t1441: limit must be a whole number"),
])
def test_korea_invalid_settings_raise_with_tr_code(config, prefix):
    with pytest.raises(rn.RankingNodeError) as err:
        rn.korea_ranking_request(config)
    assert str(err.value).startswith(prefix)


def test_overseas_invalid_settings_raise():
    with pytest.raises(rn.RankingNodeError, match=r"^g3112: unsupported market"):
        rn.overseas_ranking_request({"market": "KOSPI"})
    with pytest.raises(rn.RankingNodeError, match=r"^g3112: unsupported ranking_type 'upper_limit'"):
        rn.overseas_ranking_request({"ranking_type": "upper_limit"})


def test_static_validate_rejects_market_cap_all_and_bad_limit():
    wf = {
        "id": "w", "name": "w", "credentials": [],
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "c"},
            {"id": "r1", "type": "KoreaStockRankingNode", "ranking_type": "market_cap", "market": "all"},
            {"id": "r2", "type": "OverseasStockRankingNode", "limit": 500},
            {"id": "r3", "type": "KoreaStockRankingNode", "ranking_type": "volume", "market": "KOSDAQ", "limit": 30},
        ],
        "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "r1"},
                  {"from": "broker", "to": "r2"}, {"from": "broker", "to": "r3"}],
    }
    result = WorkflowExecutor().validate(wf)
    errors = [(e.location.node_id, e.location.field_path) for e in result.errors
              if getattr(e.code, "value", e.code) == "INVALID_FIELD_ENUM"]
    assert ("r1", "market") in errors
    assert ("r2", "limit") in errors
    assert not [e for e in errors if e[0] == "r3"]


# ── Korea executor: mapping, signs, units, paging ──────────────────────────────

@pytest.mark.asyncio
async def test_t1441_rows_signs_units_and_symbols(monkeypatch):
    rows = [
        korea_row("005930", sign="2", change=1500, diff=2.5),
        korea_row("000660", sign="5", change=3000, diff=1.7),
        korea_row("035420", sign="3", change=0, diff=0.0),
        korea_row("068270", sign="4", change=-500, diff=-30.0),
        korea_row("251270", sign="1", change=7000, diff=29.9),
    ]
    out, fake, logins = await _execute(
        monkeypatch, "KoreaStockRankingNode", {"ranking_type": "change_rate_up", "market": "all", "limit": 5},
        [(_korea_body("t1441", rows, 0), _headers("t1441", False))],
    )
    assert logins == [("korea_stock", False)]
    assert out["count"] == 5 and len(out["rankings"]) == 5
    first = out["rankings"][0]
    assert first == {
        "rank": 1, "symbol": "005930", "exchange": "KRX", "market": None, "name": "name-005930",
        "price": 10000, "open": 9900, "high": 10100, "low": 9800, "sign": "2", "change": 1500,
        "change_pct": 2.5, "volume": 1000, "trading_value": 555, "trading_value_unit": "as_returned",
        "market_cap": 777, "market_cap_unit": "as_returned", "product": "korea_stock", "source_tr": "t1441",
    }
    signs = [(r["change"], r["change_pct"]) for r in out["rankings"]]
    assert signs == [(1500, 2.5), (-3000, -1.7), (0, 0.0), (-500, -30.0), (7000, 29.9)]
    assert out["symbols"][1] == {"exchange": "KRX", "market": None, "symbol": "000660",
                                 "name": "name-000660", "product": "korea_stock"}
    call = fake.calls[0]
    assert call["rate_limit_key"] == "t1441" and call["rate_limit_count"] == 1
    assert call["tr_cont"] == "N"


@pytest.mark.parametrize("ranking_type,market,tr,tv,tv_unit,mc,mc_unit,session", [
    ("volume", "KOSPI", "t1452", None, None, None, None, False),
    ("trading_value", "KOSDAQ", "t1463", 555, "KRW_million", 777, "KRW_million", False),
    ("market_cap", "KOSPI", "t1444", None, None, 777, "KRW_100million", False),
])
@pytest.mark.asyncio
async def test_units_per_tr(monkeypatch, ranking_type, market, tr, tv, tv_unit, mc, mc_unit, session):
    out, fake, _ = await _execute(
        monkeypatch, "KoreaStockRankingNode", {"ranking_type": ranking_type, "market": market, "limit": 1},
        [(_korea_body(tr, [korea_row("005930")], 0), _headers(tr, False))],
    )
    row = out["rankings"][0]
    assert row["source_tr"] == tr and row["market"] == market
    assert (row["trading_value"], row["trading_value_unit"]) == (tv, tv_unit)
    assert (row["market_cap"], row["market_cap_unit"]) == (mc, mc_unit)
    assert (row["open"], row["high"], row["low"]) == (None, None, None)
    assert out["symbols"][0]["market"] == market
    assert fake.calls[0]["rate_limit_key"] == tr


@pytest.mark.asyncio
async def test_t1463_respects_guide_rate_of_one_per_second(monkeypatch):
    out, fake, _ = await _execute(
        monkeypatch, "KoreaStockRankingNode", {"ranking_type": "trading_value", "limit": 1},
        [(_korea_body("t1463", [korea_row("005930")], 0), _headers("t1463", False))],
    )
    assert fake.calls[0]["rate_limit_count"] == 1


@pytest.mark.asyncio
async def test_korea_paging_cursor_dedupe_and_limit(monkeypatch):
    page1 = [korea_row(f"{i:06d}") for i in range(1, 21)]
    page2 = [korea_row("000020")] + [korea_row(f"{i:06d}") for i in range(21, 40)]  # one repeat
    out, fake, _ = await _execute(
        monkeypatch, "KoreaStockRankingNode", {"ranking_type": "volume", "market": "all", "limit": 30},
        [
            (_korea_body("t1452", page1, 20), _headers("t1452", True, "KEY1")),
            (_korea_body("t1452", page2, 40), _headers("t1452", True, "KEY2")),
        ],
    )
    assert out["count"] == 30
    assert [r["rank"] for r in out["rankings"]] == list(range(1, 31))
    symbols = [r["symbol"] for r in out["rankings"]]
    assert len(set(symbols)) == 30 and symbols[19] == "000020" and symbols[20] == "000021"
    assert len(fake.calls) == 2
    assert fake.calls[1]["body"]["idx"] == 20
    assert fake.calls[1]["tr_cont"] == "Y" and fake.calls[1]["tr_cont_key"] == "KEY1"


@pytest.mark.asyncio
async def test_korea_paging_stops_at_last_page(monkeypatch):
    out, fake, _ = await _execute(
        monkeypatch, "KoreaStockRankingNode", {"ranking_type": "volume", "limit": 100},
        [
            (_korea_body("t1452", [korea_row("000001")], 10), _headers("t1452", True, "K")),
            (_korea_body("t1452", [korea_row("000002")], 0), _headers("t1452", True, "K2")),  # idx 0 → end
        ],
    )
    assert out["count"] == 2 and len(fake.calls) == 2

    out, fake, _ = await _execute(
        monkeypatch, "KoreaStockRankingNode", {"ranking_type": "volume", "limit": 100},
        [(_korea_body("t1452", [korea_row("000001")], 10), _headers("t1452", False))],  # tr_cont N → end
    )
    assert out["count"] == 1 and len(fake.calls) == 1


@pytest.mark.asyncio
async def test_korea_paging_is_capped_at_five_requests(monkeypatch):
    pages = [
        (_korea_body("t1441", [korea_row(f"{p:03d}{i:03d}") for i in range(10)], (p + 1) * 10),
         _headers("t1441", True, f"K{p}"))
        for p in range(7)
    ]
    out, fake, _ = await _execute(
        monkeypatch, "KoreaStockRankingNode", {"ranking_type": "change_rate_up", "limit": 100}, pages,
    )
    assert len(fake.calls) == rn.MAX_RANKING_REQUESTS == 5
    assert out["count"] == 50


@pytest.mark.asyncio
async def test_empty_successful_result_is_valid(monkeypatch):
    out, _, _ = await _execute(
        monkeypatch, "KoreaStockRankingNode", {"ranking_type": "change_rate_up"},
        [(_korea_body("t1441", [], 0), _headers("t1441", False))],
    )
    assert out == {"rankings": [], "symbols": [], "count": 0}


@pytest.mark.asyncio
async def test_ls_rejection_raises_with_tr_code(monkeypatch):
    with pytest.raises(rn.RankingNodeError, match=r"^t1463: 01234 조회 불가"):
        await _execute(
            monkeypatch, "KoreaStockRankingNode", {"ranking_type": "trading_value"},
            [(_korea_body("t1463", [], 0, code="01234", msg="조회 불가"), _headers("t1463", False))],
        )


@pytest.mark.asyncio
async def test_http_error_raises_with_tr_code(monkeypatch):
    class _Err:
        status = 500

    fake = _FakeLS([])
    import programgarden.executor as ex
    monkeypatch.setattr(ex, "_resolve_broker_credentials", lambda conn, ctx: ("k", "s", False))
    monkeypatch.setattr(ex, "ensure_ls_login", lambda *a, **k: (fake, True, None))

    async def _boom(self):
        return self._tr._build_response(_Err(), {"rsp_msg": "server busy"}, {}, None)

    monkeypatch.setattr(_FakeTR, "req_async", _boom)
    with pytest.raises(rn.RankingNodeError, match=r"^t1441: HTTP 500: server busy"):
        await RankingNodeExecutor().execute(
            "rank", "KoreaStockRankingNode", {"connection": {"product": "korea_stock"}}, _context(),
        )


@pytest.mark.asyncio
async def test_missing_connection_or_credentials_fail_closed(monkeypatch):
    with pytest.raises(rn.RankingNodeError, match=r"^t1441: a matching korea_stock broker connection"):
        await RankingNodeExecutor().execute("rank", "KoreaStockRankingNode", {}, _context())
    with pytest.raises(rn.RankingNodeError, match=r"^g3112: a matching overseas_stock broker connection"):
        await RankingNodeExecutor().execute(
            "rank", "OverseasStockRankingNode", {"connection": {"product": "korea_stock"}}, _context())
    import programgarden.executor as ex
    monkeypatch.setattr(ex, "_resolve_broker_credentials", lambda conn, ctx: ("", "", False))
    with pytest.raises(rn.RankingNodeError, match=r"^t1441: broker credentials are not set"):
        await RankingNodeExecutor().execute(
            "rank", "KoreaStockRankingNode", {"connection": {"product": "korea_stock"}}, _context())


@pytest.mark.asyncio
async def test_overseas_paper_connection_is_rejected(monkeypatch):
    with pytest.raises(rn.RankingNodeError, match=r"^g3112: overseas_stock does not support paper_trading"):
        await _execute(monkeypatch, "OverseasStockRankingNode", {}, [], paper=True)


# ── Overseas executor ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_g3112_rows_exchange_numbers_and_symbols(monkeypatch):
    rows = [
        us_row("TSLA", prefix="82"),
        us_row("IBM", prefix="81", sign="5", diff="2.000000", rate="1.50"),
        {**us_row("ODD"), "keysymbol": "99ODD"},
        {**us_row("MIS"), "keysymbol": "82XYZ"},
        us_row("NIL", amount="", shareprc=" ", trgt="", price="abc"),
    ]
    out, fake, logins = await _execute(
        monkeypatch, "OverseasStockRankingNode", {"ranking_type": "volume", "market": "all", "limit": 10},
        [(_g3112_body(rows), _headers("g3112", False))],
    )
    assert logins == [("overseas_stock", False)]
    first = out["rankings"][0]
    assert first == {
        "rank": 1, "symbol": "TSLA", "exchange": "NASDAQ", "exchange_source": "keysymbol", "name": "k-TSLA",
        "exchange_name": "나스닥 TSLA", "keysymbol": "82TSLA", "price": 100.5, "sign": "2", "change": 1.25,
        "change_pct": 1.26, "volume": 1000000, "trading_value": 100500, "trading_value_unit": "as_returned",
        "turnover": 0.81, "market_cap": 250000, "market_cap_unit": "as_returned", "high_52w": 120.0,
        "low_52w": 80.0, "product": "overseas_stock", "source_tr": "g3112",
    }
    ibm = out["rankings"][1]
    assert ibm["exchange"] == "NYSE" and ibm["change"] == -2.0 and ibm["change_pct"] == -1.5
    assert out["rankings"][2]["exchange"] is None and out["rankings"][2]["exchange_source"] == "unavailable"
    assert out["rankings"][3]["exchange"] is None  # prefix ok but symbol mismatch
    nil = out["rankings"][4]
    assert nil["trading_value"] is None and nil["trading_value_unit"] is None
    assert nil["market_cap"] is None and nil["market_cap_unit"] is None
    assert nil["turnover"] is None and nil["price"] is None
    assert out["count"] == 5
    assert [s["symbol"] for s in out["symbols"]] == ["TSLA", "IBM", "NIL"]
    assert out["symbols"][0] == {"exchange": "NASDAQ", "symbol": "TSLA", "name": "k-TSLA", "product": "overseas_stock"}
    call = fake.calls[0]
    assert call["body"] == {"delaygb": "R", "natcode": "US", "exgubun": "1", "rankgubun": "2", "cts_value": ""}
    assert call["rate_limit_key"] == "g3112" and call["rate_limit_count"] == 1


@pytest.mark.asyncio
async def test_g3112_paging_uses_cts_value(monkeypatch):
    out, fake, _ = await _execute(
        monkeypatch, "OverseasStockRankingNode", {"limit": 3},
        [
            (_g3112_body([us_row("A"), us_row("B")], cts="2"), _headers("g3112", True, "CK")),
            (_g3112_body([us_row("B"), us_row("C"), us_row("D")], cts=""), _headers("g3112", False)),
        ],
    )
    assert [r["symbol"] for r in out["rankings"]] == ["A", "B", "C"]
    assert fake.calls[1]["body"]["cts_value"] == "2"
    assert fake.calls[1]["tr_cont"] == "Y" and fake.calls[1]["tr_cont_key"] == "CK"


# First two rows of the single read-only live call (2026-10-15 KST, natcode US, exgubun 1,
# rankgubun 0): volume/amount/shareprc and rec_count arrive as JSON integers.
LIVE_G3112 = {
    "g3112OutBlock": {"delaygb": "R", "natcode": "US", "exgubun": "1", "rankgubun": "0",
                      "cts_value": "0000000000000021", "rec_count": 20},
    "g3112OutBlock1": [
        {"keysymbol": "82AEHL", "symbol": "AEHL", "exsymbol": "나스닥 AEHL", "korname": "안텔로페 엔터프라이즈 홀딩스",
         "price": "23.4600", "sign": "2", "diff": "14.9100", "rate": "174.39", "volume": 2123215,
         "amount": 50434322, "trgt": "12.9000", "shareprc": 386138, "high52p": "30.0000", "low52p": "1.0000"},
        {"keysymbol": "81AMTD", "symbol": "AMTD", "exsymbol": "뉴욕   AMTD", "korname": "AMTD 아이디어 그룹(ADS)",
         "price": "0.6450", "sign": "2", "diff": "0.2620", "rate": "68.41", "volume": 22304599,
         "amount": 13137297, "trgt": "52.4970", "shareprc": 27404, "high52p": "1.5000", "low52p": "0.3000"},
    ],
    "rsp_cd": "00000", "rsp_msg": "조회완료",
}


@pytest.mark.asyncio
async def test_g3112_live_shape(monkeypatch):
    out, fake, _ = await _execute(
        monkeypatch, "OverseasStockRankingNode", {"limit": 2},
        [(LIVE_G3112, _headers("g3112", True, "LIVEKEY"))],
    )
    assert len(fake.calls) == 1  # limit reached on the first page
    aehl, amtd = out["rankings"]
    assert (aehl["exchange"], aehl["price"], aehl["change_pct"], aehl["volume"]) == ("NASDAQ", 23.46, 174.39, 2123215)
    assert (aehl["trading_value"], aehl["market_cap"], aehl["turnover"]) == (50434322, 386138, 12.9)
    assert aehl["exchange_name"] == "나스닥 AEHL"
    assert amtd["exchange"] == "NYSE" and amtd["exchange_source"] == "keysymbol"
    assert [s["symbol"] for s in out["symbols"]] == ["AEHL", "AMTD"]


@pytest.mark.asyncio
async def test_g3112_numeric_json_is_accepted(monkeypatch):
    row = us_row("TSLA", price=101.25, volume=1200, rate=-0.5, sign="5")
    out, _, _ = await _execute(
        monkeypatch, "OverseasStockRankingNode", {},
        [(_g3112_body([row]), _headers("g3112", False))],
    )
    assert out["rankings"][0]["price"] == 101.25 and out["rankings"][0]["volume"] == 1200
    assert out["rankings"][0]["change_pct"] == -0.5


# ── deep validation / dry run: synthetic, no broker call ───────────────────────

@pytest.mark.parametrize("params", [{"deep_validate": True}, {"dry_run": True}])
@pytest.mark.parametrize("node_type", ["KoreaStockRankingNode", "OverseasStockRankingNode"])
@pytest.mark.asyncio
async def test_validation_modes_are_synthetic(monkeypatch, node_type, params):
    import programgarden.executor as ex

    def _no_login(*a, **k):
        raise AssertionError("broker login attempted in a validation mode")

    monkeypatch.setattr(ex, "ensure_ls_login", _no_login)
    out = await RankingNodeExecutor().execute(
        "rank", node_type, {"ranking_type": "change_rate_down", "limit": 2}, _context(params),
    )
    assert out["count"] == 2 and len(out["rankings"]) == 2 and len(out["symbols"]) == 2
    assert all(r["change"] < 0 for r in out["rankings"])
    expected = rn.korea_outputs if node_type.startswith("Korea") else None
    keys = set(out["rankings"][0])
    if expected:
        assert keys == set(rn.RankingRowBuilder.korea_row(1, rn._SYNTHETIC_KOREA[0], "t1441", None))
    else:
        assert keys == set(rn.RankingRowBuilder.overseas_row(1, rn._SYNTHETIC_OVERSEAS[0]))


@pytest.mark.asyncio
async def test_synthetic_market_cap_still_validates_combination():
    with pytest.raises(rn.RankingNodeError, match="^t1444"):
        await RankingNodeExecutor().execute(
            "rank", "KoreaStockRankingNode", {"ranking_type": "market_cap", "market": "all"},
            _context({"deep_validate": True}),
        )


# ── wiring ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("node_type", ["KoreaStockRankingNode", "OverseasStockRankingNode"])
def test_wiring(node_type):
    from programgarden.node_runner import _BROKER_DEPENDENT_NODE_TYPES
    from programgarden.validation_replay import FIXTURE_NODES
    from programgarden_core import NodeTypeRegistry

    assert isinstance(WorkflowExecutor()._executors[node_type], RankingNodeExecutor)
    assert node_type in WorkflowJob.NO_AUTO_ITERATE_NODE_TYPES
    assert node_type in _BROKER_DEPENDENT_NODE_TYPES
    assert node_type in FIXTURE_NODES
    schema = NodeTypeRegistry().get_schema(node_type)
    assert [o["name"] for o in schema.outputs] == ["rankings", "symbols", "count"]
    assert schema.product_scope == ("korea_stock" if node_type.startswith("Korea") else "overseas_stock")


@pytest.mark.asyncio
async def test_workflow_deep_validate_with_ranking_and_codenode():
    wf = {
        "id": "w", "name": "w",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "c"},
            {"id": "ranking", "type": "KoreaStockRankingNode", "ranking_type": "change_rate_up",
             "market": "all", "limit": 30},
            {"id": "pick", "type": "CodeNode", "data": "{{ nodes.ranking.rankings }}",
             "code": ("async def execute(data, params, context):\n"
                      "    rows = [r for r in data if 3 <= r['change_pct'] <= 15 and r['price'] > r['open']]\n"
                      "    return {'picked': rows[:1], 'n': len(data)}"),
             "outputs": [{"name": "picked", "type": "array"}, {"name": "n", "type": "number"}]},
        ],
        "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "ranking"},
                  {"from": "ranking", "to": "pick"}],
        "credentials": [{"credential_id": "c", "type": "broker_ls_korea_stock", "data": [
            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]}],
    }
    result = await WorkflowExecutor().deep_validate(wf)
    assert result.is_valid, result.errors
