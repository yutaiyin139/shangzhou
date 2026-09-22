# -*- coding: utf-8 -*-
"""
登录问题诊断脚本
帮助排查登录时 500 错误的具体原因

用法：
    cd backend && python ../scripts/maintenance/diagnose.py
"""

import os
import sys
import traceback

# 本脚本已归档至 scripts/maintenance/，config.py / utils/ 位于 backend/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))

print('=' * 60)
print('登录问题诊断')
print('=' * 60)

# 1. 检查数据库连接
print('\n[1] 检查数据库连接...')
try:
    from config import get_db
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT 1')
    result = cur.fetchone()
    db.close()
    print('  ✓ 数据库连接正常')
except Exception as e:
    print(f'  ✗ 数据库连接失败: {e}')
    traceback.print_exc()
    sys.exit(1)

# 2. 检查必要表是否存在
print('\n[2] 检查数据库表...')
required_tables = [
    'users', 'roles', 'user_roles', 'permissions', 'role_permissions',
    'dify_accounts', 'dify_tenants', 'dify_tenant_account_joins'
]
try:
    db = get_db()
    cur = db.cursor()
    cur.execute('SHOW TABLES')
    existing_tables = [row[list(row.keys())[0]] for row in cur.fetchall()]
    db.close()

    for table in required_tables:
        if table in existing_tables:
            print(f'  ✓ {table}')
        else:
            print(f'  ✗ {table} - 不存在！')
except Exception as e:
    print(f'  ✗ 检查表失败: {e}')
    traceback.print_exc()

# 3. 检查用户数据
print('\n[3] 检查用户数据...')
try:
    db = get_db()
    cur = db.cursor()

    # 检查 dify_accounts
    cur.execute(r"SELECT id, name, email, status FROM dify_accounts WHERE name = 'yutaiyin'")
    acc = cur.fetchone()
    if acc:
        print(f'  ✓ dify_accounts 中找到: {acc["name"]} ({acc["email"]}), 状态: {acc["status"]}')
    else:
        print(f'  ✗ dify_accounts 中未找到 yutaiyin')

    # 检查 users
    cur.execute(r"SELECT id, username, email, status FROM users WHERE username = 'yutaiyin'")
    user = cur.fetchone()
    if user:
        print(f'  ✓ users 中找到: {user["username"]} ({user["email"]}), 状态: {user["status"]}')
    else:
        print(f'  ✗ users 中未找到 yutaiyin')

    # 检查角色
    cur.execute(r"SELECT COUNT(*) as cnt FROM roles")
    role_count = cur.fetchone()['cnt']
    print(f'  角色数量: {role_count}')

    db.close()
except Exception as e:
    print(f'  ✗ 检查用户失败: {e}')
    traceback.print_exc()

# 4. 测试密码验证
print('\n[4] 测试密码验证...')
try:
    from utils.helpers import _compare_password

    db = get_db()
    cur = db.cursor()
    cur.execute(r"SELECT password, password_salt FROM dify_accounts WHERE name = 'yutaiyin'")
    acc = cur.fetchone()
    db.close()

    if acc:
        test_password = os.getenv('DIAG_PASSWORD', '')
        if test_password:
            is_valid = _compare_password(test_password, acc['password'], acc['password_salt'])
            if is_valid:
                print('  ✓ 传入密码验证通过')
            else:
                print('  ✗ 传入密码验证失败')
                print(f'    可能需要重置密码')
        else:
            print('  · 未设置 DIAG_PASSWORD 环境变量，跳过密码校验')
    else:
        print(f'  ✗ 无法获取用户密码信息')
except Exception as e:
    print(f'  ✗ 密码验证失败: {e}')
    traceback.print_exc()

# 5. 测试 JWT 生成
print('\n[5] 测试 JWT Token 生成...')
try:
    from utils.auth import generate_token_pair
    tokens = generate_token_pair(
        user_id='test-id',
        email='test@test.com',
        username='testuser',
        role='admin'
    )
    if tokens and 'access_token' in tokens:
        print(f'  ✓ JWT Token 生成正常')
        print(f'    token_type: {tokens["token_type"]}')
        print(f'    expires_in: {tokens["expires_in"]}')
    else:
        print(f'  ✗ JWT Token 生成失败')
except Exception as e:
    print(f'  ✗ JWT Token 生成失败: {e}')
    traceback.print_exc()

# 6. 检查审计日志表
print('\n[6] 检查审计日志表...')
try:
    db = get_db()
    cur = db.cursor()
    cur.execute('SHOW TABLES LIKE "dify_audit_logs"')
    result = cur.fetchone()
    if result:
        print(f'  ✓ dify_audit_logs 表存在')
    else:
        print(f'  ✗ dify_audit_logs 表不存在')
    db.close()
except Exception as e:
    print(f'  ✗ 检查失败: {e}')

print('\n' + '=' * 60)
print('诊断完成')
print('=' * 60)
