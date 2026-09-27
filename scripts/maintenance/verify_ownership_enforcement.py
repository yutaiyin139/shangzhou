# -*- coding: utf-8 -*-
"""归属校验与越权面端到端验证（对运行中的后端打真实 HTTP，不改任何业务数据）。

    python scripts/maintenance/verify_ownership_enforcement.py [--base http://localhost:5000]

为什么要脚本化：这类问题（keep-alive 串台、owner 类型不匹配、account 接口信客户端 uid）
全靠手点浏览器验证，回归一次要半小时，而且没人会第二次点全。

令牌直接用 utils.auth.generate_access_token 按库中真实账号签发，不写任何账号口令。
涉及写入的用例有三个，全部自清：PUT /api/account（探针手机号，发起方与拥有者两侧都先备份原值、
结束无条件还原，见 T8）、POST /api/notifications（T19，结束删行）、POST /api/agents/<id>/config-revisions
（T22，结束删行）。角色写用例一律拿 999999 这个不存在的 id，守卫退化也不会真改到现存数据。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from config import get_db  # noqa: E402
from utils.auth import generate_access_token  # noqa: E402

RESULTS = []
PROBE_NOTIF = 'IDOR-PROBE-NOTIF'
PROBE_REV = 'IDOR-PROBE-REV'


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok), detail))
    print('%-58s %s  %s' % (name, '[PASS]' if ok else '[FAIL]', detail[:120]))


def skip(name, reason):
    """用例跑不起来必须记成失败：上一版就是因为静默跳过，把“没验到”拍成了“7/7 通过”。"""
    RESULTS.append((name, False, 'SKIPPED: ' + reason))
    print('%-58s [SKIP]  %s' % (name, reason[:120]))


def call(base, path, token=None, method='GET', body=None):
    url = base + path
    data = None
    headers = {'Accept': 'application/json'}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'ignore') or '{}'
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:200]}
    except Exception as e:
        return 0, {'err': str(e)[:200]}


def _fetch(sql, params=None):
    """只读查库；params=None 时不能把 () 交给 execute（pymysql 仍会做 % 格式化）。"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(sql) if params is None else cur.execute(sql, params)
        rows = cur.fetchall()
        db.commit()
    finally:
        db.close()
    return rows


def _run(sql, params):
    """收尾用的写（只删自己建的探针行）。"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(sql, params)
        db.commit()
        return cur.rowcount
    finally:
        db.close()


def _phone_of(uid):
    """读单个账号的手机号原值（用完必关连接）。"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT phone FROM dify_accounts WHERE id = %s', (str(uid),))
        return (cur.fetchone() or {}).get('phone')
    finally:
        db.close()


def _restore_phone(uid, value):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'UPDATE dify_accounts SET phone = %s WHERE id = %s', (value, str(uid)))
        db.commit()
    finally:
        db.close()


def pick_accounts(cur):
    """选账号的口径很关键：

    “资源拥有者”按 agents.owner 实际持有条数选，而不是按角色选。
    上一版先拿 user_roles 里的第一个 admin，结果抽中了一个 test_reg_* 账号（名下 0 个），
    于是“能看到自己的智能体”这一项验的是个空集，得不出任何结论。
    “对照账号”必须挑非管理员（管理员命中豁免，测不出 403），且优先避开 test_* 残留。
    """
    cur.execute("SELECT id, name, email FROM dify_accounts")
    accounts = {str(a['id']): a for a in cur.fetchall()}
    cur.execute("SELECT user_id, role_id FROM user_roles")
    pairs = cur.fetchall()
    cur.execute("SELECT id, name FROM roles")
    rmap = {r['id']: (r['name'] or '') for r in cur.fetchall()}
    admin_ids = set(str(p['user_id']) for p in pairs if rmap.get(p['role_id'], '').lower() == 'admin')

    cur.execute(r"SELECT owner, COUNT(1) AS n FROM agents WHERE owner IS NOT NULL AND owner <> '' "
                r"GROUP BY owner ORDER BY n DESC LIMIT 1")
    row = cur.fetchone()
    owner_id = str(row['owner']) if row else None
    admin = accounts.get(owner_id) if owner_id else None
    if admin is None:
        return None, None, None, None, [], '', []

    peer = None
    for aid, acc in accounts.items():
        if aid == str(admin['id']) or aid in admin_ids:
            continue
        nm = (acc.get('name') or '') + (acc.get('email') or '')
        if nm.startswith('test') or 'test_reg_' in nm or 'e2e' in nm:
            continue
        peer = acc
        break
    if peer is None:          # 找不到干净账号就退而求其次，宁可用测试账号也不能没有对照组
        for aid, acc in accounts.items():
            if aid != str(admin['id']) and aid not in admin_ids:
                peer = acc
                break

    cur.execute("SELECT id, name, type, owner FROM agents WHERE owner = %s ORDER BY id", (str(admin['id']),))
    owned = cur.fetchall()
    multi = next((r for r in owned if r['type'] == 'multi'), None)
    single = next((r for r in owned if (r['type'] or 'single') != 'multi'), None)
    # /api/agents 只列 single，拿全量条数去比会假报失败（上一轮就这样被红了一次）
    owned_single = [r for r in owned if (r['type'] or 'single') != 'multi']
    admin_role = 'admin' if str(admin['id']) in admin_ids else 'user'
    return admin, peer, single, multi, owned, admin_role, owned_single


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://localhost:5000')
    args = ap.parse_args()
    base = args.base.rstrip('/')

    db = get_db()
    cur = db.cursor()
    admin, peer, single, multi, owned, admin_role, owned_single = pick_accounts(cur)
    # 拥有者自己的 phone 原值（PUT 用例要还原）
    cur.execute("SELECT phone, email FROM dify_accounts WHERE id = %s", (str(admin['id']),)) if admin else None
    owner_backup = cur.fetchone() if admin else {}
    db.close()

    if not admin:
        print('!! 库里找不到任何有 owner 的智能体，无法验证归属（先跑 migrate_agent_owner.py --apply）')
        return 2
    if not peer:
        print('!! 只有 1 个账号，缺少对照组：越权类用例无法验证')
        return 2
    print('资源拥有者 = %s(%s, 角色 %s)  对照非管理员 = %s(%s)  名下智能体 %d 个'
          % (admin['name'], str(admin['id'])[:8], admin_role,
             peer['name'], str(peer['id'])[:8], len(owned)))

    # 角色一定按库里实际取的：给对照账号签个 admin 角色，就等于自己把豁免后门插回去
    at = generate_access_token(str(admin['id']), admin.get('email') or '', admin['name'], admin_role)
    pt = generate_access_token(str(peer['id']), peer.get('email') or '', peer['name'], 'user')

    # ---- 1. 登录闸门 ----
    st, _ = call(base, '/api/agents')
    check('T1 匿名访问 /api/agents 被拒', st in (401, 403), 'HTTP %s' % st)

    # ---- 2. 列表可见性（迁移后最关键：不能把用户的资源弄丢）----
    st, body = call(base, '/api/agents?uid=1', at)
    rows = body.get('data') or []
    check('T2 拥有者 /api/agents 能看到自己名下全部单智能体',
          st == 200 and len(rows) >= len(owned_single) and len(owned_single) > 0,
          'HTTP %s, %d 条（库里名下 single %d 条）' % (st, len(rows), len(owned_single)))
    st, body = call(base, '/api/agents?uid=1', pt)
    rows_p = [r for r in (body.get('data') or [])]
    check('T3 非管理员带 ?uid=1 不再看到别人的私有智能体', st == 200 and len(rows_p) == 0,
          'HTTP %s, 泄漏 %d 条' % (st, len(rows_p)))

    # ---- 3. 详情越权 ----
    if single:
        sid = single['id']
        st, _ = call(base, '/api/agents/%s' % sid, at)
        check('T4 拥有者读自己资源 200', st == 200, 'HTTP %s' % st)
        st, body = call(base, '/api/agents/%s' % sid, pt)
        check('T5 非管理员读他人智能体详情被拒', st == 403,
              'HTTP %s %s' % (st, str(body.get('msg') or '')[:40]))
    else:
        skip('T4 拥有者读自己资源 200', '名下没有单智能体可测')
        skip('T5 非管理员读他人智能体详情被拒', '名下没有单智能体可测')
    if multi:
        st, body = call(base, '/api/multi-agents/%s' % multi['id'], pt)
        check('T6 多智能体详情同样受归属约束', st == 403, 'HTTP %s' % st)
    else:
        skip('T6 多智能体详情同样受归属约束', '名下没有多智能体可测')

    # ---- 4. 账户接口 IDOR（本次新发现的洞）----
    st, body = call(base, '/api/account?uid=%s' % urllib.parse.quote(str(admin['id'])), pt)
    got = body.get('data') or {}
    # 比主键而不是比 email：换列名/脏数据都能穿，比对“返回的是不是对方那一行”才能说明问题
    leaked = got and str(got.get('id') or '') == str(admin['id'])
    check('T7 非管理员用 ?uid=<别人的账号> 读不到对方账号', st == 200 and not leaked,
          'HTTP %s, 返回 id=%s 邮箱=%s' % (st, got.get('id') if got else '(空)',
                                            got.get('email') if got else '(空)'))

    probe = 'IDOR-PROBE-9999'
    # 身份收敛后 PUT /api/account 只认 token，body.uid 会被忽略 ——
    # 等于探针值会写到**发起方自己**的手机号上。上一版只还原了拥有者那一侧，
    # 结果把对照账号（鼎正）的手机号永久留在了 IDOR-PROBE-9999。
    # 两边都先备份原值、结束无条件还原，本脚本才算真“不改业务数据”。
    my_before = _phone_of(peer['id'])
    st, body = call(base, '/api/account', pt, method='PUT',
                    body={'uid': str(admin['id']), 'phone': probe})
    now_phone = _phone_of(admin['id'])
    check('T8 非管理员 PUT /api/account 改不动别人的手机号', str(now_phone) != probe,
          'HTTP %s, 拥有者 phone=%s' % (st, now_phone or '(空)'))
    if str(now_phone) == probe:
        _restore_phone(admin['id'], owner_backup.get('phone'))
        print('     （已还原拥有者被改坏的手机号）')
    if str(_phone_of(peer['id'])) != str(my_before):
        _restore_phone(peer['id'], my_before)
        print('     （已还原发起方自己身上的探针残留）')

    # ---- 5. 我的智能体聚合页 ----
    st, body = call(base, '/api/my-agents', at)
    mine = [x for x in (body.get('data') or []) if x.get('type') in ('single', 'multi')]
    check('T9 拥有者 /api/my-agents 聚合到名下智能体',
          st == 200 and len(mine) >= len(owned) and len(owned) > 0,
          'HTTP %s, %d 条' % (st, len(mine)))

    # ---- 6. API Key 归属 ----
    st, body = call(base, '/api/account/api-keys?uid=%s' % urllib.parse.quote(str(admin['id'])), pt)
    check('T10 非管理员看不到别人工作区的 API Key 列表',
          st in (200, 403) and not (body.get('data') and st == 200),
          'HTTP %s, %d 条' % (st, len(body.get('data') or [])))

    # ---- 7. 技能双通道兼容（配置页“暂无 Skill”那个缺陷）----
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT a.id FROM agents a "
                "LEFT JOIN agent_skill_bindings b ON b.agent_id = a.id "
                "WHERE a.owner = %s AND b.id IS NULL AND a.config LIKE %s LIMIT 1",
                (str(admin['id']), '%skills%'))
    legacy = cur.fetchone()
    db.close()
    if legacy:
        st, body = call(base, '/api/agents/%s/skills' % legacy['id'], at)
        n = len(body.get('data') or [])
        check('T11 只写在 config.skills 里的技能仍能被读到', st == 200 and n > 0,
              'HTTP %s, 智能体 %s 返回 %d 条' % (st, legacy['id'], n))
    else:
        skip('T11 只写在 config.skills 里的技能仍能被读到',
             '库里没有“绑定表为空但 config 有 skills”的样本，验不到兜底分支')

    # ---- 8. 平台管理面边界（utils/auth.platform_admin_required）----
    # 集中闸门只保证“必须登录”，登录了不等于能用管理面。这组曾经全部开着：
    # 普通用户能拉到全体账号的邮箱/手机号、能建 admin 号、能改别人密码、能自我提权。
    hacker = 'IDOR-PROBE-HACKER'
    st, body = call(base, '/api/users', pt)
    check('T12 非管理员读 /api/users（全体账号 PII）被拒', st == 403,
          'HTTP %s %s' % (st, str(body.get('msg') or '')[:36]))
    st, body = call(base, '/api/users', pt, method='POST',
                    body={'username': hacker, 'password': 'Probe#Hack2026',
                          'email': 'idor-probe-hacker@example.com', 'role': 'admin'})
    check('T13 非管理员建 admin 账号被拒', st == 403,
          'HTTP %s %s' % (st, str(body.get('msg') or '')[:36]))
    st, body = call(base, '/api/users/%s/roles' % urllib.parse.quote(str(peer['id'])), pt,
                    method='PUT', body={'role': 'admin'})
    check('T14 非管理员给自己提权被拒', st == 403,
          'HTTP %s %s' % (st, str(body.get('msg') or '')[:36]))
    # 用 999999 这个不存在的角色号：万一守卫退化，也不会真改到任何现存角色的权限
    st, body = call(base, '/api/roles/999999/permissions', pt, method='PUT',
                    body={'permission_ids': []})
    check('T15 非管理员改角色权限矩阵被拒', st == 403,
          'HTTP %s %s' % (st, str(body.get('msg') or '')[:36]))
    still = _fetch('SELECT id FROM dify_accounts WHERE name = %s', (hacker,))
    promoted = [r['name'] for r in _fetch(
        'SELECT r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = %s',
        (str(peer['id']),))]
    check('T16 被拒的写一行都没落库',
          not still and 'admin' not in promoted,
          '残留账号=%d, 对照账号角色=%s' % (len(still), promoted or '(无)'))
    st, body = call(base, '/api/users', at)
    rows = body.get('data') or []
    check('T17 管理员读 /api/users 正常（不误伤）',
          st == 200 and len(rows) >= 2, 'HTTP %s, %d 条' % (st, len(rows)))
    st, body = call(base, '/api/roles', pt)
    check('T18 普通用户读角色清单仍可用（用户管理页下拉要用）', st == 200,
          'HTTP %s, %d 条' % (st, len(body.get('data') or [])))

    # ---- 9. 通知收件箱只认 token ----
    notif_id = None
    try:
        st, body = call(base, '/api/notifications', pt, method='POST',
                        body={'user_id': str(admin['id']), 'title': PROBE_NOTIF,
                              'type': 'info'})
        notif_id = str(((body.get('data') or {}).get('id')) or '')
        owner_row = _fetch('SELECT user_id FROM user_notifications WHERE id = %s', (notif_id,)) \
            if notif_id else []
        check('T19 POST /api/notifications 的 body.user_id 不采信（落在自己名下）',
              st == 200 and str((owner_row[0] if owner_row else {}).get('user_id') or '') == str(peer['id']),
              'HTTP %s, 落库 user_id=%s' % (st,
                                        str((owner_row[0] if owner_row else {}).get('user_id') or '')[:8]))
        st, body = call(base, '/api/notifications?uid=%s' % urllib.parse.quote(str(peer['id'])), at)
        items = ((body.get('data') or {}).get('items')) or []
        check('T20 拥有者带 ?uid=<别人> 读不到对方的探针通知',
              st == 200 and not any(i.get('id') == notif_id for i in items),
              'HTTP %s, 看到 %d 条' % (st, len(items)))
    finally:
        if notif_id:
            _run('DELETE FROM user_notifications WHERE id = %s AND user_id = %s',
                 (notif_id, str(peer['id'])))
    check('T21 通知探针行已清掉',
          not _fetch('SELECT id FROM user_notifications WHERE title = %s', (PROBE_NOTIF,)))

    # ---- 10. 配置快照归属（agent_config_revisions.created_by 曾仍是 INT）----
    # 列还是整型时，写 UUID 会被 MySQL 静默截成 0：“谁改的”全丢且不报错。
    rev_id = None
    if single:
        try:
            st, body = call(base, '/api/agents/%s/config-revisions' % single['id'], at,
                            method='POST',
                            body={'config': {'probe': True}, 'strategy': 'react',
                                  'change_note': PROBE_REV,
                                  'uid': str(peer['id']), 'created_by': str(peer['id'])})
            rev_id = (body.get('data') or {}).get('revision_id')
            row = _fetch('SELECT created_by FROM agent_config_revisions WHERE id = %s', (rev_id,)) \
                if rev_id else []
            wrote = str((row[0] if row else {}).get('created_by') or '')
            check('T22 保存配置版本：created_by = token 本人（请求体里的 uid 不采信）',
                  st == 200 and bool(rev_id) and wrote == str(admin['id']),
                  'HTTP %s, created_by=%s' % (st, wrote[:36] or '(空)'))
        finally:
            if rev_id:
                _run('DELETE FROM agent_config_revisions WHERE id = %s', (rev_id,))
        check('T23 快照探针行已清掉且表里没有 created_by=0',
              not _fetch('SELECT id FROM agent_config_revisions WHERE change_note = %s', (PROBE_REV,))
              and int(_fetch('SELECT COUNT(1) AS n FROM agent_config_revisions '
                             'WHERE created_by = %s', ('0',))[0]['n']) == 0)
    else:
        skip('T22 保存配置版本：created_by = token 本人', '拥有者名下没有单智能体，无法写快照')
        skip('T23 快照探针行已清掉且表里没有 created_by=0', '同上')

    failed = [n for n, ok, _ in RESULTS if not ok]
    print('\n=== %d/%d 通过 ===' % (len(RESULTS) - len(failed), len(RESULTS)))
    for f in failed:
        print('  [X] ' + f)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
