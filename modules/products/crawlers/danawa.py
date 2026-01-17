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
    seller_name: str                              # 판매처명
    price: int                                    # 현재가
    seller_url: Optional[str] = None              # 판매페이지URL
    seller_logo: Optional[str] = None             # 판매처로고


@dataclass
class PriceHistory:
    """월별 가격 변동 정보."""
    month_offset: int                             # 몇 개월 전 (1~24)
    price: Optional[int] = None                   # 해당 월 최저가


@dataclass
class ReviewInfo:
    """다나와 리뷰 정보."""
    shop_name: Optional[str] = None               # 리뷰 쇼핑몰명
    reviewer: Optional[str] = None                # 리뷰 작성자
    rating: Optional[int] = None                  # 리뷰 평점 (1-5)
    review_date: Optional[str] = None             # 리뷰 작성일
    content: Optional[str] = None                 # 리뷰 내용
    review_images: List[str] = field(default_factory=list)  # 리뷰 이미지


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
            # 상품명 (불필요한 텍스트 제거)
            name_elem = soup.select_one('.prod_tit')
            if name_elem:
                # 버튼, 링크 등 제거
                for btn in name_elem.select('.btn_vs_compare, .btn_vs, .vs_compare, button, a, span'):
                    btn.decompose()
                product_name = name_elem.get_text(strip=True)
                # 불필요한 텍스트 제거
                remove_texts = ['VS검색하기', 'VS검색 도움말', '추천상품과스펙비교하세요', '닫기']
                for txt in remove_texts:
                    product_name = product_name.replace(txt, '')
                product_name = product_name.strip()
            else:
                product_name = None

            # meta 태그에서 fallback (더 깔끔한 상품명)
            if not product_name or len(product_name) < 5:
                meta_title = soup.select_one('meta[property="og:title"]')
                if meta_title:
                    product_name = meta_title.get('content', 'Unknown').replace('[다나와] ', '')
                else:
                    product_name = "Unknown"

            # 브랜드 (상품명에서 추출)
            brand = self._parse_brand(soup, product_name)

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

    def _parse_brand(self, soup: BeautifulSoup, product_name: str = "") -> str:
        """브랜드 파싱."""
        # 1. 기존 셀렉터 시도
        brand_elem = soup.select_one('.spec_list .makerName')
        if brand_elem:
            return brand_elem.get_text(strip=True)

        # 2. 제조사 정보에서 찾기
        maker_elem = soup.select_one('.made_info .maker')
        if maker_elem:
            return maker_elem.get_text(strip=True)

        # 3. 상품명 첫 단어에서 브랜드 추출 (예: "LG전자 그램..." -> "LG전자")
        if product_name:
            known_brands = [
                'LG전자', '삼성전자', 'APPLE', 'MSI', 'ASUS', '레노버', 'HP', '에이서',
                '델', '기가바이트', 'ASRock', '인텔', 'AMD', '엔비디아', 'NVIDIA',
                '로지텍', '레이저', 'ATK', 'AULA', '커세어', '시게이트', 'WD',
            ]
            for brand in known_brands:
                if brand in product_name:
                    return brand
            # 첫 단어 추출
            first_word = product_name.split()[0] if product_name.split() else ""
            if first_word and len(first_word) > 1:
                return first_word

        return ""

    def _parse_registration_date(self, soup: BeautifulSoup) -> Optional[str]:
        """등록월 파싱."""
        import re

        # 1. 기존 셀렉터 시도
        reg_elem = soup.select_one('.spec_list .regDate')
        if reg_elem:
            return reg_elem.get_text(strip=True)

        # 2. 페이지 텍스트에서 등록월 패턴 찾기
        text = soup.get_text()
        patterns = [
            r'등록월[:\s]*(\d{4}\.\d{2})',
            r'(\d{4}\.\d{2})\.\s*등록',
            r'출시[:\s]*(\d{4}\.\d{2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1) + '.'

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

        # 1. 기존 셀렉터 시도
        price_elem = soup.select_one('.lowest_price .lwst_prc .prc')
        if price_elem:
            price_text = price_elem.get_text(strip=True).replace(',', '').replace('원', '')
            if price_text.isdigit():
                return int(price_text)

        # 2. 새로운 셀렉터들 시도
        selectors = [
            '.box__price.lowest .sell-price',
            '.sell-price',
            '.price_num',
            '.prc_c',
            '.link__sell-price',
        ]
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.get_text(strip=True).replace(',', '').replace('원', '')
                # 숫자만 추출
                price_match = re.search(r'(\d+)', price_text.replace(',', ''))
                if price_match:
                    return int(price_match.group(1))

        return 0

    def _parse_categories(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """카테고리 파싱."""
        categories = {
            'category_1': None,
            'category_2': None,
            'category_3': None,
            'category_4': None,
        }

        # 1. 기존 셀렉터 시도
        breadcrumb = soup.select('.location_category a')
        if not breadcrumb:
            # 2. 새로운 셀렉터 - location_wrap에서 상품 관련 카테고리만 추출
            # location_wrap에는 많은 링크가 있으므로 상품 상세 페이지의 실제 경로만 추출
            # 보통 "컴퓨터/노트북/조립PC > 노트북 > 표준노트북" 형태
            breadcrumb = soup.select('.location_wrap a')

        # 중복 및 메뉴 항목 제외하고 카테고리 경로 추출
        seen = set()
        valid_cats = []
        skip_keywords = ['홈', '전체', '카테고리', 'AI', '가전', '태블릿', '스포츠', '자동차',
                        '가구', '식품', '생활', '패션', '반려동물', '로켓배송', '쿠팡']

        for item in breadcrumb:
            text = item.get_text(strip=True)
            if text and text not in seen:
                # 메뉴 항목 건너뛰기
                if any(skip in text for skip in skip_keywords):
                    continue
                if '노트북' in text or 'PC' in text or '컴퓨터' in text or '모니터' in text:
                    seen.add(text)
                    valid_cats.append(text)
                    if len(valid_cats) >= 4:
                        break

        for i, cat in enumerate(valid_cats[:4], 1):
            categories[f'category_{i}'] = cat

        return categories

    def _parse_spec(self, soup: BeautifulSoup) -> tuple:
        """스펙 정보 파싱."""
        spec = {}
        spec_summary = []

        try:
            # 스펙 테이블 파싱
            spec_items = soup.select('.spec_tbl tr')
            for row in spec_items:
                th = row.select_one('th')
                td = row.select_one('td')
                if th and td:
                    key = th.get_text(strip=True)
                    value = td.get_text(strip=True)
                    spec[key] = value

            # 주요 스펙 요약
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
                        seller_name=seller_name,
                        price=price,
                        seller_url=seller_url,
                        seller_logo=seller_logo,
                    ))

        except Exception as e:
            logger.error(f"Failed to parse mall prices for {pcode}: {e}")

        return mall_list

    # ============================================================
    # 가격 변동 이력 크롤링
    # ============================================================

    def get_price_history(self, pcode: str, months: int = 24) -> List[PriceHistory]:
        """
        월별 가격 변동 이력 크롤링.

        Args:
            pcode: 다나와 상품 코드
            months: 조회할 개월 수 (기본 24개월)

        Returns:
            PriceHistory 리스트 (1개월 전 ~ 24개월 전)
        """
        # 차트 API 호출
        params = {
            'pcode': pcode,
            'type': 'price',
        }

        data = self._get_json(self.CHART_API_URL, params)

        history = []

        if data and 'data' in data:
            price_data = data.get('data', [])
            now = datetime.now()

            for i in range(1, months + 1):
                target_date = now - relativedelta(months=i)
                target_key = target_date.strftime('%Y%m')

                price = None
                for item in price_data:
                    if item.get('date', '').startswith(target_key):
                        price = item.get('price')
                        break

                history.append(PriceHistory(
                    month_offset=i,
                    price=price,
                ))
        else:
            # API 실패 시 빈 이력 반환
            for i in range(1, months + 1):
                history.append(PriceHistory(month_offset=i, price=None))

        return history

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
                    reviewer=reviewer,
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
                pcode = item.get('data-pcode', '')

                name_elem = item.select_one('.prod_name')
                product_name = name_elem.get_text(strip=True) if name_elem else ""

                price_elem = item.select_one('.price_sect .price')
                price = 0
                if price_elem:
                    price_text = price_elem.get_text(strip=True).replace(',', '').replace('원', '')
                    price = int(price_text) if price_text.isdigit() else 0

                if pcode:
                    results.append({
                        'pcode': pcode,
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
            'product_info': product_info,
            'mall_list': mall_list,
            'price_history': price_history,
            'reviews': reviews,
        }

    def close(self):
        """세션 종료."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
