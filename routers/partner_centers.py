"""Partner center (HC_PARTNER_CENTER) endpoints."""
import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/partner-centers", tags=["partner-centers"])


@router.get("/detail")
def get_partner_center_detail(
    partner_center_id: str = Query(..., description="PARTNER_CENTER_ID (e.g. H00001)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Get HC_PARTNER_CENTER row by PARTNER_CENTER_ID. Returns SPECIAL_CHECKUP_YN (특수검진 진행 여부) and key fields.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT PARTNER_CENTER_ID, PARTNER_CENTER_NAME, SPECIAL_CHECKUP_YN,
                           PARTNER_CENTER_ST, PARTNER_CENTER_TYPE
                    FROM HC_PARTNER_CENTER
                    WHERE PARTNER_CENTER_ID = %s
                    """,
                    (partner_center_id.strip(),),
                )
                row = cur.fetchone()
                if not row:
                    return {
                        "prod": prod,
                        "partner_center_id": partner_center_id.strip(),
                        "found": False,
                        "message": "No partner center found for this ID.",
                    }
                return {"prod": prod, "found": True, "center": dict(row)}
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
