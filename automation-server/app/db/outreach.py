"""
Outreach database operations: email templates and outreach logs.
"""
from typing import Dict, List, Optional
from app.db.database import get_connection


DEFAULT_TEMPLATES = [
    {
        "name": "Cold intro",
        "subject": "Quick question about {{business_name}}'s online presence",
        "body": (
            "Hi {{business_name}} team,\n\n"
            "I came across your business in {{location}} and noticed you don't have a website yet. "
            "I help local {{industry}} businesses get found online and wanted to see if that's "
            "something you'd be interested in.\n\n"
            "Would you be open to a quick chat this week?\n\n"
            "Best,\n[Your name]"
        ),
    },
    {
        "name": "Follow-up",
        "subject": "Re: Quick question about {{business_name}}",
        "body": (
            "Hi again,\n\n"
            "Just following up on my last note — I know things get busy! If getting "
            "{{business_name}} online is something you'd like help with, I'd love to chat "
            "whenever works for you.\n\n"
            "No pressure either way.\n\n"
            "Best,\n[Your name]"
        ),
    },
    {
        "name": "Unclaimed listing",
        "subject": "{{business_name}}'s Google listing isn't claimed yet",
        "body": (
            "Hi {{business_name}} team,\n\n"
            "I noticed your Google Business listing in {{location}} isn't claimed yet — that means "
            "you're missing out on being able to respond to reviews, update your hours, and show up "
            "better in local search.\n\n"
            "I help businesses like yours get set up properly online. Happy to walk you through it "
            "if you're interested.\n\n"
            "Best,\n[Your name]"
        ),
    },
]


def create_tables():
    """Create email_templates and outreach_logs tables if they don't exist, seeding
    a few starter templates the very first time the table is created (not on every
    startup — deliberately-deleted defaults don't reappear on a later restart)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('email_templates')")
            table_existed = cur.fetchone()["to_regclass"] is not None

            cur.execute('''
                CREATE TABLE IF NOT EXISTS email_templates (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS outreach_logs (
                    id SERIAL PRIMARY KEY,
                    lead_id INT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
                    channel VARCHAR(20) NOT NULL,
                    status VARCHAR(30) NOT NULL,
                    subject TEXT,
                    body TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

            if not table_existed:
                for template in DEFAULT_TEMPLATES:
                    cur.execute(
                        "INSERT INTO email_templates (name, subject, body) VALUES (%s, %s, %s)",
                        (template["name"], template["subject"], template["body"]),
                    )
                conn.commit()
                print(f"✅ Seeded {len(DEFAULT_TEMPLATES)} default email templates.")
    print("✅ PostgreSQL Tables 'email_templates' and 'outreach_logs' initialized.")


# ============== Email Templates ==============

def create_template(name: str, subject: str, body: str) -> Optional[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO email_templates (name, subject, body)
                    VALUES (%s, %s, %s)
                    RETURNING *
                ''', (name, subject, body))
                result = cur.fetchone()
                conn.commit()
                return result
    except Exception as e:
        print(f"❌ Template Create Error: {e}")
        return None


def get_template(template_id: int) -> Optional[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM email_templates WHERE id = %s", (template_id,))
                return cur.fetchone()
    except Exception as e:
        print(f"❌ Template Fetch Error: {e}")
        return None


def list_templates() -> List[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM email_templates ORDER BY created_at DESC")
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Template Fetch Error: {e}")
        return []


def update_template(template_id: int, fields: Dict) -> Optional[Dict]:
    updatable = ("name", "subject", "body")
    updates = {k: v for k, v in fields.items() if k in updatable}
    if not updates:
        return get_template(template_id)

    set_clause = ", ".join(f"{col} = %s" for col in updates)
    values = list(updates.values()) + [template_id]

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE email_templates SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING *",
                    values
                )
                result = cur.fetchone()
                conn.commit()
                return result
    except Exception as e:
        print(f"❌ Template Update Error: {e}")
        return None


def delete_template(template_id: int) -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM email_templates WHERE id = %s RETURNING id", (template_id,))
                result = cur.fetchone()
                conn.commit()
                return result is not None
    except Exception as e:
        print(f"❌ Template Delete Error: {e}")
        return False


# ============== Outreach Logs ==============

def create_log(lead_id: int, channel: str, status: str, subject: Optional[str] = None,
                body: Optional[str] = None, error: Optional[str] = None) -> Optional[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO outreach_logs (lead_id, channel, status, subject, body, error)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                ''', (lead_id, channel, status, subject, body, error))
                result = cur.fetchone()
                conn.commit()
                return result
    except Exception as e:
        print(f"❌ Outreach Log Create Error: {e}")
        return None


def list_logs(lead_id: Optional[int] = None, limit: int = 20, offset: int = 0) -> List[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if lead_id is not None:
                    cur.execute('''
                        SELECT * FROM outreach_logs WHERE lead_id = %s
                        ORDER BY created_at DESC LIMIT %s OFFSET %s
                    ''', (lead_id, limit, offset))
                else:
                    cur.execute('''
                        SELECT * FROM outreach_logs
                        ORDER BY created_at DESC LIMIT %s OFFSET %s
                    ''', (limit, offset))
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Outreach Log Fetch Error: {e}")
        return []


def count_logs(lead_id: Optional[int] = None) -> int:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if lead_id is not None:
                    cur.execute("SELECT COUNT(*) AS count FROM outreach_logs WHERE lead_id = %s", (lead_id,))
                else:
                    cur.execute("SELECT COUNT(*) AS count FROM outreach_logs")
                result = cur.fetchone()
                return result["count"] if result else 0
    except Exception as e:
        print(f"❌ Outreach Log Count Error: {e}")
        return 0


def get_outreach_stats() -> Dict:
    """Aggregate email send/failure counts for the analytics dashboard."""
    stats = {"total": 0, "sent": 0, "failed": 0}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT status, COUNT(*) AS count FROM outreach_logs
                    WHERE channel = 'email' GROUP BY status
                """)
                for row in cur.fetchall():
                    if row["status"] in stats:
                        stats[row["status"]] = row["count"]
                    stats["total"] += row["count"]
    except Exception as e:
        print(f"❌ Outreach Stats Error: {e}")
    return stats
