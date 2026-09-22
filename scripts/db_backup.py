#!/usr/bin/env python3
"""
Database backup/restore tool for Shangzhou Smart Workbench.
Uses PyMySQL to dump/restore the szagent database.

Usage:
  python db_backup.py backup [--full] [--db DB_NAME]
  python db_backup.py restore [--file FILE]
  python db_backup.py list
"""
import os
import sys
import argparse
from datetime import datetime

try:
    import pymysql
except ImportError:
    print("[ERROR] PyMySQL not installed. Run: pip install pymysql")
    sys.exit(1)

# --- Config (override via environment variables) ---
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASS = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "szagent")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(SCRIPT_DIR, "..", "backups")


def get_conn(database=None):
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=database,
        charset="utf8mb4",
    )


def cmd_backup(args):
    db_name = args.db or DB_NAME
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.full:
        backup_file = os.path.join(BACKUP_DIR, f"full_{timestamp}.sql")
    else:
        backup_file = os.path.join(BACKUP_DIR, f"{db_name}_{timestamp}.sql")

    print(f"[Mode] {'Full' if args.full else 'Single'} database backup")
    print(f"[Target] {backup_file}")

    try:
        conn = get_conn(None if args.full else db_name)
        cur = conn.cursor()

        with open(backup_file, "w", encoding="utf-8") as f:
            f.write("-- Shangzhou Smart Workbench Database Backup\n")
            f.write(f"-- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-- ============================================\n\n")

            # Determine which databases to dump
            if args.full:
                cur.execute("SHOW DATABASES")
                databases = [
                    row[0]
                    for row in cur.fetchall()
                    if row[0]
                    not in ("information_schema", "performance_schema", "mysql", "sys")
                ]
            else:
                databases = [db_name]

            for db in databases:
                print(f"  Dumping: {db}")
                cur.execute(f"USE `{db}`")
                cur.execute("SHOW TABLES")
                tables = [row[0] for row in cur.fetchall()]

                f.write(f"\n-- Database: {db}\n")
                f.write(f"CREATE DATABASE IF NOT EXISTS `{db}`;\n")
                f.write(f"USE `{db}`;\n")

                for table in tables:
                    # Table structure
                    cur.execute(f"SHOW CREATE TABLE `{table}`")
                    create = cur.fetchone()
                    f.write(f"\n-- Table structure: {table}\n")
                    f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                    f.write(create[1] + ";\n\n")

                    # Table data
                    cur.execute(f"SELECT * FROM `{table}`")
                    rows = cur.fetchall()
                    if rows:
                        f.write(f"-- Data: {table} ({len(rows)} rows)\n")
                        for row in rows:
                            vals = []
                            for v in row:
                                if v is None:
                                    vals.append("NULL")
                                elif isinstance(v, (int, float)):
                                    vals.append(str(v))
                                else:
                                    vals.append(
                                        "'" + str(v).replace("'", "''") + "'"
                                    )
                            f.write(
                                f"INSERT INTO `{table}` VALUES ({','.join(vals)});\n"
                            )
                        f.write("\n")

        conn.close()
        size = os.path.getsize(backup_file)
        print(f"[OK] Backup complete: {backup_file}")
        print(f"     Size: {size:,} bytes")
    except Exception as e:
        print(f"[ERROR] Backup failed: {e}")
        sys.exit(1)


def cmd_restore(args):
    # Find latest backup if no file specified
    if args.file:
        backup_file = args.file
    else:
        if not os.path.isdir(BACKUP_DIR):
            print("[ERROR] No backup directory found")
            sys.exit(1)
        sql_files = sorted(
            (f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")),
            reverse=True,
        )
        if not sql_files:
            print("[ERROR] No backup files found")
            sys.exit(1)
        backup_file = os.path.join(BACKUP_DIR, sql_files[0])

    print(f"[Restore] {backup_file}")

    try:
        conn = get_conn(None)
        cur = conn.cursor()

        with open(backup_file, "r", encoding="utf-8") as f:
            sql = f.read()

        statements = 0
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--") and not stmt.startswith("/*"):
                try:
                    cur.execute(stmt)
                    statements += 1
                except Exception as e:
                    msg = str(e).lower()
                    if "already exists" not in msg:
                        print(f"  Warning: {e}")

        conn.commit()
        conn.close()
        print(f"[OK] Restore complete ({statements} statements)")
    except Exception as e:
        print(f"[ERROR] Restore failed: {e}")
        sys.exit(1)


def cmd_list(_args):
    if not os.path.isdir(BACKUP_DIR):
        print("No backup directory found.")
        return

    sql_files = sorted(
        (f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")),
        reverse=True,
    )
    if not sql_files:
        print("No backup files found.")
        return

    print("[Backup List]")
    print("-" * 46)
    for f in sql_files:
        path = os.path.join(BACKUP_DIR, f)
        size = os.path.getsize(path)
        print(f"  {f}  ({size:,} bytes)")
    print(f"\nBackup directory: {BACKUP_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Database backup/restore tool")
    sub = parser.add_subparsers(dest="command")

    p_backup = sub.add_parser("backup", help="Backup database")
    p_backup.add_argument("--full", action="store_true", help="Backup all databases")
    p_backup.add_argument("--db", help="Database name (default: szagent)")

    p_restore = sub.add_parser("restore", help="Restore database")
    p_restore.add_argument("--file", help="Backup file to restore")

    sub.add_parser("list", help="List all backups")

    args = parser.parse_args()

    if args.command == "backup":
        cmd_backup(args)
    elif args.command == "restore":
        cmd_restore(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
