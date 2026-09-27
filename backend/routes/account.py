# -*- coding: utf-8 -*-
"""账户信息路由（MySQL 版，脱离 Dify）"""

import uuid
import secrets
import string
from datetime import datetime
from flask import jsonify, request
from config import get_db
from utils.helpers import (now, _generate_password, _compare_password, _valid_password,
                           _safe_uid, _check_account_identity)
from models.tables import DIFY_ACCOUNTS_TABLE_SQL, DIFY_API_TOKENS_TABLE_SQL


def _ensure_account_tables():
    """确保账户相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_ACCOUNTS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _caller_uid():
    """账户类接口的身份：只认登录 token（dify_accounts.id）。

    改之前的写法是 str(request.args.get('uid') or 默认用户)，等于把“我是谁”
    交给调用方填：任何登录用户传 ?uid=<别人的账号 id> 就能读别人的手机号/邮箱，
    PUT /api/account 更是能直接改别人的 email —— 改完走一次“忘记密码”就完成账号接管。
    现在统一走 _safe_uid：HTTP 请求里只看 api_guard 核过的 request.user。
    这个函数只负责转成字符串并收成一个出处，避免 5 个端点各写一遍又写歪。

    返回空串 = 没有登录态（闸门处于 off/warn 且未带 token），调用方必须回 401，
    不能拿空串去查库——那会“查无此人”地把缺登录当成业务错误（如“用户不存在”）报给前端。
    """
    return str(_safe_uid(None))


def _need_login():
    """未登录时统一的拒绝响应；登录时返回 None（供 `err = _need_login()` 写法）"""
    if not _caller_uid():
        return jsonify(code=401, msg='请先登录')
    return None


def register_account_routes(app):
    """注册账户相关路由"""

    @app.route('/api/account', methods=['GET'])
    def get_account():
        """当前登录用户的账户信息：身份取自登录 token，不看 URL 上的 uid（防越权读他人资料）"""
        err = _need_login()
        if err:
            return err
        uid = _caller_uid()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''
                SELECT da.id, da.name AS username, da.email, da.phone,
                       da.status, da.created_at,
                       COALESCE(GROUP_CONCAT(r.name SEPARATOR ', '), '') AS role_name
                FROM dify_accounts da
                LEFT JOIN user_roles ur ON ur.user_id = da.id
                LEFT JOIN roles r ON r.id = ur.role_id
                WHERE da.id = %s
                GROUP BY da.id
            ''', (uid,))
            row = cur.fetchone()
            if row:
                if row['created_at']:
                    row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, data=row)
        finally:
            db.close()

    @app.route('/api/account', methods=['PUT'])
    def update_account():
        _ensure_account_tables()
        err = _need_login()
        if err:
            return err
        d = request.get_json()
        uid = _caller_uid()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT id, name, email, phone, password, password_salt FROM dify_accounts WHERE id = %s', (uid,))
            me = cur.fetchone()
            if not me:
                return jsonify(code=400, msg='用户不存在')
            # 改账号名/邮箱：与“管理员建号/改号”同一套全库唯一规则（排除自己）。
            # 不拦就等于任何人都能把别人的登录名改成自己的邮箱，
            # 把登录匹配（name OR email）弄成歧义，还能绕过“忘记密码”的邮箱寻址。
            if 'username' in d or 'email' in d:
                err = _check_account_identity(
                    cur,
                    d.get('username', me['name']) if 'username' in d else me['name'],
                    (d.get('email') or '').strip().lower() if 'email' in d else me['email'],
                    exclude_id=uid)
                if err:
                    return jsonify(code=400, msg=err)
            # 如果传了 old_password，校验旧密码
            if 'old_password' in d and d['old_password']:
                if not _compare_password(d['old_password'], me['password'], me['password_salt']):
                    return jsonify(code=400, msg='原密码错误')
            fields = []
            vals = []
            # username 对应 dify_accounts.name
            if 'username' in d:
                fields.append('name = %s')
                vals.append(d['username'])
            if 'email' in d:
                fields.append('email = %s')
                vals.append((d['email'] or '').strip().lower())
            if 'phone' in d:
                fields.append('phone = %s')
                vals.append(d['phone'])
            salt_b64 = pwd_b64 = None
            if 'password' in d and d['password']:
                if not _valid_password(d['password']):
                    return jsonify(code=400, msg='密码至少 8 位且需同时包含字母和数字')
                # 使用 Argon2id（或 PBKDF2 回退）生成新密码哈希
                salt_b64, pwd_b64 = _generate_password(d['password'], use_argon2=True)
                fields.append('password = %s')
                vals.append(pwd_b64)
            if salt_b64:
                fields.append('password_salt = %s')
                vals.append(salt_b64)
            if fields:
                fields.append('updated_at = %s')
                vals.append(now())
                vals.append(uid)
                cur.execute(f'UPDATE dify_accounts SET {", ".join(fields)} WHERE id = %s', vals)
            db.commit()
            return jsonify(code=200, msg='保存成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='保存失败: ' + str(e))
        finally:
            db.close()

    # ============================================================
    # API Key 管理
    # ============================================================

    @app.route('/api/account/api-keys', methods=['GET'])
    def list_api_keys():
        """获取当前用户的 API Key 列表"""
        err = _need_login()
        if err:
            return err
        uid = _caller_uid()

        db = get_db()
        try:
            cur = db.cursor()
            # 确保表存在
            cur.execute(DIFY_API_TOKENS_TABLE_SQL)

            # 获取用户的 API tokens
            cur.execute(r'''
                SELECT t.id, t.token, t.type, t.app_id, t.created_at, a.name AS app_name
                FROM dify_api_tokens t
                LEFT JOIN dify_apps a ON a.id = t.app_id
                WHERE t.tenant_id = (
                    SELECT tenant_id FROM dify_tenant_account_joins
                    WHERE account_id = %s
                    LIMIT 1
                )
                ORDER BY t.created_at DESC
            ''', (uid,))
            items = []
            for r in cur.fetchall():
                # 脱敏显示 token
                token_display = r['token'][:8] + '...' + r['token'][-4:] if r['token'] and len(r['token']) > 12 else r['token']
                items.append({
                    'id': r['id'],
                    'token': token_display,
                    'type': r['type'],
                    'app_id': r['app_id'],
                    'app_name': r['app_name'],
                    'created_at': str(r['created_at']),
                })
            return jsonify(code=200, data=items)
        except Exception as e:
            return jsonify(code=500, msg='获取 API Key 失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/account/api-keys', methods=['POST'])
    def create_api_key():
        """为本人工作空间内的某个应用创建 Service API Key

        这张表是「应用级」token：utils/auth.api_key_required 校验时走
        `JOIN dify_apps a ON a.id = t.app_id`。以前这里 INSERT 没带 app_id，而
        dify_api_tokens.app_id 是 NOT NULL 且无默认值 → MySQL 直接 1364，
        本接口仍一直返回“创建失败: Field 'app_id' doesn't have a default value”
        （前端只把原因显示成“网络错误”，所以从界面上看不出来）。
        也不能图省事插一条 app_id='' 的记录：那样“创建成功”的 key 拿到 /api/v1
        上只会 401，是假成功。故改成显式选应用，并复用编排页已有的
        _get_or_create_api_token，避免两处各写一份 'app-' 生成规则。
        """
        err = _need_login()
        if err:
            return err
        uid = _caller_uid()

        d = request.get_json() or {}
        app_id = (d.get('app_id') or '').strip()
        if not app_id:
            return jsonify(code=400, msg='请先选择要创建 API Key 的应用')

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(DIFY_API_TOKENS_TABLE_SQL)
            cur.execute(r'SELECT id, name, tenant_id FROM dify_apps WHERE id = %s AND status = %s',
                        (app_id, 'normal'))
            app = cur.fetchone()
            if not app:
                return jsonify(code=404, msg='应用不存在或已删除')
            cur.execute(r'SELECT tenant_id FROM dify_tenant_account_joins WHERE account_id = %s LIMIT 1', (uid,))
            row = cur.fetchone()
            my_tenant = str(row['tenant_id']) if row and row['tenant_id'] else ''
            # 不给别人工作空间的应用发 key
            if not my_tenant or my_tenant != str(app['tenant_id']):
                return jsonify(code=403, msg='只能为本人工作空间内的应用创建 API Key')
            tenant_id = app['tenant_id']
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='创建失败: %s' % e)
        finally:
            db.close()

        from routes.workflows import _get_or_create_api_token   # 懒导入：避开路由模块间的循环依赖
        try:
            token = _get_or_create_api_token(app_id, tenant_id)
        except Exception as e:
            return jsonify(code=500, msg='创建失败: %s' % e)

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT id, created_at FROM dify_api_tokens WHERE token = %s LIMIT 1', (token,))
            rec = cur.fetchone()
        finally:
            db.close()

        # 同一应用已有 key 时 _get_or_create_api_token 会直接返回已有的那一条（幂等）
        return jsonify(code=200, msg='API Key 已就绪', data={
            'id': rec['id'] if rec else '',
            'token': token,                       # 仅创建/查看时返回完整 token
            'type': 'app',
            'app_id': app_id,
            'app_name': app['name'],
            'created_at': str(rec['created_at']) if rec and rec['created_at'] else '',
        })

    @app.route('/api/account/api-keys/<key_id>', methods=['DELETE'])
    def delete_api_key(key_id):
        """删除 API Key"""
        err = _need_login()
        if err:
            return err
        uid = _caller_uid()

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''
                DELETE FROM dify_api_tokens
                WHERE id = %s AND tenant_id = (
                    SELECT tenant_id FROM dify_tenant_account_joins
                    WHERE account_id = %s
                    LIMIT 1
                )
            ''', (key_id, uid))
            db.commit()
            affected = cur.rowcount
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='删除失败: ' + str(e))
        finally:
            db.close()
        # 删不中（id 不存在 / 不是本工作空间的 key）不能也说“已删除”：
        # 前端现在会判 code，不判的话用户会以为列表里那条已经没了
        if not affected:
            return jsonify(code=404, msg='API Key 不存在或无权删除')
        return jsonify(code=200, msg='API Key 已删除')
