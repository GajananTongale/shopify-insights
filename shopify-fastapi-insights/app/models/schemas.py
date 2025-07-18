from pydantic import BaseModel, HttpUrl, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ScrapingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ProductSchema(BaseModel):
    id: int
    title: str
    handle: str
    vendor: str
    product_type: str
    price: float
    url: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_hero_product: bool = False

class FAQSchema(BaseModel):
    question: str
    answer: str

class ContactDetailsSchema(BaseModel):
    emails: List[str] = []
    phones: List[str] = []

class SocialHandlesSchema(BaseModel):
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None
    pinterest: Optional[str] = None

class ImportantLinksSchema(BaseModel):
    order_tracking: Optional[str] = None
    contact_us: Optional[str] = None
    blogs: Optional[str] = None
    shipping_info: Optional[str] = None
    size_guide: Optional[str] = None

class BrandInsightsRequest(BaseModel):
    website_url: HttpUrl
    include_competitors: bool = False
    
    @validator('website_url')
    def validate_url(cls, v):
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

class BrandInsightsResponse(BaseModel):
    id: int
    website_url: str
    brand_name: Optional[str] = None
    
    # Core insights
    product_catalog: List[ProductSchema] = []
    hero_products: List[ProductSchema] = []
    privacy_policy: Optional[str] = None
    refund_policy: Optional[str] = None
    faqs: List[FAQSchema] = []
    brand_context: Optional[str] = None
    
    # Contact and social
    contact_details: ContactDetailsSchema = ContactDetailsSchema()
    social_handles: SocialHandlesSchema = SocialHandlesSchema()
    important_links: ImportantLinksSchema = ImportantLinksSchema()
    
    # Metadata
    is_shopify_store: bool = False
    scraping_status: ScrapingStatus
    error_message: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

class CompetitorInsightsSchema(BaseModel):
    competitor_url: str
    insights: Optional[BrandInsightsResponse] = None
    similarity_score: Optional[float] = None

class CompetitorAnalysisResponse(BaseModel):
    brand_insights: BrandInsightsResponse
    competitors: List[CompetitorInsightsSchema] = [] 