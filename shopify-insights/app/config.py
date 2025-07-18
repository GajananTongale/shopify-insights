import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str = os.getenv('GEMINI_API_KEY', '')
    mysql_user: str = os.getenv('MYSQL_USER', 'user')
    mysql_password: str = os.getenv('MYSQL_PASSWORD', 'pass')
    mysql_host: str = os.getenv('MYSQL_HOST', 'localhost')
    mysql_db: str = os.getenv('MYSQL_DB', 'shopify_insights')

    class Config:
        env_file = ".env"

settings = Settings() 