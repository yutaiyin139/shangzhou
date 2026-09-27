# -*- coding: utf-8 -*-
"""
全局 API 鉴权闸门：默认拒绝 + 显式公开白名单。

为什么需要它：本项目此前的鉴权是"逐路由贴 @login_required"，而 32 个路由模块里有
27 个一处都没贴。实测（匿名 GET 全量扫描）未登录就能拿到 60 多个接口的真实数据，
包括 /api/users（13 条用户记录）、/api/conversations 与 /api/messages/<id>/thoughts
（对话内容与思考链）、/api/agents/<id>/access-points（**连访问点 token 一起给出**）。
一处处贴装饰器要改几百个函数，且以后新增路由默认还是裸的，所以改成默认拒绝。

模式由环境变量 REQUIRE_LOGIN_FOR_API 控制：
    off     不拦截（默认，保持历史行为，便于灰度）
    warn    照常放行，但把"strict 下会被拒"的请求记进日志——用来发现漏网的豁免项
    strict  未登录一律 401

豁免的判定标准只有一条：**该接口的凭证已经体现在 URL/请求体里，或它设计上就是公开的**。
新增公开接口必须同时在这里登记，不能靠"这个接口正好没加装饰器"。
"""
import logging
import os
import re

from flask import jsonify, request

logger = logging.getLogger(__name__)

# 完全匹配：登录流程本身与健康探针
PUBLIC_EXACT = {
    '/api/health',
    '/api/ping',
    '/api/login',
    '/api/logout',      # 登出对无效 token 也应幂等返回，不应要求再次鉴权
    '/api/refresh',
    '/api/register',
    '/api/register-config',
    '/api/password/forgot',
    '/api/password/reset',
    '/api/model-types',  # 静态枚举，不含任何业务数据
    '/api/tools/oauth/callback',  # 工具 OAuth 回调：第三方授权服务器的浏览器回跳
}

# 前缀匹配：凭证在路径里的公开入口
PUBLIC_PREFIXES = (
    '/api/web-agent/',                    # 智能体 Web 访问点：<token> 即凭证
    '/api/share/',                        # 分享页 chat/workflow：<token> 即凭证
    '/api/workflows/human-input-forms/',  # 人工输入表单：<formKey> 即凭证
    '/api/webhooks/trigger/',             # 入站 Webhook：外部系统 POST，webhook_key 即凭证
    '/api/oauth/callback/',               # 第三方授权回跳：浏览器导航，带不了 Authorization
)

# 正则匹配：服务 API 用自己的 AppKey 校验（见 routes/agents.py 的 app_keys 校验）
PUBLIC_PATTERNS = (
    re.compile(r'^/api/agents/\d+/chat$'),
    re.compile(r'^/api/multi-agent/\d+/chat$'),
)


def is_public_path(path):
    if path in PUBLIC_EXACT:
        return True
    if any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return True
    return any(rx.match(path) for rx in PUBLIC_PATTERNS)


def _normalize(raw):
    raw = (raw or '').strip().lower()
    # 'strict' 本身就是文档推荐值，不能再只认 true/on/enforce
    if raw in ('1', 'true', 'on', 'enforce', 'strict'):
        return 'strict'
    if raw in ('warn', 'log', 'observe'):
        return 'warn'
    if raw in ('0', 'false', 'off', '', 'none'):
        return 'off'
    logger.warning('REQUIRE_LOGIN_FOR_API 取值 %r 无法识别，按 off 处理', raw)
    return 'off'


def get_guard_mode():
    """从环境变量读闸门模式（兼容历史布尔值 true/false）。"""
    return _normalize(os.environ.get('REQUIRE_LOGIN_FOR_API'))


def resolve_mode():
    """请求时的实际模式，优先级：

    1. app.config['REQUIRE_LOGIN_FOR_API'] —— 给测试显式开启用（安全用例就靠它）
    2. app.config['TESTING'] 为真 -> off。本仓 E2E 用例直接 python e2e_xxx.py 跑，
       均假定接口不需登录；不这样处理会让整个测试集因安全加固而全红。
    3. 环境变量 REQUIRE_LOGIN_FOR_API

    逐请求解析而不是安装时读一次：便于 warn -> strict 灰度时无需重启进程。
    """
    try:
        from flask import current_app
        forced = current_app.config.get('REQUIRE_LOGIN_FOR_API')
    except Exception:
        return get_guard_mode()
    if forced is not None:
        return _normalize(forced if isinstance(forced, str) else str(forced))
    if current_app.config.get('TESTING'):
        return 'off'
    return get_guard_mode()


def install_api_guard(app):
    """在 create_app / 模块导入时调用。返回是否已注册钩子。

    即使当前环境是 off 也照旧注册：因为模式是逐请求解析的，
    测试可以通过 app.config 强制打开，环境变量也可以在进程不改启动值的情况下调整。
    """
    @app.before_request
    def _api_guard():
        mode = resolve_mode()
        if mode == 'off':
            return None
        path = request.path or ''
        # 静态资源、/v1 服务 API（Blueprint 自带 AppKey 校验）不在闸门职责内
        if not path.startswith('/api/'):
            return None
        if request.method == 'OPTIONS' or is_public_path(path):
            return None

        # 复用各路由装饰器同一套取值与校验逻辑，避免出现第二种"登录态"定义
        from utils.auth import extract_token_from_request, verify_token

        token = extract_token_from_request()
        if token:
            payload, error = verify_token(token)
            if not error:
                request.user = {
                    'user_id': payload.get('user_id'),
                    'email': payload.get('email'),
                    'username': payload.get('username', ''),
                    'role': payload.get('role', ''),
                }
                # 登录后的第二道卡：资源归属（utils/ownership.py，模式由 .env 的
                # OWNERSHIP_CHECK_MODE 控制，缺省 warn 只记日志，不影响现有使用）
                from utils.ownership import check_request as _check_ownership
                denied = _check_ownership()
                if denied is not None:
                    return denied
                return None
            reason = error
        else:
            reason = '未提供认证令牌，请先登录'

        if mode == 'warn':
            logger.warning('[api-guard:warn] 未登录访问 %s %s —— strict 模式下会被拒绝',
                           request.method, path)
            return None
        return jsonify(code=401, msg=reason), 401

    logger.info('API 鉴权闸门已装载，当前模式=%s（豁免 %d 条精确 + %d 个前缀 + %d 条正则）',
                get_guard_mode(), len(PUBLIC_EXACT), len(PUBLIC_PREFIXES), len(PUBLIC_PATTERNS))
    return True
