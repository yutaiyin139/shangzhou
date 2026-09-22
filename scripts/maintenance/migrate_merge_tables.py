# -*- coding: utf-8 -*-
r"""
用户表合并迁移脚本

功能：
    1. 在 dify_accounts 表增加 phone、account_id 字段
    2. 将 users 表的 phone 数据迁移到 dify_accounts
    3. 将 user_roles 表的 user_id 从 INT 改为 VARCHAR(36)，直接关联 dify_accounts.id
    4. 删除 users 表

使用方法：
    python migrate_merge_tables.py              # 执行迁移
    python migrate_merge_tables.py --dry-run    # 仅预览
    python migrate_merge_tables.py --force      # 跳过确认
"""

import sys
import os
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


def get_db():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def migrate_tables(dry_run=False):
    """执行表合并迁移"""
    db = get_db()
    try:
        cur = db.cursor()

        # 0. 检查当前表结构
        logger.info('=' * 60)
        logger.info('0. 检查当前表结构')

        cur.execute('DESCRIBE dify_accounts')
        columns = {row['Field']: row for row in cur.fetchall()}
        logger.info(f'   dify_accounts 当前字段: {list(columns.keys())}')

        # 检查是否需要迁移
        has_phone = 'phone' in columns
        has_account_id = 'account_id' in columns
        logger.info(f'   - phone 字段: {"存在" if has_phone else "不存在"}')
        logger.info(f'   - account_id 字段: {"存在" if has_account_id else "不存在"}')

        # 检查 users 表是否存在
        cur.execute("SHOW TABLES LIKE 'users'")
        users_exists = cur.fetchone() is not None
        logger.info(f'   - users 表: {"存在" if users_exists else "不存在"}')

        # 检查 user_roles 表结构
        cur.execute('DESCRIBE user_roles')
        user_roles_cols = {row['Field']: row for row in cur.fetchall()}
        user_id_type = user_roles_cols.get('user_id', {}).get('Type', 'unknown')
        logger.info(f'   - user_roles.user_id 类型: {user_id_type}')

        # 1. 添加 dify_accounts 字段
        logger.info('-' * 60)
        logger.info('1. 修改 dify_accounts 表结构')
        if not dry_run:
            if not has_phone:
                cur.execute("ALTER TABLE dify_accounts ADD COLUMN phone VARCHAR(20) DEFAULT '' AFTER email")
                logger.info('   - 已添加 phone 字段')
            else:
                logger.info('   - phone 字段已存在，跳过')

            if not has_account_id:
                cur.execute("ALTER TABLE dify_accounts ADD COLUMN account_id VARCHAR(36) DEFAULT NULL AFTER id")
                logger.info('   - 已添加 account_id 字段')
                # 添加唯一索引
                try:
                    cur.execute("ALTER TABLE dify_accounts ADD UNIQUE KEY uk_account_id (account_id)")
                    logger.info('   - 已添加 account_id 唯一索引')
                except Exception as e:
                    logger.warning(f'   - 添加索引失败（可能已存在）: {e}')
            else:
                logger.info('   - account_id 字段已存在，跳过')
        else:
            logger.info('   [预览] 将添加 phone 和 account_id 字段')

        # 2. 迁移 users 表数据到 dify_accounts
        if users_exists:
            logger.info('-' * 60)
            logger.info('2. 迁移 users 表数据到 dify_accounts')

            # 获取 users 表数据
            cur.execute('SELECT * FROM users')
            users = cur.fetchall()
            logger.info(f'   - users 表有 {len(users)} 条记录')

            if not dry_run:
                for user in users:
                    account_id = user.get('account_id', '')
                    phone = user.get('phone', '')
                    if account_id:
                        # 更新 dify_accounts 的 phone
                        cur.execute('UPDATE dify_accounts SET phone = %s WHERE id = %s', (phone, account_id))
                        logger.info(f'   - 已更新 account_id={account_id[:8]}... 的 phone={phone}')

            else:
                logger.info('   [预览] 将迁移 phone 数据到 dify_accounts')
        else:
            logger.info('-' * 60)
            logger.info('2. users 表不存在，跳过数据迁移')

        # 3. 修改 user_roles 表结构
        logger.info('-' * 60)
        logger.info('3. 修改 user_roles 表结构')

        if 'int' in user_id_type.lower():
            if not dry_run:
                # 需要先删除旧数据（因为 user_id 类型不兼容）
                cur.execute('SELECT COUNT(*) as cnt FROM user_roles')
                cnt = cur.fetchone()['cnt']
                logger.info(f'   - user_roles 表有 {cnt} 条记录，需要迁移')

                # 获取旧的角色关联（通过 users 表关联到 dify_accounts.id）
                if users_exists:
                    cur.execute('''
                        SELECT ur.role_id, u.account_id
                        FROM user_roles ur
                        JOIN users u ON ur.user_id = u.id
                    ''')
                    old_roles = cur.fetchall()
                else:
                    old_roles = []

                # 删除旧的角色关联
                cur.execute('DELETE FROM user_roles')
                logger.info('   - 已清空 user_roles 表')

                # 修改 user_id 类型
                cur.execute('ALTER TABLE user_roles MODIFY COLUMN user_id VARCHAR(36) NOT NULL')
                logger.info('   - 已修改 user_id 为 VARCHAR(36)')

                # 重新插入角色关联
                for role in old_roles:
                    if role['account_id']:
                        cur.execute(
                            'INSERT INTO user_roles (user_id, role_id, created_at) VALUES (%s, %s, NOW())',
                            (role['account_id'], role['role_id'])
                        )
                        logger.info(f'   - 已迁移角色: user_id={role["account_id"][:8]}..., role_id={role["role_id"]}')
            else:
                logger.info('   [预览] 将修改 user_id 为 VARCHAR(36) 并迁移数据')
        else:
            logger.info('   - user_id 已经是 VARCHAR 类型，跳过')

        # 4. 确保 yutaiyin 有 admin 角色
        logger.info('-' * 60)
        logger.info('4. 确保 yutaiyin 有 admin 角色')
        if not dry_run:
            cur.execute("INSERT IGNORE INTO roles (name, description) VALUES ('admin', '系统管理员')")
            cur.execute("INSERT IGNORE INTO roles (name, description) VALUES ('user', '普通用户')")
            cur.execute('''
                INSERT IGNORE INTO user_roles (user_id, role_id)
                SELECT da.id, r.id
                FROM dify_accounts da, roles r
                WHERE da.name = 'yutaiyin' AND r.name = 'admin'
            ''')
            logger.info('   - 已确保 yutaiyin 有 admin 角色')
        else:
            logger.info('   [预览] 将确保 yutaiyin 有 admin 角色')

        # 5. 删除 users 表
        logger.info('-' * 60)
        logger.info('5. 删除 users 表')
        if users_exists:
            if not dry_run:
                # 先备份
                backup_name = f'users_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                cur.execute(f'CREATE TABLE {backup_name} AS SELECT * FROM users')
                logger.info(f'   - 已备份 users 表为 {backup_name}')

                cur.execute('DROP TABLE users')
                logger.info('   - 已删除 users 表')
            else:
                logger.info('   [预览] 将备份并删除 users 表')
        else:
            logger.info('   - users 表不存在，跳过')

        # 6. 提交
        if not dry_run:
            db.commit()
            logger.info('=' * 60)
            logger.info('✅ 迁移完成并已提交')
        else:
            logger.info('=' * 60)
            logger.info('🔍 预览模式，未执行实际变更')

        # 7. 验证
        logger.info('-' * 60)
        logger.info('6. 验证结果')
        cur.execute('DESCRIBE dify_accounts')
        columns = {row['Field'] for row in cur.fetchall()}
        logger.info(f'   dify_accounts 字段: {columns}')

        cur.execute('DESCRIBE user_roles')
        user_roles_cols = {row['Field']: row for row in cur.fetchall()}
        logger.info(f'   user_roles.user_id 类型: {user_roles_cols.get("user_id", {}).get("Type")}')

        cur.execute("SHOW TABLES LIKE 'users'")
        users_exists = cur.fetchone() is not None
        logger.info(f'   users 表: {"存在" if users_exists else "已删除"}')

        # 检查 yutaiyin
        cur.execute("SELECT id, name, email FROM dify_accounts WHERE name = 'yutaiyin'")
        yu = cur.fetchone()
        if yu:
            logger.info(f'   yutaiyin: id={yu["id"][:8]}...')
            # 检查 phone 字段是否存在
            if 'phone' in columns:
                cur.execute("SELECT phone FROM dify_accounts WHERE name = 'yutaiyin'")
                phone_row = cur.fetchone()
                if phone_row:
                    logger.info(f'   yutaiyin phone: {phone_row["phone"]}')

        # 检查角色
        cur.execute('''
            SELECT da.name, r.name AS role_name
            FROM user_roles ur
            JOIN dify_accounts da ON da.id = ur.user_id
            JOIN roles r ON r.id = ur.role_id
        ''')
        roles = cur.fetchall()
        for r in roles:
            logger.info(f'   角色: {r["name"]} -> {r["role_name"]}')

    except Exception as e:
        db.rollback()
        logger.error(f'❌ 迁移失败: {e}')
        raise
    finally:
        db.close()


def main():
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv

    logger.info('=' * 60)
    logger.info('用户表合并迁移')
    logger.info('=' * 60)

    if dry_run:
        logger.info('🔍 预览模式（dry-run）：仅显示变更，不执行')
        migrate_tables(dry_run=True)
        return

    if not force:
        logger.warning('⚠️ 此操作将合并 users 表到 dify_accounts，并删除 users 表！')
        confirm = input('确认执行？输入 "yes" 继续: ')
        if confirm.lower() != 'yes':
            logger.info('已取消')
            return

    migrate_tables(dry_run=False)
    logger.info('=' * 60)
    logger.info('迁移结束')


if __name__ == '__main__':
    main()
