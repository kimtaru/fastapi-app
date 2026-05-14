"""Roster (HC_CHECKUP_ROSTER) endpoints. Search examinees by customer and name."""
from typing import Optional

import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/rosters", tags=["rosters"])


@router.get("")
def search_rosters(
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000015950)"),
    name: str = Query(..., description="ROSTER_NAME partial match (e.g. 강경화)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
    active_only: bool = Query(True, description="If True, only CHECKUP_ROSTER_ST = '00'"),
):
    """
    Search HC_CHECKUP_ROSTER (수검자) by customer and name. Does not require HC_USER (pre-registered examinees included).
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT CHECKUP_ROSTER_NO, CUSTOMER_ID, ROSTER_NAME, USER_NO, BIRTHDAY,
                           MOBILE_NO, EMPLOY_NO, COMPANY_SUPPORT_AMOUNT, CHECKUP_ROSTER_ST, POLICY_YEAR,
                           EMPLOY_RELATION_TYPE, SUPER_CHECKUP_ROSTER_NO, ETC_CHECKUP_TEXT, REG_DT
                    FROM HC_CHECKUP_ROSTER
                    WHERE CUSTOMER_ID = %s AND ROSTER_NAME LIKE %s
                """
                params = [customer_id.strip(), f"%{name.strip()}%"]
                if active_only:
                    sql += " AND CHECKUP_ROSTER_ST = '00'"
                sql += " ORDER BY ROSTER_NAME"
                cur.execute(sql, params)
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "customer_id": customer_id,
                    "name": name.strip(),
                    "count": len(rows),
                    "rosters": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/by-employ-no-suffix")
def search_rosters_by_employ_no_suffix(
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000002136)"),
    employ_no_suffix: str = Query(
        ...,
        min_length=1,
        max_length=30,
        description="EMPLOY_NO suffix match (e.g. 4090 matches ...4090)",
    ),
    policy_year: Optional[str] = Query(
        None,
        min_length=4,
        max_length=4,
        description="Optional POLICY_YEAR (e.g. 2026)",
    ),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
    active_only: bool = Query(True, description="If True, only CHECKUP_ROSTER_ST = '00'"),
):
    """Search HC_CHECKUP_ROSTER by CUSTOMER_ID and EMPLOY_NO ending with the given suffix."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT CHECKUP_ROSTER_NO, CUSTOMER_ID, ROSTER_NAME, USER_NO, BIRTHDAY,
                           MOBILE_NO, EMPLOY_NO, COMPANY_SUPPORT_AMOUNT, CHECKUP_ROSTER_ST, POLICY_YEAR,
                           EMPLOY_RELATION_TYPE, SUPER_CHECKUP_ROSTER_NO, ETC_CHECKUP_TEXT, REG_DT
                    FROM HC_CHECKUP_ROSTER
                    WHERE CUSTOMER_ID = %s AND EMPLOY_NO LIKE CONCAT('%%', %s)
                """
                params: list = [customer_id.strip(), employ_no_suffix.strip()]
                if policy_year is not None and policy_year.strip():
                    sql += " AND POLICY_YEAR = %s"
                    params.append(policy_year.strip())
                if active_only:
                    sql += " AND CHECKUP_ROSTER_ST = '00'"
                sql += " ORDER BY EMPLOY_NO, ROSTER_NAME, CHECKUP_ROSTER_NO"
                cur.execute(sql, params)
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "customer_id": customer_id.strip(),
                    "employ_no_suffix": employ_no_suffix.strip(),
                    "policy_year": policy_year.strip() if policy_year else None,
                    "active_only": active_only,
                    "count": len(rows),
                    "rosters": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/by-etc-text")
def search_rosters_by_etc_text(
    customer_id: str = Query(..., description="CUSTOMER_ID"),
    etc_text: str = Query(..., description="ETC_CHECKUP_TEXT exact match"),
    policy_year: Optional[str] = Query(None, min_length=4, max_length=4, description="Optional POLICY_YEAR filter"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
    active_only: Optional[bool] = Query(
        None,
        description="If True/False, filter CHECKUP_ROSTER_ST; if omitted, include all",
    ),
):
    """List HC_CHECKUP_ROSTER rows by CUSTOMER_ID and exact ETC_CHECKUP_TEXT."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT CHECKUP_ROSTER_NO, CUSTOMER_ID, ROSTER_NAME, USER_NO, BIRTHDAY,
                           MOBILE_NO, EMPLOY_NO, COMPANY_SUPPORT_AMOUNT, CHECKUP_ROSTER_ST, POLICY_YEAR,
                           EMPLOY_RELATION_TYPE, SUPER_CHECKUP_ROSTER_NO, ETC_CHECKUP_TEXT, REG_DT
                    FROM HC_CHECKUP_ROSTER
                    WHERE CUSTOMER_ID = %s AND ETC_CHECKUP_TEXT = %s
                """
                params: list = [customer_id.strip(), etc_text.strip()]
                if policy_year is not None and policy_year.strip():
                    sql += " AND POLICY_YEAR = %s"
                    params.append(policy_year.strip())
                if active_only is True:
                    sql += " AND CHECKUP_ROSTER_ST = '00'"
                elif active_only is False:
                    sql += " AND CHECKUP_ROSTER_ST <> '00'"
                sql += " ORDER BY REG_DT, CHECKUP_ROSTER_NO"
                cur.execute(sql, params)
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "customer_id": customer_id.strip(),
                    "etc_text": etc_text.strip(),
                    "policy_year": policy_year.strip() if policy_year else None,
                    "active_only": active_only,
                    "count": len(rows),
                    "rosters": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/by-user")
def list_rosters_by_user_no(
    user_no: int = Query(..., description="HC_USER.USER_NO (mapped examinees)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
    active_only: bool = Query(True, description="If True, only CHECKUP_ROSTER_ST = '00'"),
):
    """
    List HC_CHECKUP_ROSTER (수검자) where USER_NO = user_no.
    Use to find all examinee rows mapped to a given corporate member.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT CHECKUP_ROSTER_NO, CUSTOMER_ID, ROSTER_NAME, USER_NO, BIRTHDAY,
                           MOBILE_NO, EMPLOY_NO, COMPANY_SUPPORT_AMOUNT, CHECKUP_ROSTER_ST, POLICY_YEAR,
                           EMPLOY_RELATION_TYPE, SUPER_CHECKUP_ROSTER_NO, ETC_CHECKUP_TEXT, REG_DT
                    FROM HC_CHECKUP_ROSTER
                    WHERE USER_NO = %s
                """
                params = [user_no]
                if active_only:
                    sql += " AND CHECKUP_ROSTER_ST = '00'"
                sql += " ORDER BY CUSTOMER_ID, ROSTER_NAME"
                cur.execute(sql, params)
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "user_no": user_no,
                    "count": len(rows),
                    "rosters": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/super-roster")
def get_super_roster(
    user_no: int = Query(..., description="HC_USER.USER_NO"),
    customer_id: Optional[str] = Query(None, description="CUSTOMER_ID (optional, scope to one company)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Return the super roster for a corporate member (USER_NO).
    Criteria: self (00) + SUPER_CHECKUP_ROSTER_NO 0 or null; if multiple, lowest by CHECKUP_DIV_CD, ROSTER_MGMT_TYPE, CHECKUP_ROSTER_NO.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT CHECKUP_ROSTER_NO, CUSTOMER_ID, ROSTER_NAME, USER_NO, BIRTHDAY,
                           MOBILE_NO, EMPLOY_NO, CHECKUP_ROSTER_ST, POLICY_YEAR,
                           EMPLOY_RELATION_TYPE, SUPER_CHECKUP_ROSTER_NO, CHECKUP_DIV_CD, ROSTER_MGMT_TYPE,
                           ETC_CHECKUP_TEXT
                    FROM HC_CHECKUP_ROSTER
                    WHERE USER_NO = %s
                      AND EMPLOY_RELATION_TYPE = '00'
                      AND (SUPER_CHECKUP_ROSTER_NO = 0 OR SUPER_CHECKUP_ROSTER_NO IS NULL)
                      AND CHECKUP_ROSTER_ST = '00'
                """
                params = [user_no]
                if customer_id and customer_id.strip():
                    sql += " AND CUSTOMER_ID = %s"
                    params.append(customer_id.strip())
                sql += " ORDER BY CHECKUP_DIV_CD, ROSTER_MGMT_TYPE, CHECKUP_ROSTER_NO LIMIT 1"
                cur.execute(sql, params)
                row = cur.fetchone()
                if not row:
                    return {
                        "prod": prod,
                        "user_no": user_no,
                        "customer_id": customer_id,
                        "found": False,
                        "message": "No super roster found for this user (no self roster with SUPER_CHECKUP_ROSTER_NO 0/null).",
                    }
                return {"prod": prod, "user_no": user_no, "found": True, "super_roster": dict(row)}
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/by-principal")
def list_family_rosters_by_principal(
    super_checkup_roster_no: int = Query(..., description="본인(principal) 로스터 번호. 이 번호를 SUPER_CHECKUP_ROSTER_NO로 참조하는 가족 로스터 목록"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
    active_only: bool = Query(False, description="True면 CHECKUP_ROSTER_ST = '00'만"),
):
    """List HC_CHECKUP_ROSTER rows where SUPER_CHECKUP_ROSTER_NO = super_checkup_roster_no (가족 수검자)."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT CHECKUP_ROSTER_NO, CUSTOMER_ID, ROSTER_NAME, USER_NO, BIRTHDAY,
                           MOBILE_NO, EMPLOY_NO, COMPANY_SUPPORT_AMOUNT, CHECKUP_ROSTER_ST, POLICY_YEAR,
                           EMPLOY_RELATION_TYPE, SUPER_CHECKUP_ROSTER_NO, ETC_CHECKUP_TEXT, REG_DT
                    FROM HC_CHECKUP_ROSTER
                    WHERE SUPER_CHECKUP_ROSTER_NO = %s
                """
                params = [super_checkup_roster_no]
                if active_only:
                    sql += " AND CHECKUP_ROSTER_ST = '00'"
                sql += " ORDER BY CHECKUP_ROSTER_NO"
                cur.execute(sql, params)
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "super_checkup_roster_no": super_checkup_roster_no,
                    "count": len(rows),
                    "family_rosters": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/detail")
def get_roster_detail(
    checkup_roster_no: int = Query(..., description="HC_CHECKUP_ROSTER.CHECKUP_ROSTER_NO"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """Get one HC_CHECKUP_ROSTER row by CHECKUP_ROSTER_NO (for principal lookup via SUPER_CHECKUP_ROSTER_NO)."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT CHECKUP_ROSTER_NO, CUSTOMER_ID, ROSTER_NAME, USER_NO, BIRTHDAY,
                           MOBILE_NO, EMPLOY_NO, EMPLOY_RELATION_TYPE, SUPER_CHECKUP_ROSTER_NO,
                           POLICY_YEAR, CHECKUP_DIV_CD, CHECKUP_ROSTER_ST,
                           COMPANY_SUPPORT_TYPE, COMPANY_SUPPORT_AMOUNT, COMPANY_SUPPORT_FAMILY_COUNT,
                           ETC_CHECKUP_TEXT, LAST_PATH, PERSONAL_PAYER_BILLING_YN, REG_DT
                    FROM HC_CHECKUP_ROSTER
                    WHERE CHECKUP_ROSTER_NO = %s
                    """,
                    (checkup_roster_no,),
                )
                row = cur.fetchone()
                if not row:
                    return {"prod": prod, "checkup_roster_no": checkup_roster_no, "found": False}
                return {"prod": prod, "found": True, "roster": dict(row)}
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


def _serialize(val):
    """Convert DB value to JSON-serializable (e.g. datetime, decimal)."""
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if hasattr(val, "__float__") and type(val).__name__ in ("Decimal",):
        return float(val)
    return val


@router.get("/compare-with-history")
def compare_roster_with_history(
    checkup_roster_no: int = Query(..., description="HC_CHECKUP_ROSTER.CHECKUP_ROSTER_NO (수검자 번호)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    수검자 번호로 HC_CHECKUP_ROSTER 1건, HC_CHECKUP_ROSTER_HIST 전체 조회 후
    공통 컬럼 기준으로 로우 간 차이점 비교하여 반환.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM HC_CHECKUP_ROSTER WHERE CHECKUP_ROSTER_NO = %s",
                    (checkup_roster_no,),
                )
                roster_row = cur.fetchone()
                if not roster_row:
                    return {
                        "prod": prod,
                        "checkup_roster_no": checkup_roster_no,
                        "roster_found": False,
                        "message": "No HC_CHECKUP_ROSTER row for this CHECKUP_ROSTER_NO.",
                    }
                roster = {k: _serialize(v) for k, v in roster_row.items()}

                cur.execute(
                    "SELECT * FROM HC_CHECKUP_ROSTER_HIST WHERE CHECKUP_ROSTER_NO = %s ORDER BY CHECKUP_ROSTER_NO",
                    (checkup_roster_no,),
                )
                hist_rows = cur.fetchall()
                hist_list = [{k: _serialize(v) for k, v in row.items()} for row in hist_rows]

                common_keys = set(roster.keys()) & (set(hist_list[0].keys()) if hist_list else set())

                differences = []
                for i, h in enumerate(hist_list):
                    diff = {}
                    for col in common_keys:
                        rv = roster.get(col)
                        hv = h.get(col)
                        if rv != hv:
                            diff[col] = {"roster": rv, "hist_row": hv, "hist_index": i}
                    differences.append({"hist_row_index": i, "hist_row": h, "differences": diff})

                return {
                    "prod": prod,
                    "checkup_roster_no": checkup_roster_no,
                    "roster_found": True,
                    "roster": roster,
                    "hist_count": len(hist_list),
                    "hist_rows": hist_list,
                    "comparison": differences,
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
