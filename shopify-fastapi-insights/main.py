from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

from app.core.config import Settings
from app.core.database import init_db
from app.api.v1.endpoints import insights, health
from app.core.exceptions import setup_exception_handlers

load_dotenv()

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Shopify Insights Fetcher API",
    description="Extract comprehensive insights from Shopify stores using web scraping and AI",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
setup_exception_handlers(app)

# Routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(insights.router, prefix="/api/v1", tags=["insights"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    ) 