"""Customer (HC_CUSTOMER) endpoints. Reusable for lookup by company name and env (EDU/prod)."""
from typing import Optional

import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
def search_customers(
    name: str = Query(..., description="Company name or partial match (e.g. LG이노텍)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Search HC_CUSTOMER by company name (CUSTOMER_NAME LIKE %name%).
    Returns CUSTOMER_ID and CUSTOMER_NAME for reuse by Agent, other services, or API clients.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT CUSTOMER_ID, CUSTOMER_NAME FROM HC_CUSTOMER WHERE CUSTOMER_NAME LIKE %s ORDER BY CUSTOMER_NAME",
                    (f"%{name.strip()}%",),
                )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "query": name.strip(),
                    "count": len(rows),
                    "customers": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


PAGE_SIZE = 20


@router.get("/list")
def list_customers_by_name(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터)"),
    name: Optional[str] = Query(None, description="CUSTOMER_NAME 부분 일치. 미입력 시 전체"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    CUSTOMER_NAME 기준으로 HC_CUSTOMER 목록 반환. 페이지네이션: page(1부터), 20개씩.
    name 미입력 시 전체, 입력 시 LIKE %name% 필터.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cols = (
                    "CUSTOMER_ID, CUSTOMER_NAME, CEO_NAME, CORP_NO, CUSTOMER_DOMAIN, "
                    "CUSTOMER_DOMAIN_YN, CUSTOMER_ST, MAIN_CUSTOMER_ID, REG_DT, ADMIN_ID"
                )
                offset = (page - 1) * PAGE_SIZE
                if name is not None and name.strip():
                    cur.execute(
                        "SELECT COUNT(*) AS total FROM HC_CUSTOMER WHERE CUSTOMER_NAME LIKE %s",
                        (f"%{name.strip()}%",),
                    )
                    total = cur.fetchone()["total"]
                    cur.execute(
                        f"SELECT {cols} FROM HC_CUSTOMER WHERE CUSTOMER_NAME LIKE %s ORDER BY CUSTOMER_NAME LIMIT %s OFFSET %s",
                        (f"%{name.strip()}%", PAGE_SIZE, offset),
                    )
                else:
                    cur.execute("SELECT COUNT(*) AS total FROM HC_CUSTOMER")
                    total = cur.fetchone()["total"]
                    cur.execute(
                        f"SELECT {cols} FROM HC_CUSTOMER ORDER BY CUSTOMER_NAME LIMIT %s OFFSET %s",
                        (PAGE_SIZE, offset),
                    )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "page": page,
                    "page_size": PAGE_SIZE,
                    "total": total,
                    "count": len(rows),
                    "customers": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/detail")
def get_customer_detail(
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000015952)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """Get one HC_CUSTOMER row by CUSTOMER_ID. Returns CUSTOMER_DOMAIN (도메인명) etc."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_DOMAIN, CUSTOMER_DOMAIN_YN, ROSTER_ID_TYPE,
                           MAIN_CUSTOMER_ID, CUSTOMER_ST, CUSTOMER_CERTIFY_CD, CUSTOMER_CERTIFY_CD_TYPE,
                           LOGIN_TYPE, LOGIN_URL, LOGIN_CONF_TYPE, COMMON_LOGIN_TARGET_YN
                    FROM HC_CUSTOMER
                    WHERE CUSTOMER_ID = %s
                    """,
                    (customer_id.strip(),),
                )
                row = cur.fetchone()
                if not row:
                    return {"prod": prod, "customer_id": customer_id, "found": False}
                return {"prod": prod, "found": True, "customer": dict(row)}
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
