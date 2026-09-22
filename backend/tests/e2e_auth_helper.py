# -*- coding: utf-8 -*-
"""E2E 测试辅助：为受 @login_required 保护的接口取得 Bearer Token。

设计要点：
  - 不内置任何明文口令（避免把凭据写进仓库，也避免误触发登录失败锁定）；
  - 优先走真实登录接口：凭据来自环境变量 SHANGZHOU_TEST_USERNAME / SHANGZHOU_TEST_PASSWORD；
  - 若未提供环境变量，则退化为「用后端自身的 JWT 密钥直接签发 access token」，
    仅用于本地功能验证，同样经过真实的 verify_token 校验链路。
"""
import json
import os
import urllib.error
import urllib.request

BASE_URL = os.environ.get('SHANGZHOU_TEST_BASE_URL', 'http://127.0.0.1:5000')


def _post_json(path, payload, timeout=15):
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except Exception:
            return e.code, {}


def _login_with_env_credentials():
    """环境变量提供凭据时走真实登录接口"""
    username = os.environ.get('SHANGZHOU_TEST_USERNAME')
    password = os.environ.get('SHANGZHOU_TEST_PASSWORD')
    if not username or not password:
        return None, '未设置 SHANGZHOU_TEST_USERNAME / SHANGZHOU_TEST_PASSWORD'
    status, body = _post_json('/api/login', {'username': username, 'password': password})
    data = (body or {}).get('data') or {}
    token = data.get('access_token')
    if status == 200 and token:
        return token, 'login'
    return None, f'登录失败 HTTP {status}: {(body or {}).get("msg", "")}'


def _mint_access_token():
    """用后端自身的 JWT 签发函数生成 access token（本地验证用，无需口令）"""
    import sys

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from config import get_db
    from utils.auth import generate_token_pair

    db = get_db()
    try:
        cur = db.cursor()
        env_user = os.environ.get('SHANGZHOU_TEST_USERNAME')
        if env_user:
            cur.execute(
                'SELECT id, name, email FROM dify_accounts WHERE name = %s OR email = %s LIMIT 1',
                (env_user, env_user))
        else:
            # 优先取具备 admin 角色的账号，保证知识库等接口有完整权限语义
            cur.execute('''
                SELECT da.id, da.name, da.email
                FROM dify_accounts da
                LEFT JOIN user_roles ur ON ur.user_id = da.id
                LEFT JOIN roles r ON r.id = ur.role_id
                WHERE da.status = 'active'
                ORDER BY (r.name = 'admin') DESC, da.id ASC
                LIMIT 1
            ''')
        acc = cur.fetchone()
    finally:
        db.close()

    if not acc:
        return None, 'dify_accounts 中没有可用账号'

    tokens = generate_token_pair(
        user_id=str(acc['id']),
        email=acc['email'] or '',
        username=acc['name'] or '',
        role='admin',
    )
    return tokens.get('access_token'), f'minted for {acc["name"]}'


def get_auth_header(verbose=False):
    """返回可直接并入请求头的 dict，失败返回 {}"""
    token, how = _login_with_env_credentials()
    if not token:
        if verbose:
            print(f'   [auth] 真实登录不可用（{how}），改用后端密钥签发 token')
        token, how = _mint_access_token()
    if not token:
        if verbose:
            print(f'   [auth] 无法取得 token：{how}')
        return {}
    if verbose:
        print(f'   [auth] 已获取访问令牌（{how}）')
    return {'Authorization': 'Bearer ' + token}
