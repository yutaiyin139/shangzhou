# -*- coding: utf-8 -*-
"""
数据迁移脚本测试
测试迁移函数的核心逻辑（不依赖实际数据库连接）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from unittest.mock import patch, MagicMock, call


def _mock_pg():
    """创建 psycopg2 的 mock 模块"""
    mock_pg = MagicMock()
    return mock_pg


def test_pg_table_exists():
    """测试检查 PostgreSQL 表是否存在"""
    mock_pg = _mock_pg()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = (1,)
    mock_conn.cursor.return_value = mock_cur
    mock_pg.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'psycopg2': mock_pg, 'psycopg2.extras': MagicMock()}):
        from migrate_from_dify import pg_table_exists
        result = pg_table_exists('tenants')

        assert result is True
        mock_cur.execute.assert_called_once()
    print('[PASS] test_pg_table_exists')


def test_pg_table_not_exists():
    """测试检查不存在的表"""
    mock_pg = _mock_pg()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = None
    mock_conn.cursor.return_value = mock_cur
    mock_pg.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'psycopg2': mock_pg, 'psycopg2.extras': MagicMock()}):
        from migrate_from_dify import pg_table_exists
        result = pg_table_exists('nonexistent_table')

        assert result is False
    print('[PASS] test_pg_table_not_exists')


def test_migrate_table_empty():
    """测试迁移空表"""
    mock_pg = _mock_pg()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cur
    mock_pg.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'psycopg2': mock_pg, 'psycopg2.extras': MagicMock()}):
        from migrate_from_dify import migrate_table
        result = migrate_table('tenants', 'dify_tenants', ['id', 'name'])

        assert result == 0
    print('[PASS] test_migrate_table_empty')


def test_migrate_table_with_data():
    """测试迁移有数据的表"""
    mock_pg = _mock_pg()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [
        {'id': 'tenant-1', 'name': '测试租户', 'plan': 'basic', 'status': 'normal',
         'created_at': '2024-01-01', 'updated_at': '2024-01-01'},
        {'id': 'tenant-2', 'name': '企业租户', 'plan': 'enterprise', 'status': 'normal',
         'created_at': '2024-01-02', 'updated_at': '2024-01-02'},
    ]
    mock_conn.cursor.return_value = mock_cur
    mock_pg.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'psycopg2': mock_pg, 'psycopg2.extras': MagicMock()}):
        with patch('config.get_db') as mock_get_db:
            mock_mysql_conn = MagicMock()
            mock_mysql_cur = MagicMock()
            mock_mysql_cur.rowcount = 1  # 插入成功
            mock_mysql_conn.cursor.return_value = mock_mysql_cur
            mock_get_db.return_value = mock_mysql_conn

            from migrate_from_dify import migrate_table
            result = migrate_table('tenants', 'dify_tenants',
                                   ['id', 'name', 'plan', 'status', 'created_at', 'updated_at'])

            assert result == 2
            assert mock_mysql_cur.execute.call_count == 2
    print('[PASS] test_migrate_table_with_data')


def test_migrate_table_with_json_data():
    """测试迁移包含 JSON 数据的表"""
    mock_pg = _mock_pg()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # 包含 dict 和 list 的数据
    mock_cur.fetchall.return_value = [
        {'id': 'app-1', 'name': '测试应用', 'graph': {'nodes': [], 'edges': []},
         'config': {'key': 'value'}},
    ]
    mock_conn.cursor.return_value = mock_cur
    mock_pg.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'psycopg2': mock_pg, 'psycopg2.extras': MagicMock()}):
        with patch('config.get_db') as mock_get_db:
            mock_mysql_conn = MagicMock()
            mock_mysql_cur = MagicMock()
            mock_mysql_cur.rowcount = 1
            mock_mysql_conn.cursor.return_value = mock_mysql_cur
            mock_get_db.return_value = mock_mysql_conn

            from migrate_from_dify import migrate_table
            result = migrate_table('apps', 'dify_apps',
                                   ['id', 'name', 'graph', 'config'])

            assert result == 1
            # 验证 JSON 序列化
            call_args = mock_mysql_cur.execute.call_args
            values = call_args[0][1]
            # graph 和 config 应该被序列化为 JSON 字符串
            assert isinstance(values[2], str)  # graph
            assert isinstance(values[3], str)  # config
    print('[PASS] test_migrate_table_with_json_data')


def test_migrate_table_with_transform():
    """测试使用 transform 函数"""
    mock_pg = _mock_pg()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [
        {'id': '1', 'name': 'test', 'extra_field': 'value'},
    ]
    mock_conn.cursor.return_value = mock_cur
    mock_pg.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'psycopg2': mock_pg, 'psycopg2.extras': MagicMock()}):
        with patch('config.get_db') as mock_get_db:
            mock_mysql_conn = MagicMock()
            mock_mysql_cur = MagicMock()
            mock_mysql_cur.rowcount = 1
            mock_mysql_conn.cursor.return_value = mock_mysql_cur
            mock_get_db.return_value = mock_mysql_conn

            # 自定义 transform 函数
            def my_transform(row, values, columns):
                values[1] = row.get('name', '').upper()
                return values

            from migrate_from_dify import migrate_table
            result = migrate_table('test', 'test_table',
                                   ['id', 'name'], transform=my_transform)

            assert result == 1
            # 验证 transform 被应用
            call_args = mock_mysql_cur.execute.call_args
            values = call_args[0][1]
            assert values[1] == 'TEST'
    print('[PASS] test_migrate_table_with_transform')


def test_migrate_table_if_exists_skipped():
    """测试迁移不存在的表（跳过）"""
    mock_pg = _mock_pg()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = None  # 表不存在
    mock_conn.cursor.return_value = mock_cur
    mock_pg.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'psycopg2': mock_pg, 'psycopg2.extras': MagicMock()}):
        from migrate_from_dify import migrate_table_if_exists
        result = migrate_table_if_exists('nonexistent', 'dify_table', ['id'])

        assert result == 0
    print('[PASS] test_migrate_table_if_exists_skipped')


def test_ensure_dify_tables():
    """测试创建表"""
    with patch('config.get_db') as mock_get_db:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        from migrate_from_dify import ensure_dify_tables
        ensure_dify_tables()

        # 验证执行了 CREATE TABLE（多个表）
        assert mock_cur.execute.call_count > 10
        mock_conn.commit.assert_called_once()
    print('[PASS] test_ensure_dify_tables')


def test_init_mysql_database():
    """测试初始化数据库"""
    mock_pymysql = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_pymysql.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'pymysql': mock_pymysql}):
        # 需要重新导入以使用 mock 的 pymysql
        import importlib
        import migrate_from_dify
        importlib.reload(migrate_from_dify)
        migrate_from_dify.init_mysql_database()

        mock_cur.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
    print('[PASS] test_init_mysql_database')


def test_verify_migration():
    """测试验证迁移结果"""
    with patch('config.get_db') as mock_get_db:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [
            {'cnt': 5},   # tenants
            {'cnt': 10},  # accounts
            {'cnt': 3},   # apps
            {'cnt': 8},   # workflows
            {'cnt': 2},   # datasets
            {'cnt': 15},  # documents
            {'cnt': 100}, # segments
            {'cnt': 50},  # conversations
            {'cnt': 200}, # messages
            {'cnt': 4},   # providers
        ]
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        from migrate_from_dify import verify_migration
        verify_migration()

        assert mock_cur.execute.call_count == 10
    print('[PASS] test_verify_migration')


def test_migrate_model_configs():
    """测试从 providers 提取模型配置"""
    mock_pg = _mock_pg()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [
        {
            'provider_name': 'openai',
            'credential': {'api_key': 'sk-test', 'openai_api_base': 'https://api.openai.com'},
        },
    ]
    mock_conn.cursor.return_value = mock_cur
    mock_pg.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'psycopg2': mock_pg, 'psycopg2.extras': MagicMock()}):
        with patch('config.get_db') as mock_get_db:
            mock_mysql_conn = MagicMock()
            mock_mysql_cur = MagicMock()
            mock_mysql_conn.cursor.return_value = mock_mysql_cur
            mock_get_db.return_value = mock_mysql_conn

            from migrate_from_dify import migrate_model_configs_from_providers
            migrate_model_configs_from_providers()

            assert mock_mysql_cur.execute.call_count == 1
    print('[PASS] test_migrate_model_configs')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('数据迁移脚本单元测试')
    print('=' * 60)

    test_pg_table_exists()
    test_pg_table_not_exists()
    test_migrate_table_empty()
    test_migrate_table_with_data()
    test_migrate_table_with_json_data()
    test_migrate_table_with_transform()
    test_migrate_table_if_exists_skipped()
    test_ensure_dify_tables()
    test_init_mysql_database()
    test_verify_migration()
    test_migrate_model_configs()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
