"""
테이블 스키마(컬럼 목록) 조회 API.
- GET /schema/{table_name}: SHOW COLUMNS 결과를 반환.
"""
from fastapi import APIRouter, Query
from db import get_db_connection

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/{table_name}")
def get_table_schema(
    table_name: str,
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    테이블 컬럼 정보 조회 (MySQL SHOW COLUMNS FROM table_name).
    반환: Field, Type, Null, Key, Default, Extra
    """
    # 테이블명 화이트리스트 (SQL injection 방지)
    allowed = {
        "HC_RESERV", "HC_PAY", "HC_USER", "HC_USER_COMMON", "HC_CUSTOMER", "HC_CUSTOMER_MAP",
        "HC_CHECKUP_ROSTER", "HC_CHECKUP_ROSTER_HIST", "HC_CHECKUP_PRODUCT", "HC_CHECKUP_PROPOS", "HC_CHECKUP_POLICY", "HC_CHECKUP_POLICY_HIST",
        "HC_PARTNER_CENTER",
        "HC_TEST_ITEM_CD", "HC_CHECKUP_ITEM_CD", "HC_RESERV_TEST_ITEM", "HC_PRODUCT_TEST_ITEM",
        "HC_DEPARTMENT_TEMP", "HC_MINDTEST_CHECKUP",
    }
    if table_name.upper() not in allowed:
        return {"error": f"Table not allowed: {table_name}", "allowed": list(allowed)}
    with get_db_connection(prod=prod) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
            rows = cur.fetchall()
    return {"table": table_name, "columns": rows}
