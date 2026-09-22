#!/usr/bin/env python3
"""
Initialize database tables for Shangzhou Smart Workbench.
Reads CREATE_TABLES_SQL from backend/models/tables.py and executes it.
"""
import os
import sys

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))


def main():
    try:
        from config import get_db
        from models.tables import CREATE_TABLES_SQL
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        print("         Make sure backend/config.py and backend/models/tables.py exist")
        sys.exit(1)

    try:
        db = get_db()
        cur = db.cursor()
        errors = 0
        for stmt in CREATE_TABLES_SQL.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    cur.execute(stmt)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"  Warning: {e}")
                        errors += 1
        db.commit()
        db.close()
        if errors:
            print(f"  [OK] Database tables initialized with {errors} warnings")
        else:
            print("  [OK] Database tables initialized")
    except Exception as e:
        print(f"  [FAIL] Database init failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
