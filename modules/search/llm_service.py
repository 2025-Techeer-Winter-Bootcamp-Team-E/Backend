"""
LLM-based product recommendation service.

Uses hybrid search (HNSW vector + GIN keyword) with Gemini Pro for
intent extraction and recommendation reason generation.
"""
import json
import logging
import re
import difflib
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple

from django.db.models import F
from django.contrib.postgres.search import TrigramSimilarity
from pgvector.django import L2Distance

from modules.products.models import ProductModel, MallInformationModel
from modules.categories.models import CategoryModel
from shared.ai_clients import get_openai_client, get_gemini_client
from .prompts import (
    INTENT_EXTRACTION_PROMPT,
    COMBINED_RECOMMENDATION_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMRecommendationService:
    """Service for LLM-based product recommendations using hybrid search."""

    VECTOR_WEIGHT = 0.7
    KEYWORD_WEIGHT = 0.3
    TOP_K = 5
    SEARCH_LIMIT = 50  # 각 검색에서 가져올 후보 수 (20 → 50)

    _category_cache = []  # Class-level cache for categories

    def __init__(self):
        self.openai_client = get_openai_client()
        self.gemini_client = get_gemini_client()

    def get_recommendations(self, user_query: str) -> Dict[str, Any]:
        """
        메인 진입점: 사용자 쿼리로 상품 추천 수행.

        Args:
            user_query: 자연어 사용자 쿼리

        Returns:
            analysis_message와 추천 상품 5개를 포함한 딕셔너리
        """
        # 1. 의도 추출 (Gemini Pro)
        intent = self._extract_intent(user_query)

        # 1.5 카테고리 매핑 (In-Memory Cache)
        category_id = self._find_matching_category(intent.get('product_category'))
        min_price = intent.get('min_price')
        max_price = intent.get('max_price')

        # 2. 병렬 검색 수행
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_vector = executor.submit(self._vector_search, intent['search_query'], category_id, min_price, max_price)
            future_keyword = executor.submit(self._keyword_search, intent['keywords'], category_id, min_price, max_price)
            
            vector_results = future_vector.result()
            keyword_results = future_keyword.result()

        # 3. 하이브리드 점수 결합
        fused_results = self._fuse_results(vector_results, keyword_results)

        # 4. 결과가 부족하면 대체 검색 수행
        if len(fused_results) < self.SEARCH_LIMIT // 2:
            logger.info(f"Hybrid search returned only {len(fused_results)} results. Running fallback search.")
            # 대체 검색 시에는 카테고리 필터를 완화하거나 제거할 수도 있음 (여기서는 유지)
            fallback_results = self._fallback_search(user_query, intent['keywords'], category_id, min_price, max_price)
            # 기존 결과에 없는 상품만 추가
            existing_ids = {r['product'].danawa_product_id for r in fused_results}
            for result in fallback_results:
                if result['product'].danawa_product_id not in existing_ids:
                    fused_results.append(result)
                    existing_ids.add(result['product'].danawa_product_id)

        # 5. LLM 통합 추천 (재랭킹 + 추천사유 + 리뷰요약) - 속도 개선
        candidate_products = fused_results[:10]  # 상위 10개 후보 (기존 20개에서 축소)
        
        # LLM 호출 (재랭킹)
        recommendation_results = self._rerank_and_analyze(
            user_query=user_query,
            intent=intent,
            candidates=candidate_products
        )
        
        # 분석 메시지는 의도 추출 단계에서 가져온 것을 사용
        analysis_message = intent.get('analysis_message', f"'{user_query}'에 대한 추천 결과입니다.")

        # 7. 최종 응답 구성
        recommended_products = []
        
        # 추천 결과 맵핑
        product_map = {str(p['product'].danawa_product_id): p for p in candidate_products}
        
        for rec_item in recommendation_results:
            p_code = str(rec_item.get('product_code'))
            if p_code not in product_map:
                continue
                
            product_data = product_map[p_code]
            product = product_data['product']
            mall_info = product_data.get('mall_info')
            specs = self._extract_display_specs(product.detail_spec)

            recommended_products.append({
                'product_code': product.danawa_product_id,
                'name': product.name,
                'brand': product.brand,
                'price': product.lowest_price,
                'thumbnail_url': mall_info.representative_image_url if mall_info else None,
                'product_detail_url': mall_info.product_page_url if mall_info else None,
                'recommendation_reason': rec_item.get('recommendation_reason', '추천 상품입니다.'),
                'specs': specs,
                'review_count': product.review_count,
                'review_rating': product.review_rating,
            })

        return {
            'analysis_message': analysis_message,
            'recommended_products': recommended_products
        }

    def _get_descendant_category_ids(self, category_id: int) -> List[int]:
        """하위 카테고리 ID 재귀적 수집"""
        ids = [category_id]
        children = CategoryModel.objects.filter(parent_id=category_id, deleted_at__isnull=True)
        for child in children:
            ids.extend(self._get_descendant_category_ids(child.id))
        return ids

    def _refresh_category_cache(self):
        """Cache all categories in memory."""
        if not self._category_cache:
            try:
                categories = CategoryModel.objects.filter(deleted_at__isnull=True).values('id', 'name')
                self._category_cache = list(categories)
                logger.info(f"Cached {len(self._category_cache)} categories in memory.")
            except Exception as e:
                logger.error(f"Failed to cache categories: {e}")

    def _find_matching_category(self, llm_category_name: str) -> Optional[int]:
        """Find matching category ID using in-memory fuzzy matching."""
        if not self._category_cache:
            self._refresh_category_cache()
        
        if not llm_category_name or llm_category_name == '기타':
            return None

        # Exact match first
        for cat in self._category_cache:
            if cat['name'] == llm_category_name:
                return cat['id']
        
        # Fuzzy match
        category_names = [cat['name'] for cat in self._category_cache]
        matches = difflib.get_close_matches(llm_category_name, category_names, n=1, cutoff=0.4)
        
        if matches:
            matched_name = matches[0]
            for cat in self._category_cache:
                if cat['name'] == matched_name:
                    logger.info(f"LLM category '{llm_category_name}' mapped to DB category '{matched_name}' (ID: {cat['id']})")
                    return cat['id']
        
        return None

    def _extract_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Gemini Pro를 사용하여 사용자 쿼리에서 의도 추출.

        Returns:
            keywords, priorities, search_query, user_needs를 포함한 딕셔너리
        """
        prompt = INTENT_EXTRACTION_PROMPT.format(user_query=user_query)

        try:
            response = self.gemini_client.generate_content(prompt)

            # JSON 파싱 시도
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                intent = json.loads(json_match.group())
            else:
                intent = json.loads(response)

            # 필수 필드 검증 및 기본값 설정
            return {
                'product_category': intent.get('product_category', '노트북'),
                'keywords': intent.get('keywords', [user_query]),
                'priorities': intent.get('priorities', {
                    'portability': 5,
                    'performance': 5,
                    'price': 5,
                    'display': 5,
                    'battery': 5
                }),
                'search_query': intent.get('search_query', user_query),
                'min_price': intent.get('min_price'),
                'max_price': intent.get('max_price'),
                'user_needs': intent.get('user_needs', user_query),
                'analysis_message': intent.get('analysis_message', f"'{user_query}'에 대한 분석 결과입니다.")
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Intent extraction failed: {e}. Using fallback.")
            return {
                'product_category': '노트북',
                'keywords': [user_query],
                'priorities': {
                    'portability': 5,
                    'performance': 5,
                    'price': 5,
                    'display': 5,
                    'battery': 5
                },
                'search_query': user_query,
                'min_price': None,
                'max_price': None,
                'user_needs': user_query,
                'analysis_message': f"'{user_query}'에 대한 추천 결과입니다."
            }

    def _vector_search(
        self, 
        search_query: str,
        category_id: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        HNSW 벡터 검색 수행.

        Args:
            search_query: 벡터 검색용 자연어 쿼리

        Returns:
            상품 및 점수 정보를 포함한 리스트
        """
        # 쿼리 임베딩 생성 (OpenAI text-embedding-3-small)
        query_embedding = self.openai_client.create_embedding(search_query)

        queryset = ProductModel.objects.filter(
            deleted_at__isnull=True,
            detail_spec_vector__isnull=False
        )

        # 필터 적용
        if category_id:
            category_ids = self._get_descendant_category_ids(category_id)
            queryset = queryset.filter(category_id__in=category_ids)
        if min_price:
            queryset = queryset.filter(lowest_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(lowest_price__lte=max_price)

        # HNSW 벡터 검색 (CosineDistance - 텍스트 임베딩에 더 적합)
        products = queryset.exclude(
            product_status__in=['단종', '판매중지', '품절']  # 실제로 구매 불가능한 상태만 제외
        ).annotate(
            distance=L2Distance('detail_spec_vector', query_embedding)
        ).order_by('distance')[:self.SEARCH_LIMIT]

        products = list(products)
        product_ids = [p.id for p in products]

        # N+1 문제를 해결하기 위해 한 번의 쿼리로 모든 mall_info를 가져옵니다.
        mall_infos = MallInformationModel.objects.filter(
            product_id__in=product_ids,
            deleted_at__isnull=True
        ).order_by('product_id', '-created_at').distinct('product_id')
        mall_info_map = {mi.product_id: mi for mi in mall_infos}

        results = []
        for product in products:
            # Cosine 거리를 유사도 점수로 변환 (0~1 범위)
            # Cosine 거리: 0 = 완전 일치, 2 = 완전 반대
            # 유사도 = 1 - (distance / 2)
            similarity = max(0.0, 1.0 - (product.distance / 2.0))
            mall_info = mall_info_map.get(product.id)

            results.append({
                'product': product,
                'mall_info': mall_info,
                'vector_score': similarity,
                'keyword_score': 0.0
            })
        return results

    def _keyword_search(
        self, 
        keywords: List[str],
        category_id: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        GIN trigram 키워드 검색 수행.

        Args:
            keywords: 검색 키워드 리스트

        Returns:
            상품 및 점수 정보를 포함한 리스트
        """
        if not keywords:
            return []

        # 키워드를 공백으로 연결하여 검색 쿼리 생성
        search_text = ' '.join(keywords)

        queryset = ProductModel.objects.filter(deleted_at__isnull=True)

        # 필터 적용
        if category_id:
            category_ids = self._get_descendant_category_ids(category_id)
            queryset = queryset.filter(category_id__in=category_ids)
        if min_price:
            queryset = queryset.filter(lowest_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(lowest_price__lte=max_price)

        # GIN Trigram 유사도 검색
        # product_status 필터를 완화하여 구매 불가능한 상태만 제외
        products = queryset.exclude(
            product_status__in=['단종', '판매중지', '품절']
        ).annotate(
            name_similarity=TrigramSimilarity('name', search_text),
            brand_similarity=TrigramSimilarity('brand', search_text)
        ).annotate(
            # name과 brand 유사도의 가중 평균
            total_similarity=F('name_similarity') * 0.7 + F('brand_similarity') * 0.3
        ).filter(
            total_similarity__gt=0.05  # 임계값을 낮춤 (0.1 → 0.05)
        ).order_by('-total_similarity')[:self.SEARCH_LIMIT]

        products = list(products)
        product_ids = [p.id for p in products]

        # N+1 문제를 해결하기 위해 한 번의 쿼리로 모든 mall_info를 가져옵니다.
        mall_infos = MallInformationModel.objects.filter(
            product_id__in=product_ids,
            deleted_at__isnull=True
        ).order_by('product_id', '-created_at').distinct('product_id')
        mall_info_map = {mi.product_id: mi for mi in mall_infos}

        results = []
        for product in products:
            results.append({
                'product': product,
                'mall_info': mall_info_map.get(product.id),
                'vector_score': 0.0,
                'keyword_score': float(product.total_similarity)
            })

        return results

    def _fallback_search(
        self, 
        user_query: str, 
        keywords: List[str],
        category_id: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 결과가 부족할 때 대체 검색 수행.

        단순 icontains 검색으로 상품명/브랜드에서 키워드 포함 여부 확인.
        """
        from django.db.models import Q

        # 키워드 기반 Q 객체 생성
        q_filter = Q()
        search_terms = keywords + user_query.split()

        for term in search_terms:
            if len(term) >= 2:  # 2글자 이상만
                q_filter |= Q(name__icontains=term) | Q(brand__icontains=term)

        if not q_filter:
            return []

        queryset = ProductModel.objects.filter(q_filter, deleted_at__isnull=True)

        # 필터 적용
        if category_id:
            category_ids = self._get_descendant_category_ids(category_id)
            queryset = queryset.filter(category_id__in=category_ids)
        if min_price:
            queryset = queryset.filter(lowest_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(lowest_price__lte=max_price)

        products = queryset.exclude(
            product_status__in=['단종', '판매중지', '품절']
        ).order_by('-review_count', '-review_rating')[:self.SEARCH_LIMIT]

        products = list(products)
        product_ids = [p.id for p in products]

        # N+1 문제를 해결하기 위해 한 번의 쿼리로 모든 mall_info를 가져옵니다.
        mall_infos = MallInformationModel.objects.filter(
            product_id__in=product_ids,
            deleted_at__isnull=True
        ).order_by('product_id', '-created_at').distinct('product_id')
        mall_info_map = {mi.product_id: mi for mi in mall_infos}

        results = []
        for product in products:
            results.append({
                'product': product,
                'mall_info': mall_info_map.get(product.id),
                'vector_score': 0.3,  # 대체 검색은 중간 점수 부여
                'keyword_score': 0.3,
                'combined_score': 0.3
            })

        return results

    def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        벡터 검색과 키워드 검색 결과를 하이브리드 점수로 결합.

        combined_score = 0.7 * vector_score + 0.3 * keyword_score

        Returns:
            combined_score 기준 내림차순 정렬된 결과 리스트
        """
        # 상품 ID를 키로 하는 딕셔너리로 변환
        results_map: Dict[str, Dict[str, Any]] = {}

        # 벡터 검색 결과 추가
        for item in vector_results:
            product_id = item['product'].danawa_product_id
            results_map[product_id] = {
                'product': item['product'],
                'mall_info': item['mall_info'],
                'vector_score': item['vector_score'],
                'keyword_score': 0.0
            }

        # 키워드 검색 결과 병합
        for item in keyword_results:
            product_id = item['product'].danawa_product_id
            if product_id in results_map:
                results_map[product_id]['keyword_score'] = item['keyword_score']
            else:
                results_map[product_id] = {
                    'product': item['product'],
                    'mall_info': item['mall_info'],
                    'vector_score': 0.0,
                    'keyword_score': item['keyword_score']
                }

        # 하이브리드 점수 계산
        fused_results = []
        for product_id, data in results_map.items():
            combined_score = (
                self.VECTOR_WEIGHT * data['vector_score'] +
                self.KEYWORD_WEIGHT * data['keyword_score']
            )
            fused_results.append({
                **data,
                'combined_score': combined_score
            })

        # combined_score 기준 내림차순 정렬
        fused_results.sort(key=lambda x: (
            x['combined_score'],
            x['product'].review_count,
            x['product'].review_rating or 0
        ), reverse=True)

        return fused_results

    def _rerank_and_analyze(
        self,
        user_query: str,
        intent: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        LLM을 사용하여 검색 결과 재랭킹 및 분석 (통합 처리).
        가장 적합한 3~5개 상품을 선택하고 추천 사유를 생성함.
        """
        # 상품 목록 문자열 생성
        product_list_items = []
        for i, item in enumerate(candidates, 1):
            product = item['product']
            specs = self._extract_display_specs(product.detail_spec)

            spec_parts = []
            if specs.get('weight'):
                spec_parts.append(f"무게:{specs['weight']}")
            if specs.get('cpu'):
                spec_parts.append(f"CPU:{specs['cpu']}")
            if specs.get('ram'):
                spec_parts.append(f"RAM:{specs['ram']}")
            if specs.get('display'):
                spec_parts.append(f"화면:{specs['display']}")

            spec_str = ", ".join(spec_parts) if spec_parts else "스펙 정보 없음"

            product_list_items.append(
                f"- 상품코드: {product.danawa_product_id}\n"
                f"   상품명: [{product.brand}] {product.name}\n"
                f"   가격: {product.lowest_price:,}원 | 리뷰: {product.review_count}개 | 평점: {product.review_rating or 'N/A'}\n"
                f"   스펙: {spec_str}"
            )

        product_list = "\n".join(product_list_items)
        
        prompt = COMBINED_RECOMMENDATION_PROMPT.format(
            user_query=user_query,
            product_category=intent.get('product_category', '노트북'),
            user_needs=intent.get('user_needs', user_query),
            product_list=product_list
        )

        try:
            response = self.gemini_client.generate_content(prompt)

            # JSON 파싱
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)

            results = result.get('results', [])
            logger.info(f"LLM selected {len(results)} products")
            return results

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"LLM reranking/analysis failed: {e}. Returning empty list.")
            return []

    def _extract_display_specs(self, detail_spec: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        detail_spec JSON에서 주요 스펙 추출.

        Args:
            detail_spec: 상품의 상세 스펙 JSON

        Returns:
            cpu, ram, storage, display, weight, gpu, battery를 포함한 딕셔너리
        """
        specs = {
            'cpu': None,
            'ram': None,
            'storage': None,
            'display': None,
            'weight': None,
            'gpu': None,
            'battery': None
        }

        if not detail_spec:
            return specs

        spec_data = detail_spec.get('spec', {})
        spec_summary = detail_spec.get('spec_summary', [])

        # spec_summary에서 추출 시도
        for item in spec_summary:
            item_lower = str(item).lower()

            # 무게 추출 (예: "1.86kg")
            if 'kg' in item_lower and not specs['weight']:
                specs['weight'] = str(item)

            # 화면 크기 추출 (예: "40.6cm(16인치)")
            elif ('cm' in item_lower or '인치' in item_lower) and not specs['display']:
                specs['display'] = str(item)

            # RAM 추출 (예: "[구성]램:32GB")
            elif '램' in item_lower or 'ram' in item_lower:
                if ':' in str(item):
                    specs['ram'] = str(item).split(':')[-1].strip()
                else:
                    specs['ram'] = str(item)

            # 저장장치 추출 (예: "용량:1TB")
            elif 'tb' in item_lower or 'ssd' in item_lower:
                if ':' in str(item):
                    specs['storage'] = str(item).split(':')[-1].strip()
                else:
                    specs['storage'] = str(item)

        # spec 딕셔너리에서 추가 추출
        for key, value in spec_data.items():
            key_lower = key.lower()

            # CPU 추출
            if ('코어' in key_lower or 'core' in key_lower or
                'i7' in key_lower or 'i5' in key_lower or 'i9' in key_lower or
                'ryzen' in key_lower or '울트라' in key_lower):
                if not specs['cpu']:
                    specs['cpu'] = key if value is True else str(value)

            # GPU 추출
            elif ('rtx' in key_lower or 'gtx' in key_lower or
                  '지포스' in key_lower or 'radeon' in key_lower):
                if not specs['gpu']:
                    specs['gpu'] = key if value is True else str(value)

            # 배터리 추출
            elif '배터리' in key_lower or 'wh' in key_lower:
                if not specs['battery']:
                    specs['battery'] = key if value is True else str(value)

            # RAM 추출 (spec 딕셔너리에서)
            elif '[구성]램' in key:
                if not specs['ram']:
                    specs['ram'] = str(value)

            # 용량/저장장치 추출
            elif '용량' in key:
                if not specs['storage']:
                    specs['storage'] = str(value)

            # 해상도 추출
            elif '해상도' in key:
                if specs['display']:
                    specs['display'] = f"{specs['display']} ({value})"
                else:
                    specs['display'] = str(value)

        return specs
