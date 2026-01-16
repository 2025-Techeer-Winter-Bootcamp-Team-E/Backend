"""
Danawa product crawler.

다나와에서 상품 정보를 크롤링하는 모듈입니다.
CSV 데이터 명세서 기준으로 구현되었습니다.
"""
import logging
import time
import random
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from dateutil.relativedelta import relativedelta

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ============================================================
# 데이터 클래스 정의
# ============================================================

@dataclass
class ProductInfo:
    """크롤링된 상품 기본 정보."""
    # 기본정보
    pcode: str                                    # 상품코드
    product_name: str                             # 상품명
    brand: str                                    # 브랜드
    registration_date: Optional[str] = None       # 등록월
    product_status: Optional[str] = None          # 상품상태
    image_url: Optional[str] = None               # 대표이미지URL
    additional_images: List[str] = field(default_factory=list)  # 추가이미지URL목록
    detail_page_images: List[str] = field(default_factory=list)  # 상세페이지이미지URL
    product_description_images: List[str] = field(default_factory=list)  # 제품설명이미지URL

    # 카테고리
    category_1: Optional[str] = None              # 대분류
    category_2: Optional[str] = None              # 중분류
    category_3: Optional[str] = None              # 소분류
    category_4: Optional[str] = None              # 세분류

    # 가격정보
    price: int = 0                                # 현재가
    min_price: int = 0                            # 최저가

    # 스펙정보
    spec: Dict[str, Any] = field(default_factory=dict)  # 스펙테이블
    spec_summary: List[str] = field(default_factory=list)  # 주요스펙요약

    # 리뷰통계
    mall_review_count: int = 0                    # 쇼핑몰리뷰수


@dataclass
class MallInfo:
    """쇼핑몰 가격 정보."""
    mall_name: str                                # 판매처명 (tasks.py 호환)
    price: int                                    # 현재가
    product_url: Optional[str] = None             # 판매페이지URL (tasks.py 호환)
    logo_url: Optional[str] = None                # 판매처로고 (tasks.py 호환)
    # 별칭 (CSV 명세서 호환)
    seller_name: Optional[str] = None
    seller_url: Optional[str] = None
    seller_logo: Optional[str] = None


@dataclass
class PriceHistory:
    """월별 가격 변동 정보."""
    month_offset: int                             # 몇 개월 전 (1~24)
    price: Optional[int] = None                   # 해당 월 최저가
    date: Optional[str] = None                    # 날짜 문자열 (예: "24-04", "25-01")
    fulldate: Optional[str] = None                # 전체 날짜 (예: "25-12-23")


@dataclass
class ReviewInfo:
    """다나와 리뷰 정보."""
    shop_name: Optional[str] = None               # 리뷰 쇼핑몰명
    reviewer_name: Optional[str] = None           # 리뷰 작성자 (tasks.py 호환)
    rating: Optional[int] = None                  # 리뷰 평점 (1-5)
    review_date: Optional[str] = None             # 리뷰 작성일
    content: Optional[str] = None                 # 리뷰 내용
    review_images: List[str] = field(default_factory=list)  # 리뷰 이미지
    # 별칭 (CSV 명세서 호환)
    reviewer: Optional[str] = None


# ============================================================
# 다나와 크롤러
# ============================================================

class DanawaCrawler:
    """
    다나와 크롤러.

    CSV 데이터 명세서의 모든 필드를 크롤링합니다.

    사용 예시:
        crawler = DanawaCrawler()

        # 상품 정보 크롤링
        product = crawler.get_product_info("44762393")

        # 판매처 정보 크롤링
        mall_list = crawler.get_mall_prices("44762393")

        # 가격 변동 이력 크롤링
        price_history = crawler.get_price_history("44762393")

        # 리뷰 크롤링
        reviews = crawler.get_reviews("44762393")
    """

    BASE_URL = "https://prod.danawa.com"
    SEARCH_URL = "https://search.danawa.com"
    CHART_API_URL = "https://prod.danawa.com/info/ajax/getChartData.ajax.php"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.danawa.com/',
    }

    def __init__(self, delay_range: tuple = (1, 3)):
        """
        Args:
            delay_range: 요청 간 딜레이 범위 (초). 서버 부하 방지용.
        """
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.delay_range = delay_range

    def _delay(self):
        """요청 간 랜덤 딜레이."""
        time.sleep(random.uniform(*self.delay_range))

    def _get_page(self, url: str, params: dict = None) -> Optional[BeautifulSoup]:
        """페이지 HTML 가져오기."""
        try:
            self._delay()
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def _get_json(self, url: str, params: dict = None) -> Optional[dict]:
        """JSON API 호출."""
        try:
            self._delay()
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.error(f"Failed to fetch JSON from {url}: {e}")
            return None

    # ============================================================
    # 상품 기본 정보 크롤링
    # ============================================================

    def get_product_info(self, pcode: str) -> Optional[ProductInfo]:
        """
        상품 상세 정보 크롤링.

        Args:
            pcode: 다나와 상품 코드 (예: "44762393")

        Returns:
            ProductInfo 또는 None
        """
        url = f"{self.BASE_URL}/info/?pcode={pcode}"
        soup = self._get_page(url)

        if not soup:
            return None

        try:
            # 상품명 - .prod_tit 안의 .title span에서 가져옴
            name_elem = soup.select_one('.prod_tit .title')
            if not name_elem:
                name_elem = soup.select_one('.prod_tit')
            product_name = name_elem.get_text(strip=True) if name_elem else "Unknown"

            # 브랜드
            brand = self._parse_brand(soup)

            # 등록월
            registration_date = self._parse_registration_date(soup)

            # 상품상태
            product_status = self._parse_product_status(soup)

            # 최저가
            min_price = self._parse_min_price(soup)

            # 현재가 (= 최저가)
            price = min_price

            # 카테고리
            categories = self._parse_categories(soup)

            # 스펙 정보
            spec, spec_summary = self._parse_spec(soup)

            # 이미지 URL들
            image_url = self._parse_main_image(soup)
            additional_images = self._parse_additional_images(soup)
            detail_page_images = self._parse_detail_page_images(soup, pcode)
            product_description_images = self._parse_product_description_images(soup)

            # 쇼핑몰 리뷰 수
            mall_review_count = self._parse_mall_review_count(soup)

            return ProductInfo(
                pcode=pcode,
                product_name=product_name,
                brand=brand,
                registration_date=registration_date,
                product_status=product_status,
                image_url=image_url,
                additional_images=additional_images,
                detail_page_images=detail_page_images,
                product_description_images=product_description_images,
                category_1=categories.get('category_1'),
                category_2=categories.get('category_2'),
                category_3=categories.get('category_3'),
                category_4=categories.get('category_4'),
                price=price,
                min_price=min_price,
                spec=spec,
                spec_summary=spec_summary,
                mall_review_count=mall_review_count,
            )

        except Exception as e:
            logger.error(f"Failed to parse product {pcode}: {e}")
            return None

    def _parse_brand(self, soup: BeautifulSoup) -> str:
        """브랜드 파싱."""
        import re

        # 1. spec_list에서 찾기
        brand_elem = soup.select_one('.spec_list .makerName')
        if brand_elem:
            return brand_elem.get_text(strip=True)

        # 2. made_info에서 제조사 추출
        maker_elem = soup.select_one('.made_info')
        if maker_elem:
            text = maker_elem.get_text(strip=True)

            # "제조사:" 뒤의 값 추출 (예: "제조사:APPLE")
            match = re.search(r'제조사[:\s]*([^ㅣ\|]+)', text)
            if match:
                brand = match.group(1).strip()
                # 빈 값이 아니고 ":"만 있는 경우가 아니면 반환
                if brand and brand != ':':
                    return brand

            # 3. 제조사가 비어있으면 "이미지출처"에서 추출 (예: "이미지출처: LG전자")
            match = re.search(r'이미지출처[:\s]*([^ㅣ\|]+)', text)
            if match:
                brand = match.group(1).strip()
                if brand:
                    return brand

        # 4. 상품명에서 브랜드 추출 시도 (첫 단어)
        prod_name = soup.select_one('.prod_tit .title')
        if prod_name:
            name_text = prod_name.get_text(strip=True)
            # 알려진 브랜드 패턴 매칭
            known_brands = ['삼성전자', 'LG전자', 'APPLE', 'MSI', 'ASUS', 'AULA', 'ATK', '로지텍', '레노버', 'HP', 'DELL']
            for brand in known_brands:
                if brand in name_text:
                    return brand
            # 첫 단어 추출
            first_word = name_text.split()[0] if name_text else ''
            if first_word and len(first_word) <= 10:
                return first_word

        return ""

    def _parse_registration_date(self, soup: BeautifulSoup) -> Optional[str]:
        """등록월 파싱."""
        import re

        # 1. spec_list에서 찾기
        reg_elem = soup.select_one('.spec_list .regDate')
        if reg_elem:
            return reg_elem.get_text(strip=True)

        # 2. made_info에서 등록월 추출 (예: "등록월: 2025.09.ㅣ...")
        maker_elem = soup.select_one('.made_info')
        if maker_elem:
            text = maker_elem.get_text(strip=True)
            match = re.search(r'등록월[:\s]*([\d.]+)', text)
            if match:
                return match.group(1).strip()

        return None

    def _parse_product_status(self, soup: BeautifulSoup) -> Optional[str]:
        """상품상태 파싱."""
        status_elem = soup.select_one('.prod_status')
        if status_elem:
            return status_elem.get_text(strip=True)
        return "판매중"

    def _parse_min_price(self, soup: BeautifulSoup) -> int:
        """최저가 파싱."""
        import re
        from collections import Counter

        # 1. 기존 선택자 시도
        price_elem = soup.select_one('.lowest_price .lwst_prc .prc')
        if price_elem:
            price_text = price_elem.get_text(strip=True).replace(',', '').replace('원', '')
            if price_text.isdigit():
                return int(price_text)

        # 2. summary_left 영역에서 가격 추출 (메인 가격 영역)
        summary_left = soup.select_one('.summary_left')
        if summary_left:
            summary_text = summary_left.get_text()
            prices = re.findall(r'([\d,]+)\s*원', summary_text)

            if prices:
                # 가격들을 정수로 변환
                valid_prices = []
                for p in prices:
                    try:
                        price_val = int(p.replace(',', ''))
                        # 최소 1,000원 이상 (배송비 등 제외)
                        if price_val >= 1000:
                            valid_prices.append(price_val)
                    except ValueError:
                        continue

                if valid_prices:
                    # 가격대별 그룹핑하여 가장 많이 나온 가격대의 최저가 반환
                    # 이렇게 하면 배송비, 포인트 등을 제외하고 실제 상품 가격을 찾을 수 있음
                    price_ranges = {}
                    for p in valid_prices:
                        # 가격대 구간 (만원 단위)
                        range_key = p // 10000
                        if range_key not in price_ranges:
                            price_ranges[range_key] = []
                        price_ranges[range_key].append(p)

                    # 가장 많은 가격이 속한 구간 찾기
                    if price_ranges:
                        most_common_range = max(price_ranges.keys(), key=lambda k: len(price_ranges[k]))
                        # 해당 구간의 최저가 반환
                        return min(price_ranges[most_common_range])

        # 3. 페이지 전체에서 가격 패턴 추출 (fallback)
        page_text = str(soup)
        prices = re.findall(r'([\d,]+)원', page_text)

        if prices:
            valid_prices = []
            for p in prices:
                try:
                    price_val = int(p.replace(',', ''))
                    if price_val >= 1000:  # 최소 1,000원 이상
                        valid_prices.append(price_val)
                except ValueError:
                    continue

            if valid_prices:
                # 같은 로직 적용
                price_ranges = {}
                for p in valid_prices:
                    range_key = p // 10000
                    if range_key not in price_ranges:
                        price_ranges[range_key] = []
                    price_ranges[range_key].append(p)

                if price_ranges:
                    most_common_range = max(price_ranges.keys(), key=lambda k: len(price_ranges[k]))
                    return min(price_ranges[most_common_range])

        return 0

    def _parse_categories(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """카테고리 파싱."""
        import re

        categories = {
            'category_1': None,
            'category_2': None,
            'category_3': None,
            'category_4': None,
        }

        # 1. location_category 시도
        breadcrumb = soup.select('.location_category a')
        if breadcrumb:
            for i, item in enumerate(breadcrumb[:4], 1):
                categories[f'category_{i}'] = item.get_text(strip=True)
            return categories

        # 2. JavaScript 변수에서 카테고리 추출
        # 다나와 페이지의 스크립트에 Category 정보가 포함됨
        page_html = str(soup)

        # Category 변수 패턴 찾기 (예: Category: "태블릿/휴대폰")
        cat_matches = re.findall(r"['\"]?Category['\"]?\s*[=:]\s*['\"]([^'\"]+)['\"]", page_html)

        if cat_matches:
            # 중복 제거하고 유효한 카테고리만 필터링
            seen = set()
            unique_cats = []
            for cat in cat_matches:
                # 무효한 값 필터링
                if cat and cat not in seen and not cat.startswith('review') and len(cat) < 50:
                    seen.add(cat)
                    unique_cats.append(cat)

            # 카테고리 할당 (최대 4개)
            for i, cat in enumerate(unique_cats[:4], 1):
                categories[f'category_{i}'] = cat

            if any(categories.values()):
                return categories

        # 3. 카테고리 링크에서 추출
        cat_links = soup.select('.cate_wrap a')
        if cat_links:
            idx = 1
            for item in cat_links:
                text = item.get_text(strip=True)
                # VS검색, 메인 네비게이션 항목 제외
                if text and not text.startswith('VS') and idx <= 4:
                    if '·' not in text and len(text) < 30:  # 메인 카테고리 구분
                        categories[f'category_{idx}'] = text
                        idx += 1
            if any(categories.values()):
                return categories

        # 4. og:description 메타 태그에서 카테고리 추출 시도
        og_desc = soup.select_one('meta[property="og:description"]')
        if og_desc:
            content = og_desc.get('content', '')
            if '>' in content:
                parts = content.split('>')
                for i, part in enumerate(parts[:4], 1):
                    categories[f'category_{i}'] = part.strip()

        return categories

    def _parse_spec(self, soup: BeautifulSoup) -> tuple:
        """스펙 정보 파싱."""
        import re

        spec = {}
        spec_summary = []

        try:
            # 1. 스펙 테이블 파싱 (기존 방식)
            spec_items = soup.select('.spec_tbl tr')
            for row in spec_items:
                th = row.select_one('th')
                td = row.select_one('td')
                if th and td:
                    key = th.get_text(strip=True)
                    value = td.get_text(strip=True)
                    spec[key] = value

            # 2. .spec_list에서 "/" 구분 문자열 파싱
            # 다나와 스펙 형식: "스마트폰(바형)/화면:15.9cm/120Hz/램:8GB/..."
            spec_list_elem = soup.select_one('.spec_list')
            if spec_list_elem:
                spec_text = spec_list_elem.get_text(strip=True)

                # "/"로 분리
                spec_items_text = spec_text.split('/')

                for item in spec_items_text:
                    item = item.strip()
                    if not item:
                        continue

                    # spec_summary에 추가 (요약용)
                    spec_summary.append(item)

                    # key:value 형식이면 spec dict에 추가
                    if ':' in item:
                        parts = item.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key and value:
                                spec[key] = value
                    else:
                        # key:value가 아닌 경우 (예: "5G", "120Hz")
                        # 특성 이름으로 저장
                        spec[item] = True

            # 3. 주요 스펙 요약 (li 태그가 있는 경우)
            if not spec_summary:
                summary_items = soup.select('.spec_list li')
                for item in summary_items[:10]:
                    text = item.get_text(strip=True)
                    if text:
                        spec_summary.append(text)

        except Exception as e:
            logger.warning(f"Failed to parse spec: {e}")

        return spec, spec_summary

    def _parse_main_image(self, soup: BeautifulSoup) -> Optional[str]:
        """대표 이미지 URL 파싱."""
        img_elem = soup.select_one('.photo_w img')
        if img_elem:
            src = img_elem.get('src') or img_elem.get('data-src')
            if src:
                return src if src.startswith('http') else f"https:{src}"
        return None

    def _parse_additional_images(self, soup: BeautifulSoup) -> List[str]:
        """추가 이미지 URL 파싱."""
        images = []
        img_items = soup.select('.thumb_list img')
        for img in img_items[:10]:
            src = img.get('src') or img.get('data-src')
            if src:
                url = src if src.startswith('http') else f"https:{src}"
                images.append(url)
        return images

    def _parse_detail_page_images(self, soup: BeautifulSoup, pcode: str) -> List[str]:
        """상세페이지 이미지 URL 파싱 (AJAX 필요할 수 있음)."""
        images = []
        detail_imgs = soup.select('.detail_cont img')
        for img in detail_imgs:
            src = img.get('src') or img.get('data-src')
            if src:
                url = src if src.startswith('http') else f"https:{src}"
                images.append(url)
        return images

    def _parse_product_description_images(self, soup: BeautifulSoup) -> List[str]:
        """제품설명 이미지 URL 파싱."""
        images = []
        desc_imgs = soup.select('.prod_desc img')
        for img in desc_imgs:
            src = img.get('src') or img.get('data-src')
            if src:
                url = src if src.startswith('http') else f"https:{src}"
                images.append(url)
        return images

    def _parse_mall_review_count(self, soup: BeautifulSoup) -> int:
        """쇼핑몰 리뷰 수 파싱."""
        count_elem = soup.select_one('.mall_review_count')
        if count_elem:
            text = count_elem.get_text(strip=True).replace(',', '')
            if text.isdigit():
                return int(text)
        return 0

    # ============================================================
    # 판매처 정보 크롤링
    # ============================================================

    def get_mall_prices(self, pcode: str) -> List[MallInfo]:
        """
        쇼핑몰별 가격 정보 크롤링.

        Args:
            pcode: 다나와 상품 코드

        Returns:
            MallInfo 리스트
        """
        url = f"{self.BASE_URL}/info/?pcode={pcode}"
        soup = self._get_page(url)

        if not soup:
            return []

        mall_list = []

        try:
            mall_items = soup.select('.mall_list tbody tr')

            for item in mall_items:
                # 판매처명
                name_elem = item.select_one('.mall_name')
                seller_name = name_elem.get_text(strip=True) if name_elem else None

                # 가격
                price_elem = item.select_one('.price_sect .price')
                price = 0
                if price_elem:
                    price_text = price_elem.get_text(strip=True).replace(',', '').replace('원', '')
                    price = int(price_text) if price_text.isdigit() else 0

                # 판매페이지 URL
                link_elem = item.select_one('a.mall_link')
                seller_url = link_elem.get('href') if link_elem else None

                # 판매처 로고
                logo_elem = item.select_one('.mall_logo img')
                seller_logo = None
                if logo_elem:
                    src = logo_elem.get('src')
                    seller_logo = src if src and src.startswith('http') else f"https:{src}" if src else None

                if seller_name and price > 0:
                    mall_list.append(MallInfo(
                        mall_name=seller_name,
                        price=price,
                        product_url=seller_url,
                        logo_url=seller_logo,
                        seller_name=seller_name,
                        seller_url=seller_url,
                        seller_logo=seller_logo,
                    ))

        except Exception as e:
            logger.error(f"Failed to parse mall prices for {pcode}: {e}")

        return mall_list

    # ============================================================
    # 가격 변동 이력 크롤링
    # ============================================================

    PRICE_HISTORY_API_URL = "https://prod.danawa.com/info/ajax/getProductPriceList.ajax.php"

    def get_price_history(self, pcode: str, months: int = 24) -> List[PriceHistory]:
        """
        월별 가격 변동 이력 크롤링.

        다나와 가격 그래프 API를 사용하여 최대 24개월간의 월별 최저가를 조회합니다.

        Args:
            pcode: 다나와 상품 코드
            months: 조회할 개월 수 (기본 24개월, 지원: 1, 3, 6, 12, 24)

        Returns:
            PriceHistory 리스트 (최신순)
        """
        # 가격 이력 API 호출
        params = {
            'productCode': pcode,
        }

        # API 요청 헤더 설정 (Ajax 요청임을 명시)
        ajax_headers = self.HEADERS.copy()
        ajax_headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'{self.BASE_URL}/info/?pcode={pcode}',
        })

        history = []

        try:
            self._delay()
            response = self.session.get(
                self.PRICE_HISTORY_API_URL,
                params=params,
                headers=ajax_headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            # 요청한 개월 수에 해당하는 키 선택 (1, 3, 6, 12, 24 중)
            period_key = str(months) if str(months) in data else '24'
            period_data = data.get(period_key, {})

            result_list = period_data.get('result', [])

            # 결과를 PriceHistory 객체로 변환
            for i, item in enumerate(result_list):
                date_str = item.get('date', '')  # 예: "24-04" 또는 "01-06"
                fulldate_str = item.get('Fulldate', '')  # 예: "25-12-23"
                min_price = item.get('minPrice')

                history.append(PriceHistory(
                    month_offset=len(result_list) - i,  # 오래된 데이터가 먼저 오므로 역순 인덱스
                    price=min_price,
                    date=date_str,
                    fulldate=fulldate_str,
                ))

            logger.info(f"Fetched {len(history)} price history records for {pcode}")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch price history for {pcode}: {e}")
            # API 실패 시 빈 이력 반환
            for i in range(1, months + 1):
                history.append(PriceHistory(month_offset=i, price=None))
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse price history response for {pcode}: {e}")
            for i in range(1, months + 1):
                history.append(PriceHistory(month_offset=i, price=None))

        return history

    def get_price_history_detailed(self, pcode: str) -> Dict[str, Any]:
        """
        상세 가격 이력 조회 (모든 기간 데이터 포함).

        Args:
            pcode: 다나와 상품 코드

        Returns:
            {
                '1': {'count': N, 'result': [...], 'minPrice': X, 'maxPrice': Y},
                '3': {...},
                '6': {...},
                '12': {...},
                '24': {...}
            }
        """
        params = {'productCode': pcode}

        ajax_headers = self.HEADERS.copy()
        ajax_headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'{self.BASE_URL}/info/?pcode={pcode}',
        })

        try:
            self._delay()
            response = self.session.get(
                self.PRICE_HISTORY_API_URL,
                params=params,
                headers=ajax_headers,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch detailed price history for {pcode}: {e}")
            return {}

    # ============================================================
    # 리뷰 크롤링
    # ============================================================

    def get_reviews(self, pcode: str, limit: int = 20) -> List[ReviewInfo]:
        """
        다나와 리뷰 크롤링.

        Args:
            pcode: 다나와 상품 코드
            limit: 최대 리뷰 수

        Returns:
            ReviewInfo 리스트
        """
        url = f"{self.BASE_URL}/info/?pcode={pcode}"
        soup = self._get_page(url)

        if not soup:
            return []

        reviews = []

        try:
            review_items = soup.select('.danawa_review_list .review_item')[:limit]

            for item in review_items:
                # 쇼핑몰명
                shop_elem = item.select_one('.shop_name')
                shop_name = shop_elem.get_text(strip=True) if shop_elem else None

                # 작성자
                reviewer_elem = item.select_one('.reviewer')
                reviewer = reviewer_elem.get_text(strip=True) if reviewer_elem else None

                # 평점
                rating_elem = item.select_one('.star_score')
                rating = None
                if rating_elem:
                    # 별점 파싱 (예: "4점" -> 4)
                    rating_text = rating_elem.get_text(strip=True).replace('점', '')
                    rating = int(rating_text) if rating_text.isdigit() else None

                # 작성일
                date_elem = item.select_one('.review_date')
                review_date = date_elem.get_text(strip=True) if date_elem else None

                # 내용
                content_elem = item.select_one('.review_content')
                content = content_elem.get_text(strip=True) if content_elem else None

                # 이미지
                review_images = []
                img_items = item.select('.review_img img')
                for img in img_items:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        url = src if src.startswith('http') else f"https:{src}"
                        review_images.append(url)

                reviews.append(ReviewInfo(
                    shop_name=shop_name,
                    reviewer_name=reviewer,
                    reviewer=reviewer,  # 별칭
                    rating=rating,
                    review_date=review_date,
                    content=content,
                    review_images=review_images,
                ))

        except Exception as e:
            logger.error(f"Failed to parse reviews for {pcode}: {e}")

        return reviews

    # ============================================================
    # 검색 기능
    # ============================================================

    def search_products(
        self,
        keyword: str,
        category_code: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        상품 검색.

        Args:
            keyword: 검색 키워드
            category_code: 카테고리 코드 (선택)
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트 (pcode, product_name, price)
        """
        params = {
            'query': keyword,
            'originalQuery': keyword,
            'volumeType': 'vmvs',
            'page': 1,
            'limit': limit,
        }

        if category_code:
            params['categoryCode'] = category_code

        url = f"{self.SEARCH_URL}/dsearch.php"
        soup = self._get_page(url, params)

        if not soup:
            return []

        results = []

        try:
            product_items = soup.select('.product_list .prod_item')[:limit]

            for item in product_items:
                # pcode는 data-pcode 또는 id에서 추출 (productItem12345678 형식)
                pcode = item.get('data-pcode', '')
                if not pcode:
                    item_id = item.get('id', '')
                    if item_id.startswith('productItem'):
                        pcode = item_id.replace('productItem', '')

                # 상품명
                name_elem = item.select_one('.prod_name a') or item.select_one('.prod_name')
                product_name = name_elem.get_text(strip=True) if name_elem else ""

                # 가격
                price_elem = item.select_one('.price_sect .price') or item.select_one('.price em')
                price = 0
                if price_elem:
                    import re
                    price_text = re.sub(r'[^\d]', '', price_elem.get_text(strip=True))
                    price = int(price_text) if price_text.isdigit() else 0

                if pcode:
                    results.append({
                        'danawa_product_id': pcode,
                        'pcode': pcode,
                        'name': product_name,
                        'product_name': product_name,
                        'price': price,
                    })

        except Exception as e:
            logger.error(f"Failed to search products for '{keyword}': {e}")

        return results

    # ============================================================
    # 전체 상품 데이터 크롤링 (통합)
    # ============================================================

    def crawl_full_product_data(self, pcode: str) -> Optional[Dict[str, Any]]:
        """
        상품의 모든 데이터를 한 번에 크롤링.

        Args:
            pcode: 다나와 상품 코드

        Returns:
            전체 상품 데이터 딕셔너리
        """
        logger.info(f"Starting full crawl for product {pcode}")

        # 1. 기본 정보
        product_info = self.get_product_info(pcode)
        if not product_info:
            return None

        # 2. 판매처 정보
        mall_list = self.get_mall_prices(pcode)

        # 3. 가격 변동 이력
        price_history = self.get_price_history(pcode)

        # 4. 리뷰
        reviews = self.get_reviews(pcode)

        return {
            'product': product_info,
            'product_info': product_info,  # 호환성을 위해 유지
            'mall_prices': mall_list,
            'mall_list': mall_list,  # 호환성을 위해 유지
            'price_history': price_history,
            'reviews': reviews,
        }

    def close(self):
        """세션 종료."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.close()
