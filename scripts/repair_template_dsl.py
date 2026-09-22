# -*- coding: utf-8 -*-
"""一次性修复 app_templates.dsl_yaml 中被 MySQL 字符集破坏成 '?' 的 emoji 脏数据。

来源优先级：本地缓存文件 backend/cache/templates/<id>/dsl.yaml -> 重新下载 Marketplace DSL。
用法：python scripts/repair_template_dsl.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(os.path.dirname(HERE), 'backend')
sys.path.insert(0, BACKEND)

import yaml  # noqa: E402
from config import get_db  # noqa: E402

CACHE_DIR = os.path.join(BACKEND, 'cache', 'templates')


def parses(text):
    if not text:
        return False
    try:
        return isinstance(yaml.safe_load(text), dict)
    except Exception:
        return False


def download(tid):
    """复用路由里的下载逻辑"""
    from routes.app_templates import _download_dsl_with_retry
    return _download_dsl_with_retry(tid)


def main():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT marketplace_id, name, dsl_yaml FROM app_templates WHERE status = %s', ('active',))
        rows = cur.fetchall()
        fixed, still_bad, total = 0, [], len(rows)
        for r in rows:
            tid = r['marketplace_id']
            if parses(r['dsl_yaml']):
                continue
            good = None
            capath = os.path.join(CACHE_DIR, tid, 'dsl.yaml')
            if os.path.exists(capath):
                try:
                    with open(capath, 'r', encoding='utf-8') as f:
                        c = f.read()
                    if parses(c):
                        good = c
                except Exception:
                    pass
            if good is None and os.getenv('REPAIR_ALLOW_DOWNLOAD') == '1':
                try:
                    c = download(tid)
                    if parses(c):
                        good = c
                except Exception:
                    good = None
            if good is None:
                still_bad.append((tid, r['name']))
                continue
            cur.execute('UPDATE app_templates SET dsl_yaml = %s WHERE marketplace_id = %s', (good, tid))
            fixed += 1
            print('FIXED', tid, repr(r['name']))
        db.commit()
    finally:
        db.close()
    print('\n== total active: %d, fixed: %d, still-bad: %d ==' % (total, fixed, len(still_bad)))
    for tid, name in still_bad:
        print('  STILL BAD', tid, repr(name), '(缓存缺失且下载失败，创建时将自动再回退)')


if __name__ == '__main__':
    main()
