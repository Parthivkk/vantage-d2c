import requests
import logging
from datetime import datetime
from database import init_db
from scraper import scrape_product

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# List of target competitors and a sample product URL for each.
# (In production, you would fetch these target URLs from a database table)
TARGETS = [
    {
        "brand": "HK Vitals",
        "url": "https://www.hkvitals.com/products/healthkart-hkvitals-multivitamin-for-women"
    },
    {
        "brand": "Kapiva",
        "url": "https://www.kapiva.in/products/kapiva-wild-amla-juice-1l"
    },
    {
        "brand": "MuscleBlaze",
        "url": "https://www.muscleblaze.com/products/muscleblaze-raw-whey-protein-concentrate-80"
    },
    {
        "brand": "Plix",
        "url": "https://www.plixlife.com/products/plix-apple-cider-vinegar-effervescent-tablets"
    },
    {
        "brand": "OZiva",
        "url": "https://www.oziva.in/products/oziva-protein-herbs-for-women"
    },
    {
        "brand": "Wellbeing Nutrition",
        "url": "https://wellbeingnutrition.com/products/daily-greens-multivitamin"
    },
    {
        "brand": "Fast&Up",
        "url": "https://www.fastandup.in/products/fast-up-charge-natural-vitamin-c"
    },
    {
        "brand": "The Whole Truth",
        "url": "https://thewholetruthfoods.com/products/dark-chocolate-peanut-butter"
    },
    {
        "brand": "Cosmix",
        "url": "https://cosmix.in/products/what-women-want"
    },
    {
        "brand": "Setu Nutrition",
        "url": "https://www.setu.in/products/eye-max-lutein-gummies"
    }
]

def run_daily_sync():
    """
    Daily Sync Job triggered at 11:59 PM.
    """
    start_time = datetime.now()
    logger.info(f"Starting daily inventory scrape at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize the database and table structures if they don't exist
    init_db()
    
    session = requests.Session()
    success_count = 0
    failure_count = 0
    
    for target in TARGETS:
        brand = target["brand"]
        url = target["url"]
        logger.info(f"Processing brand: {brand} | URL: {url}")
        
        success = scrape_product(brand=brand, product_url=url, session=session)
        if success:
            success_count += 1
        else:
            failure_count += 1
            logger.error(f"Failed to scrape {brand} product: {url}")
            
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Daily scrape finished. Success: {success_count}, Failures: {failure_count}. Duration: {duration:.2f}s")

if __name__ == "__main__":
    run_daily_sync()
