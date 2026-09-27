# -*- coding: utf-8 -*-
"""遍历 app.url_map 的**全部 GET 路由**逐条真实调用，只报 5xx（未处理异常）。

    python scripts/maintenance/check_routes_5xx.py [--methods GET] [--include-write]
        [--base http://localhost:5000] [--verbose]

默认用 test_client 在进程内扫（扫的是磁盘上的当前代码）；给了 --base 就打**真实 HTTP**，
用来确认“跑着的这个进程”确实加载了修复（本项目的修复不改完重启看不到，FLASK_DEBUG=0）。

为什么常驻：本项目反复出现“路由函数从来没被调用过就一直不报错，第一次真实调用即 500”
的缺陷（NameError / AttributeError / 死引用 / pymysql 的 % 未转义）。单测覆盖不到它们，
浏览器手点更覆盖不全 —— 2026-09 这一轮就是这样抓到两个真 500：
  * routes/workflow_monitor.py 把 MySQL 的 '%Y-%m-%d %H:00' 拼进带参数的 SQL，
    pymysql 先做 % 格式化 → ValueError: unsupported format character 'Y'（监控页执行趋势永远空）
  * 5 个路由模块共 15 处读 request.user_id —— Flask 的 Request 根本没有这个属性
    （身份在 request.user['user_id']），插件市场 / Agent 模板列表一调用就 AttributeError。

安全边界：默认**只打 GET**（GET 在本项目里都是读接口），并且跳过下载/导出/流式这类
会产生外部副作用或超大响应的路由。要连写接口一起扫需显式加 --include-write，
它会用占位 body 打 POST/PUT/DELETE —— 那会真的写库，只应在本地测试库上用。
"""
import argparse
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from app import app  # noqa: E402
from config import get_db  # noqa: E402
from utils.auth import generate_access_token, get_account_role  # noqa: E402

UUID = '00000000-0000-4000-8000-000000000000'
# 这些路由要么产生外部副作用，要么响应是文件流，扫它们没有意义
SKIP_WORDS = ('download', 'export', 'stream', '/file', '/proxy')


def _one(cur, sql):
    """取一个占位主键；列名猜错不能把整个扫描弄挂。"""
    try:
        cur.execute(sql)
        return cur.fetchone()
    except Exception as e:
        print('  [!] 占位查询失败（不阻断扫描）: %s' % str(e)[:90])
        return None


def build_samples():
    db = get_db()
    try:
        cur = db.cursor()
        acc = _one(cur, r"SELECT id, name, email FROM dify_accounts WHERE status = 'active' "
                        r"ORDER BY created_at LIMIT 1")
        agent = _one(cur, r'SELECT id FROM agents LIMIT 1')
        dify_app = _one(cur, r'SELECT id FROM dify_apps LIMIT 1')
        dataset = _one(cur, r'SELECT id FROM dify_datasets LIMIT 1')
        conv = _one(cur, r'SELECT id FROM dify_conversations LIMIT 1')
    finally:
        db.close()
    if not acc:
        return None, {}
    samples = {
        'agent_id': str((agent or {}).get('id') or 1),
        'aid': str((agent or {}).get('id') or 1),
        'app_id': str((dify_app or {}).get('id') or UUID),
        'appid': str((dify_app or {}).get('id') or UUID),
        'dataset_id': str((dataset or {}).get('id') or UUID),
        'conversation_id': str((conv or {}).get('id') or UUID),
    }
    return acc, samples


def fill(rule, samples):
    def rep(m):
        inner = m.group(1)
        parts = re.split(r'[:!]', inner)
        # <id> 这种不写转换器名的也要能吃
        name = parts[-1] if len(parts) > 1 else parts[0]
        if name in samples:
            return samples[name]
        return '1' if inner.startswith('int') else UUID
    return re.sub(r'<([^>]+)>', rep, rule)


def http_call(base, url, method, headers):
    """对跑着的服务打真实请求（只读，不带 body）"""
    req = urllib.request.Request(base + url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode('utf-8', 'ignore')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'ignore')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--methods', default='GET', help='逗号分隔，如 GET 或 GET,POST')
    ap.add_argument('--include-write', action='store_true',
                    help='连 POST/PUT/DELETE 一起打（会真写库，只在本地测试库用）')
    ap.add_argument('--base', default='', help='对运行中的后端打真实 HTTP，如 http://localhost:5000')
    ap.add_argument('--verbose', action='store_true', help='逐条打印状态码')
    args = ap.parse_args()
    methods = [m.strip().upper() for m in args.methods.split(',') if m.strip()]
    if args.include_write:
        methods = sorted(set(methods + ['POST', 'PUT', 'DELETE']))
    base = (args.base or '').rstrip('/')

    # 本脚本测的是“装载后的真实行为”，闸门按 .env 的配置生效即可
    acc, samples = build_samples()
    if acc is None:
        print('[X] 库里没有可用账号，无法签发令牌')
        return 2
    tok = generate_access_token(str(acc['id']), acc['email'] or '', acc['name'],
                                get_account_role(str(acc['id']))['level'])
    client = app.test_client()
    headers = {'Authorization': 'Bearer ' + tok}
    if base:
        # 先确认服务在：否则 195 条全部“连不上”会被当成 0 个故障结过去
        try:
            code, _ = http_call(base, '/api/health', 'GET', headers)
        except Exception as e:
            print('[X] 目标不可达 %s：%s' % (base, str(e)[:120]))
            return 2
        if code != 200:
            print('[X] %s/api/health 返回 %s，不继续扫' % (base, code))
            return 2
        print('目标服务：%s（/api/health 200）' % base)

    plan = []
    for r in app.url_map.iter_rules():
        allow = set(r.methods or ()) & set(methods)
        rule = str(r.rule)
        if not allow or not (rule.startswith('/api/') or rule.startswith('/v1/')):
            continue
        if any(w in rule.lower() for w in SKIP_WORDS):
            continue
        plan.append((sorted(allow)[0], rule))
    plan.sort(key=lambda x: x[1])
    print('共 %d 条路由待打（方法集合=%s，%s）'
          % (len(plan), ','.join(methods), ('真实 HTTP ' + base) if base else '进程内 test_client'))

    bad = []
    verbose_on = args.verbose
    for method, rule in plan:
        url = fill(rule, samples)
        try:
            if base:
                code, body = http_call(base, url, method, headers)
            else:
                resp = client.open(url, method=method, headers=headers,
                                   json={} if method in ('POST', 'PUT') else None)
                code = resp.status_code
                body = (resp.get_data(as_text=True) or '') if code >= 500 else ''
        except Exception as e:
            code, body = -1, '%s: %s' % (type(e).__name__, str(e)[:200])
        if verbose_on:
            print('  %-6s %-56s %s' % (method, url, code))
        if code == -1 or code >= 500:
            bad.append((method, url, code, (body or '')[:200].replace('\n', ' ')))

    print('\n=== 5xx / 未处理异常：%d 条 ===' % len(bad))
    for method, url, code, detail in bad:
        print('  [X] %-6s %-52s %s %s' % (method, url, code, detail[:150]))
    if not bad:
        print('  [OK] 全部路由均无未处理异常')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
