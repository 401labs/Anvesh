import os
import time
import psycopg
from psycopg.rows import dict_row
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env.local or .env
load_dotenv(".env.local")
load_dotenv()

# Database Configuration
DB_CONFIG = {
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "lead_scraper")
}

def get_connection():
    """Create and return a connection to the PostgreSQL database."""
    conn_str = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    return psycopg.connect(conn_str, row_factory=dict_row)

def init_db():
    """Initialize the PostgreSQL database and the leads table."""
    max_retries = 10
    retry_delay = 3
    
    # 1. Connect to default 'postgres' db to create our target db if it doesn't exist
    for attempt in range(max_retries):
        try:
            sys_conn_str = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/postgres"
            with psycopg.connect(sys_conn_str, autocommit=True) as conn:
                res = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG['dbname'],)).fetchone()
                if not res:
                    print(f"🛠️  Database '{DB_CONFIG['dbname']}' not found. Creating...")
                    conn.execute(f"CREATE DATABASE {DB_CONFIG['dbname']}")
                    print(f"✅ Database '{DB_CONFIG['dbname']}' created.")
                else:
                    print(f"✅ Database '{DB_CONFIG['dbname']}' exists.")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Database not ready (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s... Error: {e}")
                time.sleep(retry_delay)
            else:
                print(f"❌ Database Init Error: {e}")
                # We raise here because if DB doesn't exist/connect, app shouldn't start
                raise e

    # 2. Connect to the specific database to create the table
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS leads (
                        id SERIAL PRIMARY KEY,
                        business_name VARCHAR(255),
                        industry VARCHAR(255),
                        category VARCHAR(255),
                        location VARCHAR(255),
                        address TEXT,
                        rating DECIMAL(3, 1),
                        review_count INT,
                        is_claimed BOOLEAN,
                        has_website BOOLEAN,
                        website_url TEXT,
                        phone VARCHAR(255),
                        email VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (business_name, address)
                    )
                ''')
                # Migration for pre-existing databases created before the email column existed.
                cur.execute('ALTER TABLE leads ADD COLUMN IF NOT EXISTS email VARCHAR(255)')
                conn.commit()
        print("✅ PostgreSQL Table 'leads' initialized.")
        
        # Initialize API key tables
        from app.db.api_keys import create_tables as create_api_key_tables
        create_api_key_tables()
    except Exception as e:
        print(f"❌ Table Init Error: {e}")

def insert_lead(lead: Dict):
    """Insert a lead into PostgreSQL. Returns True if added, False if duplicate."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = '''
                    INSERT INTO leads (
                        business_name, industry, category, location, address,
                        rating, review_count, is_claimed,
                        has_website, website_url, phone, email
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (business_name, address) DO NOTHING
                    RETURNING id
                '''
                values = (
                    lead["business_name"],
                    lead["industry"],
                    lead.get("category"),
                    lead["location"],
                    lead["address"],
                    lead.get("rating"),
                    lead.get("review_count"),
                    lead.get("is_claimed"),
                    lead["has_website"],
                    lead["website_url"],
                    lead["phone"],
                    lead.get("email")
                )
                cur.execute(query, values)
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    return True
                else:
                    return False
    except Exception as e:
        print(f"❌ Insert Error: {e}")
        return False

LEAD_SORT_COLUMNS = {
    "created_at": "created_at",
    "rating": "rating",
    "review_count": "review_count",
    "business_name": "business_name",
}


def _build_lead_filters(filters: Optional[Dict]) -> tuple:
    """Build a WHERE clause + params list from a filters dict. Every key is optional."""
    filters = filters or {}
    clauses = []
    params = []

    if filters.get("industry"):
        clauses.append("industry ILIKE %s")
        params.append(filters["industry"])
    if filters.get("location"):
        clauses.append("location ILIKE %s")
        params.append(filters["location"])
    if filters.get("category"):
        clauses.append("category ILIKE %s")
        params.append(filters["category"])
    if filters.get("has_website") is not None:
        clauses.append("has_website = %s")
        params.append(filters["has_website"])
    if filters.get("has_email") is not None:
        if filters["has_email"]:
            clauses.append("email IS NOT NULL AND email != ''")
        else:
            clauses.append("(email IS NULL OR email = '')")
    if filters.get("is_claimed") is not None:
        clauses.append("is_claimed = %s")
        params.append(filters["is_claimed"])
    if filters.get("min_rating") is not None:
        clauses.append("rating >= %s")
        params.append(filters["min_rating"])
    if filters.get("search"):
        like = f"%{filters['search']}%"
        clauses.append("(business_name ILIKE %s OR address ILIKE %s OR phone ILIKE %s)")
        params.extend([like, like, like])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def get_all_leads(filters: Optional[Dict] = None):
    """Retrieve all leads matching `filters` (or all leads if none) for CSV export."""
    where_sql, params = _build_lead_filters(filters)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM leads {where_sql} ORDER BY created_at DESC", params)
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
        return []


def get_leads(limit: int = 20, offset: int = 0, filters: Optional[Dict] = None, sort_by: str = "created_at", sort_dir: str = "desc"):
    """Retrieve a page of leads matching `filters`, sorted by `sort_by`/`sort_dir`."""
    where_sql, params = _build_lead_filters(filters)
    sort_column = LEAD_SORT_COLUMNS.get(sort_by, "created_at")
    sort_direction = "ASC" if sort_dir == "asc" else "DESC"
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = (
                    f"SELECT * FROM leads {where_sql} "
                    f"ORDER BY {sort_column} {sort_direction} NULLS LAST LIMIT %s OFFSET %s"
                )
                cur.execute(query, params + [limit, offset])
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
        return []


def count_leads(filters: Optional[Dict] = None) -> int:
    """Count leads matching `filters` (or all leads if none)."""
    where_sql, params = _build_lead_filters(filters)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM leads {where_sql}", params)
                result = cur.fetchone()
                return result["count"] if result else 0
    except Exception as e:
        print(f"❌ Count Error: {e}")
        return 0


def get_lead_filter_options() -> Dict:
    """Distinct values currently in use, for populating filter dropdowns."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL AND industry != '' ORDER BY industry")
                industries = [r["industry"] for r in cur.fetchall()]

                cur.execute("SELECT DISTINCT location FROM leads WHERE location IS NOT NULL AND location != '' ORDER BY location")
                locations = [r["location"] for r in cur.fetchall()]

                cur.execute("SELECT DISTINCT category FROM leads WHERE category IS NOT NULL AND category NOT IN ('', 'N/A') ORDER BY category")
                categories = [r["category"] for r in cur.fetchall()]

                return {"industries": industries, "locations": locations, "categories": categories}
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
        return {"industries": [], "locations": [], "categories": []}


def get_lead(lead_id: int) -> Optional[Dict]:
    """Retrieve a single lead by ID."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
                return cur.fetchone()
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
        return None


def create_lead(lead: Dict) -> Optional[Dict]:
    """
    Manually create a lead (as opposed to insert_lead, used by the scraper).
    Returns the created row, or None if a lead with the same
    (business_name, address) already exists.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO leads (
                        business_name, industry, category, location, address,
                        rating, review_count, is_claimed,
                        has_website, website_url, phone, email
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (business_name, address) DO NOTHING
                    RETURNING *
                ''', (
                    lead["business_name"],
                    lead["industry"],
                    lead.get("category"),
                    lead["location"],
                    lead["address"],
                    lead.get("rating"),
                    lead.get("review_count"),
                    lead.get("is_claimed"),
                    lead.get("has_website", False),
                    lead.get("website_url"),
                    lead.get("phone"),
                    lead.get("email"),
                ))
                result = cur.fetchone()
                conn.commit()
                return result
    except Exception as e:
        print(f"❌ Insert Error: {e}")
        return None


LEAD_UPDATABLE_FIELDS = (
    "business_name", "industry", "category", "location", "address",
    "rating", "review_count", "is_claimed", "has_website", "website_url", "phone", "email",
)


def update_lead(lead_id: int, fields: Dict) -> Optional[Dict]:
    """
    Update a lead. `fields` may contain any subset of LEAD_UPDATABLE_FIELDS —
    only keys present are changed. Returns the updated row, or None if not found.
    """
    updates = {k: v for k, v in fields.items() if k in LEAD_UPDATABLE_FIELDS}
    if not updates:
        return get_lead(lead_id)

    set_clause = ", ".join(f"{col} = %s" for col in updates)
    values = list(updates.values()) + [lead_id]

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE leads SET {set_clause} WHERE id = %s RETURNING *",
                    values
                )
                result = cur.fetchone()
                conn.commit()
                return result
    except Exception as e:
        print(f"❌ Update Error: {e}")
        return None


def delete_lead(lead_id: int) -> bool:
    """Permanently delete a lead."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM leads WHERE id = %s RETURNING id", (lead_id,))
                result = cur.fetchone()
                conn.commit()
                return result is not None
    except Exception as e:
        print(f"❌ Delete Error: {e}")
        return False


def bulk_delete_leads(lead_ids: List[int]) -> int:
    """Delete multiple leads by ID. Returns the number actually deleted."""
    if not lead_ids:
        return 0
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM leads WHERE id = ANY(%s) RETURNING id",
                    (lead_ids,)
                )
                deleted = cur.fetchall()
                conn.commit()
                return len(deleted)
    except Exception as e:
        print(f"❌ Bulk Delete Error: {e}")
        return 0
