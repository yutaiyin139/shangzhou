# -*- coding: utf-8 -*-
"""技能管理路由"""

import io
import os
import re
import zipfile
from flask import jsonify, request
from config import get_db
from utils.helpers import now
from models.tables import SKILLS_TABLE_SQL, SKILL_INSTALLS_TABLE_SQL
from models.builtin_skills import BUILTIN_SKILLS


def _ensure_skills_tables():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(SKILLS_TABLE_SQL)
        cur.execute(SKILL_INSTALLS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _installed_skill_keys():
    """已安装的内置技能 key 集合"""
    _ensure_skills_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT skill_key FROM skill_installs')
        return {row['skill_key'] for row in cur.fetchall()}
    finally:
        db.close()


def _builtin_skill(key):
    for s in BUILTIN_SKILLS:
        if s['key'] == key:
            return s
    return None


def register_skill_routes(app):
    """注册技能相关路由"""

    @app.route('/api/skills', methods=['GET'])
    def get_skills():
        """技能列表：内置 Skills（带安装状态）+ 自定义 Skills"""
        _ensure_skills_tables()
        installed = _installed_skill_keys()
        data = []
        for s in BUILTIN_SKILLS:
            data.append({'key': s['key'], 'name': s['name'], 'icon': s['icon'], 'category': s['category'],
                         'description': s['description'], 'author': s['author'], 'updated_at': s['updated_at'],
                         'kind': 'builtin', 'version': '1.0.0', 'installed': s['key'] in installed})
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"SELECT id, name, description, icon, category, created_at, updated_at FROM skills WHERE kind = 'custom' ORDER BY id DESC")
            for r in cur.fetchall():
                data.append({'key': 'custom_' + str(r['id']), 'name': r['name'], 'icon': r['icon'],
                             'category': r['category'], 'description': r['description'],
                             'author': '自定义', 'updated_at': r['updated_at'] or r['created_at'] or '',
                             'kind': 'custom', 'installed': True})
        finally:
            db.close()
        return jsonify(code=200, data=data)

    @app.route('/api/skills/<key>/detail', methods=['GET'])
    def get_skill_detail(key):
        """技能详情（含 SKILL.md 正文）"""
        _ensure_skills_tables()
        if key.startswith('custom_'):
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'SELECT id, name, description, icon, category, content, created_at, updated_at FROM skills WHERE id = %s AND kind = %s',
                            (key[7:], 'custom'))
                r = cur.fetchone()
            finally:
                db.close()
            if not r:
                return jsonify(code=404, msg='技能不存在')
            return jsonify(code=200, data={'key': key, 'name': r['name'], 'icon': r['icon'], 'category': r['category'],
                                           'description': r['description'], 'author': '自定义', 'kind': 'custom',
                                           'installed': True, 'content': r['content'] or '',
                                           'updated_at': r['updated_at'] or r['created_at'] or ''})
        s = _builtin_skill(key)
        if not s:
            return jsonify(code=404, msg='技能不存在')
        installed = _installed_skill_keys()
        d = dict(s)
        d['installed'] = key in installed
        d['kind'] = 'builtin'
        return jsonify(code=200, data=d)

    @app.route('/api/skills/import', methods=['POST'])
    def import_skill():
        """导入自定义 Skill：ZIP 包内必须包含 SKILL.md"""
        f = request.files.get('file')
        if not f:
            return jsonify(code=400, msg='请选择 ZIP 文件')
        try:
            zf = zipfile.ZipFile(io.BytesIO(f.read()))
        except Exception:
            return jsonify(code=400, msg='不是有效的 ZIP 文件')
        md = None
        for n in zf.namelist():
            if n.lower().endswith('skill.md'):
                md = zf.read(n).decode('utf-8', errors='ignore')
                break
        if md is None:
            return jsonify(code=400, msg='ZIP 包内必须包含 SKILL.md 文件')
        md = md.lstrip('﻿')
        name = ''
        description = ''
        content = md.strip()
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', md, re.S)
        if m:
            for line in m.group(1).splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    if k.strip().lower() == 'name':
                        name = v.strip()
                    elif k.strip().lower() == 'description':
                        description = v.strip()
            content = m.group(2).strip()
        if not name:
            name = os.path.splitext(f.filename or '')[0] or 'untitled-skill'
        if not description and content:
            description = content.splitlines()[0][:200]
        _ensure_skills_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO skills (name, description, icon, category, kind, content, created_at, updated_at)
                            VALUES (%s, %s, '✨', '其他', 'custom', %s, %s, %s)''',
                        (name[:100], description[:500], content, now(), now()))
            db.commit()
            cur.execute(r'SELECT id, name, description, icon, category, content, created_at, updated_at FROM skills WHERE id = %s', (cur.lastrowid,))
            r = cur.fetchone()
            return jsonify(code=200, msg='导入成功', data={'key': 'custom_' + str(r['id']), 'name': r['name'],
                                                          'icon': r['icon'], 'category': r['category'],
                                                          'description': r['description'], 'author': '自定义', 'kind': 'custom',
                                                          'installed': True, 'content': r['content'] or '',
                                                          'updated_at': r['updated_at'] or ''})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/skills/<int:sid>', methods=['DELETE'])
    def delete_skill(sid):
        """删除自定义 Skill（内置 Skill 不可删除）"""
        _ensure_skills_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT kind FROM skills WHERE id = %s', (sid,))
            r = cur.fetchone()
            if not r:
                return jsonify(code=404, msg='技能不存在')
            if r['kind'] != 'custom':
                return jsonify(code=400, msg='内置 Skill 不可删除')
            cur.execute(r'DELETE FROM skills WHERE id = %s', (sid,))
            db.commit()
            return jsonify(code=200, msg='已删除')
        finally:
            db.close()

    @app.route('/api/skills/<key>/install', methods=['POST'])
    def install_skill(key):
        """在线安装内置 Skill"""
        s = _builtin_skill(key)
        if not s:
            return jsonify(code=404, msg='技能不存在')
        _ensure_skills_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'INSERT IGNORE INTO skill_installs (skill_key, installed_at) VALUES (%s, %s)', (key, now()))
            db.commit()
            return jsonify(code=200, msg='已安装', data={'key': key, 'version': '1.0.0', 'source': 'ADP Skills 在线市场'})
        finally:
            db.close()

    @app.route('/api/skills/<key>/install', methods=['DELETE'])
    def uninstall_skill(key):
        """卸载内置 Skill"""
        _ensure_skills_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM skill_installs WHERE skill_key = %s', (key,))
            db.commit()
            return jsonify(code=200, msg='已卸载')
        finally:
            db.close()
