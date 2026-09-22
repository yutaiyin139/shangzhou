# -*- coding: utf-8 -*-
"""模型配置路由 —— 对齐 Dify 的模型供应商管理

功能：
- 已配置模型供应商列表（顶部卡片区）
- 93 个可安装供应商列表 + 详情 + 安装
- 模型参数配置（temperature, max_tokens 等）
- 模型连接测试
- API Key 加密存储
"""

import json
import time
import logging
from datetime import datetime

import pymysql
import requests as http_requests
from flask import jsonify, request, Response

from config import get_db
from utils.helpers import now

logger = logging.getLogger(__name__)

# 需要加密的敏感字段
SENSITIVE_FIELDS = ['api_key', 'client_secret']


def _encrypt_sensitive_fields(data):
    """加密敏感字段"""
    try:
        from utils.encryption import encrypt_dict_fields
        return encrypt_dict_fields(data, SENSITIVE_FIELDS)
    except ImportError:
        return data


def _decrypt_sensitive_fields(data):
    """解密敏感字段"""
    try:
        from utils.encryption import decrypt_dict_fields
        return decrypt_dict_fields(data, SENSITIVE_FIELDS)
    except ImportError:
        return data


def _mask_sensitive_fields(data):
    """脱敏敏感字段（用于返回给前端展示）"""
    try:
        from utils.encryption import is_encrypted
        for field in SENSITIVE_FIELDS:
            if field in data and data[field]:
                val = data[field]
                if is_encrypted(val):
                    data[field] = '********（已加密）'
                elif len(str(val)) > 8:
                    s = str(val)
                    data[field] = s[:4] + '****' + s[-4:]
                else:
                    data[field] = '****'
    except Exception:
        pass
    return data


def _ensure_tables():
    """确保模型供应商相关表存在"""
    from models.tables import (
        MODEL_CONFIGS_TABLE_SQL,
        MODEL_PROVIDER_CONFIGS_TABLE_SQL,
        MODEL_DEFINITIONS_TABLE_SQL,
    )
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(MODEL_CONFIGS_TABLE_SQL)
        cur.execute(MODEL_PROVIDER_CONFIGS_TABLE_SQL)
        cur.execute(MODEL_DEFINITIONS_TABLE_SQL)
    finally:
        db.close()


def _row_to_dict(row):
    """将数据库行转换为 dict，处理 datetime"""
    if not row:
        return None
    d = dict(row)
    for k, v in d.items():
        if v and hasattr(v, 'strftime'):
            d[k] = v.strftime('%Y-%m-%d %H:%M:%S')
    return d


def _rows_to_list(rows):
    """将多行转换为 dict 列表"""
    return [_row_to_dict(r) for r in rows]


def register_model_routes(app):
    """注册模型配置相关路由"""
    _ensure_tables()

    # ============================================================
    # 已配置模型（顶部卡片区）
    # ============================================================

    @app.route('/api/model-providers/installed', methods=['GET'])
    def get_installed_providers():
        """获取已安装的模型供应商（去重 + 统计），含最新配置 id 用于 by-id 测试"""
        db = get_db()
        try:
            cur = db.cursor()
            # 子查询：每个供应商最新一条启用配置的 id
            cur.execute(r'''
                SELECT c.provider, c.provider_label,
                       COUNT(*) as model_count,
                       MAX(c.updated_at) as last_updated,
                       SUBSTRING_INDEX(GROUP_CONCAT(c.id ORDER BY c.updated_at DESC, c.id DESC), ',', 1) as latest_config_id
                FROM model_configs c
                WHERE c.status = 1
                GROUP BY c.provider, c.provider_label
                ORDER BY last_updated DESC
            ''')
            rows = cur.fetchall()
            providers = []
            for r in rows:
                provider_name = r['provider']
                # 查找图标
                cur2 = db.cursor()
                cur2.execute(
                    r'SELECT icon, icon_background FROM model_provider_configs WHERE provider_name = %s',
                    (provider_name,)
                )
                meta = cur2.fetchone()
                providers.append({
                    'provider_name': provider_name,
                    'provider_label': r['provider_label'] or provider_name,
                    'model_count': r['model_count'],
                    'latest_config_id': int(r['latest_config_id']) if r['latest_config_id'] else None,
                    'icon': meta['icon'] if meta else '🤖',
                    'icon_background': meta['icon_background'] if meta else '#E8F3FF',
                    'last_updated': r['last_updated'].strftime('%Y-%m-%d %H:%M:%S') if r['last_updated'] else None,
                })
            return jsonify(code=200, data=providers)
        finally:
            db.close()

    # ============================================================
    # 可安装供应商列表（93 个）
    # ============================================================

    @app.route('/api/model-providers', methods=['GET'])
    def get_all_providers():
        """获取所有模型供应商列表（含安装状态）"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''
                SELECT p.*,
                       CASE WHEN c.provider IS NOT NULL THEN 1 ELSE 0 END as is_installed
                FROM model_provider_configs p
                LEFT JOIN (
                    SELECT DISTINCT provider FROM model_configs WHERE status = 1
                ) c ON p.provider_name = c.provider
                WHERE p.status = 1
                ORDER BY p.is_built_in DESC, p.provider_label ASC
            ''')
            rows = cur.fetchall()
            providers = []
            for r in rows:
                d = _row_to_dict(r)
                # 解析 JSON 字段
                for json_field in ('supported_model_types', 'config_schema'):
                    if d.get(json_field) and isinstance(d[json_field], str):
                        try:
                            d[json_field] = json.loads(d[json_field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                d['is_installed'] = bool(d.get('is_installed', 0))
                # 移除敏感字段
                d.pop('config_schema', None)
                providers.append(d)
            return jsonify(code=200, data=providers)
        finally:
            db.close()

    @app.route('/api/model-providers/<provider_name>', methods=['GET'])
    def get_provider_detail(provider_name):
        """获取供应商详情（含模型定义）"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'SELECT * FROM model_provider_configs WHERE provider_name = %s',
                (provider_name,)
            )
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='供应商不存在')
            provider = _row_to_dict(row)

            # 解析 JSON
            for json_field in ('supported_model_types', 'config_schema'):
                if provider.get(json_field) and isinstance(provider[json_field], str):
                    try:
                        provider[json_field] = json.loads(provider[json_field])
                    except (json.JSONDecodeError, TypeError):
                        pass

            # 获取模型定义
            cur.execute(
                r'SELECT * FROM model_definitions WHERE provider_name = %s AND status = 1 ORDER BY model_type, model_label',
                (provider_name,)
            )
            models = _rows_to_list(cur.fetchall())
            for m in models:
                for jf in ('parameters_schema',):
                    if m.get(jf) and isinstance(m[jf], str):
                        try:
                            m[jf] = json.loads(m[jf])
                        except (json.JSONDecodeError, TypeError):
                            pass

            # 检查是否已安装
            cur.execute(
                r'SELECT COUNT(*) as cnt FROM model_configs WHERE provider = %s AND status = 1',
                (provider_name,)
            )
            provider['is_installed'] = cur.fetchone()['cnt'] > 0
            provider['models'] = models

            return jsonify(code=200, data=provider)
        finally:
            db.close()

    # ============================================================
    # 安装供应商（创建凭据配置）
    # ============================================================

    @app.route('/api/model-providers/<provider_name>/install', methods=['POST'])
    def install_provider(provider_name):
        """安装模型供应商 —— 创建凭据配置"""
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求参数为空')

        api_key = d.get('api_key', '').strip()
        api_base_url = d.get('api_base_url', '').strip()
        credential_name = d.get('credential_name', '').strip()

        if not api_key:
            return jsonify(code=400, msg='API Key 为必填项')

        # 获取供应商信息
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'SELECT * FROM model_provider_configs WHERE provider_name = %s',
                (provider_name,)
            )
            provider_meta = cur.fetchone()
            if not provider_meta:
                return jsonify(code=404, msg='供应商不存在')

            # 自动生成凭据名称
            if not credential_name:
                credential_name = f"{provider_meta['provider_label']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # 使用默认 Base URL
            if not api_base_url:
                api_base_url = provider_meta.get('default_base_url', '')

            # 加密 API Key
            encrypted_key = _encrypt_sensitive_fields({'api_key': api_key})['api_key']

            # 获取供应商下第一个模型作为默认
            cur.execute(
                r'SELECT model_name, model_label, model_type, context_size, max_output_tokens, supports_vision, supports_function_calling, supports_streaming FROM model_definitions WHERE provider_name = %s AND status = 1 LIMIT 1',
                (provider_name,)
            )
            default_model = cur.fetchone()

            model_name = d.get('model_name', default_model['model_name'] if default_model else '')
            model_label = d.get('model_label', default_model['model_label'] if default_model else '')
            model_type = d.get('model_type', default_model['model_type'] if default_model else 'llm')

            # 模型参数（部分模型如 kimi-k3 要求 temperature=1）
            temperature = d.get('temperature', 1.0 if provider_name == 'moonshot' else 0.7)
            max_tokens = d.get('max_tokens', default_model['max_output_tokens'] if default_model else 2048)
            top_p = d.get('top_p', 1.0)
            presence_penalty = d.get('presence_penalty', 0.0)
            frequency_penalty = d.get('frequency_penalty', 0.0)
            context_size = d.get('context_size', default_model['context_size'] if default_model else 4096)
            supports_vision = d.get('supports_vision', default_model['supports_vision'] if default_model else 0)
            supports_function_calling = d.get('supports_function_calling', default_model['supports_function_calling'] if default_model else 0)
            supports_streaming = d.get('supports_streaming', default_model['supports_streaming'] if default_model else 1)

            cur.execute(r'''
                INSERT INTO model_configs
                  (credential_name, provider, provider_label, model_name, model_type, model_label,
                   api_key, api_base_url, temperature, max_tokens, top_p, presence_penalty,
                   frequency_penalty, context_size, supports_vision, supports_function_calling,
                   supports_streaming, config_type, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'credential', 1, %s, %s)
            ''', (
                credential_name, provider_name, provider_meta['provider_label'],
                model_name, model_type, model_label,
                encrypted_key, api_base_url,
                temperature, max_tokens, top_p, presence_penalty, frequency_penalty,
                context_size, supports_vision, supports_function_calling, supports_streaming,
                now(), now()
            ))
            # 必须在执行后续 UPDATE 前捕获 lastrowid，否则会被覆盖为 0
            new_config_id = cur.lastrowid
            db.commit()

            # 更新安装计数
            cur.execute(
                r'UPDATE model_provider_configs SET install_count = install_count + 1 WHERE provider_name = %s',
                (provider_name,)
            )
            db.commit()

            return jsonify(code=200, msg='安装成功', data={'id': new_config_id})
        except pymysql.err.IntegrityError as e:
            db.rollback()
            if 'uk_credential' in str(e):
                return jsonify(code=400, msg='该凭据名称已存在')
            return jsonify(code=400, msg='该供应商已安装')
        except Exception as e:
            db.rollback()
            logger.exception("安装供应商失败")
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ============================================================
    # 卸载供应商
    # ============================================================

    @app.route('/api/model-providers/<provider_name>/uninstall', methods=['POST'])
    def uninstall_provider(provider_name):
        """卸载模型供应商 —— 禁用所有相关配置"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'UPDATE model_configs SET status = 0, updated_at = %s WHERE provider = %s',
                (now(), provider_name)
            )
            db.commit()
            return jsonify(code=200, msg='卸载成功', data={'affected': cur.rowcount})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ============================================================
    # 模型配置 CRUD
    # ============================================================

    @app.route('/api/model-configs', methods=['GET'])
    def get_model_configs():
        """获取所有模型配置"""
        provider = request.args.get('provider', '').strip()
        model_type = request.args.get('model_type', '').strip()
        db = get_db()
        try:
            cur = db.cursor()
            sql = r'SELECT * FROM model_configs WHERE 1=1'
            params = []
            if provider:
                sql += ' AND provider = %s'
                params.append(provider)
            if model_type:
                sql += ' AND model_type = %s'
                params.append(model_type)
            sql += ' ORDER BY created_at DESC'
            cur.execute(sql, params)
            rows = cur.fetchall()
            configs = []
            for r in rows:
                d = _row_to_dict(r)
                _mask_sensitive_fields(d)
                configs.append(d)
            return jsonify(code=200, data=configs)
        finally:
            db.close()

    @app.route('/api/model-configs', methods=['POST'])
    def create_model_config():
        """创建模型配置"""
        d = request.get_json()
        provider = d.get('provider', '').strip()
        credential_name = d.get('credential_name', '').strip()
        model_name = d.get('model_name', '').strip()
        api_key = d.get('api_key', '').strip()
        api_base_url = d.get('api_base_url', '').strip()
        if not provider or not api_key:
            return jsonify(code=400, msg='模型供应商和 API Key 为必填项')
        encrypted_key = _encrypt_sensitive_fields({'api_key': api_key})['api_key']
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''INSERT INTO model_configs
                    (credential_name, provider, provider_label, model_name, model_type, model_label,
                     api_key, api_base_url, temperature, max_tokens, top_p, presence_penalty,
                     frequency_penalty, context_size, supports_vision, supports_function_calling,
                     supports_streaming, config_type, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'credential', 1, %s, %s)''',
                (
                    credential_name, provider, d.get('provider_label', provider),
                    model_name, d.get('model_type', 'llm'), d.get('model_label', model_name),
                    encrypted_key, api_base_url,
                    d.get('temperature', 0.7), d.get('max_tokens', 2048),
                    d.get('top_p', 1.0), d.get('presence_penalty', 0.0),
                    d.get('frequency_penalty', 0.0), d.get('context_size', 4096),
                    d.get('supports_vision', 0), d.get('supports_function_calling', 0),
                    d.get('supports_streaming', 1),
                    now(), now()
                )
            )
            db.commit()
            return jsonify(code=200, msg='保存成功', data={'id': cur.lastrowid})
        except pymysql.err.IntegrityError:
            db.rollback()
            return jsonify(code=400, msg='该模型供应商已存在')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/model-configs/<int:mid>', methods=['PUT'])
    def update_model_config(mid):
        """更新模型配置"""
        d = request.get_json()
        db = get_db()
        try:
            cur = db.cursor()
            fields = []
            vals = []
            updatable = (
                'credential_name', 'provider', 'provider_label', 'model_name', 'model_type',
                'model_label', 'api_key', 'api_base_url', 'temperature', 'max_tokens',
                'top_p', 'presence_penalty', 'frequency_penalty', 'context_size',
                'supports_vision', 'supports_function_calling', 'supports_streaming',
                'config_type', 'status'
            )
            for key in updatable:
                if key in d:
                    fields.append(f'{key} = %s')
                    if key == 'api_key' and d[key]:
                        val = _encrypt_sensitive_fields({'api_key': d[key]})['api_key']
                    else:
                        val = d[key]
                    vals.append(val)
            if fields:
                fields.append('updated_at = %s')
                vals.append(now())
                vals.append(mid)
                cur.execute(f'UPDATE model_configs SET {", ".join(fields)} WHERE id = %s', vals)
            db.commit()
            return jsonify(code=200, msg='更新成功')
        except pymysql.err.IntegrityError:
            db.rollback()
            return jsonify(code=400, msg='该模型供应商名称已存在')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/model-configs/<int:mid>', methods=['DELETE'])
    def delete_model_config(mid):
        """删除模型配置"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM model_configs WHERE id = %s', (mid,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/model-configs/<int:mid>/decrypt', methods=['GET'])
    def get_decrypted_api_key(mid):
        """获取解密的 API Key（仅内部调用）"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT api_key FROM model_configs WHERE id = %s', (mid,))
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='配置不存在')
            decrypted = _decrypt_sensitive_fields({'api_key': row['api_key']})
            return jsonify(code=200, data={'api_key': decrypted['api_key']})
        except Exception as e:
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/model-configs/<int:mid>', methods=['GET'])
    def get_model_config_by_id(mid):
        """获取指定模型配置（脱敏）"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM model_configs WHERE id = %s', (mid,))
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='配置不存在')
            cfg = _row_to_dict(row)
            _mask_sensitive_fields(cfg)
            return jsonify(code=200, data=cfg)
        except Exception as e:
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/model-configs/<int:mid>/test', methods=['POST'])
    def test_model_config_by_id(mid):
        """按配置 ID 测试模型连接（从 DB 加载配置，无需前端传 key）"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM model_configs WHERE id = %s', (mid,))
            cfg = cur.fetchone()
            if not cfg:
                return jsonify(code=404, msg='配置不存在')
        finally:
            db.close()

        # 解密 API Key
        decrypted = _decrypt_sensitive_fields({'api_key': cfg['api_key']})
        provider = cfg['provider']
        api_key = decrypted['api_key']
        api_base_url = cfg.get('api_base_url', '')
        model_name = cfg.get('model_name', '')
        model_type = cfg.get('model_type', 'llm')

        if not api_key:
            return jsonify(code=400, msg='API Key 为空')

        start_time = time.time()
        try:
            if model_type == 'llm':
                result = _test_llm_connection(provider, api_key, api_base_url, model_name)
            elif model_type == 'embedding':
                result = _test_embedding_connection(provider, api_key, api_base_url, model_name)
            elif model_type == 'tts':
                result = _test_tts_connection(provider, api_key, api_base_url, model_name)
            elif model_type == 'stt':
                result = _test_stt_connection(provider, api_key, api_base_url, model_name)
            else:
                result = {'success': True, 'msg': '连接测试通过（默认）'}

            elapsed_ms = int((time.time() - start_time) * 1000)
            result['elapsed_ms'] = elapsed_ms
            return jsonify(code=200 if result.get('success') else 500, data=result)
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return jsonify(code=500, data={
                'success': False,
                'msg': f'连接失败: {str(e)}',
                'elapsed_ms': elapsed_ms,
            })

    # ============================================================
    # 模型连接测试（body-based，无需 id）
    # ============================================================

    @app.route('/api/model-configs/test', methods=['POST'])
    def test_model_connection():
        """测试模型连接（body-based）"""
        d = request.get_json()
        provider = d.get('provider', '').strip()
        api_key = d.get('api_key', '').strip()
        api_base_url = d.get('api_base_url', '').strip()
        model_name = d.get('model_name', '').strip()
        model_type = d.get('model_type', 'llm')

        if not api_key:
            return jsonify(code=400, msg='API Key 为必填项')

        start_time = time.time()

        try:
            if model_type == 'llm':
                result = _test_llm_connection(provider, api_key, api_base_url, model_name)
            elif model_type == 'embedding':
                result = _test_embedding_connection(provider, api_key, api_base_url, model_name)
            elif model_type == 'tts':
                result = _test_tts_connection(provider, api_key, api_base_url, model_name)
            elif model_type == 'stt':
                result = _test_stt_connection(provider, api_key, api_base_url, model_name)
            else:
                result = {'success': True, 'msg': '连接测试通过（默认）'}

            elapsed_ms = int((time.time() - start_time) * 1000)
            result['elapsed_ms'] = elapsed_ms
            return jsonify(code=200 if result.get('success') else 500, data=result)
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return jsonify(code=500, data={
                'success': False,
                'msg': f'连接失败: {str(e)}',
                'elapsed_ms': elapsed_ms,
            })

    def _test_llm_connection(provider, api_key, api_base_url, model_name):
        """测试 LLM 连接"""
        # 根据供应商选择测试端点
        if 'openai' in provider or provider in ('deepseek', 'moonshot', 'zhipu', 'tongyi', 'minimax'):
            return _test_openai_compatible(api_key, api_base_url, model_name)
        elif 'anthropic' in provider:
            return _test_anthropic(api_key, api_base_url, model_name)
        elif 'google' in provider or 'gemini' in provider:
            return _test_google(api_key, api_base_url, model_name)
        else:
            # 通用 OpenAI 兼容测试
            return _test_openai_compatible(api_key, api_base_url, model_name)

    def _test_openai_compatible(api_key, api_base_url, model_name):
        """测试 OpenAI 兼容接口"""
        if not api_base_url:
            return {'success': False, 'msg': '缺少 API Base URL'}
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        # 清洗 URL：将 Unicode 连字符（U+2011 等）替换为 ASCII 连字符
        url = api_base_url.replace('‑', '-').replace('–', '-').replace('—', '-').rstrip('/')
        # 先尝试 models 列表
        try:
            resp = http_requests.get(f'{url}/models', headers=headers, timeout=10)
            if resp.status_code == 200:
                return {'success': True, 'msg': '连接成功', 'models_count': len(resp.json().get('data', []))}
        except Exception:
            pass
        # 再尝试 chat/completions
        payload = {
            'model': model_name or 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'max_tokens': 5,
        }
        resp = http_requests.post(f'{url}/chat/completions', headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return {'success': True, 'msg': '连接成功'}
        else:
            return {'success': False, 'msg': f'HTTP {resp.status_code}: {resp.text[:200]}'}

    def _test_anthropic(api_key, api_base_url, model_name):
        """测试 Anthropic 接口"""
        url = (api_base_url or 'https://api.anthropic.com').rstrip('/')
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01',
        }
        payload = {
            'model': model_name or 'claude-3-haiku-20240307',
            'max_tokens': 5,
            'messages': [{'role': 'user', 'content': 'Hello'}],
        }
        resp = http_requests.post(f'{url}/v1/messages', headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return {'success': True, 'msg': '连接成功'}
        else:
            return {'success': False, 'msg': f'HTTP {resp.status_code}: {resp.text[:200]}'}

    def _test_google(api_key, api_base_url, model_name):
        """测试 Google Gemini 接口"""
        url = (api_base_url or 'https://generativelanguage.googleapis.com').rstrip('/')
        model = model_name or 'gemini-pro'
        target = f'{url}/v1beta/models/{model}:generateContent?key={api_key}'
        payload = {
            'contents': [{'parts': [{'text': 'Hello'}]}],
            'generationConfig': {'maxOutputTokens': 5},
        }
        resp = http_requests.post(target, json=payload, timeout=15)
        if resp.status_code == 200:
            return {'success': True, 'msg': '连接成功'}
        else:
            return {'success': False, 'msg': f'HTTP {resp.status_code}: {resp.text[:200]}'}

    def _test_embedding_connection(provider, api_key, api_base_url, model_name):
        """测试 Embedding 连接"""
        if not api_base_url:
            return {'success': False, 'msg': '缺少 API Base URL'}
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        url = api_base_url.rstrip('/')
        payload = {
            'model': model_name or 'text-embedding-3-small',
            'input': 'Hello world',
        }
        resp = http_requests.post(f'{url}/embeddings', headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            return {'success': True, 'msg': '连接成功', 'dimensions': len(data[0].get('embedding', [])) if data else 0}
        else:
            return {'success': False, 'msg': f'HTTP {resp.status_code}: {resp.text[:200]}'}

    def _test_tts_connection(provider, api_key, api_base_url, model_name):
        """测试 TTS（文本转语音）连接"""
        from utils.llm import build_openai_url
        if not api_base_url:
            return {'success': False, 'msg': '缺少 API Base URL'}
        if not api_key:
            return {'success': False, 'msg': '缺少 API Key'}
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        url = build_openai_url(api_base_url, 'audio/speech')
        payload = {
            'model': model_name or 'tts-1',
            'input': 'Hello',
            'voice': 'alloy',
            'response_format': 'mp3',
        }
        try:
            resp = http_requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 0:
                return {'success': True, 'msg': 'TTS 连接成功', 'audio_bytes': len(resp.content)}
            else:
                return {'success': False, 'msg': f'HTTP {resp.status_code}: {resp.text[:200]}'}
        except Exception as e:
            return {'success': False, 'msg': f'连接异常: {str(e)}'}

    def _test_stt_connection(provider, api_key, api_base_url, model_name):
        """测试 STT（语音转文本）连接"""
        from utils.llm import build_openai_url
        if not api_base_url:
            return {'success': False, 'msg': '缺少 API Base URL'}
        if not api_key:
            return {'success': False, 'msg': '缺少 API Key'}
        url = build_openai_url(api_base_url, 'audio/transcriptions')
        headers = {
            'Authorization': f'Bearer {api_key}',
        }
        # 生成一段简短的静音 WAV 用于连接测试（1秒静音）
        import struct, wave, io
        sample_rate = 16000
        duration = 0.5  # 秒
        num_samples = int(sample_rate * duration)
        # PCM 16-bit 静音
        pcm_data = b'\x00\x00' * num_samples
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        wav_bytes = buf.getvalue()

        files = {'file': ('test.wav', wav_bytes, 'audio/wav')}
        data = {'model': model_name or 'whisper-1', 'response_format': 'text'}
        try:
            resp = http_requests.post(url, headers=headers, files=files, data=data, timeout=30)
            if resp.status_code == 200:
                return {'success': True, 'msg': 'STT 连接成功', 'sample_text': resp.text.strip()[:100]}
            else:
                return {'success': False, 'msg': f'HTTP {resp.status_code}: {resp.text[:200]}'}
        except Exception as e:
            return {'success': False, 'msg': f'连接异常: {str(e)}'}

    # ============================================================
    # 获取模型参数 Schema（用于前端动态渲染配置表单）
    # ============================================================

    @app.route('/api/model-providers/<provider_name>/config-schema', methods=['GET'])
    def get_provider_config_schema(provider_name):
        """获取供应商的配置 Schema"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'SELECT config_schema, default_base_url, supported_model_types FROM model_provider_configs WHERE provider_name = %s',
                (provider_name,)
            )
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='供应商不存在')
            result = {
                'config_schema': {},
                'default_base_url': row['default_base_url'],
                'supported_model_types': [],
            }
            if row['config_schema']:
                try:
                    result['config_schema'] = json.loads(row['config_schema'])
                except (json.JSONDecodeError, TypeError):
                    pass
            if row['supported_model_types']:
                try:
                    result['supported_model_types'] = json.loads(row['supported_model_types'])
                except (json.JSONDecodeError, TypeError):
                    pass
            return jsonify(code=200, data=result)
        finally:
            db.close()

    # ============================================================
    # 获取模型类型列表
    # ============================================================

    @app.route('/api/model-types', methods=['GET'])
    def get_model_types():
        """获取支持的模型类型"""
        return jsonify(code=200, data=[
            {'value': 'llm', 'label': '大语言模型 (LLM)', 'icon': '💬'},
            {'value': 'embedding', 'label': 'Embedding 模型', 'icon': '📊'},
            {'value': 'rerank', 'label': 'Rerank 模型', 'icon': '🔄'},
            {'value': 'tts', 'label': '语音合成 (TTS)', 'icon': '🔊'},
            {'value': 'stt', 'label': '语音识别 (STT)', 'icon': '🎤'},
        ])
