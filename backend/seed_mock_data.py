import random
from datetime import datetime, timedelta
try:
    from backend.database import init_db, insert_snapshot, get_db_connection
except ModuleNotFoundError:
    from database import init_db, insert_snapshot, get_db_connection

PRODUCTS_DATA = [
    {
        "brand": "HK Vitals",
        "product_name": "Multivitamin for Women",
        "variants": [
            {"id": "hkv_mvw_30", "title": "30 Tablets", "price": 399.0, "init_stock": 500},
            {"id": "hkv_mvw_60", "title": "60 Tablets", "price": 699.0, "init_stock": 350}
        ]
    },
    {
        "brand": "HK Vitals",
        "product_name": "Fish Oil Capsule",
        "variants": [
            {"id": "hkv_fo_60", "title": "60 Capsules", "price": 599.0, "init_stock": 420}
        ]
    },
    {
        "brand": "Kapiva",
        "product_name": "Wild Amla Juice",
        "variants": [
            {"id": "kap_waj_1l", "title": "1 Litre", "price": 299.0, "init_stock": 600}
        ]
    },
    {
        "brand": "Kapiva",
        "product_name": "Thar Aloe Vera Juice",
        "variants": [
            {"id": "kap_avj_1l", "title": "1 Litre", "price": 320.0, "init_stock": 450}
        ]
    },
    {
        "brand": "MuscleBlaze",
        "product_name": "Raw Whey Protein Concentrate 80%",
        "variants": [
            {"id": "mb_rwp_1kg", "title": "1 kg", "price": 1999.0, "init_stock": 250},
            {"id": "mb_rwp_2kg", "title": "2 kg", "price": 3799.0, "init_stock": 150}
        ]
    },
    {
        "brand": "Plix",
        "product_name": "Apple Cider Vinegar Tablets",
        "variants": [
            {"id": "plx_acv_15", "title": "15 Tablets", "price": 350.0, "init_stock": 800},
            {"id": "plx_acv_30", "title": "30 Tablets", "price": 650.0, "init_stock": 550}
        ]
    },
    {
        "brand": "OZiva",
        "product_name": "Protein & Herbs for Women",
        "variants": [
            {"id": "ozv_phw_choc", "title": "500g Chocolate", "price": 1699.0, "init_stock": 200},
            {"id": "ozv_phw_van", "title": "500g Vanilla", "price": 1699.0, "init_stock": 180}
        ]
    },
    {
        "brand": "Wellbeing Nutrition",
        "product_name": "Daily Greens Multivitamin",
        "variants": [
            {"id": "wbn_dg_15", "title": "15 Tablets", "price": 390.0, "init_stock": 400},
            {"id": "wbn_dg_30", "title": "30 Tablets", "price": 720.0, "init_stock": 300}
        ]
    },
    {
        "brand": "Fast&Up",
        "product_name": "Charge Vitamin C",
        "variants": [
            {"id": "fau_cvc_20", "title": "20 Tablets Orange", "price": 390.0, "init_stock": 700}
        ]
    },
    {
        "brand": "The Whole Truth",
        "product_name": "Dark Chocolate Peanut Butter",
        "variants": [
            {"id": "twt_pb_creamy", "title": "350g Creamy", "price": 450.0, "init_stock": 300},
            {"id": "twt_pb_crunchy", "title": "350g Crunchy", "price": 450.0, "init_stock": 280}
        ]
    },
    {
        "brand": "Cosmix",
        "product_name": "What Women Want",
        "variants": [
            {"id": "cmx_www_100", "title": "100g Powder", "price": 699.0, "init_stock": 250}
        ]
    },
    {
        "brand": "Setu Nutrition",
        "product_name": "Eye Max Lutein Gummies",
        "variants": [
            {"id": "set_emg_30", "title": "30 Gummies", "price": 599.0, "init_stock": 350}
        ]
    }
]

def seed_data():
    init_db()
    
    # We will seed 14 days of data, ending today (July 4, 2026)
    # So we start on June 20, 2026
    start_date = datetime(2026, 6, 20, 23, 59, 0)
    
    # Track stock states
    current_stocks = {}
    for product in PRODUCTS_DATA:
        for var in product["variants"]:
            current_stocks[var["id"]] = var["init_stock"]
            
    conn, _ = get_db_connection()
    # Clear existing snapshots for a clean seed
    conn.execute("DELETE FROM inventory_snapshots")
    conn.commit()
    conn.close()
    
    print("Seeding database with 14 days of historical data...")
    
    for i in range(15):  # 15 days total (June 20 to July 4)
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"Seeding date: {date_str}")
        
        for p in PRODUCTS_DATA:
            brand = p["brand"]
            product_name = p["product_name"]
            
            for var in p["variants"]:
                v_id = var["id"]
                v_title = var["title"]
                price = var["price"]
                
                # Retrieve current stock
                stock = current_stocks[v_id]
                
                # Daily sales decrement
                sales = random.randint(5, 30)
                
                # Restock condition (restock when stock drops below 120 or randomly every 5 days)
                restocked = False
                if stock - sales < 120 or (i > 0 and i % 6 == 0):
                    restock_qty = random.randint(250, 450)
                    stock = stock + restock_qty
                    restocked = True
                    # If restocked, we might still have sales, but today's final stock could be higher
                    # So the stock level after restocking is simply `stock - sales`
                    # If the stock goes up, velocity will register as 0
                
                final_stock = max(0, stock - sales)
                current_stocks[v_id] = final_stock
                
                # Save snapshot
                # This will automatically compute velocity based on the last record inserted
                insert_snapshot(
                    brand=brand,
                    product_name=product_name,
                    variant_id=v_id,
                    variant_title=v_title,
                    stock_qty=final_stock,
                    price=price,
                    timestamp=date_str
                )
                
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_data()
