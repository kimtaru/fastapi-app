"""
DB 설정 및 연결.
- 비운영(EDU): get_db_connection() 또는 get_db_connection(prod=False)
- 운영(HOPS): get_db_connection(prod=True)
- .env 에서 DB_* 환경 변수 로드.
"""
import os
from contextlib import contextmanager
from typing import Generator

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()

# 비운영(EDU) DB 설정 (.env)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", ""),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}

# 운영(HOPS) DB 설정
DB_CONFIG_PROD = {
    "host": os.getenv("DB_HOST_PROD", ""),
    "port": int(os.getenv("DB_PORT_PROD", "3306")),
    "user": os.getenv("DB_USER_PROD", ""),
    "password": os.getenv("DB_PASSWORD_PROD", ""),
    "database": os.getenv("DB_NAME_PROD", ""),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}


@contextmanager
def get_db_connection(prod: bool = False) -> Generator[pymysql.Connection, None, None]:
    """
    DB 연결 컨텍스트 매니저.
    - prod=False: 비운영(EDU) DB
    - prod=True: 운영(HOPS) DB
    """
    config = DB_CONFIG_PROD if prod else DB_CONFIG
    conn = pymysql.connect(**config)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
