"""Reservation (HC_RESERV) endpoints. Reusable for count/list by reg_dt and env (EDU/prod)."""
from datetime import date
from typing import List, Optional

import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _parse_reserv_st(reserv_st: Optional[str]) -> Optional[List[str]]:
    """쉼표 구분 RESERV_ST 코드 리스트. 공백 제거."""
    if not reserv_st or not reserv_st.strip():
        return None
    return [s.strip() for s in reserv_st.strip().split(",") if s.strip()]


@router.get("/count")
def count_reservations(
    reg_dt: Optional[str] = Query(None, description="등록일자 YYYYMMDD (미입력 시 오늘, 비우려면 공백)"),
    reg_year: Optional[str] = Query(None, description="등록연도 YYYY (예: 2026). 지정 시 해당 연도 등록분만. reg_dt보다 우선"),
    company: Optional[str] = Query(None, description="고객사명 부분 일치 (예: LG이노텍). 미입력 시 전체"),
    reserv_st: Optional[str] = Query(
        None,
        description="예약상태 코드 쉼표 구분 (예: 10,50,51,56,60 = 신청/확정/변경대기/예약변경/변경완료)",
    ),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    예약 건수 조회. reg_dt 미입력 시 오늘(YYYYMMDD) 기준. reg_year 지정 시 해당 연도(RESERV_REG_DT LIKE 'YYYY%')만.
    company 입력 시 HC_CHECKUP_ROSTER·HC_CUSTOMER 조인하여 해당 고객사만.
    reserv_st 입력 시 해당 상태만 (예: 10,50,51,56,60).
    """
    dt = (reg_dt or "").strip()
    if dt and (len(dt) != 8 or not dt.isdigit()):
        raise HTTPException(status_code=400, detail="reg_dt must be YYYYMMDD")
    if not dt:
        dt = None
    year = (reg_year or "").strip()
    if year and (len(year) != 4 or not year.isdigit()):
        raise HTTPException(status_code=400, detail="reg_year must be YYYY")
    if not year:
        year = None
    # 등록일 조건: reg_year 우선, 없으면 reg_dt, 없으면 전체
    date_prefix: Optional[str] = None
    if year:
        date_prefix = f"{year}%"
    elif dt:
        date_prefix = f"{dt}%"
    st_list = _parse_reserv_st(reserv_st)
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                if company and company.strip():
                    sql = """
                        SELECT COUNT(*) AS cnt
                        FROM HC_RESERV R
                        INNER JOIN HC_CHECKUP_ROSTER CR ON R.CHECKUP_ROSTER_NO = CR.CHECKUP_ROSTER_NO
                        INNER JOIN HC_CUSTOMER C ON CR.CUSTOMER_ID = C.CUSTOMER_ID
                        WHERE 1=1
                    """
                    params: list = []
                    if date_prefix:
                        sql += " AND R.RESERV_REG_DT LIKE %s"
                        params.append(date_prefix)
                    sql += " AND C.CUSTOMER_NAME LIKE %s"
                    params.append(f"%{company.strip()}%")
                    if st_list:
                        sql += " AND R.RESERV_ST IN (" + ",".join(["%s"] * len(st_list)) + ")"
                        params.extend(st_list)
                    cur.execute(sql, params)
                else:
                    sql = "SELECT COUNT(*) AS cnt FROM HC_RESERV R WHERE 1=1"
                    params = []
                    if date_prefix:
                        sql += " AND R.RESERV_REG_DT LIKE %s"
                        params.append(date_prefix)
                    if st_list:
                        sql += " AND R.RESERV_ST IN (" + ",".join(["%s"] * len(st_list)) + ")"
                        params.extend(st_list)
                    cur.execute(sql, params)
                row = cur.fetchone()
                return {
                    "prod": prod,
                    "reg_dt": dt or None,
                    "reg_year": year or None,
                    "company": company.strip() if company and company.strip() else None,
                    "reserv_st": st_list,
                    "count": row["cnt"],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/by-person")
def list_reservations_by_person(
    user_no: int = Query(..., description="HC_USER.USER_NO (e.g. 37640)"),
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000015950)"),
    policy_year: Optional[str] = Query(None, description="Policy year (e.g. 2026). If set, only reservations within that policy's company-supported period."),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    List reservations for a corporate member (USER_NO + CUSTOMER_ID).
    Optionally filter by policy_year: uses HC_CHECKUP_POLICY RESERV_START_DT~RESERV_END_DT for that customer/year.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                # Roster(s) for this user at this customer
                cur.execute(
                    """
                    SELECT CHECKUP_ROSTER_NO FROM HC_CHECKUP_ROSTER
                    WHERE USER_NO = %s AND CUSTOMER_ID = %s AND CHECKUP_ROSTER_ST = '00'
                    """,
                    (user_no, customer_id.strip()),
                )
                rosters = cur.fetchall()
                if not rosters:
                    return {
                        "prod": prod,
                        "user_no": user_no,
                        "customer_id": customer_id,
                        "policy_year": policy_year,
                        "found": False,
                        "message": "No active roster for this user at this customer.",
                        "reservations": [],
                    }
                roster_nos = [r["CHECKUP_ROSTER_NO"] for r in rosters]
                placeholders = ",".join(["%s"] * len(roster_nos))

                if policy_year:
                    cur.execute(
                        """
                        SELECT RESERV_START_DT, RESERV_END_DT FROM HC_CHECKUP_POLICY
                        WHERE CUSTOMER_ID = %s AND POLICY_YEAR = %s
                        """,
                        (customer_id.strip(), policy_year.strip()),
                    )
                    policy_row = cur.fetchone()
                    if not policy_row:
                        return {
                            "prod": prod,
                            "user_no": user_no,
                            "customer_id": customer_id,
                            "policy_year": policy_year,
                            "found": False,
                            "message": f"No policy for customer {customer_id} year {policy_year}.",
                            "reservations": [],
                        }
                    start_dt = policy_row["RESERV_START_DT"]
                    end_dt = policy_row["RESERV_END_DT"]
                    sql = f"""
                        SELECT R.RESERV_NO, R.CHECKUP_ROSTER_NO, R.RESERV_REG_DT, R.RESERV_DAY, R.RESERV_ST
                        FROM HC_RESERV R
                        WHERE R.CHECKUP_ROSTER_NO IN ({placeholders})
                          AND R.RESERV_REG_DT >= %s AND R.RESERV_REG_DT <= %s
                        ORDER BY R.RESERV_REG_DT DESC
                    """
                    cur.execute(sql, (*roster_nos, start_dt, end_dt))
                else:
                    cur.execute(
                        f"""
                        SELECT R.RESERV_NO, R.CHECKUP_ROSTER_NO, R.RESERV_REG_DT, R.RESERV_DAY, R.RESERV_ST
                        FROM HC_RESERV R
                        WHERE R.CHECKUP_ROSTER_NO IN ({placeholders})
                        ORDER BY R.RESERV_REG_DT DESC
                        """,
                        tuple(roster_nos),
                    )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "user_no": user_no,
                    "customer_id": customer_id,
                    "policy_year": policy_year,
                    "found": True,
                    "count": len(rows),
                    "reservations": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/test-items")
def list_reserv_test_items(
    reserv_no: int = Query(..., description="HC_RESERV.RESERV_NO"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    List HC_RESERV_TEST_ITEM for a reservation. Joins HC_CHECKUP_ITEM_CD to return ITEM_NAME.
    CHOICE_GROUP_NO: 0=기본, 1~5=선택(A~E), 9=추가검사 (see item-schema.mdc).
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT RT.RESERV_NO, RT.TEST_ITEM_CD, RT.CHECKUP_ITEM_CD, RT.CHOICE_GROUP_NO,
                           RT.ADD_CHECKUP_YN, RT.SELF_PAY_AMOUNT, RT.ONPAY_AMOUNT,
                           C.ITEM_NAME
                    FROM HC_RESERV_TEST_ITEM RT
                    LEFT JOIN HC_CHECKUP_ITEM_CD C ON RT.CHECKUP_ITEM_CD = C.CHECKUP_ITEM_CD
                    WHERE RT.RESERV_NO = %s
                    ORDER BY RT.CHOICE_GROUP_NO, RT.TEST_ITEM_CD
                    """,
                    (reserv_no,),
                )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "reserv_no": reserv_no,
                    "count": len(rows),
                    "test_items": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/by-roster")
def list_reservations_by_roster(
    checkup_roster_no: int = Query(..., description="HC_CHECKUP_ROSTER.CHECKUP_ROSTER_NO"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    List HC_RESERV for a single roster (CHECKUP_ROSTER_NO). Use when the person has no USER_NO (e.g. pre-registered only).
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT R.RESERV_NO, R.CHECKUP_ROSTER_NO, R.RESERV_REG_DT, R.RESERV_DAY, R.RESERV_ST
                    FROM HC_RESERV R
                    WHERE R.CHECKUP_ROSTER_NO = %s
                    ORDER BY R.RESERV_REG_DT DESC
                    """,
                    (checkup_roster_no,),
                )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "checkup_roster_no": checkup_roster_no,
                    "count": len(rows),
                    "reservations": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/full-row")
def get_reservation_full_row(
    reserv_no: int = Query(..., description="HC_RESERV.RESERV_NO"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Get one HC_RESERV row with all columns (full row). Use for debugging or when every field is needed.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM HC_RESERV WHERE RESERV_NO = %s", (reserv_no,))
                row = cur.fetchone()
                if not row:
                    return {"prod": prod, "reserv_no": reserv_no, "found": False}
                return {"prod": prod, "found": True, "reservation": dict(row)}
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/detail")
def get_reservation_detail(
    reserv_no: int = Query(..., description="HC_RESERV.RESERV_NO"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Get one reservation row with amount fields. Joins HC_CHECKUP_ROSTER for roster COMPANY_SUPPORT_AMOUNT.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT R.RESERV_NO, R.CHECKUP_ROSTER_NO, R.CHECKUP_PRODUCT_NO, R.RESERV_DAY, R.RESERV_ST,
                           R.COMPANY_SUPPORT_AMOUNT, R.SELF_PAY_AMOUNT, R.SYSTEM_USAGE_FEE,
                           R.CUSTOM_AMOUNT_YN, R.CUSTOM_TOTAL_AMOUNT, R.CUSTOM_COMPANY_AMOUNT, R.CUSTOM_SELF_AMOUNT,
                           R.ONPAY_AMOUNT, R.RESERV_REG_DT, R.LAST_PATH, R.LAST_MODIFIER,
                           CR.COMPANY_SUPPORT_AMOUNT AS ROSTER_COMPANY_SUPPORT_AMOUNT,
                           P.CHECKUP_PRODUCT_TITLE, P.PARTNER_CENTER_ID
                    FROM HC_RESERV R
                    LEFT JOIN HC_CHECKUP_ROSTER CR ON R.CHECKUP_ROSTER_NO = CR.CHECKUP_ROSTER_NO
                    LEFT JOIN HC_CHECKUP_PRODUCT P ON R.CHECKUP_PRODUCT_NO = P.CHECKUP_PRODUCT_NO
                    WHERE R.RESERV_NO = %s
                    """,
                    (reserv_no,),
                )
                row = cur.fetchone()
                if not row:
                    return {"prod": prod, "reserv_no": reserv_no, "found": False}
                return {"prod": prod, "found": True, "reservation": dict(row)}
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
