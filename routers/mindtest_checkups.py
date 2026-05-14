"""Mindtest checkup (HC_MINDTEST_CHECKUP) endpoints."""
import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/mindtest-checkups", tags=["mindtest-checkups"])


@router.get("")
def list_mindtest_checkups(
    year: str = Query(..., min_length=4, max_length=4, description="CHECKUP_DATE year (e.g. 2026)"),
    finished_only: bool = Query(True, description="If True, only rows with CHECKUP_FINISH_DATE present"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    List HC_MINDTEST_CHECKUP rows by checkup year (CHECKUP_DATE starts with year).
    Optionally filters to finished checkups only.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT MINDTEST_CHECKUP_NO, CHECKUP_DIV_CD, CUSTOMER_ID, CUSTOMER_NAME, RCEPT_STATUS_CD,
                           CHECKUP_ROSTER_NO, CHECKUP_DATE, CHECKUP_FINISH_DATE, CHECKUP_REPORT_URL,
                           POLICY_YEAR, USER_NO, DEPART_MENT_CODE
                    FROM HC_MINDTEST_CHECKUP
                    WHERE CHECKUP_DATE LIKE %s
                """
                params = [f"{year}%"]
                if finished_only:
                    sql += " AND CHECKUP_FINISH_DATE IS NOT NULL AND CHECKUP_FINISH_DATE <> ''"
                sql += " ORDER BY CHECKUP_DATE, MINDTEST_CHECKUP_NO"
                cur.execute(sql, params)
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "year": year,
                    "finished_only": finished_only,
                    "count": len(rows),
                    "rows": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/dept-temp-mismatch")
def list_dept_temp_mismatch(
    policy_year: str = Query("2026", min_length=4, max_length=4, description="HM.POLICY_YEAR (e.g. 2026)"),
    rcept_status_cd: str = Query("03", min_length=2, max_length=2, description="HM.RCEPT_STATUS_CD (e.g. 03)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Execute the provided query (read-only) and return rows for CSV export.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT HM.MINDTEST_CHECKUP_NO AS '마음검진번호',
                           HR.CHECKUP_ROSTER_NO AS '검진대상자 번호',
                           hdt.NAME AS 'TEMP 부서명',
                           HR.DEPARTMENT AS '대상자 부서명',
                           HM.DEPART_MENT_CODE AS '풀코드',
                           HR.CUSTOMER_ID AS '고객사코드',
                           CONCAT('0101', hdt.CODE) AS '바꿔야할 풀코드'
                    FROM HC_MINDTEST_CHECKUP HM
                             JOIN HC_CHECKUP_ROSTER HR ON HR.CHECKUP_ROSTER_NO = HM.CHECKUP_ROSTER_NO
                             LEFT JOIN HC_DEPARTMENT_TEMP hdt ON hdt.CUSTOMER_ID = HR.CUSTOMER_ID
                        AND hdt.CATEGORY = 2
                        AND hdt.NAME = IFNULL(NULLIF(HR.DEPARTMENT, ''), '부서없음')
                    WHERE HM.RCEPT_STATUS_CD = %s
                      AND HM.POLICY_YEAR = %s
                      AND hdt.CODE != '01'
                    """,
                    (rcept_status_cd.strip(), policy_year.strip()),
                )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "policy_year": policy_year,
                    "rcept_status_cd": rcept_status_cd,
                    "count": len(rows),
                    "rows": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
