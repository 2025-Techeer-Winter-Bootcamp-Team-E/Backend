#!/usr/bin/env python
"""상품을 세분화된 카테고리로 재분류하는 스크립트"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import logging
logging.disable(logging.DEBUG)

from modules.products.models import ProductModel
from modules.categories.models import CategoryModel


def get_or_create_category(parent, name):
    cat, _ = CategoryModel.objects.get_or_create(
        name=name, parent=parent, defaults={'deleted_at': None}
    )
    return cat


def main():
    # 최상위 카테고리
    root, _ = CategoryModel.objects.get_or_create(
        name='컴퓨터/노트북/조립PC', parent=None, defaults={'deleted_at': None}
    )

    # 상위 카테고리 생성
    cat_notebook = get_or_create_category(root, '노트북')
    cat_desktop = get_or_create_category(root, '데스크탑')
    cat_parts = get_or_create_category(root, 'PC부품')
    cat_monitor = get_or_create_category(root, '모니터')
    cat_peripheral = get_or_create_category(root, '주변기기')

    # 노트북 하위 카테고리
    sub_lg_gram = get_or_create_category(cat_notebook, 'LG 그램')
    sub_galaxy = get_or_create_category(cat_notebook, '삼성 갤럭시북')
    sub_macbook = get_or_create_category(cat_notebook, 'Apple 맥북')
    sub_gaming_nb = get_or_create_category(cat_notebook, '게이밍 노트북')
    sub_ultrabook = get_or_create_category(cat_notebook, '울트라북')
    sub_general_nb = get_or_create_category(cat_notebook, '일반 노트북')

    # 데스크탑 하위 카테고리
    sub_brand_pc = get_or_create_category(cat_desktop, '브랜드PC')
    sub_custom_pc = get_or_create_category(cat_desktop, '조립PC')
    sub_gaming_pc = get_or_create_category(cat_desktop, '게이밍PC')
    sub_mini_pc = get_or_create_category(cat_desktop, '미니PC')

    # PC부품 하위 카테고리
    sub_cpu = get_or_create_category(cat_parts, 'CPU')
    sub_gpu = get_or_create_category(cat_parts, '그래픽카드')
    sub_ssd = get_or_create_category(cat_parts, 'SSD')
    sub_ram = get_or_create_category(cat_parts, 'RAM')
    sub_mainboard = get_or_create_category(cat_parts, '메인보드')

    # 모니터 하위 카테고리
    sub_gaming_mon = get_or_create_category(cat_monitor, '게이밍 모니터')
    sub_4k_mon = get_or_create_category(cat_monitor, '4K 모니터')

    # 주변기기 하위 카테고리
    sub_keyboard = get_or_create_category(cat_peripheral, '키보드')
    sub_mouse = get_or_create_category(cat_peripheral, '마우스')

    print('카테고리 구조 생성 완료!')

    # 상품 재분류
    updated = 0
    for product in ProductModel.objects.filter(deleted_at__isnull=True):
        name = product.name.lower()
        brand = (product.brand or '').lower()
        old_cat = product.category.name if product.category else ''
        new_cat = None

        # 노트북 분류 - 브랜드/시리즈별
        if '그램' in name or 'gram' in name:
            new_cat = sub_lg_gram
        elif '갤럭시북' in name or 'galaxy' in name:
            new_cat = sub_galaxy
        elif '맥북' in name or 'macbook' in name:
            new_cat = sub_macbook
        elif any(x in name for x in ['rog', 'predator', 'legion', 'omen', 'nitro', 'tuf', 'sword', 'crosshair', 'katana']):
            # 게이밍 노트북 키워드
            if any(x in old_cat.lower() for x in ['노트북', '울트라북', '2in1']):
                new_cat = sub_gaming_nb
            elif '모니터' in old_cat.lower():
                new_cat = sub_gaming_mon
            elif any(x in old_cat.lower() for x in ['pc', '데스크탑']):
                new_cat = sub_gaming_pc
        elif '울트라북' in old_cat.lower():
            new_cat = sub_ultrabook
        elif any(x in old_cat.lower() for x in ['노트북', '2in1']):
            new_cat = sub_general_nb

        # 데스크탑 분류
        elif '브랜드pc' in old_cat.lower():
            new_cat = sub_brand_pc
        elif '조립pc' in old_cat.lower():
            new_cat = sub_custom_pc
        elif '다나와표준' in old_cat.lower():
            new_cat = sub_brand_pc
        elif '데스크탑' in old_cat.lower():
            if '미니' in name or 'mini' in name:
                new_cat = sub_mini_pc
            else:
                new_cat = sub_brand_pc

        # PC부품 분류
        elif 'cpu' in old_cat.lower():
            new_cat = sub_cpu
        elif '그래픽' in old_cat.lower():
            new_cat = sub_gpu
        elif 'ssd' in old_cat.lower():
            new_cat = sub_ssd
        elif 'ram' in old_cat.lower():
            new_cat = sub_ram
        elif '메인보드' in old_cat.lower():
            new_cat = sub_mainboard

        # 모니터 분류
        elif '4k' in old_cat.lower():
            new_cat = sub_4k_mon
        elif '모니터' in old_cat.lower():
            new_cat = sub_gaming_mon

        # 주변기기 분류
        elif '키보드' in old_cat.lower() or '키보드' in name:
            new_cat = sub_keyboard
        elif '마우스' in old_cat.lower() or '마우스' in name:
            new_cat = sub_mouse
        elif '입력' in old_cat.lower():
            if '마우스' in name or 'mouse' in name:
                new_cat = sub_mouse
            else:
                new_cat = sub_keyboard

        if new_cat:
            current_cat_id = product.category.id if product.category else None
            if current_cat_id != new_cat.id:
                product.category = new_cat
                product.save()
                updated += 1

    print(f'재분류된 상품: {updated}개')

    # 결과 출력
    print('\n' + '=' * 60)
    print('세분화된 카테고리별 상품 수')
    print('=' * 60)

    for parent in CategoryModel.objects.filter(parent=root, deleted_at__isnull=True).order_by('name'):
        children = CategoryModel.objects.filter(parent=parent, deleted_at__isnull=True).order_by('name')
        parent_total = sum(
            ProductModel.objects.filter(category=c, deleted_at__isnull=True).count()
            for c in children
        )
        if parent_total > 0:
            print(f'\n[{parent.name}] ({parent_total}개)')
            for child in children:
                count = ProductModel.objects.filter(category=child, deleted_at__isnull=True).count()
                if count > 0:
                    print(f'  └─ {child.name}: {count}개')

    total = ProductModel.objects.filter(deleted_at__isnull=True).count()
    print(f'\n총 상품 수: {total}개')


if __name__ == '__main__':
    main()
