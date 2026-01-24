from . import ai_research
from . import bitcoin
import logging

logger = logging.getLogger(__name__)

async def run_calculation(query: str):
    """
    Orchestrates the research and calculation flow.
    """
    # 1. AI Research the purchase
    research = await ai_research.research_purchase(query)
    if not research or 'total_usd' not in research or 'date' not in research:
        return None
    
    # 2. Get BTC price then
    btc_then = await bitcoin.get_btc_price_on_date(research['date'])
    if not btc_then:
        return None
        
    # 3. Get BTC price now
    btc_now = await bitcoin.get_current_btc_price()
    if not btc_now:
        return None
        
    # 4. Calculate
    usd_spent = research['total_usd']
    btc_amount = usd_spent / btc_then
    btc_value_now = btc_amount * btc_now
    
    return {
        "query": query,
        "item": research['item'],
        "purchase_date": research['date'],
        "total_usd": usd_spent,
        "btc_price_then": btc_then,
        "btc_amount": btc_amount,
        "btc_price_now": btc_now,
        "btc_value_now": btc_value_now,
        "source": research.get('source', 'Unknown')
    }
