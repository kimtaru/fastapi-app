# 플레이북: 회사지원 로스터가 있는데 `최신정책대상자` 로스터가 추가로 생긴 경우

동일·유사 인입 시 **원인 규명**을 빠르게 하기 위한 기록입니다. (참고 사례: 부쉐론 `C000001911`, 로스터 `9239758` vs `9352774`·`9353064`, 기준일 2026-03-23)

---

## 1. 현상(증상)

- 동일 인원(`USER_NO` 동일)·동일 고객사·동일 `POLICY_YEAR`에 **로스터가 여러 건** 존재한다.
- **회사지원 대상**으로 보이는 로스터(예: `COMPANY_SUPPORT_TYPE` 10, 회사지원금 있음, 사번 있음)가 이미 있는데,
- **추가 로스터**가 생겼다가 곧 **`CHECKUP_ROSTER_ST = 90`** 등으로 정리되었거나, 비고에 **`최신정책대상자`**가 붙어 있다.
- 추가 건은 `REG_ADMIN_ID`가 비어 있고 `ROSTER_BATCH_YN = N`인 경우가 많다. (시스템/자동 생성 패턴)

---

## 2. 원인 가설(업무 로직)

1. **회사지원(지원타입 10) 예약·수검 기간**(`HC_CHECKUP_POLICY`의 `RESERV_*`, `CHECKUP_*`)이 **아직 시작 전**이거나, 해당 일자가 그 구간에 속하지 않는다.
2. 그 시점에는 **회사지원 로스터**가 일부 **조회·매칭 경로**에 잡히지 않거나 사용되지 않는다.
3. 반면 **가족/개인 구간**(`FAMILY_CHECKUP_*`)은 이미 열려 있어, **개인수납(또는 동 구간용) 대상**으로 시스템이 **별도 로스터를 자동 생성**한다.
4. 그 결과가 **`ETC_CHECKUP_TEXT = 최신정책대상자`** 등으로 남는 **중복 후보 로스터**다.
5. 운영에서 중복·불필요로 판단되면 **관리자 계정으로 상태 90** 등으로 정리할 수 있다.

**한 줄:**  
*“회사지원 기간 밖인 날, 회사지원 로스터는 그 흐름에 안 쓰이고 → 최신 정책(개인/가족 구간)용 자동 로스터가 생긴다.”*

---

## 3. 규명 절차 (API·데이터 확인)

아래는 **읽기 전용**으로 이 프로젝트 FastAPI를 쓰는 경우의 순서이다.

### 3.1 정책 일정 확인 (필수)

- `GET /policies/years-by-customer?customer_id={CUSTOMER_ID}&prod=true`  
  → 최신 `POLICY_YEAR` 확인.
- `GET /policies?customer_id={CUSTOMER_ID}&policy_year={연도}&prod=true`  
  → 아래 컬럼과 **문의 기준일(당일 문자열 `yyyyMMdd`)**을 비교한다.

| 컬럼 | 의미(요약) |
|------|------------|
| `RESERV_START_DT` ~ `RESERV_END_DT` | `COMPANY_SUPPORT_TYPE` **10**(회사지원) 수검자 해당 구간 |
| `CHECKUP_START_DT` ~ `CHECKUP_END_DT` | 검진 실시 기간(본 정책에서는 보통 회사지원 구간과 동일한 경우 많음) |
| `FAMILY_CHECKUP_START_DT` ~ `FAMILY_CHECKUP_END_DT` | 명세상 `COMPANY_SUPPORT_TYPE` **00** 등 가족/개인 쪽 구간 |

**판단:**  
문의일이 `FAMILY_CHECKUP_*` 안에 있고, `RESERV_*`(회사지원) 안에는 **아직** 없다 → 본 플레이북과 **동일 계열** 가능성이 높다.

### 3.2 로스터끼리 비교

- `GET /rosters/detail?checkup_roster_no={본건}&prod=true`  
- `GET /rosters/compare-with-history?checkup_roster_no={의심 건}&prod=true`  
  → `REG_DT`, `REG_ADMIN_ID`, `CHANGE_ADMIN_ID`, `ROSTER_BATCH_YN`, `EMPLOY_NO`, `COMPANY_SUPPORT_AMOUNT`, `ETC_CHECKUP_TEXT`, `USER_NO`, `CHECKUP_ROSTER_ST` 비교.

**본건(회사지원) 쪽에 가깝다:** 사번·지원금·`ROSTER_BATCH_YN=Y`·`REG_ADMIN_ID` 있음 등.  
**자동 생성 쪽에 가깝다:** `최신정책대상자`, `REG_ADMIN_ID` 공란, `ROSTER_BATCH_YN=N`, 지원금 0, 이후 90 처리 등.

### 3.3 매핑·통합회원 (부가)

- `USER_NO` 존재 여부: `GET /rosters/detail`
- 통합 연결: `GET /persons/unified-accounts-by-corporate?user_no={USER_NO}&prod=true`

---

## 4. 참고 스키마

- `tables/hc-checkup-policy.mdc` — `RESERV_*`, `FAMILY_CHECKUP_*`와 `COMPANY_SUPPORT_TYPE` 설명
- `.cursor/rules/product-schema.mdc` — 정책 기간과 수검자 지원타입 매핑 요약

---

## 5. 인입 시 체크리스트

- [ ] 고객사 `CUSTOMER_ID`, 문의 **기준일**
- [ ] 해당 연도 `GET /policies`로 회사지원 vs 가족/개인 구간에 기준일이 어디에 걸리는지
- [ ] 의심 로스터 vs 기존 로스터: `USER_NO` 동일 여부, `ETC_CHECKUP_TEXT`, 등록·변경 관리자, 상태(90) 여부
- [ ] 필요 시 이력: `GET /rosters/compare-with-history`의 `hist_rows`·`comparison`

이 항목을 채우면 **“기간 불일치로 인한 자동 생성 후 정리”** 여부를 근거 있게 설명할 수 있다.
