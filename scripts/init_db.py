"""
init_db.py — Database initialization script.

Run this once before starting the tracker for the first time,
or any time you need to reset/recreate the database.

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --db-path data/custom.db
    python scripts/init_db.py --reset   # WARNING: drops all data
"""

import argparse
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.storage.database import Database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize the CSC Job Tracker SQLite database."
    )
    parser.add_argument(
        "--db-path",
        default="data/jobs.db",
        help="Path to the SQLite database file (default: data/jobs.db)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all existing tables before re-creating them. "
             "WARNING: all data will be lost.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    db = Database(db_path=args.db_path)

    if args.reset:
        confirm = input(
            f"\n⚠️  This will DELETE all data in '{args.db_path}'.\n"
            "Type 'yes' to confirm: "
        ).strip()
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
        print("🗑️  Dropping all tables...")
        db.drop_all_tables()

    print(f"🗄️  Initializing database at: {args.db_path}")
    db.initialize()

    stats = db.get_statistics()
    print("✅  Database ready.")
    print(f"    Total jobs tracked : {stats.total_jobs}")
    print(f"    Notifications sent : {stats.total_notifications_sent}")
    print(f"    DB path            : {db.db_path.resolve()}")


if __name__ == "__main__":
    main()
