from pydantic import BaseModel
from typing import List, Dict, Optional
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text

Base = declarative_base()

class Product(BaseModel):
    id: str
    title: str
    handle: str
    description: Optional[str]
    price: str
    image_url: Optional[str]

class FAQItem(BaseModel):
    question: str
    answer: str

class ContactDetails(BaseModel):
    emails: List[str]
    phone_numbers: List[str]

class BrandInsights(BaseModel):
    product_catalog: List[Product]
    hero_products: List[Product]
    privacy_policy: str
    return_refund_policy: str
    faqs: List[FAQItem]
    social_handles: Dict[str, str]
    contact_details: ContactDetails
    about_brand: str
    important_links: Dict[str, str]

# SQLAlchemy DB model example (expand as needed)
class BrandInsightsDB(Base):
    __tablename__ = 'brand_insights'
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), unique=True, index=True)
    product_count = Column(Integer)
    # Add other fields as needed 