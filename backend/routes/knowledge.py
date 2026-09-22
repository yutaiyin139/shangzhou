# -*- coding: utf-8 -*-
"""知识库路由：读写本机 MySQL 中的 dify_datasets/dify_documents/dify_document_segments"""

import json
import os
import io
import uuid
from datetime import datetime
from flask import jsonify, request
from config import get_db
from utils.auth import login_required, resource_permission_required
from models.tables import (
    DIFY_DATASETS_TABLE_SQL,
    DIFY_DOCUMENTS_TABLE_SQL,
    DIFY_DOCUMENT_SEGMENTS_TABLE_SQL,
    DIFY_TENANTS_TABLE_SQL,
    DIFY_ACCOUNTS_TABLE_SQL,
)


ALLOWED_UPLOAD_EXTS = {'txt', 'md', 'markdown', 'html', 'htm', 'csv', 'properties', 'vtt', 'mdx', 'json',
                       'docx', 'pdf', 'xlsx'}
MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15MB


def _ensure_knowledge_tables():
    """确保知识库相关表已创建（含字段迁移）"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_DATASETS_TABLE_SQL)
        cur.execute(DIFY_DOCUMENTS_TABLE_SQL)
        cur.execute(DIFY_DOCUMENT_SEGMENTS_TABLE_SQL)
        cur.execute(DIFY_TENANTS_TABLE_SQL)
        cur.execute(DIFY_ACCOUNTS_TABLE_SQL)

        # 迁移：补齐 dify_document_segments 缺失的列
        cur.execute("SHOW COLUMNS FROM dify_document_segments")
        existing_cols = {row['Field'] for row in cur.fetchall()}
        migrations = [
            ("embedding", "LONGTEXT DEFAULT NULL"),
            ("embedding_model", "VARCHAR(100) DEFAULT NULL"),
            ("embedding_status", "VARCHAR(20) DEFAULT 'pending'"),
            ("parent_id", "VARCHAR(36) DEFAULT NULL"),
            ("segment_type", "VARCHAR(20) DEFAULT 'general'"),
            ("metadata", "TEXT"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing_cols:
                cur.execute(f"ALTER TABLE dify_document_segments ADD COLUMN {col_name} {col_def}")

        # 迁移：补齐缺失的索引
        cur.execute("SHOW INDEX FROM dify_document_segments")
        existing_indexes = {row['Key_name'] for row in cur.fetchall()}
        if 'idx_parent_id' not in existing_indexes:
            cur.execute("CREATE INDEX idx_parent_id ON dify_document_segments(parent_id)")
        if 'idx_segment_type' not in existing_indexes:
            cur.execute("CREATE INDEX idx_segment_type ON dify_document_segments(segment_type)")
        if 'idx_embedding_status' not in existing_indexes:
            cur.execute("CREATE INDEX idx_embedding_status ON dify_document_segments(embedding_status)")

        db.commit()
    finally:
        db.close()


def _get_default_tenant_and_creator():
    """获取默认租户和创建者 ID"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT id FROM dify_tenants ORDER BY created_at LIMIT 1')
        tenant_row = cur.fetchone()
        tenant_id = tenant_row['id'] if tenant_row else str(uuid.uuid4())
        cur.execute(r"SELECT id FROM dify_accounts WHERE name = 'yutaiyin' LIMIT 1")
        creator_row = cur.fetchone()
        creator_id = creator_row['id'] if creator_row else None
    finally:
        db.close()
    return tenant_id, creator_id


def _parse_upload_text(raw, filename):
    """把上传文件内容解析为纯文本（txt/md/html 等直接解码，docx/pdf/xlsx 用解析库）"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in ('txt', 'md', 'markdown', 'html', 'htm', 'csv', 'properties', 'vtt', 'mdx', 'json'):
        for enc in ('utf-8', 'gbk', 'utf-16'):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode('utf-8', errors='replace')
    if ext == 'docx':
        from docx import Document
        doc = Document(io.BytesIO(raw))
        parts = [p.text for p in doc.paragraphs]
        for tbl in doc.tables:
            for row in tbl.rows:
                parts.append(' | '.join(c.text for c in row.cells))
        return '\n'.join(parts)
    if ext == 'pdf':
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        return '\n'.join((page.extract_text() or '') for page in reader.pages)
    if ext == 'xlsx':
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw), read_only=True)
        rows = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                vals = [str(c) for c in row if c is not None]
                if vals:
                    rows.append(' | '.join(vals))
        return '\n'.join(rows)
    raise ValueError('不支持的文件类型: .%s' % ext)


def _segment_text(text, delimiter='\n', max_length=1024, overlap=50, clean_rules=None):
    """
    将文本分段（中文智能分段引擎）。

    参数:
    - text: 原始文本
    - delimiter: 分隔符（如 '\\n', '\\n\\n', '。', ' '）
    - max_length: 每段最大字符数
    - overlap: 段间重叠字符数
    - clean_rules: 清洗规则 {
        'replace_whitespace': bool,  # 合并连续空白
        'remove_urls': bool,         # 移除 URL 和邮箱
        'remove_extra_spaces': bool, # 移除多余空格
      }

    返回: 分段后的文本列表
    """
    import re

    if not text or not text.strip():
        return []

    # 应用清洗规则
    if clean_rules:
        if clean_rules.get('replace_whitespace'):
            text = re.sub(r'\s+', ' ', text)
        if clean_rules.get('remove_urls'):
            text = re.sub(r'https?://\S+', '', text)
            text = re.sub(r'\S+@\S+\.\S+', '', text)
        if clean_rules.get('remove_extra_spaces'):
            text = re.sub(r' +', ' ', text)

    # 检测是否包含中文内容
    has_chinese = bool(re.search(r'[一-鿿]', text))

    if has_chinese:
        # 中文智能分段
        segments = _chinese_segment(text, delimiter, max_length)
    else:
        # 英文/其他语言分段
        segments = _western_segment(text, delimiter, max_length)

    # 添加重叠
    if overlap > 0 and len(segments) > 1:
        overlapped = []
        for i, seg in enumerate(segments):
            if i > 0:
                prev_tail = segments[i - 1][-overlap:]
                seg = prev_tail + seg
            overlapped.append(seg)
        segments = overlapped

    return segments


def _chinese_segment(text, delimiter, max_length):
    """
    中文智能分段策略：
    1. 按标题/段落结构拆分（Markdown # 标题、空行分隔）
    2. 按句子边界拆分（。！？…）
    3. 智能合并短句、拆分长句
    4. 保留语义完整性
    """
    import re

    # 第一步：按结构边界拆分（标题、空行）
    # 匹配 Markdown 标题、空行分隔的段落
    structure_pattern = r'(?:^|\n)(#{1,6}\s+.+|\n{2,})'
    parts = re.split(structure_pattern, text)

    # 过滤空分段
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        # 回退：直接按空行分段
        parts = [p.strip() for p in text.split('\n\n') if p.strip()]

    if not parts:
        return []

    # 第二步：处理每个结构块，按句子边界拆分长文本
    segments = []
    current = ''

    for part in parts:
        # 保留 Markdown 标题
        is_header = re.match(r'^#{1,6}\s+', part)

        if is_header:
            # 标题单独作为一个分段，或与后续内容合并
            if current and len(current) + len(part) + 1 <= max_length:
                current += '\n' + part
            else:
                if current:
                    segments.append(current)
                current = part
            continue

        # 如果当前块可以直接加入
        if len(current) + len(part) + 1 <= max_length:
            current = (current + '\n' + part) if current else part
            continue

        # 当前块太长，需要拆分
        if current:
            segments.append(current)
            current = ''

        if len(part) <= max_length:
            current = part
        else:
            # 按中文句子边界拆分
            sentences = _split_chinese_sentences(part)
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if len(current) + len(sent) + 1 <= max_length:
                    current = (current + sent) if current else sent
                else:
                    if current:
                        segments.append(current)
                    # 单句超长，按逗号/分号拆分
                    if len(sent) > max_length:
                        sub_segments = _split_by_clauses(sent, max_length)
                        segments.extend(sub_segments[:-1])
                        current = sub_segments[-1]
                    else:
                        current = sent

    if current:
        segments.append(current)

    return segments


def _split_chinese_sentences(text):
    """
    按中文句子边界拆分文本。

    句子结束符：。！？…；.!?;（后面跟空格或换行或结尾）
    保留结束符在前一个句子中。
    """
    import re

    # 中文句子边界：。！？…；以及英文 .!?
    # 使用 lookahead 保留结束符
    pattern = r'(?<=[。！？…；.!?])\s*'
    sentences = re.split(pattern, text)

    # 合并被错误拆分的缩写（如 Dr. Mr. 等）
    merged = []
    i = 0
    while i < len(sentences):
        s = sentences[i]
        # 检查是否是缩写结尾
        if i + 1 < len(sentences) and re.search(r'\b[DMJS]r\.$', s, re.IGNORECASE):
            s = s + sentences[i + 1]
            i += 2
        else:
            i += 1
        merged.append(s)

    return [s for s in merged if s.strip()]


def _split_by_clauses(text, max_length):
    """
    按子句（逗号、分号、冒号）拆分超长句子。
    """
    import re

    # 按逗号、分号、冒号拆分
    pattern = r'(?<=[，：；,;:])'
    clauses = re.split(pattern, text)

    segments = []
    current = ''

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        if len(current) + len(clause) + 1 <= max_length:
            current = (current + clause) if current else clause
        else:
            if current:
                segments.append(current)
            # 子句仍超长，强制截断
            if len(clause) > max_length:
                for i in range(0, len(clause), max_length):
                    chunk = clause[i:i + max_length]
                    if len(chunk) > max_length // 2:
                        segments.append(chunk)
                    elif segments:
                        segments[-1] += chunk
                    else:
                        segments.append(chunk)
                current = ''
            else:
                current = clause

    if current:
        segments.append(current)

    return segments


def _western_segment(text, delimiter, max_length):
    """
    英文/西方语言分段策略：
    1. 按分隔符或段落分段
    2. 按句子边界拆分
    3. 智能合并
    """
    import re

    # 按分隔符分段
    if delimiter and delimiter in text:
        actual_delimiter = delimiter.replace('\\n', '\n').replace('\\t', '\t')
        parts = text.split(actual_delimiter)
    else:
        parts = text.split('\n\n')

    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return []

    segments = []
    current = ''

    for part in parts:
        if len(current) + len(part) + 1 <= max_length:
            current = (current + '\n' + part) if current else part
        else:
            if current:
                segments.append(current)
            if len(part) > max_length:
                # 按英文句子边界拆分
                sentences = re.split(r'(?<=[.!?])\s+', part)
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(current) + len(sent) + 1 <= max_length:
                        current = (current + ' ' + sent) if current else sent
                    else:
                        if current:
                            segments.append(current)
                        if len(sent) > max_length:
                            # 强制截断
                            for i in range(0, len(sent), max_length):
                                chunk = sent[i:i + max_length]
                                if len(chunk) > max_length // 2:
                                    segments.append(chunk)
                                elif segments:
                                    segments[-1] += chunk
                                else:
                                    segments.append(chunk)
                            current = ''
                        else:
                            current = sent
            else:
                current = part

    if current:
        segments.append(current)

    return segments


def _extract_document_structure(text):
    """
    提取文档结构（标题层级）。

    返回: 结构列表 [{level, title, path, start_pos, end_pos}]
    """
    import re
    structure = []
    lines = text.split('\n')
    current_path = []
    current_start = 0

    for i, line in enumerate(lines):
        header_match = re.match(r'^(#{1,6})\s+(.+)', line)
        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            current_path = current_path[:level - 1] + [title]
            structure.append({
                'level': level,
                'title': title,
                'path': ' > '.join(current_path),
                'line_number': i,
            })

    return structure


def _get_segment_structure(text, segment_start, segment_end, structure):
    """
    根据分段位置获取该分段所属的文档结构路径。

    参数:
    - text: 原始文本
    - segment_start: 分段起始字符位置
    - segment_end: 分段结束字符位置
    - structure: 文档结构列表

    返回: 结构路径字符串
    """
    # 将字符位置转换为行号
    lines_before_start = text[:segment_start].count('\n')
    lines_before_end = text[:segment_end].count('\n')

    # 找到该分段所属的最深标题
    current_path = []
    for header in structure:
        if header['line_number'] <= lines_before_start:
            # 根据层级调整路径
            while current_path and current_path[-1]['level'] >= header['level']:
                current_path.pop()
            current_path.append(header)
        elif header['line_number'] > lines_before_end:
            break

    return ' > '.join(h['title'] for h in current_path) if current_path else ''


def _segment_parent_child(text, child_max=256, parent_max=1024, overlap=50, clean_rules=None):
    """
    父子分段：子段落用于精准检索，父段落提供上下文。

    参数:
    - text: 原始文本
    - child_max: 子段落最大字符数
    - parent_max: 父段落最大字符数
    - overlap: 段间重叠字符数
    - clean_rules: 清洗规则

    返回: 分段列表 [{content, segment_type, parent_id, position, metadata}]
    """
    import re

    if not text or not text.strip():
        return []

    # 应用清洗规则
    if clean_rules:
        if clean_rules.get('replace_whitespace'):
            text = re.sub(r'\s+', ' ', text)
        if clean_rules.get('remove_urls'):
            text = re.sub(r'https?://\S+', '', text)
            text = re.sub(r'\S+@\S+\.\S+', '', text)
        if clean_rules.get('remove_extra_spaces'):
            text = re.sub(r' +', ' ', text)

    structure = _extract_document_structure(text)
    segments = []

    # 第一步：按 parent_max 生成父段落
    parent_segments = _segment_text(text, '\n', parent_max, 0, {})

    for parent_idx, parent_text in enumerate(parent_segments):
        parent_text = parent_text.strip()
        if not parent_text:
            continue

        parent_id = str(uuid.uuid4())
        parent_start = text.find(parent_text)
        parent_end = parent_start + len(parent_text) if parent_start >= 0 else -1

        # 获取父段落的文档结构路径
        parent_structure_path = ''
        if parent_start >= 0:
            parent_structure_path = _get_segment_structure(text, parent_start, parent_end, structure)

        # 添加父段落
        segments.append({
            'id': parent_id,
            'content': parent_text,
            'segment_type': 'parent',
            'parent_id': None,
            'position': parent_idx,
            'metadata': json.dumps({
                'structure_path': parent_structure_path,
                'char_count': len(parent_text),
            }, ensure_ascii=False),
        })

        # 第二步：在父段落内按 child_max 生成子段落
        if len(parent_text) > child_max:
            child_segments = _segment_text(parent_text, '\n', child_max, overlap, {})
            for child_idx, child_text in enumerate(child_segments):
                child_text = child_text.strip()
                if not child_text:
                    continue
                segments.append({
                    'id': str(uuid.uuid4()),
                    'content': child_text,
                    'segment_type': 'child',
                    'parent_id': parent_id,
                    'position': child_idx,
                    'metadata': json.dumps({
                        'structure_path': parent_structure_path,
                        'parent_index': parent_idx,
                        'char_count': len(child_text),
                    }, ensure_ascii=False),
                })
        else:
            # 父段落本身较短，无需拆分子段落
            segments.append({
                'id': str(uuid.uuid4()),
                'content': parent_text,
                'segment_type': 'child',
                'parent_id': parent_id,
                'position': 0,
                'metadata': json.dumps({
                    'structure_path': parent_structure_path,
                    'parent_index': parent_idx,
                    'char_count': len(parent_text),
                }, ensure_ascii=False),
            })

    return segments


def _segment_qa(text, model_cfg=None):
    """
    使用 LLM 生成问答对分段。

    参数:
    - text: 原始文本
    - model_cfg: 模型配置

    返回: 问答对列表 [{content, segment_type, metadata}]
    """
    from utils.llm import _call_llm_with_config

    if not text or not text.strip():
        return []

    system_prompt = """请根据以下文本生成 3-5 个问答对。
格式：JSON 数组 [{"question": "...", "answer": "..."}]
要求：问题覆盖文本核心，答案简洁准确。只输出 JSON 数组，不要其他内容。"""

    content, error = _call_llm_with_config(system_prompt, text[:4000], model_cfg, temperature=0.3)
    if error:
        return []

    # 提取 JSON 列表
    qa_list = _extract_json_list(content)
    segments = []
    for i, qa in enumerate(qa_list):
        if not isinstance(qa, dict):
            continue
        question = qa.get('question', '').strip()
        answer = qa.get('answer', '').strip()
        if not question or not answer:
            continue

        segments.append({
            'id': str(uuid.uuid4()),
            'content': f"Q: {question}\nA: {answer}",
            'segment_type': 'qa',
            'parent_id': None,
            'position': i,
            'metadata': json.dumps({
                'question': question,
                'answer': answer,
                'char_count': len(question) + len(answer),
            }, ensure_ascii=False),
        })

    return segments


def _extract_json_list(text):
    """
    从文本中提取 JSON 列表。
    """
    import re
    import json

    # 尝试直接解析
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except Exception:
        pass

    # 尝试提取 JSON 数组
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except Exception:
            pass

    return []


def _import_notion(token, page_id):
    """
    从 Notion 导入页面内容。

    参数:
    - token: Notion API Token
    - page_id: 页面 ID

    返回: 页面内容文本
    """
    import urllib.request
    import json

    url = f'https://api.notion.com/v1/pages/{page_id}'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
    })

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    # 获取页面标题
    title = ''
    if 'properties' in data:
        for prop in data['properties'].values():
            if prop.get('type') == 'title':
                title_parts = prop.get('title', [])
                if title_parts:
                    title = ''.join([t.get('plain_text', '') for t in title_parts])
                break

    # 获取页面内容（通过 blocks API）
    blocks_url = f'https://api.notion.com/v1/blocks/{page_id}/children?page_size=100'
    blocks_req = urllib.request.Request(blocks_url, headers={
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
    })

    content_parts = [title] if title else []
    with urllib.request.urlopen(blocks_req, timeout=30) as resp:
        blocks_data = json.loads(resp.read().decode('utf-8'))

    for block in blocks_data.get('results', []):
        block_type = block.get('type', '')
        if block_type in ('paragraph', 'heading_1', 'heading_2', 'heading_3',
                          'bulleted_list_item', 'numbered_list_item', 'quote'):
            text_key = block_type.replace('heading_', 'heading_')
            text_data = block.get(block_type, {})
            texts = text_data.get('rich_text', []) or text_data.get('text', [])
            if texts:
                text = ''.join([t.get('plain_text', '') for t in texts])
                if block_type.startswith('heading_'):
                    level = block_type[-1]
                    content_parts.append(f"{'#' * int(level)} {text}")
                elif block_type == 'bulleted_list_item':
                    content_parts.append(f"- {text}")
                elif block_type == 'numbered_list_item':
                    content_parts.append(f"1. {text}")
                elif block_type == 'quote':
                    content_parts.append(f"> {text}")
                else:
                    content_parts.append(text)

    return '\n\n'.join(content_parts)


def _import_website(url, max_depth=1, selector=None):
    """
    爬取网站内容。

    参数:
    - url: 网站 URL
    - max_depth: 爬取深度
    - selector: CSS 选择器（可选）

    返回: 页面内容文本
    """
    import urllib.request
    import re
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        def __init__(self, selector=None):
            super().__init__()
            self.selector = selector
            self.text_parts = []
            self.current_tag = ''
            self.skip_tags = {'script', 'style', 'nav', 'footer', 'header'}
            self.skip_level = 0

        def handle_starttag(self, tag, attrs):
            self.current_tag = tag
            if tag in self.skip_tags:
                self.skip_level += 1
            # 检查 CSS 选择器
            if self.selector and tag in ('div', 'section', 'article', 'main'):
                attrs_dict = dict(attrs)
                class_str = attrs_dict.get('class', '')
                id_str = attrs_dict.get('id', '')
                # 简单匹配：选择器作为 class 或 id 的子串
                if self.selector in class_str or self.selector in id_str:
                    self.text_parts.append('\n')

        def handle_endtag(self, tag):
            if tag in self.skip_tags:
                self.skip_level -= 1
            if tag in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'):
                self.text_parts.append('\n')

        def handle_data(self, data):
            if self.skip_level <= 0:
                stripped = data.strip()
                if stripped:
                    self.text_parts.append(stripped)

    # 安全加固：SSRF 防护检查
    from utils.ssrf import is_safe_url
    if not is_safe_url(url):
        raise ValueError('URL 被安全策略禁止（SSRF 防护）')

    # 获取页面
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode('utf-8', errors='replace')

    # 提取文本
    extractor = _TextExtractor(selector)
    extractor.feed(html)
    text = ' '.join(extractor.text_parts)

    # 清理文本
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    return text.strip()


def _knowledge_create_with_files(files, segmentation=None):
    """
    上传文件创建知识库。

    参数:
    - files: 上传的文件列表
    - segmentation: 分段配置 {
        'mode': str,            # 分段模式：auto/parent_child/qa
        'delimiter': str,       # 分隔符
        'max_length': int,      # 每段最大字符数
        'overlap': int,         # 段间重叠字符数
        'clean_rules': dict,    # 清洗规则
        'child_max': int,       # 父子分段子段落最大字符数
        'parent_max': int,      # 父子分段父段落最大字符数
      }
    """
    if len(files) > 5:
        return jsonify(code=400, msg='每批最多上传 5 个文件')
    checked = []
    for f in files:
        fn = f.filename or ''
        ext = fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''
        if ext not in ALLOWED_UPLOAD_EXTS:
            return jsonify(code=400, msg='不支持的文件类型: .%s（支持 MD/TXT/HTML/CSV/DOCX/PDF/XLSX 等）' % ext)
        f.stream.seek(0, 2)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > MAX_UPLOAD_SIZE:
            return jsonify(code=400, msg='文件「%s」超过 15MB 限制' % fn)
        checked.append((f, fn, ext))
    name = os.path.splitext(checked[0][1])[0].strip() or '未命名知识库'

    # 解析分段配置
    seg_config = segmentation or {}
    mode = seg_config.get('mode', 'auto')
    delimiter = seg_config.get('delimiter', '\n')
    max_length = int(seg_config.get('max_length', 1024))
    overlap = int(seg_config.get('overlap', 50))
    clean_rules = seg_config.get('clean_rules', {})
    child_max = int(seg_config.get('child_max', 256))
    parent_max = int(seg_config.get('parent_max', 1024))

    tenant_id, creator_id = _get_default_tenant_and_creator()
    batch = 'manual-' + datetime.now().strftime('%Y%m%d%H%M%S%f')
    dataset_id = str(uuid.uuid4())
    try:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO dify_datasets (id, tenant_id, name, description, created_by, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (dataset_id, tenant_id, name, '', creator_id, creator_id))

            total_segments = 0
            for pos, (f, fn, ext) in enumerate(checked):
                text = _parse_upload_text(f.stream.read(), fn)
                wc = len(text.replace('\n', '').replace(' ', ''))
                doc_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO dify_documents (id, tenant_id, dataset_id, position, data_source_type, data_source_info,
                                               batch, name, created_from, created_by, indexing_status, word_count)
                    VALUES (%s, %s, %s, %s, 'upload_file', %s, %s, %s, 'api', %s, 'completed', %s)
                """, (doc_id, tenant_id, dataset_id, pos, json.dumps({'filename': fn, 'size': 0}, ensure_ascii=False), batch, fn, creator_id, wc))

                # 根据模式选择分段策略
                if mode == 'parent_child':
                    seg_results = _segment_parent_child(text, child_max, parent_max, overlap, clean_rules)
                elif mode == 'qa':
                    seg_results = _segment_qa(text)
                else:
                    # 普通模式：保留文档结构元数据
                    plain_segments = _segment_text(text, delimiter, max_length, overlap, clean_rules)
                    if not plain_segments:
                        plain_segments = [text]
                    structure = _extract_document_structure(text)
                    seg_results = []
                    for idx, seg_text in enumerate(plain_segments):
                        seg_start = text.find(seg_text)
                        seg_end = seg_start + len(seg_text) if seg_start >= 0 else -1
                        structure_path = ''
                        if seg_start >= 0:
                            structure_path = _get_segment_structure(text, seg_start, seg_end, structure)
                        seg_results.append({
                            'id': str(uuid.uuid4()),
                            'content': seg_text,
                            'segment_type': 'general',
                            'parent_id': None,
                            'position': idx,
                            'metadata': json.dumps({
                                'structure_path': structure_path,
                                'char_count': len(seg_text),
                            }, ensure_ascii=False),
                        })

                # 写入分段
                for seg_idx, seg in enumerate(seg_results):
                    seg_text = seg.get('content', '')
                    seg_wc = len(seg_text.replace('\n', '').replace(' ', ''))
                    seg_tokens = max(1, int(len(seg_text) / 3))
                    cur.execute("""
                        INSERT INTO dify_document_segments (id, tenant_id, dataset_id, document_id, position, content,
                                                           word_count, tokens, hit_count, status, created_by,
                                                           parent_id, segment_type, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 'completed', %s, %s, %s, %s)
                    """, (seg['id'], tenant_id, dataset_id, doc_id, seg_idx, seg_text, seg_wc, seg_tokens,
                          creator_id, seg.get('parent_id'), seg.get('segment_type', 'general'),
                          seg.get('metadata', '')))
                total_segments += len(seg_results)

            db.commit()
            return jsonify(code=200, data={
                'id': str(dataset_id),
                'name': name,
                'doc_count': len(checked),
                'segment_count': total_segments,
                'mode': mode,
            })
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='创建知识库失败: %s' % e)
        finally:
            db.close()
    except Exception as e:
        return jsonify(code=500, msg='创建知识库失败: %s' % e)


def register_knowledge_routes(app):
    """注册知识库相关路由"""

    @app.route('/api/knowledge/datasets', methods=['GET'])
    @login_required
    def knowledge_datasets():
        """读取本机 MySQL 中的知识库（dify_datasets）列表"""
        _ensure_knowledge_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute("""
                    SELECT d.id, d.name, d.description,
                           COUNT(doc.id) AS doc_count,
                           d.created_at, d.updated_at
                    FROM dify_datasets d
                    LEFT JOIN dify_documents doc
                           ON doc.dataset_id = d.id AND doc.indexing_status != 'deleted'
                    GROUP BY d.id
                    ORDER BY d.updated_at DESC
                """)
                rows = cur.fetchall()
            finally:
                db.close()
            data = [{
                'id': r['id'],
                'name': r['name'],
                'description': r['description'] or '',
                'doc_count': r['doc_count'],
                'created_at': (r['created_at'].isoformat() + 'Z') if r['created_at'] else '',
                'updated_at': (r['updated_at'].isoformat() + 'Z') if r['updated_at'] else '',
            } for r in rows]
            return jsonify(code=200, data=data)
        except Exception as e:
            return jsonify(code=500, msg='读取知识库失败: %s' % e)

    @app.route('/api/knowledge/datasets', methods=['POST'])
    @login_required
    def knowledge_create_dataset():
        """
        在 MySQL 中创建知识库。

        - multipart/form-data: 上传文件创建含文档的知识库
          - files: 文件列表
          - segmentation: JSON 字符串，分段配置 {delimiter, max_length, overlap, clean_rules}

        - application/json: 创建空知识库
          - name: 知识库名称
          - description: 描述
        """
        _ensure_knowledge_tables()
        files = request.files.getlist('files')
        if files:
            # 解析分段配置
            segmentation = None
            seg_str = request.form.get('segmentation', '').strip()
            if seg_str:
                try:
                    segmentation = json.loads(seg_str)
                except Exception:
                    segmentation = None
            return _knowledge_create_with_files(files, segmentation)

        body = request.get_json(silent=True) or {}
        name = (body.get('name') or '').strip()
        if not name:
            return jsonify(code=400, msg='知识库名称不能为空')
        if len(name) > 255:
            return jsonify(code=400, msg='知识库名称过长（最多 255 字符）')
        description = (body.get('description') or '').strip()
        tenant_id, creator_id = _get_default_tenant_and_creator()
        new_id = str(uuid.uuid4())
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute("""
                    INSERT INTO dify_datasets (id, tenant_id, name, description, created_by, updated_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (new_id, tenant_id, name, description, creator_id, creator_id))
                db.commit()
                return jsonify(code=200, data={'id': new_id, 'name': name})
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='创建知识库失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='创建知识库失败: %s' % e)

    @app.route('/api/knowledge/datasets/<dataset_id>', methods=['GET'])
    @login_required
    @resource_permission_required('dataset', 'dataset_id', 'read')
    def knowledge_dataset_detail(dataset_id):
        """获取知识库详情（含文档列表）"""
        _ensure_knowledge_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'SELECT * FROM dify_datasets WHERE id = %s', (dataset_id,))
                ds = cur.fetchone()
                if not ds:
                    return jsonify(code=404, msg='知识库不存在')
                # 获取文档列表
                cur.execute(r'''
                    SELECT id, name, word_count, indexing_status, enabled, created_at
                    FROM dify_documents
                    WHERE dataset_id = %s AND indexing_status != 'deleted'
                    ORDER BY position
                ''', (dataset_id,))
                docs = cur.fetchall()
            finally:
                db.close()
            # 获取关键词索引统计（3.2）
            keyword_stats = {'keyword_count': 0, 'indexed_segments': 0}
            try:
                from engine.keyword_engine import get_keyword_stats
                keyword_stats = get_keyword_stats(dataset_id)
            except Exception:
                pass
            return jsonify(code=200, data={
                'id': ds['id'],
                'name': ds['name'],
                'description': ds['description'] or '',
                'indexing_technique': ds['indexing_technique'] or 'high_quality',
                'keyword_count': keyword_stats.get('keyword_count', 0),
                'indexed_segments': keyword_stats.get('indexed_segments', 0),
                'created_at': (ds['created_at'].isoformat() + 'Z') if ds['created_at'] else '',
                'updated_at': (ds['updated_at'].isoformat() + 'Z') if ds['updated_at'] else '',
                'documents': [{
                    'id': d['id'],
                    'name': d['name'],
                    'word_count': d['word_count'] or 0,
                    'indexing_status': d['indexing_status'] or 'waiting',
                    'enabled': bool(d['enabled']),
                    'created_at': (d['created_at'].isoformat() + 'Z') if d['created_at'] else '',
                } for d in docs],
            })
        except Exception as e:
            return jsonify(code=500, msg='获取知识库详情失败: %s' % e)

    @app.route('/api/knowledge/datasets/<dataset_id>', methods=['PUT'])
    @login_required
    @resource_permission_required('dataset', 'dataset_id', 'write')
    def knowledge_update_dataset(dataset_id):
        """更新知识库信息"""
        _ensure_knowledge_tables()
        body = request.get_json(silent=True) or {}
        name = (body.get('name') or '').strip()
        description = (body.get('description') or '').strip()
        if not name:
            return jsonify(code=400, msg='知识库名称不能为空')
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''
                    UPDATE dify_datasets
                    SET name = %s, description = %s, updated_at = %s
                    WHERE id = %s
                ''', (name, description, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), dataset_id))
                db.commit()
                if not cur.rowcount:
                    return jsonify(code=404, msg='知识库不存在')
                return jsonify(code=200, msg='更新成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='更新知识库失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='更新知识库失败: %s' % e)

    @app.route('/api/knowledge/datasets/<dataset_id>', methods=['DELETE'])
    @login_required
    @resource_permission_required('dataset', 'dataset_id', 'admin')
    def knowledge_delete_dataset(dataset_id):
        """删除知识库（级联删除文档、分段、关键词索引）"""
        _ensure_knowledge_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 获取所有文档ID
                cur.execute(r'SELECT id FROM dify_documents WHERE dataset_id = %s', (dataset_id,))
                doc_ids = [r['id'] for r in cur.fetchall()]
                # 删除分段
                if doc_ids:
                    placeholders = ','.join(['%s'] * len(doc_ids))
                    cur.execute(f'DELETE FROM dify_document_segments WHERE document_id IN ({placeholders})', doc_ids)
                # 删除关键词索引（3.2）
                cur.execute(r'DELETE FROM dataset_keyword_tables WHERE dataset_id = %s', (dataset_id,))
                # 删除元数据绑定和字段（2.3）
                cur.execute(r'SELECT id FROM dataset_metadatas WHERE dataset_id = %s', (dataset_id,))
                meta_ids = [r['id'] for r in cur.fetchall()]
                if meta_ids:
                    placeholders = ','.join(['%s'] * len(meta_ids))
                    cur.execute(f'DELETE FROM dataset_metadata_bindings WHERE metadata_id IN ({placeholders})', meta_ids)
                cur.execute(r'DELETE FROM dataset_metadatas WHERE dataset_id = %s', (dataset_id,))
                # 删除文档
                cur.execute(r'DELETE FROM dify_documents WHERE dataset_id = %s', (dataset_id,))
                # 删除知识库
                cur.execute(r'DELETE FROM dify_datasets WHERE id = %s', (dataset_id,))
                db.commit()
                if not cur.rowcount:
                    return jsonify(code=404, msg='知识库不存在')
                return jsonify(code=200, msg='删除成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='删除知识库失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='删除知识库失败: %s' % e)

    @app.route('/api/knowledge/datasets/<dataset_id>/documents/<doc_id>', methods=['DELETE'])
    @login_required
    @resource_permission_required('dataset', 'dataset_id', 'write')
    def knowledge_delete_document(dataset_id, doc_id):
        """删除文档（级联删除分段和关键词索引）"""
        _ensure_knowledge_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 获取分段ID列表（用于删除关键词索引）
                cur.execute(r'SELECT id FROM dify_document_segments WHERE document_id = %s', (doc_id,))
                seg_ids = [r['id'] for r in cur.fetchall()]
                # 删除分段
                cur.execute(r'DELETE FROM dify_document_segments WHERE document_id = %s', (doc_id,))
                # 删除关键词索引（3.2）
                if seg_ids:
                    placeholders = ','.join(['%s'] * len(seg_ids))
                    cur.execute(f'DELETE FROM dataset_keyword_tables WHERE segment_id IN ({placeholders})', seg_ids)
                # 删除文档
                cur.execute(r'DELETE FROM dify_documents WHERE id = %s AND dataset_id = %s', (doc_id, dataset_id))
                db.commit()
                if not cur.rowcount:
                    return jsonify(code=404, msg='文档不存在')
                return jsonify(code=200, msg='删除成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='删除文档失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='删除文档失败: %s' % e)

    @app.route('/api/knowledge/preview-segments', methods=['POST'])
    def knowledge_preview_segments():
        """
        预览分段结果。

        参数:
        - content: 文本内容
        - file: 上传文件（与 content 二选一）
        - segmentation: 分段配置 {delimiter, max_length, overlap, clean_rules}

        返回:
        - segments: 分段列表 [{index, content, word_count}]
        - total: 总分段数
        """
        _ensure_knowledge_tables()

        # 获取文本内容
        text = ''
        if 'file' in request.files:
            f = request.files['file']
            fn = f.filename or ''
            raw = f.stream.read()
            try:
                text = _parse_upload_text(raw, fn)
            except Exception as e:
                return jsonify(code=400, msg='文件解析失败: %s' % e)
        else:
            body = request.get_json(silent=True) or {}
            text = body.get('content', '')

        if not text or not text.strip():
            return jsonify(code=400, msg='请提供文本内容或上传文件')

        # 解析分段配置
        segmentation = {}
        if 'file' in request.files:
            seg_str = request.form.get('segmentation', '').strip()
            if seg_str:
                try:
                    segmentation = json.loads(seg_str)
                except Exception:
                    segmentation = {}
        else:
            body = request.get_json(silent=True) or {}
            segmentation = body.get('segmentation', {})

        delimiter = segmentation.get('delimiter', '\n')
        max_length = int(segmentation.get('max_length', 1024))
        overlap = int(segmentation.get('overlap', 50))
        clean_rules = segmentation.get('clean_rules', {})
        mode = segmentation.get('mode', 'auto')

        # 根据模式选择分段策略
        if mode == 'parent_child':
            child_max = int(segmentation.get('child_max', 256))
            parent_max = int(segmentation.get('parent_max', 1024))
            seg_results = _segment_parent_child(text, child_max, parent_max, overlap, clean_rules)
            segments_data = [
                {
                    'index': i,
                    'content': s.get('content', ''),
                    'word_count': len(s.get('content', '').replace('\n', '').replace(' ', '')),
                    'char_count': len(s.get('content', '')),
                    'segment_type': s.get('segment_type', 'general'),
                    'parent_id': s.get('parent_id'),
                    'metadata': s.get('metadata', ''),
                }
                for i, s in enumerate(seg_results)
            ]
        elif mode == 'qa':
            seg_results = _segment_qa(text)
            segments_data = [
                {
                    'index': i,
                    'content': s.get('content', ''),
                    'word_count': len(s.get('content', '').replace('\n', '').replace(' ', '')),
                    'char_count': len(s.get('content', '')),
                    'segment_type': s.get('segment_type', 'qa'),
                    'parent_id': s.get('parent_id'),
                    'metadata': s.get('metadata', ''),
                }
                for i, s in enumerate(seg_results)
            ]
        else:
            # 普通模式
            segments = _segment_text(text, delimiter, max_length, overlap, clean_rules)
            segments_data = [
                {
                    'index': i,
                    'content': s,
                    'word_count': len(s.replace('\n', '').replace(' ', '')),
                    'char_count': len(s),
                    'segment_type': 'general',
                    'parent_id': None,
                    'metadata': '',
                }
                for i, s in enumerate(segments)
            ]

        return jsonify(code=200, data={
            'segments': segments_data,
            'total': len(segments_data),
            'config': {
                'delimiter': delimiter,
                'max_length': max_length,
                'overlap': overlap,
                'clean_rules': clean_rules,
                'mode': mode,
            }
        })

    @app.route('/api/knowledge/datasets/<dataset_id>/documents/<doc_id>/segments', methods=['GET'])
    def knowledge_document_segments(dataset_id, doc_id):
        """获取文档的分段列表"""
        _ensure_knowledge_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''
                    SELECT id, position, content, word_count, tokens, hit_count, enabled,
                           status, parent_id, segment_type, metadata, created_at
                    FROM dify_document_segments
                    WHERE document_id = %s
                    ORDER BY position
                ''', (doc_id,))
                rows = cur.fetchall()
            finally:
                db.close()
            segments = [{
                'id': r['id'],
                'position': r['position'],
                'content': r['content'] or '',
                'word_count': r['word_count'] or 0,
                'tokens': r['tokens'] or 0,
                'hit_count': r['hit_count'] or 0,
                'enabled': bool(r['enabled']),
                'status': r['status'] or 'completed',
                'parent_id': r['parent_id'],
                'segment_type': r['segment_type'] or 'general',
                'metadata': r['metadata'] or '',
                'created_at': (r['created_at'].isoformat() + 'Z') if r['created_at'] else '',
            } for r in rows]
            return jsonify(code=200, data={'segments': segments, 'total': len(segments)})
        except Exception as e:
            return jsonify(code=500, msg='获取分段列表失败: %s' % e)

    @app.route('/api/knowledge/segments', methods=['POST'])
    def knowledge_create_segment():
        """创建分段"""
        _ensure_knowledge_tables()
        body = request.get_json(silent=True) or {}
        document_id = body.get('document_id', '').strip()
        content = body.get('content', '').strip()
        if not document_id:
            return jsonify(code=400, msg='文档 ID 不能为空')
        if not content:
            return jsonify(code=400, msg='分段内容不能为空')
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 获取文档信息
                cur.execute(r'SELECT tenant_id, dataset_id FROM dify_documents WHERE id = %s', (document_id,))
                doc = cur.fetchone()
                if not doc:
                    return jsonify(code=404, msg='文档不存在')
                # 获取当前最大 position
                cur.execute(r'SELECT MAX(position) as max_pos FROM dify_document_segments WHERE document_id = %s', (document_id,))
                max_pos = cur.fetchone()['max_pos'] or 0
                seg_id = str(uuid.uuid4())
                seg_wc = len(content.replace('\n', '').replace(' ', ''))
                seg_tokens = max(1, int(len(content) / 3))
                cur.execute("""
                    INSERT INTO dify_document_segments (id, tenant_id, dataset_id, document_id, position, content,
                                                       word_count, tokens, hit_count, status, created_by,
                                                       segment_type, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 'completed', NULL, 'general', '')
                """, (seg_id, doc['tenant_id'], doc['dataset_id'], document_id, max_pos + 1, content, seg_wc, seg_tokens))
                db.commit()
                # 异步建立关键词索引（3.2）
                try:
                    from engine.keyword_engine import build_keyword_index_for_segment
                    build_keyword_index_for_segment(doc['dataset_id'], seg_id, content)
                except Exception:
                    pass
                return jsonify(code=200, data={'id': seg_id})
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='创建分段失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='创建分段失败: %s' % e)

    @app.route('/api/knowledge/segments/<segment_id>', methods=['PUT'])
    def knowledge_update_segment(segment_id):
        """更新分段"""
        _ensure_knowledge_tables()
        body = request.get_json(silent=True) or {}
        content = body.get('content', '').strip()
        if not content:
            return jsonify(code=400, msg='分段内容不能为空')
        try:
            db = get_db()
            try:
                cur = db.cursor()
                seg_wc = len(content.replace('\n', '').replace(' ', ''))
                seg_tokens = max(1, int(len(content) / 3))
                cur.execute(r'''
                    UPDATE dify_document_segments
                    SET content = %s, word_count = %s, tokens = %s, updated_at = %s
                    WHERE id = %s
                ''', (content, seg_wc, seg_tokens, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), segment_id))
                db.commit()
                if not cur.rowcount:
                    return jsonify(code=404, msg='分段不存在')
                # 更新关键词索引（3.2）
                try:
                    cur.execute(r'SELECT dataset_id FROM dify_document_segments WHERE id = %s', (segment_id,))
                    seg_info = cur.fetchone()
                    if seg_info:
                        from engine.keyword_engine import build_keyword_index_for_segment
                        build_keyword_index_for_segment(seg_info['dataset_id'], segment_id, content)
                except Exception:
                    pass
                return jsonify(code=200, msg='更新成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='更新分段失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='更新分段失败: %s' % e)

    @app.route('/api/knowledge/segments/<segment_id>', methods=['DELETE'])
    def knowledge_delete_segment(segment_id):
        """删除分段"""
        _ensure_knowledge_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'DELETE FROM dify_document_segments WHERE id = %s', (segment_id,))
                db.commit()
                if not cur.rowcount:
                    return jsonify(code=404, msg='分段不存在')
                # 删除关键词索引（3.2）
                try:
                    cur.execute(r'DELETE FROM dataset_keyword_tables WHERE segment_id = %s', (segment_id,))
                    db.commit()
                except Exception:
                    pass
                return jsonify(code=200, msg='删除成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='删除分段失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='删除分段失败: %s' % e)

    @app.route('/api/knowledge/segments/<segment_id>/resegment', methods=['POST'])
    def knowledge_resegment(segment_id):
        """重新分段（将一个分段拆分为多个）"""
        _ensure_knowledge_tables()
        body = request.get_json(silent=True) or {}
        delimiter = body.get('delimiter', '\n')
        max_length = int(body.get('max_length', 1024))
        overlap = int(body.get('overlap', 50))
        clean_rules = body.get('clean_rules', {})
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 获取原分段
                cur.execute(r'SELECT * FROM dify_document_segments WHERE id = %s', (segment_id,))
                seg = cur.fetchone()
                if not seg:
                    return jsonify(code=404, msg='分段不存在')
                # 删除原分段
                cur.execute(r'DELETE FROM dify_document_segments WHERE id = %s', (segment_id,))
                # 重新分段
                segments = _segment_text(seg['content'] or '', delimiter, max_length, overlap, clean_rules)
                if not segments:
                    segments = [seg['content'] or '']
                # 插入新分段
                for idx, seg_text in enumerate(segments):
                    seg_wc = len(seg_text.replace('\n', '').replace(' ', ''))
                    seg_tokens = max(1, int(len(seg_text) / 3))
                    cur.execute("""
                        INSERT INTO dify_document_segments (id, tenant_id, dataset_id, document_id, position, content,
                                                           word_count, tokens, hit_count, status, created_by,
                                                           segment_type, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 'completed', NULL, 'general', '')
                    """, (str(uuid.uuid4()), seg['tenant_id'], seg['dataset_id'], seg['document_id'],
                          seg['position'] + idx, seg_text, seg_wc, seg_tokens))
                db.commit()
                return jsonify(code=200, data={'segment_count': len(segments)})
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='重新分段失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='重新分段失败: %s' % e)

    @app.route('/api/knowledge/import/notion', methods=['POST'])
    def knowledge_import_notion():
        """从 Notion 导入文档"""
        _ensure_knowledge_tables()
        body = request.get_json(silent=True) or {}
        token = body.get('notion_token', '').strip()
        page_id = body.get('page_id', '').strip()
        dataset_id = body.get('dataset_id', '').strip()
        if not token:
            return jsonify(code=400, msg='Notion Token 不能为空')
        if not page_id:
            return jsonify(code=400, msg='页面 ID 不能为空')
        if not dataset_id:
            return jsonify(code=400, msg='知识库 ID 不能为空')
        try:
            # 获取页面内容
            text = _import_notion(token, page_id)
            if not text:
                return jsonify(code=400, msg='无法获取 Notion 页面内容')
            # 创建文档
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'SELECT tenant_id FROM dify_datasets WHERE id = %s', (dataset_id,))
                ds = cur.fetchone()
                if not ds:
                    return jsonify(code=404, msg='知识库不存在')
                tenant_id = ds['tenant_id']
                wc = len(text.replace('\n', '').replace(' ', ''))
                doc_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO dify_documents (id, tenant_id, dataset_id, position, data_source_type, data_source_info,
                                               batch, name, created_from, created_by, indexing_status, word_count)
                    VALUES (%s, %s, %s, 0, 'notion_import', %s, %s, %s, 'api', NULL, 'completed', %s)
                """, (doc_id, tenant_id, dataset_id, json.dumps({'page_id': page_id}, ensure_ascii=False),
                      'notion-import', 'Notion 导入', wc))
                # 分段
                segments = _segment_text(text, '\n', 1024, 50, {})
                if not segments:
                    segments = [text]
                for seg_idx, seg_text in enumerate(segments):
                    seg_wc = len(seg_text.replace('\n', '').replace(' ', ''))
                    seg_tokens = max(1, int(len(seg_text) / 3))
                    cur.execute("""
                        INSERT INTO dify_document_segments (id, tenant_id, dataset_id, document_id, position, content,
                                                           word_count, tokens, hit_count, status, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 'completed', NULL)
                    """, (str(uuid.uuid4()), tenant_id, dataset_id, doc_id, seg_idx, seg_text, seg_wc, seg_tokens))
                db.commit()
                return jsonify(code=200, data={
                    'id': doc_id,
                    'name': 'Notion 导入',
                    'segment_count': len(segments),
                })
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='导入 Notion 失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='导入 Notion 失败: %s' % e)

    @app.route('/api/knowledge/import/website', methods=['POST'])
    def knowledge_import_website():
        """从网站爬取内容导入"""
        _ensure_knowledge_tables()
        body = request.get_json(silent=True) or {}
        url = body.get('url', '').strip()
        dataset_id = body.get('dataset_id', '').strip()
        max_depth = int(body.get('max_depth', 1))
        selector = body.get('selector', '').strip() or None
        if not url:
            return jsonify(code=400, msg='URL 不能为空')
        if not dataset_id:
            return jsonify(code=400, msg='知识库 ID 不能为空')
        try:
            # 爬取内容
            text = _import_website(url, max_depth, selector)
            if not text:
                return jsonify(code=400, msg='无法获取网站内容')
            # 创建文档
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'SELECT tenant_id FROM dify_datasets WHERE id = %s', (dataset_id,))
                ds = cur.fetchone()
                if not ds:
                    return jsonify(code=404, msg='知识库不存在')
                tenant_id = ds['tenant_id']
                wc = len(text.replace('\n', '').replace(' ', ''))
                doc_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO dify_documents (id, tenant_id, dataset_id, position, data_source_type, data_source_info,
                                               batch, name, created_from, created_by, indexing_status, word_count)
                    VALUES (%s, %s, %s, 0, 'website_import', %s, %s, %s, 'api', NULL, 'completed', %s)
                """, (doc_id, tenant_id, dataset_id, json.dumps({'url': url}, ensure_ascii=False),
                      'website-import', '网站导入', wc))
                # 分段
                segments = _segment_text(text, '\n', 1024, 50, {})
                if not segments:
                    segments = [text]
                for seg_idx, seg_text in enumerate(segments):
                    seg_wc = len(seg_text.replace('\n', '').replace(' ', ''))
                    seg_tokens = max(1, int(len(seg_text) / 3))
                    cur.execute("""
                        INSERT INTO dify_document_segments (id, tenant_id, dataset_id, document_id, position, content,
                                                           word_count, tokens, hit_count, status, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 'completed', NULL)
                    """, (str(uuid.uuid4()), tenant_id, dataset_id, doc_id, seg_idx, seg_text, seg_wc, seg_tokens))
                db.commit()
                return jsonify(code=200, data={
                    'id': doc_id,
                    'name': '网站导入',
                    'segment_count': len(segments),
                })
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='导入网站失败: %s' % e)
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='导入网站失败: %s' % e)

    @app.route('/api/knowledge/recall-test', methods=['POST'])
    def knowledge_recall_test():
        """
        召回测试：测试知识库检索效果。

        参数:
        - dataset_id: 知识库 ID
        - query: 测试问题
        - top_k: 返回结果数量（默认 5）
        - use_rerank: 是否使用 rerank（默认 false）

        返回:
        - results: 检索结果列表
        """
        _ensure_knowledge_tables()
        body = request.get_json(silent=True) or {}
        dataset_id = body.get('dataset_id', '').strip()
        query = body.get('query', '').strip()
        top_k = int(body.get('top_k', 5))
        use_rerank = body.get('use_rerank', False)
        metadata_filters = body.get('metadata_filters', [])  # [{name, value, operator}]
        if not dataset_id:
            return jsonify(code=400, msg='知识库 ID 不能为空')
        if not query:
            return jsonify(code=400, msg='测试问题不能为空')
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 获取所有分段
                cur.execute(r'''
                    SELECT id, content, word_count, segment_type, parent_id, metadata
                    FROM dify_document_segments
                    WHERE dataset_id = %s AND enabled = 1 AND status = 'completed'
                ''', (dataset_id,))
                rows = cur.fetchall()
            finally:
                db.close()

            # 元数据过滤（2.3）
            if metadata_filters:
                try:
                    from engine.metadata_engine import filter_segments_by_metadata
                    seg_ids = [r['id'] for r in rows]
                    filtered = filter_segments_by_metadata(dataset_id, seg_ids, metadata_filters)
                    filtered_set = set(filtered)
                    rows = [r for r in rows if r['id'] in filtered_set]
                except Exception:
                    pass  # 过滤失败不阻塞检索

            # 关键词匹配打分
            import re
            segments = []
            for r in rows:
                content = r['content'] or ''
                score = _calc_keyword_score(query, content)
                segments.append({
                    'id': r['id'],
                    'content': content,
                    'word_count': r['word_count'] or 0,
                    'segment_type': r['segment_type'] or 'general',
                    'parent_id': r['parent_id'],
                    'metadata': r['metadata'] or '',
                    'score': score,
                })

            # 按分数排序
            segments.sort(key=lambda x: x['score'], reverse=True)

            # 如果使用 rerank
            if use_rerank:
                try:
                    from utils.rerank import rerank_segments
                    segments = rerank_segments(query, segments, top_k=top_k)
                except ImportError:
                    pass  # rerank 模块不存在时跳过

            # 取 top_k
            results = segments[:top_k]

            return jsonify(code=200, data={
                'query': query,
                'total_segments': len(rows),
                'results': results,
            })
        except Exception as e:
            return jsonify(code=500, msg='召回测试失败: %s' % e)

    # ==================== 异步 Embedding API ====================

    @app.route('/api/knowledge/datasets/<dataset_id>/generate-embeddings', methods=['POST'])
    def generate_embeddings_async_view(dataset_id):
        """
        异步触发生成 Embedding

        请求体: {batch_size: 20}
        响应: {code: 202, data: {task_id, status: 'pending'}}
        """
        body = request.json or {}
        batch_size = body.get('batch_size', 20)

        try:
            from tasks.embedding_tasks import generate_embeddings_async
            task = generate_embeddings_async.delay(dataset_id, batch_size)
            return jsonify(code=202, data={
                'task_id': task.id,
                'status': 'pending',
                'message': 'Embedding 生成任务已加入队列',
                'poll_url': f'/api/knowledge/tasks/{task.id}',
            })
        except Exception as e:
            return jsonify(code=500, msg='启动失败: %s' % str(e))

    @app.route('/api/knowledge/generate-all-embeddings', methods=['POST'])
    def generate_all_embeddings_async_view():
        """
        异步生成所有待处理的 Embedding（遍历所有数据集）

        响应: {code: 202, data: {task_id, status: 'pending'}}
        """
        try:
            from tasks.embedding_tasks import generate_all_pending_embeddings
            task = generate_all_pending_embeddings.delay()
            return jsonify(code=202, data={
                'task_id': task.id,
                'status': 'pending',
                'message': '批量 Embedding 生成任务已加入队列',
                'poll_url': f'/api/knowledge/tasks/{task.id}',
            })
        except Exception as e:
            return jsonify(code=500, msg='启动失败: %s' % str(e))

    @app.route('/api/knowledge/tasks/<task_id>', methods=['GET'])
    def get_embedding_task_status(task_id):
        """
        查询 Embedding 任务状态

        响应:
            进行中: {code: 200, data: {task_id, state: 'RUNNING', status: 'running', meta: {...}}}
            成功:   {code: 200, data: {task_id, state: 'SUCCESS', status: 'succeeded', result: {...}}}
            失败:   {code: 200, data: {task_id, state: 'FAILURE', status: 'failed', error: '...'}}
        """
        from tasks.embedding_tasks import get_embedding_task_status
        status = get_embedding_task_status(task_id)
        return jsonify(code=200, data=status)

    @app.route('/api/knowledge/datasets/<dataset_id>/pending-count', methods=['GET'])
    def get_pending_embedding_count(dataset_id):
        """
        获取待处理的 Embedding 数量

        响应: {code: 200, data: {dataset_id, pending_count}}
        """
        from tasks.embedding_tasks import get_pending_embedding_count
        count = get_pending_embedding_count(dataset_id)
        return jsonify(code=200, data={'dataset_id': dataset_id, 'pending_count': count})

    @app.route('/api/knowledge/pending-count-all', methods=['GET'])
    def get_all_pending_embedding_count():
        """
        获取所有数据集的待处理 Embedding 数量

        响应: {code: 200, data: {pending_count, datasets: [{dataset_id, pending_count}]}}
        """
        from tasks.embedding_tasks import get_pending_embedding_count
        total = get_pending_embedding_count(None)

        # 获取各数据集的统计
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                SELECT dataset_id, COUNT(*) as pending_count
                FROM dify_document_segments
                WHERE enabled = 1 AND status = 'completed'
                  AND (embedding IS NULL OR embedding_status = 'pending')
                GROUP BY dataset_id
                ORDER BY pending_count DESC
            ''')
            datasets = [{'dataset_id': r['dataset_id'], 'pending_count': r['pending_count']}
                        for r in cur.fetchall()]
        finally:
            db.close()

        return jsonify(code=200, data={
            'pending_count': total,
            'datasets': datasets,
        })

    # ============================================================
    # 元数据管理 API（2.3: 数据集级别结构化元数据 + 分段绑定 + 检索过滤）
    # ============================================================

    @app.route('/api/knowledge/datasets/<dataset_id>/metadata-fields', methods=['GET'])
    def list_metadata_fields(dataset_id):
        """列出数据集的所有元数据字段"""
        from engine.metadata_engine import list_metadata_fields
        fields = list_metadata_fields(dataset_id)
        return jsonify(code=200, data=fields)

    @app.route('/api/knowledge/datasets/<dataset_id>/metadata-fields', methods=['POST'])
    def create_metadata_field(dataset_id):
        """创建元数据字段"""
        from engine.metadata_engine import create_metadata_field
        body = request.json or {}
        name = (body.get('name') or '').strip()
        if not name:
            return jsonify(code=400, msg='字段名不能为空')
        field_type = body.get('type', 'string')
        description = (body.get('description') or '').strip()
        tenant_id = body.get('tenant_id', '')
        field = create_metadata_field(dataset_id, name, field_type, description, tenant_id)
        if not field:
            return jsonify(code=500, msg='创建失败（可能字段名已存在）')
        return jsonify(code=200, data=field)

    @app.route('/api/knowledge/datasets/<dataset_id>/metadata-fields/<field_id>', methods=['PUT'])
    def update_metadata_field(dataset_id, field_id):
        """更新元数据字段"""
        from engine.metadata_engine import update_metadata_field
        body = request.json or {}
        name = body.get('name')
        field_type = body.get('type')
        description = body.get('description')
        ok = update_metadata_field(field_id, dataset_id, name, field_type, description)
        if not ok:
            return jsonify(code=404, msg='字段不存在或更新失败')
        return jsonify(code=200, msg='更新成功')

    @app.route('/api/knowledge/datasets/<dataset_id>/metadata-fields/<field_id>', methods=['DELETE'])
    def delete_metadata_field(dataset_id, field_id):
        """删除元数据字段（级联删除绑定）"""
        from engine.metadata_engine import delete_metadata_field
        ok = delete_metadata_field(field_id, dataset_id)
        if not ok:
            return jsonify(code=404, msg='字段不存在')
        return jsonify(code=200, msg='删除成功')

    @app.route('/api/knowledge/datasets/<dataset_id>/metadata-bindings', methods=['POST'])
    def bind_segment_metadata(dataset_id):
        """绑定分段与元数据值"""
        from engine.metadata_engine import bind_segment_metadata
        body = request.json or {}
        metadata_id = (body.get('metadata_id') or '').strip()
        segment_id = (body.get('segment_id') or '').strip()
        value = str(body.get('value', '')).strip()
        if not metadata_id or not segment_id:
            return jsonify(code=400, msg='metadata_id 和 segment_id 不能为空')
        if not value:
            return jsonify(code=400, msg='value 不能为空')
        binding = bind_segment_metadata(dataset_id, metadata_id, segment_id, value)
        if not binding:
            return jsonify(code=500, msg='绑定失败（可能字段或分段不存在）')
        return jsonify(code=200, data=binding)

    @app.route('/api/knowledge/datasets/<dataset_id>/metadata-bindings', methods=['DELETE'])
    def unbind_segment_metadata(dataset_id):
        """解绑分段与元数据"""
        from engine.metadata_engine import unbind_segment_metadata
        body = request.json or {}
        metadata_id = (body.get('metadata_id') or '').strip()
        segment_id = (body.get('segment_id') or '').strip()
        if not metadata_id or not segment_id:
            return jsonify(code=400, msg='metadata_id 和 segment_id 不能为空')
        ok = unbind_segment_metadata(dataset_id, metadata_id, segment_id)
        if not ok:
            return jsonify(code=404, msg='绑定不存在')
        return jsonify(code=200, msg='解绑成功')

    @app.route('/api/knowledge/segments/<segment_id>/metadata', methods=['GET'])
    def get_segment_metadata(segment_id):
        """获取分段的所有元数据绑定"""
        from engine.metadata_engine import get_segment_metadata
        metadata = get_segment_metadata(segment_id)
        return jsonify(code=200, data=metadata)

    @app.route('/api/knowledge/datasets/<dataset_id>/segments/<segment_id>/metadata', methods=['PUT'])
    def batch_update_segment_metadata(dataset_id, segment_id):
        """批量更新分段的元数据绑定（覆盖式）"""
        from engine.metadata_engine import (
            list_metadata_fields, bind_segment_metadata, unbind_segment_metadata,
            get_segment_metadata
        )
        body = request.json or {}
        metadata = body.get('metadata') or {}  # {field_name: value}
        if not isinstance(metadata, dict):
            return jsonify(code=400, msg='metadata 必须是对象')

        # 获取数据集的元数据字段映射
        fields = list_metadata_fields(dataset_id)
        name_to_id = {f['name']: f['id'] for f in fields}

        # 获取当前绑定
        current = get_segment_metadata(segment_id)

        updated = 0
        # 删除不在新 metadata 中的绑定
        for name, fid in name_to_id.items():
            if name in current and name not in metadata:
                unbind_segment_metadata(dataset_id, fid, segment_id)

        # 添加/更新绑定
        for name, value in metadata.items():
            if name not in name_to_id:
                continue
            if value is None or str(value).strip() == '':
                # 空值 = 解绑
                if name in current:
                    unbind_segment_metadata(dataset_id, name_to_id[name], segment_id)
                continue
            binding = bind_segment_metadata(dataset_id, name_to_id[name], segment_id, str(value))
            if binding:
                updated += 1

        return jsonify(code=200, data={'updated': updated})

    # ============================================================
    # 关键词索引 API（3.2: jieba 分词 + 混合检索）
    # ============================================================

    @app.route('/api/knowledge/datasets/<dataset_id>/keyword-index', methods=['POST'])
    def build_keyword_index(dataset_id):
        """
        为数据集建立关键词索引。

        请求体: {batch_size: 100}
        响应: {code: 200, data: {dataset_id, indexed_segments, keyword_count}}
        """
        body = request.json or {}
        batch_size = body.get('batch_size', 100)
        try:
            from engine.keyword_engine import build_keyword_index_for_dataset, get_keyword_stats
            n = build_keyword_index_for_dataset(dataset_id, batch_size=batch_size)
            stats = get_keyword_stats(dataset_id)
            return jsonify(code=200, data={
                'dataset_id': dataset_id,
                'indexed_segments': n,
                'keyword_count': stats['keyword_count'],
            })
        except Exception as e:
            return jsonify(code=500, msg='建立关键词索引失败: %s' % str(e))

    @app.route('/api/knowledge/datasets/<dataset_id>/keyword-index', methods=['GET'])
    def get_keyword_index_stats(dataset_id):
        """
        获取数据集关键词索引统计。

        响应: {code: 200, data: {dataset_id, keyword_count, indexed_segments}}
        """
        try:
            from engine.keyword_engine import get_keyword_stats
            stats = get_keyword_stats(dataset_id)
            stats['dataset_id'] = dataset_id
            return jsonify(code=200, data=stats)
        except Exception as e:
            return jsonify(code=500, msg='获取统计失败: %s' % str(e))

    @app.route('/api/knowledge/datasets/<dataset_id>/keyword-search', methods=['POST'])
    def keyword_search_endpoint(dataset_id):
        """
        关键词检索。

        请求体: {query: str, top_k: int}
        响应: {code: 200, data: {results: [{segment_id, score, matched_keywords}]}}
        """
        body = request.json or {}
        query = (body.get('query') or '').strip()
        top_k = int(body.get('top_k', 5))
        if not query:
            return jsonify(code=400, msg='查询不能为空')
        try:
            from engine.keyword_engine import keyword_search
            results = keyword_search(dataset_id, query, top_k=top_k)
            return jsonify(code=200, data={'query': query, 'results': results})
        except Exception as e:
            return jsonify(code=500, msg='关键词检索失败: %s' % str(e))

    @app.route('/api/knowledge/datasets/<dataset_id>/keyword-index/build', methods=['POST'])
    def trigger_build_keyword_index(dataset_id):
        """
        异步触发关键词索引构建。

        响应: {code: 202, data: {task_id, status: 'pending'}}
        """
        try:
            from tasks.embedding_tasks import build_keyword_index
            task = build_keyword_index.delay(dataset_id)
            return jsonify(code=202, data={
                'task_id': task.id,
                'status': 'pending',
                'message': '关键词索引构建任务已加入队列',
                'poll_url': f'/api/knowledge/tasks/{task.id}',
            })
        except Exception as e:
            return jsonify(code=500, msg='启动失败: %s' % str(e))

    @app.route('/api/knowledge/build-all-keyword-index', methods=['POST'])
    def trigger_build_all_keyword_index():
        """
        异步触发所有数据集的关键词索引构建。

        响应: {code: 202, data: {task_id, status: 'pending'}}
        """
        try:
            from tasks.embedding_tasks import build_keyword_index
            task = build_keyword_index.delay(None)
            return jsonify(code=202, data={
                'task_id': task.id,
                'status': 'pending',
                'message': '全量关键词索引构建任务已加入队列',
                'poll_url': f'/api/knowledge/tasks/{task.id}',
            })
        except Exception as e:
            return jsonify(code=500, msg='启动失败: %s' % str(e))

    @app.route('/api/knowledge/datasets/<dataset_id>/hybrid-search', methods=['POST'])
    def hybrid_search_endpoint(dataset_id):
        """
        混合检索（向量 + 关键词加权）。

        请求体: {query: str, top_k: int, vector_weight: float}
        响应: {code: 200, data: {results: [{id, content, score, vector_score, keyword_score, hybrid_score}]}}
        """
        body = request.json or {}
        query = (body.get('query') or '').strip()
        top_k = int(body.get('top_k', 5))
        vector_weight = float(body.get('vector_weight', 0.7))
        if not query:
            return jsonify(code=400, msg='查询不能为空')
        try:
            from engine.keyword_engine import hybrid_search
            from engine.embedding_service import vector_search
            # 先获取向量结果（vector_search 需要 dataset_ids 列表）
            vec_results = vector_search([dataset_id], query, top_k=top_k * 2)
            # 混合检索
            merged = hybrid_search(dataset_id, query, vec_results, top_k=top_k, vector_weight=vector_weight)
            return jsonify(code=200, data={
                'query': query,
                'vector_weight': vector_weight,
                'results': merged,
            })
        except Exception as e:
            return jsonify(code=500, msg='混合检索失败: %s' % str(e))

    # ============================================================
    # 外部知识 API（3.3）
    # ============================================================

    @app.route('/api/knowledge/external-apis', methods=['GET'])
    def list_external_apis():
        """列出所有外部知识 API"""
        try:
            from engine.external_knowledge import list_external_apis as _list
            apis = _list()
            return jsonify(code=200, data=apis)
        except Exception as e:
            return jsonify(code=500, msg='获取列表失败: %s' % str(e))

    @app.route('/api/knowledge/external-apis', methods=['POST'])
    def create_external_api():
        """创建外部知识 API"""
        from engine.external_knowledge import create_external_api as _create
        body = request.json or {}
        name = (body.get('name') or '').strip()
        endpoint_url = (body.get('endpoint_url') or '').strip()
        description = (body.get('description') or '').strip()
        api_key = (body.get('api_key') or '').strip()
        timeout = int(body.get('timeout', 30))
        if not name:
            return jsonify(code=400, msg='API 名称不能为空')
        if not endpoint_url:
            return jsonify(code=400, msg='API 地址不能为空')
        result = _create(name, endpoint_url, description, api_key, timeout)
        if not result:
            return jsonify(code=500, msg='创建失败')
        return jsonify(code=200, data=result)

    @app.route('/api/knowledge/external-apis/<int:api_id>', methods=['GET'])
    def get_external_api(api_id):
        """获取外部知识 API 详情"""
        from engine.external_knowledge import get_external_api as _get
        api = _get(api_id)
        if not api:
            return jsonify(code=404, msg='API 不存在')
        return jsonify(code=200, data=api)

    @app.route('/api/knowledge/external-apis/<int:api_id>', methods=['PUT'])
    def update_external_api(api_id):
        """更新外部知识 API"""
        from engine.external_knowledge import update_external_api as _update
        body = request.json or {}
        ok = _update(
            api_id,
            name=body.get('name'),
            endpoint_url=body.get('endpoint_url'),
            description=body.get('description'),
            api_key=body.get('api_key'),
            timeout=body.get('timeout'),
            status=body.get('status'),
        )
        if not ok:
            return jsonify(code=404, msg='API 不存在或更新失败')
        return jsonify(code=200, msg='更新成功')

    @app.route('/api/knowledge/external-apis/<int:api_id>', methods=['DELETE'])
    def delete_external_api(api_id):
        """删除外部知识 API"""
        from engine.external_knowledge import delete_external_api as _delete
        ok = _delete(api_id)
        if not ok:
            return jsonify(code=404, msg='API 不存在')
        return jsonify(code=200, msg='删除成功')

    @app.route('/api/knowledge/datasets/<dataset_id>/external-bindings', methods=['GET'])
    def get_dataset_external_bindings(dataset_id):
        """获取数据集绑定的外部 API"""
        try:
            from engine.external_knowledge import get_dataset_external_apis
            apis = get_dataset_external_apis(dataset_id)
            return jsonify(code=200, data=apis)
        except Exception as e:
            return jsonify(code=500, msg='获取绑定失败: %s' % str(e))

    @app.route('/api/knowledge/datasets/<dataset_id>/external-bindings', methods=['POST'])
    def bind_external_api_to_dataset(dataset_id):
        """绑定外部 API 到数据集"""
        from engine.external_knowledge import bind_external_api
        body = request.json or {}
        external_api_id = body.get('external_api_id')
        if not external_api_id:
            return jsonify(code=400, msg='external_api_id 不能为空')
        result = bind_external_api(dataset_id, int(external_api_id))
        if not result:
            return jsonify(code=500, msg='绑定失败')
        return jsonify(code=200, data=result)

    @app.route('/api/knowledge/datasets/<dataset_id>/external-bindings/<int:api_id>', methods=['DELETE'])
    def unbind_external_api_from_dataset(dataset_id, api_id):
        """解绑外部 API"""
        from engine.external_knowledge import unbind_external_api
        ok = unbind_external_api(dataset_id, api_id)
        if not ok:
            return jsonify(code=404, msg='绑定不存在')
        return jsonify(code=200, msg='解绑成功')

    @app.route('/api/knowledge/external-retrieve', methods=['POST'])
    def external_retrieve():
        """
        测试外部知识 API 检索。

        请求体: {dataset_id: str, query: str, top_k: int}
        响应: {code: 200, data: {results: [...], errors: [...]}}
        """
        body = request.json or {}
        dataset_id = (body.get('dataset_id') or '').strip()
        query = (body.get('query') or '').strip()
        top_k = int(body.get('top_k', 5))
        if not dataset_id:
            return jsonify(code=400, msg='dataset_id 不能为空')
        if not query:
            return jsonify(code=400, msg='query 不能为空')
        try:
            from engine.external_knowledge import retrieve_external_knowledge
            results, errors = retrieve_external_knowledge([dataset_id], query, top_k=top_k)
            return jsonify(code=200, data={
                'results': results,
                'errors': errors,
            })
        except Exception as e:
            return jsonify(code=500, msg='外部检索失败: %s' % str(e))


def _calc_keyword_score(query, content):
    """
    计算关键词匹配分数。

    参数:
    - query: 查询文本
    - content: 分段内容

    返回: 匹配分数（0-1）
    """
    import re
    if not query or not content:
        return 0.0

    query_lower = query.lower()
    content_lower = content.lower()

    # 完全匹配
    if query_lower in content_lower:
        return 1.0

    # 英文单词匹配
    words = re.findall(r'[a-zA-Z]+', query_lower)
    if words:
        matched = sum(1 for w in words if w in content_lower)
        return matched / len(words) * 0.8

    # 中文 2-gram 匹配
    if len(query_lower) >= 2:
        bigrams = [query_lower[i:i + 2] for i in range(len(query_lower) - 1)]
        matched = sum(1 for b in bigrams if b in content_lower)
        return matched / len(bigrams) * 0.6

    return 0.0
