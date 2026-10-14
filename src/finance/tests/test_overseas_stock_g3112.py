"""g3112 해외주식API시세순위 (overseas stock quote ranking) — SDK contract tests.

Guard coverage:
  1. InBlock / OutBlock / OutBlock1 field sets equal the official LS guide entry
     (``[해외주식] 시세`` /overseas-stock/market-data, recorded below).
  2. Every OutBlock field is ``str`` as the guide types it ("String"); no
     float/int typing without evidence. Numeric JSON is accepted as text.
  3. Enumerated request codes come from the guide (exgubun 1-4, rankgubun 0-9).
  4. Request envelope: tr_cd g3112, market-data URL, 1 request/second
     (guide transactionPerSec "1"), shared rate-limit key.
  5. ``_build_response`` parses a guide-shaped body and reports HTTP errors and
     exceptions in ``error_msg``.
  6. Continuation copies ``cts_value`` and the header continuation key.
  7. Market accessor, Korean alias and package export.
  8. The domestic ranking TRs used by KoreaStockRankingNode keep the guide's
     per-second limits (t1463 is 1/s in the guide).
"""
from __future__ import annotations

import typing

import pytest
from pydantic import BaseModel, TypeAdapter

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.overseas_stock.market.g3112 import TrG3112
from programgarden_finance.ls.overseas_stock.market.g3112.blocks import (
    G3112InBlock,
    G3112OutBlock,
    G3112OutBlock1,
    G3112Request,
    G3112Response,
)

# Recorded from the official LS OpenAPI guide entry for g3112 (2026-10-15).
GUIDE_IN = {
    "delaygb": ("String", "1"), "natcode": ("String", "2"), "exgubun": ("String", "1"),
    "rankgubun": ("String", "1"), "cts_value": ("String", "16"),
}
GUIDE_OUT = {
    "delaygb": "String", "natcode": "String", "exgubun": "String", "rankgubun": "String",
    "cts_value": "String", "rec_count": "String",
}
GUIDE_OUT1 = {
    "keysymbol": "String", "exsymbol": "String", "symbol": "String", "korname": "String",
    "price": "String", "sign": "String", "diff": "String", "rate": "String", "volume": "String",
    "amount": "String", "trgt": "String", "shareprc": "String", "high52p": "String", "low52p": "String",
}
GUIDE_EXGUBUN = {"1": "전체", "2": "뉴욕", "3": "나스닥", "4": "ETF"}
GUIDE_RANKGUBUN = {
    "0": "전일대비상승률", "1": "전일대비하락률", "2": "당일거래량", "3": "거래대금", "4": "회전율",
    "5": "시가총액", "6": "52주신고가", "7": "52주신저가", "8": "상한가", "9": "하한가",
}
GUIDE_TRANSACTIONS_PER_SECOND = 1

HEADERS = {"Content-Type": "application/json; charset=utf-8", "tr_cd": "g3112", "tr_cont": "Y", "tr_cont_key": "NEXT"}

SAMPLE = {
    "g3112OutBlock": {"delaygb": "R", "natcode": "US", "exgubun": "1", "rankgubun": "0",
                      "cts_value": "0000000000000021", "rec_count": 2},
    "g3112OutBlock1": [
        {"keysymbol": "82TSLA", "exsymbol": "TESLA INC", "symbol": "TSLA", "korname": "테슬라",
         "price": "248.500000", "sign": "2", "diff": "3.250000", "rate": "1.33", "volume": "85000000",
         "amount": "21000000", "trgt": "2.710000", "shareprc": "800000000", "high52p": "299.290000",
         "low52p": "138.800000"},
        # Observed live 2026-10-15: volume/amount/shareprc are JSON integers.
        {"keysymbol": "81IBM", "exsymbol": "뉴욕   IBM", "symbol": "IBM", "korname": "IBM",
         "price": 211.5, "sign": "5", "diff": 1.25, "rate": -0.59, "volume": 3100000,
         "amount": 655000, "trgt": 0.33, "shareprc": 195000000, "high52p": 239.35, "low52p": 162.62},
    ],
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
}


class _Resp:
    def __init__(self, status):
        self.status = status


def _request(**overrides) -> G3112Request:
    body = {"delaygb": "R", "natcode": "US", "exgubun": "1", "rankgubun": "0", "cts_value": ""}
    body.update(overrides)
    return G3112Request(body={"g3112InBlock": G3112InBlock(**body)})


def test_field_sets_match_guide():
    assert set(G3112InBlock.model_fields) == set(GUIDE_IN)
    assert set(G3112OutBlock.model_fields) == set(GUIDE_OUT)
    assert set(G3112OutBlock1.model_fields) == set(GUIDE_OUT1)


@pytest.mark.parametrize("model", [G3112OutBlock, G3112OutBlock1])
def test_out_fields_are_strings(model):
    for name, info in model.model_fields.items():
        assert info.annotation is str, f"{model.__name__}.{name} must stay str (guide type String)"


def test_request_codes_come_from_guide():
    assert set(typing.get_args(G3112InBlock.model_fields["exgubun"].annotation)) == set(GUIDE_EXGUBUN)
    assert set(typing.get_args(G3112InBlock.model_fields["rankgubun"].annotation)) == set(GUIDE_RANKGUBUN)
    assert typing.get_args(G3112InBlock.model_fields["delaygb"].annotation) == ("R",)
    description = G3112InBlock.model_fields["rankgubun"].description
    for label in GUIDE_RANKGUBUN.values():
        assert label in description
    with pytest.raises(Exception):
        G3112InBlock(natcode="US", exgubun="5", rankgubun="0")


@pytest.mark.parametrize("model", [G3112InBlock, G3112OutBlock, G3112OutBlock1])
def test_examples_round_trip(model: typing.Type[BaseModel]):
    for name, info in model.model_fields.items():
        assert info.examples, f"{model.__name__}.{name} needs examples"
        for example in info.examples:
            TypeAdapter(info.annotation).validate_python(example)


def test_request_envelope_and_rate_limit():
    request = _request()
    assert request.header.tr_cd == "g3112"
    assert request.header.tr_cont == "N"
    options = request.options
    assert (options.rate_limit_count, options.rate_limit_seconds) == (GUIDE_TRANSACTIONS_PER_SECOND, 1)
    assert options.on_rate_limit == "wait" and options.rate_limit_key == "g3112"
    tr = TrG3112(request)
    assert tr._generic._url == URLS.MARKET_URL
    assert URLS.MARKET_URL.endswith("/overseas-stock/market-data")


def test_build_response_parses_guide_shape_and_numeric_json():
    tr = TrG3112(_request())
    response = tr._build_response(_Resp(200), SAMPLE, HEADERS, None)
    assert isinstance(response, G3112Response)
    assert response.error_msg is None and response.rsp_cd == "00000"
    assert response.block.cts_value == "0000000000000021" and response.block.rec_count == "2"
    assert response.header.tr_cont == "Y" and response.header.tr_cont_key == "NEXT"
    tsla, ibm = response.block1
    assert tsla.keysymbol == "82TSLA" and tsla.price == "248.500000" and tsla.rate == "1.33"
    # Numeric JSON (if LS ever sends it) is kept as text, not rejected.
    assert ibm.price == "211.5" and ibm.volume == "3100000" and ibm.rate == "-0.59"


def test_build_response_reports_errors():
    tr = TrG3112(_request())
    http = tr._build_response(_Resp(500), {"rsp_cd": "", "rsp_msg": "busy"}, {}, None)
    assert http.error_msg == "HTTP 500: busy" and http.block is None and http.block1 == []
    exc = tr._build_response(None, None, None, RuntimeError("socket closed"))
    assert exc.error_msg == "socket closed"
    rejected = tr._build_response(_Resp(200), {"rsp_cd": "01234", "rsp_msg": "조회불가"}, HEADERS, None)
    assert rejected.error_msg is None and rejected.rsp_cd == "01234" and rejected.block1 == []


def test_continuation_updater_copies_cursor():
    tr = TrG3112(_request())
    response = tr._build_response(_Resp(200), SAMPLE, HEADERS, None)
    captured = {}

    def _fake_occurs(updater, callback=None, delay=1):
        updater(tr.request_data, response)
        captured["cts"] = tr.request_data.body["g3112InBlock"].cts_value
        captured["cont"] = (tr.request_data.header.tr_cont, tr.request_data.header.tr_cont_key)
        return [response]

    tr._generic.occurs_req = _fake_occurs
    tr.occurs_req()
    assert captured == {"cts": "0000000000000021", "cont": ("Y", "NEXT")}


def test_market_accessor_alias_and_export():
    import programgarden_finance
    from programgarden_finance.ls.overseas_stock.market import Market

    assert programgarden_finance.g3112.G3112InBlock is G3112InBlock
    assert Market.시세순위 is Market.g3112

    from programgarden_finance.ls.token_manager import TokenManager

    manager = TokenManager()
    manager.access_token, manager.token_type = "offline-test", "Bearer"
    tr = Market(token_manager=manager).시세순위(
        body=G3112InBlock(natcode="US", exgubun="3", rankgubun="2"))
    assert isinstance(tr, TrG3112)
    assert tr.request_data.header.authorization.endswith("offline-test")
    assert tr.request_data.body["g3112InBlock"].exgubun == "3"


# Domestic ranking TRs used by KoreaStockRankingNode — LS guide transactionPerSec.
GUIDE_DOMESTIC_TPS = {"t1441": 1, "t1452": 2, "t1463": 1, "t1444": 2}


@pytest.mark.parametrize("tr_code,tps", sorted(GUIDE_DOMESTIC_TPS.items()))
def test_domestic_ranking_rate_limits_match_guide(tr_code, tps):
    from importlib import import_module

    blocks = import_module(f"programgarden_finance.ls.korea_stock.ranking.{tr_code}.blocks")
    request_cls = getattr(blocks, f"{tr_code.upper()}Request")
    options = request_cls.model_fields["options"].default
    assert (options.rate_limit_count, options.rate_limit_seconds) == (tps, 1)
    assert options.rate_limit_key == tr_code and options.on_rate_limit == "wait"
