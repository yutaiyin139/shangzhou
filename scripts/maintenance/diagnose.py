# -*- coding: utf-8 -*-
"""
登录问题诊断脚本
帮助排查登录时 500 错误的具体原因

用法：
    cd backend && python ../scripts/maintenance/diagnose.py [账号名]
    （缺省诊断 yutaiyin，即 README 里的初始管理员）
    要顺带验密码可设 DIAG_PASSWORD=<待验口令>
"""

import os
import sys
import traceback

# 本脚本已归档至 scripts/maintenance/，config.py / utils/ 位于 backend/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))

TARGET = (sys.argv[1] if len(sys.argv) > 1 else 'yutaiyin').strip()
ACCOUNT = None    # 第 [3] 步查到的账号行，第 [4] 步复用

print('=' * 60)
print(f'登录问题诊断（账号：{TARGET}）')
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
# 注意：这里刻意没有 'users' —— 账号的唯一真相源是 dify_accounts，
# 旧 users 表已合并进 dify_accounts 并删表（再把它的名字列进来只会
# 让一次正常的体检报一个假的“表不存在”）
required_tables = [
    'roles', 'user_roles', 'permissions', 'role_permissions',
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

    # 账号只看 dify_accounts：与 /api/login 同一条口径（账号名精确匹配优先于邮箱）
    cur.execute(r'''
        SELECT id, name, email, phone, status, password, password_salt
        FROM dify_accounts
        WHERE name = %s OR email = %s
        ORDER BY (name = %s) DESC
        LIMIT 1
    ''', (TARGET, TARGET, TARGET))
    acc = cur.fetchone()
    if acc:
        print(f'  ✓ dify_accounts 中找到: {acc["name"]} <{acc["email"]}> id={acc["id"]}')
        print(f'    状态: {acc["status"]}，密码哈希已存: {bool(acc["password"] and acc["password_salt"])}')
        if acc['status'] != 'active':
            print(f'  ! 状态不是 active，登录会被拒（账号已被禁用）')
    else:
        print(f'  ✗ dify_accounts 中未找到 {TARGET}')

    # 角色：登录后的 admin/user 级别全看这张角联表
    if acc:
        cur.execute(r'''
            SELECT GROUP_CONCAT(r.name ORDER BY r.name SEPARATOR ', ') AS role_name,
                   MAX(r.name = 'admin') AS is_admin
            FROM user_roles ur JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = %s
        ''', (acc['id'],))
        rrow = cur.fetchone() or {}
        print(f'  角色: {rrow.get("role_name") or "(未分配)"}；登录后的权限级别: '
              f'{"admin" if rrow.get("is_admin") else "user"}（只认角色名 == admin）')

    cur.execute(r'SELECT COUNT(*) as cnt FROM roles')
    print(f'  角色总数: {cur.fetchone()["cnt"]}')

    ACCOUNT = acc        # 第 [4] 步直接复用这一行，不再查一次库
    db.close()
except Exception as e:
    print(f'  ✗ 检查用户失败: {e}')
    traceback.print_exc()

# 4. 测试密码验证
print('\n[4] 测试密码验证...')
try:
    from utils.helpers import _compare_password

    acc = ACCOUNT
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
