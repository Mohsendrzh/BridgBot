import re
import httpx
import time
from datetime import datetime

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
API_URL = "https://nobitexcmc.darkube.app/cryptomarket/market?format=json&symbols=BTC"
CACHE_DURATION = 30  # seconds

_last_btc_price = None
_last_btc_updated_ts = 0

def is_valid_email(email: str) -> bool:
    """Checks if the email format is valid."""
    return re.match(EMAIL_REGEX, email) is not None

async def get_btc_price():
    """
    Fetches BTC price using module-level variables for caching.
    Returns a dictionary or None.
    """
    global _last_btc_price, _last_btc_updated_ts
    
    now = time.time()
    
    if _last_btc_price and (now - _last_btc_updated_ts < CACHE_DURATION):
        return {
            "price": _last_btc_price,
            "updated_at": datetime.fromtimestamp(_last_btc_updated_ts).strftime("%Y-%m-%d %H:%M:%S")
        }

    try:
        async with httpx.AsyncClient() as session:
            response = await session.get(API_URL)
            if response.status_code == 200:
                data = response.json()
                print(data)
                price = data["data"]["BTC"]["priceDetails"]["price"]
                price = f'{int(price):,}'

                _last_btc_price = price
                _last_btc_updated_ts = now
                
                return {
                    "price": price,
                    "updated_at": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return None
    except Exception as e:
        print(f"Error fetching BTC price: {e}")
        return None