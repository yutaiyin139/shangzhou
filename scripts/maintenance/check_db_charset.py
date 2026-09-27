# -*- coding: utf-8 -*-
"""全库字符集体检：找出仍然不是 utf8mb4 的表与列。

为什么要这么扫一次：本项目吃过两次同一类亏——
  · emoji 图标被写成字面量 '?'，11 条智能体图标不可还原；
  · 应用模板创建报「mapping keys are not expected」，根因也是 emoji 被截坏后
    把 DSL YAML 弄脏。
表级校对集看着对（utf8mb4_0900_ai_ci）不代表每列都对：列可以继承旧定义，
而 MySQL 在非 utf8mb4 列上写 4 字节字符是**截断成 ?**，不报错。所以必须逐列扫。

    python scripts/maintenance/check_db_charset.py

只读，不改任何数据。发现问题时打印可执行的修复 SQL，由人确认后手工执行
（ALTER ... CONVERT 会重建表，属于要挑窗口做的事，脚本不擅自动库）。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from config import get_db  # noqa: E402


def main():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT DATABASE() AS n")
    schema = (cur.fetchone() or {}).get('n') or ''

    cur.execute(
        "SELECT COUNT(1) AS n FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'", (schema,))
    n_tables = int((cur.fetchone() or {}).get('n') or 0)

    cur.execute(
        "SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
        "AND TABLE_COLLATION NOT LIKE 'utf8mb4%%' ORDER BY TABLE_NAME", (schema,))
    bad_tables = cur.fetchall()

    cur.execute(
        "SELECT TABLE_NAME, COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND CHARACTER_SET_NAME IS NOT NULL "
        "AND CHARACTER_SET_NAME <> 'utf8mb4' ORDER BY TABLE_NAME, COLUMN_NAME", (schema,))
    bad_cols = cur.fetchall()
    db.close()

    print('当前库      : %s（基表 %d 张）' % (schema, n_tables))
    print('表级非 utf8mb4 : %d 张' % len(bad_tables))
    for t in bad_tables[:15]:
        print('   %-32s %s' % (t['TABLE_NAME'], t['TABLE_COLLATION']))
    print('列级非 utf8mb4 : %d 列' % len(bad_cols))
    by_table = {}
    for c in bad_cols:
        by_table.setdefault(c['TABLE_NAME'], []).append(c)
    for tbl, cols in list(by_table.items())[:15]:
        names = ', '.join('%s(%s)' % (x['COLUMN_NAME'], x['CHARACTER_SET_NAME']) for x in cols[:4])
        print('   %-28s %s' % (tbl, names + (' ...' if len(cols) > 4 else '')))

    print('\n=== 结论 ===')
    if not bad_tables and not bad_cols:
        print('  [OK] 全库表与列均为 utf8mb4，emoji 不会再被截成 ?')
        return 0
    print('  [X] 存在会被截断 4 字节字符的表/列，修复 SQL（逐表执行，会重建表，请挑窗口）：')
    seen = set()
    for t in bad_tables:
        seen.add(t['TABLE_NAME'])
    for c in bad_cols:
        seen.add(c['TABLE_NAME'])
    for tbl in sorted(seen):
        print("      ALTER TABLE `%s` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;" % tbl)
    print('  （本脚本不擅自执行：ALTER ... CONVERT 重建整表，需人工确认备份后再做）')
    return 1


if __name__ == '__main__':
    sys.exit(main())
