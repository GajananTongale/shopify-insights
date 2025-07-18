import httpx
import asyncio
from typing import List, Optional
from urllib.parse import urljoin
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.scraper import WebScraper
from app.services.llm_service import LLMService
from app.models.schemas import BrandInsightsResponse, ScrapingStatus
from app.core.database import BrandInsight
from app.core.exceptions import WebsiteNotFoundError, ScrapingError

logger = logging.getLogger(__name__)

class InsightsService:
    def __init__(self):
        self.scraper = WebScraper()
        self.llm_service = LLMService()
    
    async def extract_insights(self, website_url: str, db: AsyncSession) -> BrandInsightsResponse:
        existing_insights = await self._get_existing_insights(website_url, db)
        if existing_insights and existing_insights.scraping_status == ScrapingStatus.COMPLETED:
            return self._convert_to_response(existing_insights)
        db_insights = existing_insights or BrandInsight(
            website_url=website_url,
            scraping_status=ScrapingStatus.IN_PROGRESS
        )
        if not existing_insights:
            db.add(db_insights)
        else:
            db_insights.scraping_status = ScrapingStatus.IN_PROGRESS
            db_insights.error_message = None
        await db.commit()
        try:
            base_url = self.scraper.get_base_url(website_url)
            async with httpx.AsyncClient() as client:
                homepage_soup = await self.scraper.get_soup(base_url, client)
                is_shopify = self.scraper.is_shopify_store(homepage_soup)
                contact_details = self.scraper.extract_contact_details(homepage_soup)
                social_handles = self.scraper.extract_social_handles(homepage_soup)
                important_links = self.scraper.extract_important_links(homepage_soup, base_url)
                product_catalog = []
                hero_products = []
                if is_shopify:
                    product_catalog = await self.scraper.fetch_product_catalog(base_url, client)
                hero_products = await self.scraper.extract_hero_products(homepage_soup, base_url)
                privacy_policy = await self._extract_page_content(base_url, 'privacy', client)
                refund_policy = await self._extract_page_content(base_url, 'refund', client)
                brand_context = await self._extract_brand_context(base_url, client)
                faqs = await self._extract_faqs(base_url, client)
                db_insights.brand_name = self._extract_brand_name(homepage_soup)
                db_insights.product_catalog = [p.model_dump() for p in product_catalog]
                db_insights.hero_products = [p.model_dump() for p in hero_products]
                db_insights.privacy_policy = privacy_policy
                db_insights.refund_policy = refund_policy
                db_insights.faqs = [f.model_dump() for f in faqs]
                db_insights.brand_context = brand_context
                db_insights.contact_details = contact_details.model_dump()
                db_insights.social_handles = social_handles.model_dump()
                db_insights.important_links = important_links.model_dump()
                db_insights.is_shopify_store = is_shopify
                db_insights.scraping_status = ScrapingStatus.COMPLETED
                await db.commit()
                return self._convert_to_response(db_insights)
        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            db_insights.scraping_status = ScrapingStatus.FAILED
            db_insights.error_message = str(e)
            await db.commit()
            raise ScrapingError(f"Failed to extract insights: {str(e)}")
    
    async def _get_existing_insights(self, website_url: str, db: AsyncSession) -> Optional[BrandInsight]:
        result = await db.execute(
            select(BrandInsight).where(BrandInsight.website_url == website_url)
        )
        return result.scalar_one_or_none()
    
    def _extract_brand_name(self, soup) -> Optional[str]:
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True).split(' - ')[0]
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
        return None
    
    async def _extract_page_content(self, base_url: str, page_type: str, client: httpx.AsyncClient) -> Optional[str]:
        page_urls = {
            'privacy': ['/pages/privacy-policy', '/privacy-policy', '/privacy'],
            'refund': ['/pages/refund-policy', '/pages/return-policy', '/refund-policy', '/returns']
        }
        for url_path in page_urls.get(page_type, []):
            try:
                page_url = urljoin(base_url, url_path)
                soup = await self.scraper.get_soup(page_url, client)
                main_content = soup.find('main') or soup.find('div', class_='main-content') or soup.find('body')
                if main_content:
                    return main_content.get_text(separator='\n', strip=True)
            except Exception as e:
                logger.warning(f"Could not fetch {page_type} page at {url_path}: {e}")
                continue
        return None
    
    async def _extract_brand_context(self, base_url: str, client: httpx.AsyncClient) -> Optional[str]:
        about_urls = ['/pages/about', '/pages/about-us', '/about', '/about-us', '/pages/our-story']
        for url_path in about_urls:
            try:
                page_url = urljoin(base_url, url_path)
                soup = await self.scraper.get_soup(page_url, client)
                main_content = soup.find('main') or soup.find('div', class_='main-content') or soup.find('body')
                if main_content:
                    page_text = main_content.get_text(separator='\n', strip=True)
                    return await self.llm_service.extract_brand_context(page_text)
            except Exception as e:
                logger.warning(f"Could not fetch about page at {url_path}: {e}")
                continue
        return None
    
    async def _extract_faqs(self, base_url: str, client: httpx.AsyncClient) -> List:
        faq_urls = [
            '/pages/faq', '/faq', '/pages/faqs', '/faqs', 
            '/pages/help', '/help', '/pages/support', '/support',
            '/pages/questions', '/questions'
        ]
        for url_path in faq_urls:
            try:
                page_url = urljoin(base_url, url_path)
                soup = await self.scraper.get_soup(page_url, client)
                main_content = soup.find('main') or soup.find('div', class_='main-content') or soup.find('body')
                if main_content:
                    page_text = main_content.get_text(separator='\n', strip=True)
                    faqs = await self.llm_service.extract_faqs(page_text)
                    if faqs:
                        return faqs
            except Exception as e:
                logger.warning(f"Could not fetch FAQ page at {url_path}: {e}")
                continue
        return []
    
    def _convert_to_response(self, db_insights: BrandInsight) -> BrandInsightsResponse:
        from app.models.schemas import (
            ProductSchema, FAQSchema, ContactDetailsSchema, 
            SocialHandlesSchema, ImportantLinksSchema
        )
        return BrandInsightsResponse(
            id=db_insights.id,
            website_url=db_insights.website_url,
            brand_name=db_insights.brand_name,
            product_catalog=[ProductSchema(**p) for p in db_insights.product_catalog or []],
            hero_products=[ProductSchema(**p) for p in db_insights.hero_products or []],
            privacy_policy=db_insights.privacy_policy,
            refund_policy=db_insights.refund_policy,
            faqs=[FAQSchema(**f) for f in db_insights.faqs or []],
            brand_context=db_insights.brand_context,
            contact_details=ContactDetailsSchema(**(db_insights.contact_details or {})),
            social_handles=SocialHandlesSchema(**(db_insights.social_handles or {})),
            important_links=ImportantLinksSchema(**(db_insights.important_links or {})),
            is_shopify_store=db_insights.is_shopify_store,
            scraping_status=db_insights.scraping_status,
            error_message=db_insights.error_message,
            created_at=db_insights.created_at,
            updated_at=db_insights.updated_at
        ) 