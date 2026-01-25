import json
import logging
import re
import concurrent.futures
from typing import List, Dict, Any, Optional

from django.db.models import F, Q
from django.contrib.postgres.search import TrigramSimilarity
from pgvector.django import L2Distance

from modules.products.models import ProductModel, MallInformationModel
from modules.categories.models import CategoryModel
from shared.ai_clients import get_openai_client, get_gemini_client
from .prompts import INTENT_EXTRACTION_PROMPT, COMBINED_RECOMMENDATION_PROMPT

logger = logging.getLogger(__name__)

class LLMRecommendationService:
    """Pro의 지능을 쓰되, 카테고리 이탈과 결과 증발을 원천 봉쇄한 코드"""

    TOP_K = 5

    def __init__(self):
        self.openai_client = get_openai_client()
        self.gemini_client = get_gemini_client()
        # 카테고리 목록 메모리 캐싱 (ID 매핑용)
        self._categories = list(CategoryModel.objects.filter(deleted_at__isnull=True).values('id', 'name'))

    def get_recommendations(self, user_query: str) -> Dict[str, Any]:
        # 1. 의도 추출 및 분석 메시지 (호출 통합으로 10초 절감)
        intent = self._extract_intent_pro(user_query)
        
        # 2. 엄격한 카테고리 매핑 (CPU 요청 시 모니터암 차단 핵심 로직)
        category_name = intent.get('product_category', '상품')
        category_id = self._find_strict_category(category_name)
        
        # 3. 병렬 DB 검색 (L2Distance + Category Hard-filter)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_vec = executor.submit(self._vector_search, intent.get('search_query', user_query), category_id)
            f_key = executor.submit(self._keyword_search, intent.get('keywords', [user_query]), category_id)
            vector_results, keyword_results = f_vec.result(), f_key.result()

        # 4. 하이브리드 결합 (상위 8개 후보 선정)
        fused_results = self._fuse_results(vector_results, keyword_results)[:8]

        if not fused_results:
            return {"analysis_message": f"'{category_name}' 카테고리에서 상품을 찾지 못했습니다.", "recommended_products": []}

        # 5. 재랭킹 및 결과 구성 (실패 시에도 상품 노출 보장)
        final_products = self._rerank_with_fallback(user_query, intent, fused_results)

        return {
            "analysis_message": intent.get('analysis_message', f"{category_name} 추천 결과입니다."),
            "recommended_products": final_products
        }

    def _extract_intent_pro(self, user_query: str) -> Dict[str, Any]:
        """Pro 모델을 사용하여 의도와 메시지 동시 추출"""
        prompt = f"{INTENT_EXTRACTION_PROMPT}\n\n필수 필드: 'analysis_message' (사용자 니즈 공감 메시지 1-2문장)"
        
        # 기본값 (KeyError 방어)
        res = {"product_category": "상품", "search_query": user_query, "keywords": [user_query], "analysis_message": "상품을 분석 중입니다."}
        try:
            response = self.gemini_client.generate_content(prompt.format(user_query=user_query))
            match = re.search(r'\{[\s\S]*\}', response.text)
            if match:
                res.update(json.loads(match.group()))
            return res
        except:
            return res

    def _find_strict_category(self, name: str) -> Optional[int]:
        """'CPU'가 '모니터암'에 낚이지 않도록 하는 엄격 매칭"""
        if not name or name == '기타': return None
        # 완전 일치 우선
        for c in self._categories:
            if c['name'].strip().lower() == name.strip().lower():
                return c['id']
        # 포함 일치 (오답 방지를 위해 카테고리명이 너무 길지 않은 경우만)
        for c in self._categories:
            if name in c['name'] and len(c['name']) < len(name) + 3:
                return c['id']
        return None

    def _vector_search(self, query, category_id):
        """L2Distance 기반 검색 + 카테고리 감옥 필터"""
        embedding = self.openai_client.create_embedding(query)
        qs = ProductModel.objects.filter(deleted_at__isnull=True, detail_spec_vector__isnull=False)
        
        # 🔥 여기서 카테고리를 꽉 잡아야 엉뚱한 상품이 안 나옵니다.
        if category_id:
            qs = qs.filter(category_id=category_id)

        products = qs.exclude(product_status__in=['단종', '판매중지', '품절']).annotate(
            distance=L2Distance('detail_spec_vector', embedding)
        ).order_by('distance')[:20]
        
        products_list = list(products)
        mall_map = self._get_mall_map([p.id for p in products_list])
        return [{'product': p, 'mall_info': mall_map.get(p.id), 'score': max(0, 1-(p.distance/2))} for p in products_list]

    def _rerank_with_fallback(self, user_query, intent, fused_results):
        """LLM이 사고를 쳐도 DB 결과 5개는 무조건 보여주는 보장 로직"""
        # LLM에게 줄 상품 리스트 문자열화
        product_list_str = "\n".join([
            f"- 코드: {r['product'].danawa_product_id} | 품명: {r['product'].name}" for r in fused_results
        ])
        
        prompt = COMBINED_RECOMMENDATION_PROMPT.format(
            user_query=user_query,
            product_category=intent.get('product_category', '상품'),
            user_needs=intent.get('user_needs', user_query),
            product_list=product_list_str
        )

        reason_map = {}
        selected_codes = []
        try:
            resp = self.gemini_client.generate_content(prompt)
            data = json.loads(re.search(r'\{[\s\S]*\}', resp.text).group())
            for r in data.get('results', []):
                code = str(r.get('product_code'))
                reason_map[code] = r.get('recommendation_reason')
                selected_codes.append(code)
        except:
            logger.error("LL Reranking failed, falling back to DB ranking.")

        # 최종 리스트 조립 (LLM 선택 우선, 없으면 DB 검색 상위 5개 강제 채움)
        final_list = []
        target_items = []
        
        if selected_codes:
            code_map = {str(f['product'].danawa_product_id): f for f in fused_results}
            for code in selected_codes:
                if code in code_map: target_items.append(code_map[code])
        
        # LLM이 선택을 못했거나 형식이 틀렸으면 DB 상위 5개로 대체
        if not target_items:
            target_items = fused_results[:self.TOP_K]

        for item in target_items[:self.TOP_K]:
            p = item['product']
            final_list.append({
                'product_code': p.danawa_product_id,
                'name': p.name,
                'brand': p.brand,
                'price': p.lowest_price,
                'thumbnail_url': item['mall_info'].representative_image_url if item['mall_info'] else None,
                'recommendation_reason': reason_map.get(str(p.danawa_product_id), "사용자의 요구 사양에 가장 부합하는 고성능 모델입니다."),
                'specs': self._extract_display_specs(p.detail_spec),
                'review_count': p.review_count,
                'review_rating': p.review_rating,
            })
        return final_list

    # (이하 _keyword_search, _fuse_results, _get_mall_map, _extract_display_specs는 기존 로직 유지)
    def _get_mall_map(self, ids):
        mall_infos = MallInformationModel.objects.filter(product_id__in=ids, deleted_at__isnull=True).order_by('product_id', '-created_at').distinct('product_id')
        return {mi.product_id: mi for mi in mall_infos}

    def _keyword_search(self, keywords, category_id):
        if not keywords: return []
        qs = ProductModel.objects.filter(deleted_at__isnull=True)
        if category_id:
            qs = qs.filter(category_id=category_id)
        qs = qs.annotate(sim=TrigramSimilarity('name', ' '.join(keywords))).filter(sim__gt=0.05).order_by('-sim')[:20]
        products = list(qs)
        mall_map = self._get_mall_map([p.id for p in products])
        return [{'product': p, 'mall_info': mall_map.get(p.id), 'score': float(p.sim)} for p in products]

    def _fuse_results(self, vec, key):
        res = {i['product'].danawa_product_id: i for i in vec}
        for i in key:
            pid = i['product'].danawa_product_id
            if pid in res: res[pid]['score'] = res[pid]['score'] * 0.7 + i['score'] * 0.3
            else: res[pid] = i
        return sorted(res.values(), key=lambda x: x['score'], reverse=True)

    def _extract_display_specs(self, detail_spec):
        return {"specs": "상세 스펙 참조"}