"""
Shopping Research service for 2-step AI recommendation.

Step 1: Generate customized questions based on user query
Step 2: Analyze survey responses and recommend top 5 products with 90%+ similarity
"""
import json
import logging
import re
import uuid
from typing import List, Dict, Any, Optional

from django.core.cache import cache
from django.db.models import F
from django.contrib.postgres.search import TrigramSimilarity
from pgvector.django import CosineDistance

from modules.products.models import ProductModel, MallInformationModel
from shared.ai_clients import get_openai_client, get_gemini_client
from .prompts import (
    QUESTION_GENERATION_PROMPT,
    SHOPPING_RESEARCH_ANALYSIS_PROMPT,
    AI_REVIEW_SUMMARY_PROMPT,
    RECOMMENDATION_REASON_PROMPT,
)

logger = logging.getLogger(__name__)


class ShoppingResearchService:
    """Service for 2-step shopping research with AI-powered recommendations."""

    CACHE_TTL = 1800  # 30 minutes
    TOP_K = 5
    SEARCH_LIMIT = 50
    VECTOR_WEIGHT = 0.7
    KEYWORD_WEIGHT = 0.3
    MIN_SIMILARITY = 0.90  # 90% similarity threshold

    def __init__(self):
        self.openai_client = get_openai_client()
        self.gemini_client = get_gemini_client()

    def _generate_search_id(self, user_query: str) -> str:
        """
        Generate unique search_id and store in cache.

        Args:
            user_query: User's search query

        Returns:
            Generated search_id (format: sr-xxxxxxxx)
        """
        search_id = f"sr-{uuid.uuid4().hex[:8]}"
        cache_key = f"shopping_research:{search_id}"
        cache.set(cache_key, {"user_query": user_query}, timeout=self.CACHE_TTL)
        return search_id

    def _validate_search_id(self, search_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate search_id and retrieve cached data.

        Args:
            search_id: The search ID to validate

        Returns:
            Cached data if valid, None otherwise
        """
        cache_key = f"shopping_research:{search_id}"
        return cache.get(cache_key)

    def generate_questions(self, user_query: str) -> Dict[str, Any]:
        """
        Step 1: Generate customized questions based on user query.

        Args:
            user_query: User's natural language search query

        Returns:
            Dict with search_id and questions list
        """
        # Generate search_id
        search_id = self._generate_search_id(user_query)

        # Generate questions using Gemini
        prompt = QUESTION_GENERATION_PROMPT.format(user_query=user_query)

        try:
            response = self.gemini_client.generate_content(prompt)

            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)

            questions = result.get('questions', [])

            # Ensure question_id is present
            for i, q in enumerate(questions, 1):
                if 'question_id' not in q:
                    q['question_id'] = i

            return {
                "search_id": search_id,
                "questions": questions
            }

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Question generation failed: {e}. Using default questions.")
            return {
                "search_id": search_id,
                "questions": self._get_default_questions()
            }

    def _get_default_questions(self) -> List[Dict[str, Any]]:
        """Return default questions when AI generation fails."""
        return [
            {
                "question_id": 1,
                "question": "주요 사용 목적은 무엇인가요?",
                "options": ["일반 업무", "영상 편집", "게임", "개발"]
            },
            {
                "question_id": 2,
                "question": "생각하시는 예산 범위는?",
                "options": ["100만원 미만", "100~150만원", "150~200만원", "200만원 이상"]
            },
            {
                "question_id": 3,
                "question": "디스플레이에서 가장 중요한 점은?",
                "options": ["해상도", "색재현율", "크기", "주사율"]
            },
            {
                "question_id": 4,
                "question": "휴대성을 어느 정도 고려하시나요?",
                "options": ["매우 중요", "보통", "성능이 더 중요"]
            }
        ]

    def get_recommendations(
        self,
        search_id: str,
        user_query: str,
        survey_contents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Step 2: Analyze survey responses and recommend products.

        Args:
            search_id: Search session ID
            user_query: User's search query
            survey_contents: List of survey responses

        Returns:
            Dict with user_query and product recommendations
        """
        # Validate search_id (optional - for tracking purposes)
        cached_data = self._validate_search_id(search_id)
        if cached_data:
            logger.info(f"Valid search_id: {search_id}")

        # Analyze survey responses
        intent = self._analyze_survey(user_query, survey_contents)

        # Perform hybrid search
        vector_results = self._vector_search(intent['search_query'])
        keyword_results = self._keyword_search(intent['keywords'])
        fused_results = self._fuse_results(vector_results, keyword_results)

        # Filter by minimum similarity (90%+)
        high_similarity_results = [
            r for r in fused_results if r['combined_score'] >= self.MIN_SIMILARITY
        ]

        # If not enough high-similarity results, use top results
        if len(high_similarity_results) < self.TOP_K:
            logger.info(f"Only {len(high_similarity_results)} products with 90%+ similarity. Using top results.")
            high_similarity_results = fused_results[:self.TOP_K]

        # Get top K products
        top_products = high_similarity_results[:self.TOP_K]

        # Build product recommendations
        products = []
        for rank, product_data in enumerate(top_products, 1):
            product_info = self._analyze_product(
                product_data=product_data,
                user_query=user_query,
                user_needs=intent['user_needs'],
                rank=rank,
                all_prices=[p['product'].lowest_price for p in top_products]
            )
            products.append(product_info)

        return {
            "user_query": user_query,
            "product": products
        }

    def _analyze_survey(
        self,
        user_query: str,
        survey_contents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze survey responses to extract search intent."""
        # Format survey responses
        survey_text = "\n".join([
            f"Q{s['question_id']}: {s['question']} -> A: {s['answer']}"
            for s in survey_contents
        ])

        prompt = SHOPPING_RESEARCH_ANALYSIS_PROMPT.format(
            user_query=user_query,
            survey_responses=survey_text
        )

        try:
            response = self.gemini_client.generate_content(prompt)

            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                intent = json.loads(json_match.group())
            else:
                intent = json.loads(response)

            return {
                'search_query': intent.get('search_query', user_query),
                'keywords': intent.get('keywords', [user_query]),
                'priorities': intent.get('priorities', {}),
                'user_needs': intent.get('user_needs', user_query)
            }

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Survey analysis failed: {e}. Using fallback.")
            # Build search query from survey answers
            answers = [s['answer'] for s in survey_contents]
            combined_query = f"{user_query} {' '.join(answers)}"
            return {
                'search_query': combined_query,
                'keywords': [user_query] + answers,
                'priorities': {},
                'user_needs': user_query
            }

    def _vector_search(self, search_query: str) -> List[Dict[str, Any]]:
        """Perform HNSW vector search."""
        query_embedding = self.openai_client.create_embedding(search_query)

        products = ProductModel.objects.filter(
            deleted_at__isnull=True,
            detail_spec_vector__isnull=False
        ).exclude(
            product_status__in=['단종', '판매중지', '품절']
        ).annotate(
            distance=CosineDistance('detail_spec_vector', query_embedding)
        ).order_by('distance')[:self.SEARCH_LIMIT]

        results = []
        for product in products:
            similarity = max(0.0, 1.0 - (product.distance / 2.0))

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
        """Perform GIN trigram keyword search."""
        if not keywords:
            return []

        search_text = ' '.join(keywords)

        products = ProductModel.objects.filter(
            deleted_at__isnull=True
        ).exclude(
            product_status__in=['단종', '판매중지', '품절']
        ).annotate(
            name_similarity=TrigramSimilarity('name', search_text),
            brand_similarity=TrigramSimilarity('brand', search_text)
        ).annotate(
            total_similarity=F('name_similarity') * 0.7 + F('brand_similarity') * 0.3
        ).filter(
            total_similarity__gt=0.05
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

    def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fuse vector and keyword search results with hybrid scoring."""
        results_map: Dict[str, Dict[str, Any]] = {}

        for item in vector_results:
            product_id = item['product'].danawa_product_id
            results_map[product_id] = {
                'product': item['product'],
                'mall_info': item['mall_info'],
                'vector_score': item['vector_score'],
                'keyword_score': 0.0
            }

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

        fused_results.sort(key=lambda x: (
            x['combined_score'],
            x['product'].review_count,
            x['product'].review_rating or 0
        ), reverse=True)

        return fused_results

    def _analyze_product(
        self,
        product_data: Dict[str, Any],
        user_query: str,
        user_needs: str,
        rank: int,
        all_prices: List[int]
    ) -> Dict[str, Any]:
        """Analyze a single product and build recommendation response."""
        product = product_data['product']
        mall_info = product_data.get('mall_info')
        combined_score = product_data.get('combined_score', 0.0)

        # Extract specs
        specs = self._extract_product_specs(product.detail_spec)

        # Generate recommendation reason
        recommendation_reason = self._generate_recommendation_reason(
            user_query=user_query,
            user_needs=user_needs,
            product_name=product.name,
            brand=product.brand,
            price=product.lowest_price,
            specs=specs
        )

        # Generate AI review summary
        ai_review_summary = self._generate_ai_review_summary(
            product_name=product.name,
            brand=product.brand,
            price=product.lowest_price,
            specs=specs,
            user_needs=user_needs
        )

        # Calculate performance score (0.0 - 1.0)
        performance_score = self._calculate_performance_score(product, combined_score)

        # Check if lowest price among top products
        is_lowest_price = product.lowest_price == min(all_prices) if all_prices else False

        return {
            "similarity_score": round(combined_score, 2),
            "product_image_url": mall_info.representative_image_url if mall_info else None,
            "product_name": product.name,
            "product_code": int(product.danawa_product_id),
            "recommendation_reason": recommendation_reason,
            "price": product.lowest_price,
            "performance_score": round(performance_score, 2),
            "product_specs": {
                "cpu": specs.get('cpu'),
                "ram": specs.get('ram'),
                "weight": specs.get('weight')
            },
            "ai_review_summary": ai_review_summary,
            "product_detail_url": mall_info.product_page_url if mall_info else None,
            "optimal_product_info": {
                "match_rank": rank,
                "is_lowest_price": is_lowest_price
            }
        }

    def _extract_product_specs(self, detail_spec: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Extract display specs from product detail_spec."""
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

        for item in spec_summary:
            item_lower = str(item).lower()

            if 'kg' in item_lower and not specs['weight']:
                specs['weight'] = str(item)
            elif ('cm' in item_lower or '인치' in item_lower) and not specs['display']:
                specs['display'] = str(item)
            elif '램' in item_lower or 'ram' in item_lower:
                if ':' in str(item):
                    specs['ram'] = str(item).split(':')[-1].strip()
                else:
                    specs['ram'] = str(item)
            elif 'tb' in item_lower or 'ssd' in item_lower:
                if ':' in str(item):
                    specs['storage'] = str(item).split(':')[-1].strip()
                else:
                    specs['storage'] = str(item)

        for key, value in spec_data.items():
            key_lower = key.lower()

            if ('코어' in key_lower or 'core' in key_lower or
                'i7' in key_lower or 'i5' in key_lower or 'i9' in key_lower or
                'ryzen' in key_lower or '울트라' in key_lower):
                if not specs['cpu']:
                    specs['cpu'] = key if value is True else str(value)
            elif ('rtx' in key_lower or 'gtx' in key_lower or
                  '지포스' in key_lower or 'radeon' in key_lower):
                if not specs['gpu']:
                    specs['gpu'] = key if value is True else str(value)
            elif '배터리' in key_lower or 'wh' in key_lower:
                if not specs['battery']:
                    specs['battery'] = key if value is True else str(value)
            elif '[구성]램' in key:
                if not specs['ram']:
                    specs['ram'] = str(value)
            elif '용량' in key:
                if not specs['storage']:
                    specs['storage'] = str(value)

        return specs

    def _generate_recommendation_reason(
        self,
        user_query: str,
        user_needs: str,
        product_name: str,
        brand: str,
        price: int,
        specs: Dict[str, Optional[str]]
    ) -> str:
        """Generate recommendation reason using Gemini."""
        spec_items = []
        for key, value in specs.items():
            if value:
                spec_items.append(f"{key}: {value}")
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

    def _generate_ai_review_summary(
        self,
        product_name: str,
        brand: str,
        price: int,
        specs: Dict[str, Optional[str]],
        user_needs: str
    ) -> str:
        """Generate AI review summary using Gemini."""
        spec_items = []
        for key, value in specs.items():
            if value:
                spec_items.append(f"{key}: {value}")
        specs_str = ', '.join(spec_items) if spec_items else '정보 없음'

        prompt = AI_REVIEW_SUMMARY_PROMPT.format(
            product_name=product_name,
            brand=brand,
            price=price,
            specs=specs_str,
            user_needs=user_needs
        )

        try:
            response = self.gemini_client.generate_content(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"AI review summary generation failed: {e}")
            return f"{product_name}은(는) 우수한 성능과 가성비를 제공합니다."

    def _calculate_performance_score(
        self,
        product: ProductModel,
        combined_score: float
    ) -> float:
        """
        Calculate performance score (0.0 - 1.0).

        Combines similarity score, review rating, and review count.
        """
        # Base score from similarity (0.0 - 1.0)
        base_score = combined_score

        # Review rating contribution (0 - 5 -> 0.0 - 0.2)
        rating_score = (product.review_rating or 0) / 25  # max 0.2

        # Review count contribution (normalized, max 0.1)
        review_score = min(product.review_count / 1000, 0.1)

        # Combined performance score (capped at 1.0)
        performance = min(1.0, base_score * 0.7 + rating_score + review_score)

        return performance
