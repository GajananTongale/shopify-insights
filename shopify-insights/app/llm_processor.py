import google.generativeai as genai
import json
from .config import settings

schema = {
    "faqs": '[{"question": "string", "answer": "string"}]',
    # Add other schemas as needed
}

async def structure_with_llm(content: str, data_type: str) -> list:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel('gemini-pro')  # Use the free model
    prompt = f"""
    Extract structured {data_type} from this content:
    {content[:10000]}
    Return as JSON matching this schema: {schema.get(data_type, '{}')}
    """
    response = model.generate_content(prompt)
    return json.loads(response.text) 