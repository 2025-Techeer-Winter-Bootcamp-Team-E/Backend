#!/usr/bin/env python
"""
컴퓨터/노트북/조립PC 카테고리 상품 크롤링 스크립트

다나와의 컴퓨터/노트북/조립PC 카테고리 하위 상품만 크롤링합니다:
- 노트북/데스크탑: 노트북, 게이밍 노트북, 브랜드PC, 조립PC, 게이밍PC
- 모니터/복합기: 모니터, 게이밍 모니터
- PC부품: CPU, 그래픽카드, SSD, RAM, 메인보드, 파워, 케이스, 쿨러, 키보드, 마우스
- 게임/사운드: 게이밍 의자, 헤드셋
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
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import logging
logging.disable(logging.DEBUG)

from modules.products.models import ProductModel
from modules.products.tasks import crawl_product


# 컴퓨터/노트북/조립PC 하위 카테고리 검색어 목록
COMPUTER_CATEGORIES = {
    '노트북/데스크탑': [
        '노트북',
        '게이밍노트북',
        '브랜드PC',
        '조립PC',
        '게이밍PC',
    ],
    '모니터/복합기': [
        '모니터',
        '게이밍모니터',
    ],
    'PC부품': [
        'CPU',
        '그래픽카드',
        'SSD',
        'RAM',
        '메인보드',
        '파워서플라이',
        'PC케이스',
        'CPU쿨러',
    ],
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def search_products(keyword: str, limit: int = 10) -> list:
    """다나와 검색으로 상품 코드 목록 추출"""
    url = f"https://search.danawa.com/dsearch.php?query={keyword}&limit={limit}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'lxml')

        products = soup.select('.product_list .prod_item')

        result = []
        for item in products:
            # pcode 추출
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
                # 상품명 추출
                name_elem = item.select_one('.prod_name a') or item.select_one('.prod_name')
                name = name_elem.get_text(strip=True) if name_elem else 'Unknown'

                result.append({
                    'pcode': pcode,
                    'name': name[:50],
                })

        return result

    except Exception as e:
        print(f"검색 오류 ({keyword}): {e}")
        return []


def main():
    print("=" * 70)
    print("컴퓨터/노트북/조립PC 카테고리 상품 크롤링")
    print("=" * 70)

    # 기존 상품 확인
    existing_pcodes = set(
        ProductModel.objects.filter(deleted_at__isnull=True)
        .values_list('danawa_product_id', flat=True)
    )
    print(f"\n기존 상품 수: {len(existing_pcodes)}개")

    # 크롤링할 상품 코드 수집
    all_products = []

    for category_name, keywords in COMPUTER_CATEGORIES.items():
        print(f"\n[{category_name}]")

        for keyword in keywords:
            time.sleep(random.uniform(0.5, 1.0))  # 서버 부하 방지

            products = search_products(keyword, limit=5)
            new_products = [p for p in products if p['pcode'] not in existing_pcodes]

            print(f"  {keyword}: {len(products)}개 검색, {len(new_products)}개 신규")

            for p in new_products:
                if p['pcode'] not in [x['pcode'] for x in all_products]:
                    all_products.append(p)

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

        print(f"\n[{i}/{len(all_products)}] [{pcode}] {name}")

        try:
            result = crawl_product(pcode)

            if result.get('success'):
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
