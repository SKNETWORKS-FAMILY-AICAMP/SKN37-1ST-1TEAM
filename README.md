# 🚗 차량 구매 추천 서비스

<br>

## 🛠️ 기술 스택

| 구분 | 기술 |
|---|---|
| **Language** | ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) |
| **Frontend** | ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white) |
| **Database** | ![MySQL](https://img.shields.io/badge/MySQL%208.x-4479A1?style=for-the-badge&logo=mysql&logoColor=white) |
| **Development** | ![Visual Studio Code](https://img.shields.io/badge/Visual%20Studio%20Code-007ACC?style=for-the-badge&logo=visualstudiocode&logoColor=white) |
| **Collaboration** | ![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white) ![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white) |
<br>
 

## 🗓️ 1. 프로젝트 개요

- **프로젝트 명:** 차량 구매 추천 서비스
- **프로젝트 진행기간:** 2026.09.23 ~ 2026.09.28
<br>


## 📖 2. 프로젝트 소개 및 필요성

### 프로젝트 소개

차량 구매 시 구매자의 특성을 입력하면 조건에 적합한 차량을 추천하여
고객의 합리적인 차량 구매를 돕는 서비스입니다.

### 프로젝트 필요성

- 자동차 구매 시 차량 가격, 연료비, 주행 환경 등 다양한 요소를 각각 비교해야 하는 번거로움이 있습니다.

- 사용자의 **거주 지역, 출퇴근 거리, 구매 예산, 선호 차량 조건**을 바탕으로 차량을 선별하고, **가격·연료비·지역 인프라를 종합적으로 점수화**하여 적합한 차량을 추천하고자 했습니다.

- 또한 **차량 통계, 기업 FAQ, 월납입금 계산, AI 챗봇** 등의 기능을 함께 제공하여 차량 탐색부터 비교 및 구매 판단까지 한 서비스에서 확인할 수 있도록 구현했습니다.
<br>

## 🚗 3. 주요 기능

### 🔎 3.1 사용자 맞춤형 차량 추천

사용자가 입력한 조건을 기반으로 적합한 차량을 추천합니다.

- 거주 지역
- 출퇴근 거리
- 차량 구매 예산
- 선호 차량 크기
- 선호 연료

### 📊 3.2 종합점수 산정

추천 차량의 순위를 결정하기 위해 다음 세 가지 요소를 점수화하여
종합점수를 산출합니다.

- **연료비 점수**: 사용자의 출퇴근 거리와 차량 연비 등을 기반으로 예상 연료비를 계산하여 점수화
- **가격 점수**: 사용자가 설정한 구매 예산과 차량 실구매가를 비교하여 점수화
- **인프라 점수**: 지역별 전기차 등록 대수 대비 충전기 수를 활용하여 충전 인프라 수준을 점수화

각 점수에 가중치를 적용하여 최종 종합점수를 계산하고,
종합점수가 높은 차량을 우선적으로 추천합니다.

> **종합점수 = 연료비 점수 × 40% + 가격 점수 × 40% + 인프라 점수 × 20%**

이를 통해 차량 가격뿐만 아니라 유지비와 지역별 이용 환경까지
종합적으로 고려한 차량 추천 결과를 제공합니다.


### 💬 3.3 자동차 FAQ 제공 및 AI 챗봇 

자동차 제조사의 FAQ 데이터를 수집하여 차량 구매 및 이용과 관련된 정보를 제공합니다.

- 제조사별 FAQ 검색 및 조회
- FAQ 데이터를 기반으로 사용자의 질문에 답변하는 **AI 챗봇 기능 제공**

### 💰 3.4 월납입금 계산

차량 가격과 계약금, 할부 기간, 연이자율을 바탕으로
**원리금균등상환 방식의 예상 월 납입금**을 계산합니다.

- 차량 검색을 통한 가격 자동 입력
- 월 납입금, 총 납입액 및 총 이자 계산
- 회차별 원금·이자 구성 및 잔여 원금 추이 시각화
- 회차별 상환 스케줄 제공
<br>



## 📊 4. 데이터 수집 및 가공

차량 추천에 필요한 다양한 데이터를 수집하고 가공하여
MySQL 데이터베이스에 저장했습니다.

| 테이블명 | 수집 데이터 | 수집 방법 | 출처 |
|---|---|---|---|
| `car_info` | 브랜드, 차종, 차량 크기, 연료 타입, 가격, 연비 | 크롤링 | 다나와 자동차 |
| `electric_car_subsidies` | 지역별 전기차 구매보조금 지급 현황 | Open API | [한국환경공단 - 전기차구매보조금지급현황정보](https://www.data.go.kr/data/15121062/fileData.do) |
| `electric_vehicles` | 지역별 전기차 등록 대수 | Open API | [한국교통안전공단 - 전국 전기차 차종별·용도별 차량 등록대수](https://www.data.go.kr/data/15142951/fileData.do) |
| `ev_chargers` | 지역별 전기자동차 충전소 정보 | Open API | [한국환경공단 - 전기자동차 충전소 정보](https://www.data.go.kr/data/15076352/openapi.do) |
| `sido_oil_price` | 시도별 주유소 평균가격 | Open API | [한국석유공사 오피넷 - 시도별 주유소 평균가격](https://www.opinet.co.kr/user/custapi/custApiInfo.do) |
| `*_faq` | 제조사별 자동차 FAQ | 크롤링 | 각 자동차 제조사 공식 홈페이지 |
<br>


## 🗄️ 5. 주요 데이터베이스 구조 (DB)

본 프로젝트는 수집 및 가공한 데이터를 MySQL에 저장하고,
차량 추천에 필요한 데이터를 조회하기 위해 `view_car_recommend` View를 구성했습니다.


### ERD

> <img width="680" height="611" alt="ERD_normal" src="https://github.com/user-attachments/assets/518f9e65-830e-484b-a7d0-d18e792f3f3d" />

<br>

## 💻 6. Streamlit 화면 (UI/UX)
### 6.1 사용자 조건 입력
> <img width="2880" height="1434" alt="7" src="https://github.com/user-attachments/assets/eadb39a4-22a7-46de-888f-f6ab44e19ce5" />

### 6.2 맞춤형 차량 추천 결과
> <img width="2880" height="1440" alt="5" src="https://github.com/user-attachments/assets/a6f26d3e-6a81-4c3a-985a-be4b72d624d8" /> <img width="2352" height="918" alt="3" src="https://github.com/user-attachments/assets/dc9c8138-a42d-437d-a008-be13d4469913" />


### 6.3 추천 차량 비교 
> <img width="2380" height="1168" alt="4" src="https://github.com/user-attachments/assets/2893ef56-36f5-4a4d-ac23-b70d8a987419" />

### 6.4 자동차 통계 조회
><img width="2286" height="1382" alt="6" src="https://github.com/user-attachments/assets/2905aeab-7e2a-4db3-8537-3ca172d3b2f9" />

### 6.5 차량 검색 및 월 납입금 계산
> <img width="2268" height="1230" alt="2" src="https://github.com/user-attachments/assets/54553a62-63e3-4035-aa0d-b904b8fc83fb" /> <img width="2269" height="895" alt="1" src="https://github.com/user-attachments/assets/1d69461c-08f8-4cf6-9070-a44bd3e64b7c" />


## 👥 7. 팀원 소개 및 역할

| 이름 | 역할 및 담당 업무 |
|------|-------------------|
| 서민석 | 팀장 · 데이터 수집 · 프로젝트 총괄 및 발표 |
| 권승현 | 데이터 수집 · 서비스 화면 설계 및 UI 구현 |
| 이재현 | 데이터 수집 및 DB 구축 · GitHub 관리 · 최종 결과물 정리 |
| 한승아 | 데이터 수집 · 데이터 가공 및 DB 설계 |

## 회고

### 서민석
> 수업시간에 배운 내용을 토대로 오픈API와 크롤링을 통해 데이터를 구축하고 직접 서비스를 구현하여 발표하는 프로젝트를 진행 할 수 있었습니다. 비전공자로써 처음 해보는 부분이어서 막막하고 크롤링하는 부분에서 막히는 부분이 있었지만, 전공자이며 좋은 팀원들이 어려운 부분을 해결하고 도와줘서 프로젝트를 잘 마무리 할 수 있었습니다. 하나도 할 줄 모르던 내가 팀원들의 도움으로 프로젝트를 끝내고나니 많은 부분을 배워서 앞으로 더 공부해야겠다는 생각이 들었습니다.

### 권승현 
> 사이드바 메뉴 순서에 맞춰 화면별 UI를 정리하고, 홈 화면 브랜드 카드에 로고 이미지를 적용했으며 AI 챗봇 상담 화면과 FAQ 카테고리·검색 UI를 구현했습니다. 도중 로고가 안 뜨는 버그를 겪으며 원인이 코드가 아니라 데이터 연결에 있었다는 걸 확인했고, 화면이 안 뜰 땐 코드보다 데이터 연결부터 점검해야 한다는 걸 배웠습니다. UI를 먼저 만들고 데이터 구조를 나중에 맞추다 보니 죽은 코드가 생긴 점은 아쉬웠고, 다음엔 와이어프레임을 먼저 구상하고 시작해야겠다는것을 이번 프로젝트를 통해 배우게됬습니다.

### 이재현
> 프로젝트를 진행하며 데이터 수집 과정에서 API 사용이 제한되거나, 회사별로 다른 웹 구조로 인해 크롤링이 원활하지 않는 등 예상하지 못한 문제들을 경험했습니다. DB 구축과 GitHub 결과물 정리 과정에서도 생각보다 많은 시행착오가 있었지만, 그 과정에서 대학에서 배웠던 내용이 실제 프로젝트에 어떻게 활용되는지 다시 체감할 수 있었습니다. 특히 생성형 AI를 활용해 문제를 해결하면서 AI가 개발 생산성을 크게 높일 수 있다는 점을 느꼈고, 프롬프트를 효과적으로 작성하는 능력의 중요성도 알게 되었습니다. 동시에 AI에 의존하기보다는 기본적인 문제는 스스로 고민하고 해결하는 과정이 개발 역량을 키우는 데 중요하다는 점을 배웠습니다.

### 한승아
> 가장 고민했던 부분은 종합점수에서 인프라 점수의 산정 기준과 비중을 결정하는 과정이었습니다. 이를 통해 단순한 데이터 수집보다 서비스 목적에 맞게 데이터를 가공하고 활용하는 것이 중요하다는 점을 배웠습니다. 또한 DB 정규화와 ERD 설계, View 생성을 진행하며 데이터의 구조와 조회 효율성을 함께 고려해야 한다는 점을 이해했습니다. 이번 프로젝트를 통해 데이터 수집부터 DB 구축, 서비스 적용까지의 과정이 서로 유기적으로 연결되어 있다는 점을 배울 수 있었습니다.


