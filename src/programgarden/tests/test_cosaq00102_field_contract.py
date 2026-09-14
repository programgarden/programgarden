"""COSAQ00102 응답 필드명이 SDK 모델과 어긋나지 않는지 — 조용한 썩음 방지.

2026-09-14 실사고 직전: 체결 재조정의 배치 조회를 쓰면서 종목 필드를 `IsuNo` 로 적었다.
실제 이름은 `ShtnIsuNo`(단축종목번호)다. `getattr(item, "IsuNo", "")` 는 예외 없이 빈
문자열을 돌려주므로, **종목 대조 가드가 조용히 무력화**된다 — 계좌를 바꾼 뒤 주문번호가
겹치면 남의 체결을 우리 주문으로 원장에 넣게 된다. 릴리스 전에 SDK 원문을 열어 잡았다.

getattr 기본값은 오타를 숨긴다. 그래서 이름 자체를 모델과 대조한다.
"""
import pytest

from programgarden_finance.ls.overseas_stock.accno.COSAQ00102 import blocks as cosaq_blocks


def _out_block3():
    for name in ("COSAQ00102OutBlock3",):
        model = getattr(cosaq_blocks, name, None)
        if model is not None:
            return model
    pytest.fail("COSAQ00102OutBlock3 를 찾지 못했다 — SDK 구조가 바뀌었다")


@pytest.mark.parametrize("field", ["OrdNo", "ShtnIsuNo", "ExecQty", "OvrsExecPrc", "OvrsOrdPrc", "ExecTime"])
def test_batch_fill_query_fields_exist(field):
    """재조정 배치 조회가 읽는 필드가 실제로 응답 모델에 있어야 한다."""
    assert field in _out_block3().model_fields, (
        f"{field} 가 COSAQ00102OutBlock3 에 없다 — getattr 기본값 때문에 런타임엔 "
        f"조용히 빈 값이 되고 재조정이 틀린 판단을 한다"
    )


def test_both_symbol_names_exist_and_we_prefer_the_short_one():
    """LS 는 한 블록에 비슷한 이름을 여럿 둔다 — 이번 사고의 정확한 형태.

    `ShtnIsuNo`(단축종목번호)와 `IsuNo`(종목번호)가 **둘 다** 있다. 이 저장소는
    ShtnIsuNo 를 종목코드로 쓰고 IsuNo 를 폴백으로 둔다(잔고·체결 파싱 관행).
    둘 중 하나가 사라지면 폴백 순서를 다시 판단해야 하므로 여기서 잠근다.
    """
    fields = _out_block3().model_fields
    assert "ShtnIsuNo" in fields, "종목코드 정본이 사라졌다"
    assert "IsuNo" in fields, "폴백이 사라졌다 — getattr 폴백을 정리할 것"


def test_market_code_exists_but_is_a_code_not_an_exchange_name():
    """`OrdMktCode` 는 있지만 코드(81/82)라 거래소 이름이 아니다.

    재조정은 이 값을 쓰지 않고 우리 주문 원장의 exchange 를 쓴다 — 원장 값이 노드가
    실제로 주문에 실어 보낸 값이라 권위가 있다.
    """
    assert "OrdMktCode" in _out_block3().model_fields
