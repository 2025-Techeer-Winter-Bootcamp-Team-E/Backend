#!/usr/bin/env python
"""하위 카테고리를 더 세분화하는 스크립트"""
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
    root = CategoryModel.objects.get(name='컴퓨터/노트북/조립PC', parent__isnull=True)

    # 기존 중간 카테고리 가져오기
    cat_notebook = CategoryModel.objects.get(name='노트북', parent=root)
    cat_desktop = CategoryModel.objects.get(name='데스크탑', parent=root)

    # 기존 하위 카테고리 가져오기
    lg_gram = CategoryModel.objects.get(name='LG 그램', parent=cat_notebook)
    galaxy = CategoryModel.objects.get(name='삼성 갤럭시북', parent=cat_notebook)
    gaming_nb = CategoryModel.objects.get(name='게이밍 노트북', parent=cat_notebook)
    brand_pc = CategoryModel.objects.get(name='브랜드PC', parent=cat_desktop)
    mini_pc = CategoryModel.objects.get(name='미니PC', parent=cat_desktop)

    # LG 그램 하위 카테고리 생성
    gram_14 = get_or_create_category(lg_gram, '그램 14')
    gram_15 = get_or_create_category(lg_gram, '그램 15')
    gram_16 = get_or_create_category(lg_gram, '그램 16')
    gram_17 = get_or_create_category(lg_gram, '그램 17')

    # 삼성 갤럭시북 하위 카테고리 생성
    galaxy_3 = get_or_create_category(galaxy, '갤럭시북3')
    galaxy_4 = get_or_create_category(galaxy, '갤럭시북4')
    galaxy_5 = get_or_create_category(galaxy, '갤럭시북5')
    galaxy_pro = get_or_create_category(galaxy, '갤럭시북 프로')
    galaxy_pro360 = get_or_create_category(galaxy, '갤럭시북 프로360')

    # 게이밍 노트북 하위 카테고리 생성 (브랜드별)
    gaming_asus = get_or_create_category(gaming_nb, 'ASUS ROG/TUF')
    gaming_msi = get_or_create_category(gaming_nb, 'MSI')
    gaming_lenovo = get_or_create_category(gaming_nb, '레노버 Legion')
    gaming_hp = get_or_create_category(gaming_nb, 'HP OMEN')
    gaming_acer = get_or_create_category(gaming_nb, '에이서 Predator')
    gaming_other = get_or_create_category(gaming_nb, '기타 게이밍')

    # 브랜드PC 하위 카테고리 생성
    brand_samsung = get_or_create_category(brand_pc, '삼성')
    brand_lg = get_or_create_category(brand_pc, 'LG')
    brand_hp = get_or_create_category(brand_pc, 'HP')
    brand_lenovo = get_or_create_category(brand_pc, '레노버')
    brand_danawa = get_or_create_category(brand_pc, '다나와표준PC')
    brand_other = get_or_create_category(brand_pc, '기타 브랜드')

    # 미니PC 하위 카테고리 생성
    mini_intel = get_or_create_category(mini_pc, '인텔 NUC')
    mini_asus = get_or_create_category(mini_pc, 'ASUS')
    mini_beelink = get_or_create_category(mini_pc, 'Beelink')
    mini_other = get_or_create_category(mini_pc, '기타 미니PC')

    print('세부 카테고리 구조 생성 완료!')

    # 상품 재분류
    updated = 0

    for product in ProductModel.objects.filter(deleted_at__isnull=True):
        if not product.category:
            continue

        name = product.name.lower()
        brand = (product.brand or '').lower()
        current_cat = product.category
        new_cat = None

        # LG 그램 세분화
        if current_cat == lg_gram:
            if '17' in product.name:
                new_cat = gram_17
            elif '16' in product.name:
                new_cat = gram_16
            elif '15' in product.name:
                new_cat = gram_15
            elif '14' in product.name:
                new_cat = gram_14

        # 삼성 갤럭시북 세분화
        elif current_cat == galaxy:
            name_lower = product.name.lower()
            if '프로360' in product.name or 'pro360' in name_lower:
                new_cat = galaxy_pro360
            elif '프로' in product.name and '360' not in product.name:
                new_cat = galaxy_pro
            elif '북5' in product.name or 'book5' in name_lower:
                new_cat = galaxy_5
            elif '북4' in product.name or 'book4' in name_lower:
                new_cat = galaxy_4
            elif '북3' in product.name or 'book3' in name_lower:
                new_cat = galaxy_3

        # 게이밍 노트북 세분화
        elif current_cat == gaming_nb:
            if 'asus' in brand or 'rog' in name or 'tuf' in name:
                new_cat = gaming_asus
            elif 'msi' in brand or 'msi' in name:
                new_cat = gaming_msi
            elif '레노버' in brand or 'legion' in name:
                new_cat = gaming_lenovo
            elif 'hp' in brand or 'omen' in name:
                new_cat = gaming_hp
            elif '에이서' in brand or 'predator' in name or 'nitro' in name:
                new_cat = gaming_acer
            else:
                new_cat = gaming_other

        # 브랜드PC 세분화
        elif current_cat == brand_pc:
            if 'lg' in brand or 'lg전자' in brand:
                new_cat = brand_lg
            elif '삼성' in brand:
                new_cat = brand_samsung
            elif 'hp' in brand:
                new_cat = brand_hp
            elif '레노버' in brand:
                new_cat = brand_lenovo
            elif '다나와' in product.name:
                new_cat = brand_danawa
            else:
                new_cat = brand_other

        # 미니PC 세분화
        elif current_cat == mini_pc:
            if 'intel' in name or '인텔' in product.name or 'nuc' in name:
                new_cat = mini_intel
            elif 'asus' in brand:
                new_cat = mini_asus
            elif 'beelink' in name or '비링크' in product.name:
                new_cat = mini_beelink
            else:
                new_cat = mini_other

        if new_cat and new_cat != current_cat:
            product.category = new_cat
            product.save()
            updated += 1

    print(f'재분류된 상품: {updated}개')

    # 결과 출력
    print('\n' + '=' * 70)
    print('세분화된 카테고리 구조 (3단계)')
    print('=' * 70)

    for level1 in CategoryModel.objects.filter(parent=root, deleted_at__isnull=True).order_by('name'):
        level1_total = 0
        level1_children = []

        for level2 in CategoryModel.objects.filter(parent=level1, deleted_at__isnull=True).order_by('name'):
            level2_count = ProductModel.objects.filter(category=level2, deleted_at__isnull=True).count()
            level3_items = []

            for level3 in CategoryModel.objects.filter(parent=level2, deleted_at__isnull=True).order_by('name'):
                level3_count = ProductModel.objects.filter(category=level3, deleted_at__isnull=True).count()
                if level3_count > 0:
                    level3_items.append((level3.name, level3_count))
                    level1_total += level3_count

            if level3_items:
                level1_children.append((level2.name, level3_items))
            elif level2_count > 0:
                level1_children.append((level2.name, level2_count))
                level1_total += level2_count

        if level1_total > 0:
            print(f'\n[{level1.name}] ({level1_total}개)')
            for item in level1_children:
                if isinstance(item[1], list):
                    # 3단계 카테고리
                    total = sum(x[1] for x in item[1])
                    print(f'  └─ {item[0]} ({total}개)')
                    for sub_name, sub_count in item[1]:
                        print(f'      └─ {sub_name}: {sub_count}개')
                else:
                    # 2단계 카테고리
                    print(f'  └─ {item[0]}: {item[1]}개')

    total = ProductModel.objects.filter(deleted_at__isnull=True).count()
    print(f'\n총 상품 수: {total}개')


if __name__ == '__main__':
    main()
