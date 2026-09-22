# -*- coding: utf-8 -*-
"""
插件市场种子数据 —— 初始化示例插件

运行方式:
    cd backend && python ../scripts/maintenance/seed_plugins.py

功能:
    1. 检查 plugins 表是否已有数据
    2. 若无数据，插入 8 个示例插件（覆盖 tool/workflow/agent/mcp 四种类型）
    3. 每个插件包含完整的 manifest/package/tags 数据
"""

import os
import sys
import json
import uuid
from datetime import datetime

# 本脚本已归档至 scripts/maintenance/，config.py 位于 backend/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))

def seed_plugins():
    from config import get_db

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT COUNT(*) as cnt FROM plugins')
        count = cur.fetchone()['cnt']
        if count > 0:
            print(f'plugins 表已有 {count} 条数据，跳过种子')
            return

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        plugins = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Google 搜索',
                'plugin_type': 'tool',
                'description': '通过 Google SERP API 搜索互联网，提取搜索结果片段和网页内容。支持多语言、多地区搜索。',
                'version': '1.2.0',
                'author_name': 'langgenius',
                'icon': '🔍',
                'icon_background': '#EAF1FE',
                'category': 'utility',
                'tags': ['搜索', '网页', '实时信息'],
                'manifest': {
                    'name': 'google_search',
                    'version': '1.2.0',
                    'description': 'Google 搜索工具',
                    'actions': [
                        {
                            'name': 'search',
                            'description': '执行 Google 搜索',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'query': {'type': 'string', 'description': '搜索关键词'},
                                    'num_results': {'type': 'number', 'description': '返回结果数量', 'default': 5},
                                    'language': {'type': 'string', 'description': '搜索语言', 'default': 'zh-CN'}
                                },
                                'required': ['query']
                            }
                        }
                    ]
                },
                'download_count': 141629,
                'rating': 4.8,
                'rating_count': 2341,
                'is_public': True,
                'is_official': True,
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'GitHub',
                'plugin_type': 'tool',
                'description': 'GitHub 仓库搜索、Issue/PR 查询、代码片段提取。支持搜索仓库、用户、代码。',
                'version': '2.0.1',
                'author_name': 'langgenius',
                'icon': '🐙',
                'icon_background': '#1D2129',
                'category': 'integration',
                'tags': ['代码', '开发', '版本控制'],
                'manifest': {
                    'name': 'github',
                    'version': '2.0.1',
                    'description': 'GitHub 集成工具',
                    'actions': [
                        {
                            'name': 'search_repos',
                            'description': '搜索 GitHub 仓库',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'query': {'type': 'string', 'description': '搜索关键词'},
                                    'language': {'type': 'string', 'description': '编程语言筛选'},
                                    'sort': {'type': 'string', 'description': '排序方式', 'default': 'stars'}
                                },
                                'required': ['query']
                            }
                        },
                        {
                            'name': 'get_repo_info',
                            'description': '获取仓库详情',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'owner': {'type': 'string', 'description': '仓库所有者'},
                                    'repo': {'type': 'string', 'description': '仓库名称'}
                                },
                                'required': ['owner', 'repo']
                            }
                        }
                    ]
                },
                'download_count': 149436,
                'rating': 4.9,
                'rating_count': 3102,
                'is_public': True,
                'is_official': True,
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'DALL-E 图片生成',
                'plugin_type': 'tool',
                'description': '通过 OpenAI DALL-E 模型根据文本描述生成高质量图片。支持多种尺寸和质量选项。',
                'version': '1.0.0',
                'author_name': 'langgenius',
                'icon': '🎨',
                'icon_background': '#FFF0F6',
                'category': 'ai',
                'tags': ['图片生成', 'AI', 'DALL-E'],
                'manifest': {
                    'name': 'dall_e',
                    'version': '1.0.0',
                    'description': 'AI 图片生成工具',
                    'actions': [
                        {
                            'name': 'generate_image',
                            'description': '根据文本描述生成图片',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'prompt': {'type': 'string', 'description': '图片描述'},
                                    'size': {'type': 'string', 'description': '图片尺寸', 'default': '1024x1024'},
                                    'quality': {'type': 'string', 'description': '图片质量', 'default': 'standard'},
                                    'style': {'type': 'string', 'description': '风格', 'default': 'vivid'}
                                },
                                'required': ['prompt']
                            }
                        }
                    ]
                },
                'download_count': 89234,
                'rating': 4.7,
                'rating_count': 1876,
                'is_public': True,
                'is_official': True,
            },
            {
                'id': str(uuid.uuid4()),
                'name': '数据分析工作流',
                'plugin_type': 'workflow',
                'description': '自动化数据分析流水线：数据清洗 → 统计分析 → 可视化图表 → 报告生成。',
                'version': '1.1.0',
                'author_name': 'szagent-team',
                'icon': '📊',
                'icon_background': '#FFF7E8',
                'category': 'data',
                'tags': ['数据分析', '可视化', '自动化'],
                'manifest': {
                    'name': 'data_analysis_workflow',
                    'version': '1.1.0',
                    'description': '数据分析自动化工作流',
                    'actions': [
                        {
                            'name': 'analyze_csv',
                            'description': '分析 CSV 数据文件',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'file_id': {'type': 'string', 'description': '上传的文件 ID'},
                                    'analysis_type': {'type': 'string', 'description': '分析类型: summary/correlation/trend'}
                                },
                                'required': ['file_id']
                            }
                        }
                    ]
                },
                'download_count': 45123,
                'rating': 4.6,
                'rating_count': 892,
                'is_public': True,
                'is_official': False,
            },
            {
                'id': str(uuid.uuid4()),
                'name': '客服 Agent',
                'plugin_type': 'agent',
                'description': '智能客服 Agent，支持多轮对话、知识库检索、工单创建。可处理常见问题并自动升级复杂问题。',
                'version': '2.3.0',
                'author_name': 'szagent-team',
                'icon': '🤖',
                'icon_background': '#F5E8FF',
                'category': 'ai',
                'tags': ['客服', '对话', '知识库'],
                'manifest': {
                    'name': 'customer_service_agent',
                    'version': '2.3.0',
                    'description': '智能客服 Agent',
                    'actions': [
                        {
                            'name': 'chat',
                            'description': '与客服 Agent 对话',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'message': {'type': 'string', 'description': '用户消息'},
                                    'session_id': {'type': 'string', 'description': '会话 ID'}
                                },
                                'required': ['message']
                            }
                        }
                    ]
                },
                'download_count': 67890,
                'rating': 4.5,
                'rating_count': 1234,
                'is_public': True,
                'is_official': False,
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Slack 通知',
                'plugin_type': 'mcp',
                'description': '通过 Slack Webhook 发送通知消息到指定频道。支持富文本、按钮、区块布局。',
                'version': '1.0.2',
                'author_name': 'community',
                'icon': '💬',
                'icon_background': '#E8FFEA',
                'category': 'integration',
                'tags': ['通知', 'Slack', '协作'],
                'manifest': {
                    'name': 'slack_notifier',
                    'version': '1.0.2',
                    'description': 'Slack 消息通知工具',
                    'actions': [
                        {
                            'name': 'send_message',
                            'description': '发送 Slack 消息',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'channel': {'type': 'string', 'description': '频道名称'},
                                    'message': {'type': 'string', 'description': '消息内容'},
                                    'blocks': {'type': 'string', 'description': '富文本区块 JSON'}
                                },
                                'required': ['channel', 'message']
                            }
                        }
                    ]
                },
                'download_count': 34567,
                'rating': 4.4,
                'rating_count': 567,
                'is_public': True,
                'is_official': False,
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'PDF 文档解析',
                'plugin_type': 'tool',
                'description': '提取 PDF 文档中的文本、表格和图片。支持 OCR 识别扫描版 PDF，保持原始布局。',
                'version': '1.3.1',
                'author_name': 'langgenius',
                'icon': '📕',
                'icon_background': '#FFECE8',
                'category': 'utility',
                'tags': ['PDF', '文档', 'OCR'],
                'manifest': {
                    'name': 'pdf_parser',
                    'version': '1.3.1',
                    'description': 'PDF 文档解析工具',
                    'actions': [
                        {
                            'name': 'extract_text',
                            'description': '提取 PDF 文本内容',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'file_id': {'type': 'string', 'description': 'PDF 文件 ID'},
                                    'page_range': {'type': 'string', 'description': '页码范围, 如 1-5'},
                                    'ocr': {'type': 'boolean', 'description': '是否启用 OCR', 'default': False}
                                },
                                'required': ['file_id']
                            }
                        }
                    ]
                },
                'download_count': 56789,
                'rating': 4.7,
                'rating_count': 1023,
                'is_public': True,
                'is_official': True,
            },
            {
                'id': str(uuid.uuid4()),
                'name': '邮件自动化',
                'plugin_type': 'workflow',
                'description': '自动化邮件处理工作流：智能分类 → 优先级排序 → 自动回复草稿 → 定时发送。',
                'version': '1.0.0',
                'author_name': 'szagent-team',
                'icon': '📧',
                'icon_background': '#FFF7E8',
                'category': 'productivity',
                'tags': ['邮件', '自动化', '办公'],
                'manifest': {
                    'name': 'email_automation',
                    'version': '1.0.0',
                    'description': '邮件自动化处理工作流',
                    'actions': [
                        {
                            'name': 'process_inbox',
                            'description': '处理收件箱邮件',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'folder': {'type': 'string', 'description': '邮件文件夹', 'default': 'INBOX'},
                                    'action': {'type': 'string', 'description': '操作: classify/reply/archive'}
                                },
                                'required': ['action']
                            }
                        }
                    ]
                },
                'download_count': 23456,
                'rating': 4.3,
                'rating_count': 456,
                'is_public': True,
                'is_official': False,
            },
        ]

        for p in plugins:
            cur.execute(r'''INSERT INTO plugins
                           (id, name, plugin_type, description, version, author_id, author_name,
                            icon, icon_background, category, tags_json, package_json, manifest_json,
                            download_url, file_size, checksum, is_public, is_official, status,
                            download_count, rating, rating_count, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                   %s, %s, %s, %s, %s, %s, %s, %s)''',
                        (
                            p['id'], p['name'], p['plugin_type'], p['description'], p['version'],
                            'system', p['author_name'],
                            p['icon'], p['icon_background'], p['category'],
                            json.dumps(p['tags'], ensure_ascii=False),
                            json.dumps({}, ensure_ascii=False),
                            json.dumps(p['manifest'], ensure_ascii=False),
                            '', 0, '',
                            1 if p['is_public'] else 0,
                            1 if p['is_official'] else 0,
                            'active',
                            p['download_count'], p['rating'], p['rating_count'],
                            now, now,
                        ))
        db.commit()
        print(f'成功插入 {len(plugins)} 个示例插件')

    except Exception as e:
        db.rollback()
        print(f'种子失败: {e}')
        raise
    finally:
        db.close()


if __name__ == '__main__':
    seed_plugins()
