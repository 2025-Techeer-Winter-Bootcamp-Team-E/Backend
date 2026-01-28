# [Stage 1] Build stage
FROM python:3.11-slim as builder

# 파이썬 환경 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements 폴더 전체를 복사하여 레이어 캐싱 활용
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir --prefix=/install -r requirements/dev.txt

# [Stage 2] Production stage
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    wget \
    gnupg \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# builder 단계에서 설치된 패키지만 깔끔하게 복사
COPY --from=builder /install /usr/local

# 소스 코드 복사
COPY . .

# 실행 권한 부여 및 디렉토리 생성
RUN chmod +x /app/scripts/entrypoint.sh && \
    mkdir -p /app/staticfiles /app/media

# 보안: Non-root user 설정
RUN addgroup --system --gid 1001 django && \
    adduser --system --uid 1001 --gid 1001 django && \
    chown -R django:django /app

USER django

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]