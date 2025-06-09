# === database.py ===
import sqlite3
from typing import Generator

DB_PATH = "data/leaderboard.db"

# Create table if it doesn't exist
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                user_id TEXT,
                facet TEXT,
                score INTEGER,
                PRIMARY KEY (user_id, facet)
            )
        ''')

init_db()

def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()