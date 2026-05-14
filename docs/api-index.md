# API 인덱스 (에이전트용)

질문에 맞는 API를 빠르게 찾기 위한 **경로·한 줄 설명·주요 파라미터**만 정리한 인덱스.  
API가 늘어나면 이 파일만 갱신해 두면, 전체 라우터 코드를 읽지 않고 후보를 좁힐 수 있음.

- 모든 DB 조회 API: `prod` (bool, 기본 false) 로 EDU/운영 선택.

---

## 플레이북 (유사 인입·원인 규명)

| 문서 | 용도 |
|------|------|
| [playbook-roster-auto-create-latest-policy.md](./playbook-roster-auto-create-latest-policy.md) | 회사지원 로스터가 있는데 `최신정책대상자` 로스터가 추가로 생긴 경우 — 정책 기간 vs 자동 생성 규명 절차 |

---

## customers

| Method | Path | 설명 | 주요 params |
|--------|------|------|-------------|
| GET | `/customers` | 고객사명 부분 일치 검색 | `name`, `prod` |
| GET | `/customers/detail` | CUSTOMER_ID로 고객사 상세 | `customer_id`, `prod` |

---

## persons (회원·통합회원)

| Method | Path | 설명 | 주요 params |
|--------|------|------|-------------|
| GET | `/persons/unified-member` | 이름+회사로 통합회원 여부·법인/통합 회원 정보 | `name`, `company`, `prod` |
| GET | `/persons/unified-by-id` | 통합 로그인 ID로 통합회원 + 연결 법인회원 | `user_id`, `prod` |
| GET | `/persons/unified-accounts-by-corporate` | 법인회원 USER_NO로 연결된 통합회원 목록 | `user_no`, `prod` |
| GET | `/persons/unified-by-name` | 통합회원 이름 검색 (활성만) | `name`, `prod` |
| GET | `/persons/corporate-by-employ-no` | CUSTOMER_ID + 사번으로 법인회원 | `customer_id`, `employ_no`, `prod` |
| GET | `/persons/by-user-no` | USER_NO로 법인회원 1건 | `user_no`, `prod` |

---

## reservations (예약)

| Method | Path | 설명 | 주요 params |
|--------|------|------|-------------|
| GET | `/reservations/count` | 예약 건수 (일자·고객사·상태 필터) | `reg_dt`, `company`, `reserv_st`, `prod` |
| GET | `/reservations/by-person` | 법인회원(USER_NO+CUSTOMER_ID)별 예약 목록 | `user_no`, `customer_id`, `policy_year`, `prod` |
| GET | `/reservations/test-items` | RESERV_NO별 검사 항목 | `reserv_no`, `prod` |
| GET | `/reservations/detail` | RESERV_NO로 예약 상세(금액 등) | `reserv_no`, `prod` |

---

## payments (결제)

| Method | Path | 설명 | 주요 params |
|--------|------|------|-------------|
| GET | `/payments/by-reservation` | RESERV_NO별 결제 목록·결제완료 여부 | `reserv_no`, `prod` |

---

## rosters (수검자)

| Method | Path | 설명 | 주요 params |
|--------|------|------|-------------|
| GET | `/rosters` | CUSTOMER_ID + 이름으로 수검자 검색 | `customer_id`, `name`, `prod`, `active_only` |
| GET | `/rosters/by-user` | USER_NO로 해당 회원의 수검자 목록 | `user_no`, `prod`, `active_only` |
| GET | `/rosters/super-roster` | USER_NO(옵션: CUSTOMER_ID)로 본인 수검자 1건 | `user_no`, `customer_id`, `prod` |
| GET | `/rosters/detail` | CHECKUP_ROSTER_NO로 로스터 1건 | `checkup_roster_no`, `prod` |

---

## policies (검진 정책)

| Method | Path | 설명 | 주요 params |
|--------|------|------|-------------|
| GET | `/policies` | CUSTOMER_ID + 연도로 검진 정책(기간 등) | `customer_id`, `policy_year`, `prod` |

---

## test-items (검사 항목 코드)

| Method | Path | 설명 | 주요 params |
|--------|------|------|-------------|
| GET | `/test-items/by-code` | TEST_ITEM_CD로 검사 항목명·센터별 정보 | `test_item_cd`, `prod` |

---

## schema (테이블 스키마)

| Method | Path | 설명 | 주요 params |
|--------|------|------|-------------|
| GET | `/schema/{table_name}` | 테이블 컬럼 정보 (화이트리스트) | `table_name`, `prod` |

---

## 질문 유형 → 추천 prefix

- 고객사 찾기/상세 → `customers`
- 회원·통합회원·사번·USER_NO → `persons`
- 예약 건수/목록/검사항목/상세 → `reservations`
- 결제 여부/목록 → `payments`
- 수검자(로스터) 검색/목록/본인 로스터 → `rosters`
- 검진 정책·기간 → `policies`
- 검사 항목 코드(TEST_ITEM_CD) 조회 → `test-items`
- 테이블 컬럼 확인 → `schema`
