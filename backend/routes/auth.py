# -*- coding: utf-8 -*-
"""认证与用户管理路由（MySQL 版，脱离 Dify —— JWT 认证）

说明：
    - dify_accounts 为用户主表（认证 + 基本信息 + 电话）
    - user_roles 直接关联 dify_accounts.id（不再需要 users 中间表）
    - roles / permissions 表保持不变
"""

import uuid
from datetime import datetime
from flask import jsonify, request
from config import get_db
from utils.helpers import (now, _generate_password, _compare_password, _valid_password,
                           _needs_rehash, _check_account_identity)
from utils.auth import (
    generate_token_pair,
    refresh_access_token,
    verify_token,
    extract_token_from_request,
    login_required,
    role_required,
    revoke_token,
    get_account_role,
    platform_admin_required,
)
from utils.login_lockout import (
    record_login_failure,
    check_login_allowed,
    lock_account,
    unlock_account,
    get_lock_status,
    get_failure_count,
)
from models.tables import (
    DIFY_ACCOUNTS_TABLE_SQL,
    DIFY_TENANTS_TABLE_SQL,
    DIFY_TENANT_ACCOUNT_JOINS_TABLE_SQL,
    ROLES_TABLE_SQL,
    USER_ROLES_TABLE_SQL,
    PERMISSIONS_TABLE_SQL,
    ROLE_PERMISSIONS_TABLE_SQL,
)
from routes.audit import log_audit_event


def _get_register_policy(cur):
    """读取注册策略（存于 system_settings 表），返回 (allow_register: bool, invite_code: str)。

    - allow_register：管理员在系统设置中开关；存 '0'/'false'/'off' 视为关闭，缺省视为开放（与历史行为一致）。
    - register_invite_code：非空则注册必须携带匹配的邀请码；为空则不需邀请码。
    读取失败（如表尚未创建）时回退为默认开放，避免因配置缺失锁死注册。
    """
    allow = True
    invite = ''
    try:
        cur.execute(r"SELECT `value` FROM system_settings WHERE `key` = 'allow_register'")
        row = cur.fetchone()
        if row is not None and str(row['value']).strip().lower() in ('0', 'false', 'off'):
            allow = False
        cur.execute(r"SELECT `value` FROM system_settings WHERE `key` = 'register_invite_code'")
        irow = cur.fetchone()
        if irow is not None:
            invite = (irow['value'] or '').strip()
    except Exception:
        pass
    return allow, invite


def _ensure_auth_tables():
    """确保认证相关表已创建"""
    try:
        db = get_db()
        try:
            cur = db.cursor()
            # Dify 兼容表
            cur.execute(DIFY_ACCOUNTS_TABLE_SQL)
            cur.execute(DIFY_TENANTS_TABLE_SQL)
            cur.execute(DIFY_TENANT_ACCOUNT_JOINS_TABLE_SQL)
            # 角色权限表
            cur.execute(ROLES_TABLE_SQL)
            cur.execute(USER_ROLES_TABLE_SQL)
            cur.execute(PERMISSIONS_TABLE_SQL)
            cur.execute(ROLE_PERMISSIONS_TABLE_SQL)
            db.commit()
        finally:
            db.close()
    except Exception:
        # 表创建失败不影响主流程（可能已存在）
        pass


def _init_default_admin():
    """初始化默认管理员角色"""
    try:
        db = get_db()
        try:
            cur = db.cursor()
            # 创建默认角色
            cur.execute(r"INSERT IGNORE INTO roles (name, description) VALUES ('admin', '系统管理员')")
            cur.execute(r"INSERT IGNORE INTO roles (name, description) VALUES ('user', '普通用户')")

            # 为 yutaiyin 赋予 admin 角色
            cur.execute(r'''
                INSERT IGNORE INTO user_roles (user_id, role_id)
                SELECT da.id, r.id
                FROM dify_accounts da, roles r
                WHERE da.name = 'yutaiyin' AND r.name = 'admin'
            ''')
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def register_auth_routes(app):
    """注册用户/角色/权限/登录相关路由"""

    # ═══════════════════════════════════════════
    #  OAuth / SSO 登录
    # ═══════════════════════════════════════════

    @app.route('/api/oauth/providers', methods=['GET'])
    def oauth_providers():
        """获取已启用的 OAuth 提供商列表"""
        from utils.oauth_user import get_available_oauth_providers
        providers = get_available_oauth_providers()
        return jsonify(code=200, data=providers)

    @app.route('/api/oauth/authorize/<provider>', methods=['GET'])
    def oauth_user_authorize(provider):
        """
        发起 OAuth 授权（Step 1: 重定向到提供商登录页）

        查询参数:
            redirect_url: 登录成功后的跳转地址（可选）

        响应:
            302 重定向到 OAuth 提供商
            或 400 { msg: '未配置的提供商' }
        """
        from utils.oauth_user import build_authorize_url
        redirect_url = request.args.get('redirect_url', '')
        url, state = build_authorize_url(provider)
        if not url:
            return jsonify(code=400, msg=f'OAuth 提供商 {provider} 未配置或未启用'), 400

        # 将 state 和 redirect_url 存入 session（或临时 token）
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''INSERT INTO oauth_states (state, provider, redirect_url, created_at, expires_at)
                    VALUES (%s, %s, %s(), NOW(), DATE_ADD(NOW(), INTERVAL 10 MINUTE))
                    ON DUPLICATE KEY UPDATE provider = VALUES(provider), redirect_url = VALUES(redirect_url), created_at = NOW()''',
                (state, provider, redirect_url))
            db.commit()
        except Exception:
            # 表可能不存在，使用内存存储
            pass
        finally:
            db.close()

        return redirect(url)

    @app.route('/api/oauth/callback/<provider>', methods=['GET'])
    def oauth_user_callback(provider):
        """
        OAuth 回调处理（Step 2: 提供商重定向回本站）

        查询参数:
            code: 授权码
            state: 防 CSRF 参数

        响应:
            成功: 302 redirect_url#access_token=xxx&refresh_token=yyy
            失败: 400 { msg: '错误信息' }
        """
        from utils.oauth_user import oauth_login
        code = request.args.get('code', '')
        state = request.args.get('state', '')

        if not code:
            return jsonify(code=400, msg='缺少授权码'), 400

        token_pair, err = oauth_login(provider, code, state)
        if err:
            return jsonify(code=400, msg=err), 400

        # 获取 redirect_url
        redirect_url = request.args.get('redirect_url', '/')
        # 将 token 附加到 redirect URL
        import urllib.parse
        separator = '&' if '?' in redirect_url else '?'
        token_params = urllib.parse.urlencode({
            'access_token': token_pair['access_token'],
            'refresh_token': token_pair['refresh_token'],
        })
        return redirect(f'{redirect_url}{separator}{token_params}')

    # ═══════════════════════════════════════════
    #  注册 / 密码重置 / 系统设置
    # ═══════════════════════════════════════════

    @app.route('/api/register', methods=['POST'])
    def register():
        """
        用户注册 —— 自助注册账号

        请求体: { username, password, email, nickname(可选) }
        响应: { code: 200, data: { id, username, email } }

        安全特性:
        - 密码强度校验（8位+字母+数字）
        - 邮箱唯一性校验
        - 自动分配 'user' 角色
        - 创建专属工作区
        """
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')

        # 注册管控：是否开放自助注册 / 邀请码（读 system_settings）
        _db = get_db()
        try:
            allow_register, invite_code_required = _get_register_policy(_db.cursor())
        finally:
            _db.close()
        if not allow_register:
            return jsonify(code=403, msg='系统已关闭自助注册，请联系管理员开通')

        username = d.get('username', '').strip()
        password = d.get('password', '')
        email = (d.get('email') or '').strip().lower()
        nickname = (d.get('nickname') or username).strip()

        if not username or not password:
            return jsonify(code=400, msg='用户名和密码为必填项')
        if not email:
            return jsonify(code=400, msg='邮箱为必填项')
        if not _valid_password(password):
            return jsonify(code=400, msg='密码至少 8 位且需同时包含字母和数字')
        if invite_code_required:
            supplied_invite = (d.get('invite_code') or '').strip()
            if supplied_invite != invite_code_required:
                return jsonify(code=400, msg='邀请码缺失或错误')

        # 账号名/邮箱唯一性（含“你的账号名是别人的邮箱”这种跨列撞车）
        db = get_db()
        try:
            err = _check_account_identity(db.cursor(), username, email)
        finally:
            db.close()
        if err:
            return jsonify(code=400, msg=err)

        # 创建账号
        salt_b64, pwd_b64 = _generate_password(password)
        account_uuid = str(uuid.uuid4())
        tenant_uuid = str(uuid.uuid4())
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO dify_accounts
                            (id, name, nickname, email, password, password_salt,
                             interface_language, interface_theme, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, 'zh-Hans', 'light', 'active', %s, %s)''',
                        (account_uuid, username, nickname, email, pwd_b64, salt_b64, ts, ts))
            cur.execute(r'''INSERT INTO dify_tenants (id, name, plan, status, created_at, updated_at)
                            VALUES (%s, %s, 'basic', 'normal', %s, %s)''',
                        (tenant_uuid, username + "'s Workspace", ts, ts))
            cur.execute(r'''INSERT INTO dify_tenant_account_joins
                            (tenant_id, account_id, role, current, created_at, updated_at)
                            VALUES (%s, %s, 'owner', true, %s, %s)''',
                        (tenant_uuid, account_uuid, ts, ts))
            # 分配默认 'user' 角色
            cur.execute(r"SELECT id FROM roles WHERE name = 'user'")
            role = cur.fetchone()
            if role:
                cur.execute(r'INSERT INTO user_roles (user_id, role_id, created_at) VALUES (%s, %s, %s)',
                            (account_uuid, role['id'], ts))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='注册失败: %s' % e)
        finally:
            db.close()

        log_audit_event(
            action='register',
            resource_type='user',
            resource_id=account_uuid,
            resource_name=username,
            description=f'用户注册: {username}',
            status='success',
            request_obj=request,
            response_code=200,
        )
        return jsonify(code=200, msg='注册成功', data={
            'id': account_uuid, 'username': username, 'email': email
        })

    @app.route('/api/register-config', methods=['GET'])
    def register_config():
        """注册页配置（公开，无需登录）。

        前端据此决定是否展示注册表单及邀请码输入框；不返回邀请码明文。
        响应: { code: 200, data: { allow_register, require_invite_code } }
        """
        db = get_db()
        try:
            allow_register, invite_code = _get_register_policy(db.cursor())
        finally:
            db.close()
        return jsonify(code=200, data={
            'allow_register': bool(allow_register),
            'require_invite_code': bool(invite_code),
        })

    @app.route('/api/password/forgot', methods=['POST'])
    def forgot_password():
        """
        忘记密码 —— 发送重置邮件

        请求体: { email }
        响应: { code: 200, msg: '重置链接已发送到邮箱' }

        安全特性:
        - 无论邮箱是否存在，返回相同提示（防止枚举）
        - 生成一次性重置 token（1小时有效）
        - 通过 SMTP 发送重置邮件
        """
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')
        email = (d.get('email') or '').strip().lower()
        if not email:
            return jsonify(code=400, msg='请填写邮箱')

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT id, name FROM dify_accounts WHERE email = %s AND status = %s', (email, 'active'))
            acc = cur.fetchone()
            if acc:
                # 生成重置 token
                reset_token = secrets.token_urlsafe(32)
                expires_at = datetime.now().timestamp() + 3600  # 1小时
                cur.execute(r'''CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    token VARCHAR(128) NOT NULL,
                    expires_at DOUBLE NOT NULL,
                    used TINYINT DEFAULT 0,
                    created_at DOUBLE DEFAULT (UNIX_TIMESTAMP())
                )''')
                cur.execute(r'''INSERT INTO password_reset_tokens (id, user_id, token, expires_at)
                    VALUES (%s, %s, %s, %s)''',
                    (str(uuid.uuid4()), str(acc['id']), reset_token, expires_at))
                db.commit()
                # 尝试发送邮件
                try:
                    from utils.smtp import send_reset_email
                    send_reset_email(email, acc['name'], reset_token)
                except Exception:
                    pass  # SMTP 未配置时不阻塞
        except Exception:
            pass
        finally:
            db.close()

        # 统一返回（防止邮箱枚举）
        return jsonify(code=200, msg='如果该邮箱已注册，重置链接将发送到您的邮箱')

    @app.route('/api/password/reset', methods=['POST'])
    def reset_password():
        """
        重置密码 —— 使用 token 设置新密码

        请求体: { token, new_password }
        响应: { code: 200, msg: '密码重置成功' }
        """
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')
        token = d.get('token', '').strip()
        new_password = d.get('new_password', '')
        if not token:
            return jsonify(code=400, msg='缺少重置令牌')
        if not _valid_password(new_password):
            return jsonify(code=400, msg='密码至少 8 位且需同时包含字母和数字')

        db = get_db()
        try:
            cur = db.cursor()
            # 确保表存在
            cur.execute(r'''CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                token VARCHAR(128) NOT NULL,
                expires_at DOUBLE NOT NULL,
                used TINYINT DEFAULT 0,
                created_at DOUBLE DEFAULT (UNIX_TIMESTAMP())
            )''')
            cur.execute(r'''SELECT user_id, token, expires_at, used FROM password_reset_tokens
                WHERE token = %s AND used = 0 AND expires_at > %s
                ORDER BY created_at DESC LIMIT 1''',
                (token, datetime.now().timestamp()))
            row = cur.fetchone()
            if not row:
                return jsonify(code=400, msg='重置链接无效或已过期')

            # 更新密码
            salt_b64, pwd_b64 = _generate_password(new_password)
            cur.execute(r'UPDATE dify_accounts SET password = %s, password_salt = %s WHERE id = %s',
                        (pwd_b64, salt_b64, row['user_id']))
            # 标记 token 已使用
            cur.execute(r'UPDATE password_reset_tokens SET used = 1 WHERE token = %s', (token,))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='重置失败: %s' % e)
        finally:
            db.close()

        return jsonify(code=200, msg='密码重置成功，请使用新密码登录')

    @app.route('/api/system/settings', methods=['GET'])
    @login_required
    @role_required('admin')
    def get_system_settings():
        """
        获取系统设置（管理员）

        返回: SMTP 配置、站点设置、功能开关
        """
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT `key`, `value`, description FROM system_settings ORDER BY `key`')
            rows = cur.fetchall()
            settings = {}
            for row in rows:
                k = row['key'] if 'key' in row else row[0]
                v = row['value'] if 'value' in row else row[1]
                settings[k] = v
            # 脱敏 SMTP 密码
            if settings.get('smtp_password'):
                settings['smtp_password'] = '********'
                settings['smtp_configured'] = '1'
            return jsonify(code=200, data=settings)
        except Exception as e:
            return jsonify(code=500, msg='读取设置失败: %s' % e)
        finally:
            db.close()

    @app.route('/api/system/settings', methods=['PUT'])
    @login_required
    @role_required('admin')
    def save_system_settings():
        """
        保存系统设置（管理员）

        请求体: { key_name: key_value, ... }
        支持: smtp_host, smtp_port, smtp_user, smtp_password, smtp_from, site_name, ...
        """
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')

        db = get_db()
        try:
            cur = db.cursor()
            for key, value in d.items():
                if value is None:
                    continue
                cur.execute(r'''INSERT INTO system_settings (`key`, `value`, updated_at)
                    VALUES (%s, %s, NOW())
                    ON DUPLICATE KEY UPDATE `value` = VALUES(`value`), updated_at = NOW()''',
                    (key, str(value)))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='保存设置失败: %s' % e)
        finally:
            db.close()

        log_audit_event(
            action='update_system_settings',
            resource_type='system',
            resource_name='settings',
            description='更新系统设置',
            status='success',
            request_obj=request,
            response_code=200,
        )
        return jsonify(code=200, msg='设置保存成功')

    # ==================== SMTP 配置管理 ====================

    @app.route('/api/system/smtp', methods=['GET'])
    @login_required
    @role_required('admin')
    def get_smtp_config():
        """获取 SMTP 配置（隐藏密码）"""
        try:
            from engine.human_input_delivery import get_smtp_config as _get
            cfg = _get()
            if not cfg:
                return jsonify(code=200, data=None)
            # 隐藏密码
            if 'password' in cfg:
                cfg['password'] = '******' if cfg['password'] else ''
            return jsonify(code=200, data=cfg)
        except Exception as e:
            return jsonify(code=500, msg='获取配置失败: ' + str(e))

    @app.route('/api/system/smtp', methods=['POST'])
    @login_required
    @role_required('admin')
    def set_smtp_config():
        """设置 SMTP 配置"""
        from engine.human_input_delivery import set_smtp_config as _set, get_smtp_config as _get
        body = request.json or {}
        host = (body.get('host') or '').strip()
        if not host:
            return jsonify(code=400, msg='SMTP 服务器地址不能为空')

        config = {
            'host': host,
            'port': int(body.get('port', 587)),
            'username': (body.get('username') or '').strip(),
            'password': body.get('password', ''),
            'use_tls': body.get('use_tls', True),
            'from_email': (body.get('from_email') or body.get('username') or '').strip(),
            'from_name': (body.get('from_name') or '熵舟智能体工作台').strip(),
        }

        # 如果密码是掩码，保留原密码
        if config['password'] == '******':
            old_cfg = _get()
            if old_cfg:
                config['password'] = old_cfg.get('password', '')

        ok = _set(config)
        if not ok:
            return jsonify(code=500, msg='保存配置失败')
        return jsonify(code=200, msg='保存成功')

    @app.route('/api/system/smtp/test', methods=['POST'])
    @login_required
    @role_required('admin')
    def test_smtp_connection():
        """
        测试 SMTP 连接

        请求体: { smtp_host, smtp_port, smtp_user, smtp_password, smtp_from, to_email }
        响应: { code: 200, msg: '测试邮件已发送' } 或 { code: 400, msg: '连接失败: ...' }
        """
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')
        try:
            from utils.smtp import test_smtp_connection
            result = test_smtp_connection(d)
            return jsonify(code=200, msg='测试邮件已发送，请查收')
        except Exception as e:
            return jsonify(code=400, msg='SMTP 测试失败: %s' % str(e))

    # ═══════════════════════════════════════════
    #  USERS（dify_accounts 为唯一用户表）
    # ═══════════════════════════════════════════

    # 用户与角色是平台管理面：只能登录 + 只能管理员。以前这组接口只被集中闸门
    # 挡了一道（= 任何登录用户可用），等于人人都能拉到全体账号的邮箱/手机号，
    # 还能 POST /api/users 建个 role=admin 的号、PUT /api/users/<id> 改任何人密码、
    # PUT /api/roles/<id>/permissions 给自己加权 —— 账号接管与提权一条路走完。
    @app.route('/api/users', methods=['GET'])
    @platform_admin_required
    def get_users():
        """用户列表：直接从 dify_accounts 查询，角色通过 user_roles 关联"""
        _ensure_auth_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''
                SELECT da.id, da.name, da.nickname, da.email, da.phone, da.status, da.created_at,
                       COALESCE(GROUP_CONCAT(r.name SEPARATOR ', '), '') AS role_name
                FROM dify_accounts da
                LEFT JOIN user_roles ur ON ur.user_id = da.id
                LEFT JOIN roles r ON r.id = ur.role_id
                WHERE da.status = 'active'
                GROUP BY da.id
                ORDER BY da.created_at DESC
            ''')
            rows = cur.fetchall()
            data = []
            for row in rows:
                data.append({
                    'id': str(row['id']),
                    'username': row['name'],
                    'nickname': row['nickname'] or '',
                    'email': row['email'] or '',
                    'phone': row['phone'] or '',
                    'status': 1 if row['status'] == 'active' else 0,
                    'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else '',
                    'role_name': row['role_name'] or '',
                })
            return jsonify(code=200, data=data)
        except Exception as e:
            return jsonify(code=500, msg='读取用户失败: %s' % e)
        finally:
            db.close()

    def _dify_account_by_id(aid):
        """按 dify account uuid 查询账号"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT id, name, nickname, email, phone, status FROM dify_accounts WHERE id = %s', (aid,))
            return cur.fetchone()
        finally:
            db.close()

    @app.route('/api/users', methods=['POST'])
    @platform_admin_required
    def create_user():
        """创建用户"""
        _ensure_auth_tables()
        d = request.get_json()
        username = d.get('username', '').strip()
        nickname = d.get('nickname', '').strip()
        password = d.get('password', '')
        email = (d.get('email') or '').strip().lower()
        phone = d.get('phone', '').strip()
        role_name = d.get('role', '').strip()

        if not username or not password:
            return jsonify(code=400, msg='用户名和密码为必填项')
        if not email:
            return jsonify(code=400, msg='邮箱为必填项')
        if not _valid_password(password):
            return jsonify(code=400, msg='密码至少 8 位且需同时包含字母和数字')

        # 检查是否已存在（账号名/邮箱交叉唯一，见 utils.helpers._check_account_identity）
        db = get_db()
        try:
            err = _check_account_identity(db.cursor(), username, email)
        finally:
            db.close()
        if err:
            return jsonify(code=400, msg=err + '，请更换')

        salt_b64, pwd_b64 = _generate_password(password)
        account_uuid = str(uuid.uuid4())
        tenant_uuid = str(uuid.uuid4())
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 1) 创建 dify 账号 + 专属工作区
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO dify_accounts (id, name, nickname, email, phone, password, password_salt,
                                                   interface_language, interface_theme, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, 'zh-Hans', 'light', 'active', %s, %s)''',
                        (account_uuid, username, nickname, email, phone, pwd_b64, salt_b64, ts, ts))
            cur.execute(r'''INSERT INTO dify_tenants (id, name, plan, status, created_at, updated_at)
                            VALUES (%s, %s, 'basic', 'normal', %s, %s)''',
                        (tenant_uuid, username + "'s Workspace", ts, ts))
            cur.execute(r'''INSERT INTO dify_tenant_account_joins (tenant_id, account_id, role, current, created_at, updated_at)
                            VALUES (%s, %s, 'owner', true, %s, %s)''', (tenant_uuid, account_uuid, ts, ts))

            # 2) 分配角色
            if role_name:
                cur.execute(r'SELECT id FROM roles WHERE name = %s', (role_name,))
                role = cur.fetchone()
                if role:
                    cur.execute(
                        r'INSERT INTO user_roles (user_id, role_id, created_at) VALUES (%s, %s, %s)',
                        (account_uuid, role['id'], ts)
                    )
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='创建账号失败: %s' % e)
        finally:
            db.close()
        return jsonify(code=200, msg='创建成功', data={'id': account_uuid})

    @app.route('/api/users/<uid>', methods=['PUT'])
    @platform_admin_required
    def update_user(uid):
        """更新用户"""
        _ensure_auth_tables()
        d = request.get_json()
        acct = _dify_account_by_id(uid)
        if not acct:
            return jsonify(code=404, msg='账号不存在')
        email = (d.get('email') or acct['email'] or '').strip().lower()
        username = (d.get('username') or acct['name'] or '').strip()
        nickname = d.get('nickname', acct['nickname'] or '')
        phone = d.get('phone', acct['phone'] or '')
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        db = get_db()
        try:
            cur = db.cursor()
            # 改名/改邮箱也要守全局唯一（排除自己），否则管理员可以把别人的账号名
            # 改成某个已存在的邮箱，把登录匹配（name OR email）弄成歧义
            err = _check_account_identity(cur, username, email, exclude_id=uid)
            if err:
                return jsonify(code=400, msg=err)
            # 更新 dify_accounts
            cur.execute(r'''UPDATE dify_accounts SET name = %s, nickname = %s, email = %s, phone = %s, updated_at = %s WHERE id = %s''',
                        (username, nickname, email, phone, ts, uid))
            # 更新密码
            if 'password' in d and d['password']:
                if not _valid_password(d['password']):
                    return jsonify(code=400, msg='密码至少 8 位且需同时包含字母和数字')
                salt_b64, pwd_b64 = _generate_password(d['password'])
                cur.execute(r'UPDATE dify_accounts SET password = %s, password_salt = %s WHERE id = %s',
                            (pwd_b64, salt_b64, uid))
            # 更新状态
            if 'status' in d:
                cur.execute(r'UPDATE dify_accounts SET status = %s WHERE id = %s',
                            ('active' if d['status'] == 1 else 'banned', uid))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='更新账号失败: %s' % e)
        finally:
            db.close()
        return jsonify(code=200, msg='更新成功')

    @app.route('/api/users/<uid>', methods=['DELETE'])
    @platform_admin_required
    def delete_user(uid):
        """删除用户"""
        _ensure_auth_tables()
        acct = _dify_account_by_id(uid)
        if not acct:
            return jsonify(code=404, msg='账号不存在')
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        db = get_db()
        try:
            cur = db.cursor()
            # 1) 解绑工作区并禁用账号
            cur.execute(r'DELETE FROM dify_tenant_account_joins WHERE account_id = %s', (uid,))
            cur.execute(r"UPDATE dify_accounts SET status = 'banned', updated_at = %s WHERE id = %s", (ts, uid))
            # 2) 删除角色关联
            cur.execute(r'DELETE FROM user_roles WHERE user_id = %s', (uid,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/users/<uid>/roles', methods=['PUT'])
    @platform_admin_required
    def set_user_role(uid):
        """设置用户角色"""
        _ensure_auth_tables()
        d = request.get_json()
        role_name = d.get('role', '').strip()
        acct = _dify_account_by_id(uid)
        if not acct:
            return jsonify(code=404, msg='账号不存在')

        db = get_db()
        try:
            cur = db.cursor()
            # 删除旧角色
            cur.execute(r'DELETE FROM user_roles WHERE user_id = %s', (uid,))
            # 分配新角色
            if role_name:
                cur.execute(r'SELECT id FROM roles WHERE name = %s', (role_name,))
                role = cur.fetchone()
                if role:
                    cur.execute(
                        r'INSERT INTO user_roles (user_id, role_id, created_at) VALUES (%s, %s, %s)',
                        (uid, role['id'], now())
                    )
            db.commit()
            return jsonify(code=200, msg='角色设置成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ═══════════════════════════════════════════
    #  ROLES
    # ═══════════════════════════════════════════

    @app.route('/api/roles', methods=['GET'])
    def get_roles():
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''
                SELECT r.id, r.name, r.description, r.status, r.created_at, r.updated_at,
                       COUNT(ur.id) AS user_count
                FROM roles r
                LEFT JOIN user_roles ur ON ur.role_id = r.id
                GROUP BY r.id
                ORDER BY r.created_at
            ''')
            rows = cur.fetchall()
            for r in rows:
                if r['created_at']:
                    r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if r['updated_at']:
                    r['updated_at'] = r['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, data=rows)
        finally:
            db.close()

    @app.route('/api/roles', methods=['POST'])
    @platform_admin_required
    def create_role():
        d = request.get_json()
        name = d.get('name', '').strip()
        desc = d.get('description', '').strip()
        if not name:
            return jsonify(code=400, msg='角色名称为必填项')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''INSERT INTO roles (name, description, status, created_at, updated_at)
                    VALUES (%s, %s, 1, %s, %s)''',
                (name, desc, now(), now())
            )
            db.commit()
            return jsonify(code=200, msg='创建成功', data={'id': cur.lastrowid})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/roles/<int:rid>', methods=['PUT'])
    @platform_admin_required
    def update_role(rid):
        d = request.get_json()
        db = get_db()
        try:
            cur = db.cursor()
            name = d.get('name', '').strip()
            desc = d.get('description', '').strip()
            cur.execute(
                r'UPDATE roles SET name = %s, description = %s, updated_at = %s WHERE id = %s',
                (name, desc, now(), rid)
            )
            db.commit()
            return jsonify(code=200, msg='更新成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/roles/<int:rid>', methods=['DELETE'])
    @platform_admin_required
    def delete_role(rid):
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM user_roles WHERE role_id = %s', (rid,))
            cur.execute(r'DELETE FROM role_permissions WHERE role_id = %s', (rid,))
            cur.execute(r'DELETE FROM roles WHERE id = %s', (rid,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ═══════════════════════════════════════════
    #  PERMISSIONS
    # ═══════════════════════════════════════════

    @app.route('/api/permissions', methods=['GET'])
    def get_permissions():
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM permissions ORDER BY module, id')
            rows = cur.fetchall()
            for r in rows:
                if r['created_at']:
                    r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, data=rows)
        finally:
            db.close()

    # ═══════════════════════════════════════════
    #  ROLE-PERMISSIONS
    # ═══════════════════════════════════════════

    @app.route('/api/roles/<int:rid>/permissions', methods=['GET'])
    def get_role_permissions(rid):
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''
                SELECT p.id, p.name, p.code, p.module
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = %s
            ''', (rid,))
            rows = cur.fetchall()
            return jsonify(code=200, data=rows)
        finally:
            db.close()

    @app.route('/api/roles/<int:rid>/permissions', methods=['PUT'])
    @platform_admin_required
    def save_role_permissions(rid):
        d = request.get_json()
        perm_ids = d.get('permission_ids', [])
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM role_permissions WHERE role_id = %s', (rid,))
            for pid in perm_ids:
                cur.execute(
                    r'INSERT INTO role_permissions (role_id, permission_id, created_at) VALUES (%s, %s, %s)',
                    (rid, pid, now())
                )
            db.commit()
            return jsonify(code=200, msg='权限保存成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ═══════════════════════════════════════════
    #  LOGIN / REFRESH / LOGOUT / ME
    # ═══════════════════════════════════════════

    @app.route('/api/login', methods=['POST'])
    def login():
        """
        用户登录 —— 返回 JWT Token 对（Access + Refresh）

        请求体: { username, password }
        响应: { code: 200, data: { user, access_token, refresh_token, token_type, expires_in } }

        安全特性:
        - 登录失败锁定（5次→15分钟，10次→1小时，20次→24小时）
        - IP 失败锁定（20次→30分钟，50次→2小时）
        - 渐进式延迟响应
        """
        try:
            _ensure_auth_tables()
            _init_default_admin()
            d = request.get_json()
            if not d:
                return jsonify(code=400, msg='请求体不能为空')
            username = d.get('username', '').strip()
            password = d.get('password', '').strip()
            if not username or not password:
                return jsonify(code=400, msg='请输入账号和密码')

            # ===== 登录失败锁定检查 =====
            allowed, lock_message = check_login_allowed(username)
            if not allowed:
                log_audit_event(
                    action='login_blocked',
                    resource_type='user',
                    resource_name=username,
                    description=f'登录被锁定: {username}',
                    status='blocked',
                    error_message=lock_message,
                    request_obj=request,
                    response_code=423,
                )
                return jsonify(code=423, msg=lock_message), 423

            # 1. 从 dify_accounts 查询用户
            db = get_db()
            try:
                cur = db.cursor()
                # 允许用「账号名」或「邮箱」登录，但必须让账号名精确匹配优先：
                # 否则当他人邮箱恰好等于某个账号名时（如 email='yutaiyin'），
                # 无 ORDER BY 的 LIMIT 1 会随机命中另一行，导致“密码正确却 401”。
                cur.execute(r'''
                    SELECT id, name, nickname, email, phone, password, password_salt, status,
                           interface_language, interface_theme, created_at
                    FROM dify_accounts
                    WHERE name = %s OR email = %s
                    ORDER BY (name = %s) DESC
                    LIMIT 1
                ''', (username, username, username))
                acc = cur.fetchone()
            finally:
                db.close()

            if not acc:
                # 记录失败并检查是否需要锁定
                record_login_failure(username)
                lock_account(username)
                failures = get_failure_count(username)
                remaining = max(0, 5 - failures.get('username_count', 0))
                msg = '账号或密码错误'
                if remaining > 0 and remaining < 5:
                    msg += f'，还可尝试 {remaining} 次'
                return jsonify(code=401, msg=msg)

            if acc['status'] != 'active':
                return jsonify(code=403, msg='账号已被禁用，请联系管理员')

            # 2. 验证密码
            if not _compare_password(password, acc['password'], acc['password_salt']):
                # 记录失败并检查是否需要锁定
                record_login_failure(username)
                lock_result = lock_account(username)
                failures = get_failure_count(username)
                remaining = max(0, 5 - failures.get('username_count', 0))

                log_audit_event(
                    action='login_failed',
                    resource_type='user',
                    resource_id=str(acc['id']),
                    resource_name=acc['name'] or '',
                    description=f'登录失败: {username} (第{failures.get("username_count", 0)}次)',
                    status='failed',
                    error_message='密码错误',
                    user_id=str(acc['id']),
                    user_name=acc['name'] or '',
                    user_email=acc['email'] or '',
                    request_obj=request,
                    response_code=401,
                )

                msg = '账号或密码错误'
                if remaining > 0 and remaining < 5:
                    msg += f'，还可尝试 {remaining} 次'
                elif lock_result.get('username_locked'):
                    duration = lock_result.get('username_duration', 0)
                    if duration >= 3600:
                        msg = f'账号已锁定，请 {duration // 3600} 小时后再试'
                    else:
                        msg = f'账号已锁定，请 {duration // 60} 分钟后再试'

                return jsonify(code=401, msg=msg)

            # 2.5 自动升级密码哈希（旧版 PBKDF2 → Argon2id）
            if _needs_rehash(acc['password'], acc['password_salt']):
                try:
                    new_salt, new_pwd = _generate_password(password, use_argon2=True)
                    db2 = get_db()
                    try:
                        cur2 = db2.cursor()
                        cur2.execute(
                            r'UPDATE dify_accounts SET password = %s, password_salt = %s WHERE id = %s',
                            (new_pwd, new_salt, acc['id'])
                        )
                        db2.commit()
                    finally:
                        db2.close()
                except Exception:
                    pass  # 升级失败不影响登录

            # 3. 角色与权限级别：判定口径全后端只有一处（utils/auth.get_account_role）。
            #    以前这里自己写了句 'admin' in role_name.lower() or '管理员' in role_name，
            #    而 roles 表里同时有遗留的“运维管理员/业务管理员/普通用户”：按子串猜会把
            #    “业务管理员”也提成 admin，而 token 里的 role=admin 是 api_guard/ownership
            #    跳过归属校验、前端放行管理员菜单的凭据 —— 等于静默提权。
            role_info = get_account_role(acc['id'])
            role_name = role_info['role_name']
            role_level = role_info['level']

            # 5. 生成 JWT Token 对
            tokens = generate_token_pair(
                user_id=str(acc['id']),
                email=acc['email'] or '',
                username=acc['name'] or '',
                role=role_level,
            )

            # 6. 格式化用户信息
            created_at = acc['created_at']
            if created_at and hasattr(created_at, 'strftime'):
                created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')

            user_info = {
                'id': str(acc['id']),
                'username': acc['name'] or '',
                'nickname': acc['nickname'] or '',
                'email': acc['email'] or '',
                'phone': acc['phone'] or '',
                'role_name': role_name,
                'role': role_level,
                'interface_language': acc['interface_language'] or 'zh-Hans',
                'interface_theme': acc['interface_theme'] or 'light',
                'created_at': created_at or '',
            }

            # 7. 记录登录成功
            log_audit_event(
                action='login',
                resource_type='user',
                resource_id=str(acc['id']),
                resource_name=acc['name'] or '',
                description=f'用户登录成功: {acc["name"]}',
                status='success',
                user_id=str(acc['id']),
                user_name=acc['name'] or '',
                user_email=acc['email'] or '',
                request_obj=request,
                response_code=200,
            )

            return jsonify(code=200, msg='登录成功', data={
                'user': user_info,
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'token_type': tokens['token_type'],
                'expires_in': tokens['expires_in'],
            })
        except Exception as e:
            import logging
            logging.error(f'登录异常: {str(e)}', exc_info=True)
            return jsonify(code=500, msg='登录失败，请稍后重试')

    @app.route('/api/refresh', methods=['POST'])
    def refresh_token():
        """
        刷新 Access Token —— 使用 Refresh Token 换取新的 Token 对

        请求体: { refresh_token }
        响应: { code: 200, data: { access_token, refresh_token, token_type, expires_in } }
        """
        d = request.get_json()
        refresh_tk = d.get('refresh_token', '').strip()
        if not refresh_tk:
            return jsonify(code=400, msg='缺少 refresh_token')
        new_tokens, error = refresh_access_token(refresh_tk)
        if error:
            return jsonify(code=401, msg=error)
        return jsonify(code=200, msg='刷新成功', data={
            'access_token': new_tokens['access_token'],
            'refresh_token': new_tokens['refresh_token'],
            'token_type': new_tokens['token_type'],
            'expires_in': new_tokens['expires_in'],
        })

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def logout():
        """
        用户登出 —— 吊销当前 Access Token

        请求头: Authorization: Bearer <token>
        响应: { code: 200, msg: '已退出登录' }
        """
        token = extract_token_from_request()
        if token:
            revoke_token(token)
        log_audit_event(
            action='logout',
            resource_type='user',
            description='用户登出',
            status='success',
            request_obj=request,
            response_code=200,
        )
        return jsonify(code=200, msg='已退出登录')

    @app.route('/api/me', methods=['GET'])
    @login_required
    def get_current_user_info():
        """
        获取当前登录用户信息

        请求头: Authorization: Bearer <token>
        响应: { code: 200, data: { user_id, email, username, role } }
        """
        user = request.user
        return jsonify(code=200, data=user)

    # ═══════════════════════════════════════════
    #  登录锁定管理（管理员）
    # ═══════════════════════════════════════════

    @app.route('/api/admin/lockout/status', methods=['GET'])
    @login_required
    @role_required('admin')
    def get_lockout_status():
        """
        查询登录锁定状态

        查询参数:
            username: 用户名（可选）
            ip: IP 地址（可选）
        """
        username = request.args.get('username', '').strip()
        ip = request.args.get('ip', '').strip()
        status = get_lock_status(username, ip if ip else None)
        return jsonify(code=200, data=status)

    @app.route('/api/admin/lockout/unlock', methods=['POST'])
    @login_required
    @role_required('admin')
    def admin_unlock_account():
        """
        手动解锁账号（管理员）

        请求体:
            { username: str, ip: str }
        """
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')

        username = d.get('username', '').strip()
        ip = d.get('ip', '').strip()

        if not username and not ip:
            return jsonify(code=400, msg='请提供 username 或 ip')

        result = unlock_account(username, ip if ip else None)

        # 记录审计日志
        log_audit_event(
            action='unlock_account',
            resource_type='user',
            resource_name=username or ip,
            description=f'管理员手动解锁: {username or ip}',
            status='success',
            user_id=request.user.get('user_id'),
            user_name=request.user.get('username'),
            request_obj=request,
            response_code=200,
        )

        return jsonify(code=200, msg='解锁成功', data=result)
