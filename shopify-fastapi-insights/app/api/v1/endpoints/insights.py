from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.services.insights_service import InsightsService
from app.services.competitor_service import CompetitorService
from app.models.schemas import (
    BrandInsightsRequest, BrandInsightsResponse, 
    CompetitorAnalysisResponse
)

router = APIRouter()

@router.post("/insights", response_model=BrandInsightsResponse)
async def fetch_brand_insights(
    request: BrandInsightsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch comprehensive insights from a Shopify store or any e-commerce website.
    """
    insights_service = InsightsService()
    try:
        insights = await insights_service.extract_insights(str(request.website_url), db)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/insights/competitors", response_model=CompetitorAnalysisResponse)
async def analyze_competitors(
    request: BrandInsightsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a brand and its competitors (Bonus feature).
    """
    competitor_service = CompetitorService()
    try:
        analysis = await competitor_service.analyze_competitors(str(request.website_url), db)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights/history", response_model=List[BrandInsightsResponse])
async def get_insights_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get history of analyzed websites"""
    from sqlalchemy import select, desc
    from app.core.database import BrandInsight
    result = await db.execute(
        select(BrandInsight)
        .order_by(desc(BrandInsight.created_at))
        .limit(limit)
    )
    insights = result.scalars().all()
    insights_service = InsightsService()
    return [insights_service._convert_to_response(insight) for insight in insights]

@router.get("/insights/{insight_id}", response_model=BrandInsightsResponse)
async def get_insight_by_id(
    insight_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific insight by ID"""
    from sqlalchemy import select
    from app.core.database import BrandInsight
    result = await db.execute(
        select(BrandInsight).where(BrandInsight.id == insight_id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    insights_service = InsightsService()
    return insights_service._convert_to_response(insight) 