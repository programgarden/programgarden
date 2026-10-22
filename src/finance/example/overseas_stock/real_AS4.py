"""
해외주식 주문거부 실시간 (AS4) 예시 — 필드 목록용

AS0~AS4 는 계좌 실시간이라 하나만 등록해도 접수·체결·정정·취소·거부가 모두 온다.
이 예제는 거부(AS4) 이벤트에서 화면에 쓸 만한 필드만 골라 출력한다. 계좌번호 등
민감한 필드는 출력하지 않는다.

⚠️ 이 예제는 실제 거부 이벤트로 실행해 본 적이 없다. 필드 이름은 SDK 모델
(`AS4RealResponseBody`)과 LS 가이드의 AS4 응답 필드에서 가져왔다. 값의 형식(소수점,
시간대 등)은 관측 전까지 단정하지 말 것.

사용법:
    APPKEY=... APPSECRET=... python real_AS4.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from programgarden_finance import LS, AS4

logger = logging.getLogger(__name__)

load_dotenv()

# 거부 이벤트에서 보여 줄 필드 (가이드 AS4 응답 필드명 그대로)
REJECT_FIELDS = (
    "sOrdxctPtnCode",  # 주문체결유형코드
    "sOrdNo",          # 주문번호
    "sOrgOrdNo",       # 원주문번호
    "sShtnIsuNo",      # 단축종목번호
    "sBnsTp",          # 매매구분 (AS4 소스에 코드표 없음 — 받은 값 그대로)
    "sOrdQty",         # 주문수량
    "sOrdPrc",         # 주문가격
    "sRjtQty",         # 거부수량
    "sRjtRsn",         # 거부사유
    "sOrdTrxPtnCode",  # 주문처리유형코드
)


async def run_example():
    ls = LS.get_instance()

    if ls.login(appkey=os.getenv("APPKEY"), appsecretkey=os.getenv("APPSECRET")) is False:
        logger.error("로그인 실패")
        return

    def on_message(resp: AS4.AS4RealResponse):
        body = resp.body
        if body is None:
            # 등록 응답(ACK) 등 본문이 없는 프레임
            print(f"[AS4] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")
            return
        print("[AS4 거부]", {name: getattr(body, name, None) for name in REJECT_FIELDS})

    client = ls.overseas_stock().real()
    await client.connect()

    as4 = client.AS4()
    as4.on_as4_message(on_message)  # 계좌 실시간 등록(tr_type=1)을 함께 보낸다

    await asyncio.sleep(120)

    as4.on_remove_as4_message(on_message)
    await client.close()


if __name__ == "__main__":
    asyncio.run(run_example())
