# 소개

[![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/tag/OWNER/REPO?label=release&sort=semver&logo=github)](https://github.com/OWNER/REPO/releases)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_3.0-blue.svg)](./LICENSE)
[![Company: LS](https://img.shields.io/badge/지원되는_증권사-LS증권-008FC7.svg)]()
[![Product: OverseasStock](https://img.shields.io/badge/지원되는_자동매매-해외주식,해외선물-purple.svg)]()



<br>

## 👏 오픈소스 개발 진행 상황
- 해외 주식·해외 선물 전략 추가 중
- 해외 옵션 추가 예정
- 코인 추가 예정

> **⚠️ 경고**: ProgramGarden 자동화매매는 현재 **테스트 버전**이므로 오류를 계속 확인하고 있습니다. 따라서 정식 버전이 출시되기 전까지는 **소액 투자**를 권장합니다. 오픈소스 사용 시 발생하는 문제에 대한 책임은 사용자에게 있으며, 라이선스를 반드시 확인해 주세요. [라이선스 보기](https://github.com/programgarden/programgarden/blob/main/LICENSE)

<br>

## 📖 오픈소스 가이드

* **개요**
  * [소개](#intro)
  * [오픈소스 구조](#structure)
  * [팀원들](#owners)
* **투자자 가이드**
  * [자동화매매 빠르게 사용하기](docs/non_dev_quick_guide.md)
* **개발자 가이드**
  * [파이썬으로 DSL 커스텀하기](docs/custom_dsl.md)
  * [자동화매매 오픈소스 성장에 기여하기](docs/contribution_guide.md)
  * [LS증권 코드 사용하기](docs/finance_guide.md)
* **시각화•WTS 만들기**
  * Dashboard 가이드로 이동 (준비중)

<br>

<a id="intro"></a>
## 📌 소개 

![programgarden 그리고 ls](docs/images/programgarden_ls.png)

**ProgramGarden**은 코딩을 모르는 시스템 트레이더와 투자자가 쉽게 사용하도록 지원하는 **개인 맞춤형 자동화매매 오픈소스 플랫폼**입니다.

유튜버 [**프로그램 동산**](https://programgarden.com)과 [**LS증권**](https://ls-sec.co.kr) 협업으로 **시스템 트레이더 생태계** 발전에 기여하기 위하여 오랜 연구 끝에

`DSL`_(Domain Specific Language, 특정 목적에 특화된 언어)_ 을 개발했으며, 코딩 경험이 없어도 손쉽게 자동매매를 실행할 수 있고 외부 개발자가 기여한 전략을 조합해서 투자에 사용 할 수 있습니다.

해외주식 · 해외선물 업데이트 내용과 국내 주식·코인 등의 업데이트 일정을 유튜브와 커뮤니티에서 실시간으로 공유하고 있으니, 꼭 구독하고 알림을 설정해 주세요!

- 공식사이트: https://programgarden.com
- 프로그램 동산 유튜브: https://youtube.com/@programgarden
- 시스템 트레이더 커뮤니티: https://cafe.naver.com/programgarden
- LS증권 유튜브: https://www.youtube.com/@lssec
- 비즈니스 문의: coding@programgarden.com

<br>

<a id="structure"></a>
## 🏗️ 오픈소스 구조

**강력하면서도 쉽게 쓸 수 있는 자동화매매 플랫폼**에 대해서 간략하게 설명합니다.

![ProgramGarden 아키텍처](docs/images/architecture.png)

#### 구성 요소

* **ProgramGarden**\
 → 자동화 매매에 최적화된 DSL을 제공하는 라이브러리입니다.
* **ProgramGarden Core**\
  → 시스템의 타입 정의, 에러 처리, 로그 관리를 제공합니다.
* **ProgramGarden Finance**\
  → 증권사 API를 간편하게 사용할 수 있도록 지원하는 라이브러리입니다.
* **ProgramGarden Community**\
  → 시스템 트레이딩 생태계 발전에 기여하고자 하는 개발자들이 모여 만드는 커뮤니티 라이브러리 공간입니다. 시스템 트레이더라면 누구나 기여할 수 있습니다.
* **ProgramGarden Dashboard**\
  → 개인화된 자동화 매매 대시보드가 필요한 개발자를 위한 라이브러리입니다. 간단한 코드 몇 줄로 데이터 분석에 필요한 시각화와 WTS 스타일의 거래 화면까지 만들 수 있습니다.


<br>

<a id="owners"></a>
## 👥 운영진

* **프로그램 동산** – DSL 개발 담당 [링크딘 주소](https://www.linkedin.com/in/masterjyj/)
* **라쿠너리 동산** – 시각화, WTS 개발 담당 [링크딘 주소](https://www.linkedin.com/in/rakunary)
* **클라우드 동산** – AI & 서버 개발 담당 (준비중)
* **디자인 동산** – 콘텐츠와 디자인 담당 [링크딘 주소](https://www.linkedin.com/in/jina-jang-4561b717a/)
