import os
import asyncio
import httpx
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from bs4 import BeautifulSoup, Tag
import google.generativeai as genai
import json
import re
from typing import List, Optional, Dict
from pydantic import BaseModel, HttpUrl, Field, ValidationError
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecret')

# --- Pydantic Models ---
class Product(BaseModel):
    id: int = 0
    title: str
    handle: str = ""
    vendor: str = ""
    product_type: str = Field(default='N/A', alias='product_type')
    price: float = 0.0
    url: Optional[str] = None
    image_url: Optional[str] = None

class FAQ(BaseModel):
    question: str
    answer: str

class BrandInsights(BaseModel):
    website_url: str
    product_catalog: List[Product] = []
    hero_products: List[Product] = []
    social_handles: Dict[str, Optional[str]] = {}
    contact_details: Dict[str, list] = {"emails": [], "phones": []}
    privacy_policy_text: Optional[str] = None
    refund_policy_text: Optional[str] = None
    faqs: List[FAQ] = []
    brand_context: Optional[str] = None
    important_links: Dict[str, str] = {}

# --- Core Scraping and LLM Logic ---
def get_base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

async def get_soup(url: str, client: httpx.AsyncClient) -> Optional[BeautifulSoup]:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = await client.get(url, follow_redirects=True, timeout=15, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

async def fetch_product_catalog(base_url: str, client: httpx.AsyncClient) -> List[Product]:
    products_url = urljoin(base_url, "/products.json")
    products = []
    try:
        response = await client.get(products_url, follow_redirects=True)
        response.raise_for_status()
        data = response.json()
        for item in data.get('products', []):
            price = 0.0
            if item.get('variants'):
                try:
                    price = float(item['variants'][0].get('price', 0.0))
                except (ValueError, TypeError):
                    price = 0.0
            try:
                products.append(Product(
                    id=item.get('id', 0),
                    title=item.get('title', ''),
                    handle=item.get('handle', ''),
                    vendor=item.get('vendor', ''),
                    product_type=item.get('product_type', 'N/A'),
                    price=price,
                    url=urljoin(base_url, f"/products/{item.get('handle','')}") if item.get('handle') else None,
                    image_url=item['images'][0]['src'] if item.get('images') and len(item['images']) > 0 else None
                ))
            except ValidationError as e:
                print(f"Skipping product due to validation error: {e}")
        return products
    except Exception as e:
        print(f"Could not fetch or parse Shopify product catalog: {e}")
        return []

def extract_hero_products(homepage_soup: BeautifulSoup, base_url: str) -> List[Product]:
    hero_products = []
    selectors = [
        '[class*="featured" i] [class*="product" i]',
        '[class*="hero" i] [class*="product" i]',
        '[class*="carousel" i] [class*="product" i]',
        '[class*="product-card" i]',
        '[class*="product-tile" i]',
        '[class*="product-item" i]',
        '[data-product]',
    ]
    for selector in selectors:
        for prod in homepage_soup.select(selector):
            if not isinstance(prod, Tag):
                continue
            # Title extraction
            title = prod.get('data-title') or prod.get('title')
            if not title:
                h2 = prod.find('h2')
                h3 = prod.find('h3')
                if h2 and hasattr(h2, 'text'):
                    title = h2.text.strip()
                elif h3 and hasattr(h3, 'text'):
                    title = h3.text.strip()
            if not isinstance(title, str) or not title.strip():
                continue
            # Link extraction
            link = prod.find('a', href=True)
            url = None
            if link and isinstance(link, Tag):
                href = link.get('href')
                if isinstance(href, list):
                    href = href[0] if href else None
                if isinstance(href, str):
                    url = urljoin(base_url, href)
            # Image extraction
            image_url = None
            image = prod.find('img')
            if image and isinstance(image, Tag) and image.has_attr('src'):
                image_url = str(image['src'])
            hero_products.append(Product(
                title=title.strip(),
                url=url,
                image_url=image_url
            ))
    # Remove duplicates by title
    seen = set()
    unique_heroes = []
    for p in hero_products:
        if p.title and p.title not in seen:
            unique_heroes.append(p)
            seen.add(p.title)
    return unique_heroes

def extract_social_handles(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    handles: Dict[str, Optional[str]] = {}
    social_patterns = {
        'instagram': r'instagram\.com',
        'facebook': r'facebook\.com',
        'x (twitter)': r'twitter\.com|x\.com',
        'tiktok': r'tiktok\.com',
        'youtube': r'youtube\.com',
        'pinterest': r'pinterest\.com'
    }
    for a in soup.find_all('a', href=True):
        for name, pattern in social_patterns.items():
            if re.search(pattern, a['href']):
                handles[name] = a['href']
                break
    return handles

def extract_contact_details(soup: BeautifulSoup) -> Dict[str, list]:
    contacts = {"emails": [], "phones": []}
    emails = set(re.findall(r'[\w\.-]+@[\w\.-]+', soup.get_text()))
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if href.startswith('mailto:'):
            emails.add(href.replace('mailto:', '').split('?')[0])
    contacts['emails'] = list(emails)
    phones = set(re.findall(r'(\+?\d[\d\s-]{8,}\d)', soup.get_text()))
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if href.startswith('tel:'):
            phones.add(href.replace('tel:', ''))
    contacts['phones'] = list(phones)
    return contacts

def extract_important_links(soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
    # Look for links with keywords
    keywords = ['order', 'track', 'contact', 'blog', 'faq', 'help', 'support', 'about', 'return', 'refund', 'shipping']
    links = {}
    for a in soup.find_all('a', href=True):
        text = a.get_text().strip().lower()
        for kw in keywords:
            if kw in text and a['href'] and not a['href'].startswith('#'):
                full_url = urljoin(base_url, a['href'])
                links[text] = full_url
    return links

async def structure_with_llm(text: str, data_type: str, model: genai.GenerativeModel) -> any:
    if not text or not text.strip():
        return [] if data_type == 'faq' else ""
    faq_prompt = """
    You are an expert data extraction assistant. Analyze the following text from a website's FAQ page.
    Extract all question-and-answer pairs.
    Format your response as a valid JSON object with a single key \"faqs\", which is a list of objects.
    Each object must have two keys: \"question\" and \"answer\".
    If no FAQs are found, return an empty list: {\"faqs\": []}. Do not add any explanations or markdown formatting.
    Text:
    """
    context_prompt = """
    You are a brand analyst. Read the following text from a company's 'About Us' page.
    Summarize it into a single, concise paragraph that captures the brand's mission, story, or values.
    Provide only the summary paragraph as a plain string, with no extra formatting.
    Text:
    """
    prompt = faq_prompt if data_type == 'faq' else context_prompt
    response_text = ""
    try:
        full_prompt = prompt + f"\n\n{text[:10000]}\n\n"
        response = await model.generate_content_async(full_prompt)
        if not response.parts:
            print(f"LLM returned no parts. Feedback: {response.prompt_feedback}")
            return [] if data_type == 'faq' else ""
        response_text = response.text.strip().replace("```json", "").replace("```", "")
        if data_type == 'faq':
            if response_text.startswith('{') and response_text.endswith('}'):
                return json.loads(response_text).get('faqs', [])
            else:
                print(f"LLM returned non-JSON for FAQ: {response_text}")
                return []
        else:
            return response_text
    except Exception as e:
        print(f"An error occurred while communicating with the LLM for {data_type}: {e}")
        return [] if data_type == 'faq' else ""

async def fetch_all_insights(url: str, gemini_model: genai.GenerativeModel) -> BrandInsights:
    base_url = get_base_url(url)
    insights = BrandInsights(website_url=base_url)
    async with httpx.AsyncClient() as client:
        homepage_soup = await get_soup(base_url, client)
        if not homepage_soup:
            raise ConnectionError("Could not fetch the homepage. The site might be down or blocking requests.")
        insights.product_catalog = await fetch_product_catalog(base_url, client)
        insights.hero_products = extract_hero_products(homepage_soup, base_url)
        insights.social_handles = extract_social_handles(homepage_soup)
        insights.contact_details = extract_contact_details(homepage_soup)
        insights.important_links = extract_important_links(homepage_soup, base_url)
        all_links = homepage_soup.find_all('a', href=True)
        pages_to_fetch = {
            'privacy': 'privacy-policy',
            'refund': 'refund-policy|return-policy',
            'faq': "faq(?:'s)?|help",
            'about': 'about|our-story'
        }
        for key, keyword_pattern in pages_to_fetch.items():
            potential_urls = []
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text()
                if re.search(keyword_pattern, text, re.IGNORECASE) or re.search(keyword_pattern, href, re.IGNORECASE):
                    if href and not urlparse(href).netloc and not href.startswith('#'):
                        full_url = urljoin(base_url, href)
                        if full_url not in potential_urls:
                            potential_urls.append(full_url)
            for url_to_try in potential_urls:
                print(f"Attempting to fetch {key} page: {url_to_try}")
                page_soup = await get_soup(url_to_try, client)
                if page_soup:
                    main_content = page_soup.find('main') or page_soup.find('body')
                    page_text = main_content.get_text(separator='\n', strip=True) if main_content else ""
                    if key == 'privacy':
                        insights.privacy_policy_text = page_text
                    elif key == 'refund':
                        insights.refund_policy_text = page_text
                    elif key == 'faq':
                        insights.faqs = await structure_with_llm(page_text, 'faq', gemini_model)
                    elif key == 'about':
                        insights.brand_context = await structure_with_llm(page_text, 'context', gemini_model)
                    print(f"Successfully processed {key} page: {url_to_try}")
                    break
    return insights

def run_async(coro):
    return asyncio.run(coro)

@app.route('/', methods=['GET', 'POST'])
def index():
    insights = None
    error = None
    if request.method == 'POST':
        url_input = request.form.get('url_input', '').strip()
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            error = "GOOGLE_API_KEY not found. Please set it in your .env file."
        elif not url_input:
            error = "Please enter a website URL."
        else:
            normalized_url = url_input
            if not normalized_url.startswith('http://') and not normalized_url.startswith('https://'):
                normalized_url = f"https://{normalized_url}"
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                insights = run_async(fetch_all_insights(normalized_url, model))
            except Exception as e:
                error = f"An error occurred: {e}"
    return render_template('index.html', insights=insights, error=error)

@app.route('/api/extract-insights', methods=['POST'])
def api_extract_insights():
    data = request.get_json()
    if not data or 'website_url' not in data:
        return jsonify({'error': 'website_url is required'}), 400
    url_input = data['website_url'].strip()
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        return jsonify({'error': 'GOOGLE_API_KEY not found'}), 500
    if not url_input:
        return jsonify({'error': 'website_url is required'}), 400
    normalized_url = url_input
    if not normalized_url.startswith('http://') and not normalized_url.startswith('https://'):
        normalized_url = f"https://{normalized_url}"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        insights = run_async(fetch_all_insights(normalized_url, model))
        return jsonify(json.loads(insights.model_dump_json())), 200
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return jsonify({'error': 'Website not found'}), 401
        return jsonify({'error': f'HTTP error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 