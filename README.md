# Backend

가격 예측 기반 쇼핑 플랫폼 백엔드 API 서버

## 기술 스택

- **Framework**: Django 5.0 + Django REST Framework
- **Database**: PostgreSQL 16 + pgvector (벡터 검색)
- **Cache**: Redis 7
- **Message Broker**: RabbitMQ
- **Task Queue**: Celery
- **Container**: Docker + Docker Compose

## 프로젝트 구조

```
Backend/
├── config/                 # Django 설정
│   ├── settings/
│   │   ├── base.py        # 공통 설정
│   │   ├── dev.py         # 개발 환경
│   │   └── prod.py        # 운영 환경
│   ├── urls.py
│   └── celery.py
├── modules/               # 도메인별 모듈
│   ├── users/            # 사용자 관리
│   ├── products/         # 상품 관리
│   ├── categories/       # 카테고리 관리
│   ├── orders/           # 주문/장바구니/리뷰
│   ├── search/           # 검색/최근 본 상품
│   └── price_prediction/ # 가격 예측
├── shared/               # 공통 유틸리티
├── tests/                # 테스트
├── scripts/              # 스크립트
├── requirements/         # 의존성
└── docker-compose.yml
```

## 시작하기

### 1. 저장소 클론

```bash
git clone <repository-url>
cd Backend
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

필요시 `.env` 파일에서 API 키 등을 수정하세요:
- `OPENAI_API_KEY`: OpenAI API 키
- `GEMINI_API_KEY`: Google Gemini API 키

### 3. Docker로 실행

```bash
# 이미지 빌드 및 컨테이너 시작
docker-compose up --build -d

# 로그 확인
docker-compose logs -f backend
```

### 4. Superuser 생성 (선택)

```bash
docker-compose exec backend python manage.py createsuperuser
```

## 접속 URL

| 서비스 | URL | 설명 |
|--------|-----|------|
| API Server | http://localhost:8000 | Django API |
| API Docs | http://localhost:8000/api/docs | Swagger UI |
| Admin | http://localhost:8000/admin | Django Admin |
| Metrics | http://localhost:8000/metrics | Prometheus 메트릭 엔드포인트 |
| Flower | http://localhost:5555 | Celery 모니터링 |
| RabbitMQ | http://localhost:15672 | RabbitMQ 관리 (.env 참조) |
| Prometheus | http://localhost:9090 | 메트릭 수집 및 저장 |
| Grafana | http://localhost:3000 | 모니터링 대시보드 (.env 참조) |
| MinIO | http://localhost:9001 | 파일 스토리지 (.env 참조) |

## 자주 사용하는 명령어

```bash
# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 중지
docker-compose down

# 볼륨 포함 삭제 (DB 초기화)
docker-compose down -v

# 특정 서비스 재시작
docker-compose restart backend

# Django 쉘 접속
docker-compose exec backend python manage.py shell

# 마이그레이션 생성
docker-compose exec backend python manage.py makemigrations

# 마이그레이션 적용
docker-compose exec backend python manage.py migrate

# 테스트 실행
docker-compose exec backend pytest
```

## API 모듈별 엔드포인트

### Users (`/api/v1/users/`)
- 회원가입, 로그인, 프로필 관리

### Products (`/api/v1/products/`)
- 상품 목록, 상세, 검색

### Categories (`/api/v1/categories/`)
- 카테고리 트리, 하위 카테고리

### Orders (`/api/v1/orders/`)
- 장바구니, 구매, 리뷰, 토큰 내역

### Search (`/api/v1/search/`)
- 상품 검색, 검색 기록, 최근 본 상품

### Price Prediction (`/api/v1/predictions/`)
- 가격 예측, 가격 이력

## 브랜치 전략

- `main`: 운영 배포 브랜치
- `develop`: 개발 통합 브랜치
- `feature/*`: 기능 개발 브랜치
- `fix/*`: 버그 수정 브랜치

## 커밋 컨벤션

```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅
refactor: 코드 리팩토링
test: 테스트 코드
chore: 빌드, 설정 변경
```

## 팀원

- Backend Team
