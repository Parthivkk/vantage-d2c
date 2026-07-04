from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
try:
    from backend.database import execute_read, init_db
except ModuleNotFoundError:
    from database import execute_read, init_db

app = FastAPI(title="Shopify Competitive Intelligence API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """
    Initialize database tables and indexes on application startup.
    Works for both local SQLite and Supabase PostgreSQL.
    """
    init_db()

@app.post("/api/scrape")
@app.get("/api/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    """
    Webhook to trigger daily inventory scraper in the background.
    """
    try:
        from backend.scheduler import run_daily_sync
    except ModuleNotFoundError:
        from scheduler import run_daily_sync
    background_tasks.add_task(run_daily_sync)
    return {"status": "success", "message": "Scraper execution scheduled in the background."}

@app.get("/api/seed")
def trigger_seed(background_tasks: BackgroundTasks):
    """
    Endpoint to seed historical mock data on the remote database.
    """
    try:
        from backend.seed_mock_data import seed_data
    except ModuleNotFoundError:
        from seed_mock_data import seed_data
    background_tasks.add_task(seed_data)
    return {"status": "success", "message": "Database seeding scheduled in the background."}

def get_latest_timestamps():
    query = "SELECT DISTINCT timestamp FROM inventory_snapshots ORDER BY timestamp DESC LIMIT 2"
    rows = execute_read(query)
    today = rows[0]["timestamp"] if len(rows) > 0 else None
    yesterday = rows[1]["timestamp"] if len(rows) > 1 else None
    return today, yesterday

@app.get("/api/brands")
def get_brands():
    query = "SELECT DISTINCT brand FROM inventory_snapshots ORDER BY brand ASC"
    rows = execute_read(query)
    brands = [row["brand"] for row in rows]
    
    # Fallback to the 10 target brands if DB is empty
    if not brands:
        brands = [
            "HK Vitals", "Kapiva", "MuscleBlaze", "Plix", "OZiva", 
            "Wellbeing Nutrition", "Fast&Up", "The Whole Truth", "Cosmix", "Setu Nutrition"
        ]
    return brands

@app.get("/api/dashboard")
def get_dashboard_data(brand: str = Query(..., description="Brand to filter dashboard data")):
    today_ts, yesterday_ts = get_latest_timestamps()
    
    if not today_ts:
        return {"error": "No inventory snapshots found. Please run the scraper or seed mock data."}
        
    # 1. Fetch table data comparing today and yesterday
    # If yesterday doesn't exist, we fall back starting stock to: current_stock + units_sold_today
    query = """
        SELECT 
            t.product_name,
            t.variant_title,
            t.variant_id,
            COALESCE(y.stock_qty, t.stock_qty + t.sales_velocity) AS starting_stock,
            t.stock_qty AS current_stock,
            t.sales_velocity AS units_sold_today,
            COALESCE(y.sales_velocity, 0) AS units_sold_yesterday,
            t.price
        FROM inventory_snapshots t
        LEFT JOIN inventory_snapshots y 
            ON t.variant_id = y.variant_id AND y.timestamp = %s
        WHERE t.brand = %s AND t.timestamp = %s
        ORDER BY units_sold_today DESC
    """
    table_rows = execute_read(query, (yesterday_ts, brand, today_ts))
    table_data = []
    
    total_items_sold = 0
    est_revenue = 0.0
    hero_variant = None
    max_sold = -1
    
    for row in table_rows:
        sold_today = row["units_sold_today"]
        sold_yesterday = row["units_sold_yesterday"]
        price = row["price"]
        
        # Calculate Day-over-Day % change in sales velocity
        if sold_yesterday > 0:
            dod_change = round(((sold_today - sold_yesterday) / sold_yesterday) * 100, 1)
        else:
            dod_change = 0.0 if sold_today == 0 else 100.0
            
        table_data.append({
            "product_name": row["product_name"],
            "variant_title": row["variant_title"],
            "starting_stock": row["starting_stock"],
            "current_stock": row["current_stock"],
            "units_sold_today": sold_today,
            "dod_pct_change": dod_change,
            "price": price
        })
        
        total_items_sold += sold_today
        est_revenue += (sold_today * price)
        
        if sold_today > max_sold:
            max_sold = sold_today
            hero_variant = f"{row['product_name']} ({row['variant_title']})"
            
    # If no items sold at all
    if total_items_sold == 0 and len(table_rows) > 0:
        hero_variant = f"{table_rows[0]['product_name']} ({table_rows[0]['variant_title']})"
        
    metrics = {
        "total_sold_today": total_items_sold,
        "hero_product": hero_variant or "N/A",
        "est_revenue_today": est_revenue
    }
    
    # 2. Get top 5 variants of this brand in the last 7 days to show in trends chart
    query_ts = "SELECT DISTINCT timestamp FROM inventory_snapshots ORDER BY timestamp DESC LIMIT 7"
    rows_ts = execute_read(query_ts)
    last_7_timestamps = [r["timestamp"] for r in rows_ts]
    last_7_timestamps.reverse() # chronologically ascending
    
    chart_data = []
    if last_7_timestamps:
        min_ts = last_7_timestamps[0]
        
        # Identify top 5 selling variants by total sales over these 7 days
        # Group by all selected non-aggregate columns to satisfy PostgreSQL strictness
        query_top = """
            SELECT variant_id, product_name, variant_title, SUM(sales_velocity) as total_sales
            FROM inventory_snapshots
            WHERE brand = %s AND timestamp >= %s
            GROUP BY variant_id, product_name, variant_title
            ORDER BY total_sales DESC
            LIMIT 5
        """
        top_variants = execute_read(query_top, (brand, min_ts))
        top_variant_ids = [v["variant_id"] for v in top_variants]
        variant_names = {v["variant_id"]: f"{v['product_name']} ({v['variant_title']})" for v in top_variants}
        
        # Query details for these top variants over the last 7 days
        if top_variant_ids:
            placeholders = ",".join("%s" for _ in top_variant_ids)
            query_rec = f"""
                SELECT timestamp, variant_id, sales_velocity
                FROM inventory_snapshots
                WHERE brand = %s AND timestamp >= %s AND variant_id IN ({placeholders})
                ORDER BY timestamp ASC
            """
            records = execute_read(query_rec, (brand, min_ts, *top_variant_ids))
            
            # Reformat to: { timestamp: { 'date': 'YYYY-MM-DD', 'Variant A': X, 'Variant B': Y } }
            temp_chart = {}
            for ts in last_7_timestamps:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                date_label = dt.strftime("%b %d")
                temp_chart[ts] = {"date": date_label}
                for v_id in top_variant_ids:
                    temp_chart[ts][variant_names[v_id]] = 0
                    
            for rec in records:
                ts = rec["timestamp"]
                v_id = rec["variant_id"]
                velocity = rec["sales_velocity"]
                if ts in temp_chart and v_id in variant_names:
                    temp_chart[ts][variant_names[v_id]] = velocity
                    
            chart_data = [temp_chart[ts] for ts in last_7_timestamps]
            
    return {
        "metrics": metrics,
        "table_data": table_data,
        "chart_data": chart_data
    }
