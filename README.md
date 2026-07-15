# Trip Dart Backend

광주·전라권 관광 데이터를 활용해 여행 장소를 추천하고, 커뮤니티 게시판과 데이터 기반 챗봇을 제공하는 FastAPI 백엔드입니다.

장소 데이터는 서버 시작 시 JSON 파일에서 한 번 읽어 메모리에 적재하며, 게시글은 SQLite에 저장합니다. 챗봇은 서버가 검색한 장소·게시글·현재 코스만 근거로 답변하고, OpenAI API를 사용할 수 없는 경우에도 기본 응답을 제공합니다.

## 주요 기능

- 광주·전라권 5개 카테고리 장소 데이터 로딩 및 메모리 캐싱
- 이동 방식별 거리 계산과 검색 반경 자동 확대
- 여행 후보 목록 및 랜덤 장소 선정
- 게시글 작성, 목록, 상세, 비밀번호 검증, 수정, 삭제
- 장소·게시글·현재 코스를 근거로 하는 여행 챗봇
- OpenAI API 키 누락 또는 호출 실패 시 fallback 응답

## 기술 스택

- Python 3.11+
- FastAPI 0.139
- SQLAlchemy 2.x
- Pydantic 2.x
- SQLite
- OpenAI Python SDK 2.x
- Uvicorn

## 프로젝트 구조

```text
trip-dart-backend/
├─ app/
│  ├─ core/                 # 환경설정
│  ├─ data/                 # 광주·전라권 장소 JSON
│  ├─ db/                   # DB 엔진, 세션, 초기화
│  ├─ models/               # SQLAlchemy 모델
│  ├─ routers/              # FastAPI 라우터
│  ├─ schemas/              # Pydantic 요청·응답 모델
│  ├─ services/             # 장소, 여행, 챗봇 비즈니스 로직
│  ├─ utils/                # 거리 계산 유틸리티
│  └─ main.py               # 애플리케이션 진입점
├─ data/                    # SQLite DB 생성 위치
├─ tests/                   # 서비스 및 API 테스트
├─ .env.example
└─ requirements.txt
```

## 설치 및 실행

### 1. 가상환경 생성

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. 패키지 설치

```bash
python -m pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env.example`을 복사해 `.env`를 생성합니다.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

```env
APP_NAME=Trip Dart Backend
OPENAI_API_KEY=
OPENAI_MODEL=
DATABASE_URL=sqlite:///./data/localhub.db
FRONTEND_ORIGIN=http://localhost:5173
```

`OPENAI_API_KEY`는 선택 사항입니다. 값이 없거나 API 호출이 실패하면 챗봇은 서버 검색 결과를 기반으로 기본 답변을 반환합니다. `OPENAI_MODEL`이 비어 있으면 애플리케이션 기본 모델을 사용합니다.

### 4. 서버 실행

```bash
python -m uvicorn app.main:app --reload
```

- API 서버: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

서버 시작 시 SQLite 테이블을 초기화하고 `app/data`의 장소 JSON 5개를 메모리에 로드합니다.

## 장소 데이터

다음 카테고리를 지원합니다.

| 카테고리 | 내부 키 | content type |
|---|---|---:|
| 관광지 | `tourist_spot` | 12 |
| 문화시설 | `cultural_facility` | 14 |
| 레포츠 | `leisure_sports` | 28 |
| 쇼핑 | `shopping` | 38 |
| 음식점 | `restaurant` | 39 |

JSON 데이터는 요청마다 다시 읽지 않습니다. 좌표가 없거나 필수 값이 유효하지 않은 장소는 로딩 과정에서 제외하고, `contentid` 기준으로 중복을 제거합니다.

## API

### 상태 확인

| Method | URL | 설명 |
|---|---|---|
| GET | `/health` | 서버 상태 확인 |

### 게시판

| Method | URL | 설명 |
|---|---|---|
| GET | `/api/posts` | 검색 및 페이지네이션 목록 조회 |
| POST | `/api/posts` | 게시글 작성 |
| GET | `/api/posts/{post_id}` | 게시글 상세 조회 |
| POST | `/api/posts/{post_id}/verify-password` | 비밀번호 검증 |
| PUT | `/api/posts/{post_id}` | 게시글 전체 수정 |
| DELETE | `/api/posts/{post_id}` | 게시글 삭제 |

게시글 비밀번호는 작성·수정 권한 확인에만 사용하며 API 응답에는 포함하지 않습니다.

목록 조회 예시:

```http
GET /api/posts?page=1&size=10&keyword=문화시설
```

게시글 작성 예시:

```json
{
  "post_type": "travel_review",
  "title": "광주 여행 후기",
  "content": "국립아시아문화전당에 방문했습니다.",
  "nickname": "여행자",
  "password": "0001",
  "route_data": null
}
```

### 여행 장소 후보

| Method | URL | 설명 |
|---|---|---|
| POST | `/api/trips/candidates` | 조건에 맞는 장소 후보 조회 |
| POST | `/api/trips/random-location` | 후보 중 장소 하나를 동일 확률로 선택 |

요청 예시:

```json
{
  "category": "cultural_facility",
  "transport_mode": "walking",
  "center": {
    "latitude": 35.1468,
    "longitude": 126.9198
  },
  "excluded_content_ids": []
}
```

이동 방식별 검색 반경:

- `walking`: 5km → 7.5km → 10km → 전체 데이터
- `public_transit`: 10km → 15km → 20km → 전체 데이터

`center`가 `null`이면 거리 필터 없이 해당 카테고리 전체에서 후보를 조회합니다. 거리는 하버사인 공식으로 계산하며 응답에서는 소수점 둘째 자리까지 표시합니다.

### 챗봇

| Method | URL | 설명 |
|---|---|---|
| POST | `/api/chat` | 장소·게시글·현재 코스 기반 답변 |

요청 예시:

```json
{
  "message": "광주 문화시설을 추천해줘.",
  "current_route": [
    {
      "contentid": "12345",
      "title": "국립아시아문화전당",
      "category": "cultural_facility"
    }
  ]
}
```

챗봇 처리 순서:

1. 메모리 장소 데이터 검색
2. SQLAlchemy로 관련 게시글 검색
3. 현재 코스 확인
4. 검색 결과 기반 기본 답변 생성
5. API 키가 있으면 검색된 자료만 OpenAI에 전달해 자연어 답변 생성
6. OpenAI 오류 시 기본 답변 유지

장소와 게시글은 각각 최대 3개를 반환합니다. 게시글 비밀번호, 전체 DB, 전체 JSON 데이터는 OpenAI에 전달하지 않습니다.

### 준비 중인 엔드포인트

다음 엔드포인트는 현재 자리표시자 응답만 제공합니다.

- `GET /locations`
- `GET /reports`

## 테스트

현재 테스트는 표준 `unittest`로 실행할 수 있으며 pytest에서도 수집 가능한 구조입니다.

```bash
python -m unittest discover -s tests -v
```

테스트 범위:

- 하버사인 거리 계산
- 이동 방식별 반경 확대 및 fallback
- 제외 목록과 원본 장소 객체 불변성
- 후보 및 랜덤 장소 API
- 챗봇 카테고리·장소명·주소 검색
- 게시글 제목·내용 검색
- 현재 코스 순서 유지
- OpenAI 키 누락·성공·실패 처리
- 응답 및 OpenAI 입력의 게시글 비밀번호 제외

## 설계상 주의사항

- 장소 데이터는 SQLite가 아닌 메모리에 저장됩니다.
- 서버 재시작 시 JSON 데이터를 다시 로드합니다.
- 여행 후보와 랜덤 선택 결과는 서버에 저장하지 않습니다.
- 게시글 수정 요청의 비밀번호는 변경값이 아니라 권한 확인값입니다.
- 챗봇은 검색된 근거만 OpenAI에 전달하지만 생성 답변은 운영 환경에서 별도 모니터링이 필요합니다.
- `.env`와 실제 API 키는 Git에 커밋하지 마세요.
