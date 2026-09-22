# -*- coding: utf-8 -*-
"""
工具 OAuth 引擎 —— OAuth 2.0 授权流程管理

职责:
    1. 管理 OAuth 客户端（系统级 + 租户级）
    2. 生成授权 URL，引导用户授权
    3. 处理 OAuth 回调（code 换 token）
    4. Token 刷新和存储
    5. 工具调用时自动附加 Bearer Token

OAuth 流程:
    1. 前端调用 /api/tools/oauth/authorize 获取授权 URL
    2. 用户访问授权 URL，在第三方平台确认授权
    3. 第三方重定向到 /api/tools/oauth/callback?code=xxx&state=yyy
    4. 后端用 code 换取 access_token + refresh_token
    5. Token 存储到 tool_oauth_tokens 表
    6. 工具调用时自动使用 access_token（过期则刷新）
"""
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from config import get_db
from models.tables import (
    TOOL_OAUTH_SYSTEM_CLIENTS_TABLE_SQL,
    TOOL_OAUTH_TENANT_CLIENTS_TABLE_SQL,
    TOOL_OAUTH_TOKENS_TABLE_SQL,
)

# 内存中的 state 存储（用于 CSRF 防护）{state: {provider_name, tenant_id, created_at}}
_oauth_states = {}


def ensure_oauth_tables():
    """确保 OAuth 表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_OAUTH_SYSTEM_CLIENTS_TABLE_SQL)
        cur.execute(TOOL_OAUTH_TENANT_CLIENTS_TABLE_SQL)
        cur.execute(TOOL_OAUTH_TOKENS_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


# ============================================================
# Token 加密/解密
# ============================================================

def _encrypt_token(token: str) -> str:
    """加密 token（简单的 XOR + base64，生产环境应使用 Fernet）"""
    try:
        from utils.encryption import encrypt_field
        return encrypt_field(token)
    except Exception:
        import base64
        key = b'shangzhou-oauth-key-2026'
        data = token.encode('utf-8')
        encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return 'enc:' + base64.urlsafe_b64encode(encrypted).decode('utf-8')


def _decrypt_token(encrypted: str) -> str:
    """解密 token"""
    if not encrypted:
        return ''
    if encrypted.startswith('enc:'):
        try:
            from utils.encryption import decrypt_field
            result = decrypt_field(encrypted)
            if result:
                return result
        except Exception:
            pass
        # 回退：本地 XOR
        import base64
        try:
            key = b'shangzhou-oauth-key-2026'
            data = base64.urlsafe_b64decode(encrypted[4:])
            decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
            return decrypted.decode('utf-8')
        except Exception:
            return encrypted
    return encrypted


# ============================================================
# OAuth 客户端 CRUD
# ============================================================

def create_system_client(provider_name: str, client_id: str, client_secret: str,
                         auth_url: str, token_url: str,
                         redirect_uri: str = '', scopes: str = '',
                         extra_params: Dict = None) -> Optional[int]:
    """创建系统级 OAuth 客户端"""
    if not provider_name or not client_id or not client_secret:
        return None
    ensure_oauth_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO tool_oauth_system_clients
            (provider_name, client_id, client_secret, auth_url, token_url,
             redirect_uri, scopes, extra_params)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                client_id = VALUES(client_id),
                client_secret = VALUES(client_secret),
                auth_url = VALUES(auth_url),
                token_url = VALUES(token_url),
                redirect_uri = VALUES(redirect_uri),
                scopes = VALUES(scopes),
                extra_params = VALUES(extra_params)
        """, (provider_name, client_id, _encrypt_token(client_secret), auth_url,
              token_url, redirect_uri, scopes,
              json.dumps(extra_params, ensure_ascii=False) if extra_params else None))
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


def create_tenant_client(tenant_id: str, provider_name: str, client_id: str,
                         client_secret: str, auth_url: str, token_url: str,
                         redirect_uri: str = '', scopes: str = '',
                         extra_params: Dict = None) -> Optional[int]:
    """创建租户级 OAuth 客户端"""
    if not tenant_id or not provider_name or not client_id:
        return None
    ensure_oauth_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO tool_oauth_tenant_clients
            (tenant_id, provider_name, client_id, client_secret, auth_url, token_url,
             redirect_uri, scopes, extra_params)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                client_id = VALUES(client_id),
                client_secret = VALUES(client_secret),
                auth_url = VALUES(auth_url),
                token_url = VALUES(token_url),
                redirect_uri = VALUES(redirect_uri),
                scopes = VALUES(scopes),
                extra_params = VALUES(extra_params)
        """, (tenant_id, provider_name, client_id, _encrypt_token(client_secret),
              auth_url, token_url, redirect_uri, scopes,
              json.dumps(extra_params, ensure_ascii=False) if extra_params else None))
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


def get_oauth_client(tenant_id: str = None, provider_name: str = '') -> Optional[Dict]:
    """
    获取 OAuth 客户端配置（优先租户级，其次系统级）。

    返回:
        {provider_name, client_id, client_secret, auth_url, token_url,
         redirect_uri, scopes, extra_params, level} 或 None
    """
    ensure_oauth_tables()
    db = get_db()
    try:
        cur = db.cursor()

        # 优先租户级
        if tenant_id:
            cur.execute("""
                SELECT * FROM tool_oauth_tenant_clients
                WHERE tenant_id = %s AND provider_name = %s AND status = 1
            """, (tenant_id, provider_name))
            row = cur.fetchone()
            if row:
                return _row_to_client(row, 'tenant')

        # 系统级
        cur.execute("""
            SELECT * FROM tool_oauth_system_clients
            WHERE provider_name = %s AND status = 1
        """, (provider_name,))
        row = cur.fetchone()
        if row:
            return _row_to_client(row, 'system')

        return None
    finally:
        db.close()


def _row_to_client(row: Dict, level: str) -> Dict:
    """将数据库行转换为客户端配置"""
    return {
        'provider_name': row['provider_name'],
        'client_id': row['client_id'],
        'client_secret': _decrypt_token(row['client_secret']),
        'auth_url': row['auth_url'],
        'token_url': row['token_url'],
        'redirect_uri': row['redirect_uri'] or '',
        'scopes': row['scopes'] or '',
        'extra_params': json.loads(row['extra_params']) if row.get('extra_params') else {},
        'level': level,
    }


def delete_oauth_client(provider_name: str, tenant_id: str = None) -> bool:
    """删除 OAuth 客户端"""
    db = get_db()
    try:
        cur = db.cursor()
        if tenant_id:
            cur.execute("DELETE FROM tool_oauth_tenant_clients WHERE provider_name = %s AND tenant_id = %s",
                        (provider_name, tenant_id))
        else:
            cur.execute("DELETE FROM tool_oauth_system_clients WHERE provider_name = %s", (provider_name,))
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# ============================================================
# OAuth 授权流程
# ============================================================

def generate_auth_url(tenant_id: str, provider_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    生成 OAuth 授权 URL。

    返回:
        (授权 URL, state) 或 (None, 错误信息)
    """
    client = get_oauth_client(tenant_id, provider_name)
    if not client:
        return None, f'未找到 {provider_name} 的 OAuth 客户端配置'

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        'provider_name': provider_name,
        'tenant_id': tenant_id or 'system',
        'created_at': time.time(),
    }

    # 构建授权 URL
    params = {
        'client_id': client['client_id'],
        'redirect_uri': client['redirect_uri'],
        'response_type': 'code',
        'state': state,
    }
    if client['scopes']:
        params['scope'] = client['scopes']
    # 额外参数
    for k, v in client.get('extra_params', {}).items():
        if k not in params:
            params[k] = v

    auth_url = client['auth_url']
    separator = '&' if '?' in auth_url else '?'
    full_url = auth_url + separator + urllib.parse.urlencode(params)

    return full_url, state


def exchange_code_for_token(tenant_id: str, provider_name: str,
                            code: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    用授权码换取 token。

    返回:
        (token 信息, 错误信息)
    """
    client = get_oauth_client(tenant_id, provider_name)
    if not client:
        return None, f'未找到 {provider_name} 的 OAuth 客户端配置'

    payload = {
        'grant_type': 'authorization_code',
        'client_id': client['client_id'],
        'client_secret': client['client_secret'],
        'code': code,
        'redirect_uri': client['redirect_uri'],
    }

    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(
        client['token_url'],
        data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:500]
        return None, f'Token 交换失败 HTTP {e.code}: {body}'
    except Exception as e:
        return None, f'Token 交换失败: {str(e)[:200]}'

    if 'access_token' not in result:
        return None, f'Token 响应缺少 access_token: {str(result)[:200]}'

    # 计算过期时间
    expires_in = int(result.get('expires_in', 3600))
    expires_at = datetime.now() + timedelta(seconds=expires_in)

    token_info = {
        'access_token': result['access_token'],
        'refresh_token': result.get('refresh_token', ''),
        'expires_at': expires_at,
        'scopes': result.get('scope', client['scopes']),
    }

    # 存储 token
    save_token(tenant_id or 'system', provider_name, token_info)

    return token_info, None


def handle_oauth_callback(state: str, code: str = None,
                          error: str = None) -> Tuple[bool, str]:
    """
    处理 OAuth 回调。

    返回:
        (是否成功, 消息)
    """
    # 清理过期 state（超过 10 分钟）
    now = time.time()
    expired = [s for s, v in _oauth_states.items() if now - v['created_at'] > 600]
    for s in expired:
        _oauth_states.pop(s, None)

    if state not in _oauth_states:
        return False, '无效的 state 参数（可能已过期）'

    info = _oauth_states.pop(state)

    if error:
        return False, f'授权被拒绝: {error}'

    if not code:
        return False, '缺少授权码'

    token_info, err = exchange_code_for_token(
        info['tenant_id'], info['provider_name'], code
    )
    if err:
        return False, err

    return True, f'{info["provider_name"]} 授权成功'


def save_token(tenant_id: str, provider_name: str, token_info: Dict):
    """存储 OAuth token"""
    ensure_oauth_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO tool_oauth_tokens
            (tenant_id, provider_name, access_token, refresh_token, expires_at, scopes, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'active')
            ON DUPLICATE KEY UPDATE
                access_token = VALUES(access_token),
                refresh_token = VALUES(refresh_token),
                expires_at = VALUES(expires_at),
                scopes = VALUES(scopes),
                status = 'active',
                updated_at = NOW()
        """, (
            tenant_id, provider_name,
            _encrypt_token(token_info['access_token']),
            _encrypt_token(token_info.get('refresh_token', '')),
            token_info['expires_at'],
            token_info.get('scopes', ''),
        ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def get_valid_token(tenant_id: str, provider_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    获取有效的 access_token（过期则自动刷新）。

    返回:
        (access_token, 错误信息)
    """
    ensure_oauth_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT * FROM tool_oauth_tokens
            WHERE tenant_id = %s AND provider_name = %s AND status = 'active'
        """, (tenant_id, provider_name))
        row = cur.fetchone()
        if not row:
            return None, f'未找到 {provider_name} 的授权令牌，请先完成 OAuth 授权'

        expires_at = row['expires_at']
        # 如果还有 5 分钟以上有效期，直接返回
        if expires_at and (expires_at - datetime.now()).total_seconds() > 300:
            return _decrypt_token(row['access_token']), None

        # 需要刷新
        refresh_token = _decrypt_token(row['refresh_token'])
        if not refresh_token:
            return None, f'{provider_name} 的令牌已过期且无刷新令牌，请重新授权'

        client = get_oauth_client(tenant_id, provider_name)
        if not client:
            return None, f'未找到 {provider_name} 的 OAuth 客户端配置'

        # 刷新 token
        payload = {
            'grant_type': 'refresh_token',
            'client_id': client['client_id'],
            'client_secret': client['client_secret'],
            'refresh_token': refresh_token,
        }
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(
            client['token_url'],
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return None, f'Token 刷新失败: {str(e)[:200]}'

        if 'access_token' not in result:
            return None, f'Token 刷新响应缺少 access_token'

        expires_in = int(result.get('expires_in', 3600))
        token_info = {
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token', refresh_token),
            'expires_at': datetime.now() + timedelta(seconds=expires_in),
            'scopes': result.get('scope', row['scopes'] or ''),
        }
        save_token(tenant_id, provider_name, token_info)
        return token_info['access_token'], None
    finally:
        db.close()


def revoke_token(tenant_id: str, provider_name: str) -> bool:
    """撤销 OAuth token"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            UPDATE tool_oauth_tokens
            SET status = 'revoked'
            WHERE tenant_id = %s AND provider_name = %s
        """, (tenant_id, provider_name))
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def get_token_status(tenant_id: str, provider_name: str) -> Optional[Dict]:
    """获取 token 状态（不返回 token 本身）"""
    ensure_oauth_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT expires_at, scopes, status, created_at, updated_at
            FROM tool_oauth_tokens
            WHERE tenant_id = %s AND provider_name = %s
        """, (tenant_id, provider_name))
        row = cur.fetchone()
        if not row:
            return None
        expired = row['expires_at'] and row['expires_at'] < datetime.now()
        return {
            'provider_name': provider_name,
            'status': row['status'],
            'expired': expired,
            'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None,
            'scopes': row['scopes'] or '',
            'authorized_at': row['created_at'].isoformat() if row['created_at'] else None,
        }
    finally:
        db.close()
