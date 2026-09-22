# -*- coding: utf-8 -*-
"""
文档提取节点执行模块

负责从上传的文档中提取文本内容，支持：
- 纯文本文件（txt, md, csv, json, xml, html, htm）
- PDF 文件（需要 PyPDF2 库）
- Word 文档（docx，需要 python-docx 库）
- 文件数组批量提取
"""


def _resolve_selector(context, selector):
    """根据选择器路径从上下文中获取变量值"""
    if not selector:
        return None
    if isinstance(selector, str):
        selector = [selector]

    value = context
    for key in selector:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
        if value is None:
            return None
    return value


def _node_document_extractor(data, context, model_cfg=None):
    """
    Document Extractor 节点 —— 从上传的文档中提取文本内容。

    节点数据结构:
    - variable_selector: 文件变量选择器 ["node_id", "variable"]
    - is_array_file: 是否为文件数组

    返回:
    - text: 提取的文本内容
    """
    variable_selector = data.get('variable_selector', [])
    is_array_file = data.get('is_array_file', False)

    # 从上下文中获取文件
    files = _resolve_selector(context, variable_selector) if variable_selector else None

    if not files:
        return {'text': ''}

    # 确保是列表
    if not isinstance(files, list):
        files = [files]

    extracted_texts = []
    for f in files:
        text = _extract_text_from_file(f)
        if text:
            extracted_texts.append(text)

    result = '\n\n'.join(extracted_texts)
    return {'text': result}


def _extract_text_from_file(file_info):
    """从文件中提取文本"""
    if isinstance(file_info, str):
        # 如果是字符串，直接返回
        return file_info

    if not isinstance(file_info, dict):
        return ''

    # 如果已经有提取的文本
    if 'text' in file_info:
        return file_info['text']

    # 如果有文件路径，尝试读取
    file_path = file_info.get('path', '') or file_info.get('url', '')
    if not file_path:
        return ''

    # 根据文件扩展名选择提取方式
    ext = file_info.get('extension', '').lower()
    if not ext:
        # 从路径获取扩展名
        ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''

    try:
        if ext in ('txt', 'md', 'csv', 'json', 'xml', 'html', 'htm'):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as fh:
                return fh.read()
        elif ext == 'pdf':
            return _extract_pdf_text(file_path)
        elif ext in ('doc', 'docx'):
            return _extract_docx_text(file_path)
        else:
            # 尝试作为文本读取
            with open(file_path, 'r', encoding='utf-8', errors='replace') as fh:
                return fh.read()
    except Exception as e:
        return f'[文件读取错误: {str(e)}]'


def _extract_pdf_text(file_path):
    """从 PDF 提取文本"""
    try:
        import PyPDF2
        text = ''
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + '\n'
        return text
    except ImportError:
        return '[PDF 提取需要 PyPDF2 库]'
    except Exception as e:
        return f'[PDF 提取错误: {str(e)}]'


def _extract_docx_text(file_path):
    """从 DOCX 提取文本"""
    try:
        import docx
        doc = docx.Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    except ImportError:
        return '[DOCX 提取需要 python-docx 库]'
    except Exception as e:
        return f'[DOCX 提取错误: {str(e)}]'
