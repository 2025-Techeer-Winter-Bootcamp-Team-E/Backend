#!/usr/bin/env python
"""
컴퓨터/노트북/조립PC 전체 카테고리 상품 크롤링 스크립트

상위 카테고리 > 하위 카테고리 구조로 분류하여 크롤링합니다.
"""
import os
import sys
import re
import django
import requests
from bs4 import BeautifulSoup
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

import logging
logging.disable(logging.DEBUG)

from modules.products.models import ProductModel
from modules.categories.models import CategoryModel
from modules.products.tasks import crawl_product


# 컴퓨터/노트북/조립PC 카테고리 구조 (상위 > 하위)
CATEGORY_STRUCTURE = {
    '노트북/데스크탑': [
        '노트북',
        '게이밍노트북',
        '울트라북',
        '2in1노트북',
        '브랜드PC',
        '조립PC',
        '게이밍PC',
        '미니PC',
        '올인원PC',
    ],
    '모니터/복합기': [
        '모니터',
        '게이밍모니터',
        '커브드모니터',
        '4K모니터',
        '프린터',
        '복합기',
        '레이저프린터',
    ],
    'PC부품': [
        'CPU',
        '그래픽카드',
        'RTX그래픽카드',
        'SSD',
        'NVMe SSD',
        'RAM',
        'DDR5',
        '메인보드',
        '파워서플라이',
        'PC케이스',
        'CPU쿨러',
        '수랭쿨러',
    ],
    '키보드/마우스': [
        '기계식키보드',
        '게이밍키보드',
        '무선키보드',
        '게이밍마우스',
        '무선마우스',
        '버티컬마우스',
    ],
    '주변기기': [
        '웹캠',
        '공유기',
        '와이파이공유기',
        '외장하드',
        'USB허브',
        '마우스패드',
    ],
    '게임/사운드': [
        '게이밍헤드셋',
        '블루투스이어폰',
        'PC스피커',
        '사운드바',
        '게이밍의자',
        '게이밍데스크',
    ],
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def search_products(keyword: str, limit: int = 20) -> list:
    """다나와 검색으로 상품 코드 목록 추출"""
    url = f"https://search.danawa.com/dsearch.php?query={keyword}&limit={limit}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'lxml')
        products = soup.select('.product_list .prod_item')

        result = []
        for item in products:
            pcode = None
            item_id = item.get('id', '')
            if item_id.startswith('productItem'):
                pcode = item_id.replace('productItem', '')

            if not pcode:
                link = item.select_one('a[href*="pcode"]')
                if link:
                    href = link.get('href', '')
                    pcode_match = re.search(r'pcode=(\d+)', href)
                    if pcode_match:
                        pcode = pcode_match.group(1)

            if pcode and pcode.isdigit():
                name_elem = item.select_one('.prod_name a') or item.select_one('.prod_name')
                name = name_elem.get_text(strip=True) if name_elem else 'Unknown'
                result.append({'pcode': pcode, 'name': name[:50]})

        return result
    except Exception as e:
        print(f"    검색 오류 ({keyword}): {e}")
        return []


def get_or_create_category(parent_name: str, child_name: str):
    """상위/하위 카테고리 생성"""
    # 최상위 카테고리 (컴퓨터/노트북/조립PC)
    root, _ = CategoryModel.objects.get_or_create(
        name='컴퓨터/노트북/조립PC',
        parent=None,
        defaults={'deleted_at': None}
    )

    # 상위 카테고리
    parent, _ = CategoryModel.objects.get_or_create(
        name=parent_name,
        parent=root,
        defaults={'deleted_at': None}
    )

    # 하위 카테고리
    child, _ = CategoryModel.objects.get_or_create(
        name=child_name,
        parent=parent,
        defaults={'deleted_at': None}
    )

    return child


def main():
    print("=" * 70)
    print("컴퓨터/노트북/조립PC 전체 카테고리 크롤링")
    print("=" * 70)

    # 기존 상품 확인
    existing_pcodes = set(
        ProductModel.objects.filter(deleted_at__isnull=True)
        .values_list('danawa_product_id', flat=True)
    )
    print(f"\n기존 상품 수: {len(existing_pcodes)}개")

    # 크롤링 결과 저장
    all_products = []
    category_mapping = {}  # pcode -> (parent_cat, child_cat)

    # 각 카테고리별로 검색
    for parent_cat, child_cats in CATEGORY_STRUCTURE.items():
        print(f"\n[{parent_cat}]")

        for child_cat in child_cats:
            time.sleep(random.uniform(0.3, 0.7))

            products = search_products(child_cat, limit=15)
            new_products = [p for p in products if p['pcode'] not in existing_pcodes]

            # 이미 수집한 상품 제외
            new_products = [p for p in new_products
                          if p['pcode'] not in [x['pcode'] for x in all_products]]

            print(f"  {child_cat}: {len(products)}개 검색, {len(new_products)}개 신규")

            for p in new_products:
                all_products.append(p)
                category_mapping[p['pcode']] = (parent_cat, child_cat)

    print("\n" + "=" * 70)
    print(f"크롤링 대상: {len(all_products)}개 신규 상품")
    print("=" * 70)

    if not all_products:
        print("크롤링할 신규 상품이 없습니다.")
        return

    # 상품 크롤링 및 저장
    success_count = 0
    fail_count = 0

    for i, product in enumerate(all_products, 1):
        pcode = product['pcode']
        name = product['name']
        parent_cat, child_cat = category_mapping[pcode]

        print(f"\n[{i}/{len(all_products)}] [{parent_cat} > {child_cat}]")
        print(f"  [{pcode}] {name}")

        try:
            # 카테고리 생성
            category = get_or_create_category(parent_cat, child_cat)

            # 크롤링 실행
            result = crawl_product(pcode)

            if result.get('success'):
                # 카테고리 업데이트
                try:
                    prod = ProductModel.objects.get(danawa_product_id=pcode)
                    prod.category = category
                    prod.save()
                except:
                    pass

                action = result.get('action', 'saved')
                history_count = result.get('history_count', 0)
                print(f"  ✓ {action} (가격이력: {history_count}개)")
                success_count += 1
                existing_pcodes.add(pcode)
            else:
                error = result.get('error', 'Unknown error')
                print(f"  ✗ 실패: {error}")
                fail_count += 1

        except Exception as e:
            print(f"  ✗ 오류: {str(e)[:50]}")
            fail_count += 1

    # 결과 요약
    print("\n" + "=" * 70)
    print("크롤링 완료!")
    print("=" * 70)
    print(f"  성공: {success_count}개")
    print(f"  실패: {fail_count}개")

    # 최종 상품 수
    final_count = ProductModel.objects.filter(deleted_at__isnull=True).count()
    print(f"\n총 상품 수: {final_count}개")


if __name__ == '__main__':
    main()
