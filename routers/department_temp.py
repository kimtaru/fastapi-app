"""Department temp (HC_DEPARTMENT_TEMP) endpoints."""
import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/department-temp", tags=["department-temp"])


@router.get("")
def list_department_temp(
    customer_id: list[str] = Query(..., description="Repeatable CUSTOMER_ID query param (e.g. ?customer_id=C000...&customer_id=C000...)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """List HC_DEPARTMENT_TEMP rows for the given customer IDs."""
    customer_ids = [c.strip() for c in customer_id if c and c.strip()]
    if not customer_ids:
        return {"prod": prod, "count": 0, "rows": []}
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                ph = ",".join(["%s"] * len(customer_ids))
                cur.execute(
                    f"""
                    SELECT SEQ, CATEGORY, PR_SEQ, CUSTOMER_ID, NAME, CODE
                    FROM HC_DEPARTMENT_TEMP
                    WHERE CUSTOMER_ID IN ({ph})
                    ORDER BY CUSTOMER_ID, SEQ
                    """,
                    tuple(customer_ids),
                )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "customer_ids": customer_ids,
                    "count": len(rows),
                    "rows": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
