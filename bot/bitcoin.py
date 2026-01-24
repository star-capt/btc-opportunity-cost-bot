import cryptocompare
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# CryptoCompare doesn't strictly need a key for basic public data, but good to have env var
# cryptocompare.cryptocompare._set_api_key_parameter(os.getenv("CRYPTOCOMPARE_API_KEY"))

async def get_btc_price_on_date(date_str: str):
    """
    Returns the BTC price in USD on a specific date (YYYY-MM-DD).
    Uses cryptocompare which has excellent historical data.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # price_historical returns a dict like {'BTC': {'USD': 1234.56}}
        data = cryptocompare.get_historical_price('BTC', 'USD', dt)
        if data and 'BTC' in data and 'USD' in data['BTC']:
            return data['BTC']['USD']
        return None
    except Exception as e:
        logger.error(f"Failed to fetch historical BTC price: {e}")
        return None

async def get_current_btc_price():
    """Returns the current BTC price in USD."""
    try:
        data = cryptocompare.get_price('BTC', 'USD')
        if data and 'BTC' in data and 'USD' in data['BTC']:
            return data['BTC']['USD']
        return None
    except Exception as e:
        logger.error(f"Failed to fetch current BTC price: {e}")
        return None
