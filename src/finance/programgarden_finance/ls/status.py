from enum import Enum


class RequestStatus(Enum):
    """
    요청 상태를 나타내는 Enum 클래스입니다.
    - REQUESTING: 첫 요청이 진행 중
    - SUCCESS: 요청이 성공적으로 처리됨
    - FAIL: 요청이 실패함
    - END: 모든 요청 시도가 완료됨
    - OCCURS: 연속 요청을 진행함
    """

    REQUEST = "request"
    """ 데이터 요청 """
    OCCURS_REQUEST = "occurs_request"
    """ 추가 데이터 요청 """
    RESPONSE = "response"
    """ 데이터 응답 """
    COMPLETE = "complete"
    """ 모든 데이터 요청/응답 완료 """
    FAIL = "fail"
    """ 요청 실패 """
    CLOSE = "close"
    """ 종료 """
