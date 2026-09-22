# -*- coding: utf-8 -*-
"""联网补齐 app_templates 中 DSL 为空/损坏的模板：
对每个问题模板从 Marketplace 下载 DSL -> 校验可解析 -> 写回数据库(列已 utf8mb4) + 本地缓存。
用法：python scripts/resync_empty_template_dsl.py [并发数，默认4]
"""
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(os.path.dirname(HERE), 'backend')
sys.path.insert(0, BACKEND)

import yaml  # noqa: E402
from config import get_db, MARKETPLACE_API_BASE  # noqa: E402

CACHE_DIR = os.path.join(BACKEND, 'cache', 'templates')
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4
TIMEOUT = 45


def parses(text):
    if not text:
        return False
    try:
        return isinstance(yaml.safe_load(text), dict)
    except Exception:
        return False


def download(tid):
    url = '%s/templates/%s/dsl' % (MARKETPLACE_API_BASE, tid)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/x-yaml'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.status != 200:
                return None
            return r.read().decode('utf-8', 'replace')
    except Exception:
        return None


def save(tid, dsl):
    # 写缓存文件（UTF-8 原样，含 emoji）
    try:
        d = os.path.join(CACHE_DIR, tid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'dsl.yaml'), 'w', encoding='utf-8') as f:
            f.write(dsl)
    except Exception:
        pass
    # 写数据库
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('UPDATE app_templates SET dsl_yaml=%s, dsl_path=%s WHERE marketplace_id=%s',
                    (dsl, 'cache/templates/%s/dsl.yaml' % tid, tid))
        db.commit()
    finally:
        db.close()


def work(tid):
    for attempt in range(2):
        dsl = download(tid)
        if parses(dsl):
            # 二次校验：确认 emoji 未被写坏（存回再读）
            save(tid, dsl)
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute('SELECT dsl_yaml FROM app_templates WHERE marketplace_id=%s', (tid,))
                back = cur.fetchone()['dsl_yaml']
            finally:
                db.close()
            if parses(back):
                return (tid, 'OK', len(back))
            return (tid, 'CORRUPT-AGAIN', 0)
        time.sleep(1)
    return (tid, 'FAILED', 0)


def main():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT marketplace_id, dsl_yaml FROM app_templates WHERE status=%s', ('active',))
    targets = [r['marketplace_id'] for r in cur.fetchall() if not parses(r['dsl_yaml'])]
    db.close()
    total = len(targets)
    print('待补齐模板数: %d, 并发: %d' % (total, WORKERS), flush=True)
    ok = fail = corrupt = done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, tid): tid for tid in targets}
        for fut in as_completed(futs):
            tid, status, size = fut.result()
            done += 1
            if status == 'OK':
                ok += 1
            elif status == 'CORRUPT-AGAIN':
                corrupt += 1
            else:
                fail += 1
            print('[%d/%d] %-10s %s (%d bytes)' % (done, total, status, tid[:8], size), flush=True)
    print('\n==== 补齐完成: 成功 %d, 下载失败 %d, 仍损坏 %d / 共 %d ====' % (ok, fail, corrupt, total), flush=True)


if __name__ == '__main__':
    main()
