from app.db.database import get_connection


def seed_data():
    conn = get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO posts (id, title, content) VALUES (1, 'Welcome', 'Seed post created')")
        conn.commit()
    finally:
        conn.close()
