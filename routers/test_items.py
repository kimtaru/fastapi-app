"""Test item (HC_TEST_ITEM_CD) endpoints. Look up test item by code."""
import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/test-items", tags=["test-items"])


@router.get("/by-code")
def get_test_item_by_code(
    test_item_cd: str = Query(..., description="TEST_ITEM_CD (e.g. HL324)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Get HC_TEST_ITEM_CD row(s) by TEST_ITEM_CD. Same code may exist per center/checkup item; returns TEST_ITEM_NAME and related info.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT TEST_ITEM_CD, TEST_ITEM_NAME, CHECKUP_ITEM_CD, PARTNER_CENTER_ID,
                           STANDARD_PRICE, ADD_TEST_YN, TEST_ITEM_ST
                    FROM HC_TEST_ITEM_CD
                    WHERE TEST_ITEM_CD = %s
                    LIMIT 50
                    """,
                    (test_item_cd.strip(),),
                )
                rows = cur.fetchall()
                if not rows:
                    return {
                        "prod": prod,
                        "test_item_cd": test_item_cd.strip(),
                        "found": False,
                        "message": "No test item found for this code.",
                    }
                return {
                    "prod": prod,
                    "test_item_cd": test_item_cd.strip(),
                    "found": True,
                    "test_item_name": rows[0]["TEST_ITEM_NAME"],
                    "count": len(rows),
                    "items": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/search")
def search_test_items_by_name(
    name: str = Query(..., description="TEST_ITEM_NAME partial match (e.g. 위내시경)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Search HC_TEST_ITEM_CD by TEST_ITEM_NAME (partial match). Returns distinct TEST_ITEM_CD, TEST_ITEM_NAME.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT TEST_ITEM_CD, TEST_ITEM_NAME
                    FROM HC_TEST_ITEM_CD
                    WHERE TEST_ITEM_NAME LIKE %s AND (TEST_ITEM_ST = '00' OR TEST_ITEM_ST IS NULL)
                    ORDER BY TEST_ITEM_CD
                    LIMIT 50
                    """,
                    (f"%{name.strip()}%",),
                )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "query": name.strip(),
                    "count": len(rows),
                    "items": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
