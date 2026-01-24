from openai import AsyncOpenAI
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Global client cache
_client = None

def get_openai_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY is not set. AI research will be disabled.")
            return None
        _client = AsyncOpenAI(api_key=api_key)
    return _client

async def research_purchase(query: str):
    """
    Uses AI to parse a natural language purchase and research its historical USD cost.
    """
    client = get_openai_client()
    if not client:
        logger.error("AI research failed: OpenAI client not initialized (missing API key).")
        return None
    prompt = f"""
    Research the historical USD price for the following purchase description: "{query}"
    
    Current local time: {datetime.now().strftime('%Y-%m-%d')}
    
    Strictly return a JSON object with:
    - item: Specific product name
    - date: YYYY-MM-DD format (best estimate)
    - total_usd: Total price paid in USD (excluding tax/shipping)
    - source: Brief mention of where this price came from (e.g., "Launch price", "Historical stock data")
    
    If the text is a stock (e.g. "100 shares of GOOG"), find the closing price on that date.
    If the text is a product (e.g. "iPhone 16"), find the retail price at launch or the specific date mention.
    
    Example:
    Query: "iPhone 15 Pro at launch"
    Response: {{"item": "iPhone 15 Pro", "date": "2023-09-22", "total_usd": 999.00, "source": "Apple retail price"}}
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional research assistant specializing in historical pricing data for consumer products and stocks."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        logger.error(f"AI research failed: {e}")
        return None
