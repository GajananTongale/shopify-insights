from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean
from datetime import datetime
from typing import AsyncGenerator

from app.core.config import settings

class Base(DeclarativeBase):
    pass

class BrandInsight(Base):
    __tablename__ = "brand_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    website_url = Column(String(500), nullable=False, index=True)
    brand_name = Column(String(255), nullable=True)
    
    # Product data
    product_catalog = Column(JSON, nullable=True)
    hero_products = Column(JSON, nullable=True)
    
    # Policies
    privacy_policy = Column(Text, nullable=True)
    refund_policy = Column(Text, nullable=True)
    
    # FAQ and context
    faqs = Column(JSON, nullable=True)
    brand_context = Column(Text, nullable=True)
    
    # Contact and social
    contact_details = Column(JSON, nullable=True)
    social_handles = Column(JSON, nullable=True)
    important_links = Column(JSON, nullable=True)
    
    # Metadata
    is_shopify_store = Column(Boolean, default=False)
    scraping_status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CompetitorAnalysis(Base):
    __tablename__ = "competitor_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_insight_id = Column(Integer, nullable=False)
    competitor_url = Column(String(500), nullable=False)
    competitor_insights = Column(JSON, nullable=True)
    similarity_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

# Database engine and session
engine = create_async_engine(
    settings.DATABASE_URL.replace("mysql+pymysql", "mysql+aiomysql"),
    echo=True if settings.ENVIRONMENT == "development" else False
)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close() 