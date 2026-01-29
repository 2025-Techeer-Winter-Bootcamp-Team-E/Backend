# AI 쇼핑 리서치 (2단계 맞춤형 상품 추천)

## 개요

AI 쇼핑 리서치는 **2단계 프로세스**를 통해 사용자의 니즈를 정확히 파악하고 최적의 상품을 추천하는 시스템입니다. **Google Gemini**와 **OpenAI Embedding**을 활용하여 맞춤형 질문을 생성하고, **pgvector** 기반 벡터 검색으로 유사도가 높은 상품을 추천합니다.

---

## 1. 시스템 아키텍처

### 1.1 2단계 프로세스

```
[Step 1: 질문 생성]
사용자 쿼리 → Gemini AI → 맞춤형 질문 4개 생성 → 사용자 설문 응답

[Step 2: 상품 추천]
설문 응답 → Gemini AI (의도 분석) → 벡터 검색 → 상품 분석 → 최종 추천 5개
```

### 1.2 기술 스택

- **질문 생성**: Google Gemini 2.0 Flash
- **의도 분석**: Google Gemini 2.0 Flash
- **벡터 검색**: OpenAI Embedding (text-embedding-3-small, 1536차원)
- **벡터 DB**: PostgreSQL + pgvector (HNSW 인덱스)
- **상품 분석**: Google Gemini 2.0 Flash (일괄 처리)
- **캐싱**: Redis (30분 TTL)

---

## 2. Step 1: 맞춤형 질문 생성

### 2.1 프로세스

```python
def generate_questions(user_query: str) -> Dict[str, Any]:
    """
    1. 검색 ID 생성 (UUID 기반)
    2. Gemini에게 사용자 쿼리 전달
    3. 카테고리별 최적화된 질문 4개 생성
    4. JSON 파싱 및 검증
    """
```

### 2.2 질문 생성 프롬프트 전략

#### 카테고리 분석
- **완제품** (노트북, 태블릿): 용도, 예산, 핵심 스펙, 휴대성/환경
- **PC 부품** (GPU, CPU): 용도, 예산, 성능 지표, 호환성/환경
- **주변기기** (모니터, 마우스): 용도, 예산, 핵심 스펙, 설치 환경

#### 질문 구성 원칙
1. **논리적 일관성**: 부품 검색 시 완제품 관련 질문 제외
   - 예: 그래픽카드 검색 시 "휴대성", "OS" 질문 금지
   - 대신: "파워 용량", "CPU 병목", "케이스 공간", "모니터 해상도"

2. **질문 1 (용도)**: 카테고리별 구체적 활용 수준
   - 노트북: "일반 업무", "영상 편집", "게임", "개발"
   - 그래픽카드: "게임", "영상 편집", "AI 학습", "마이닝"

3. **질문 2 (예산)**: 시장 시세에 맞는 현실적 가격대
   - 노트북: "100만원 미만", "100~150만원", "150~200만원", "200만원 이상"
   - 그래픽카드: "30만원 미만", "30~50만원", "50~80만원", "80만원 이상"

4. **질문 3 (핵심 스펙)**: 성능을 결정짓는 기술적 지표
   - 노트북: "CPU 성능", "그래픽카드", "RAM 용량", "저장공간"
   - 모니터: "해상도", "주사율", "색재현율", "크기"

5. **질문 4 (환경/제약)**: 물리적 제약 사항
   - 노트북: "휴대성", "배터리", "화면 크기"
   - 그래픽카드: "케이스 크기", "파워 용량", "소음"

### 2.3 폴백 메커니즘

Gemini API 실패 시 기본 질문 세트 사용:
```python
def _get_default_questions() -> List[Dict[str, Any]]:
    return [
        {
            "question_id": 1,
            "question": "주요 사용 목적은 무엇인가요?",
            "options": ["일반 업무", "영상 편집", "게임", "개발"]
        },
        # ... (4개 질문)
    ]
```

### 2.4 응답 형식

```json
{
  "search_id": "sr-xxxxxxxx",
  "questions": [
    {
      "question_id": 1,
      "question": "주요 사용 목적은 무엇인가요?",
      "options": [
        {"id": 1, "label": "일반 업무"},
        {"id": 2, "label": "영상 편집"},
        ...
      ]
    }
  ]
}
```

---

## 3. Step 2: 상품 추천

### 3.1 전체 프로세스

```python
def get_recommendations(
    search_id: str,
    user_query: str,
    survey_contents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    1. 설문 응답 분석 (Gemini)
    2. 카테고리 매핑 (TrigramSimilarity)
    3. 벡터 검색 (pgvector)
    4. 유사도 필터링 (60% 이상)
    5. 상위 5개 선택
    6. 일괄 상품 분석 (Gemini)
    7. 최종 추천 결과 구성
    """
```

### 3.2 설문 응답 분석

#### Gemini 프롬프트
```python
SHOPPING_RESEARCH_ANALYSIS_PROMPT = """
사용자 원래 검색: "{user_query}"
설문 응답: {survey_responses}

다음 JSON 형식으로 응답:
{
    "product_category": "카테고리명",
    "search_query": "벡터 검색용 쿼리",
    "keywords": ["키워드1", "키워드2"],
    "priorities": {
        "portability": 0-10,
        "performance": 0-10,
        "price": 0-10,
        "display": 0-10,
        "battery": 0-10
    },
    "min_price": 0,
    "max_price": 0,
    "user_needs": "사용자 니즈 요약"
}
"""
```

#### 추출된 의도 (Intent)
```python
intent = {
    'product_category': str,      # 예: "노트북", "그래픽카드"
    'search_query': str,          # 벡터 검색용 최적화 쿼리
    'keywords': List[str],        # 핵심 키워드 목록
    'priorities': Dict[str, int], # 우선순위 점수 (0-10)
    'min_price': int | None,      # 최소 예산
    'max_price': int | None,      # 최대 예산
    'user_needs': str             # 사용자 니즈 요약
}
```

### 3.3 카테고리 매핑

#### TrigramSimilarity를 활용한 유사 카테고리 검색
```python
# LLM이 추출한 카테고리명을 DB 카테고리와 매핑
best_match = CategoryModel.objects.annotate(
    similarity=TrigramSimilarity('name', llm_category_name)
).filter(similarity__gt=0.3).order_by('-similarity').first()

if best_match:
    category_id = best_match.id
    # 하위 카테고리까지 포함 (재귀적)
    category_ids = self._get_descendant_category_ids(category_id)
```

#### 재귀적 하위 카테고리 수집
```python
def _get_descendant_category_ids(category_id: int) -> List[int]:
    """모든 자식 카테고리 ID를 재귀적으로 수집"""
    ids = [category_id]
    children = CategoryModel.objects.filter(
        parent_id=category_id,
        deleted_at__isnull=True
    )
    for child in children:
        ids.extend(self._get_descendant_category_ids(child.id))
    return ids
```

### 3.4 벡터 검색 (pgvector)

#### Embedding 생성
```python
# OpenAI Embedding API 호출
query_embedding = self.openai_client.create_embedding(search_query)
# 모델: text-embedding-3-small
# 차원: 1536
```

#### 벡터 검색 쿼리
```python
products = ProductModel.objects.filter(
    deleted_at__isnull=True,
    detail_spec_vector__isnull=False,  # 벡터가 있는 상품만
    category_id__in=category_ids,       # 카테고리 필터
    lowest_price__gte=min_price,        # 최소 가격 필터
    lowest_price__lte=max_price         # 최대 가격 필터
).exclude(
    product_status__in=['단종', '판매중지', '품절']  # 판매 중지 제품 제외
).annotate(
    distance=CosineDistance('detail_spec_vector', query_embedding)
).order_by('distance')[:SEARCH_LIMIT]  # 상위 50개
```

#### 유사도 계산
```python
# Cosine Distance를 유사도로 변환 (0.0 ~ 1.0)
similarity = max(0.0, 1.0 - (product.distance / 2.0))
```

### 3.5 결과 융합 (Fusion)

#### 하이브리드 스코어링
```python
def _fuse_results(vector_results: List[Dict]) -> List[Dict]:
    """
    현재는 벡터 검색만 사용 (VECTOR_WEIGHT = 1.0)
    향후 키워드 검색 추가 가능
    """
    combined_score = VECTOR_WEIGHT * vector_score
    
    # 정렬 기준:
    # 1. combined_score (내림차순)
    # 2. review_count (내림차순)
    # 3. review_rating (내림차순)
    fused_results.sort(key=lambda x: (
        x['combined_score'],
        x['product'].review_count,
        x['product'].review_rating or 0
    ), reverse=True)
```

### 3.6 유사도 필터링

```python
# 최소 유사도 임계값: 60%
MIN_SIMILARITY = 0.60

high_similarity_results = [
    r for r in fused_results 
    if r['combined_score'] >= MIN_SIMILARITY
]

# 60% 이상 상품이 5개 미만이면 상위 5개 사용 (유사도 무관)
if len(high_similarity_results) < TOP_K:
    high_similarity_results = fused_results[:TOP_K]
```

### 3.7 상품 분석 (일괄 처리)

#### 배치 분석 최적화
```python
def _batch_analyze_products(
    user_query: str,
    user_needs: str,
    products: List[Dict]
) -> Dict[str, Dict[str, str]]:
    """
    5개 상품을 한 번에 Gemini에게 전달하여
    추천 사유와 리뷰 요약을 일괄 생성
    (API 호출 횟수: 5회 → 1회로 최적화)
    """
    products_info = "\n\n".join([
        f"- 상품코드: {product.danawa_product_id}\n"
        f"  상품명: {product.name}\n"
        f"  브랜드: {product.brand}\n"
        f"  가격: {product.lowest_price:,}원\n"
        f"  스펙: {specs_str}"
        for product in products
    ])
    
    prompt = BATCH_PRODUCT_ANALYSIS_PROMPT.format(
        user_query=user_query,
        user_needs=user_needs,
        products_info=products_info
    )
    
    response = self.gemini_client.generate_content(prompt)
    # JSON 파싱하여 상품별 분석 결과 맵 반환
    return analysis_map  # {product_code: {recommendation_reason, ai_review_summary}}
```

#### 개별 상품 분석 (Fallback)
```python
def _analyze_product(...) -> Dict[str, Any]:
    """
    배치 분석 결과가 없으면 개별 Gemini 호출
    (추천 사유 + 리뷰 요약)
    """
    if pre_analysis:
        # 배치 분석 결과 사용
        recommendation_reason = pre_analysis.get('recommendation_reason')
        ai_review_summary = pre_analysis.get('ai_review_summary')
    else:
        # 개별 호출
        recommendation_reason = self._generate_recommendation_reason(...)
        ai_review_summary = self._generate_ai_review_summary(...)
```

### 3.8 최종 추천 결과 구성

```python
{
    "similarity_score": 0.85,              # 유사도 점수 (0.0-1.0)
    "product_image_url": "...",            # 대표 이미지 URL
    "product_name": "상품명",
    "product_code": 12345678,              # 다나와 상품 코드
    "recommendation_reason": "추천 사유",   # Gemini 생성
    "price": 1500000,                      # 최저가
    "performance_score": 0.92,             # 성능 점수 (0.0-1.0)
    "product_specs": {
        "summary": "스펙 요약"              # spec_summary 리스트를 텍스트로 변환
    },
    "ai_review_summary": "리뷰 요약",       # Gemini 생성
    "product_detail_url": "...",           # 상품 상세 페이지 URL
    "optimal_product_info": {
        "match_rank": 1,                   # 추천 순위 (1-5)
        "is_lowest_price": true            # 최저가 여부
    }
}
```

---

## 4. 핵심 기술 상세

### 4.1 벡터 검색 (pgvector)

#### HNSW 인덱스
```sql
-- PostgreSQL에서 HNSW 인덱스 생성
CREATE INDEX products_detail_spec_vector_hnsw_idx
ON products USING hnsw (detail_spec_vector vector_l2_ops);
```

#### Cosine Distance 계산
```python
from pgvector.django import CosineDistance

# Cosine Distance = 1 - Cosine Similarity
# 유사도 변환: similarity = 1 - (distance / 2.0)
distance = CosineDistance('detail_spec_vector', query_embedding)
```

#### 벡터 차원
- **모델**: OpenAI `text-embedding-3-small`
- **차원**: 1536
- **저장 필드**: `ProductModel.detail_spec_vector` (VectorField)

### 4.2 성능 점수 계산

```python
def _calculate_performance_score(
    product: ProductModel,
    combined_score: float
) -> float:
    """
    성능 점수 = 유사도 점수 (0.0-1.0)
    향후 리뷰 평점, 리뷰 수 등을 가중치로 추가 가능
    """
    return combined_score
```

### 4.3 최저가 판단

```python
# 상위 5개 상품 중 최저가인지 확인
all_prices = [p['product'].lowest_price for p in top_products]
is_lowest_price = product.lowest_price == min(all_prices)
```

### 4.4 캐싱 전략

```python
# 검색 세션 캐싱 (30분 TTL)
CACHE_TTL = 1800  # 30 minutes

# 검색 ID 생성 및 캐싱
search_id = f"sr-{uuid.uuid4().hex[:8]}"
cache_key = f"shopping_research:{search_id}"
cache.set(cache_key, {
    "user_query": user_query,
    "questions": questions
}, timeout=CACHE_TTL)
```

---

## 5. API 엔드포인트

### 5.1 질문 생성 API

**POST** `/api/v1/search/questions/`

**Request:**
```json
{
  "user_query": "노트북 추천해줘"
}
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "search_id": "sr-xxxxxxxx",
    "questions": [...]
  }
}
```

### 5.2 상품 추천 API

**POST** `/api/v1/search/shopping-research/`

**Request:**
```json
{
  "search_id": "sr-xxxxxxxx",
  "user_query": "노트북 추천해줘",
  "survey_contents": [
    {
      "question_id": 1,
      "question": "주요 사용 목적은 무엇인가요?",
      "answer": "영상 편집"
    },
    ...
  ]
}
```

**Response:**
```json
{
  "status": 200,
  "message": "쇼핑 리서치 결과 분석 성공 (상위 5개 상품)",
  "data": {
    "user_query": "노트북 추천해줘",
    "product": [
      {
        "similarity_score": 0.85,
        "product_name": "...",
        "product_code": 12345678,
        "recommendation_reason": "...",
        "price": 1500000,
        ...
      },
      ... (최대 5개)
    ]
  }
}
```

---

## 6. 프롬프트 엔지니어링

### 6.1 질문 생성 프롬프트

**핵심 전략:**
- 카테고리별 맞춤형 질문 생성
- 논리적 일관성 보장 (부품 vs 완제품 구분)
- 현실적인 예산 옵션 제공
- JSON 형식 엄격 준수

### 6.2 의도 분석 프롬프트

**핵심 전략:**
- 설문 응답에서 카테고리, 예산, 우선순위 추출
- 벡터 검색용 최적화된 쿼리 생성
- 사용자 니즈 요약

### 6.3 상품 분석 프롬프트

**핵심 전략:**
- 일괄 처리로 API 호출 최소화 (5회 → 1회)
- 구체적 스펙 인용 (모호한 표현 지양)
- 사용자 상황과 스펙 연결
- 존댓말 사용

---

## 7. 성능 최적화

### 7.1 API 호출 최적화

#### Before (개별 호출)
```
상품 1: Gemini 호출 (추천 사유)
상품 2: Gemini 호출 (추천 사유)
상품 3: Gemini 호출 (추천 사유)
상품 4: Gemini 호출 (추천 사유)
상품 5: Gemini 호출 (추천 사유)
→ 총 5회 호출
```

#### After (일괄 처리)
```
상품 1-5: Gemini 호출 1회 (일괄 분석)
→ 총 1회 호출 (80% 감소)
```

### 7.2 벡터 검색 최적화

- **HNSW 인덱스**: 빠른 근사 최근접 이웃 검색
- **하드 필터링**: 카테고리, 가격 범위로 사전 필터링
- **검색 제한**: 상위 50개만 조회 후 유사도 필터링

### 7.3 캐싱

- **검색 세션**: 30분 TTL로 재검색 시 질문 재사용
- **Redis**: 빠른 조회 성능

---

## 8. 에러 처리 및 폴백

### 8.1 질문 생성 실패
- **폴백**: 기본 질문 세트 사용
- **로깅**: 에러 원인 상세 기록

### 8.2 Embedding 생성 실패
- **폴백**: 빈 결과 반환
- **에러 처리**: OpenAI API 키 검증

### 8.3 Gemini API 실패
- **폴백**: 개별 상품 분석으로 전환
- **에러 처리**: JSON 파싱 실패 시 재시도

### 8.4 검색 결과 없음
- **응답**: 빈 배열 반환
- **로깅**: 필터 조건과 쿼리 기록

---

## 9. 주요 파라미터

```python
class ShoppingResearchService:
    CACHE_TTL = 1800          # 캐시 TTL (30분)
    TOP_K = 5                 # 추천 상품 개수
    SEARCH_LIMIT = 50         # 벡터 검색 상위 N개
    VECTOR_WEIGHT = 1.0       # 벡터 점수 가중치
    MIN_SIMILARITY = 0.60     # 최소 유사도 임계값 (60%)
```

---

## 10. 향후 개선 방향

1. **하이브리드 검색 강화**
   - 키워드 검색 추가 (BM25, TF-IDF)
   - 벡터 + 키워드 융합 점수 최적화

2. **개인화 추천**
   - 사용자 구매 이력 기반 가중치
   - 선호 브랜드/카테고리 학습

3. **실시간 가격 비교**
   - 최저가 알림 통합
   - 가격 변동 추적

4. **다중 모델 앙상블**
   - 여러 LLM 모델 결과 비교
   - 신뢰도 기반 가중 평균

---

## 참고 파일

- **쇼핑 리서치 서비스**: `Backend/modules/search/shopping_research_service.py`
- **프롬프트 템플릿**: `Backend/modules/search/prompts.py`
- **API 뷰**: `Backend/modules/search/views.py`
- **프론트엔드**: `Web/src/pages/ShoppingResearchPage.tsx`, `ShoppingResearchResultPage.tsx`
