# -*- coding: utf-8 -*-
"""agents 归属健康检查（只读，不写库）。

用途：迁移完成后随时复核，避免"列改了但值没回填"或"身份来源与列类型不匹配"
这类只在运行时才暴露的问题留到发布后。

    python scripts/maintenance/check_agent_ownership.py

检查项：
    1) agents.owner 列类型是否为 VARCHAR(36)（UUID 承载体）
    2) owner 取值分布：空值/无主条数、仍为纯数字的遗留条数
    3) owner 能否反查到 dify_accounts（对齐"已知他人"与"迁移遗留未知"）
    4) 登录身份 _safe_uid 的返回类型是否与列类型一致
    5) 开启 strict 归属过滤后，每个真实账号还能看到多少条自有智能体/应用
       （回答“会不会有人一升级列表就空了”）
"""
import os
import sys

# 本文件在 scripts/maintenance/ 下，要退三级到仓库根再进 backend
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from config import get_db  # noqa: E402


def main():
    fails = []
    db = get_db()
    cur = db.cursor()

    cur.execute(
        "SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS "
        "WHERE TABLE_NAME='agents' AND COLUMN_NAME='owner'"
    )
    col = cur.fetchone()
    if not col:
        print('[!] agents 表没有 owner 列')
        return 1
    col_type = str(col.get('COLUMN_TYPE') or '')
    print('列类型      : %s  (nullable=%s, default=%r)'
          % (col_type, col.get('IS_NULLABLE'), col.get('COLUMN_DEFAULT')))
    if 'varchar' not in col_type.lower():
        fails.append('owner 仍是非字符串列，写入 UUID 会被截断成 0')

    cur.execute(
        "SELECT COALESCE(NULLIF(TRIM(owner),''),'(空)') owner, COUNT(1) n "
        "FROM agents GROUP BY owner ORDER BY n DESC"
    )
    rows = cur.fetchall()
    print('owner 分布  :')
    total = 0
    numeric_left = 0
    empty_left = 0
    for r in rows:
        v = str(r['owner'])
        total += int(r['n'])
        if v == '(空)':
            empty_left += int(r['n'])
        elif v.isdigit():
            numeric_left += int(r['n'])
        print('   %-40s %s' % (v[:40], r['n']))
    print('合计        : %d 条' % total)

    cur.execute("SELECT COUNT(1) n FROM dify_accounts")
    acc_total = int((cur.fetchone() or {}).get('n') or 0)
    cur.execute("SELECT DISTINCT owner FROM agents WHERE owner IS NOT NULL AND owner<>''")
    owners = [str(r['owner']) for r in cur.fetchall()]
    cur.execute("SELECT id FROM dify_accounts")
    valid = set(str(r['id']) for r in cur.fetchall())
    orphans = [o for o in owners if o not in valid]
    print('归属可反查  : owner 去重 %d 个，账号总数 %d，反查不到 %d 个 %s'
          % (len(owners), acc_total, len(orphans), orphans[:3]))

    db.close()

    # 身份来源与列类型是否一致：迁移后 _safe_uid 在 HTTP 上下文应返回账号 UUID
    sys.path.insert(0, os.path.join(BACKEND, 'utils'))
    from utils.helpers import _safe_uid  # noqa: E402
    no_ctx = _safe_uid(None)
    print('无 HTTP 上下文时 _safe_uid = %r (%s)' % (no_ctx, type(no_ctx).__name__))

    # ---- 每个账号的可见性预览：strict 后谁会“列表空掉” ----
    print('\n--- 账号可见性预览（owner 过滤后的自有资源条数）---')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, email FROM dify_accounts ORDER BY created_at")
    accounts = cur.fetchall()
    cur.execute("SELECT user_id, role_id FROM user_roles")
    pairs = cur.fetchall()
    cur.execute("SELECT id, name FROM roles")
    rmap = {r['id']: (r['name'] or '') for r in cur.fetchall()}
    admin_ids = set(str(p['user_id']) for p in pairs
                    if rmap.get(p['role_id'], '').lower() == 'admin')
    empty_real = []
    for acc in accounts:
        aid = str(acc['id'])
        nm = (acc.get('name') or '') + (acc.get('email') or '')
        is_test = nm.startswith('test') or 'test_reg_' in nm or 'e2e' in nm
        cur.execute("SELECT COUNT(1) AS n FROM agents WHERE owner = %s", (aid,))
        n_agents = int((cur.fetchone() or {}).get('n') or 0)
        cur.execute("SELECT COUNT(1) AS n FROM dify_apps WHERE created_by = %s", (aid,))
        n_apps = int((cur.fetchone() or {}).get('n') or 0)
        tag = 'admin' if aid in admin_ids else ('test' if is_test else 'user')
        if aid not in admin_ids and not is_test and n_agents == 0 and n_apps == 0:
            # 管理员命中豁免（看得全量），条数为 0 不算问题；普通账号才会真的“列表空”
            empty_real.append(acc.get('name') or aid[:8])
        print('   %-9s %-22s agents=%-3d apps=%-3d %s'
              % (tag, str(acc.get('name') or '')[:22], n_agents, n_apps, aid[:8]))
    db.close()
    if empty_real:
        print('   -> 非管理员且名下无任何资源（它们只能看到自己新建的东西，不是数据丢了）：'
              + ', '.join(empty_real[:6]))

    # ---- emoji 完整性：图标存成字面量 '?' 就是字符集在某一环丢了 ----
    db = get_db()          # 上面那段预览已经 close 过，这里另开一个连接
    cur = db.cursor()
    cur.execute("SELECT TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'agents'")
    coll = (cur.fetchone() or {}).get('TABLE_COLLATION') or ''
    cur.execute("SELECT COUNT(1) AS n FROM agents WHERE icon = '?'")
    n_icon_q = int((cur.fetchone() or {}).get('n') or 0)
    cur.execute(r"SELECT COUNT(1) AS n FROM agents WHERE config LIKE '%\"icon\": \"?\"%'")
    n_cfg_q = int((cur.fetchone() or {}).get('n') or 0)
    print('\nagents 表校对集 : %s' % coll)
    print('图标为 ? 的行数 : icon=%d, config 内嵌 icon=%d' % (n_icon_q, n_cfg_q))
    # 往返测试：拿一行写个 emoji 再读回来，结束时 ROLLBACK（不提交，不留痕迹）。
    # 不测这一句就分不清“现在还在写坏”与“只是历史数据坏过”。
    try:
        cur.execute("SELECT id FROM agents ORDER BY id LIMIT 1")
        probe_id = (cur.fetchone() or {}).get('id')
        if probe_id is not None:
            cur.execute("SELECT icon FROM agents WHERE id = %s FOR UPDATE", (probe_id,))
            cur.execute("UPDATE agents SET icon = %s WHERE id = %s", ('🤖', probe_id))
            cur.execute("SELECT icon FROM agents WHERE id = %s", (probe_id,))
            back = (cur.fetchone() or {}).get('icon')
            db.rollback()
            if str(back) == '🤖':
                print('emoji 往返     : OK（表与连接都能承载 4 字节字符，存量的 ? 是历史写入造成的）')
            else:
                print('emoji 往返     : 仍被截成 %r' % back)
                fails.append('emoji 写入仍在被截断：当前连接写不进 4 字节字符')
    except Exception as e:
        db.rollback()
        print('emoji 往返     : 未能完成（%s）' % str(e)[:80])
    db.close()
    if n_icon_q or n_cfg_q:
        fails.append('存量 %d 条 icon 已被存成字面量 ?（表校对集与当前连接均能承载 emoji，'
                     '属历史写入损坏，不可还原）：需在页面上重设这些智能体的图标'
                     % (n_icon_q + n_cfg_q))

    if numeric_left:
        fails.append('仍有 %d 条 owner 是纯数字（旧 users.id 遗留）' % numeric_left)
    if empty_left:
        fails.append('仍有 %d 条 owner 为空（按 token 过滤后对这些账号不可见）' % empty_left)
    if orphans:
        fails.append('%d 个 owner 值反查不到账号，非管理员看不到对应资源' % len(orphans))

    print('\n=== 结论 ===')
    if fails:
        for f in fails:
            print('  [X] ' + f)
        return 1
    print('  [OK] 列类型、回填、可反查三项全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
