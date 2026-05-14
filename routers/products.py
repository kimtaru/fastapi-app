"""Product (HC_CHECKUP_PRODUCT) endpoints. List products by customer, optionally filtered by test item."""
import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/detail")
def get_product_detail(
    checkup_product_no: int = Query(..., description="HC_CHECKUP_PRODUCT.CHECKUP_PRODUCT_NO"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """Get one HC_CHECKUP_PRODUCT by CHECKUP_PRODUCT_NO. For debugging display/query conditions."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT CHECKUP_PRODUCT_NO, CUSTOMER_ID, POLICY_YEAR, PARTNER_CENTER_ID,
                           CHECKUP_DIV_CD, CHECKUP_PRODUCT_ST, PRODUCT_DISPLAY_YN, SETTLE_PRICE,
                           CHECKUP_PROPOS_NO, CHECKUP_PRODUCT_TITLE, RESERV_START_DT, RESERV_END_DT,
                           CHECKUP_START_DT, CHECKUP_END_DT
                    FROM HC_CHECKUP_PRODUCT
                    WHERE CHECKUP_PRODUCT_NO = %s
                    """,
                    (checkup_product_no,),
                )
                row = cur.fetchone()
                if not row:
                    return {"prod": prod, "checkup_product_no": checkup_product_no, "found": False}
                cur.execute(
                    """
                    SELECT PARTNER_CENTER_ID, PRODUCT_PROPOS_TYPE
                    FROM HC_PRODUCT_TEST_ITEM
                    WHERE CHECKUP_PRODUCT_NO = %s
                    """,
                    (checkup_product_no,),
                )
                test_items = cur.fetchall()
                has_non_20 = any(t.get("PRODUCT_PROPOS_TYPE") != "20" for t in test_items)
                return {
                    "prod": prod,
                    "found": True,
                    "product": dict(row),
                    "product_test_items": [dict(t) for t in test_items],
                    "has_product_propos_type_not_20": has_non_20,
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("")
def list_products_by_customer(
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000013209)"),
    test_item_name: str = Query(None, description="Include only products that have this test item (TEST_ITEM_NAME partial match, e.g. 위내시경)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    List HC_CHECKUP_PRODUCT for a customer. If test_item_name is given, only products that contain
    a test item whose name matches (via HC_PRODUCT_TEST_ITEM) are returned.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                if test_item_name and test_item_name.strip():
                    # Find TEST_ITEM_CD(s) matching the name
                    cur.execute(
                        """
                        SELECT DISTINCT TEST_ITEM_CD FROM HC_TEST_ITEM_CD
                        WHERE TEST_ITEM_NAME LIKE %s AND (TEST_ITEM_ST = '00' OR TEST_ITEM_ST IS NULL)
                        """,
                        (f"%{test_item_name.strip()}%",),
                    )
                    test_codes = [r["TEST_ITEM_CD"] for r in cur.fetchall()]
                    if not test_codes:
                        return {
                            "prod": prod,
                            "customer_id": customer_id.strip(),
                            "test_item_name": test_item_name.strip(),
                            "found": False,
                            "message": "No test item found matching the name.",
                            "products": [],
                        }
                    placeholders = ",".join(["%s"] * len(test_codes))
                    sql = f"""
                        SELECT DISTINCT P.CHECKUP_PRODUCT_NO, P.CHECKUP_PRODUCT_TITLE, P.CUSTOMER_ID,
                               P.PARTNER_CENTER_ID, P.POLICY_YEAR, P.CHECKUP_PRODUCT_ST, P.CHECKUP_PRICE
                        FROM HC_CHECKUP_PRODUCT P
                        INNER JOIN HC_PRODUCT_TEST_ITEM PTI ON P.CHECKUP_PRODUCT_NO = PTI.CHECKUP_PRODUCT_NO
                          AND P.PARTNER_CENTER_ID = PTI.PARTNER_CENTER_ID
                        WHERE P.CUSTOMER_ID = %s AND PTI.TEST_ITEM_CD IN ({placeholders})
                        ORDER BY P.CHECKUP_PRODUCT_NO
                    """
                    cur.execute(sql, (customer_id.strip(), *test_codes))
                else:
                    cur.execute(
                        """
                        SELECT CHECKUP_PRODUCT_NO, CHECKUP_PRODUCT_TITLE, CUSTOMER_ID,
                               PARTNER_CENTER_ID, POLICY_YEAR, CHECKUP_PRODUCT_ST, CHECKUP_PRICE
                        FROM HC_CHECKUP_PRODUCT
                        WHERE CUSTOMER_ID = %s
                        ORDER BY CHECKUP_PRODUCT_NO
                        """,
                        (customer_id.strip(),),
                    )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "customer_id": customer_id.strip(),
                    "test_item_name": test_item_name.strip() if test_item_name else None,
                    "found": len(rows) > 0,
                    "count": len(rows),
                    "products": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
