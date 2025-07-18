from fastapi import FastAPI, HTTPException
from .models import BrandInsights
from .scraper import ShopifyScraper
import httpx
import asyncio

app = FastAPI()

class WebsiteRequest:
    url: str

@app.post("/extract-insights", response_model=BrandInsights)
async def extract_insights(request: WebsiteRequest):
    try:
        scraper = ShopifyScraper(request.url)
        # Execute scraping tasks concurrently
        results = await asyncio.gather(
            scraper.get_products(),
            scraper.get_hero_products(),
            scraper.get_policy("privacy"),
            scraper.get_policy("refund"),
            scraper.get_faqs(),
            scraper.get_social_handles(),
            scraper.get_contact_details(),
            scraper.get_about_brand(),
            scraper.get_important_links(),
            return_exceptions=True
        )
        # Build response object
        return BrandInsights(
            product_catalog=results[0],
            hero_products=results[1],
            privacy_policy=results[2],
            return_refund_policy=results[3],
            faqs=results[4],
            social_handles=results[5],
            contact_details=results[6],
            about_brand=results[7],
            important_links=results[8]
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=401, detail="Website not found")
        raise HTTPException(status_code=500, detail=f"HTTP error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 