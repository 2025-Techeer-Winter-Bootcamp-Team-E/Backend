# 서비스 접속 가이드

이 문서는 개발 환경에서 각 서비스에 접속하는 방법과 인증 정보를 정리합니다.

> **주의**: 이 문서의 인증 정보는 개발 환경 전용입니다. 운영 환경에서는 반드시 다른 값을 사용하세요.

---

## 서비스 접속 정보 요약

| 서비스 | URL | ID | PW |
|--------|-----|----|----|
| Django API | http://localhost:8000 | - | - |
| Swagger UI | http://localhost:8000/api/docs/ | - | - |
| Django Admin | http://localhost:8000/admin/ | (생성 필요) | (생성 필요) |
| PostgreSQL | localhost:5432 | postgres | postgres |
| Redis | localhost:6379 | - | redis123 |
| RabbitMQ Console | http://localhost:15672 | admin | admin123 |
| MinIO Console | http://localhost:9001 | minioadmin | minioadmin |
| Flower | http://localhost:5555 | - | - |
| Prometheus | http://localhost:9090 | - | - |
| Grafana | http://localhost:3000 | admin | admin123 |

---

## 1. Django API 서버

### 접속 정보

| 항목 | 값 |
|------|-----|
| URL | http://localhost:8000 |
| API 문서 (Swagger) | http://localhost:8000/api/docs/ |
| API 문서 (ReDoc) | http://localhost:8000/api/redoc/ |
| Admin 패널 | http://localhost:8000/admin/ |
| OpenAPI 스키마 | http://localhost:8000/api/schema/ |

### API 테스트 방법

```bash
# 헬스 체크
curl http://localhost:8000/api/v1/health/

# 회원가입
curl -X POST http://localhost:8000/api/v1/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "testuser", "password": "testpass123"}'

# 로그인 (JWT 토큰 발급)
curl -X POST http://localhost:8000/api/v1/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'

# 인증이 필요한 API 호출
curl http://localhost:8000/api/v1/users/me/ \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

### Admin 계정 생성

```bash
docker-compose exec backend python manage.py createsuperuser
```

---

## 2. PostgreSQL

### 접속 정보

| 항목 | 값 |
|------|-----|
| Host | localhost (외부) / postgres (Docker 내부) |
| Port | 5432 |
| Database | backend |
| User | postgres |
| Password | postgres |

### 접속 방법

#### CLI (psql)

```bash
# Docker 컨테이너 내부에서
docker-compose exec postgres psql -U postgres -d backend

# 호스트에서 직접 (psql 설치 필요)
psql -h localhost -p 5432 -U postgres -d backend
```

#### GUI 도구 (DBeaver, DataGrip 등)

```
Host: localhost
Port: 5432
Database: backend
User: postgres
Password: postgres
```

#### Connection String

```
# 외부 접속
postgresql://postgres:postgres@localhost:5432/backend

# Docker 내부 접속
postgresql://postgres:postgres@postgres:5432/backend
```

#### Django Shell에서 확인

```bash
docker-compose exec backend python manage.py dbshell
```

---

## 3. Redis

### 접속 정보

| 항목 | 값 |
|------|-----|
| Host | localhost (외부) / redis (Docker 내부) |
| Port | 6379 |
| Password | redis123 |
| Cache DB | 0 |
| Celery Result DB | 1 |

### 접속 방법

#### CLI (redis-cli)

```bash
# Docker 컨테이너 내부에서
docker-compose exec redis redis-cli -a redis123

# 호스트에서 직접
redis-cli -h localhost -p 6379 -a redis123
```

#### 기본 명령어

```bash
# 연결 테스트
PING

# 모든 키 조회
KEYS *

# 특정 키 조회
GET key_name

# 캐시 전체 삭제
FLUSHDB

# DB 전환 (Celery 결과 확인)
SELECT 1
KEYS *
```

#### Connection String

```
# 외부 접속
redis://:redis123@localhost:6379/0

# Docker 내부 접속
redis://:redis123@redis:6379/0
```

---

## 4. RabbitMQ

### 접속 정보

| 항목 | 값 |
|------|-----|
| Host | localhost (외부) / rabbitmq (Docker 내부) |
| AMQP Port | 5672 |
| Management Port | 15672 |
| User | admin |
| Password | admin123 |
| Virtual Host | backend |

### 접속 방법

#### 관리 콘솔 (Web UI)

```
URL: http://localhost:15672
Username: admin
Password: admin123
```

#### Connection String (AMQP)

```
# 외부 접속
amqp://admin:admin123@localhost:5672/backend

# Docker 내부 접속
amqp://admin:admin123@rabbitmq:5672/backend
```

#### CLI 관리 도구

```bash
# 큐 목록 확인
docker-compose exec rabbitmq rabbitmqctl list_queues

# 연결 목록 확인
docker-compose exec rabbitmq rabbitmqctl list_connections

# 채널 목록 확인
docker-compose exec rabbitmq rabbitmqctl list_channels
```

---

## 5. MinIO (S3 호환 스토리지)

### 접속 정보

| 항목 | 값 |
|------|-----|
| API Endpoint | http://localhost:9000 |
| Console URL | http://localhost:9001 |
| Access Key | minioadmin |
| Secret Key | minioadmin |
| Bucket | backend-media |

### 접속 방법

#### 관리 콘솔 (Web UI)

```
URL: http://localhost:9001
Username: minioadmin
Password: minioadmin
```

#### AWS CLI

```bash
# AWS CLI 설정
aws configure --profile minio
# Access Key: minioadmin
# Secret Key: minioadmin
# Region: us-east-1

# 버킷 목록
aws --endpoint-url http://localhost:9000 --profile minio s3 ls

# 파일 업로드
aws --endpoint-url http://localhost:9000 --profile minio s3 cp file.jpg s3://backend-media/

# 파일 목록
aws --endpoint-url http://localhost:9000 --profile minio s3 ls s3://backend-media/
```

#### 버킷 생성 (최초 1회)

```bash
# MinIO CLI 사용
docker-compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb local/backend-media
```

---

## 6. Celery Flower (태스크 모니터링)

### 접속 정보

| 항목 | 값 |
|------|-----|
| URL | http://localhost:5555 |
| 인증 | 없음 |

### 주요 기능

- 실시간 태스크 모니터링
- 워커 상태 확인
- 태스크 성공/실패 통계
- 태스크 상세 정보 조회

### 확인 가능한 정보

| 탭 | 설명 |
|----|------|
| Dashboard | 전체 현황 요약 |
| Tasks | 태스크 목록 및 상태 |
| Broker | RabbitMQ 연결 상태 |
| Workers | Celery 워커 상태 |

---

## 7. Prometheus (메트릭 수집)

### 접속 정보

| 항목 | 값 |
|------|-----|
| URL | http://localhost:9090 |
| 인증 | 없음 |

### 주요 쿼리 예시

```promql
# Django 요청 수
django_http_requests_total_by_method_total

# 요청 지연시간
django_http_requests_latency_seconds_by_view_method_bucket

# DB 쿼리 수
django_db_query_total

# Celery 태스크 수
celery_task_total
```

### Django 메트릭 엔드포인트

```
http://localhost:8000/metrics
```

---

## 8. Grafana (시각화)

### 접속 정보

| 항목 | 값 |
|------|-----|
| URL | http://localhost:3000 |
| Username | admin |
| Password | admin123 |

### 기본 설정

1. 로그인 후 Data Sources 설정
2. Prometheus 추가:
   - URL: `http://prometheus:9090`
   - Access: `Server (default)`

### 권장 대시보드

- Django 성능 모니터링
- Celery 태스크 현황
- PostgreSQL 데이터베이스 현황
- Redis 캐시 현황

---

## 9. Docker 컨테이너 접속

### 컨테이너 목록 확인

```bash
docker-compose ps
```

### 컨테이너 로그 확인

```bash
# 전체 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs backend
docker-compose logs celery_worker

# 실시간 로그 추적
docker-compose logs -f backend
```

### 컨테이너 쉘 접속

```bash
# Django 백엔드
docker-compose exec backend bash

# PostgreSQL
docker-compose exec postgres bash

# Redis
docker-compose exec redis sh

# RabbitMQ
docker-compose exec rabbitmq bash
```

### Django 관리 명령어

```bash
# 마이그레이션
docker-compose exec backend python manage.py migrate

# 슈퍼유저 생성
docker-compose exec backend python manage.py createsuperuser

# Django Shell
docker-compose exec backend python manage.py shell

# 정적 파일 수집
docker-compose exec backend python manage.py collectstatic
```

---

## 10. 네트워크 구성

### Docker 네트워크

```
backend_network (bridge)
├── backend_app        (Django)      - 8000
├── backend_postgres   (PostgreSQL)  - 5432
├── backend_redis      (Redis)       - 6379
├── backend_rabbitmq   (RabbitMQ)    - 5672, 15672
├── backend_celery_worker
├── backend_celery_beat
├── backend_flower                   - 5555
├── backend_minio      (MinIO)       - 9000, 9001
├── backend_prometheus (Prometheus)  - 9090
└── backend_grafana    (Grafana)     - 3000
```

### 호스트 포트 매핑

| 서비스 | 내부 포트 | 외부 포트 |
|--------|-----------|-----------|
| Django | 8000 | 8000 |
| PostgreSQL | 5432 | 5432 |
| Redis | 6379 | 6379 |
| RabbitMQ AMQP | 5672 | 5672 |
| RabbitMQ Console | 15672 | 15672 |
| MinIO API | 9000 | 9000 |
| MinIO Console | 9001 | 9001 |
| Flower | 5555 | 5555 |
| Prometheus | 9090 | 9090 |
| Grafana | 3000 | 3000 |

---

## 11. 트러블슈팅

### 서비스 상태 확인

```bash
# 전체 서비스 상태
docker-compose ps

# 헬스 체크
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/api/v1/health/ready/
```

### 일반적인 문제 해결

| 문제 | 해결 방법 |
|------|----------|
| DB 연결 실패 | `docker-compose restart postgres` |
| Redis 연결 실패 | `docker-compose restart redis` |
| Celery 태스크 실행 안됨 | `docker-compose restart celery_worker` |
| 포트 충돌 | 기존 프로세스 종료 후 재시작 |

### 전체 초기화

```bash
# 컨테이너 중지 및 삭제
docker-compose down

# 볼륨까지 삭제 (데이터 초기화)
docker-compose down -v

# 재시작
docker-compose up -d
```

---

*마지막 업데이트: 2025년 1월*
