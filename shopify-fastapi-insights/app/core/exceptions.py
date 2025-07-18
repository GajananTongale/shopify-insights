from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

class InsightsException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class WebsiteNotFoundError(InsightsException):
    def __init__(self, message: str = "Website not found or not accessible"):
        super().__init__(message, 404)

class ScrapingError(InsightsException):
    def __init__(self, message: str = "Error occurred during website scraping"):
        super().__init__(message, 500)

def setup_exception_handlers(app):
    @app.exception_handler(InsightsException)
    async def insights_exception_handler(request: Request, exc: InsightsException):
        logger.error(f"Insights error: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "status_code": exc.status_code}
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"error": "Validation error", "details": exc.errors()}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unexpected error: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "status_code": 500}
        ) 