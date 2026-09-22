# -*- coding: utf-8 -*-
"""
JWT 认证工具 —— Token 生成、验证、权限装饰器

功能：
1. 生成 Access Token + Refresh Token
2. 验证 Token 有效性
3. 从请求中提取 Token
4. 登录_required 装饰器
5. 角色权限装饰器

依赖：PyJWT
安装：pip install PyJWT
"""

import os
import time
import jwt
from functools import wraps
from flask import request, jsonify

from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================
# 配置
# ============================================================

# 从环境变量读取密钥，缺省时使用随机值（每次重启失效，生产环境必须设置）
# 安全加固：生成持久化密钥文件，避免每次重启失效
def _load_jwt_secret():
    """加载 JWT 密钥，优先级：环境变量 > 密钥文件 > 生成并持久化"""
    env_key = os.getenv('JWT_SECRET')
    if env_key:
        return env_key
    # 尝试从密钥文件读取
    secret_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.jwt_secret')
    if os.path.exists(secret_file):
        try:
            with open(secret_file, 'r') as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass
    # 生成新密钥并持久化
    new_key = os.urandom(32).hex()
    try:
        with open(secret_file, 'w') as f:
            f.write(new_key)
        os.chmod(secret_file, 0o600)  # 仅所有者可读写
    except Exception:
        pass
    return new_key

SECRET_KEY = _load_jwt_secret()
# Access Token 有效期：2 小时
ACCESS_TOKEN_EXPIRY = int(os.getenv('JWT_ACCESS_EXPIRY', 7200))
# Refresh Token 有效期：7 天
REFRESH_TOKEN_EXPIRY = int(os.getenv('JWT_REFRESH_EXPIRY', 604800))
# Token 算法
ALGORITHM = 'HS256'
# Token 类型字段
TOKEN_TYPE_ACCESS = 'access'
TOKEN_TYPE_REFRESH = 'refresh'


# ============================================================
# Token 生成
# ============================================================

def generate_access_token(user_id, email, username='', role='', **extra_claims):
    """
    生成 Access Token（短期有效）

    参数:
        user_id: 用户 ID
        email: 用户邮箱
        username: 用户名
        role: 角色名称
        **extra_claims: 额外声明

    返回:
        str: JWT Token 字符串
    """
    now = int(time.time())
    payload = {
        'token_type': TOKEN_TYPE_ACCESS,
        'user_id': str(user_id),
        'email': email,
        'username': username,
        'role': role,
        'iat': now,
        'exp': now + ACCESS_TOKEN_EXPIRY,
        'nbf': now,  # 生效时间
        'jti': os.urandom(16).hex(),  # 唯一标识（用于吊销）
    }
    # 合并额外声明（但不能覆盖核心字段）
    for k, v in extra_claims.items():
        if k not in payload:
            payload[k] = v
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def generate_refresh_token(user_id):
    """
    生成 Refresh Token（长期有效，仅用于换取新 Access Token）

    参数:
        user_id: 用户 ID

    返回:
        str: JWT Token 字符串
    """
    now = int(time.time())
    payload = {
        'token_type': TOKEN_TYPE_REFRESH,
        'user_id': str(user_id),
        'iat': now,
        'exp': now + REFRESH_TOKEN_EXPIRY,
        'jti': os.urandom(16).hex(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def generate_token_pair(user_id, email, username='', role='', **extra_claims):
    """
    生成 Token 对（Access + Refresh）

    返回:
        dict: {access_token, refresh_token, token_type, expires_in}
    """
    return {
        'access_token': generate_access_token(user_id, email, username, role, **extra_claims),
        'refresh_token': generate_refresh_token(user_id),
        'token_type': 'Bearer',
        'expires_in': ACCESS_TOKEN_EXPIRY,
    }


# ============================================================
# Token 验证
# ============================================================

def verify_token(token, expected_type=TOKEN_TYPE_ACCESS):
    """
    验证 Token 有效性

    参数:
        token: JWT Token 字符串
        expected_type: 期望的 Token 类型 ('access' 或 'refresh')

    返回:
        tuple: (payload_dict, error_message)
        - 成功时返回 (payload, None)
        - 失败时返回 (None, error_message)
    """
    if not token:
        return None, '未提供认证令牌'
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 验证 Token 类型
        if payload.get('token_type') != expected_type:
            return None, 'Token 类型不匹配'
        # 安全加固：检查 Token 是否已被吊销（黑名单）
        jti = payload.get('jti')
        if jti and _is_token_revoked_jti(jti):
            return None, '令牌已被吊销'
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, '令牌已过期'
    except jwt.InvalidTokenError as e:
        return None, f'令牌无效: {str(e)}'


def refresh_access_token(refresh_token):
    """
    使用 Refresh Token 换取新的 Access Token

    参数:
        refresh_token: Refresh Token 字符串

    返回:
        tuple: (new_token_pair, error_message)
    """
    payload, error = verify_token(refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    if error:
        return None, error
    # 安全加固：从数据库重新查询用户信息，保留完整身份
    user_info = _get_user_by_id(payload['user_id'])
    email = user_info.get('email', '') if user_info else payload.get('email', '')
    username = user_info.get('name', '') if user_info else payload.get('username', '')
    role = user_info.get('role', '') if user_info else payload.get('role', '')
    # 生成新的 Token 对（Refresh Token 轮转）
    return generate_token_pair(
        user_id=payload['user_id'],
        email=email,
        username=username,
        role=role,
    ), None


def _get_user_by_id(user_id):
    """根据用户 ID 查询用户信息（用于刷新 Token 时恢复身份）"""
    try:
        from config import get_db
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT id, name, email, role FROM dify_accounts WHERE id = %s', (user_id,))
            return cur.fetchone()
        finally:
            db.close()
    except Exception:
        logger.exception('查询用户信息失败 (user_id=%s)，刷新 Token 身份恢复将回退到旧声明', user_id)
        return None


# ============================================================
# 请求中提取 Token
# ============================================================

def extract_token_from_request():
    """
    从 HTTP 请求中提取 Token

    优先级：
    1. Authorization: Bearer <token>
    2. 查询参数 ?token=<token>（仅用于特殊场景如 SSE）

    返回:
        str or None
    """
    # 从 Header 提取
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    # 从查询参数提取（SSE EventSource 不支持自定义 Header）
    token = request.args.get('token')
    if token:
        return token
    return None


def get_current_user():
    """
    从请求中获取当前用户信息（不验证，仅解析）

    返回:
        dict or None: 用户信息 {user_id, email, username, role}
    """
    token = extract_token_from_request()
    if not token:
        return None
    payload, error = verify_token(token)
    if error:
        return None
    return {
        'user_id': payload.get('user_id'),
        'email': payload.get('email'),
        'username': payload.get('username', ''),
        'role': payload.get('role', ''),
    }


# ============================================================
# 装饰器
# ============================================================

def login_required(f):
    """
    登录_required 装饰器

    验证请求中的 JWT Token，验证通过后将用户信息注入 request.user

    用法:
        @app.route('/api/protected')
        @login_required
        def protected_route():
            user = request.user
            return jsonify(data=f'Hello {user[\"email\"]}')
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = extract_token_from_request()
        if not token:
            return jsonify(code=401, msg='未提供认证令牌，请先登录'), 401
        payload, error = verify_token(token)
        if error:
            return jsonify(code=401, msg=error), 401
        # 注入用户信息
        request.user = {
            'user_id': payload.get('user_id'),
            'email': payload.get('email'),
            'username': payload.get('username', ''),
            'role': payload.get('role', ''),
        }
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """
    角色权限装饰器

    要求用户具有指定角色之一

    用法:
        @app.route('/api/admin')
        @login_required
        @role_required('admin', 'owner')
        def admin_route():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 先验证登录
            token = extract_token_from_request()
            if not token:
                return jsonify(code=401, msg='未提供认证令牌'), 401
            payload, error = verify_token(token)
            if error:
                return jsonify(code=401, msg=error), 401
            # 验证角色
            user_role = payload.get('role', '')
            if allowed_roles and user_role not in allowed_roles:
                return jsonify(code=403, msg='权限不足，需要角色: %s' % ', '.join(allowed_roles)), 403
            request.user = {
                'user_id': payload.get('user_id'),
                'email': payload.get('email'),
                'username': payload.get('username', ''),
                'role': user_role,
            }
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================
# Token 黑名单（可选，用于登出）
# ============================================================

# 使用 Redis 存储吊销的 Token（需要 redis_cache 模块）
_blacklist_cache_key = 'jwt:blacklist:'


def revoke_token(token):
    """
    吊销 Token（加入黑名单）

    参数:
        token: 要吊销的 JWT Token

    返回:
        bool: 是否成功
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={'verify_exp': False})
        jti = payload.get('jti')
        if jti:
            # 计算过期时间（黑名单保留至 Token 自然过期）
            exp = payload.get('exp', 0)
            ttl = max(exp - int(time.time()), 3600)  # 至少保留 1 小时
            # 尝试使用 Redis，失败则使用内存集合
            try:
                from utils.redis_cache import cache_set
                cache_set(f'{_blacklist_cache_key}{jti}', '1', expires_in=ttl)
                return True
            except Exception:
                # Redis 失败时回退到内存集合
                logger.warning('Redis 吊销写入失败，回退内存黑名单 (jti=%s)', jti)
                _memory_blacklist.add(jti)
                return True
    except Exception:
        logger.exception('吊销 Token 失败（无法解析 JWT 或数据库异常）')
    return False


# 内存黑名单（Redis 不可用时的回退）
_memory_blacklist = set()


def _is_token_revoked_jti(jti):
    """
    检查 JTI 是否已被吊销（内部函数，直接接收 JTI）

    参数:
        jti: Token 的唯一标识

    返回:
        bool: 是否已吊销
    """
    if not jti:
        return False
    try:
        from utils.redis_cache import cache_get
        return cache_get(f'{_blacklist_cache_key}{jti}') is not None
    except Exception:
        # Redis 不可用时回退到内存集合
        return jti in _memory_blacklist


def api_key_required(f):
    """API Key 认证装饰器（用于 Service API）"""
    from flask import request, jsonify
    from config import get_db

    def decorated(*args, **kwargs):
        api_key = request.headers.get('Authorization', '').replace('Bearer ', '') or request.args.get('api_key')
        if not api_key:
            return jsonify(code=401, msg='缺少 API Key'), 401
        db = get_db()
        try:
            cur = db.cursor()
            # API Key 存储在 dify_api_tokens（Dify 格式 token: app-xxx），
            # 关联 dify_apps 校验应用状态
            cur.execute(
                'SELECT a.* FROM dify_api_tokens t '
                'JOIN dify_apps a ON a.id = t.app_id '
                'WHERE t.token = %s AND a.status = %s',
                (api_key, 'normal'))
            app = cur.fetchone()
            if not app:
                return jsonify(code=401, msg='无效的 API Key'), 401
            # 将 app 信息存入 request 上下文
            request._api_app = app
        finally:
            db.close()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated


def get_current_app():
    """获取当前 API Key 对应的应用信息"""
    from flask import request
    return getattr(request, '_api_app', None)


def is_token_revoked(token):
    """
    检查 Token 是否已被吊销

    参数:
        token: JWT Token

    返回:
        bool: 是否已吊销
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={'verify_exp': False})
        jti = payload.get('jti')
        return _is_token_revoked_jti(jti)
    except Exception:
        logger.exception('检查 Token 吊销状态失败，按未吊销处理')
        return False


# ============================================================
# 资源级 RBAC（对齐 Dify 权限矩阵）
# ============================================================

def user_has_permission(user_id, permission_code):
    """
    检查用户是否拥有指定权限点。

    逻辑：admin 角色自动拥有所有权限；其他角色查询 role_permissions 表。

    参数:
        user_id: 用户 ID
        permission_code: 权限标识（如 'app:create', 'dataset:delete'）

    返回:
        bool
    """
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        # 获取用户角色
        cur.execute(
            r'''SELECT r.name FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = %s LIMIT 1''',
            (user_id,))
        row = cur.fetchone()
        if not row:
            return False
        role_name = row['name']
        # admin 拥有所有权限
        if role_name == 'admin':
            return True
        # 查询权限表
        cur.execute(
            r'''SELECT COUNT(*) as cnt FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.name = %s AND p.code = %s''',
            (role_name, permission_code))
        result = cur.fetchone()
        return (result['cnt'] or 0) > 0
    except Exception:
        logger.exception('查询用户权限失败 (user_id=%s, permission=%s)，按无权限处理', user_id, permission_code)
        return False
    finally:
        db.close()


def check_dataset_permission(dataset_id, user_id, required='read'):
    """
    检查用户对知识库的权限（单租户工作区模型）。

    实际 schema 说明：dify_datasets 没有 owner 列（只有 created_by），
    且不存在 dify_dataset_permissions 表。因此按以下模型判定：

    权限级别: read < write < admin
    - 读：工作区内任意登录用户（与知识库列表接口一致，列表亦未按属主过滤）
    - 写/管理：创建者（created_by）或 admin 角色

    返回:
        bool
    """
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'SELECT created_by FROM dify_datasets WHERE id = %s',
            (dataset_id,))
        ds = cur.fetchone()
        if not ds:
            return False
        # 读权限：工作区内所有登录成员可见
        if required == 'read':
            return True
        # 写/管理：创建者或管理员
        if str(ds.get('created_by') or '') == str(user_id):
            return True
        cur.execute(
            r'''SELECT r.name FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = %s LIMIT 1''',
            (user_id,))
        role_row = cur.fetchone()
        return bool(role_row and role_row['name'] == 'admin')
    except Exception:
        logger.exception('检查知识库权限失败 (dataset_id=%s, user_id=%s)，按无权限处理', dataset_id, user_id)
        return False
    finally:
        db.close()


def check_app_access(app_id, user_id):
    """
    检查用户是否有权访问应用。

    - 应用 owner 自动拥有权限
    - admin 角色自动拥有权限
    - published 应用所有人可读

    返回:
        bool
    """
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'SELECT created_by, status FROM dify_apps WHERE id = %s',
            (app_id,))
        app = cur.fetchone()
        if not app:
            return False
        # 创建者拥有权限（本表无 owner 列，统一用 created_by）
        if str(app.get('created_by') or '') == str(user_id):
            return True
        # published 应用可读
        if app.get('status') == 'published':
            return True
        # 检查 admin
        cur.execute(
            r'''SELECT r.name FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = %s LIMIT 1''',
            (user_id,))
        role_row = cur.fetchone()
        if role_row and role_row['name'] == 'admin':
            return True
        return False
    except Exception:
        logger.exception('检查应用访问权限失败 (app_id=%s, user_id=%s)，按无权限处理', app_id, user_id)
        return False
    finally:
        db.close()


def dataset_permission_required(dataset_id_param, permission='read'):
    """
    知识库权限装饰器工厂。

    用法:
        @app.route('/api/datasets/<dataset_id>/documents')
        @login_required
        @dataset_permission_required('dataset_id', 'read')
        def list_documents(dataset_id):
            ...

    参数:
        dataset_id_param: 视图函数中 dataset_id 参数的名称
        permission: 所需权限 'read' / 'write' / 'admin'
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import request
            user_id = getattr(request, 'user', {}).get('user_id', '')
            if not user_id:
                return jsonify(code=401, msg='未登录'), 401
            # 获取 dataset_id（从路径参数或查询参数）
            ds_id = kwargs.get(dataset_id_param) or request.args.get(dataset_id_param) or request.view_args.get(dataset_id_param)
            if not ds_id:
                return jsonify(code=400, msg='缺少数据集 ID'), 400
            if not check_dataset_permission(ds_id, user_id, permission):
                return jsonify(code=403, msg='无权访问该知识库'), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================
# 资源级 RBAC（统一资源权限检查）
# ============================================================

# 资源类型注册表：每种资源表名 + owner 字段 + 状态字段
_RESOURCE_REGISTRY = {
    'app': {
        'table': 'dify_apps',
        'owner_field': 'created_by',
        'status_field': 'status',
        'published_value': 'published',
        'admin_permission': 'app:manage',
    },
    'workflow': {
        'table': 'dify_workflows',
        'owner_field': 'created_by',
        'status_field': 'status',
        'published_value': 'published',
        'admin_permission': 'workflow:manage',
    },
    'dataset': {
        'table': 'dify_datasets',
        'owner_field': 'created_by',
        'status_field': None,
        'published_value': None,
        'admin_permission': 'knowledge:manage',
    },
    'tool': {
        'table': 'dify_builtin_tools',
        'owner_field': 'creator_id',
        'status_field': 'status',
        'published_value': 'published',
        'admin_permission': 'tool:manage',
    },
}


def check_resource_permission(resource_type, resource_id, user_id, required='read'):
    """
    统一资源权限检查。

    权限级别: read < write < admin
    - owner 自动拥有所有权限
    - admin 角色自动拥有所有权限
    - published 资源所有人可读（read）

    Args:
        resource_type: 'app' | 'workflow' | 'dataset' | 'tool'
        resource_id: 资源 ID
        user_id: 用户 ID
        required: 'read' | 'write' | 'admin'

    Returns:
        bool
    """
    from config import get_db
    registry = _RESOURCE_REGISTRY.get(resource_type)
    if not registry:
        return False

    db = get_db()
    try:
        cur = db.cursor()
        table = registry['table']
        owner_field = registry['owner_field']

        # 查询资源
        if registry['status_field']:
            cur.execute(
                f'SELECT {owner_field}, {registry["status_field"]} FROM {table} WHERE id = %s',
                (resource_id,))
        else:
            cur.execute(
                f'SELECT {owner_field} FROM {table} WHERE id = %s',
                (resource_id,))
        resource = cur.fetchone()
        if not resource:
            return False

        # owner 拥有所有权限
        if str(resource.get(owner_field, '')) == str(user_id):
            return True

        # published 资源可读
        if required == 'read' and registry['published_value']:
            if resource.get(registry['status_field']) == registry['published_value']:
                return True

        # 数据集走独立权限表
        if resource_type == 'dataset':
            return check_dataset_permission(resource_id, user_id, required)

        # 检查 admin 角色
        cur.execute(
            r'''SELECT r.name FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = %s LIMIT 1''',
            (user_id,))
        role_row = cur.fetchone()
        if role_row and role_row['name'] == 'admin':
            return True

        return False
    except Exception:
        logger.exception('检查资源权限失败 (resource_type=%s, resource_id=%s, user_id=%s)，按无权限处理', resource_type, resource_id, user_id)
        return False
    finally:
        db.close()


def resource_permission_required(resource_type, resource_id_param, permission='read'):
    """
    资源级权限装饰器工厂（通用）。

    用法:
        @app.route('/api/apps/<app_id>')
        @login_required
        @resource_permission_required('app', 'app_id', 'read')
        def get_app(app_id):
            ...

        @app.route('/api/workflows/<wf_id>', methods=['PUT'])
        @login_required
        @resource_permission_required('workflow', 'wf_id', 'write')
        def update_workflow(wf_id):
            ...

    参数:
        resource_type: 'app' | 'workflow' | 'dataset' | 'tool'
        resource_id_param: 视图函数中资源 ID 参数的名称
        permission: 所需权限 'read' / 'write' / 'admin'
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(request, 'user', {}).get('user_id', '')
            if not user_id:
                return jsonify(code=401, msg='未登录'), 401
            # 获取 resource_id（从路径参数、查询参数或 JSON body）
            res_id = kwargs.get(resource_id_param) \
                or request.args.get(resource_id_param) \
                or request.view_args.get(resource_id_param)
            if not res_id and request.is_json:
                res_id = request.json.get(resource_id_param)
            if not res_id:
                return jsonify(code=400, msg='缺少资源 ID'), 400
            if not check_resource_permission(resource_type, res_id, user_id, permission):
                return jsonify(code=403, msg='无权访问该资源'), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def check_user_permission(user_id, permission_code):
    """
    检查用户是否拥有指定权限码。

    通过 roles → role_permissions → permissions 链式查询。

    Args:
        user_id: 用户 ID
        permission_code: 权限码（如 'app:manage'）

    Returns:
        bool
    """
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        # 检查 admin 角色
        cur.execute(
            r'''SELECT r.name FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = %s LIMIT 1''',
            (user_id,))
        role_row = cur.fetchone()
        if role_row and role_row['name'] == 'admin':
            return True
        # 检查具体权限码
        cur.execute(
            r'''SELECT p.code FROM permissions p
                JOIN role_permissions rp ON rp.permission_id = p.id
                JOIN user_roles ur ON ur.role_id = rp.role_id
                WHERE ur.user_id = %s AND p.code = %s
                LIMIT 1''',
            (user_id, permission_code))
        return cur.fetchone() is not None
    except Exception:
        logger.exception('检查用户权限码失败 (user_id=%s, permission=%s)，按无权限处理', user_id, permission_code)
        return False
    finally:
        db.close()


def permission_required(permission_code):
    """
    权限码装饰器工厂。

    用法:
        @app.route('/api/apps', methods=['POST'])
        @login_required
        @permission_required('app:create')
        def create_app():
            ...

    参数:
        permission_code: 权限码（如 'app:create', 'workflow:delete'）
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(request, 'user', {}).get('user_id', '')
            if not user_id:
                return jsonify(code=401, msg='未登录'), 401
            if not check_user_permission(user_id, permission_code):
                return jsonify(code=403, msg='缺少权限: %s' % permission_code), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
