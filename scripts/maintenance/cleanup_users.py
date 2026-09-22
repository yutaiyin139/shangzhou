# -*- coding: utf-8 -*-
r"""
用户表数据清理脚本（直接连接，不依赖 DBUtils）

目标：
    1. 清理 dify_accounts 和 users 表中不匹配的多余数据
    2. 确保只保留 username=yutaiyin 的用户
    3. 将目标账号密码重置为环境变量 CLEANUP_TARGET_PASSWORD 指定的值

使用方法：
    python cleanup_users.py              # 执行清理
    python cleanup_users.py --dry-run    # 仅预览
    python cleanup_users.py --force      # 跳过确认
"""

import sys
import os
import uuid
import hashlib
import base64
import logging
from datetime import datetime

import pymysql
import pymysql.cursors

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 数据库配置（从环境变量/.env 读取，切勿在脚本中硬编码真实密码）
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'szagent'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

# 目标账号与重置密码均从环境变量注入，不再硬编码到仓库
TARGET_USERNAME = os.getenv('CLEANUP_TARGET_USERNAME', '')
TARGET_PASSWORD = os.getenv('CLEANUP_TARGET_PASSWORD', '')


def get_db():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def generate_password(password):
    """生成密码哈希（PBKDF2-SHA256，与系统一致）"""
    import binascii
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 10000)
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    pwd_b64 = base64.b64encode(binascii.hexlify(dk)).decode('utf-8')
    return salt_b64, pwd_b64


def cleanup_users_data(dry_run=False):
    """清理多余用户数据，仅保留 yutaiyin"""
    db = get_db()
    try:
        cur = db.cursor()

        # 1. 查看当前数据
        logger.info('=' * 60)
        logger.info('当前数据预览:')
        cur.execute('SELECT id, name, email, status FROM dify_accounts')
        all_accounts = cur.fetchall()
        logger.info(f'  dify_accounts 表有 {len(all_accounts)} 个账号:')
        for acc in all_accounts:
            logger.info(f'    - id={acc["id"][:8]}..., name={acc["name"]}, email={acc["email"]}, status={acc["status"]}')

        cur.execute('SELECT u.id, u.account_id, u.phone, u.status FROM users u')
        all_users = cur.fetchall()
        logger.info(f'  users 表有 {len(all_users)} 条记录:')
        for u in all_users:
            logger.info(f'    - id={u["id"]}, account_id={u["account_id"][:8] if u["account_id"] else "None"}..., phone={u["phone"]}, status={u["status"]}')

        # 2. 查找 yutaiyin 的账号
        cur.execute(r'SELECT id, name, email, password, password_salt FROM dify_accounts WHERE name = %s', (TARGET_USERNAME,))
        target_acc = cur.fetchone()

        if not target_acc:
            logger.error(f'❌ dify_accounts 表中未找到 {TARGET_USERNAME} 账号！')
            if not dry_run:
                # 创建 yutaiyin 账号
                logger.info(f'📋 正在创建 {TARGET_USERNAME} 账号...')
                salt_b64, pwd_b64 = generate_password(TARGET_PASSWORD)
                account_uuid = str(uuid.uuid4())
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cur.execute(r'''INSERT INTO dify_accounts (id, name, email, password, password_salt,
                                                           interface_language, interface_theme, status, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, 'zh-Hans', 'light', 'active', %s, %s)''',
                            (account_uuid, TARGET_USERNAME, f'{TARGET_USERNAME}@shangzhou.local', pwd_b64, salt_b64, ts, ts))
                target_acc_id = account_uuid
                db.commit()
                logger.info(f'✅ 已创建 {TARGET_USERNAME} 账号, id={target_acc_id}')
            else:
                logger.info(f'🔍 预览模式：将创建 {TARGET_USERNAME} 账号')
                return
        else:
            target_acc_id = target_acc['id']
            logger.info(f'✅ 找到 {TARGET_USERNAME} 账号, id={target_acc_id}')

        # 3. 清理 dify_tenant_account_joins（删除非 yutaiyin 的绑定）
        logger.info('-' * 60)
        logger.info('📋 清理 dify_tenant_account_joins...')
        if not dry_run:
            cur.execute(r'DELETE FROM dify_tenant_account_joins WHERE account_id != %s', (target_acc_id,))
            logger.info(f'  ✅ 已清理非 {TARGET_USERNAME} 的工作区绑定')

        # 4. 清理 dify_accounts（删除非 yutaiyin 的账号）
        logger.info('-' * 60)
        logger.info('📋 清理 dify_accounts 中的多余账号...')
        if not dry_run:
            cur.execute(r'DELETE FROM dify_accounts WHERE id != %s', (target_acc_id,))
            logger.info(f'  ✅ 已删除 dify_accounts 中除 {TARGET_USERNAME} 外的所有账号')
        else:
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_accounts WHERE id != %s', (target_acc_id,))
            cnt = cur.fetchone()['cnt']
            logger.info(f'  🔍 预览：将删除 {cnt} 个多余账号')

        # 5. 重置 yutaiyin 密码
        logger.info('-' * 60)
        logger.info(f'📋 重置 {TARGET_USERNAME} 密码为 {TARGET_PASSWORD}...')
        if not dry_run:
            salt_b64, pwd_b64 = generate_password(TARGET_PASSWORD)
            cur.execute(r'UPDATE dify_accounts SET password = %s, password_salt = %s, status = %s WHERE id = %s',
                        (pwd_b64, salt_b64, 'active', target_acc_id))
            logger.info(f'  ✅ 密码已重置')
        else:
            logger.info(f'  🔍 预览：将重置密码为 {TARGET_PASSWORD}')

        # 6. 清理 users 表
        logger.info('-' * 60)
        logger.info('📋 清理 users 表...')
        if not dry_run:
            # 删除所有角色关联
            cur.execute(r'DELETE FROM user_roles')
            # 删除所有 users 记录
            cur.execute(r'DELETE FROM users')
            # 插入 yutaiyin 的 users 记录
            cur.execute(r'INSERT INTO users (account_id, phone, status, created_at, updated_at) VALUES (%s, %s, 1, %s, %s)',
                        (target_acc_id, '', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            user_id = cur.lastrowid
            logger.info(f'  ✅ users 表已清理，仅保留 {TARGET_USERNAME} (user_id={user_id})')
        else:
            logger.info(f'  🔍 预览：将清空 users 表，仅插入 {TARGET_USERNAME} 记录')

        # 7. 确保角色存在并分配给 yutaiyin
        logger.info('-' * 60)
        logger.info('📋 配置角色...')
        if not dry_run:
            cur.execute(r"INSERT IGNORE INTO roles (name, description) VALUES ('admin', '系统管理员')")
            cur.execute(r"INSERT IGNORE INTO roles (name, description) VALUES ('user', '普通用户')")
            # 给用户分配 admin 角色
            cur.execute(r'''
                INSERT IGNORE INTO user_roles (user_id, role_id)
                SELECT %s, id FROM roles WHERE name = 'admin'
            ''', (user_id,))
            logger.info(f'  ✅ 已分配 admin 角色')
        else:
            logger.info(f'  🔍 预览：将创建 admin/user 角色并分配给 {TARGET_USERNAME}')

        # 8. 清理孤立的工作区
        logger.info('-' * 60)
        logger.info('📋 清理关联表...')
        if not dry_run:
            cur.execute(r'''
                DELETE t FROM dify_tenants t
                LEFT JOIN dify_tenant_account_joins j ON j.tenant_id = t.id
                WHERE j.tenant_id IS NULL
            ''')
            logger.info(f'  ✅ 已清理孤立工作区')

        # 提交所有变更
        if not dry_run:
            db.commit()
            logger.info('=' * 60)
            logger.info('✅ 所有变更已提交')
        else:
            logger.info('=' * 60)
            logger.info('🔍 预览模式，未执行实际变更')

        # 最终验证
        logger.info('-' * 60)
        logger.info('📋 最终验证...')
        cur.execute('SELECT COUNT(*) as cnt FROM dify_accounts')
        acc_cnt = cur.fetchone()['cnt']
        cur.execute('SELECT COUNT(*) as cnt FROM users')
        user_cnt = cur.fetchone()['cnt']
        cur.execute(r'SELECT name, email, status FROM dify_accounts WHERE name = %s', (TARGET_USERNAME,))
        yu = cur.fetchone()
        logger.info(f'  dify_accounts: {acc_cnt} 个账号')
        logger.info(f'  users: {user_cnt} 条记录')
        if yu:
            logger.info(f'  {TARGET_USERNAME}: name={yu["name"]}, email={yu["email"]}, status={yu["status"]}')

    except Exception as e:
        db.rollback()
        logger.error(f'❌ 清理失败: {e}')
        raise
    finally:
        db.close()


def main():
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv

    logger.info('=' * 60)
    logger.info('用户表数据清理')
    logger.info(f'目标：仅保留 {TARGET_USERNAME}，密码 {TARGET_PASSWORD}')
    logger.info('=' * 60)

    if dry_run:
        logger.info('🔍 预览模式（dry-run）：仅显示变更，不执行')
        cleanup_users_data(dry_run=True)
        return

    if not force:
        logger.warning(f'⚠️ 此操作将删除除 {TARGET_USERNAME} 外的所有用户数据！')
        confirm = input('确认执行？输入 "yes" 继续: ')
        if confirm.lower() != 'yes':
            logger.info('已取消')
            return

    cleanup_users_data(dry_run=False)
    logger.info('=' * 60)
    logger.info('清理完成')


if __name__ == '__main__':
    main()
