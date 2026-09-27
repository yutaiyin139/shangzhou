# -*- coding: utf-8 -*-
"""
密码重置脚本
用于重置指定用户的密码。

用法：
    cd backend && python ../scripts/maintenance/reset_password.py <username> <new_password>
    或设置环境变量 RESET_USERNAME / RESET_PASSWORD 后直接运行。

账号的唯一真相源是 dify_accounts（旧 users 表已废弃并删表，不要再往回同步）。
新密码会打印到日志里吗？不会 —— 只回显账号名，口令不落到 stdout。
"""

import os
import sys

# 本脚本已归档至 scripts/maintenance/，config.py / utils/ 位于 backend/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))

from utils.helpers import _generate_password, _valid_password
from config import get_db

# ============================================================
# 配置区域 —— 优先命令行参数，次环境变量（避免将真实口令写进仓库）
# ============================================================
TARGET_USERNAME = sys.argv[1] if len(sys.argv) > 1 else os.getenv('RESET_USERNAME', '')
NEW_PASSWORD = sys.argv[2] if len(sys.argv) > 2 else os.getenv('RESET_PASSWORD', '')
# ============================================================


def reset_password(username, new_password):
    """重置指定账号的密码（账号只存在于 dify_accounts，users 表已废弃删除）"""
    if not _valid_password(new_password):
        print('错误：新密码至少 8 位且需同时包含字母和数字（与 /api/register 同一口径）')
        return False
    # 生成新的密码哈希
    salt_b64, pwd_b64 = _generate_password(new_password)
    print(f'生成密码哈希完成')
    print(f'  Salt: {salt_b64[:20]}...')
    print(f'  Hash: {pwd_b64[:20]}...')

    db = get_db()
    try:
        cur = db.cursor()

        # 1. 查找 dify_accounts 中的用户：与 /api/login 同一条口径 ——
        #    账号名精确匹配必须优先于邮箱匹配，否则“输入某人的账号名恰好
        #    等于另一人的邮箱”时，无 ORDER BY 的 LIMIT 1 会改错人的密码
        cur.execute(
            r"SELECT id, name, email FROM dify_accounts WHERE name = %s OR email = %s "
            r"ORDER BY (name = %s) DESC LIMIT 1",
            (username, username, username)
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
        db.commit()
        print(f'\n密码重置成功！')
        print(f'  用户名: {acc["name"]}')
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
    print('新密码: ****（不回显，避免落进终端录屏/历史）')
    print('-' * 50)

    confirm = input('确认重置密码？(y/N): ').strip().lower()
    if confirm == 'y':
        reset_password(TARGET_USERNAME, NEW_PASSWORD)
    else:
        print('已取消')
