# -*- coding: utf-8 -*-
"""数据源管理路由"""

import json
from flask import jsonify, request
from config import get_db
from models.tables import DATA_SOURCES_TABLE_SQL
from models.builtin_data_sources import BUILTIN_DATA_SOURCES


def _ensure_ds_tables():
    db = get_db()
    try:
        db.cursor().execute(DATA_SOURCES_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _ds_conn():
    _ensure_ds_tables()
    return get_db()


def _builtin_ds(key):
    for s in BUILTIN_DATA_SOURCES:
        if s['key'] == key:
            return s
    return None


def _ds_public(s, row):
    """内置数据源 + 安装状态（不回传 config 明文）"""
    info = {'key': s['key'], 'name': s['name'], 'icon': s['icon'], 'bg': s['bg'], 'desc': s['desc'],
            'author': s['author'], 'downloads': s['downloads'], 'tags': s['tags'], 'fields': s['fields']}
    info['status'] = row['status'] if row else ''
    if row and row['config']:
        try:
            info['configured_keys'] = list(json.loads(row['config']).keys())
        except Exception:
            info['configured_keys'] = []
    else:
        info['configured_keys'] = []
    return info


def register_data_source_routes(app):
    """注册数据源相关路由"""

    @app.route('/api/data-sources', methods=['GET'])
    def list_data_sources():
        """数据源市场列表（含安装/配置状态）"""
        db = _ds_conn()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT ds_key, status, config FROM data_sources')
            rows = {r['ds_key']: r for r in cur.fetchall()}
            return jsonify(code=200, data=[_ds_public(s, rows.get(s['key'])) for s in BUILTIN_DATA_SOURCES])
        finally:
            db.close()

    @app.route('/api/data-sources/<key>/install', methods=['POST'])
    def install_data_source(key):
        """安装数据源"""
        if not _builtin_ds(key):
            return jsonify(code=404, msg='数据源不存在')
        db = _ds_conn()
        try:
            cur = db.cursor()
            cur.execute(r'INSERT INTO data_sources (ds_key, status) VALUES (%s, %s) ON DUPLICATE KEY UPDATE status = status', (key, 'installed'))
            db.commit()
            return jsonify(code=200, msg='已安装')
        finally:
            db.close()

    @app.route('/api/data-sources/<key>/configure', methods=['POST'])
    def configure_data_source(key):
        """配置数据源"""
        s = _builtin_ds(key)
        if not s:
            return jsonify(code=404, msg='数据源不存在')
        body = request.get_json(silent=True) or {}
        cfg = {}
        for f in s['fields']:
            v = (body.get(f['key']) or '').strip()
            if f['required'] and not v:
                return jsonify(code=400, msg='请填写' + f['label'])
            cfg[f['key']] = v
        db = _ds_conn()
        try:
            cur = db.cursor()
            cur.execute(r'INSERT INTO data_sources (ds_key, status, config) VALUES (%s, %s, %s) '
                        r'ON DUPLICATE KEY UPDATE status = %s, config = %s',
                        (key, 'configured', json.dumps(cfg, ensure_ascii=False), 'configured', json.dumps(cfg, ensure_ascii=False)))
            db.commit()
            return jsonify(code=200, msg='已配置')
        finally:
            db.close()

    @app.route('/api/data-sources/<key>', methods=['DELETE'])
    def remove_data_source(key):
        """移除数据源"""
        db = _ds_conn()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM data_sources WHERE ds_key = %s', (key,))
            db.commit()
            return jsonify(code=200, msg='已移除')
        finally:
            db.close()
