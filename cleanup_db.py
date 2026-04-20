import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "prev_articles.db")
TABLE_NAME = "PREV_ARTICLES"


def delete_older_than_30_days() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE_NAME,),
        )
        if cursor.fetchone() is None:
            print(f"Table {TABLE_NAME} does not exist yet; skipping cleanup.")
            return

        cursor.execute(
            f"DELETE FROM {TABLE_NAME} WHERE added_at < datetime('now', '-30 days')"
        )
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"Deleted {deleted_count} rows older than 30 days.")


if __name__ == "__main__":
    if Path(DB_PATH).is_file():
        delete_older_than_30_days()
    else:
        print(f"Database file {DB_PATH} does not exist yet; skipping cleanup.")
