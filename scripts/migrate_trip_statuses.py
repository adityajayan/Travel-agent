"""One-time migration: add is_archived column, map old statuses to new ones.

Usage: python -m scripts.migrate_trip_statuses
"""

import sqlite3
import sys

from core.config import settings

STATUS_MAP = {
    "pending": "planning",
    "running": "planning",
    "awaiting_approval": "review",
    "completed": "complete",
    # These stay the same but are listed for clarity:
    "complete": "complete",
    "failed": "failed",
    "cancelled": "cancelled",
}


def migrate() -> None:
    # Parse DB path from async URL
    db_url = settings.database_url
    db_path = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: Add is_archived column if not exists
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(trips)")]
    if "is_archived" not in columns:
        cursor.execute(
            "ALTER TABLE trips ADD COLUMN is_archived BOOLEAN DEFAULT 0 NOT NULL"
        )
        print("  Added is_archived column")
    else:
        print("  is_archived column already exists")

    # Step 2: Map old statuses to new
    for old_status, new_status in STATUS_MAP.items():
        if old_status == new_status:
            continue
        cursor.execute(
            "UPDATE trips SET status = ? WHERE status = ?",
            (new_status, old_status),
        )
        changed = cursor.rowcount
        if changed > 0:
            print(f"  {old_status} → {new_status}: {changed} row(s)")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()
