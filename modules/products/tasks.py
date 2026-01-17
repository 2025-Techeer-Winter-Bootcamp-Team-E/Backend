"""
Products module Celery tasks.
다나와 크롤링 데이터를 DB에 저장하는 태스크들.
"""
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Optional

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================
# 카테고리 헬퍼 함수
# ============================================================

def get_or_create_category_hierarchy(
    category_1: Optional[str],
    category_2: Optional[str],
    category_3: Optional[str],
    category_4: Optional[str]
):
    """
    카테고리 계층 구조를 생성하거나 조회.

    Args:
        category_1: 대분류
        category_2: 중분류
        category_3: 소분류
        category_4: 세분류

    Returns:
        가장 하위 카테고리 모델 (없으면 None)
    """
    from modules.categories.models import CategoryModel

    categories = [category_1, category_2, category_3, category_4]
    categories = [c for c in categories if c]  # None 제거

    if not categories:
        return None

    parent = None
    current_category = None

    for name in categories:
        current_category, _ = CategoryModel.objects.get_or_create(
            name=name,
            parent=parent,
            defaults={'deleted_at': None}
        )
        parent = current_category

    return current_category


# ============================================================
# 크롤링 태스크
# ============================================================

@shared_task(name='products.crawl_product')
def crawl_product(danawa_product_id: str) -> dict:
    """
    단일 상품 전체 크롤링 및 DB 저장.

    CSV 데이터 명세서의 모든 필드를 크롤링하여 저장:
    - 상품 기본 정보 → ProductModel
    - 카테고리 → CategoryModel (계층 구조)
    - 쇼핑몰/판매자 정보 → MallInformationModel
    - 24개월 가격 이력 → PriceHistoryModel
    - 리뷰 → ReviewModel

    Args:
        danawa_product_id: 다나와 상품 ID (pcode)

    Returns:
        결과 딕셔너리
    """
    from .crawlers import DanawaCrawler
    from .models import ProductModel, MallInformationModel
    from modules.price_prediction.models import PriceHistoryModel
    from modules.orders.models import ReviewModel
    from modules.users.models import UserModel

    try:
        with DanawaCrawler() as crawler:
            # 전체 상품 데이터 크롤링
            full_data = crawler.crawl_full_product_data(danawa_product_id)

            if not full_data:
                return {'success': False, 'error': 'Failed to crawl product data'}

            product_info = full_data.get('product_info')
            mall_prices = full_data.get('mall_list', [])
            price_history = full_data.get('price_history', [])
            reviews = full_data.get('reviews', [])

            if not product_info:
                return {'success': False, 'error': 'No product info found'}

            # ========================================
            # 1. 카테고리 저장
            # ========================================
            category = get_or_create_category_hierarchy(
                product_info.category_1,
                product_info.category_2,
                product_info.category_3,
                product_info.category_4
            )

            # ========================================
            # 2. 상품 정보 저장 (ProductModel)
            # ========================================
            # detail_spec에 spec과 spec_summary 모두 저장
            detail_spec_data = {
                'spec': product_info.spec,
                'spec_summary': product_info.spec_summary,
            }

            product, created = ProductModel.objects.update_or_create(
                danawa_product_id=danawa_product_id,
                defaults={
                    'name': product_info.product_name,
                    'lowest_price': product_info.min_price or product_info.price,
                    'brand': product_info.brand or '',
                    'detail_spec': detail_spec_data,
                    'registration_month': product_info.registration_date,
                    'product_status': product_info.product_status,
                    'category': category,
                }
            )

            action = 'created' if created else 'updated'
            logger.info(f"Product {danawa_product_id} {action}")

            # ========================================
            # 3. 쇼핑몰/판매자 정보 저장 (MallInformationModel)
            # ========================================
            mall_count = 0
            for mall in mall_prices:
                MallInformationModel.objects.update_or_create(
                    product=product,
                    mall_name=mall.seller_name,
                    defaults={
                        'current_price': mall.price,
                        'product_page_url': mall.seller_url or '',
                        'seller_logo_url': mall.seller_logo or '',
                        'representative_image_url': product_info.image_url or '',
                        'additional_image_urls': product_info.additional_images,
                        'detail_page_image_url': ', '.join(product_info.detail_page_images) if product_info.detail_page_images else '',
                        'product_description_image_url': ', '.join(product_info.product_description_images) if product_info.product_description_images else '',
                    }
                )
                mall_count += 1

            # 쇼핑몰 정보가 없을 경우에도 이미지 정보 저장을 위해 기본 레코드 생성
            if not mall_prices and product_info.image_url:
                MallInformationModel.objects.update_or_create(
                    product=product,
                    mall_name='다나와',
                    defaults={
                        'current_price': product_info.min_price or product_info.price,
                        'product_page_url': f'https://prod.danawa.com/info/?pcode={danawa_product_id}',
                        'representative_image_url': product_info.image_url or '',
                        'additional_image_urls': product_info.additional_images,
                        'detail_page_image_url': ', '.join(product_info.detail_page_images) if product_info.detail_page_images else '',
                        'product_description_image_url': ', '.join(product_info.product_description_images) if product_info.product_description_images else '',
                    }
                )
                mall_count = 1

            # ========================================
            # 4. 가격 이력 저장 (PriceHistoryModel) - 24개월
            # ========================================
            history_count = 0
            now = timezone.now()

            for ph in price_history:
                # month_offset: 1 = 1개월 전, 24 = 24개월 전
                recorded_date = now - relativedelta(months=ph.month_offset)

                # 중복 방지: 해당 월에 이미 기록이 있으면 업데이트
                PriceHistoryModel.objects.update_or_create(
                    product=product,
                    recorded_at__year=recorded_date.year,
                    recorded_at__month=recorded_date.month,
                    defaults={
                        'lowest_price': ph.price,
                        'recorded_at': recorded_date,
                    }
                )
                history_count += 1

            # ========================================
            # 5. 리뷰 저장 (ReviewModel)
            # ========================================
            review_count = 0

            # 리뷰 저장 시 사용할 시스템 유저 (크롤링 리뷰용)
            # 실제 서비스에서는 별도의 시스템 유저를 생성하거나 null 허용 필요
            system_user = None
            try:
                system_user = UserModel.objects.filter(email='system@danawa.com').first()
                if not system_user:
                    # 시스템 유저가 없으면 첫 번째 유저 사용 (개발용)
                    system_user = UserModel.objects.first()
            except Exception:
                pass

            if system_user:
                for review in reviews:
                    # 리뷰 내용으로 중복 체크
                    existing_review = ReviewModel.objects.filter(
                        product=product,
                        reviewer_name=review.reviewer,
                        content=review.content[:100] if review.content else ''
                    ).first()

                    if not existing_review:
                        ReviewModel.objects.create(
                            product=product,
                            user=system_user,
                            mall_name=review.shop_name,
                            reviewer_name=review.reviewer,
                            content=review.content,
                            rating=review.rating,
                            review_images=review.review_images,
                            external_review_count=product_info.mall_review_count,
                        )
                        review_count += 1

            return {
                'success': True,
                'product_id': product.id,
                'danawa_product_id': danawa_product_id,
                'action': action,
                'mall_count': mall_count,
                'history_count': history_count,
                'review_count': review_count,
            }

    except Exception as e:
        logger.error(f"Error crawling product {danawa_product_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='products.crawl_product_basic')
def crawl_product_basic(danawa_product_id: str) -> dict:
    """
    상품 기본 정보만 크롤링 (가격, 쇼핑몰 정보).
    빠른 가격 업데이트용.

    Args:
        danawa_product_id: 다나와 상품 ID

    Returns:
        결과 딕셔너리
    """
    from .crawlers import DanawaCrawler
    from .models import ProductModel, MallInformationModel

    try:
        with DanawaCrawler() as crawler:
            # 상품 정보 크롤링
            product_info = crawler.get_product_info(danawa_product_id)

            if not product_info:
                return {'success': False, 'error': 'Failed to crawl product'}

            # 카테고리 처리
            category = get_or_create_category_hierarchy(
                product_info.category_1,
                product_info.category_2,
                product_info.category_3,
                product_info.category_4
            )

            # detail_spec 구성
            detail_spec_data = {
                'spec': product_info.spec,
                'spec_summary': product_info.spec_summary,
            }

            # DB 저장 (upsert)
            product, created = ProductModel.objects.update_or_create(
                danawa_product_id=danawa_product_id,
                defaults={
                    'name': product_info.product_name,
                    'lowest_price': product_info.min_price or product_info.price,
                    'brand': product_info.brand or '',
                    'detail_spec': detail_spec_data,
                    'registration_month': product_info.registration_date,
                    'product_status': product_info.product_status,
                    'category': category,
                }
            )

            # 쇼핑몰 가격 정보 크롤링
            mall_prices = crawler.get_mall_prices(danawa_product_id)

            for mall in mall_prices:
                MallInformationModel.objects.update_or_create(
                    product=product,
                    mall_name=mall.seller_name,
                    defaults={
                        'current_price': mall.price,
                        'product_page_url': mall.seller_url or '',
                        'seller_logo_url': mall.seller_logo or '',
                        'representative_image_url': product_info.image_url or '',
                        'additional_image_urls': product_info.additional_images,
                    }
                )

            action = 'created' if created else 'updated'
            logger.info(f"Product {danawa_product_id} {action}")

            return {
                'success': True,
                'product_id': product.id,
                'action': action,
                'mall_count': len(mall_prices),
            }

    except Exception as e:
        logger.error(f"Error crawling product {danawa_product_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='products.crawl_products_batch')
def crawl_products_batch(danawa_product_ids: list, full_crawl: bool = True) -> dict:
    """
    여러 상품 일괄 크롤링.

    Args:
        danawa_product_ids: 다나와 상품 ID 리스트
        full_crawl: True면 전체 크롤링, False면 기본 정보만

    Returns:
        결과 딕셔너리
    """
    results = {
        'total': len(danawa_product_ids),
        'success': 0,
        'failed': 0,
        'errors': [],
    }

    crawl_func = crawl_product if full_crawl else crawl_product_basic

    for product_id in danawa_product_ids:
        result = crawl_func(product_id)

        if result.get('success'):
            results['success'] += 1
        else:
            results['failed'] += 1
            results['errors'].append({
                'product_id': product_id,
                'error': result.get('error'),
            })

    logger.info(
        f"Batch crawl completed: {results['success']}/{results['total']} succeeded"
    )

    return results


@shared_task(name='products.search_and_crawl')
def search_and_crawl(keyword: str, limit: int = 10, full_crawl: bool = True) -> dict:
    """
    키워드로 검색 후 결과 상품들 크롤링.

    Args:
        keyword: 검색 키워드
        limit: 최대 크롤링 수
        full_crawl: True면 전체 크롤링 (가격이력, 리뷰 포함)

    Returns:
        결과 딕셔너리
    """
    from .crawlers import DanawaCrawler

    try:
        with DanawaCrawler() as crawler:
            # 검색
            search_results = crawler.search_products(keyword, limit=limit)

            if not search_results:
                return {'success': False, 'error': 'No search results'}

            # 검색된 상품들 크롤링 태스크 생성
            product_ids = [r['danawa_product_id'] for r in search_results]

            # 비동기로 크롤링 시작
            crawl_products_batch.delay(product_ids, full_crawl=full_crawl)

            return {
                'success': True,
                'keyword': keyword,
                'queued_count': len(product_ids),
                'product_ids': product_ids,
            }

    except Exception as e:
        logger.error(f"Error in search_and_crawl for '{keyword}': {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='products.update_all_prices')
def update_all_prices() -> dict:
    """
    모든 상품의 가격 정보 업데이트.
    주기적 실행용 (예: 매일 새벽).
    기본 정보만 업데이트 (빠른 실행).

    Returns:
        결과 딕셔너리
    """
    from .models import ProductModel

    products = ProductModel.objects.filter(
        deleted_at__isnull=True
    ).values_list('danawa_product_id', flat=True)

    product_ids = list(products)

    if not product_ids:
        return {'success': True, 'message': 'No products to update'}

    # 배치로 크롤링 시작 (기본 정보만)
    crawl_products_batch.delay(product_ids, full_crawl=False)

    logger.info(f"Queued {len(product_ids)} products for price update")

    return {
        'success': True,
        'queued_count': len(product_ids),
    }


@shared_task(name='products.full_update_all_products')
def full_update_all_products() -> dict:
    """
    모든 상품의 전체 정보 업데이트.
    주기적 실행용 (예: 매주).
    가격 이력, 리뷰 포함.

    Returns:
        결과 딕셔너리
    """
    from .models import ProductModel

    products = ProductModel.objects.filter(
        deleted_at__isnull=True
    ).values_list('danawa_product_id', flat=True)

    product_ids = list(products)

    if not product_ids:
        return {'success': True, 'message': 'No products to update'}

    # 배치로 전체 크롤링 시작
    crawl_products_batch.delay(product_ids, full_crawl=True)

    logger.info(f"Queued {len(product_ids)} products for full update")

    return {
        'success': True,
        'queued_count': len(product_ids),
    }


# ============================================================
# 가격 이력 태스크
# ============================================================

@shared_task(name='products.record_price_history')
def record_price_history(product_id: int) -> dict:
    """
    상품의 현재 최저가를 가격 이력에 기록.

    Args:
        product_id: 상품 ID

    Returns:
        결과 딕셔너리
    """
    from .models import ProductModel
    from modules.price_prediction.models import PriceHistoryModel

    try:
        product = ProductModel.objects.get(id=product_id, deleted_at__isnull=True)

        PriceHistoryModel.objects.create(
            product=product,
            lowest_price=product.lowest_price,
            recorded_at=timezone.now(),
        )

        return {'success': True, 'product_id': product_id}

    except ProductModel.DoesNotExist:
        return {'success': False, 'error': 'Product not found'}
    except Exception as e:
        logger.error(f"Error recording price history for {product_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='products.record_all_price_histories')
def record_all_price_histories() -> dict:
    """
    모든 상품의 가격 이력 기록.
    주기적 실행용 (예: 매일).

    Returns:
        결과 딕셔너리
    """
    from .models import ProductModel

    products = ProductModel.objects.filter(deleted_at__isnull=True)
    count = 0

    for product in products:
        record_price_history.delay(product.id)
        count += 1

    return {
        'success': True,
        'queued_count': count,
    }


# ============================================================
# 리뷰 크롤링 태스크
# ============================================================

@shared_task(name='products.crawl_product_reviews')
def crawl_product_reviews(danawa_product_id: str, max_pages: int = 5) -> dict:
    """
    특정 상품의 리뷰만 크롤링.

    Args:
        danawa_product_id: 다나와 상품 ID
        max_pages: 최대 크롤링 페이지 수

    Returns:
        결과 딕셔너리
    """
    from .crawlers import DanawaCrawler
    from .models import ProductModel
    from modules.orders.models import ReviewModel
    from modules.users.models import UserModel

    try:
        product = ProductModel.objects.get(
            danawa_product_id=danawa_product_id,
            deleted_at__isnull=True
        )
    except ProductModel.DoesNotExist:
        return {'success': False, 'error': 'Product not found in DB'}

    try:
        with DanawaCrawler() as crawler:
            reviews = crawler.get_reviews(danawa_product_id, max_pages=max_pages)

            if not reviews:
                return {'success': True, 'message': 'No reviews found', 'count': 0}

            # 시스템 유저 조회
            system_user = UserModel.objects.filter(email='system@danawa.com').first()
            if not system_user:
                system_user = UserModel.objects.first()

            if not system_user:
                return {'success': False, 'error': 'No user available for review creation'}

            review_count = 0
            for review in reviews:
                # 중복 체크
                existing = ReviewModel.objects.filter(
                    product=product,
                    reviewer_name=review.reviewer,
                    content=review.content[:100] if review.content else ''
                ).exists()

                if not existing:
                    ReviewModel.objects.create(
                        product=product,
                        user=system_user,
                        mall_name=review.shop_name,
                        reviewer_name=review.reviewer,
                        content=review.content,
                        rating=review.rating,
                        review_images=review.review_images,
                    )
                    review_count += 1

            return {
                'success': True,
                'product_id': product.id,
                'review_count': review_count,
                'total_crawled': len(reviews),
            }

    except Exception as e:
        logger.error(f"Error crawling reviews for {danawa_product_id}: {e}")
        return {'success': False, 'error': str(e)}


# ============================================================
# 임베딩 태스크
# ============================================================

@shared_task(name='products.generate_product_embedding')
def generate_product_embedding(product_id: int) -> bool:
    """
    상품 임베딩 생성 (벡터 검색용).

    Args:
        product_id: 상품 ID

    Returns:
        성공 여부
    """
    from .models import ProductModel

    try:
        product = ProductModel.objects.get(id=product_id)
    except ProductModel.DoesNotExist:
        return False

    # 임베딩 텍스트 생성
    spec_summary = ''
    if product.detail_spec and isinstance(product.detail_spec, dict):
        spec_summary = ' '.join(product.detail_spec.get('spec_summary', []))

    text = f"{product.name}. {product.brand}. {spec_summary}"

    try:
        from shared.ai_clients import OpenAIClient
        client = OpenAIClient()
        embedding = client.create_embedding(text)

        product.detail_spec_vector = embedding
        product.save()
        return True
    except Exception as e:
        logger.error(f"Error generating embedding for product {product_id}: {e}")
        return False


@shared_task(name='products.generate_all_embeddings')
def generate_all_embeddings() -> dict:
    """
    임베딩이 없는 모든 상품에 대해 임베딩 생성.

    Returns:
        결과 딕셔너리
    """
    from .models import ProductModel

    products = ProductModel.objects.filter(
        deleted_at__isnull=True,
        detail_spec_vector__isnull=True
    )

    count = 0
    for product in products:
        generate_product_embedding.delay(product.id)
        count += 1

    return {
        'success': True,
        'queued_count': count,
    }
