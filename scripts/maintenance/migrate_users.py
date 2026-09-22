# -*- coding: utf-8 -*-
r"""
用户表合并数据迁移脚本

用途：
    1. 备份现有 users 表数据
    2. 将旧 users 表的 account_id 关联同步到新结构
    3. 从 dify_accounts 同步缺失的活跃账号到 users 表
    4. 清理冗余字段数据（如果存在）

使用方法：
    python migrate_users.py              # 执行迁移
    python migrate_users.py --dry-run    # 仅预览，不执行
    python migrate_users.py --backup     # 仅备份
"""

import sys
import os
import logging
from datetime import datetime

# 添加后端目录到路径（本脚本已归档至 scripts/maintenance/，config.py 位于 backend/）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))

from config import get_db
from utils.helpers import now

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def backup_users_table():
    """备份 users 表"""
    db = get_db()
    try:
        cur = db.cursor()
        backup_table = f'users_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        cur.execute(f'CREATE TABLE IF NOT EXISTS {backup_table} AS SELECT * FROM users')
        cur.execute(f'SELECT COUNT(*) as cnt FROM {backup_table}')
        result = cur.fetchone()
        db.commit()
        logger.info(f'✅ 备份完成: {backup_table} ({result["cnt"]} 条记录)')
        return backup_table
    except Exception as e:
        logger.error(f'❌ 备份失败: {e}')
        return None
    finally:
        db.close()


def migrate_users_data(dry_run=False):
    """
    执行用户表合并迁移

    迁移逻辑：
    1. 确保 users 表结构正确（仅有 id, account_id, phone, status, created_at, updated_at）
    2. 从 dify_accounts 同步所有活跃账号到 users 表
    3. 修复旧的 account_id 关联
    """
    db = get_db()
    try:
        cur = db.cursor()

        # 检查 users 表当前结构
        cur.execute('DESCRIBE users')
        columns = {row['Field'] for row in cur.fetchall()}
        logger.info(f'当前 users 表字段: {columns}')

        # 检查是否有冗余字段需要清理
        redundant_fields = columns - {'id', 'account_id', 'phone', 'status', 'created_at', 'updated_at'}
        if redundant_fields:
            logger.warning(f'⚠️ 发现冗余字段: {redundant_fields}')
            if not dry_run:
                for field in redundant_fields:
                    try:
                        cur.execute(f'ALTER TABLE users DROP COLUMN {field}')
                        logger.info(f'  ✅ 已删除冗余字段: {field}')
                    except Exception as e:
                        logger.warning(f'  ⚠️ 删除字段 {field} 失败: {e}')

        # 统计当前数据
        cur.execute('SELECT COUNT(*) as cnt FROM users')
        users_count = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) as cnt FROM dify_accounts WHERE status = 'active'")
        accounts_count = cur.fetchone()['cnt']
        logger.info(f'当前数据: users={users_count}, dify_accounts(active)={accounts_count}')

        # 同步缺失的 dify_accounts 到 users 表
        cur.execute(r'''
            SELECT da.id, da.name, da.email
            FROM dify_accounts da
            LEFT JOIN users u ON u.account_id = da.id
            WHERE da.status = 'active' AND u.id IS NULL
        ''')
        missing_accounts = cur.fetchall()

        if missing_accounts:
            logger.info(f'📋 需要同步 {len(missing_accounts)} 个账号到 users 表:')
            for acc in missing_accounts:
                logger.info(f'  - {acc["name"]} ({acc["email"]})')
                if not dry_run:
                    cur.execute(
                        r'INSERT IGNORE INTO users (account_id, status, created_at, updated_at) VALUES (%s, 1, %s, %s)',
                        (str(acc['id']), now(), now())
                    )
        else:
            logger.info('✅ 无需同步，所有活跃账号已关联')

        # 检查孤立 users 记录（account_id 在 dify_accounts 中不存在）
        cur.execute(r'''
            SELECT u.id, u.account_id
            FROM users u
            LEFT JOIN dify_accounts da ON da.id = u.account_id
            WHERE da.id IS NULL
        ''')
        orphan_users = cur.fetchall()
        if orphan_users:
            logger.warning(f'⚠️ 发现 {len(orphan_users)} 条孤立 users 记录:')
            for u in orphan_users:
                logger.warning(f'  - users.id={u["id"]}, account_id={u["account_id"]}')
            if not dry_run:
                # 可选：删除孤立记录（默认保留）
                logger.info('  （孤立记录已保留，请手动处理）')

        # 确保默认角色存在
        cur.execute(r"INSERT IGNORE INTO roles (name, description) VALUES ('admin', '系统管理员')")
        cur.execute(r"INSERT IGNORE INTO roles (name, description) VALUES ('user', '普通用户')")

        # 为 yutaiyin 赋予 admin 角色
        cur.execute(r'''
            INSERT IGNORE INTO user_roles (user_id, role_id)
            SELECT u.id, r.id
            FROM users u
            JOIN dify_accounts da ON da.id = u.account_id
            CROSS JOIN roles r
            WHERE da.name = 'yutaiyin' AND r.name = 'admin'
        ''')

        if not dry_run:
            db.commit()
            logger.info('✅ 迁移完成并已提交')
        else:
            logger.info('🔍 预览模式，未执行实际变更')

        # 最终统计
        cur.execute('SELECT COUNT(*) as cnt FROM users')
        final_users = cur.fetchone()['cnt']
        cur.execute('SELECT COUNT(*) as cnt FROM user_roles')
        final_roles = cur.fetchone()['cnt']
        logger.info(f'最终数据: users={final_users}, user_roles={final_roles}')

    except Exception as e:
        db.rollback()
        logger.error(f'❌ 迁移失败: {e}')
        raise
    finally:
        db.close()


def main():
    """主函数"""
    dry_run = '--dry-run' in sys.argv
    backup_only = '--backup' in sys.argv

    logger.info('=' * 60)
    logger.info('用户表合并数据迁移')
    logger.info('=' * 60)

    if dry_run:
        logger.info('🔍 预览模式（dry-run）：仅显示变更，不执行')
    if backup_only:
        logger.info('💾 仅备份模式')
        backup_users_table()
        return

    # 先备份
    logger.info('📦 开始备份...')
    backup_table = backup_users_table()
    if not backup_table:
        logger.error('备份失败，终止迁移')
        return

    # 执行迁移
    logger.info('🚀 开始迁移...')
    migrate_users_data(dry_run=dry_run)

    logger.info('=' * 60)
    logger.info('迁移结束')


if __name__ == '__main__':
    main()
