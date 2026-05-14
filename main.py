from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from routers import (
    persons,
    customers,
    policies,
    schema,
    reservations,
    payments,
    rosters,
    test_items,
    partner_centers,
    products,
    mindtest_checkups,
    department_temp,
)

app = FastAPI(
    title="Healthcare Checkup API",
    description="Read-only API for querying customer, reservation, and product data. Agent uses this to answer user questions.",
    version="1.0.0",
)

# 도메인별 라우터 등록
app.include_router(persons.router)
app.include_router(customers.router)
app.include_router(policies.router)
app.include_router(schema.router)
app.include_router(reservations.router)
app.include_router(payments.router)
app.include_router(rosters.router)
app.include_router(test_items.router)
app.include_router(partner_centers.router)
app.include_router(products.router)
app.include_router(mindtest_checkups.router)
app.include_router(department_temp.router)


# 요청/응답 모델 (예제용)
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float


class ItemResponse(Item):
    id: int


# 인메모리 저장소 (예제용)
items_db: dict[int, Item] = {}
item_id_counter = 1


@app.get("/")
def read_root():
    """루트 경로 - 환영 메시지"""
    return {"message": "FastAPI에 오신 것을 환영합니다!", "docs": "/docs"}


@app.get("/health")
def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "ok"}
