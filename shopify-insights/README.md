# Shopify Store Insights-Fetcher

## Overview
This application scrapes Shopify stores to extract insights (products, policies, FAQs, etc.) without using the official Shopify API. It uses FastAPI, async scraping, OpenAI LLM for structuring, and MySQL for persistence.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables for OpenAI and MySQL credentials (or edit `app/config.py`).

## Running the App
```bash
uvicorn app.main:app --reload
```

## Sample Request
POST `/extract-insights`
```json
{
  "url": "https://memy.co.in"
}
```

## Features
- Async scraping with httpx
- LLM-powered FAQ/policy parsing
- MySQL persistence
- Robust error handling

## Extending
Add new scrapers for non-standard Shopify implementations as needed. 