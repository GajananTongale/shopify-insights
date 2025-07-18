import google.generativeai as genai
import json
import re
from typing import List, Optional
import logging
import asyncio

from app.models.schemas import FAQSchema
from app.core.config import settings
from app.core.exceptions import ScrapingError

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    async def extract_faqs(self, text: str) -> List[FAQSchema]:
        if not text or not text.strip():
            return []
        prompt = """
        You are an expert data extraction assistant. Analyze the following text and extract ALL question-and-answer pairs.
        Look for:
        - Questions in headings (h1-h6) with answers in following paragraphs
        - Definition lists (dt/dd pairs)
        - Any text patterns like "Q:" and "A:" or "Question:" and "Answer:"
        - Section titles that look like questions
        - Accordion-style content
        - Any structured Q&A format
        Return ONLY valid JSON in this exact format:
        {"faqs": [{"question": "...", "answer": "..."}]}
        If no FAQs are found, return: {"faqs": []}
        Text to analyze:
        """
        try:
            full_prompt = prompt + text[:10000]
            response = await self.model.generate_content_async(full_prompt)
            if not response.parts:
                return []
            response_text = response.text.strip()
            response_text = re.sub(r'```json\s*|\s*```', '', response_text)
            if response_text.startswith('{') and response_text.endswith('}'):
                data = json.loads(response_text)
                faqs = data.get('faqs', [])
                return [FAQSchema(**faq) for faq in faqs if isinstance(faq, dict)]
        except Exception as e:
            logger.error(f"Error extracting FAQs with LLM: {e}")
        return []
    
    async def extract_brand_context(self, text: str) -> Optional[str]:
        if not text or not text.strip():
            return None
        prompt = """
        You are a brand analyst. Read the following text from a company's website (likely an 'About Us' page).
        Extract and summarize the key information about the brand in 2-3 sentences. Focus on:
        - Brand mission and values
        - What they do/sell
        - Their unique story or background
        - Target audience
        Return only the summary text, no additional formatting or explanations.
        Text:
        """
        try:
            full_prompt = prompt + text[:8000]
            response = await self.model.generate_content_async(full_prompt)
            if response.parts:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Error extracting brand context with LLM: {e}")
        return None
    
    async def find_competitors(self, brand_name: str, industry: str) -> List[str]:
        if not brand_name:
            return []
        prompt = f"""
        You are a business analyst. Find 3-5 main competitors for the brand \"{brand_name}\" in the {industry} industry.
        Return only a JSON array of competitor website URLs:
        ["https://competitor1.com", "https://competitor2.com", ...]
        Focus on direct competitors with similar products/services.
        """
        try:
            response = await self.model.generate_content_async(prompt)
            if response.parts:
                response_text = response.text.strip()
                response_text = re.sub(r'```json\s*|\s*```', '', response_text)
                if response_text.startswith('[') and response_text.endswith(']'):
                    return json.loads(response_text)
        except Exception as e:
            logger.error(f"Error finding competitors with LLM: {e}")
        return [] 