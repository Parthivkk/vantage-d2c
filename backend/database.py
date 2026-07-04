import sqlite3
import os
from datetime import datetime
import urllib.parse as urlparse

# psycopg2 is only required if we connect to Supabase/PostgreSQL
try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    """
    Returns a database connection.
    If DATABASE_URL is set in environment, connects to PostgreSQL (Supabase).
    Otherwise, falls back to local SQLite database.
    """
    if DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")):
        if not HAS_POSTGRES:
            raise ImportError("psycopg2-binary is not installed but DATABASE_URL requires PostgreSQL.")
        
        # Render sometimes provides postgres:// URLs, but psycopg2 requires postgresql://
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
            
        conn = psycopg2.connect(url)
        return conn, "postgres"
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

def execute_write(query, params=()):
    """
    Executes a query that writes data (INSERT, UPDATE, CREATE, DELETE).
    Automatically adapts placeholders (%s vs ?) for SQLite.
    """
    conn, db_type = get_db_connection()
    try:
        cursor = conn.cursor()
        if db_type == "sqlite":
            # Convert %s placeholders to SQLite ? placeholders
            sqlite_query = query.replace("%s", "?")
            cursor.execute(sqlite_query, params)
        else:
            cursor.execute(query, params)
        conn.commit()
    finally:
        conn.close()

def execute_read(query, params=()):
    """
    Executes a SELECT query and returns rows as dictionaries.
    """
    conn, db_type = get_db_connection()
    try:
        if db_type == "sqlite":
            cursor = conn.cursor()
            sqlite_query = query.replace("%s", "?")
            cursor.execute(sqlite_query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        else:
            # PostgreSQL connection returns RealDictRow or standard tuple.
            # We use DictCursor for dictionary output.
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()

def init_db():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    if db_type == "sqlite":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                brand TEXT NOT NULL,
                product_name TEXT NOT NULL,
                variant_id TEXT NOT NULL,
                variant_title TEXT NOT NULL,
                stock_qty INTEGER,
                price REAL NOT NULL,
                sales_velocity INTEGER DEFAULT 0
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_variant_timestamp ON inventory_snapshots(variant_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand_timestamp ON inventory_snapshots(brand, timestamp)")
    else:
        # PostgreSQL syntax for Supabase
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_snapshots (
                id SERIAL PRIMARY KEY,
                timestamp VARCHAR(50) NOT NULL,
                brand VARCHAR(100) NOT NULL,
                product_name VARCHAR(255) NOT NULL,
                variant_id VARCHAR(100) NOT NULL,
                variant_title VARCHAR(100) NOT NULL,
                stock_qty INTEGER,
                price DOUBLE PRECISION NOT NULL,
                sales_velocity INTEGER DEFAULT 0
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_variant_timestamp ON inventory_snapshots(variant_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand_timestamp ON inventory_snapshots(brand, timestamp)")
        
    conn.commit()
    conn.close()

def get_latest_stock(variant_id):
    """
    Get the most recent stock level for a variant before today.
    """
    query = """
        SELECT stock_qty FROM inventory_snapshots
        WHERE variant_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
    """
    rows = execute_read(query, (str(variant_id),))
    return rows[0]["stock_qty"] if rows else None

def insert_snapshot(brand, product_name, variant_id, variant_title, stock_qty, price, timestamp=None):
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate daily sales velocity
    prev_stock = get_latest_stock(variant_id)
    sales_velocity = 0
    
    if prev_stock is not None and stock_qty is not None:
        if prev_stock >= 0 and stock_qty >= 0:
            sales_velocity = max(0, prev_stock - stock_qty)
            
    query = """
        INSERT INTO inventory_snapshots (
            timestamp, brand, product_name, variant_id, variant_title, stock_qty, price, sales_velocity
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_write(query, (timestamp, brand, product_name, str(variant_id), variant_title, stock_qty, price, sales_velocity))
    return sales_velocity
