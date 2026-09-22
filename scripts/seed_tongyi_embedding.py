# -*- coding: utf-8 -*-
"""配置通义千问（DashScope）Embedding 模型。

用法：
    python scripts/seed_tongyi_embedding.py <DASHSCOPE_API_KEY>
    或  set TONGYI_API_KEY=sk-xxx && python scripts/seed_tongyi_embedding.py

流程：
    1) 用给定 Key 直连 DashScope OpenAI 兼容 /embeddings 端点做连通性 + 维度自检；
    2) 自检通过后，幂等 upsert 一条 model_configs（model_type='embedding', status=1）；
    3) 旧的 tongyi_embedding 配置先置 status=0，避免 get_embedding_config 命中过期项。
API Key 仅从入参/环境变量读取，不落盘明文；入库使用与线上一致的 Fernet 加密（enc: 前缀）。
"""
import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config import get_db
from utils.encryption import encrypt_field

PROVIDER = 'tongyi_embedding'
PROVIDER_LABEL = 'Tongyi Embedding'
MODEL_NAME = 'text-embedding-v3'
BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
EMBED_URL = BASE_URL + '/embeddings'


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def test_key(api_key):
    """直连自检：返回 (ok, dim, msg)"""
    payload = json.dumps({'model': MODEL_NAME, 'input': '你好，世界'}).encode('utf-8')
    req = urllib.request.Request(
        EMBED_URL, data=payload, method='POST',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return False, 0, f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:300]}'
    except Exception as e:
        return False, 0, f'连接异常: {e}'
    data = result.get('data') or []
    if not data or not data[0].get('embedding'):
        return False, 0, f'响应无向量: {json.dumps(result)[:300]}'
    return True, len(data[0]['embedding']), 'OK'


def upsert_config(api_key, dim):
    db = get_db()
    try:
        cur = db.cursor()
        # 旧配置停用（幂等）
        cur.execute(
            "UPDATE model_configs SET status = 0, updated_at = %s "
            "WHERE provider = %s AND model_type = 'embedding'",
            (now(), PROVIDER))
        enc_key = encrypt_field(api_key)
        cred_name = f'{PROVIDER_LABEL}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        cur.execute(r'''
            INSERT INTO model_configs
              (credential_name, provider, provider_label, model_name, model_type, model_label,
               api_key, api_base_url, temperature, max_tokens, top_p, presence_penalty,
               frequency_penalty, context_size, supports_vision, supports_function_calling,
               supports_streaming, config_type, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 'embedding', %s, %s, %s, 0.7, 1024, 1.0, 0.0,
                    0.0, %s, 0, 0, 0, 'credential', 1, %s, %s)
        ''', (
            cred_name, PROVIDER, PROVIDER_LABEL, MODEL_NAME, f'{MODEL_NAME} (dim={dim})',
            enc_key, BASE_URL, dim, now(), now()))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def main():
    api_key = sys.argv[1] if len(sys.argv) > 1 else os.getenv('TONGYI_API_KEY', '')
    if not api_key:
        print('用法: python scripts/seed_tongyi_embedding.py <DASHSCOPE_API_KEY>')
        sys.exit(2)
    print(f'[1/3] 连通性自检 {MODEL_NAME} @ {EMBED_URL} ...')
    ok, dim, msg = test_key(api_key)
    print(f'      -> {"PASS" if ok else "FAIL"} dim={dim} {msg}')
    if not ok:
        print('自检未通过，未写入数据库。')
        sys.exit(1)
    print('[2/3] 幂等 upsert model_configs (model_type=embedding, status=1) ...')
    cid = upsert_config(api_key, dim)
    print(f'      -> 新配置 id={cid}')
    print('[3/3] 复核 get_embedding_config 命中 ...')
    from engine.embedding_service import get_embedding_config, get_embedding
    cfg = get_embedding_config()
    print(f"      -> provider={cfg['provider']} model={cfg['model_name']} type={cfg['model_type']} base={cfg['api_base_url']}")
    v = get_embedding('分布式系统与后端工程')
    print(f'      -> get_embedding 返回维度={len(v)}（应为 {dim}）')
    print('完成。')


if __name__ == '__main__':
    main()
