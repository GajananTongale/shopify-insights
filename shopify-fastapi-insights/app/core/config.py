from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost/shopify_insights"
    
    # Google AI
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Shopify Insights Fetcher"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour
    
    # Timeouts
    HTTP_TIMEOUT: int = 30
    LLM_TIMEOUT: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings() 