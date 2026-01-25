"""
LLM-based product recommendation service.

Uses hybrid search (HNSW vector + GIN keyword) with Gemini Pro for
intent extraction and recommendation reason generation.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from django.db.models import F
from django.contrib.postgres.search import TrigramSimilarity
from pgvector.django import L2Distance, CosineDistance

from modules.products.models import ProductModel, MallInformationModel
from shared.ai_clients import get_openai_client, get_gemini_client
from .prompts import (
    INTENT_EXTRACTION_PROMPT,
    ANALYSIS_MESSAGE_PROMPT,
    RECOMMENDATION_REASON_PROMPT,
    RERANKING_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMRecommendationService:
    """Service for LLM-based product recommendations using hybrid search."""

    VECTOR_WEIGHT = 0.7
    KEYWORD_WEIGHT = 0.3
    TOP_K = 5
    SEARCH_LIMIT = 50  # 각 검색에서 가져올 후보 수 (20 → 50)

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

        # 2. 병렬 검색 수행
        vector_results = self._vector_search(intent['search_query'])
        keyword_results = self._keyword_search(intent['keywords'])

        # 3. 하이브리드 점수 결합
        fused_results = self._fuse_results(vector_results, keyword_results)

        # 4. 결과가 부족하면 대체 검색 수행
        if len(fused_results) < self.SEARCH_LIMIT // 2:
            logger.info(f"Hybrid search returned only {len(fused_results)} results. Running fallback search.")
            fallback_results = self._fallback_search(user_query, intent['keywords'])
            # 기존 결과에 없는 상품만 추가
            existing_ids = {r['product'].danawa_product_id for r in fused_results}
            for result in fallback_results:
                if result['product'].danawa_product_id not in existing_ids:
                    fused_results.append(result)
                    existing_ids.add(result['product'].danawa_product_id)

        # 5. LLM 재랭킹 - 검색 결과 중 사용자 요청에 가장 적합한 상품 선택
        candidate_products = fused_results[:20]  # 상위 20개 후보
        if len(candidate_products) > self.TOP_K:
            top_products = self._rerank_with_llm(
                user_query=user_query,
                intent=intent,
                candidates=candidate_products
            )
        else:
            top_products = candidate_products[:self.TOP_K]

        # 5. 분석 메시지 생성 (Gemini Pro)
        analysis_message = self._generate_analysis_message(
            user_query=user_query,
            user_needs=intent['user_needs'],
            priorities=intent['priorities'],
            product_count=len(top_products)
        )

        # 6. 상품별 추천 사유 생성 및 응답 구성
        recommended_products = []
        for product_data in top_products:
            product = product_data['product']
            mall_info = product_data.get('mall_info')
            specs = self._extract_display_specs(product.detail_spec)

            # 추천 사유 생성 (Gemini Pro)
            recommendation_reason = self._generate_recommendation_reason(
                user_query=user_query,
                user_needs=intent['user_needs'],
                product_name=product.name,
                brand=product.brand,
                price=product.lowest_price,
                specs=specs
            )

            recommended_products.append({
                'product_code': product.danawa_product_id,
                'name': product.name,
                'brand': product.brand,
                'price': product.lowest_price,
                'thumbnail_url': mall_info.representative_image_url if mall_info else None,
                'product_detail_url': mall_info.product_page_url if mall_info else None,
                'recommendation_reason': recommendation_reason,
                'specs': specs,
                'review_count': product.review_count,
                'review_rating': product.review_rating,
            })

        return {
            'analysis_message': analysis_message,
            'recommended_products': recommended_products
        }

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
                'user_needs': intent.get('user_needs', user_query)
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
                'user_needs': user_query
            }

    def _vector_search(self, search_query: str) -> List[Dict[str, Any]]:
        """
        HNSW 벡터 검색 수행.

        Args:
            search_query: 벡터 검색용 자연어 쿼리

        Returns:
            상품 및 점수 정보를 포함한 리스트
        """
        # 쿼리 임베딩 생성 (OpenAI text-embedding-3-small)
        query_embedding = self.openai_client.create_embedding(search_query)

        # HNSW 벡터 검색 (CosineDistance - 텍스트 임베딩에 더 적합)
        # product_status 필터를 완화하여 '판매중'을 포함하는 모든 상태 허용
        products = ProductModel.objects.filter(
            deleted_at__isnull=True,
            detail_spec_vector__isnull=False
        ).exclude(
            product_status__in=['단종', '판매중지', '품절']  # 실제로 구매 불가능한 상태만 제외
        ).annotate(
            distance=CosineDistance('detail_spec_vector', query_embedding)
        ).order_by('distance')[:self.SEARCH_LIMIT]

        results = []
        for product in products:
            # Cosine 거리를 유사도 점수로 변환 (0~1 범위)
            # Cosine 거리: 0 = 완전 일치, 2 = 완전 반대
            # 유사도 = 1 - (distance / 2)
            similarity = max(0.0, 1.0 - (product.distance / 2.0))

            # mall_information 조회
            mall_info = MallInformationModel.objects.filter(
                product=product,
                deleted_at__isnull=True
            ).first()

            results.append({
                'product': product,
                'mall_info': mall_info,
                'vector_score': similarity,
                'keyword_score': 0.0
            })

        return results

    def _keyword_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
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

        # GIN Trigram 유사도 검색
        # product_status 필터를 완화하여 구매 불가능한 상태만 제외
        products = ProductModel.objects.filter(
            deleted_at__isnull=True
        ).exclude(
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

        results = []
        for product in products:
            mall_info = MallInformationModel.objects.filter(
                product=product,
                deleted_at__isnull=True
            ).first()

            results.append({
                'product': product,
                'mall_info': mall_info,
                'vector_score': 0.0,
                'keyword_score': float(product.total_similarity)
            })

        return results

    def _fallback_search(self, user_query: str, keywords: List[str]) -> List[Dict[str, Any]]:
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

        products = ProductModel.objects.filter(
            q_filter,
            deleted_at__isnull=True
        ).exclude(
            product_status__in=['단종', '판매중지', '품절']
        ).order_by('-review_count', '-review_rating')[:self.SEARCH_LIMIT]

        results = []
        for product in products:
            mall_info = MallInformationModel.objects.filter(
                product=product,
                deleted_at__isnull=True
            ).first()

            results.append({
                'product': product,
                'mall_info': mall_info,
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

    def _rerank_with_llm(
        self,
        user_query: str,
        intent: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        LLM을 사용하여 검색 결과 재랭킹.

        검색된 후보 상품 중 사용자 요청에 가장 적합한 5개를 선택.
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
                f"{i}. [{product.brand}] {product.name}\n"
                f"   가격: {product.lowest_price:,}원 | 리뷰: {product.review_count}개 | 평점: {product.review_rating or 'N/A'}\n"
                f"   스펙: {spec_str}"
            )

        product_list = "\n".join(product_list_items)

        prompt = RERANKING_PROMPT.format(
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

            selected_indices = result.get('selected_indices', [])

            # 선택된 인덱스로 상품 추출 (1-based index)
            selected_products = []
            for idx in selected_indices:
                if 1 <= idx <= len(candidates):
                    selected_products.append(candidates[idx - 1])

            # 5개 미만이면 나머지는 점수 순으로 채움
            if len(selected_products) < self.TOP_K:
                existing_ids = {p['product'].danawa_product_id for p in selected_products}
                for item in candidates:
                    if item['product'].danawa_product_id not in existing_ids:
                        selected_products.append(item)
                        if len(selected_products) >= self.TOP_K:
                            break

            logger.info(f"LLM reranking selected: {[p['product'].name[:20] for p in selected_products]}")
            return selected_products[:self.TOP_K]

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"LLM reranking failed: {e}. Using default ranking.")
            return candidates[:self.TOP_K]

    def _generate_analysis_message(
        self,
        user_query: str,
        user_needs: str,
        priorities: Dict[str, int],
        product_count: int
    ) -> str:
        """
        Gemini Pro를 사용하여 분석 메시지 생성.
        """
        # 우선순위 문자열 생성
        priority_items = []
        for key, value in priorities.items():
            if value >= 7:
                priority_items.append(f"{key}(높음)")
            elif value >= 4:
                priority_items.append(f"{key}(중간)")

        priorities_str = ', '.join(priority_items) if priority_items else '균형잡힌 스펙'

        prompt = ANALYSIS_MESSAGE_PROMPT.format(
            user_query=user_query,
            user_needs=user_needs,
            priorities=priorities_str,
            product_count=product_count
        )

        try:
            response = self.gemini_client.generate_content(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"Analysis message generation failed: {e}")
            return f"'{user_query}'에 맞는 노트북 {product_count}개를 추천해드려요."

    def _generate_recommendation_reason(
        self,
        user_query: str,
        user_needs: str,
        product_name: str,
        brand: str,
        price: int,
        specs: Dict[str, Optional[str]]
    ) -> str:
        """
        Gemini Pro를 사용하여 상품별 추천 사유 생성.

        Args:
            user_query: 사용자의 원래 질문
            user_needs: 분석된 핵심 니즈
            product_name: 상품명
            brand: 브랜드
            price: 가격
            specs: 스펙 딕셔너리
        """
        # 스펙 문자열 생성
        spec_items = []
        if specs.get('cpu'):
            spec_items.append(f"CPU: {specs['cpu']}")
        if specs.get('ram'):
            spec_items.append(f"RAM: {specs['ram']}")
        if specs.get('weight'):
            spec_items.append(f"무게: {specs['weight']}")
        if specs.get('display'):
            spec_items.append(f"화면: {specs['display']}")
        if specs.get('gpu'):
            spec_items.append(f"GPU: {specs['gpu']}")
        if specs.get('storage'):
            spec_items.append(f"저장장치: {specs['storage']}")
        if specs.get('battery'):
            spec_items.append(f"배터리: {specs['battery']}")

        specs_str = ', '.join(spec_items) if spec_items else '정보 없음'

        prompt = RECOMMENDATION_REASON_PROMPT.format(
            user_query=user_query,
            user_needs=user_needs,
            product_name=product_name,
            brand=brand,
            price=price,
            specs=specs_str
        )

        try:
            response = self.gemini_client.generate_content(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"Recommendation reason generation failed: {e}")
            return f"{brand}의 {product_name}은(는) 사용자의 요구사항에 적합한 제품입니다."

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
