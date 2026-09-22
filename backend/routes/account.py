# -*- coding: utf-8 -*-
"""账户信息路由（MySQL 版，脱离 Dify）"""

import uuid
import secrets
import string
from datetime import datetime
from flask import jsonify, request
from config import get_db
from utils.helpers import now, _generate_password, _compare_password, _valid_password, _safe_uid, CURRENT_USER_ID
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


def register_account_routes(app):
    """注册账户相关路由"""

    @app.route('/api/account', methods=['GET'])
    def get_account():
        """当前登录用户的账户信息：前端从登录态传 uid，缺省回退 CURRENT_USER_ID"""
        uid = str(request.args.get('uid') or CURRENT_USER_ID)
        db = get_db()
        try:
            cur = db.cursor()
            # 使用 dify_accounts 表（users 表已合并到 dify_accounts）
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
        d = request.get_json()
        uid = str(d.get('uid') or CURRENT_USER_ID)
        db = get_db()
        try:
            cur = db.cursor()
            # 使用 dify_accounts 表（users 表已合并）
            cur.execute(r'SELECT id, name, email, phone, password, password_salt FROM dify_accounts WHERE id = %s', (uid,))
            me = cur.fetchone()
            if not me:
                return jsonify(code=400, msg='用户不存在')
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
                vals.append(d['email'])
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
        uid = str(request.args.get('uid') or CURRENT_USER_ID)

        db = get_db()
        try:
            cur = db.cursor()
            # 确保表存在
            cur.execute(DIFY_API_TOKENS_TABLE_SQL)

            # 获取用户的 API tokens（使用 dify_accounts 表）
            cur.execute(r'''
                SELECT t.id, t.token, t.type, t.created_at, a.name AS app_name
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
        """创建新的 API Key"""
        uid = str(request.args.get('uid') or CURRENT_USER_ID)

        d = request.get_json() or {}
        key_name = (d.get('name', '') or 'API Key').strip()
        key_type = d.get('type', 'app')

        # 生成安全的 API token
        api_token = 'sk-' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(32))

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(DIFY_API_TOKENS_TABLE_SQL)

            # 获取用户的 tenant_id（使用 dify_accounts 表）
            cur.execute(r'''
                SELECT tenant_id FROM dify_tenant_account_joins
                WHERE account_id = %s
                LIMIT 1
            ''', (uid,))
            row = cur.fetchone()
            tenant_id = row['tenant_id'] if row else 'default'

            token_id = str(uuid.uuid4())
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                r'''INSERT INTO dify_api_tokens (id, tenant_id, token, type, created_at)
                    VALUES (%s, %s, %s, %s, %s)''',
                (token_id, tenant_id, api_token, key_type, ts)
            )
            db.commit()
            return jsonify(code=200, msg='API Key 创建成功', data={
                'id': token_id,
                'token': api_token,  # 仅创建时返回完整 token
                'type': key_type,
                'created_at': ts,
            })
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='创建失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/account/api-keys/<key_id>', methods=['DELETE'])
    def delete_api_key(key_id):
        """删除 API Key"""
        uid = str(request.args.get('uid') or CURRENT_USER_ID)

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
            return jsonify(code=200, msg='API Key 已删除')
        except Exception as e:
            return jsonify(code=500, msg='删除失败: ' + str(e))
        finally:
            db.close()
