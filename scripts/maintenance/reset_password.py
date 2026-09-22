# -*- coding: utf-8 -*-
"""
密码重置脚本
用于重置指定用户的密码。

用法：
    cd backend && python ../scripts/maintenance/reset_password.py <username> <new_password>
    或设置环境变量 RESET_USERNAME / RESET_PASSWORD 后直接运行。
"""

import os
import sys

# 本脚本已归档至 scripts/maintenance/，config.py / utils/ 位于 backend/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))

from utils.helpers import _generate_password
from config import get_db

# ============================================================
# 配置区域 —— 优先命令行参数，次环境变量（避免将真实口令写进仓库）
# ============================================================
TARGET_USERNAME = sys.argv[1] if len(sys.argv) > 1 else os.getenv('RESET_USERNAME', '')
NEW_PASSWORD = sys.argv[2] if len(sys.argv) > 2 else os.getenv('RESET_PASSWORD', '')
# ============================================================


def reset_password(username, new_password):
    """
    重置指定用户的密码。
    同时更新 dify_accounts 和 users 表。
    """
    # 生成新的密码哈希
    salt_b64, pwd_b64 = _generate_password(new_password)
    print(f'生成密码哈希完成')
    print(f'  Salt: {salt_b64[:20]}...')
    print(f'  Hash: {pwd_b64[:20]}...')

    db = get_db()
    try:
        cur = db.cursor()

        # 1. 查找 dify_accounts 中的用户
        cur.execute(
            r"SELECT id, name, email FROM dify_accounts WHERE name = %s OR email = %s LIMIT 1",
            (username, username)
        )
        acc = cur.fetchone()
        if not acc:
            print(f'错误：在 dify_accounts 中未找到用户 "{username}"')
            return False

        print(f'找到账号: {acc["name"]} ({acc["email"]})')

        # 2. 更新 dify_accounts 密码
        cur.execute(
            r'UPDATE dify_accounts SET password = %s, password_salt = %s WHERE id = %s',
            (pwd_b64, salt_b64, acc['id'])
        )
        print(f'已更新 dify_accounts 密码')

        # 3. users 表已合并到 dify_accounts，无需额外同步
        print(f'users 表已合并到 dify_accounts，跳过同步')

        db.commit()
        print(f'\n密码重置成功！')
        print(f'  用户名: {username}')
        print(f'  新密码: {new_password}')
        return True

    except Exception as e:
        db.rollback()
        print(f'错误：{e}')
        return False
    finally:
        db.close()


if __name__ == '__main__':
    print('=' * 50)
    print('密码重置工具')
    print('=' * 50)
    print(f'目标用户: {TARGET_USERNAME}')
    print(f'新密码: {NEW_PASSWORD}')
    print('-' * 50)

    confirm = input('确认重置密码？(y/N): ').strip().lower()
    if confirm == 'y':
        reset_password(TARGET_USERNAME, NEW_PASSWORD)
    else:
        print('已取消')
