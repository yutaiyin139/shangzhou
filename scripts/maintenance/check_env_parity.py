# -*- coding: utf-8 -*-
"""环境变量模板完整性检查：代码里读了的键，必须都登记在 .env.example。

为什么常驻：项目部署时生产 .env 是由 scripts/deploy-ubuntu.sh 现场生成的，
不是从 .env.example 复制的。任何"只在代码里读、模板和生成脚本都没写"的键，
都会在新部署上静默取到缺省值 —— 而 REQUIRE_LOGIN_FOR_API 的缺省值是 off（免登录）。
这类缺口只有把三方对齐比对才看得见，所以做成检查而不是靠人记。

    python scripts/maintenance/check_env_parity.py

退出码 0 = 三方一致；1 = 有键缺登记（会列出具体键与读取位置）。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')

READ_RX = re.compile(r"""(?:os\.environ\.get|os\.getenv)\(\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]""")
SUBRX_READ = re.compile(r"""os\.environ\[\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]""")
# deploy-ubuntu.sh 的 heredoc 里形如 KEY=value 的行（忽略 ${} 变量值）
DEPLOY_KEY_RX = re.compile(r'^([A-Z][A-Z0-9_]{2,})=', re.M)

SKIP_DIRS = {'venv_libs', '__pycache__', '.pytest_cache', 'logs', 'cache', 'data'}


def keys_read_by_code():
    """返回 {KEY: 第一个读它的文件:行}。"""
    found = {}
    for dirpath, dirnames, filenames in os.walk(BACKEND):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith('.py'):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding='utf-8') as fh:
                    lines = fh.readlines()
            except (UnicodeDecodeError, OSError):
                continue
            rel = os.path.relpath(path, BACKEND).replace('\\', '/')
            for no, line in enumerate(lines, 1):
                for rx in (READ_RX, SUBRX_READ):
                    for m in rx.finditer(line):
                        found.setdefault(m.group(1), '%s:%d' % (rel, no))
    return found


def keys_in_file(path, pattern):
    if not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8', errors='ignore') as fh:
        text = fh.read()
    return set(m.group(1) for m in pattern.finditer(text))


def main():
    strict = '--strict' in sys.argv
    code_keys = keys_read_by_code()
    example = keys_in_file(os.path.join(ROOT, '.env.example'), DEPLOY_KEY_RX)
    deploy = keys_in_file(os.path.join(ROOT, 'scripts', 'deploy-ubuntu.sh'), DEPLOY_KEY_RX)

    # 前端只把 VITE_ 前缀打进包里，另行核对
    front_dir = os.path.join(ROOT, 'front', 'src')
    front_keys = set()
    for dirpath, _dn, filenames in os.walk(front_dir):
        for fn in filenames:
            if fn.endswith(('.vue', '.ts', '.js')):
                try:
                    with open(os.path.join(dirpath, fn), encoding='utf-8') as fh:
                        text = fh.read()
                except (UnicodeDecodeError, OSError):
                    continue
                front_keys.update(re.findall(r'import\.meta\.env\.([A-Z][A-Z0-9_]+)', text))

    print('代码读取键 %d 个（后端）+ %d 个（前端 VITE_）' % (len(code_keys), len(front_keys)))
    print('.env.example 登记 %d 个；deploy-ubuntu.sh 生成 %d 个' % (len(example), len(deploy)))

    missing_example = sorted((set(code_keys) | front_keys) - example)
    print('\n--- .env.example 未登记 ---')
    for k in missing_example:
        print('   %-32s 读取处 %s' % (k, code_keys.get(k, 'front/src')))
    if not missing_example:
        print('   (无)')

    # 安全相关的键必须同时出现在部署脚本里：那里才是生产真正读到的地方
    SECURITY_KEYS = ('REQUIRE_LOGIN_FOR_API', 'OWNERSHIP_CHECK_MODE',
                     'LOGIN_LOCKOUT_ENABLED', 'VITE_LOGIN_CAPTCHA')
    print('\n--- 安全开关是否随部署脚本落地 ---')
    bad = []
    for k in SECURITY_KEYS:
        in_dep = k in deploy
        print('   %-24s .env.example=%-5s deploy-ubuntu.sh=%s'
              % (k, k in example, in_dep))
        if not in_dep:
            bad.append(k)

    print('\n=== 结论 ===')
    problems = []
    if missing_example:
        problems.append('%d 个代码读取键未登记进 .env.example' % len(missing_example))
    if bad:
        problems.append('安全开关未写进部署生成的 .env，新服务器会取到缺省值：%s' % ', '.join(bad))
    if problems:
        for p in problems:
            print('  [X] ' + p)
        if not strict:
            print('  （默认只报告不失败；加 --strict 可作为发布门禁）')
        return 0 if not strict else 1
    print('  [OK] 代码读取键、模板、部署脚本三方一致')
    return 0


if __name__ == '__main__':
    sys.exit(main())
