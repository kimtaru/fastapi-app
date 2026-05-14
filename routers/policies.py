"""Checkup policy (HC_CHECKUP_POLICY) endpoints. Reusable for policy lookup by customer and year."""
import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/years-by-customer")
def list_policy_years_by_customer(
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000003653)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    List POLICY_YEAR values for a customer from HC_CHECKUP_POLICY (정책연도 목록).
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT POLICY_YEAR
                    FROM HC_CHECKUP_POLICY
                    WHERE CUSTOMER_ID = %s
                    ORDER BY POLICY_YEAR
                    """,
                    (customer_id.strip(),),
                )
                rows = cur.fetchall()
                years = [r["POLICY_YEAR"] for r in rows]
                return {
                    "prod": prod,
                    "customer_id": customer_id.strip(),
                    "count": len(years),
                    "policy_years": years,
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("")
def get_policy(
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000015950)"),
    policy_year: str = Query(..., description="Policy year (e.g. 2026)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Get HC_CHECKUP_POLICY for a customer and year.
    Returns validity periods: RESERV_* (company-supported), CHECKUP_*, FAMILY_CHECKUP_*.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT CUSTOMER_ID, POLICY_YEAR,
                           RESERV_START_DT, RESERV_END_DT,
                           CHECKUP_START_DT, CHECKUP_END_DT,
                           FAMILY_CHECKUP_START_DT, FAMILY_CHECKUP_END_DT,
                           FAMILY_SUPPORT_TYPE, PRODUCT_DISPLAY_TYPE
                    FROM HC_CHECKUP_POLICY
                    WHERE CUSTOMER_ID = %s AND POLICY_YEAR = %s
                    """,
                    (customer_id.strip(), policy_year.strip()),
                )
                row = cur.fetchone()
                if not row:
                    return {
                        "prod": prod,
                        "customer_id": customer_id,
                        "policy_year": policy_year,
                        "found": False,
                        "message": "No policy found for this customer and year.",
                    }
                return {
                    "prod": prod,
                    "found": True,
                    "policy": dict(row),
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/history")
def get_policy_history(
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000029424)"),
    policy_year: str = Query(..., description="Policy year (e.g. 2026)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    HC_CHECKUP_POLICY_HIST 조회. 해당 고객사·정책연도로 적재된 정책 이력 전체 반환.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM HC_CHECKUP_POLICY_HIST
                    WHERE CUSTOMER_ID = %s AND POLICY_YEAR = %s
                    ORDER BY CHECKUP_POLICY_HIST_NO
                    """,
                    (customer_id.strip(), policy_year.strip()),
                )
                rows = cur.fetchall()
                # JSON serializable
                hist_list = []
                for r in rows:
                    row_dict = {}
                    for k, v in r.items():
                        if v is not None and hasattr(v, "isoformat"):
                            row_dict[k] = v.isoformat()
                        elif hasattr(v, "__float__") and type(v).__name__ == "Decimal":
                            row_dict[k] = float(v)
                        else:
                            row_dict[k] = v
                    hist_list.append(row_dict)
                return {
                    "prod": prod,
                    "customer_id": customer_id.strip(),
                    "policy_year": policy_year.strip(),
                    "count": len(hist_list),
                    "hist_rows": hist_list,
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
