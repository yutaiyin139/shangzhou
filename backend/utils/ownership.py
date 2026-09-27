# -*- coding: utf-8 -*-
"""资源归属校验（默认拒绝的第二道卡：登录之后还要证明"这是你的"）。

模式由根目录 .env 的 OWNERSHIP_CHECK_MODE 控制：
  off    —— 完全不校验
  warn   —— 只记日志（默认；用于先把数据现实摸清楚）
  strict —— 非归属且非管理员时返回 403

数据现实（2026-09 在本机库实测，写这里是为了不让后来人误判）：
  agents.owner             账号 UUID（dify_accounts.id）。历史上是 INT、存的是已删除的
                           旧 users.id（1/2/3），已由 scripts/maintenance/migrate_agent_owner.py
                           完成列类型变更与回填，现在能与 token 里的 user_id 直接比对；
  dify_apps.created_by     账号 UUID，且存在 NULL / 指向已不存在账号的历史数据；
  dify_conversations.user_id  大部分为 NULL，还有 e2e-tester / test-user 这类测试值。
  另：库里没有 `users` 表，账号在 dify_accounts、角色在 user_roles。
因此归属比对就是“token 里的 user_id == 归属列”一句：不需要再拿 name/email 去凑
（users 表时代两个 id 体系不同源才需要那层中转）。凑 name/email 不只是冗余，它还危险：
库里真实出现过“A 的 email == B 的 name”这种错位数据，按姓名/邮箱比对会把别人的
资源认成自己的。

本模块的策略是：归属信息缺失（NULL/查不到/指向已无对应账号）一律放行并只记一条日志，
绝对不要因为"数据没写全"就把用户挡在自己的资源之外。
"""
import logging
import os
import re

from flask import current_app, jsonify

logger = logging.getLogger('szagent.ownership')

# 只有这些资源参与归属判定；知识库、模型、插件、TTS 等属于全局共享资源。
#
# 刻意不包含 dify_conversations：实测该表 user_id 只有 NULL / e2e-tester / test-user
# 三种值，没有任何真实账号，拿它做归属判定只会误伤（对话本来是按应用/工作区组织的）。
RESOURCE_RULES = (
    # (路径正则, 表名, 主键列, 归属列)
    (re.compile(r'^/api/agents/(?P<id>\d+)(?:[/?].*)?$'), 'agents', 'id', 'owner'),
    # 多智能体与单智能体同表（agents.type='multi'），不登记就是归属校验的缺口：
    # 列表接口已按 owner 过滤，详情/编辑/删除却不校验，等于“看不到但能改”。
    (re.compile(r'^/api/multi-agents/(?P<id>\d+)(?:[/?].*)?$'), 'agents', 'id', 'owner'),
    (re.compile(r'^/api/workflows/(?P<id>[^/?]+)(?:[/?].*)?$'), 'dify_apps', 'id', 'created_by'),
    (re.compile(r'^/api/apps/(?P<id>[^/?]+)(?:[/?].*)?$'), 'dify_apps', 'id', 'created_by'),
)

# 列表接口同样要按归属过滤才有意义，但那是"查询条件"层面的改动，本模块只在 warn 里提示
LIST_PATH_HINTS = ('/api/agents', '/api/workflows', '/api/apps', '/api/conversations')


def get_mode():
    forced = current_app.config.get('OWNERSHIP_CHECK_MODE')
    if forced is not None:
        raw = str(forced).strip().lower()
    else:
        raw = (os.environ.get('OWNERSHIP_CHECK_MODE') or 'warn').strip().lower()
    if raw in ('strict', '1', 'true', 'on', 'enforce'):
        return 'strict'
    if raw in ('warn', 'log', 'observe'):
        return 'warn'
    if raw in ('off', '0', 'false', ''):
        return 'off'
    logger.warning('OWNERSHIP_CHECK_MODE 取值 %r 无法识别，按 warn 处理', raw)
    return 'warn'


def _match_rule(path):
    for pattern, table, pk_col, owner_col in RESOURCE_RULES:
        m = pattern.match(path)
        if m:
            return table, pk_col, owner_col, m.group('id')
    return None


def _owner_of(table, pk_col, owner_col, res_id):
    """读出该资源的归属值；查不到资源或列值时返回 (None, None)。"""
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT `%s` AS v FROM `%s` WHERE `%s` = %%s' % (owner_col, table, pk_col), (res_id,))
        row = cur.fetchone()
        if not row:
            return None, None
        return row.get('v'), True
    except Exception as e:
        logger.warning('归属查询失败 %s.%s(%s): %s', table, owner_col, res_id, str(e)[:160])
        return None, None
    finally:
        db.close()


def _my_identity_values(user_id):
    """当前账号可用的归属标识：就只有 token 里的 user_id（= dify_accounts.id）。

    以前这里还会把账号的 name / email / nickname 和工作区 account_id、tenant_id 一起
    收进来比对。那是“本地 users.id 与 Dify account_id 不同源”年代的补偿动作：
    users 表已废弃删除、owner/created_by 列已统一回填为 dify_accounts.id，这层中转
    既多余又危险 —— 邮箱与姓名在人手里会撞车（库里就有 email='yutaiyin' 与
    name='yutaiyin' 分属两个账号），撞上就是把别人的资源判成自己的。
    任何查询失败只降级不抛异常（本函数已不再查库，保留同名与返回类型供调用方使用）。
    """
    if user_id is None:
        return set()
    return {str(user_id)}


_KNOWN_CACHE = {'values': set(), 'at': 0.0}
_KNOWN_TTL = 60.0


def _known_owner_values():
    """全库已知归属值：所有账号 id。

    用途是区分“这是别人的资源”（403）与“这是迁移遗留、指向已不存在的账号”（放行）。
    不区分的后果很严重：从 Dify 迁过来的数据里有 created_by 已无对应账号，
    直接 strict 会把资源锁死给任何人看。

    只收 id：归属列现在只可能存 dify_accounts.id。把 name/email 也收进来会让
    “恰好等于某人邮箱的一个字符串”被当成有效归属，把遗留数据误判成别人的资源。
    """
    import time as _time
    now = _time.time()
    if _KNOWN_CACHE['values'] and now - _KNOWN_CACHE['at'] < _KNOWN_TTL:
        return _KNOWN_CACHE['values']
    values = set()
    try:
        from config import get_db
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT id FROM dify_accounts')
            for row in cur.fetchall():
                val = str(row.get('id') or '').strip()
                if val:
                    values.add(val)
        finally:
            db.close()
    except Exception as e:
        logger.warning('汇总已知归属标识失败，本轮全部按"未知"放行: %s', str(e)[:160])
        return _KNOWN_CACHE['values'] or values
    _KNOWN_CACHE['values'] = values
    _KNOWN_CACHE['at'] = now
    return values


def check_request():
    """返回 None 表示放行；返回 (dict, status) 表示拒绝。"""
    from flask import request
    mode = get_mode()
    if mode == 'off':
        return None
    user = getattr(request, 'user', None)
    if not user:
        return None            # 未登录由 api_guard 负责，这里不重复管
    if (user.get('role') or '') == 'admin':
        return None            # 管理员可跨归属排障（写操作也一律走审计日志）

    rule = _match_rule(request.path or '')
    if not rule:
        return None
    table, pk_col, owner_col, res_id = rule

    owner, found = _owner_of(table, pk_col, owner_col, res_id)
    if not found:
        return None            # 资源不存在：交给业务接口自己回 404
    if owner is None or owner == '':
        # 历史数据没有归属信息：只提示，不拦截，否则会把用户挡在自己的资源之外
        logger.warning('[ownership:warn] %s %s 的资源 %s.%s 无归属记录，strict 下仍放行',
                       request.method, request.path, table, res_id)
        return None

    mine = _my_identity_values(user.get('user_id'))
    owner_text = str(owner)
    if owner_text in mine:
        return None

    # 归属指向已不存在的账号（从 Dify 迁移遗留、或账号已被删）：这不是“别人的资源”，
    # 拦下来只会把资源锁死，所以只记日志。
    if owner_text not in _known_owner_values():
        logger.warning('[ownership:warn] %s %s 的资源 %s.%s=%s 归属 %r 在库里已无对应账号，'
                       '按遗留数据放行', request.method, request.path, table, owner_col, res_id, owner_text)
        return None

    if mode == 'warn':
        logger.warning('[ownership:warn] 用户 %s(user_id=%s) 访问非本人资源 %s %s.%s=%s（owner=%s）'
                       ' —— strict 模式将被拒绝', user.get('username') or user.get('email'),
                       user.get('user_id'), request.method, table, owner_col, res_id, owner)
        return None

    logger.warning('[ownership:blocked] %s %s user_id=%s 资源 %s=%s owner=%s',
                   request.method, request.path, user.get('user_id'), table, res_id, owner)
    return jsonify(code=403, msg='无权访问该资源，它不属于当前账号'), 403
