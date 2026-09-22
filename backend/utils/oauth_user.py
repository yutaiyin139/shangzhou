# -*- coding: utf-8 -*-
"""
用户 OAuth/SSO 登录框架（对齐 Dify 社交登录设计）

支持提供商：
- Google (OAuth 2.0)
- GitHub (OAuth 2.0)
- 通用 OAuth 2.0 / OIDC 提供商

架构：
- 配置存储：system_settings 表（oauth_providers JSON）
- 流程：authorize URL → 回调 → code 换 token → 获取用户信息 → 创建/绑定本地用户 → 签发 JWT
"""
import os
import json
import time
import uuid
import secrets
import hashlib
from datetime import datetime
import requests as http_requests
from urllib.parse import urlencode
from functools import wraps
from flask import request, jsonify, redirect, session

from config import get_db
from utils.auth import generate_token_pair


# ============================================================
# 提供商配置
# ============================================================

# 内置提供商模板（用户只需填写 client_id 和 client_secret）
OAUTH_PROVIDERS = {
    'google': {
        'label': 'Google',
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'userinfo_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
        'scope': 'openid email profile',
        'icon': '🔵',
    },
    'github': {
        'label': 'GitHub',
        'authorize_url': 'https://github.com/login/oauth/authorize',
        'token_url': 'https://github.com/login/oauth/access_token',
        'userinfo_url': 'https://api.github.com/user',
        'emails_url': 'https://api.github.com/user/emails',
        'scope': 'read:user user:email',
        'icon': '🐙',
    },
}


# ============================================================
# 配置管理
# ============================================================

def get_oauth_config(provider_name):
    """
    获取 OAuth 提供商配置。

    从 system_settings 表读取 oauth_providers JSON。
    返回合并后的配置（内置模板 + 用户填写的 client_id/secret）。
    """
    if provider_name not in OAUTH_PROVIDERS:
        return None

    template = OAUTH_PROVIDERS[provider_name].copy()

    # 从数据库读取用户配置
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r"SELECT value FROM system_settings WHERE key_name = 'oauth_providers'")
        row = cur.fetchone()
        if row and row['value']:
            user_configs = json.loads(row['value'])
            user_cfg = user_configs.get(provider_name, {})
            template.update(user_cfg)
    except Exception:
        pass
    finally:
        db.close()

    # 检查是否已配置 client_id 和 client_secret
    if not template.get('client_id') or not template.get('client_secret'):
        return None

    # 设置默认回调 URL
    if not template.get('redirect_uri'):
        base_url = os.getenv('APP_BASE_URL', 'http://localhost:5000')
        template['redirect_uri'] = f'{base_url}/api/oauth/callback/{provider_name}'

    template['name'] = provider_name
    return template


def get_available_oauth_providers():
    """获取已启用且配置完整的 OAuth 提供商列表"""
    providers = []
    for name in OAUTH_PROVIDERS:
        cfg = get_oauth_config(name)
        if cfg:
            providers.append({
                'name': name,
                'label': cfg.get('label', name),
                'icon': cfg.get('icon', '🔗'),
            })
    return providers


# ============================================================
# OAuth 流程：Step 1 - 生成授权 URL
# ============================================================

def build_authorize_url(provider_name, state=None):
    """
    生成 OAuth 授权 URL。

    参数:
        provider_name: 提供商名称（google/github/...）
        state: 防 CSRF 的 state 参数（可选，自动生成）

    返回:
        (authorize_url, state) 或 (None, None)
    """
    cfg = get_oauth_config(provider_name)
    if not cfg:
        return None, None

    if not state:
        state = secrets.token_urlsafe(32)

    params = {
        'client_id': cfg['client_id'],
        'redirect_uri': cfg['redirect_uri'],
        'response_type': 'code',
        'scope': cfg['scope'],
        'state': state,
    }

    # Google 特有参数
    if provider_name == 'google':
        params['access_type'] = 'offline'
        params['prompt'] = 'consent'

    url = f"{cfg['authorize_url']}?{urlencode(params)}"
    return url, state


# ============================================================
# OAuth 流程：Step 2 - 回调处理
# ============================================================

def handle_oauth_callback(provider_name, code, state):
    """
    处理 OAuth 回调：code 换 token → 获取用户信息。

    返回:
        { email, name, avatar_url, provider_user_id } 或 None
    """
    cfg = get_oauth_config(provider_name)
    if not cfg:
        return None

    # 1. code 换 access_token
    token_data = {
        'client_id': cfg['client_id'],
        'client_secret': cfg['client_secret'],
        'code': code,
        'redirect_uri': cfg['redirect_uri'],
        'grant_type': 'authorization_code',
    }

    headers = {'Accept': 'application/json'}
    resp = http_requests.post(cfg['token_url'], data=token_data, headers=headers, timeout=15)

    if resp.status_code != 200:
        return None

    tokens = resp.json()
    access_token = tokens.get('access_token')
    if not access_token:
        return None

    # 2. 获取用户信息
    user_info = fetch_user_info(provider_name, cfg, access_token)
    return user_info


def fetch_user_info(provider_name, cfg, access_token):
    """
    获取 OAuth 提供商的用户信息。

    返回标准化格式: { email, name, avatar_url, provider_user_id }
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    }

    if provider_name == 'google':
        resp = http_requests.get(cfg['userinfo_url'], headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'email': data.get('email', ''),
                'name': data.get('name', data.get('email', '')),
                'avatar_url': data.get('picture', ''),
                'provider_user_id': data.get('id', ''),
            }

    elif provider_name == 'github':
        # 获取基本用户信息
        resp = http_requests.get(cfg['userinfo_url'], headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            email = data.get('email', '')
            # GitHub 可能不公开 email，需要额外请求
            if not email and cfg.get('emails_url'):
                emails_resp = http_requests.get(cfg['emails_url'], headers=headers, timeout=10)
                if emails_resp.status_code == 200:
                    emails = emails_resp.json()
                    # 找主邮箱 + 已验证
                    for e in emails:
                        if e.get('primary') and e.get('verified'):
                            email = e.get('email', '')
                            break
                    if not email and emails:
                        email = emails[0].get('email', '')

            return {
                'email': email,
                'name': data.get('name', data.get('login', '')),
                'avatar_url': data.get('avatar_url', ''),
                'provider_user_id': str(data.get('id', '')),
            }

    return None


# ============================================================
# 用户绑定/创建
# ============================================================

def _lookup_role_name(cur, user_id, default='user'):
    """从 roles/user_roles 查询用户角色名（dify_accounts 无 role 列）"""
    cur.execute(
        r'''SELECT r.name FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = %s LIMIT 1''',
        (user_id,))
    row = cur.fetchone()
    return row['name'] if row else default


def find_or_create_oauth_user(provider_name, user_info):
    """
    根据 OAuth 用户信息查找或创建本地用户（对齐 dify_accounts 真实 schema）。

    - email 已存在 → 直接复用该账号登录（按 email 关联外部身份）
    - 不存在 → 新建账号 + 工作区 + 默认 'user' 角色（与常规注册完全一致）

    注：dify_accounts 无 password_hash/role/oauth_info/avatar 列（角色在
    roles/user_roles，密码为 password/password_salt），故 OAuth 绑定按 email
    关联，不复用旧实现中不存在的列（否则 INSERT 抛异常被吞成 None，登录失败）。

    返回:
        { id, name, email, role } 或 None
    """
    if not user_info or not user_info.get('email'):
        return None

    email = user_info['email'].lower().strip()
    # 白空 email 归一化后为空必须拒绝（否则会写入空邮箱账号）
    if not email:
        return None
    name = (user_info.get('name') or '').strip() or email.split('@')[0]
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    from utils.helpers import _generate_password

    db = get_db()
    try:
        cur = db.cursor()

        # 1. 按 email 查找现有用户
        cur.execute(
            r'SELECT id, name, email FROM dify_accounts WHERE email = %s LIMIT 1',
            (email,))
        user = cur.fetchone()
        if user:
            role = _lookup_role_name(cur, user['id'])
            return {'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': role}

        # 2. 用户名唯一性处理（name 冲突则追加随机后缀）
        cur.execute(r'SELECT id FROM dify_accounts WHERE name = %s LIMIT 1', (name,))
        if cur.fetchone():
            name = f"{name}-{uuid.uuid4().hex[:6]}"

        # 3. 创建新账号 + 工作区 + 默认角色（镜像 routes/auth.py 注册流程）
        account_uuid = str(uuid.uuid4())
        tenant_uuid = str(uuid.uuid4())
        # OAuth 用户不使用密码登录，生成随机不可用密码（沿用统一哈希方案）
        salt_b64, pwd_b64 = _generate_password(secrets.token_urlsafe(24))
        cur.execute(
            r'''INSERT INTO dify_accounts
                (id, name, nickname, email, password, password_salt,
                 interface_language, interface_theme, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'zh-Hans', 'light', 'active', %s, %s)''',
            (account_uuid, name, name, email, pwd_b64, salt_b64, ts, ts))
        cur.execute(
            r'''INSERT INTO dify_tenants (id, name, plan, status, created_at, updated_at)
                VALUES (%s, %s, 'basic', 'normal', %s, %s)''',
            (tenant_uuid, name + "'s Workspace", ts, ts))
        cur.execute(
            r'''INSERT INTO dify_tenant_account_joins
                (tenant_id, account_id, role, current, created_at, updated_at)
                VALUES (%s, %s, 'owner', true, %s, %s)''',
            (tenant_uuid, account_uuid, ts, ts))
        cur.execute(r"SELECT id FROM roles WHERE name = 'user'")
        role_row = cur.fetchone()
        if role_row:
            cur.execute(
                r'INSERT INTO user_roles (user_id, role_id, created_at) VALUES (%s, %s, %s)',
                (account_uuid, role_row['id'], ts))
        db.commit()

        return {'id': account_uuid, 'name': name, 'email': email, 'role': 'user'}
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


# ==================================
# 登录处理
# ============================================================

def oauth_login(provider_name, code, state):
    """
    完整的 OAuth 登录流程。

    返回:
        (token_pair, error_message)
    """
    # 处理回调
    user_info = handle_oauth_callback(provider_name, code, state)
    if not user_info:
        return None, 'OAuth 授权失败，无法获取用户信息'

    if not user_info.get('email'):
        return None, 'OAuth 提供商未返回邮箱地址，无法完成登录'

    # 查找或创建用户
    user = find_or_create_oauth_user(provider_name, user_info)
    if not user:
        return None, '创建用户失败，请稍后重试'

    # 生成 JWT Token
    token_pair = generate_token_pair(
        user_id=user['id'],
        email=user['email'],
        username=user.get('name', ''),
        role=user.get('role', 'user'),
    )

    return token_pair, None
