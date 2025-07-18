import asyncio
from typing import List
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.insights_service import InsightsService
from app.services.llm_service import LLMService
from app.models.schemas import CompetitorAnalysisResponse, CompetitorInsightsSchema
from app.core.database import CompetitorAnalysis

logger = logging.getLogger(__name__)

class CompetitorService:
    def __init__(self):
        self.insights_service = InsightsService()
        self.llm_service = LLMService()
    
    async def analyze_competitors(self, website_url: str, db: AsyncSession) -> CompetitorAnalysisResponse:
        brand_insights = await self.insights_service.extract_insights(website_url, db)
        competitors = await self._find_competitors(brand_insights, db)
        return CompetitorAnalysisResponse(
            brand_insights=brand_insights,
            competitors=competitors
        )
    
    async def _find_competitors(self, brand_insights, db: AsyncSession) -> List[CompetitorInsightsSchema]:
        competitors = []
        try:
            industry = self._determine_industry(brand_insights.product_catalog)
            competitor_urls = await self.llm_service.find_competitors(
                brand_insights.brand_name or "Unknown Brand",
                industry
            )
            for competitor_url in competitor_urls[:3]:
                try:
                    competitor_insights = await self.insights_service.extract_insights(competitor_url, db)
                    similarity_score = self._calculate_similarity(brand_insights, competitor_insights)
                    competitors.append(CompetitorInsightsSchema(
                        competitor_url=competitor_url,
                        insights=competitor_insights,
                        similarity_score=similarity_score
                    ))
                except Exception as e:
                    logger.warning(f"Could not analyze competitor {competitor_url}: {e}")
                    competitors.append(CompetitorInsightsSchema(
                        competitor_url=competitor_url,
                        insights=None,
                        similarity_score=None
                    ))
        except Exception as e:
            logger.error(f"Error in competitor analysis: {e}")
        return competitors
    
    def _determine_industry(self, products) -> str:
        if not products:
            return "E-commerce"
        product_types = [p.product_type.lower() for p in products if p.product_type]
        if any(keyword in ' '.join(product_types) for keyword in ['fashion', 'clothing', 'apparel']):
            return "Fashion"
        elif any(keyword in ' '.join(product_types) for keyword in ['beauty', 'cosmetics', 'skincare']):
            return "Beauty"
        elif any(keyword in ' '.join(product_types) for keyword in ['electronics', 'tech', 'gadgets']):
            return "Electronics"
        else:
            return "E-commerce"
    
    def _calculate_similarity(self, brand1, brand2) -> float:
        try:
            score = 0.0
            if brand1.product_catalog and brand2.product_catalog:
                types1 = set(p.product_type.lower() for p in brand1.product_catalog)
                types2 = set(p.product_type.lower() for p in brand2.product_catalog)
                intersection = len(types1.intersection(types2))
                union = len(types1.union(types2))
                if union > 0:
                    score += (intersection / union) * 0.5
            if brand1.product_catalog and brand2.product_catalog:
                prices1 = [p.price for p in brand1.product_catalog if p.price > 0]
                prices2 = [p.price for p in brand2.product_catalog if p.price > 0]
                if prices1 and prices2:
                    avg_price1 = sum(prices1) / len(prices1)
                    avg_price2 = sum(prices2) / len(prices2)
                    price_diff = abs(avg_price1 - avg_price2) / max(avg_price1, avg_price2)
                    score += (1 - price_diff) * 0.3
            social1 = brand1.social_handles.model_dump()
            social2 = brand2.social_handles.model_dump()
            social_platforms1 = set(k for k, v in social1.items() if v)
            social_platforms2 = set(k for k, v in social2.items() if v)
            if social_platforms1 or social_platforms2:
                social_similarity = len(social_platforms1.intersection(social_platforms2)) / len(social_platforms1.union(social_platforms2))
                score += social_similarity * 0.2
            return min(score, 1.0)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0 