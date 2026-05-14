# FastAPI 앱

간단한 FastAPI 예제 프로젝트입니다.

## 설치

```bash
cd fastapi-app
pip install -r requirements.txt
```

## 실행

```bash
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger 문서: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 환영 메시지 |
| GET | `/health` | 헬스 체크 |
| GET | `/items` | 아이템 목록 |
| GET | `/items/{id}` | 아이템 조회 |
| POST | `/items` | 아이템 생성 |
| DELETE | `/items/{id}` | 아이템 삭제 |

POST `/items` 요청 예시 (JSON):

```json
{
  "name": "샘플 상품",
  "description": "설명 (선택)",
  "price": 9900.0
}
```
