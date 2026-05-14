# FastAPI 프로젝트 전반 분석 보고서

**분석 일자:** 2025-03-05  
**프로젝트명:** Healthcare Checkup API (fastapi-app)

---

## 1. 개요

본 프로젝트는 **헬스케어 검진 예약 플랫폼**의 데이터를 조회하기 위한 **Read-only REST API**입니다.  
에이전트(Agent)나 외부 클라이언트가 고객사·회원·예약·결제·로스터·정책 등 도메인 데이터를 질의할 수 있도록 설계되어 있습니다.

- **프레임워크:** FastAPI
- **DB:** MySQL (PyMySQL, DictCursor)
- **환경:** 비운영(EDU) / 운영(HOPS) 이원화
- **원칙:** INSERT/UPDATE/DELETE 금지, 조회(READ) 전용

---

## 2. 프로젝트 구조

```
fastapi-app/
├── main.py                 # FastAPI 앱 생성 및 라우터 등록
├── db.py                   # DB 연결 설정 (EDU/PROD)
├── requirements.txt        # 의존성 (fastapi, uvicorn)
├── .env                    # DB_* 환경 변수 (비공개)
├── .gitignore
├── README.md
├── PROJECT_REPORT.md       # 본 보고서
├── docs/
│   └── request-log.md      # 사용자 요청 로그 (기능 개선용)
├── routers/                # 도메인별 API
│   ├── customers.py        # 고객사 (HC_CUSTOMER)
│   ├── persons.py          # 회원·통합회원 (HC_USER, HC_USER_COMMON, HC_CUSTOMER_MAP)
│   ├── reservations.py     # 예약 (HC_RESERV, HC_RESERV_TEST_ITEM)
│   ├── payments.py         # 결제 (HC_PAY)
│   ├── rosters.py          # 수검자 로스터 (HC_CHECKUP_ROSTER)
│   ├── policies.py         # 검진 정책 (HC_CHECKUP_POLICY)
│   └── schema.py           # 테이블 스키마 조회 (SHOW COLUMNS)
├── tables/                 # 테이블 명세 (MD)
│   ├── hc-user.mdc, hc-user-common.mdc, hc-customer.mdc, hc-customer-map.mdc
│   ├── hc-reserv.mdc, hc-pay.mdc
│   ├── hc-checkup-roster.mdc, hc-checkup-policy.mdc, hc-checkup-product.mdc, hc-checkup-propos.mdc
│   ├── hc-partner-center.mdc
│   ├── hc-checkup-item-cd.mdc, hc-test-item-cd.mdc
│   ├── hc-reserv-test-item.mdc, hc-product-test-item.mdc
│   └── ...
└── .cursor/
    ├── rules/              # 에이전트/개발 가이드
    │   ├── usage.mdc       # API 우선 응답, 요청 로깅
    │   ├── schema-info.mdc # Read-only, API 설계, 도메인 구조
    │   ├── user-schema.mdc
    │   ├── reservation-schema.mdc
    │   ├── product-schema.mdc
    │   └── item-schema.mdc
    └── commands/
        └── server.md
```

---

## 3. 기술 스택 및 의존성

| 구분 | 내용 |
|------|------|
| **Python** | (버전 명시 없음, 3.x 가정) |
| **웹** | FastAPI ≥0.109.0, Uvicorn[standard] ≥0.27.0 |
| **DB** | PyMySQL (코드에서 사용, requirements.txt에는 미기재) |
| **환경** | python-dotenv (db.py에서 load_dotenv 사용) |

**참고:** `db.py`에서 `pymysql`, `python-dotenv`를 사용하므로 `requirements.txt`에 추가하는 것이 좋습니다.

---

## 4. 데이터베이스 설계

### 4.1 연결 방식

- **비운영(EDU):** `get_db_connection()` 또는 `get_db_connection(prod=False)`  
  → `.env`의 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- **운영(HOPS):** `get_db_connection(prod=True)`  
  → `DB_HOST_PROD`, `DB_PORT_PROD`, `DB_USER_PROD`, `DB_PASSWORD_PROD`, `DB_NAME_PROD`

컨텍스트 매니저로 연결·커밋·롤백·종료를 처리합니다.

### 4.2 주요 테이블 (도메인별)

| 도메인 | 테이블 | 설명 |
|--------|--------|------|
| **고객사** | HC_CUSTOMER | 법인(고객사) 마스터 |
| **회원** | HC_USER | 법인 회원 |
| | HC_USER_COMMON | 통합 회원 |
| | HC_CUSTOMER_MAP | 통합회원 ↔ 법인회원 매핑 |
| **예약** | HC_RESERV | 검진 예약 |
| | HC_RESERV_TEST_ITEM | 예약별 검사 항목 |
| **결제** | HC_PAY | 결제 |
| **로스터** | HC_CHECKUP_ROSTER | 수검자(검진 대상자) |
| **정책/상품** | HC_CHECKUP_POLICY | 고객사별 검진 정책(연도·기간) |
| | HC_CHECKUP_PRODUCT | 검진 상품 |
| | HC_CHECKUP_PROPOS | 검진 제안 |
| **기타** | HC_PARTNER_CENTER | 파트너 센터 |
| | HC_TEST_ITEM_CD, HC_CHECKUP_ITEM_CD | 검사/검진 항목 코드 |
| | HC_PRODUCT_TEST_ITEM | 상품별 검사 항목 |

상태 코드 예: `USER_ST` '00'=활성, '90'=삭제 / `CHECKUP_ROSTER_ST` '00'=활성 / `RESERV_ST` 10=신청, 50=확정 등 / `PAY_ST` 70=결제완료.

---

## 5. API 엔드포인트 요약

모든 DB 조회 API는 쿼리 파라미터 `prod: bool = False`로 **EDU(비운영)** / **HOPS(운영)** 를 선택합니다.

### 5.1 공통

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 환영 메시지 |
| GET | `/health` | 헬스 체크 |

### 5.2 고객사 (`/customers`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/customers` | 고객사명 부분 일치 검색 (CUSTOMER_ID, CUSTOMER_NAME) |
| GET | `/customers/detail` | CUSTOMER_ID로 상세 (도메인, MAIN_CUSTOMER_ID 등) |

### 5.3 회원/인물 (`/persons`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/persons/unified-member` | 이름+회사로 통합회원 여부 및 법인·통합 회원 정보 |
| GET | `/persons/unified-by-id` | 통합 로그인 USER_ID로 통합회원 + 연결된 법인회원 |
| GET | `/persons/unified-accounts-by-corporate` | 법인회원 USER_NO로 연결된 통합회원 목록 |
| GET | `/persons/unified-by-name` | 통합회원 이름 검색 (USER_ST='00') |
| GET | `/persons/corporate-by-employ-no` | CUSTOMER_ID + 사번(EMPLOY_NO)으로 법인회원 |
| GET | `/persons/by-user-no` | USER_NO로 법인회원 1건 |

### 5.4 예약 (`/reservations`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/reservations/count` | 예약 건수 (reg_dt, company, reserv_st 필터) |
| GET | `/reservations/by-person` | 법인회원(USER_NO+CUSTOMER_ID)별 예약 목록 (policy_year 옵션) |
| GET | `/reservations/test-items` | RESERV_NO별 검사 항목 (HC_RESERV_TEST_ITEM + 항목명) |
| GET | `/reservations/detail` | RESERV_NO로 예약 상세 (금액 등) |

### 5.5 결제 (`/payments`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/payments/by-reservation` | RESERV_NO별 HC_PAY 목록, 결제완료(PAY_ST=70) 여부 포함 |

### 5.6 로스터 (`/rosters`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/rosters` | CUSTOMER_ID + 이름으로 수검자 검색 |
| GET | `/rosters/by-user` | USER_NO로 해당 회원의 수검자 목록 |
| GET | `/rosters/super-roster` | USER_NO(옵션: CUSTOMER_ID)로 본인(00) 수검자 1건 |
| GET | `/rosters/detail` | CHECKUP_ROSTER_NO로 로스터 1건 |

### 5.7 정책 (`/policies`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/policies` | CUSTOMER_ID + policy_year로 HC_CHECKUP_POLICY (예약/검진/가족 기간 등) |

### 5.8 스키마 (`/schema`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/schema/{table_name}` | 화이트리스트 테이블에 대해 `SHOW COLUMNS` 결과 반환 |

---

## 6. 설계 원칙 및 규칙

### 6.1 API 우선 (usage.mdc)

- DB/백엔드가 필요한 답변은 **일회성 터미널 명령 대신 기존 API 호출 후 응답으로 답변**.
- **Workflow:** (1) 기존 엔드포인트로 충족 가능한지 확인 → (2) 불가하면 재사용 가능하게 파라미터화된 API 추가(기존 API 조합 우선) → (3) 선택한 API를 호출하고 **JSON 응답**으로만 답변(추측·생성 금지).
- 새 API는 **기존 API로 조합이 불가할 때만** 추가하고, **재사용 가능한 GET·파라미터 설계** 유지.
- 모든 사용자 요청은 **받자마자** **영문 한 줄**으로 `docs/request-log.md`에 기록(형식: `- YYYY-MM-DD: [설명]`).

### 6.2 Read-only 및 이원화

- DB는 **조회 전용**. INSERT/UPDATE/DELETE 금지.
- “운영/실서비스” 요청 시 `prod=True`(HOPS), 그 외 기본은 EDU.

### 6.3 코드 배치

- `main.py`: 앱 생성·라우터 등록만.
- `db.py`: DB 설정·`get_db_connection()`.
- `routers/<domain>.py`: 도메인별 엔드포인트 (고객·회원·예약·결제·로스터·정책·스키마).

---

## 7. 문서 및 에이전트 가이드

- **docs/request-log.md:** 요청 이력 (기능/API 개선 참고).
- **.cursor/rules/:**  
  - `usage.mdc`: API 우선, 요청 로깅.  
  - `schema-info.mdc`: Read-only, API 설계, 도메인·테이블 개요.  
  - `user-schema.mdc`, `reservation-schema.mdc`, `product-schema.mdc`, `item-schema.mdc`: 도메인별 스키마/코드 설명.
- **tables/*.mdc:** 테이블별 컬럼·코드 값 명세.

---

## 8. 보안 및 운영 고려사항

- **SQL 인젝션:** 파라미터는 %s 바인딩 사용. `schema` 라우터는 테이블명 화이트리스트로 제한.
- **비밀정보:** DB 계정은 `.env`에 두고 저장소에 포함하지 않음.
- **.gitignore:** `node_modules/`, Playwright 관련 경로 등 포함 (Python 가상환경은 미기재되어 있어 추가 권장).

---

## 9. API 수가 많아질 때 선별 비용(토큰) 절감

질문에 맞는 API/조합을 고를 때 검색·읽기로 토큰이 많이 나갈 수 있으므로, 아래처럼 **선별 비용을 줄이는 구조**를 두는 것이 좋다.

| 전략 | 설명 |
|------|------|
| **1. API 인덱스 유지** | `docs/api-index.md`처럼 **경로·한 줄 설명·주요 파라미터**만 모은 짧은 인덱스를 두고, 에이전트가 전체 라우터 코드 대신 이 파일만 먼저 읽어 후보를 좁힌 뒤 필요한 라우터만 열어보게 함. |
| **2. 도메인별 라우터 분리 유지** | 지금처럼 `customers`, `persons`, `reservations` 등 **도메인별 파일**을 유지하면, “고객사/회원/예약 중 뭘 쓰지?”만 정하면 해당 파일만 검색·로드하면 됨. |
| **3. 규칙으로 질문→API 매핑** | `.cursor/rules`에 “회원/통합회원 → `/persons/*`”, “예약 건수/목록 → `/reservations/*`”처럼 **질문 유형→ prefix/태그** 매핑을 적어 두어, 코드 검색 전에 규칙만 보고 후보를 줄임. |
| **4. OpenAPI 요약 제공** | Swagger JSON이 커지면, **에이전트용 요약**(경로 + method + 한 줄 summary + 필수 쿼리만)을 별도 작은 문서나 엔드포인트(`/docs/api-summary`)로 제공해, 전체 스펙을 읽지 않게 함. |
| **5. 자주 쓰는 조합 고정** | “이름+회사로 회원/통합회원”처럼 **자주 나오는 질문 패턴**은 한 번에 답하는 전용 API 하나를 두면, 매번 여러 API 조합을 찾는 비용을 줄일 수 있음. (재사용이 많은 패턴에만 적용.) |

정리하면: **짧은 인덱스 + 도메인 분리 + 규칙 매핑**으로 “어디를 볼지”를 빠르게 좁히고, 필요한 부분만 열어서 토큰을 아끼는 방식이 효과적이다.

---

## 10. 개선 제안

1. **requirements.txt:** `pymysql`, `python-dotenv` 명시.
2. **README.md:** 실제 서비스에 맞게 “Healthcare Checkup API”와 현재 라우터 기준 엔드포인트 표로 정리 (현재는 예제용 `/items` 위주).
3. **테스트:** `test_*.py`가 없음. 라우터별/통합 테스트 추가 시 유지보수성 향상.
4. **.gitignore:** `venv/`, `.env`(이미 보통 제외), `__pycache__/` 등 Python 관련 항목 확인.

---

## 11. 요약

| 항목 | 내용 |
|------|------|
| **목적** | 검진 예약 플랫폼 데이터 조회용 Read-only API |
| **대상** | 에이전트, 외부 서비스, API 클라이언트 |
| **스택** | FastAPI, Uvicorn, PyMySQL, MySQL (EDU/HOPS) |
| **도메인** | 고객사, 회원(법인/통합), 예약, 결제, 로스터, 정책, 스키마 |
| **규칙** | API 우선 응답, 요청 로깅, DB 조회 전용, EDU/PROD 분리 |

이 문서는 프로젝트 루트의 소스·설정·문서를 기준으로 작성되었습니다.
