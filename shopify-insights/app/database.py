from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, BrandInsightsDB
from .config import settings

engine = create_engine(f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}@{settings.mysql_host}/{settings.mysql_db}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def save_insights(insights):
    db = SessionLocal()
    try:
        db_insights = BrandInsightsDB(
            domain=getattr(insights, 'domain', None),
            product_count=len(getattr(insights, 'product_catalog', [])),
            # ... other fields
        )
        db.add(db_insights)
        db.commit()
    finally:
        db.close() 