import requests
import json
import re
import time
import random
from urllib.parse import urlparse
import logging
try:
    from backend.database import insert_snapshot
except ModuleNotFoundError:
    from database import insert_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def get_headers(domain):
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": f"https://{domain}",
        "Referer": f"https://{domain}/",
        "X-Requested-With": "XMLHttpRequest"
    }

def parse_stock_from_description(description):
    """
    Parse inventory limits from Shopify 422 error messages.
    """
    logger.debug(f"Parsing stock from description: '{description}'")
    
    # "You can only add 47 of this item to your cart."
    only_add_match = re.search(r'only add (\d+)', description, re.IGNORECASE)
    if only_add_match:
        return int(only_add_match.group(1))
        
    # "All 12 of this item are in your cart."
    all_match = re.search(r'All (\d+) ', description, re.IGNORECASE)
    if all_match:
        return int(all_match.group(1))
        
    # Fallback to any first integer in the text
    fallback_match = re.search(r'(\d+)', description)
    if fallback_match:
        return int(fallback_match.group(1))
        
    # Handle text indicators of sold out / unavailable
    desc_lower = description.lower()
    if "sold out" in desc_lower or "out of stock" in desc_lower or "can't add" in desc_lower or "unavailable" in desc_lower:
        return 0
        
    return None

def get_shopify_stock(domain, variant_id, session):
    """
    Shopify Cart Reservation Trick:
    Attempts to add 99999 units of a variant to the cart.
    Parses the 422 response description for the stock limits.
    If 200 OK, stock is infinite or untracked.
    """
    add_url = f"https://{domain}/cart/add.js"
    clear_url = f"https://{domain}/cart/clear.js"
    headers = get_headers(domain)
    
    # Try payload formats (some Shopify stores require nested items, some accept flat)
    payload = {"items": [{"id": int(variant_id), "quantity": 99999}]}
    
    try:
        # Avoid rate-limiting with randomized sleep
        time.sleep(random.uniform(1.5, 3.5))
        
        response = session.post(add_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 422:
            try:
                err_data = response.json()
                desc = err_data.get("description", err_data.get("message", ""))
                stock = parse_stock_from_description(desc)
                if stock is not None:
                    return stock
                else:
                    logger.warning(f"422 Error but could not parse stock from description: {err_data}")
                    return None
            except Exception as e:
                logger.error(f"Failed to parse 422 JSON response: {e}")
                return None
                
        elif response.status_code == 200:
            logger.info(f"Successfully added 99999 units for variant {variant_id}. Tracking is likely off or backorders allowed.")
            # Clear the cart so we don't pollute the session
            session.post(clear_url, headers=headers, timeout=5)
            return -1 # Represents infinite / untracked stock
            
        else:
            logger.warning(f"Unexpected status code {response.status_code} for variant {variant_id}: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error querying stock for variant {variant_id}: {e}")
        return None

def scrape_product(brand, product_url, session=None):
    """
    Appends .json to product URL, extracts variants, and queries Shopify cart for stock level.
    """
    if not session:
        session = requests.Session()
        
    parsed_url = urlparse(product_url)
    domain = parsed_url.netloc
    
    # Append .json to get product detail metadata
    json_url = f"{product_url}.json"
    headers = get_headers(domain)
    
    logger.info(f"Fetching product metadata from {json_url}")
    try:
        # Add random delay
        time.sleep(random.uniform(1.0, 2.5))
        response = session.get(json_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            # Fall back to .js which is also supported in storefronts
            js_url = f"{product_url}.js"
            logger.info(f"Failed JSON metadata. Trying fallback JS metadata: {js_url}")
            response = session.get(js_url, headers=headers, timeout=10)
            
        if response.status_code != 200:
            logger.error(f"Failed to fetch metadata for {product_url}. Status: {response.status_code}")
            return False
            
        data = response.json()
        
        # Structure differs slightly between .json (wrapped in "product") and .js (root fields)
        product_data = data.get("product", data)
        product_name = product_data.get("title")
        variants = product_data.get("variants", [])
        
        logger.info(f"Found product: '{product_name}' with {len(variants)} variants.")
        
        for variant in variants:
            variant_id = variant.get("id")
            variant_title = variant.get("title")
            price = float(variant.get("price"))
            
            logger.info(f"Querying stock for variant: {variant_title} (ID: {variant_id}, Price: Rs. {price})")
            
            # Use Shopify Cart Reservation trick
            stock_qty = get_shopify_stock(domain, variant_id, session)
            
            if stock_qty is not None:
                velocity = insert_snapshot(
                    brand=brand,
                    product_name=product_name,
                    variant_id=str(variant_id),
                    variant_title=variant_title,
                    stock_qty=stock_qty,
                    price=price
                )
                logger.info(f"Saved snapshot: {brand} | {product_name} ({variant_title}) | Stock: {stock_qty} | Velocity: {velocity}")
            else:
                logger.warning(f"Could not retrieve stock level for variant {variant_id}")
                
        return True
    except Exception as e:
        logger.error(f"Error scraping product {product_url}: {e}")
        return False
