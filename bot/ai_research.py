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
    Returns enhanced data including quantity, unit price, and current value.
    """
    client = get_openai_client()
    if not client:
        logger.error("AI research failed: OpenAI client not initialized (missing API key).")
        return None
    prompt = f"""
    Research the historical USD price for the following purchase description: "{query}"
    
    Current date: {datetime.now().strftime('%Y-%m-%d')}
    
    Strictly return a JSON object with:
    - item: Specific product/asset name
    - date: YYYY-MM-DD format (best estimate of purchase date)
    - quantity: Number of units purchased (e.g., 1 for a single product, number of shares for stocks)
    - unit_price: Price per unit at time of purchase in USD
    - total_usd: Total price paid in USD (quantity × unit_price)
    - current_unit_value: Current value per unit in USD today (0 for consumed items like food, depreciated value for old electronics, current stock price for stocks)
    - current_total_value: Current total value in USD (quantity × current_unit_value)
    - value_explanation: Brief explanation of current value (e.g., "Consumed/no resale value", "Depreciated ~60%", "Current stock price")
    - source: Brief mention of where the original price came from (e.g., "Launch price", "Historical stock data")
    
    Important notes:
    - For stocks: Use historical closing price for purchase, current market price for current value
    - For electronics: Estimate reasonable resale/depreciated value
    - For consumables (food, gas, etc.): current_unit_value should be 0
    - For services: current value is typically 0 (already consumed)
    
    Example for stock:
    Query: "$500 of S&P 500 in January 2013"
    Response: {{"item": "S&P 500 Index Shares", "date": "2013-01-02", "quantity": 3.39, "unit_price": 147.50, "total_usd": 500.00, "current_unit_value": 603.89, "current_total_value": 2047.19, "value_explanation": "Current S&P 500 price", "source": "Historical index data"}}
    
    Example for consumer product:
    Query: "iPhone 12 in October 2020"  
    Response: {{"item": "iPhone 12", "date": "2020-10-23", "quantity": 1, "unit_price": 799.00, "total_usd": 799.00, "current_unit_value": 280.00, "current_total_value": 280.00, "value_explanation": "Typical resale value for used iPhone 12", "source": "Apple retail price"}}
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional research assistant specializing in historical pricing data for consumer products, stocks, and assets. Provide accurate, well-researched data."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        logger.error(f"AI research failed: {e}")
        return None


async def generate_clever_commentary(result: dict) -> str:
    """
    Generates a witty, contextual one-liner about the opportunity cost.
    """
    client = get_openai_client()
    if not client:
        return ""  # Gracefully degrade - no commentary if no API key
    
    gain_usd = result['btc_value_now'] - result['total_usd']
    gain_multiplier = result['btc_value_now'] / result['total_usd'] if result['total_usd'] > 0 else 0
    current_value = result.get('current_total_value', 0)
    btc_vs_current = result['btc_value_now'] - current_value if current_value else gain_usd
    
    # Determine the scenario for appropriate tone
    btc_won_vs_purchase = gain_usd > 0
    btc_won_vs_holding = btc_vs_current > 0
    
    if btc_won_vs_purchase and btc_won_vs_holding:
        scenario = "BTC_CRUSHED_IT"
        tone_guidance = "BTC massively outperformed. Make them feel the FOMO hard but playfully."
    elif btc_won_vs_purchase and not btc_won_vs_holding:
        scenario = "BTC_BEAT_PURCHASE_BUT_ITEM_DID_BETTER"
        tone_guidance = "BTC made money, but holding the item would have been even better. Acknowledge the irony."
    elif not btc_won_vs_purchase and btc_won_vs_holding:
        scenario = "BTC_LOST_BUT_BEAT_ITEM"
        tone_guidance = "BTC lost value, but the item lost even more. Cold comfort - mention that both were bad choices."
    else:
        scenario = "BTC_UNDERPERFORMED"
        tone_guidance = "BTC actually LOST money or underperformed the original purchase. Congratulate them on NOT buying BTC! Be self-deprecating about BTC's performance in this window."
    
    prompt = f"""
    Generate a single witty, clever one-liner comment about this Bitcoin opportunity cost calculation.
    
    CRITICAL CONTEXT:
    - Scenario: {scenario}
    - {tone_guidance}
    
    Numbers:
    - Item purchased: {result['item']}
    - Original cost: ${result['total_usd']:,.2f}
    - Current value of item: ${current_value:,.2f} ({result.get('value_explanation', 'Unknown')})
    - If they'd bought BTC instead: ${result['btc_value_now']:,.2f}
    - BTC gain/loss vs original: ${gain_usd:,.2f} ({gain_multiplier:.1f}x)
    - BTC vs holding item: ${btc_vs_current:,.2f}
    
    IMPORTANT: If BTC underperformed (scenario is BTC_UNDERPERFORMED), DO NOT say they should have bought BTC!
    Instead, congratulate them on their purchase or make a self-deprecating joke about BTC's poor timing.
    
    Examples for BTC_UNDERPERFORMED scenario:
    - "Plot twist: You actually WON this round! BTC would've lost you money. Well played. 🏆"
    - "For once, NOT buying Bitcoin was the big brain move. Your {result['item']} aged better than BTC did!"
    - "BTC had a rough patch there. Your purchase? Still a better investment. Unexpected W."
    
    Examples for BTC_CRUSHED_IT scenario:
    - "That S&P 500 did fine, but BTC would've turned you into a small whale. 🐋"
    - "Your iPhone is worth $200 now. BTC would've been worth $47,000. Different kind of upgrade."
    
    Return ONLY the one-liner, no quotes or extra formatting. Keep it under 200 characters.
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a witty copywriter who specializes in making people laugh while also feeling mild regret about their financial decisions. Be clever, not cruel."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Commentary generation failed: {e}")
        return ""

