import httpx
from bs4 import BeautifulSoup
import asyncio
import json
import re
from typing import List, Optional, Dict, Tuple
from urllib.parse import urlparse, urljoin
import logging
from datetime import datetime

from app.models.schemas import (
    ProductSchema, FAQSchema, ContactDetailsSchema, 
    SocialHandlesSchema, ImportantLinksSchema
)
from app.core.exceptions import WebsiteNotFoundError, ScrapingError
from app.core.config import settings

logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self):
        self.timeout = settings.HTTP_TIMEOUT
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    async def get_soup(self, url: str, client: httpx.AsyncClient) -> BeautifulSoup:
        try:
            response = await client.get(
                url, 
                headers=self.headers, 
                timeout=self.timeout,
                follow_redirects=True
            )
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise WebsiteNotFoundError(f"Page not found: {url}")
            raise ScrapingError(f"HTTP error {e.response.status_code} for {url}")
        except httpx.RequestError as e:
            raise ScrapingError(f"Network error for {url}: {str(e)}")
    
    def get_base_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def is_shopify_store(self, soup: BeautifulSoup) -> bool:
        shopify_indicators = [
            'shopify',
            'cdn.shopify.com',
            'myshopify.com',
            'shopify-analytics'
        ]
        page_content = str(soup).lower()
        return any(indicator in page_content for indicator in shopify_indicators)
    
    async def fetch_product_catalog(self, base_url: str, client: httpx.AsyncClient) -> List[ProductSchema]:
        products = []
        try:
            products_url = urljoin(base_url, "/products.json")
            response = await client.get(products_url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            for item in data.get('products', []):
                try:
                    price = 0.0
                    image_url = None
                    if item.get('variants'):
                        try:
                            price = float(item['variants'][0].get('price', 0.0))
                        except (ValueError, TypeError):
                            price = 0.0
                    if item.get('images'):
                        image_url = item['images'][0].get('src')
                    products.append(ProductSchema(
                        id=item['id'],
                        title=item['title'],
                        handle=item['handle'],
                        vendor=item['vendor'],
                        product_type=item.get('product_type', 'N/A'),
                        price=price,
                        url=urljoin(base_url, f"/products/{item['handle']}"),
                        image_url=image_url,
                        description=item.get('body_html', '')[:500] if item.get('body_html') else None
                    ))
                except Exception as e:
                    logger.warning(f"Skipping product due to error: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Could not fetch product catalog: {e}")
        return products
    
    async def extract_hero_products(self, soup: BeautifulSoup, base_url: str) -> List[ProductSchema]:
        hero_products = []
        hero_selectors = [
            '.hero-product',
            '.featured-product',
            '.product-card',
            '[data-product-id]',
            '.product-item'
        ]
        for selector in hero_selectors:
            elements = soup.select(selector)
            for element in elements[:6]:
                try:
                    title = element.select_one('.product-title, .product-name, h3, h4')
                    price_elem = element.select_one('.price, .product-price')
                    link_elem = element.select_one('a[href*="/products/"]')
                    if title and price_elem and link_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)
                        hero_products.append(ProductSchema(
                            id=len(hero_products) + 1,
                            title=title.get_text(strip=True),
                            handle=link_elem['href'].split('/')[-1],
                            vendor="Unknown",
                            product_type="Hero Product",
                            price=price,
                            url=urljoin(base_url, link_elem['href']),
                            is_hero_product=True
                        ))
                except Exception as e:
                    logger.warning(f"Error extracting hero product: {e}")
                    continue
            if hero_products:
                break
        return hero_products
    
    def _extract_price(self, price_text: str) -> float:
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                pass
        return 0.0
    
    def extract_contact_details(self, soup: BeautifulSoup) -> ContactDetailsSchema:
        emails = set()
        phones = set()
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails.update(re.findall(email_pattern, soup.get_text()))
        for link in soup.find_all('a', href=lambda x: x and x.startswith('mailto:')):
            email = link['href'].replace('mailto:', '').split('?')[0]
            emails.add(email)
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones.update(re.findall(phone_pattern, soup.get_text()))
        for link in soup.find_all('a', href=lambda x: x and x.startswith('tel:')):
            phone = link['href'].replace('tel:', '')
            phones.add(phone)
        return ContactDetailsSchema(
            emails=list(emails),
            phones=list(phones)
        )
    
    def extract_social_handles(self, soup: BeautifulSoup) -> SocialHandlesSchema:
        social_handles = {}
        social_patterns = {
            'instagram': r'instagram\.com/([^/\s]+)',
            'facebook': r'facebook\.com/([^/\s]+)',
            'twitter': r'(?:twitter\.com|x\.com)/([^/\s]+)',
            'tiktok': r'tiktok\.com/@([^/\s]+)',
            'youtube': r'youtube\.com/(?:channel/|user/|c/)?([^/\s]+)',
            'pinterest': r'pinterest\.com/([^/\s]+)'
        }
        page_text = str(soup)
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                social_handles[platform] = f"https://{platform}.com/{matches[0]}"
        return SocialHandlesSchema(**social_handles)
    
    def extract_important_links(self, soup: BeautifulSoup, base_url: str) -> ImportantLinksSchema:
        important_links = {}
        link_patterns = {
            'order_tracking': r'track|tracking|order.*status',
            'contact_us': r'contact|support|help',
            'blogs': r'blog|news|article',
            'shipping_info': r'shipping|delivery',
            'size_guide': r'size.*guide|sizing'
        }
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            href = link['href']
            if href.startswith('/'):
                href = urljoin(base_url, href)
            for key, pattern in link_patterns.items():
                if re.search(pattern, link_text, re.IGNORECASE) and key not in important_links:
                    important_links[key] = href
                    break
        return ImportantLinksSchema(**important_links) 