#!/usr/bin/env python
"""크롤링한 상품 데이터를 계층적 카테고리별로 CSV 파일로 내보내기"""
import os
import sys
import csv
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import logging
logging.disable(logging.DEBUG)

from modules.products.models import ProductModel
from modules.price_prediction.models import PriceHistoryModel


def get_category_path(category):
    """카테고리의 전체 경로를 반환 (최대 4단계)"""
    if not category:
        return '', '', '', ''

    path = []
    current = category
    while current:
        path.insert(0, current.name)
        current = current.parent

    # 최대 4단계 (루트, 상위, 중간, 하위)
    while len(path) < 4:
        path.append('')

    return path[0], path[1], path[2], path[3]


def main():
    # CSV 파일 경로
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, 'products_by_category.csv')

    # 상품 데이터 조회
    products = ProductModel.objects.filter(deleted_at__isnull=True).select_related('category', 'category__parent', 'category__parent__parent')

    print(f"총 {products.count()}개 상품을 CSV로 내보냅니다...")

    # CSV 파일 작성
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # 헤더 작성
        writer.writerow([
            '대분류',
            '중분류',
            '소분류',
            '세분류',
            '상품코드(다나와)',
            '상품명',
            '브랜드',
            '최저가',
            '등록월',
            '상품상태',
            '가격이력수',
            '스펙요약',
        ])

        # 카테고리별로 정렬하여 데이터 작성
        for product in products.order_by('category__parent__parent__parent__name', 'category__parent__parent__name', 'category__parent__name', 'category__name', 'name'):
            top_cat, mid_cat, sub_cat, leaf_cat = get_category_path(product.category)
            history_count = PriceHistoryModel.objects.filter(product=product).count()

            # 스펙 요약 추출
            spec_summary = ''
            if product.detail_spec and isinstance(product.detail_spec, dict):
                spec_list = product.detail_spec.get('spec_summary', [])
                if spec_list:
                    spec_summary = ' / '.join(spec_list[:5])

            writer.writerow([
                top_cat or '미분류',
                mid_cat or '',
                sub_cat or '',
                leaf_cat or '',
                product.danawa_product_id,
                product.name,
                product.brand or '',
                product.lowest_price or 0,
                product.registration_month or '',
                product.product_status or '',
                history_count,
                spec_summary[:200] if spec_summary else '',
            ])

    print(f"✓ CSV 파일 생성 완료: {csv_path}")

    # 계층적 카테고리별 통계 출력
    print("\n" + "=" * 60)
    print("계층적 카테고리별 상품 수")
    print("=" * 60)

    # 카테고리 통계 수집
    stats = {}
    for p in products:
        top, mid, sub, leaf = get_category_path(p.category)
        key = (top, mid, sub, leaf)
        stats[key] = stats.get(key, 0) + 1

    # 계층별로 출력
    current_top = None
    current_mid = None
    current_sub = None
    for (top, mid, sub, leaf), count in sorted(stats.items()):
        if top != current_top:
            print(f"\n[{top or '미분류'}]")
            current_top = top
            current_mid = None
            current_sub = None
        if mid and mid != current_mid:
            print(f"  └─ {mid}")
            current_mid = mid
            current_sub = None
        if sub and sub != current_sub:
            print(f"      └─ {sub}")
            current_sub = sub
        if leaf:
            print(f"          └─ {leaf}: {count}개")
        elif sub:
            print(f"          └─ (직접): {count}개")
        elif mid:
            print(f"      └─ (직접): {count}개")
        else:
            print(f"  └─ (직접): {count}개")

    print(f"\n총 {products.count()}개 상품")


if __name__ == '__main__':
    main()
