# AI 쇼핑 인텔리전스 (가격 예측 + 최저가)

## 개요

본 프로젝트는 **XGBoost 머신러닝 모델**을 활용한 가격 예측 시스템과 **실시간 최저가 추적 시스템**을 결합하여 사용자에게 최적의 구매 타이밍을 제공하는 AI 쇼핑 인텔리전스 플랫폼입니다.

---

## 1. 가격 예측 시스템

### 1.1 기술 스택

- **머신러닝 모델**: XGBoost (XGBRegressor)
- **데이터 처리**: Pandas, NumPy
- **시계열 분석**: 이동 평균, 트렌드 분석
- **폴백 메커니즘**: XGBoost 실패 시 간단한 이동 평균 기반 예측

### 1.2 예측 모델 구조

#### 특징(Feature) 추출

```python
# 시계열 윈도우 크기: 최근 7일 데이터 사용
window_size = min(7, len(df) - 1)

# 추출되는 특징:
feature_row = [
    window_prices[-1],      # 최신 가격
    np.mean(window_prices), # 평균 가격
    np.std(window_prices),  # 표준편차
    price_change,           # 가격 변화량
    deviation_rate,         # 평균 대비 편차율
    day_of_week,           # 요일 (0-6)
    day_of_month,          # 일 (1-31)
]
```

#### XGBoost 모델 파라미터

```python
model = xgb.XGBRegressor(
    n_estimators=50,        # 트리 개수
    max_depth=3,            # 트리 깊이
    learning_rate=0.1,      # 학습률
    random_state=42,        # 재현성 보장
    objective='reg:squarederror'  # 회귀 목적 함수
)
```

### 1.3 예측 프로세스

1. **가격 이력 수집** (`PriceHistoryModel`)
   - 최근 30일간의 가격 데이터 조회
   - `lowest_price` 기준으로 시계열 데이터 구성

2. **특징 생성**
   - 최근 7일 윈도우를 사용한 시계열 특징 추출
   - 통계적 특징 (평균, 표준편차, 변화량) 계산
   - 시간적 특징 (요일, 일) 추가

3. **모델 학습 및 예측**
   - XGBoost 모델을 실시간으로 학습
   - 예측일까지의 일수를 고려한 예측 수행
   - 예측 범위: 1~30일

4. **신뢰도 계산**
   ```python
   # 시간이 지날수록 신뢰도 감소
   confidence = max(0.5, 0.95 - (days_ahead * 0.02))
   ```

### 1.4 구매 적합도 점수 (0-100)

#### 예측 가격 ≤ 목표가인 경우
```python
price_diff = target_price - predicted_price
discount_rate = (price_diff / target_price * 100)
suitability_score = min(100, int(75 + discount_rate * 0.5))

# 할인율에 따른 가이드 메시지:
# - 10% 이상: "현재 역대 최저가에 근접한 저점 구간입니다. 구매를 강력 추천합니다."
# - 5~10%: "예측 가격이 목표가보다 낮습니다. 구매를 권장합니다."
# - 5% 미만: "예측 가격이 목표가와 유사합니다. 구매를 고려해볼 수 있습니다."
```

#### 예측 가격 > 목표가인 경우
```python
price_diff = predicted_price - target_price
premium_rate = (price_diff / target_price * 100)
suitability_score = max(0, int(50 - premium_rate * 0.5))

# 프리미엄율에 따른 가이드 메시지:
# - 10% 이상: "예측 가격이 목표가보다 높습니다. 좀 더 기다려보세요."
# - 10% 미만: "예측 가격이 목표가보다 약간 높습니다. 관찰을 권장합니다."
```

### 1.5 폴백 메커니즘

XGBoost가 사용 불가능하거나 데이터가 부족한 경우:

```python
# 간단한 이동 평균 기반 예측
prices = [h.lowest_price for h in history[-7:]]
avg_price = sum(prices) / len(prices)

# 트렌드 계산
recent_avg = sum(prices[-3:]) / 3
older_avg = sum(prices[:3]) / 3
trend_factor = (recent_avg - older_avg) / older_avg

# 예측 가격 계산
predicted = int(avg_price * (1 + trend_factor * days_ahead * 0.1))
```

---

## 2. 최저가 추적 시스템

### 2.1 데이터 수집

#### 크롤링 기술
- **Selenium**: 동적 웹페이지 크롤링
- **BeautifulSoup**: HTML 파싱
- **다나와 API**: 가격 그래프 API 활용 (최대 24개월)

#### 수집 데이터
```python
# 상품 정보
ProductModel:
  - danawa_product_id: 상품 고유 번호
  - lowest_price: 최저가
  - name, brand, detail_spec, ...

# 판매처별 가격 정보
MallInformationModel:
  - mall_name: 쇼핑몰 이름
  - current_price: 현재가
  - product_page_url: 상품 페이지 URL
```

### 2.2 가격 이력 관리

#### PriceHistoryModel 구조
```python
class PriceHistoryModel:
    danawa_product_id: str      # 상품 고유 번호
    lowest_price: int           # 해당 시점의 최저가
    recorded_at: datetime       # 기록 일시
    created_at, updated_at      # 생성/수정 시각
    deleted_at                  # 논리적 삭제 플래그
```

#### 가격 이력 기록 프로세스

1. **Celery 태스크**: `record_price_history`
   ```python
   @shared_task(name='products.record_price_history')
   def record_price_history(product_id: int):
       product = ProductModel.objects.get(id=product_id)
       PriceHistoryModel.objects.create(
           danawa_product_id=product.danawa_product_id,
           lowest_price=product.lowest_price,
           recorded_at=timezone.now(),
       )
   ```

2. **배치 처리**: `record_all_price_histories`
   - 모든 활성 상품의 최저가를 일괄 기록
   - Celery Beat를 통한 주기적 실행

### 2.3 가격 트렌드 분석

```python
def get_price_trend(danawa_product_id: str, days: int = 30) -> dict:
    """
    가격 트렌드 분석 결과:
    {
        'trend': 'increasing' | 'decreasing' | 'stable',
        'change_percent': float,  # 변화율 (%)
        'data_points': int,       # 데이터 포인트 수
        'min_price': int,         # 기간 내 최저가
        'max_price': int,         # 기간 내 최고가
        'avg_price': float        # 기간 내 평균가
    }
    """
    
    # 트렌드 판단 기준:
    # - change_percent > 5%: 'increasing'
    # - change_percent < -5%: 'decreasing'
    # - 그 외: 'stable'
```

---

## 3. 통합 시스템 아키텍처

### 3.1 데이터 흐름

```
[크롤러] → [ProductModel] → [PriceHistoryModel]
                ↓                    ↓
         [최저가 업데이트]    [가격 이력 저장]
                ↓                    ↓
         [실시간 가격 비교]    [XGBoost 예측 모델]
                ↓                    ↓
         [MallInformationModel]  [TimerModel]
                ↓                    ↓
         [판매처별 가격]      [구매 타이밍 예측]
```

### 3.2 API 엔드포인트

#### 가격 예측 (Timer)
- `POST /api/v1/timers/`: 타이머 생성 (가격 예측 수행)
- `GET /api/v1/timers/{product_code}/`: 상품별 타이머 조회
- `GET /api/v1/timers/detail/{timer_id}/`: 타이머 상세 조회
- `PATCH /api/v1/timers/detail/{timer_id}/`: 목표가 수정
- `DELETE /api/v1/timers/detail/{timer_id}/`: 타이머 삭제

#### 가격 추이
- `GET /api/v1/products/{product_code}/price-trend/`: 가격 추이 조회 (6/12/24개월)
- `GET /api/v1/timers/trend/{product_code}/`: 가격 트렌드 분석

#### 최저가 정보
- `GET /api/v1/products/{product_code}/prices/`: 판매처별 현재가 조회

### 3.3 비동기 작업 (Celery)

#### 배치 작업
```python
# 일일 가격 예측 생성
@shared_task(name='timers.generate_daily_predictions')
def generate_daily_predictions():
    # 모든 활성 상품에 대한 예측 생성

# 가격 이력 기록
@shared_task(name='products.record_all_price_histories')
def record_all_price_histories():
    # 모든 상품의 최저가를 가격 이력에 기록
```

---

## 4. 프론트엔드 연동

### 4.1 가격 예측 UI 컴포넌트

#### PriceTrendCard
- **예측 가격**: `predicted_price`
- **신뢰도**: `confidence_score` (0-100%)
- **추천도**: `purchase_suitability_score` (0-100%)
- **가이드 메시지**: `purchase_guide_message`

#### PriceTrendGraph
- **최저가 추이**: `price_history` (6/12/24개월)
- **최저가**: 기간 내 최소값
- **최고가**: 기간 내 최대값
- **현재가**: `product.lowest_price` (실시간 최저가)

### 4.2 데이터 타입

```typescript
// Timer 정보
type TimerInfo = {
  timer_id: number;
  product_code: number;
  target_price: number;           // 목표가
  predicted_price: number;         // AI 예측가
  confidence: number;              // 신뢰도 (%)
  recommendation_score: number;    // 추천도 (%)
  reason_message: string;          // 구매 가이드 메시지
  predicted_at: string;           // 예측 일시
};

// 가격 추이
type ProductPriceTrendsResDto = {
  product_code: number;
  product_name: string;
  period_unit: 'month' | 'day';
  selected_period: number;
  price_history: Array<{
    date: string;
    price: number;
  }>;
};
```

---

## 5. 핵심 기술 요약

### 5.1 가격 예측
- ✅ **XGBoost 머신러닝 모델**: 시계열 가격 예측
- ✅ **특징 엔지니어링**: 통계적 특징 + 시간적 특징
- ✅ **신뢰도 계산**: 예측 기간에 따른 동적 신뢰도
- ✅ **구매 적합도 점수**: 목표가 대비 예측가 분석
- ✅ **폴백 메커니즘**: 데이터 부족 시 이동 평균 기반 예측

### 5.2 최저가 추적
- ✅ **실시간 크롤링**: Selenium + BeautifulSoup
- ✅ **가격 이력 관리**: PostgreSQL 기반 시계열 데이터 저장
- ✅ **판매처별 가격 비교**: 다중 쇼핑몰 가격 수집 및 비교
- ✅ **트렌드 분석**: 가격 변동 패턴 분석 (상승/하락/안정)

### 5.3 시스템 아키텍처
- ✅ **비동기 처리**: Celery + RabbitMQ
- ✅ **배치 작업**: 일일 가격 예측 생성, 가격 이력 기록
- ✅ **RESTful API**: Django REST Framework
- ✅ **데이터베이스**: PostgreSQL + pgvector (벡터 검색)

---

## 6. 성능 최적화

### 6.1 모델 최적화
- **윈도우 크기**: 최근 7일 데이터만 사용하여 학습 속도 향상
- **트리 깊이 제한**: `max_depth=3`으로 과적합 방지
- **조기 종료**: 데이터 부족 시 폴백으로 빠른 응답

### 6.2 데이터 최적화
- **인덱싱**: `danawa_product_id`, `recorded_at` 복합 인덱스
- **논리적 삭제**: `deleted_at` 플래그로 데이터 보존
- **캐싱**: Redis를 통한 자주 조회되는 데이터 캐싱

### 6.3 비동기 처리
- **Celery 태스크**: 가격 크롤링, 예측 생성 등 시간 소요 작업 비동기화
- **배치 처리**: 대량 데이터 처리 시 일괄 작업으로 효율성 향상

---

## 7. 향후 개선 방향

1. **모델 고도화**
   - LSTM/GRU 등 딥러닝 모델 적용 검토
   - 외부 요인 (계절성, 이벤트 등) 특징 추가
   - 앙상블 모델로 예측 정확도 향상

2. **실시간 알림**
   - WebSocket을 통한 실시간 가격 변동 알림
   - 목표가 도달 시 즉시 푸시 알림

3. **개인화 추천**
   - 사용자 구매 이력 기반 개인화된 가격 예측
   - 유사 상품 가격 패턴 분석

---

## 참고 파일

- **가격 예측 서비스**: `Backend/modules/timers/services.py`
- **가격 이력 모델**: `Backend/modules/timers/models.py`
- **크롤러**: `Backend/modules/products/crawlers/danawa.py`
- **프론트엔드 컴포넌트**: `Web/src/components/productDetail/PriceTrendCard.tsx`, `PriceTrendGraph.tsx`
