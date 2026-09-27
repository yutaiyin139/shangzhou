#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
熵舟·智能体工作台 —— 多机器部署地址一键迁移工具

与早期脚本 change_ip.py（仅作参考，已删除）的关键区别：旧实现会把 Redis/Celery 的
localhost 一起带走，按子串全文替换而误伤 nginx/gunicorn 的回环地址，且写文件时破坏
.bat 的 CRLF（它登记的 12 个路径中 11 个已随 V1.0 前的 Dify/nginx 架构失效）：

  1. 只改「已登记的配置点」，不全文盲替换；每处都带角色语义（db/app/deploy/...）。
  2. 回环与本机基础设施地址结构性受保护：不显式点名就永不改动。
  3. 字节级按行改写，完整保留各文件原有换行符（.bat=CRLF、.sh=LF）与编码。
  4. 默认只预览；加 --apply 才落盘；自动备份，可 --restore 回滚。
  5. 改完可选 --probe 实测连通性，并识别目标 IP 是否属于动态虚拟网卡。

用法示例:
  python set_ip.py --show                              # 查看当前地址分布（不改任何东西）
  python set_ip.py 192.168.1.20 --dry-run              # 预览：所有非回环旧地址 → 新地址
  python set_ip.py 192.168.1.20 --apply                # 实际执行
  python set_ip.py 172.28.240.1 --old-ip 10.38.3.14    # 只迁移指定旧地址（旧版 CLI 兼容）
  python set_ip.py 10.0.5.9 --role db,deploy --apply   # 只改数据库与部署目标
  python set_ip.py 192.168.1.20 --from localhost --role backend   # 前端指向远程后端
  python set_ip.py --restore                           # 回滚到最近一次备份
"""

import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKUP_ROOT = os.path.join(PROJECT_ROOT, 'logs', 'set_ip_backup')

IP_RE = re.compile(
    r'(?<![.\d])'
    r'(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)'
    r'(?![.\d])')

# 这些地址不是「部署地址」，永远不能作为迁移目标，也不在自动检测范围内
RESERVED = {'0.0.0.0', '127.0.0.1', '255.255.255.255', '::'}
LOCALHOST = 'localhost'

ROLES = {
    'db':      'MySQL 服务器地址（应用连库用）',
    'app':     '平台对外访问地址（浏览器/OAuth 回调/e2e 基址）',
    'deploy':  'Ubuntu 部署目标机（SSH 与文档示例中的服务器 IP）',
    'backend': '后端服务地址（前端 dev 代理、测试脚本直连）',
    'storage': 'MinIO 对象存储地址（仅 STORAGE_TYPE=minio 时生效）',
    'redis':   'Redis / Celery broker 地址（Windows 本机开发必须保持 localhost）',
}
# 默认参与的迁移：redis 需显式点名，backend 需显式点名 --from localhost 才会真的动
DEFAULT_ROLES = ['db', 'app', 'deploy', 'storage', 'backend']

# ---------------------------------------------------------------------------
# 配置点登记表：role / 文件 / 定位当前地址的正则（host 命名组）/ 人类可读说明
# ---------------------------------------------------------------------------
SITES = [
    ('db',      '.env',                             r'^\s*DB_HOST=(?P<host>[^\s#]+)', 'DB_HOST'),
    ('db',      'scripts/deploy-ubuntu-online.sh',  r'DB_HOST="\$\{DB_HOST:-(?P<host>[^}"]+)\}"', '部署脚本 DB_HOST 默认值'),
    ('app',     '.env',                             r'^\s*APP_BASE_URL=https?://(?P<host>[^:/\s#]+)', 'APP_BASE_URL'),
    ('app',     '.env',                             r'^\s*SHANGZHOU_TEST_BASE_URL=https?://(?P<host>[^:/\s#]+)', 'SHANGZHOU_TEST_BASE_URL'),
    ('storage', '.env',                             r'^\s*MINIO_ENDPOINT=(?P<host>[^:/\s#]+)', 'MINIO_ENDPOINT'),
    ('redis',   '.env',                             r'^\s*REDIS_HOST=(?P<host>[^\s#]+)', 'REDIS_HOST'),
    ('redis',   '.env',                             r'^\s*CELERY_BROKER_URL=redis://(?P<host>[^:/\s#]+)', 'CELERY_BROKER_URL'),
    ('redis',   '.env',                             r'^\s*CELERY_RESULT_BACKEND=redis://(?P<host>[^:/\s#]+)', 'CELERY_RESULT_BACKEND'),
    ('deploy',  'scripts/deploy_ubuntu_online.py',  r'SZ_HOST",\s*"(?P<host>[^"]+)"', '在线部署驱动 SZ_HOST 默认值'),
    ('deploy',  'README.md',                        r'SZ_HOST="(?P<host>[^"]+)"', 'README 部署示例'),
    ('deploy',  os.path.join('docs', '生产环境部署手册-V1.0.md'), r'SZ_HOST="(?P<host>[^"]+)"', '部署手册示例'),
    ('backend', os.path.join('front', 'vite.config.ts'), r"target:\s*'https?://(?P<host>[^:/']+)", '前端 dev /api 代理目标'),
]
# 测试脚本：默认不动，--include-tests 才纳入
TEST_GLOBS = [('backend', 'backend/tests/e2e_*.py', r"BASE(?:_URL)?\s*=\s*'https?://(?P<host>[^:/']+)", 'e2e 测试基址'),
              ('backend', 'backend/tests/e2e_*.py', r"getenv\('SHANGZHOU_TEST_BASE_URL',\s*'https?://(?P<host>[^:/']+)", 'e2e 测试基址默认值')]

# 模板类文件：机器专属地址不应进入 .env.example
TEMPLATE_FILES = ('.env.example',)


def valid_address(s):
    """合法地址 = 严格四段 IPv4，或含字母的 DNS 主机名。

    刻意不用“允许 1.2.3.4.5 这种数字+点串当主机名”的宽松写法：
    那会让畸形 IP 静默通过校验。
    """
    if IP_RE.match(s) and re.match(r'^(?:\d{1,3}\.){3}\d{1,3}$', s):
        return True
    if re.match(r'^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$', s):
        return any(ch.isalpha() for ch in s)
    return False


def color(text, c=''):
    palette = {'red': '91', 'green': '92', 'yellow': '93', 'cyan': '96', 'bold': '1', 'dim': '2'}
    if os.name == 'nt':
        os.system('')  # 启用 ANSI
    return '%s%s%s' % ('\033[%sm' % palette[c] if c else '', text, '\033[0m' if c else '')


def info(msg):
    print(color('  ' + msg, 'cyan'))


def warn(msg):
    print(color('  [警告] ' + msg, 'yellow'))


def read_lines(path):
    """按行返回原始文本，保留行尾（CRLF/LF 不被动）。"""
    with io.open(path, 'r', encoding='utf-8', errors='surrogateescape', newline='') as f:
        return f.read().splitlines(keepends=True)


def write_lines(path, lines):
    with io.open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(''.join(lines))


def resolve_files(spec):
    """配置点里的文件可以是路径或 glob。"""
    if any(ch in spec for ch in '*?['):
        return sorted(os.path.relpath(p, PROJECT_ROOT).replace(os.sep, '/')
                      for p in glob.glob(os.path.join(PROJECT_ROOT, spec)))
    return [spec.replace(os.sep, '/')]


def all_sites(include_tests=False, include_template=False):
    out = list(SITES)
    if include_tests:
        out.extend(TEST_GLOBS)
    if not include_template:
        pass  # .env.example 从未登记，天然排除
    return out


def scan(roles, include_tests=False):
    """返回每个配置点的当前地址：[{role,file,line,host,note,lineno}]"""
    hits = []
    for role, spec, pattern, note in all_sites(include_tests):
        if role not in roles:
            continue
        for rel in resolve_files(spec):
            if rel in TEMPLATE_FILES:
                continue
            abspath = os.path.join(PROJECT_ROOT, rel)
            if not os.path.isfile(abspath):
                hits.append({'role': role, 'file': rel, 'host': None,
                             'missing': True, 'note': note})
                continue
            rx = re.compile(pattern)
            for lineno, line in enumerate(read_lines(abspath), 1):
                m = rx.search(line.rstrip('\r\n'))
                if m and 'host' in m.groupdict():
                    hits.append({'role': role, 'file': rel, 'lineno': lineno,
                                 'host': m.group('host'), 'line': line.rstrip('\r\n').strip(),
                                 'note': note, 'pattern': pattern})
    return hits


def print_map(hits):
    print(color('\n当前地址分布（按角色）', 'bold'))
    cur_role = None
    for h in hits:
        if h.get('missing'):
            print(color('  %-8s %-38s 文件不存在（该配置点已失效）' % (h['role'], h['file']), 'dim'))
            continue
        if h['role'] != cur_role:
            cur_role = h['role']
            print(color('  ── %s：%s' % (cur_role, ROLES.get(cur_role, '')), 'bold'))
        host = h['host']
        tag = ''
        if host in RESERVED or host == LOCALHOST:
            tag = color('  ← 回环/本机，默认不动', 'dim')
        print('     %-36s L%-5s %-22s %s%s' % (h['file'], h['lineno'], host, h['note'], tag))


def adapter_of(ip):
    """查询该 IP 属于本机哪个网卡，用于识别动态虚拟网卡地址。"""
    if os.name != 'nt':
        return None
    ps = ("Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -eq '%s'} "
          "| ForEach-Object {\"$($_.InterfaceAlias)\"}" % ip)
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                           capture_output=True, text=True, timeout=30)
        return (r.stdout or '').strip() or None
    except Exception:
        return None


def plan(hits, new_addr, old_addr, roles, explicit_from):
    """决定要改哪些点。"""
    changes, skipped = [], []
    for h in hits:
        if h.get('missing') or h['role'] not in roles:
            continue
        cur = h['host']
        if cur == new_addr:
            continue
        is_loop = cur in RESERVED or cur == LOCALHOST
        if explicit_from:
            if cur != old_addr:
                continue
        else:
            if is_loop:
                skipped.append((h, '回环/本机地址未点名（需要 --from %s）' % cur))
                continue
            if old_addr and cur != old_addr:
                continue
        changes.append({'site': h, 'from': cur, 'to': new_addr})
    return changes, skipped


def do_changes(changes, apply=False, backup_dir=None):
    """按文件分组落盘；只替换命中行的 host 子串，保留行尾与编码。"""
    by_file = {}
    for c in changes:
        by_file.setdefault(c['site']['file'], []).append(c)
    touched = 0
    for rel, items in by_file.items():
        abspath = os.path.join(PROJECT_ROOT, rel)
        lines = read_lines(abspath)
        changed = 0
        for c in items:
            idx = c['site']['lineno'] - 1
            old_line = lines[idx]
            tail = ''
            body = old_line
            while body and body[-1] in '\r\n':
                tail = body[-1] + tail
                body = body[:-1]
            if c['from'] not in body:
                continue
            rx = re.compile(c['site']['pattern'])
            m = rx.search(body)
            if not m or 'host' not in m.groupdict() or m.group('host') != c['from']:
                continue
            s, e = m.span('host')
            new_body = body[:s] + c['to'] + body[e:]
            if new_body != body:
                lines[idx] = new_body + tail
                changed += 1
        if changed and apply:
            if backup_dir:
                dst = os.path.join(backup_dir, rel.replace('/', os.sep))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(abspath, dst)
            write_lines(abspath, lines)
        touched += changed
    return touched


def _probe_one(host, port, kind, path='/'):
    """按协议真实握手。仅看 TCP 端口会误判：Redis 对非回环地址是先接受再重置。"""
    import socket
    import urllib.error
    import urllib.request
    s = socket.socket()
    s.settimeout(2.5)
    try:
        if s.connect_ex((host, port)) != 0:
            return 'fail', '端口不通'
    except Exception as e:
        return 'fail', '端口不通(%s)' % str(e)[:20]
    try:
        if kind == 'redis':
            s.sendall(b'PING\r\n')
            data = s.recv(256)
            if data.startswith(b'+PONG'):
                return 'ok', 'Redis PING 应答正常'
            if b'-DENIED' in data or b'protected-mode' in data:
                return 'fail', '服务端主动拒绝：protected-mode 只信任回环（需改为加载 redis.conf 并设 bind + requirepass）'
            return 'warn', '端口开但 PING 无正常应答：%r' % data[:24]
        if kind == 'mysql':
            data = s.recv(8)
            if data and len(data) >= 5:
                return 'ok', 'MySQL 握手包正常'
            return 'warn', '端口开但无 MySQL 握手包'
        s.close()
        url = 'http://%s:%d%s' % (host, port, path)
        try:
            with urllib.request.urlopen(url, timeout=4) as resp:
                return 'ok', 'HTTP %s' % resp.status
        except urllib.error.HTTPError as e:
            return 'ok', 'HTTP %s（服务在跑）' % e.code
    except ConnectionResetError:
        return 'fail', '连接被对端强制重置（该服务很可能只信任回环地址 / protected-mode）'
    except socket.timeout:
        return 'warn', '已连接但无应答（超时）'
    except Exception as e:
        return 'warn', '端口开，协议层异常：%s' % str(e)[:40]
    finally:
        try:
            s.close()
        except Exception:
            pass


def probe(new_addr):
    """实测新机地址上关键服务是否真的可用（不只是端口开）。"""
    checks = [('MySQL', new_addr, 3306, 'mysql', '/'),
              ('后端 :5000', new_addr, 5000, 'http', '/api/health'),
              ('前端 dev :5173', new_addr, 5173, 'http', '/'),
              ('Redis', new_addr, 6379, 'redis', '/')]
    print(color('\n连通性实测（按协议握手，不只看端口）%s' % new_addr, 'bold'))
    for label, host, port, kind, path in checks:
        state, detail = _probe_one(host, port, kind, path)
        c = {'ok': 'green', 'warn': 'yellow', 'fail': 'red'}[state]
        print('     %-18s %-24s %s' % (label, '%s:%d' % (host, port), color(detail, c)))
    print(color('     说明：Redis 显示“被强制重置”属正常——Windows 本机开发它只信任回环，'
                '不要为此把 REDIS_HOST 改成局域网地址。', 'dim'))


def ask_yes(prompt, assume_yes=False):
    if assume_yes or not sys.stdin or not hasattr(sys.stdin, 'isatty') or not sys.stdin.isatty():
        return assume_yes
    try:
        return input(prompt).strip().lower() in ('y', 'yes')
    except Exception:
        return False


def restore(ts=None):
    if not os.path.isdir(BACKUP_ROOT):
        print(color('  没有备份记录，无法回滚。', 'yellow'))
        return 1
    versions = sorted(os.listdir(BACKUP_ROOT))
    chosen = ts or versions[-1]
    src = os.path.join(BACKUP_ROOT, chosen)
    if not os.path.isdir(src):
        print(color('  找不到备份版本 %s；可用版本：%s' % (chosen, ', '.join(versions)), 'yellow'))
        return 1
    n = 0
    for root, _dirs, files in os.walk(src):
        for f in files:
            if f == 'manifest.json':      # 记录文件不是被改配置，不能回写项目根
                continue
            sp = os.path.join(root, f)
            rel = os.path.relpath(sp, src)
            dp = os.path.join(PROJECT_ROOT, rel)
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            shutil.copy2(sp, dp)
            n += 1
    print(color('  已从 %s 恢复 %d 个文件。' % (chosen, n), 'green'))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description='熵舟多机器部署：配置文件与源码中的地址一键迁移',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument('new_ip', nargs='?', help='新地址（IP 或主机名）')
    ap.add_argument('--from', dest='from_addr', help='只迁移这个旧地址（含 localhost 需显式点名）')
    ap.add_argument('--old-ip', dest='old_ip', help='同 --from（兼容旧版 CLI）')
    ap.add_argument('--role', default='', help='逗号分隔：%s' % ','.join(ROLES))
    ap.add_argument('--apply', action='store_true', help='真正写入（默认只预览）')
    ap.add_argument('--dry-run', action='store_true', help='仅预览（默认行为）')
    ap.add_argument('-y', '--yes', action='store_true', help='跳过确认')
    ap.add_argument('--show', action='store_true', help='只打印当前地址分布')
    ap.add_argument('--probe', action='store_true', help='改完后实测端口连通性')
    ap.add_argument('--include-tests', action='store_true', help='一并修改 backend/tests/e2e_*')
    ap.add_argument('--allow-local-infra', action='store_true',
                    help='允许把 Redis/Celery 指向非回环地址（Windows 上会 10054）')
    ap.add_argument('--restore', nargs='?', const='', default=None, metavar='TS',
                    help='回滚：不带参数恢复最近一次备份')
    args = ap.parse_args()

    if args.restore is not None:
        return restore(args.restore or None)

    roles = [r.strip() for r in args.role.split(',') if r.strip()] or list(DEFAULT_ROLES)
    bad = [r for r in roles if r not in ROLES]
    if bad:
        print(color('  未知角色 %s；可选：%s' % (bad, ', '.join(ROLES)), 'red'))
        return 2

    hits = scan(roles + ['redis', 'backend'] if args.show else roles, include_tests=args.include_tests)
    if args.show:
        print_map(scan(list(ROLES), include_tests=True))
        print(color('\n  提示：Redis/Celery 在 Windows 本机开发必须保持 localhost；'
                    'nginx/gunicorn/redis bind 等回环地址不在本工具管辖范围。', 'dim'))
        return 0

    if not args.new_ip:
        print(color('  需要新地址，或改用 --show / --restore。', 'red'))
        return 2
    new_addr = args.new_ip.strip()
    if not valid_address(new_addr):
        print(color('  地址格式不合法：%s（需为四段 IPv4 或含字母的主机名）' % new_addr, 'red'))
        return 2
    if new_addr in RESERVED:
        print(color('  %s 是保留地址，不能作为部署地址。' % new_addr, 'red'))
        return 2

    old_addr = args.from_addr or args.old_ip
    explicit = bool(old_addr)
    if explicit and old_addr not in RESERVED and old_addr != LOCALHOST and not IP_RE.match(old_addr):
        print(color('  旧地址格式不合法：%s' % old_addr, 'red'))
        return 2

    print(color('\n目标地址：%s' % new_addr, 'bold'))
    print(color('参与角色：%s' % ', '.join('%s(%s)' % (r, ROLES[r].split('（')[0]) for r in roles), 'dim'))

    if 'redis' in roles and not args.allow_local_infra:
        warn('Redis/Celery 已被点名。实测 Windows 本机把 REDIS_HOST/CELERY_* 指向任何本机 LAN IP '
             '都会刚连接就被重置（Winsock 10054，因为 redis-server 未加载 conf、只信任回环）。'
             '确认要改请加 --allow-local-infra。')
        roles = [r for r in roles if r != 'redis']
        hits = scan(roles, include_tests=args.include_tests)

    changes, skipped = plan(hits, new_addr, old_addr, roles, explicit)

    print(color('\n将修改 %d 处：' % len(changes), 'bold'))
    for c in changes:
        s = c['site']
        print('     %-36s L%-5s %-18s %s → %s' % (s['file'], s['lineno'], s['note'],
                                                  color(c['from'], 'yellow'), color(c['to'], 'green')))
    if skipped:
        print(color('\n按规则跳过 %d 处：' % len(skipped), 'dim'))
        for h, why in skipped:
            print(color('     %-36s L%-5s %-18s (%s) %s' % (h['file'], h['lineno'], h['note'], h['host'], why), 'dim'))
    if not changes:
        print(color('\n  没有需要修改的配置点（可能地址已是目标值，或旧地址未点名）。', 'yellow'))
        return 0

    adapter = adapter_of(new_addr)
    if adapter:
        line = '     新地址 %s 属于本机网卡「%s」' % (new_addr, adapter)
        if 'vEthernet' in adapter or 'Default Switch' in adapter:
            print(color(line + ' —— 虚拟交换机地址会被 Hyper-V/WSL 重新分配，不建议作为部署地址。', 'red'))
        else:
            print(color(line + '（DHCP 分配的话重连网络可能变化）。', 'cyan'))

    if not args.apply or args.dry_run:
        if args.probe:
            probe(new_addr)
        print(color('\n[预览模式] 未写入任何文件。确认无误后加 --apply 执行。', 'yellow'))
        return 0
    if not ask_yes('\n确认写入以上 %d 处修改？[y/N] ' % len(changes), args.yes):
        print(color('  已取消，未改动任何文件。', 'yellow'))
        return 0

    ts = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_dir = os.path.join(BACKUP_ROOT, ts)
    os.makedirs(backup_dir, exist_ok=True)
    n = do_changes(changes, apply=True, backup_dir=backup_dir)
    with io.open(os.path.join(backup_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump({'new_ip': new_addr, 'from': old_addr, 'roles': roles,
                   'changes': [{'file': c['site']['file'], 'line': c['site']['lineno'],
                                'note': c['site']['note'], 'from': c['from'], 'to': c['to']}
                               for c in changes]}, f, ensure_ascii=False, indent=2)
    print(color('\n  已修改 %d 处，%d 个文件；备份在 %s' % (n, len({c['site']['file'] for c in changes}),
                                                          os.path.relpath(backup_dir, PROJECT_ROOT)), 'green'))
    print(color('  需要回滚：python set_ip.py --restore %s' % ts, 'dim'))

    if args.probe:
        probe(new_addr)

    print(color('\n下一步（否则改动不生效）：', 'bold'))
    if os.name == 'nt':
        print('     1. 重启本机服务：  powershell -File .\\stop-services.ps1 ; powershell -File .\\start-services.ps1')
    else:
        print('     1. 重启服务：      bash scripts/szagent-ctl.sh restart all')
    print('     2. .env 是 gitignore 的机器专属文件；scripts/ 与 docs/ 的改动会进 git，请 review 后再提交')
    if any(c['site']['role'] == 'backend' for c in changes):
        print('     3. 前端代理目标变了：dev 需重启 vite；生产需重新 npm run build 产出 dist')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
