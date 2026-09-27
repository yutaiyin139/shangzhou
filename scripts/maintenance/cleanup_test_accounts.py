# -*- coding: utf-8 -*-
"""清理 e2e / 安全探针留下的垃圾账号（默认 dry-run，不写库）。

来历一：backend/tests/e2e_*.py 里有的用例每次跑都会调 /api/register 建一个新账号
（注册会连带建租户与 join 记录），于是库里堆了一批 test_reg_* / test_dup_* / testuser*。
来历二：/api/users/<id> 垃圾不只有测试命名前缀。验证越权修复的探针会把
phone 改成 'IDOR-PROBE-9999'，还会建出 email 根本不是邮箱的账号（实测存在
email='yutaiyin' 而它是另一个账号的登录名）—— 这种脏数据会直接干扰登录
（`WHERE name = %s OR email = %s` 一个条件找两种输入）。它们都不命中 test* 前缀，
所以必须多一层“形状”判定。

护栏（任何一条不满足就直接跳过该账号，绝不误删真实用户）：
  1) 命中垃圾模式（名字/邮箱、非法邮箱格式、探针哨兵 phone）；
  2) 名下没有任何资源：agents.owner、dify_apps.created_by、dify_datasets.created_by 均为 0；
  3) 不是 dify_apps.created_by 统计出的主账号；
  4) 不在 --keep 列表里。

用法：
    python scripts/maintenance/cleanup_test_accounts.py            # 只看会删什么
    python scripts/maintenance/cleanup_test_accounts.py --apply    # 真删（单事务，失败回滚）
    python scripts/maintenance/cleanup_test_accounts.py --apply --keep yuty,yu
    python scripts/maintenance/cleanup_test_accounts.py --no-repair-orphans   # 不改无主应用归属
"""
import argparse
import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from config import get_db  # noqa: E402

# 哈希形状判定直接复用体检脚本里那份，不另抄一份：两处对“什么形状算能验”的理解
# 必须只有一个出处（argon2 原始 32 字节 / PBKDF2 hex 64 字节）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_password_hash import classify  # noqa: E402

NAME_PATTERNS = ('test%', 'e2e%', '%@test.com')   # 第三个匹配 email 列，前两个匹配 name

# “形状就不对”的一类：email 不是邮箱格式（收不到重置邮件，还会与别人的登录名撞车），
# 或 phone/name 带着越权探针的哨兵值。它们不命中上面的测试前缀，但不可能是真实账号。
JUNK_WHERE = (r'(email IS NULL OR email = %s OR email NOT LIKE %s '
              r'OR name LIKE %s OR phone LIKE %s)')
JUNK_PARAMS = ('', '%@%.%', 'IDOR-PROBE%', 'IDOR-PROBE%')


def _test_where():
    return 'name LIKE %s OR name LIKE %s OR email LIKE %s'


def _junk_params():
    return list(NAME_PATTERNS) + list(JUNK_PARAMS)


def _candidate_where():
    """一个 WHERE 片段：测试命名模式 OR 形状不对。与 _candidate_params() 配套使用。"""
    return '(' + _test_where() + ') OR ' + JUNK_WHERE


def _count_owned(cur, table, column, account_id):
    try:
        cur.execute('SELECT COUNT(1) AS n FROM `%s` WHERE `%s` = %%s' % (table, column),
                    (account_id,))
        return int((cur.fetchone() or {}).get('n') or 0)
    except Exception:
        # 表/列不存在时按 0 处理，但会打印一行提示，避免把"查不动"当成"没有资源"
        print('     (跳过检查 %s.%s：表或列不可用)' % (table, column))
        return 0


def _prune_orphan_tenants(cur, apply_changes):
    """清理孤立租户（没有任何成员关联、且名下没有应用）。

    单独做成函数而不是附在账号删除后面：早期测试账号的租户没写进 join 表，
    按 join 删账号时不到它们；账号清干净后再跑一次本脚本仍需要能收到这些尾巴。
    护栏“名下无应用”不能省：否则可能把真实工作区整体扫掉。
    """
    cur.execute('SELECT t.id FROM dify_tenants t LEFT JOIN '
                'dify_tenant_account_joins j ON j.tenant_id = t.id WHERE j.tenant_id IS NULL')
    orphan_ids = [str(r['id']) for r in cur.fetchall()]
    prunable, held = [], []
    for tid in orphan_ids:
        (held if _count_owned(cur, 'dify_apps', 'tenant_id', tid) else prunable).append(tid)
    if apply_changes and prunable:
        ph = ', '.join(['%s'] * len(prunable))
        cur.execute('DELETE FROM dify_tenants WHERE id IN (%s)' % ph, prunable)
    print('孤立租户：可清 %d 个，因名下有应用而保留 %d 个%s'
          % (len(prunable), len(held), '' if apply_changes else '（dry-run，未写库）'))
    return len(prunable)


def _repair_orphan_apps(cur, primary, apply_changes):
    """把“归属指向不存在的账号 / 干脆没写归属”的应用回填给主账号。

    为什么需要这一步：users 表删除、agents.owner 迁为 UUID 之后，库里还剩这类
    “孤儿 created_by”。utils/ownership.py 对它们一律放行（不然会把资源锁死），
    列表接口也把它们归入“无主可见” —— 等于谁都能改。回填给主账号是把
    “没人负责”变成“有人负责”，并且主账号本来就是这台机器上唯一的管理员。

    护栏：只改 created_by 为空或全库反查不到账号的行，绝不抢已有有效归属的应用。
    """
    if not primary:
        print('无主应用归属回填：跳过（未能识别主账号）')
        return 0
    cur.execute(r'''SELECT id, name, created_by FROM dify_apps
                    WHERE created_by IS NULL OR created_by = ''
                       OR created_by NOT IN (SELECT id FROM dify_accounts)
                    ORDER BY created_at''')
    rows = cur.fetchall()
    if apply_changes and rows:
        # IN 列表的占位符必须逐行拼：写成一个 '%s' 会让参数比占位符多，
        # pymysql 直接报“not all arguments converted”（dry-run 不执行这一句，测不出来）
        ph = ', '.join(['%s'] * len(rows))
        cur.execute('UPDATE dify_apps SET created_by = %s WHERE id IN (%s)' % ('%s', ph),
                    [primary] + [str(r['id']) for r in rows])
    print('无主应用归属回填：%d 个应用（created_by 为空或指向已不存在的账号）归到主账号 %s%s'
          % (len(rows), str(primary)[:8], '' if apply_changes else '（dry-run，未写库）'))
    for r in rows:
        print('   %-32s created_by=%-40s %s'
              % (str(r['name'] or '')[:32], str(r['created_by']), str(r['id'])[:8]))
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='真正删除；缺省只做 dry-run')
    ap.add_argument('--keep', default='', help='额外保护的用户名，逗号分隔')
    ap.add_argument('--drop-unverifiable', action='store_true',
                    help='额外删除“存量哈希形状不属于任何已知算法”（已不可能登录）且名下无资源的账号')
    ap.add_argument('--no-repair-orphans', dest='repair_orphans', action='store_false',
                    help='不把无主应用的 created_by 回填给主账号（缺省会回填）')
    args = ap.parse_args()
    keep_names = set(x.strip() for x in args.keep.split(',') if x.strip())

    db = get_db()
    try:
        cur = db.cursor()

        # 主账号：拥有最多应用创建记录的那个，永远保护
        cur.execute("SELECT created_by FROM dify_apps WHERE created_by IS NOT NULL "
                    "AND created_by <> '' GROUP BY created_by ORDER BY COUNT(1) DESC LIMIT 1")
        primary = (cur.fetchone() or {}).get('created_by')

        cur.execute("SELECT id, name, email, status FROM dify_accounts WHERE " + _candidate_where() +
                    " ORDER BY created_at", _junk_params())
        rows = cur.fetchall()

        targets, skipped = [], []

        # 可选的一类：不是测试名字、但密码形状已不属于任何算法 -> 这台机器上永远登不进去。
        # 同样受“名下无资源 + 非主账号”护栏保护，不满足只报告不删。
        extra = []
        if args.drop_unverifiable:
            cur.execute('SELECT id, name, email, password, password_salt FROM dify_accounts')
            for r in cur.fetchall():
                aid = str(r['id'])
                if primary and aid == str(primary):
                    continue
                if any(t['id'] == r['id'] for t in targets):
                    continue
                if not r.get('password') or not r.get('password_salt'):
                    continue
                try:
                    fmt = classify(base64.b64decode(r['password']))
                except Exception:
                    continue
                if fmt not in ('argon2_raw32', 'pbkdf2_hex64'):
                    owned = (_count_owned(cur, 'agents', 'owner', aid)
                             + _count_owned(cur, 'dify_apps', 'created_by', aid)
                             + _count_owned(cur, 'dify_datasets', 'created_by', aid))
                    if owned:
                        print('   [KEEP] %-24s 哈希形状不认识但名下有 %d 项资源，不删'
                              % ((r.get('name') or '')[:24], owned))
                        continue
                    r['_why'] = '哈希形状 %s，已无法登录' % fmt
                    extra.append(r)
        targets.extend(extra)

        for a in rows:
            aid = str(a['id'])
            name = a.get('name') or ''
            why = None
            if primary and aid == str(primary):
                why = '主账号'
            elif name in keep_names:
                why = '--keep 指定保护'
            else:
                owned = {
                    'agents': _count_owned(cur, 'agents', 'owner', aid),
                    'dify_apps': _count_owned(cur, 'dify_apps', 'created_by', aid),
                    'dify_datasets': _count_owned(cur, 'dify_datasets', 'created_by', aid),
                }
                if any(owned.values()):
                    why = '名下有资源 %s' % owned
            if why:
                skipped.append((name, aid[:8], why))
            else:
                targets.append(a)

        print('主账号（永不删除）: %s' % (str(primary)[:8] if primary else '(未识别)'))
        print('命中垃圾模式     : %d 个' % len(rows))
        for name, short, why in skipped:
            print('   [KEEP] %-24s %s  原因：%s' % (name, short, why))
        print('\n将删除 %d 个账号：' % len(targets))
        tenant_ids = []
        for a in targets:
            aid = str(a['id'])
            cur.execute('SELECT tenant_id FROM dify_tenant_account_joins WHERE account_id = %s',
                        (aid,))
            ts = [str(r['tenant_id']) for r in cur.fetchall()]
            tenant_ids.extend(ts)
            print('   %-26s %-10s email=%-28s 租户 %d 个%s'
                  % ((a.get('name') or '')[:26], aid[:8],
                     str(a.get('email') or '')[:28], len(ts),
                     '  <- ' + a['_why'] if a.get('_why') else ''))

        if not targets:
            print('\n没有需要删除的垃圾账号，但仍检查无主应用归属与孤立租户尾巴。')
            if args.repair_orphans:
                _repair_orphan_apps(cur, primary, args.apply)
            _prune_orphan_tenants(cur, args.apply)
            if args.apply:
                db.commit()
            print('\n=== 结论 ===\n  [OK] 库里已无垃圾模式账号')
            return 0

        if not args.apply:
            print('\nDRY-RUN：未写库。加 --apply 才会真删。')
            if args.repair_orphans:
                _repair_orphan_apps(cur, primary, False)
            _prune_orphan_tenants(cur, False)
            return 0

        ids = [str(a['id']) for a in targets]
        ph_ids = ', '.join(['%s'] * len(ids))
        cur.execute('DELETE FROM user_roles WHERE user_id IN (%s)' % ph_ids, ids)
        try:
            # 通知表的列名历史上改过，不允许它带着整笔删除回滚；失败就只记一笔
            cur.execute('DELETE FROM user_notifications WHERE user_id IN (%s)' % ph_ids, ids)
        except Exception as e:
            print('   (user_notifications 未清理: %s)' % str(e)[:60])
        cur.execute('DELETE FROM dify_tenant_account_joins WHERE account_id IN (%s)' % ph_ids, ids)
        if tenant_ids:
            ph_t = ', '.join(['%s'] * len(tenant_ids))
            cur.execute('DELETE FROM dify_tenants WHERE id IN (%s)' % ph_t, tenant_ids)
        cur.execute('DELETE FROM dify_accounts WHERE id IN (%s)' % ph_ids, ids)
        # 这里故意不 commit：本脚本对外承诺“单事务、失败回滚”，而下面还有
        # 无主应用回填与孤立租户清理两步。中途 commit 会把已删账号固化下来，
        # 后面一报错就只回滚一半（实测踩过：账号已真删、应用归属没回填）。
        # 同一个连接里未提交的写入自己看得见，所以下面的统计不受影响。

        cur.execute('SELECT COUNT(1) AS n FROM dify_accounts')
        left = int((cur.fetchone() or {}).get('n') or 0)
        cur.execute('SELECT COUNT(1) AS n FROM dify_accounts WHERE ' + _candidate_where(),
                    _junk_params())
        left_test = int((cur.fetchone() or {}).get('n') or 0)
        cur.execute('SELECT COUNT(1) AS n FROM dify_tenants t LEFT JOIN '
                    'dify_tenant_account_joins j ON j.tenant_id = t.id WHERE j.tenant_id IS NULL')
        orphan_tenants = int((cur.fetchone() or {}).get('n') or 0)

        # 收尾：无主应用归属回填 + 清掉本次删不到、也没随 join 走的孤立租户
        if args.repair_orphans:
            _repair_orphan_apps(cur, primary, True)
        _prune_orphan_tenants(cur, True)
        db.commit()
        cur.execute('SELECT COUNT(1) AS n FROM dify_tenants t LEFT JOIN '
                    'dify_tenant_account_joins j ON j.tenant_id = t.id WHERE j.tenant_id IS NULL')
        orphan_after = int((cur.fetchone() or {}).get('n') or 0)
        print('\n删除后：账号 %d 个，其中垃圾模式残留 %d 个' % (left, left_test))
        print('=== 结论 ===')
        if left_test:
            print('  [X] 仍有 %d 个垃圾模式账号未删（应都在 [KEEP] 里，请核对）' % left_test)
            return 1
        if orphan_after:
            print('  [!] 还剩 %d 个孤立租户：它们名下有应用或被别的流程引用，已故意不删' % orphan_after)
        print('  [OK] 垃圾账号已清空，真实账号未受影响')
        return 0
    except Exception as e:
        db.rollback()
        print('!! 失败已回滚: %r' % e)
        return 1
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
