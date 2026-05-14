"""Person-related endpoints (HC_USER, HC_USER_COMMON, HC_CUSTOMER_MAP)."""
from datetime import datetime
from typing import Optional

import pymysql
from fastapi import APIRouter, HTTPException, Query

from db import get_db_connection

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("/unified-member")
def check_unified_member(
    name: str = Query(..., description="Person name (e.g. 김진솔)"),
    company: str = Query(..., description="Company name (e.g. 오빠닭)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Check whether a person (by name + company) is a unified member (통합 회원).
    Returns corporate member info and, if linked, unified member (HC_USER_COMMON) info.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT CUSTOMER_ID, CUSTOMER_NAME FROM HC_CUSTOMER WHERE CUSTOMER_NAME LIKE %s",
                    (f"%{company.strip()}%",),
                )
                customers = cur.fetchall()
                if not customers:
                    return {
                        "found": False,
                        "message": f"No company found for: {company}",
                        "is_unified_member": False,
                    }

                customer_ids = [c["CUSTOMER_ID"] for c in customers]
                placeholders = ",".join(["%s"] * len(customer_ids))
                cur.execute(
                    f"SELECT USER_NO, USER_ID, USER_NAME, CUSTOMER_ID, MOBILE_NO, BIRTHDAY, USER_ST "
                    f"FROM HC_USER WHERE USER_NAME LIKE %s AND CUSTOMER_ID IN ({placeholders})",
                    (f"%{name.strip()}%", *customer_ids),
                )
                users = cur.fetchall()
                if not users:
                    return {
                        "found": False,
                        "message": f"No corporate member found: name={name}, company={company}",
                        "is_unified_member": False,
                        "company": [dict(c) for c in customers],
                    }

                user_nos = [u["USER_NO"] for u in users]
                ph = ",".join(["%s"] * len(user_nos))
                cur.execute(
                    f"SELECT COMMON_USER_NO, USER_NO, CUSTOMER_ID FROM HC_CUSTOMER_MAP "
                    f"WHERE USER_NO IN ({ph})",
                    tuple(user_nos),
                )
                maps = cur.fetchall()
                common_user_nos = list({m["COMMON_USER_NO"] for m in maps})

                if not common_user_nos:
                    return {
                        "found": True,
                        "is_unified_member": False,
                        "corporate_members": [dict(u) for u in users],
                        "company": [dict(c) for c in customers],
                    }

                ph2 = ",".join(["%s"] * len(common_user_nos))
                cur.execute(
                    f"SELECT COMMON_USER_NO, USER_ID, USER_NAME, MOBILE_NO, USER_ST "
                    f"FROM HC_USER_COMMON WHERE COMMON_USER_NO IN ({ph2})",
                    tuple(common_user_nos),
                )
                common = cur.fetchall()

                return {
                    "found": True,
                    "is_unified_member": True,
                    "corporate_members": [dict(u) for u in users],
                    "unified_member": [dict(c) for c in common],
                    "company": [dict(c) for c in customers],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/unified-by-id")
def get_unified_member_by_user_id(
    user_id: str = Query(..., description="HC_USER_COMMON.USER_ID (통합 로그인 아이디)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Get HC_USER_COMMON (통합회원) by USER_ID (exact match).
    Returns unified member and linked corporate members (HC_CUSTOMER_MAP + HC_USER).
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COMMON_USER_NO, USER_ID, USER_NAME, MOBILE_NO, BIRTHDAY, USER_ST, DORMANT_YN
                    FROM HC_USER_COMMON
                    WHERE USER_ID = %s
                    """,
                    (user_id.strip(),),
                )
                row = cur.fetchone()
                if not row:
                    return {
                        "prod": prod,
                        "user_id": user_id.strip(),
                        "found": False,
                        "message": "No unified member with this USER_ID.",
                    }
                common_user_no = row["COMMON_USER_NO"]
                cur.execute(
                    """
                    SELECT M.COMMON_USER_NO, M.USER_NO, U.CUSTOMER_ID, U.USER_NAME, C.CUSTOMER_NAME
                    FROM HC_CUSTOMER_MAP M
                    JOIN HC_USER U ON M.USER_NO = U.USER_NO
                    LEFT JOIN HC_CUSTOMER C ON U.CUSTOMER_ID = C.CUSTOMER_ID
                    WHERE M.COMMON_USER_NO = %s
                    """,
                    (common_user_no,),
                )
                maps = cur.fetchall()
                return {
                    "prod": prod,
                    "user_id": user_id.strip(),
                    "found": True,
                    "unified_member": dict(row),
                    "corporate_members": [dict(m) for m in maps],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/unified-accounts-by-corporate")
def list_unified_accounts_by_user_no(
    user_no: int = Query(..., description="HC_USER.USER_NO (법인회원)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    List all HC_USER_COMMON (통합회원) linked to a corporate member (USER_NO) via HC_CUSTOMER_MAP.
    Use to check how many unified accounts one person (one USER_NO) has.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT C.COMMON_USER_NO, C.USER_ID, C.USER_NAME, C.MOBILE_NO, C.USER_ST, C.DORMANT_YN
                    FROM HC_CUSTOMER_MAP M
                    JOIN HC_USER_COMMON C ON M.COMMON_USER_NO = C.COMMON_USER_NO
                    WHERE M.USER_NO = %s
                    ORDER BY C.COMMON_USER_NO
                    """,
                    (user_no,),
                )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "user_no": user_no,
                    "count": len(rows),
                    "unified_accounts": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/unified-by-name")
def search_unified_member_by_name(
    name: str = Query(..., description="Unified member name (e.g. 심예지)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Search HC_USER_COMMON (통합회원) by USER_NAME. Returns unified member(s) and linked corporate members.
    Uses USER_ST = '00' (active only).
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COMMON_USER_NO, USER_ID, USER_NAME, MOBILE_NO, BIRTHDAY, USER_ST
                    FROM HC_USER_COMMON
                    WHERE USER_NAME LIKE %s AND USER_ST = '00'
                    ORDER BY USER_NAME
                    """,
                    (f"%{name.strip()}%",),
                )
                common_list = cur.fetchall()
                if not common_list:
                    return {
                        "prod": prod,
                        "query": name.strip(),
                        "count": 0,
                        "found": False,
                        "unified_members": [],
                    }
                common_nos = [c["COMMON_USER_NO"] for c in common_list]
                ph = ",".join(["%s"] * len(common_nos))
                cur.execute(
                    f"""
                    SELECT M.COMMON_USER_NO, M.USER_NO, U.CUSTOMER_ID, U.USER_NAME, C.CUSTOMER_NAME
                    FROM HC_CUSTOMER_MAP M
                    JOIN HC_USER U ON M.USER_NO = U.USER_NO
                    LEFT JOIN HC_CUSTOMER C ON U.CUSTOMER_ID = C.CUSTOMER_ID
                    WHERE M.COMMON_USER_NO IN ({ph})
                    """,
                    tuple(common_nos),
                )
                maps = cur.fetchall()
                by_common = {}
                for m in maps:
                    cno = m["COMMON_USER_NO"]
                    if cno not in by_common:
                        by_common[cno] = []
                    by_common[cno].append(
                        {"CUSTOMER_ID": m["CUSTOMER_ID"], "CUSTOMER_NAME": m["CUSTOMER_NAME"], "USER_NO": m["USER_NO"]}
                    )
                result = []
                for c in common_list:
                    result.append(
                        {
                            "unified": dict(c),
                            "corporate_members": by_common.get(c["COMMON_USER_NO"], []),
                        }
                    )
                return {
                    "prod": prod,
                    "query": name.strip(),
                    "count": len(result),
                    "found": True,
                    "unified_members": result,
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/corporate-by-employ-no")
def get_corporate_member_by_employ_no(
    customer_id: str = Query(..., description="CUSTOMER_ID (e.g. C000012396)"),
    employ_no: str = Query(..., description="EMPLOY_NO (사번, e.g. A018)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """Get HC_USER row(s) by CUSTOMER_ID and EMPLOY_NO (사번)."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT U.USER_NO, U.USER_ID, U.USER_NAME, U.CUSTOMER_ID, U.EMPLOY_NO,
                           U.MOBILE_NO, U.BIRTHDAY, U.USER_ST, U.DEPARTMENT,
                           C.CUSTOMER_NAME
                    FROM HC_USER U
                    LEFT JOIN HC_CUSTOMER C ON U.CUSTOMER_ID = C.CUSTOMER_ID
                    WHERE U.CUSTOMER_ID = %s AND U.EMPLOY_NO = %s
                    """,
                    (customer_id.strip(), employ_no.strip()),
                )
                rows = cur.fetchall()
                return {
                    "prod": prod,
                    "customer_id": customer_id.strip(),
                    "employ_no": employ_no.strip(),
                    "count": len(rows),
                    "found": len(rows) > 0,
                    "users": [dict(r) for r in rows],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/by-user-no")
def get_user_by_user_no(
    user_no: int = Query(..., description="HC_USER.USER_NO"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """Get one HC_USER row by USER_NO (for mapping check)."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT U.USER_NO, U.USER_ID, U.USER_NAME, U.CUSTOMER_ID, U.EMPLOY_NO, U.MOBILE_NO, U.BIRTHDAY, U.USER_ST,
                           U.USER_TYPE, U.USER_RELATION_TYPE,
                           C.CUSTOMER_NAME
                    FROM HC_USER U
                    LEFT JOIN HC_CUSTOMER C ON U.CUSTOMER_ID = C.CUSTOMER_ID
                    WHERE U.USER_NO = %s
                    """,
                    (user_no,),
                )
                row = cur.fetchone()
                if not row:
                    return {"prod": prod, "user_no": user_no, "found": False}
                return {"prod": prod, "found": True, "user": dict(row)}
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/creation-dates")
def get_creation_dates(
    user_no: Optional[int] = Query(None, description="HC_USER.USER_NO (법인회원 번호)"),
    common_user_no: Optional[int] = Query(None, description="HC_USER_COMMON.COMMON_USER_NO (통합회원 번호)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """Get creation timestamps for HC_USER/HC_USER_COMMON and mapping REG_DT."""
    if user_no is None and common_user_no is None:
        raise HTTPException(status_code=400, detail="Provide at least one of user_no or common_user_no.")

    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                result = {"prod": prod, "user_no": user_no, "common_user_no": common_user_no}

                if user_no is not None:
                    cur.execute(
                        """
                        SELECT USER_NO, USER_NAME, CUSTOMER_ID, JOIN_DT
                        FROM HC_USER
                        WHERE USER_NO = %s
                        """,
                        (user_no,),
                    )
                    row = cur.fetchone()
                    result["corporate_user"] = dict(row) if row else None

                if common_user_no is not None:
                    cur.execute(
                        """
                        SELECT COMMON_USER_NO, USER_ID, USER_NAME, JOIN_DT
                        FROM HC_USER_COMMON
                        WHERE COMMON_USER_NO = %s
                        """,
                        (common_user_no,),
                    )
                    row = cur.fetchone()
                    result["unified_user"] = dict(row) if row else None

                if user_no is not None and common_user_no is not None:
                    cur.execute(
                        """
                        SELECT COMMON_USER_NO, USER_NO, CUSTOMER_ID, REG_DT
                        FROM HC_CUSTOMER_MAP
                        WHERE USER_NO = %s AND COMMON_USER_NO = %s
                        ORDER BY REG_DT
                        """,
                        (user_no, common_user_no),
                    )
                    maps = cur.fetchall()
                    result["mapping_count"] = len(maps)
                    result["mappings"] = [dict(m) for m in maps]

                return result
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/ci-compare")
def compare_user_ci(
    user_no: int = Query(..., description="HC_USER.USER_NO (법인회원 번호)"),
    common_user_no: int = Query(..., description="HC_USER_COMMON.COMMON_USER_NO (통합회원 번호)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """Compare USER_CI values between HC_USER and HC_USER_COMMON."""
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT USER_NO, USER_NAME, USER_CI
                    FROM HC_USER
                    WHERE USER_NO = %s
                    """,
                    (user_no,),
                )
                corp = cur.fetchone()

                cur.execute(
                    """
                    SELECT COMMON_USER_NO, USER_ID, USER_NAME, USER_CI
                    FROM HC_USER_COMMON
                    WHERE COMMON_USER_NO = %s
                    """,
                    (common_user_no,),
                )
                unified = cur.fetchone()

                return {
                    "prod": prod,
                    "user_no": user_no,
                    "common_user_no": common_user_no,
                    "corporate_user": dict(corp) if corp else None,
                    "unified_user": dict(unified) if unified else None,
                    "ci_match": bool(corp and unified and corp.get("USER_CI") == unified.get("USER_CI")),
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/user-change-clues")
def get_user_change_clues(
    user_no: int = Query(..., description="HC_USER.USER_NO (법인회원 번호)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """
    Gather forensic clues for HC_USER changes when no dedicated history table exists.
    Returns timestamps/admin fields from HC_USER plus mapping/roster/reservation related times.
    """
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT USER_NO, USER_ID, USER_NAME, CUSTOMER_ID, EMPLOY_NO, MOBILE_NO, BIRTHDAY, USER_ST,
                           JOIN_DT, LOGIN_DT, PWD_RESET_DT, LAST_PASSWORD_CHANGE_DT, TRY_LOGIN_DT,
                           CHANGE_ADMIN_ID, DORMANT_YN
                    FROM HC_USER
                    WHERE USER_NO = %s
                    """,
                    (user_no,),
                )
                user_row = cur.fetchone()
                if not user_row:
                    return {"prod": prod, "user_no": user_no, "found": False}

                cur.execute(
                    """
                    SELECT COMMON_USER_NO, USER_NO, CUSTOMER_ID, REG_DT
                    FROM HC_CUSTOMER_MAP
                    WHERE USER_NO = %s
                    ORDER BY REG_DT
                    """,
                    (user_no,),
                )
                maps = cur.fetchall()

                cur.execute(
                    """
                    SELECT CHECKUP_ROSTER_NO, CUSTOMER_ID, ROSTER_NAME, USER_NO, BIRTHDAY, MOBILE_NO,
                           EMPLOY_NO, CHECKUP_ROSTER_ST, POLICY_YEAR, REG_DT, LAST_PATH
                    FROM HC_CHECKUP_ROSTER
                    WHERE USER_NO = %s
                    ORDER BY REG_DT
                    """,
                    (user_no,),
                )
                rosters = cur.fetchall()

                cur.execute(
                    """
                    SELECT R.RESERV_NO, R.CHECKUP_ROSTER_NO, R.RESERV_REG_DT, R.RESERV_DAY, R.RESERV_ST, R.LAST_MODIFIER
                    FROM HC_RESERV R
                    JOIN HC_CHECKUP_ROSTER CR ON CR.CHECKUP_ROSTER_NO = R.CHECKUP_ROSTER_NO
                    WHERE CR.USER_NO = %s
                    ORDER BY R.RESERV_REG_DT
                    """,
                    (user_no,),
                )
                reservs = cur.fetchall()

                return {
                    "prod": prod,
                    "user_no": user_no,
                    "found": True,
                    "user": dict(user_row),
                    "map_count": len(maps),
                    "maps": [dict(m) for m in maps],
                    "roster_count": len(rosters),
                    "rosters": [dict(r) for r in rosters],
                    "reservation_count": len(reservs),
                    "reservations": [dict(r) for r in reservs],
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.patch("/by-user-no")
def update_user_relation_and_type(
    user_no: int = Query(..., description="HC_USER.USER_NO"),
    user_relation_type: Optional[str] = Query(None, description="USER_RELATION_TYPE (e.g. 50)"),
    user_type: Optional[str] = Query(None, description="USER_TYPE (e.g. 20)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
):
    """Update HC_USER.USER_RELATION_TYPE and/or USER_TYPE for the given USER_NO."""
    if user_relation_type is None and user_type is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of user_relation_type or user_type must be provided.",
        )
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                updates = []
                params = []
                if user_relation_type is not None:
                    updates.append("USER_RELATION_TYPE = %s")
                    params.append(user_relation_type.strip())
                if user_type is not None:
                    updates.append("USER_TYPE = %s")
                    params.append(user_type.strip())
                params.append(user_no)
                cur.execute(
                    f"UPDATE HC_USER SET {', '.join(updates)} WHERE USER_NO = %s",
                    params,
                )
                if cur.rowcount == 0:
                    return {
                        "prod": prod,
                        "user_no": user_no,
                        "updated": False,
                        "message": "No row found for this USER_NO.",
                    }
                return {
                    "prod": prod,
                    "user_no": user_no,
                    "updated": True,
                    "user_relation_type": user_relation_type,
                    "user_type": user_type,
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@router.get("/mapped-customers-diagnostics")
def mapped_customers_diagnostics(
    common_user_no: int = Query(..., description="HC_USER_COMMON.COMMON_USER_NO (통합회원 번호)"),
    prod: bool = Query(False, description="Use production DB (HOPS) when True, else EDU"),
    as_of: Optional[str] = Query(
        None,
        description="Evaluate policy validity as of this timestamp (YYYYMMDDHHMMSS). Default: now().",
        min_length=14,
        max_length=14,
    ),
):
    """
    Diagnostics endpoint to explain why a 'mapped customers' query may return 0 rows.
    Evaluates key join/where conditions similar to legacy query:
    - HC_USER_COMMON / HC_CUSTOMER_MAP / HC_CUSTOMER / HC_USER
    - Existence of matching roster under customer/user
    - Customer display flag (CUSTOMER_DISPLAY_YN)
    - Policy validity windows (RESERV_* or FAMILY_CHECKUP_*) at a point in time
    """
    as_of_ts = as_of.strip() if as_of is not None else datetime.now().strftime("%Y%m%d%H%M%S")
    try:
        with get_db_connection(prod=prod) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COMMON_USER_NO, USER_ID, USER_NAME, MOBILE_NO, USER_ST, DORMANT_YN
                    FROM HC_USER_COMMON
                    WHERE COMMON_USER_NO = %s
                    """,
                    (common_user_no,),
                )
                common = cur.fetchone()
                if not common:
                    return {
                        "prod": prod,
                        "common_user_no": common_user_no,
                        "as_of": as_of_ts,
                        "found_common_user": False,
                        "message": "No HC_USER_COMMON row for this COMMON_USER_NO.",
                    }

                cur.execute(
                    """
                    SELECT CUSTOMER_ID, USER_NO
                    FROM HC_CUSTOMER_MAP
                    WHERE COMMON_USER_NO = %s
                    ORDER BY CUSTOMER_ID, USER_NO
                    """,
                    (common_user_no,),
                )
                maps = cur.fetchall()
                if not maps:
                    return {
                        "prod": prod,
                        "common_user_no": common_user_no,
                        "as_of": as_of_ts,
                        "found_common_user": True,
                        "common_user": dict(common),
                        "map_count": 0,
                        "diagnostics": [],
                        "message": "No HC_CUSTOMER_MAP rows for this COMMON_USER_NO.",
                    }

                diagnostics = []
                for m in maps:
                    customer_id = m["CUSTOMER_ID"]
                    user_no = m["USER_NO"]

                    cur.execute(
                        """
                        SELECT *
                        FROM HC_CUSTOMER_MAP
                        WHERE COMMON_USER_NO = %s AND CUSTOMER_ID = %s AND USER_NO = %s
                        LIMIT 1
                        """,
                        (common_user_no, customer_id, user_no),
                    )
                    map_row = cur.fetchone()

                    cur.execute(
                        """
                        SELECT CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_DISPLAY_YN, ROSTER_ID_TYPE,
                               RELATION_POPUP_YN, COMPANY_LOGO_URL,
                               CUSTOMER_PERSONAL_CODE, CUSTOMER_PERSONAL_START_DT, CUSTOMER_PERSONAL_END_DT, CUSTOMER_PERSONAL_NOTE,
                               MULTI_ROSTER_RESERV_YN, MAPPING_TYPE, ADD_TEST_YN
                        FROM HC_CUSTOMER
                        WHERE CUSTOMER_ID = %s
                        """,
                        (customer_id,),
                    )
                    customer = cur.fetchone()

                    cur.execute(
                        """
                        SELECT USER_NO, USER_ID, USER_NAME, CUSTOMER_ID, EMPLOY_NO, MOBILE_NO, BIRTHDAY, USER_ST, USER_TYPE, USER_RELATION_TYPE
                        FROM HC_USER
                        WHERE USER_NO = %s
                        """,
                        (user_no,),
                    )
                    user = cur.fetchone()

                    # Policy validity: either corporate billing period OR personal(family) billing period contains as_of_ts
                    cur.execute(
                        """
                        SELECT COUNT(*) AS cnt
                        FROM HC_CHECKUP_POLICY P
                        WHERE P.CUSTOMER_ID = %s
                          AND (
                                (P.RESERV_START_DT <= %s AND P.RESERV_END_DT >= %s)
                             OR (P.FAMILY_CHECKUP_START_DT <= %s AND P.FAMILY_CHECKUP_END_DT >= %s)
                          )
                        """,
                        (customer_id, as_of_ts, as_of_ts, as_of_ts, as_of_ts),
                    )
                    valid_policy_cnt = cur.fetchone()["cnt"]

                    # Roster match existence similar to legacy join:
                    # HCR.CUSTOMER_ID = HU.CUSTOMER_ID AND (HCR.USER_NO = HU.USER_NO OR (name + (mobile or employ) + birthday))
                    roster_match_cnt = 0
                    roster_customer_id_mismatch_cnt = 0
                    if user:
                        hu_customer_id = user["CUSTOMER_ID"]
                        # count matches under HU.CUSTOMER_ID (as legacy join uses HU.CUSTOMER_ID, not HCM.CUSTOMER_ID)
                        cur.execute(
                            """
                            SELECT COUNT(*) AS cnt
                            FROM HC_CHECKUP_ROSTER HCR
                            WHERE HCR.CUSTOMER_ID = %s
                              AND (
                                    HCR.USER_NO = %s
                                 OR (
                                        HCR.ROSTER_NAME = %s
                                    AND (HCR.MOBILE_NO = %s OR HCR.EMPLOY_NO = %s)
                                    AND HCR.BIRTHDAY = %s
                                 )
                              )
                              AND (
                                    HCR.CHECKUP_ROSTER_ST = '00'
                                 OR (HCR.CHECKUP_ROSTER_ST = '90' AND HCR.EMPLOY_RELATION_TYPE = '99')
                              )
                            """,
                            (
                                hu_customer_id,
                                user_no,
                                user["USER_NAME"],
                                user["MOBILE_NO"],
                                user["EMPLOY_NO"],
                                user["BIRTHDAY"],
                            ),
                        )
                        roster_match_cnt = cur.fetchone()["cnt"]

                        # If HCM.CUSTOMER_ID != HU.CUSTOMER_ID, legacy query can silently filter depending on other joins.
                        roster_customer_id_mismatch_cnt = 1 if (hu_customer_id and hu_customer_id != customer_id) else 0

                    # Employ info existence
                    has_user_employ_info = False
                    if user:
                        cur.execute(
                            "SELECT 1 FROM HC_USER_EMPLOY_INFO UEI WHERE UEI.USER_NO = %s LIMIT 1",
                            (user_no,),
                        )
                        has_user_employ_info = cur.fetchone() is not None

                    diagnostics.append(
                        {
                            "map": dict(map_row) if map_row else {"CUSTOMER_ID": customer_id, "USER_NO": user_no},
                            "common_user_filters": {
                                "HUC_USER_ST_is_00": common.get("USER_ST") == "00",
                                "HU_USER_ST_is_00": (user.get("USER_ST") == "00") if user else False,
                            },
                            "customer": dict(customer) if customer else None,
                            "customer_filters": {
                                "CUSTOMER_DISPLAY_YN_is_Y": (customer.get("CUSTOMER_DISPLAY_YN") == "Y") if customer else False,
                            },
                            "user": dict(user) if user else None,
                            "computed": {
                                "as_of": as_of_ts,
                                "has_user_employ_info": has_user_employ_info,
                                "valid_policy_count": int(valid_policy_cnt),
                                "roster_match_count": int(roster_match_cnt),
                                "hcm_customer_id_differs_from_hu_customer_id": bool(roster_customer_id_mismatch_cnt),
                            },
                            "would_pass_legacy_query_core": bool(
                                common.get("USER_ST") == "00"
                                and user
                                and user.get("USER_ST") == "00"
                                and customer
                                and customer.get("CUSTOMER_DISPLAY_YN") == "Y"
                                and valid_policy_cnt > 0
                                and roster_match_cnt > 0
                            ),
                        }
                    )

                return {
                    "prod": prod,
                    "common_user_no": common_user_no,
                    "as_of": as_of_ts,
                    "found_common_user": True,
                    "common_user": dict(common),
                    "map_count": len(maps),
                    "diagnostics": diagnostics,
                }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
