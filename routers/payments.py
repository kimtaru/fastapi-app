"""Payment (HC_PAY) endpoints. Reusable for lookup by reservation or roster."""
import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/by-reservation")
def get_payments_by_reserv_no(
    reserv_no: int = Query(..., description="HC_RESERV.RESERV_NO"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    List HC_PAY rows for a reservation. PAY_ST 70 = payment complete (결제완료).
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT PAY_NO, RESERV_NO, PAY_AMOUNT, PAY_REQ_AMOUNT, PAY_ST,
                           PAY_COMPLETE_DT, REG_DT, PAYWAY_TYPE
                    FROM HC_PAY
                    WHERE RESERV_NO = %s
                    ORDER BY REG_DT DESC
                    """,
                    (reserv_no,),
                )
                rows = cur.fetchall()
                paid = any(r.get("PAY_ST") == "70" for r in rows)
                return {
                    "prod": prod,
                    "reserv_no": reserv_no,
                    "count": len(rows),
                    "paid": paid,
                    "payments": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
