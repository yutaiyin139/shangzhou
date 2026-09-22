# -*- coding: utf-8 -*-
"""文件上传与管理路由（使用存储抽象层）"""

import os
import uuid
import mimetypes
from datetime import datetime
from flask import jsonify, request, send_file, Response
from config import get_db
from models.tables import DIFY_UPLOAD_FILES_TABLE_SQL
from utils.storage import get_storage

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    # 文档
    'txt', 'md', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'json', 'xml', 'yaml', 'yml',
    # 图片
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico',
    # 音频
    'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac',
    # 视频
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm',
    # 压缩包
    'zip', 'rar', '7z', 'tar', 'gz',
    # 代码
    'py', 'js', 'ts', 'java', 'c', 'cpp', 'h', 'go', 'rs', 'rb', 'php', 'html', 'css', 'sql', 'sh', 'bat',
}

# 最大文件大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


def _ensure_file_tables():
    """确保文件相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_UPLOAD_FILES_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _get_extension(filename):
    """获取文件扩展名"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def _is_allowed_file(filename):
    """检查文件是否允许上传"""
    ext = _get_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def register_file_routes(app):
    """注册文件相关路由"""

    @app.route('/api/files/upload', methods=['POST'])
    def upload_file():
        """上传文件（使用存储抽象层）"""
        _ensure_file_tables()

        if 'file' not in request.files:
            return jsonify(code=400, msg='未选择文件')

        file = request.files['file']
        if not file or not file.filename:
            return jsonify(code=400, msg='未选择文件')

        original_name = file.filename
        if not _is_allowed_file(original_name):
            ext = _get_extension(original_name)
            return jsonify(code=400, msg=f'不支持的文件类型: {ext or "未知"}')

        # 读取文件内容检查大小
        file_content = file.read()
        file_size = len(file_content)
        if file_size > MAX_FILE_SIZE:
            return jsonify(code=400, msg=f'文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)')
        if file_size == 0:
            return jsonify(code=400, msg='文件为空')

        # 获取文件信息
        ext = _get_extension(original_name)
        mime_type = file.content_type or mimetypes.guess_type(original_name)[0] or 'application/octet-stream'

        # 使用存储抽象层保存文件
        storage = get_storage()
        try:
            result = storage.save(file_content, original_name, mime_type)
        except Exception as e:
            return jsonify(code=500, msg='文件保存失败: ' + str(e))

        # 获取关联信息
        tenant_id = request.form.get('tenant_id', 'default')
        user_id = request.form.get('user_id', '')
        conversation_id = request.form.get('conversation_id', '')

        # 保存到数据库
        file_id = str(uuid.uuid4())
        storage_key = result['storage_key']

        db = get_db()
        try:
            cur = db.cursor()
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                r'''INSERT INTO dify_upload_files
                    (id, tenant_id, user_id, conversation_id, original_name, file_path,
                     file_size, file_type, mime_type, extension, source, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (file_id, tenant_id, user_id, conversation_id, original_name, storage_key,
                 file_size, ext, mime_type, ext, 'upload', 'active', ts)
            )
            db.commit()
        except Exception as e:
            # 保存失败则删除文件
            try:
                storage.delete(storage_key)
            except Exception:
                pass
            return jsonify(code=500, msg='保存文件记录失败: ' + str(e))
        finally:
            db.close()

        return jsonify(code=200, msg='上传成功', data={
            'id': file_id,
            'original_name': original_name,
            'file_size': file_size,
            'file_type': ext,
            'mime_type': mime_type,
            'created_at': ts,
        })

    @app.route('/api/files', methods=['GET'])
    def list_files():
        """列出文件"""
        _ensure_file_tables()
        tenant_id = request.args.get('tenant_id', 'default')
        user_id = request.args.get('user_id', '')
        conversation_id = request.args.get('conversation_id', '')
        file_type = request.args.get('file_type', '')
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 20)), 100)

        where = ['status = "active"']
        params = []

        if tenant_id:
            where.append('tenant_id = %s')
            params.append(tenant_id)
        if user_id:
            where.append('user_id = %s')
            params.append(user_id)
        if conversation_id:
            where.append('conversation_id = %s')
            params.append(conversation_id)
        if file_type:
            where.append('extension = %s')
            params.append(file_type)

        where_sql = 'WHERE ' + ' AND '.join(where)
        offset = (page - 1) * page_size

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'SELECT COUNT(*) as total FROM dify_upload_files ' + where_sql,
                params
            )
            total = cur.fetchone()['total']

            cur.execute(
                r'SELECT * FROM dify_upload_files ' + where_sql +
                r' ORDER BY created_at DESC LIMIT %s OFFSET %s',
                params + [page_size, offset]
            )
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'],
                    'original_name': r['original_name'],
                    'file_size': r['file_size'],
                    'file_type': r['file_type'],
                    'mime_type': r['mime_type'],
                    'extension': r['extension'],
                    'user_id': r['user_id'],
                    'conversation_id': r['conversation_id'],
                    'source': r['source'],
                    'created_at': str(r['created_at']),
                })
            return jsonify(code=200, data={
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
            })
        finally:
            db.close()

    @app.route('/api/files/<file_id>', methods=['GET'])
    def get_file(file_id):
        """获取文件信息或下载文件（使用存储抽象层）"""
        _ensure_file_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM dify_upload_files WHERE id = %s AND status = "active"', (file_id,))
            file_record = cur.fetchone()
        finally:
            db.close()

        if not file_record:
            return jsonify(code=404, msg='文件不存在')

        # 检查是否是预览请求
        preview = request.args.get('preview', '0') == '1'

        # 使用存储抽象层读取文件
        storage = get_storage()
        storage_key = file_record['file_path']

        if preview:
            # 预览模式：返回文件内容（仅文本和图片）
            if file_record['mime_type'].startswith('image/'):
                try:
                    file_data = storage.read(storage_key)
                    return Response(file_data, mimetype=file_record['mime_type'])
                except FileNotFoundError:
                    return jsonify(code=404, msg='文件已丢失')
            elif file_record['mime_type'].startswith('text/') or file_record['extension'] in ('json', 'xml', 'yaml', 'yml', 'md', 'txt'):
                try:
                    file_data = storage.read(storage_key)
                    content = file_data.decode('utf-8', errors='replace')
                    return jsonify(code=200, data={
                        'id': file_record['id'],
                        'original_name': file_record['original_name'],
                        'content': content[:10000],  # 限制预览大小
                        'mime_type': file_record['mime_type'],
                    })
                except FileNotFoundError:
                    return jsonify(code=404, msg='文件已丢失')
            else:
                # 不支持预览的类型直接下载
                try:
                    file_data = storage.read(storage_key)
                    return Response(
                        file_data,
                        mimetype=file_record['mime_type'],
                        headers={'Content-Disposition': f'attachment; filename="{file_record["original_name"]}"'}
                    )
                except FileNotFoundError:
                    return jsonify(code=404, msg='文件已丢失')
        else:
            # 下载模式
            try:
                file_data = storage.read(storage_key)
                return Response(
                    file_data,
                    mimetype=file_record['mime_type'],
                    headers={'Content-Disposition': f'attachment; filename="{file_record["original_name"]}"'}
                )
            except FileNotFoundError:
                return jsonify(code=404, msg='文件已丢失')

    @app.route('/api/files/<file_id>', methods=['DELETE'])
    def delete_file(file_id):
        """删除文件（软删除，使用存储抽象层）"""
        _ensure_file_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT file_path FROM dify_upload_files WHERE id = %s', (file_id,))
            file_record = cur.fetchone()
            if not file_record:
                return jsonify(code=404, msg='文件不存在')

            # 软删除
            cur.execute(r'UPDATE dify_upload_files SET status = "deleted" WHERE id = %s', (file_id,))
            db.commit()

            # 可选：物理删除文件（通过存储抽象层）
            # storage = get_storage()
            # storage.delete(file_record['file_path'])

            return jsonify(code=200, msg='文件已删除')
        except Exception as e:
            return jsonify(code=500, msg='删除失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/files/stats', methods=['GET'])
    def get_file_stats():
        """获取文件统计信息"""
        _ensure_file_tables()
        tenant_id = request.args.get('tenant_id', 'default')

        db = get_db()
        try:
            cur = db.cursor()

            # 总体统计
            cur.execute(r'''
                SELECT
                    COUNT(*) AS total_files,
                    COALESCE(SUM(file_size), 0) AS total_size,
                    COUNT(DISTINCT user_id) AS upload_users
                FROM dify_upload_files
                WHERE status = 'active' AND tenant_id = %s
            ''', (tenant_id,))
            overall = cur.fetchone()

            # 按类型统计
            cur.execute(r'''
                SELECT extension, COUNT(*) AS count, SUM(file_size) AS size
                FROM dify_upload_files
                WHERE status = 'active' AND tenant_id = %s
                GROUP BY extension
                ORDER BY count DESC
                LIMIT 10
            ''', (tenant_id,))
            by_type = []
            for r in cur.fetchall():
                by_type.append({
                    'extension': r['extension'] or 'unknown',
                    'count': int(r['count']),
                    'size': int(r['size']),
                })

            # 最近 7 天上传统计
            cur.execute(r'''
                SELECT DATE(created_at) AS date, COUNT(*) AS count, SUM(file_size) AS size
                FROM dify_upload_files
                WHERE status = 'active' AND tenant_id = %s
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''', (tenant_id,))
            trend = []
            for r in cur.fetchall():
                trend.append({
                    'date': str(r['date']),
                    'count': int(r['count']),
                    'size': int(r['size']),
                })

            return jsonify(code=200, data={
                'overall': {
                    'total_files': int(overall['total_files']),
                    'total_size': int(overall['total_size']),
                    'upload_users': int(overall['upload_users']),
                },
                'by_type': by_type,
                'trend': trend,
            })
        finally:
            db.close()
