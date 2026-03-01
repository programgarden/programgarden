"""주식주문 SC0~SC4 통합 실시간 테스트

SC0~SC4 전부 리스너를 등록하고, 실제 매수 주문을 넣어
실시간 주문 이벤트가 정상 수신되는지 확인합니다.

테스트 시나리오:
1. SC0~SC4 리스너 전부 등록 (SC0 하나 등록으로 5개 전부 활성화되는지 확인)
2. 삼성전자 시장가 1주 매수 주문
3. SC0(접수), SC1(체결) 등 이벤트 수신 확인
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.SC0.blocks import SC0RealResponse
from programgarden_finance.ls.korea_stock.real.SC1.blocks import SC1RealResponse
from programgarden_finance.ls.korea_stock.real.SC2.blocks import SC2RealResponse
from programgarden_finance.ls.korea_stock.real.SC3.blocks import SC3RealResponse
from programgarden_finance.ls.korea_stock.real.SC4.blocks import SC4RealResponse

logger = logging.getLogger(__name__)
load_dotenv()


async def run_example():
    ls = LS.get_instance()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )
    if login_result is False:
        logger.error("로그인 실패")
        return

    # ─── SC0~SC4 리스너 전부 등록 ───
    def on_sc0(resp: SC0RealResponse):
        print(f"[SC0 주문접수] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")
        if resp.body:
            b = resp.body
            print(f"  → 주문번호:{b.ordno} 종목:{b.expcode}({b.hname}) "
                  f"구분:{b.ordchegb} 수량:{b.ordqty} 가격:{b.ordprice}")

    def on_sc1(resp: SC1RealResponse):
        print(f"[SC1 주문체결] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")
        if resp.body:
            b = resp.body
            print(f"  → 종목:{b.shtnIsuno}({b.Isunm}) "
                  f"체결가:{b.execprc} 체결수량:{b.execqty} "
                  f"주문유형:{b.ordxctptncode} 매매구분:{b.bnstp}")

    def on_sc2(resp: SC2RealResponse):
        print(f"[SC2 주문정정] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")
        if resp.body:
            b = resp.body
            print(f"  → 종목:{b.shtnIsuno}({b.Isunm}) 주문유형:{b.ordxctptncode}")

    def on_sc3(resp: SC3RealResponse):
        print(f"[SC3 주문취소] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")
        if resp.body:
            b = resp.body
            print(f"  → 종목:{b.shtnIsuno}({b.Isunm}) 주문유형:{b.ordxctptncode}")

    def on_sc4(resp: SC4RealResponse):
        print(f"[SC4 주문거부] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")
        if resp.body:
            b = resp.body
            print(f"  → 종목:{b.shtnIsuno}({b.Isunm}) 주문유형:{b.ordxctptncode}")

    client = ls.korea_stock().real()
    await client.connect()
    print(f"WebSocket 연결 성공. _sc01234_connect={client._sc01234_connect}")

    # SC0 하나만 등록 → SC0~SC4 전부 활성화 확인
    sc0 = client.SC0()
    sc0.on_sc0_message(on_sc0)
    print(f"SC0 리스너 등록 완료. _sc01234_connect={client._sc01234_connect}")

    # 나머지 SC1~SC4도 리스너만 추가 (추가 websocket 등록 없이 _on_message만)
    sc1 = client.SC1()
    sc1.on_sc1_message(on_sc1)
    print(f"SC1 리스너 등록 완료. _sc01234_connect={client._sc01234_connect}")

    sc2 = client.SC2()
    sc2.on_sc2_message(on_sc2)

    sc3 = client.SC3()
    sc3.on_sc3_message(on_sc3)

    sc4 = client.SC4()
    sc4.on_sc4_message(on_sc4)
    print("SC0~SC4 리스너 전부 등록 완료.")

    # 주문 실시간 등록 후 잠시 대기
    await asyncio.sleep(3)

    # ─── 실제 매수 주문 (동전주 1주 시장가) ───
    # 저가 종목으로 테스트 (예수금 절약)
    TEST_STOCK = "024850"  # HLB이노베이션 (저가주)
    print(f"\n=== {TEST_STOCK} 1주 시장가 매수 주문 ===")
    order_client = ls.korea_stock().order()
    try:
        from programgarden_finance import CSPAT00601
        m_order = order_client.cspat00601(
            CSPAT00601.CSPAT00601InBlock1(
                IsuNo=TEST_STOCK,
                OrdQty=1,
                OrdPrc=0,
                BnsTpCode="2",          # 매수
                OrdprcPtnCode="03",     # 시장가
                MgntrnCode="000",
                LoanDt="",
                OrdCndiTpCode="0",
            )
        )
        response = m_order.req()
        print(f"주문 rsp_cd={response.rsp_cd} rsp_msg={response.rsp_msg}")
        if response.block2:
            print(f"주문번호: {response.block2.OrdNo} 종목: {response.block2.IsuNm}")
    except Exception as e:
        print(f"매수 주문 오류: {e}")

    # 실시간 이벤트 수신 대기
    print("\n실시간 이벤트 수신 대기 중... (30초)")
    await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run_example())
