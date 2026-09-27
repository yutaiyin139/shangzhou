# -*- coding: utf-8 -*-
"""用「普通用户」的真实令牌扫一遍疑似管理面的 GET 接口，看还有多少人人都能读。

    python scripts/maintenance/check_admin_surface_exposure.py [--base http://localhost:5000]

来历：集中式闸门（utils/api_guard.py）只保证「必须登录」，不保证「必须是管理员」。
实测普通用户能直接 GET /api/users 拿到全体账号的邮箱与手机号，而配套的
POST /api/users、PUT /api/users/<id>、PUT /api/roles/<id>/permissions 一度也全开着 ——
建一个 role=admin 的号、改任何人密码、给自己加权，一条路就能走完提权。
用户/角色那组已在 routes/auth.py 用 platform_admin_required 收紧，本脚本负责盯住
「以后新增的管理面接口忘了加守卫」。

判定分两档：
  HARD —— 明确只该管理员能用，普通用户读到就算 [X]（退出码 1）
  SOFT —— 全平台可观测数据（审计/监控/任务/统计），是否该收归管理员还没定论，
          只列出来给人判断，不影响退出码
不写任何数据：只发 GET。
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from config import get_db  # noqa: E402
from utils.auth import generate_access_token, get_account_role  # noqa: E402

# 关键词命中 = 疑似管理面；再按下面两档分类
ADMIN_WORDS = ('backup', 'cache', 'user', 'role', 'permission', 'system', 'audit',
               'admin', 'statistic', 'stats', 'overview', 'dashboard', 'monitor',
               'task', 'worker', 'queue', 'encrypt', 'secret')
# 业务面（人人可用），命中即从疑似管理面里剔掉
BUSINESS_WORDS = ('/api/agents', '/api/multi-agent', '/api/datasets', '/api/workflows',
                  '/api/tools', '/api/plugins', '/api/models', '/api/skills', '/api/account',
                  '/api/notifications', '/api/my-agents', '/api/app-templates', '/api/share',
                  '/api/conversation', '/api/messages', '/api/register-config', '/api/health',
                  '/api/ping', '/api/knowledge', '/api/stats/')
# HARD：必须管理员，普通用户读到就是缺陷。本脚本只扫 GET，所以这里只列“读本身就是隐私”的；
# /api/roles 与 /api/permissions 的 GET 是“角色/权限点清单”这类参考数据，用户管理页的
# 角色下拉要用，故意保留给登录用户（它们的**写**接口由
# backend/tests/test_account_identity_single_source.py::TestPlatformAdminSurface 钉住只能管理员）。
HARD_PREFIXES = ('/api/users', '/api/system/', '/api/cache/', '/api/backup')


def list_candidate_gets():
    import app as app_module
    rules = set()
    for r in app_module.app.url_map.iter_rules():
        rule = str(r.rule)
        if '<' in rule or 'GET' not in (r.methods or set()) or not rule.startswith('/api/'):
            continue
        low = rule.lower()
        if any(w in low for w in ADMIN_WORDS) and not any(b in rule.lower() for b in BUSINESS_WORDS):
            rules.add(rule)
    return sorted(rules)


def pick_plain_account():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r"SELECT id, name, email FROM dify_accounts WHERE status = 'active' "
                    r"ORDER BY created_at")
        rows = cur.fetchall()
    finally:
        db.close()
    for a in rows:
        if get_account_role(a['id'])['level'] != 'admin':
            return a
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://localhost:5000')
    args = ap.parse_args()
    base = args.base.rstrip('/')

    plain = pick_plain_account()
    if plain is None:
        print('[X] 库里没有非管理员账号，缺少对照组 —— 无法验证管理面边界')
        return 2
    tok = generate_access_token(str(plain['id']), plain['email'] or '', plain['name'], 'user')
    paths = list_candidate_gets()
    print('以普通用户 %s（库里角色 %s）扫描 %d 个疑似管理面 GET 接口 @ %s\n'
          % (plain['name'], get_account_role(str(plain['id']))['role_name'], len(paths), base))

    hard, soft = [], []
    for path in paths:
        req = urllib.request.Request(base + path,
                                     headers={'Authorization': 'Bearer ' + tok,
                                              'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                status, raw = resp.status, resp.read().decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            status, raw = e.code, ''
        except Exception as e:
            status, raw = 0, str(e)
        if status != 200:
            print('  %-46s 已拦 (%s)' % (path, status))
            continue
        body = {}
        try:
            body = json.loads(raw or '{}')
        except Exception:
            pass
        # 本项目用 HTTP 200 + body.code 承载业务错误，两个都要看
        if int(body.get('code') or 200) != 200:
            print('  %-46s 已拦 (body.code=%s)' % (path, body.get('code')))
            continue
        size = len(re.sub(r'\s', '', raw or ''))
        row = (path, size)
        (hard if path.startswith(HARD_PREFIXES) else soft).append(row)
        print('  %-46s 可读  %d 字节' % (path, size))

    print('\n=== 判定 ===')
    for p, s in hard:
        print('  [X] %s（%d 字节）普通用户不该读到，需要管理员守卫' % (p, s))
    if not hard:
        print('  [OK] 没有管理面接口（用户/系统设置/缓存/备份）向普通用户开放')
    for p, s in soft:
        print('  [?] %s（%d 字节）全平台可观测数据，是否收归管理员待产品定' % (p, s))
    if not soft:
        print('  [OK] 没有待定的可观测类接口')
    return 1 if hard else 0


if __name__ == '__main__':
    sys.exit(main())
