# -*- coding: utf-8 -*-
"""
Human Input 邮件投递引擎 —— 工作流暂停时通过邮件发送表单链接

职责:
    1. SMTP 配置管理（通过 system_settings 表）
    2. 当 Human Input 节点暂停工作流时，发送包含表单链接的邮件
    3. 记录投递状态

使用方式:
    1. 在系统设置中配置 SMTP
    2. Human Input 节点配置 email 字段（接收邮箱）
    3. 工作流暂停时自动发送邮件
    4. 用户点击邮件中的链接，打开表单页面提交输入
"""
import json
import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional, List

from config import get_db
from models.tables import SYSTEM_SETTINGS_TABLE_SQL, HUMAN_INPUT_FORM_DELIVERIES_TABLE_SQL


def ensure_tables():
    """确保相关表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(SYSTEM_SETTINGS_TABLE_SQL)
        cur.execute(HUMAN_INPUT_FORM_DELIVERIES_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


# ============================================================
# SMTP 配置管理
# ============================================================

def get_smtp_config() -> Optional[Dict]:
    """获取 SMTP 配置"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT `value` FROM system_settings WHERE `key` = 'smtp_config'")
        row = cur.fetchone()
        if not row or not row['value']:
            return None
        return json.loads(row['value'])
    except Exception:
        return None
    finally:
        db.close()


def set_smtp_config(config: Dict) -> bool:
    """设置 SMTP 配置"""
    ensure_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO system_settings (`key`, `value`, description)
            VALUES ('smtp_config', %s, 'SMTP 邮件服务器配置')
            ON DUPLICATE KEY UPDATE `value` = VALUES(`value`), updated_at = NOW()
        """, (json.dumps(config, ensure_ascii=False),))
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def test_smtp_connection() -> tuple:
    """
    测试 SMTP 连接。

    返回:
        (是否成功, 错误信息)
    """
    cfg = get_smtp_config()
    if not cfg:
        return False, '未配置 SMTP'

    host = cfg.get('host', '')
    port = int(cfg.get('port', 587))
    username = cfg.get('username', '')
    password = cfg.get('password', '')
    use_tls = cfg.get('use_tls', True)

    if not host:
        return False, 'SMTP 服务器地址不能为空'

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=10)

        if username and password:
            server.login(username, password)

        server.quit()
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, 'SMTP 认证失败（用户名或密码错误）'
    except smtplib.SMTPConnectError:
        return False, f'无法连接到 SMTP 服务器 {host}:{port}'
    except Exception as e:
        return False, f'SMTP 连接失败: {str(e)[:200]}'


# ============================================================
# 邮件发送
# ============================================================

def send_email(to: str, subject: str, html_body: str, text_body: str = '') -> tuple:
    """
    发送邮件。

    参数:
        to: 接收邮箱
        subject: 主题
        html_body: HTML 内容
        text_body: 纯文本内容（可选）

    返回:
        (是否成功, 错误信息)
    """
    cfg = get_smtp_config()
    if not cfg:
        return False, '未配置 SMTP'

    host = cfg.get('host', '')
    port = int(cfg.get('port', 587))
    username = cfg.get('username', '')
    password = cfg.get('password', '')
    use_tls = cfg.get('use_tls', True)
    from_email = cfg.get('from_email', username)
    from_name = cfg.get('from_name', '熵舟智能体工作台')

    if not host:
        return False, 'SMTP 服务器地址不能为空'

    # 构建邮件
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'{from_name} <{from_email}>'
    msg['To'] = to

    if text_body:
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=30)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=30)

        if username and password:
            server.login(username, password)

        server.sendmail(from_email, [to], msg.as_string())
        server.quit()
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, 'SMTP 认证失败'
    except Exception as e:
        return False, f'发送失败: {str(e)[:200]}'


# ============================================================
# Human Input 邮件投递
# ============================================================

def build_form_url(app_id: str, run_id: str) -> str:
    """构建表单 URL"""
    # 使用前端路由
    return f'/human-input-form?app_id={app_id}&run_id={run_id}'


def build_email_html(app_name: str, node_message: str, form_url: str, fields: List[Dict]) -> str:
    """构建邮件 HTML"""
    fields_html = ''
    if fields:
        fields_html = '<h3>需要填写的字段：</h3><ul>'
        for f in fields:
            required = '（必填）' if f.get('required') else ''
            fields_html += f"<li><strong>{f.get('label', f.get('name', ''))}</strong>{required}</li>"
        fields_html += '</ul>'

    return f'''
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #f8f9fa; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
    <h1 style="color: #1a73e8; margin-top: 0;">⏸ 工作流等待您的输入</h1>
    <p style="font-size: 16px; color: #555;">「{app_name}」需要您提供信息才能继续执行。</p>
  </div>

  <div style="background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
    <h2 style="margin-top: 0; color: #333;">📋 提示信息</h2>
    <p style="color: #666;">{node_message}</p>
    {fields_html}
  </div>

  <div style="text-align: center; margin: 30px 0;">
    <a href="{form_url}" style="background: #1a73e8; color: white; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">
      打开表单填写
    </a>
  </div>

  <p style="color: #999; font-size: 12px; text-align: center;">
    如果您无法点击按钮，请复制以下链接到浏览器：<br>
    <a href="{form_url}" style="color: #1a73e8;">{form_url}</a>
  </p>

  <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">

  <p style="color: #999; font-size: 12px; text-align: center;">
    此邮件由熵舟·智能体工作台自动发送，请勿回复。
  </p>
</body>
</html>
'''


def create_delivery(run_id: str, app_id: str, node_id: str, email: str,
                    subject: str, form_url: str) -> Optional[int]:
    """创建投递记录"""
    ensure_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO human_input_form_deliveries
            (run_id, app_id, node_id, email, subject, form_url, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """, (run_id, app_id, node_id, email, subject, form_url))
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


def update_delivery_status(delivery_id: int, status: str, error: str = None):
    """更新投递状态"""
    db = get_db()
    try:
        cur = db.cursor()
        if status == 'sent':
            cur.execute("""
                UPDATE human_input_form_deliveries
                SET status = %s, delivered_at = NOW(), error = NULL
                WHERE id = %s
            """, (status, delivery_id))
        else:
            cur.execute("""
                UPDATE human_input_form_deliveries
                SET status = %s, error = %s
                WHERE id = %s
            """, (status, error, delivery_id))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def mark_delivery_submitted(run_id: str):
    """标记投递为已提交"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            UPDATE human_input_form_deliveries
            SET status = 'submitted', submitted_at = NOW()
            WHERE run_id = %s AND status IN ('sent', 'opened')
        """, (run_id,))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def deliver_human_input_email(app_id: str, run_id: str, node_id: str,
                              email: str, app_name: str,
                              node_message: str, fields: List[Dict]) -> tuple:
    """
    投递 Human Input 表单邮件。

    参数:
        app_id: 应用 ID
        run_id: 运行 ID
        node_id: 节点 ID
        email: 接收邮箱
        app_name: 应用名称
        node_message: 节点提示信息
        fields: 表单字段列表

    返回:
        (是否成功, 错误信息, delivery_id)
    """
    # 检查 SMTP 配置
    if not get_smtp_config():
        return False, '未配置 SMTP，无法发送邮件', None

    # 构建表单 URL 和邮件内容
    form_url = build_form_url(app_id, run_id)
    subject = f'【{app_name}】需要您的输入'
    html_body = build_email_html(app_name, node_message, form_url, fields)
    text_body = f'{app_name} 需要您的输入：\n\n{node_message}\n\n请访问：{form_url}'

    # 创建投递记录
    delivery_id = create_delivery(run_id, app_id, node_id, email, subject, form_url)
    if not delivery_id:
        return False, '创建投递记录失败', None

    # 发送邮件
    success, error = send_email(email, subject, html_body, text_body)
    if success:
        update_delivery_status(delivery_id, 'sent')
        return True, None, delivery_id
    else:
        update_delivery_status(delivery_id, 'failed', error)
        return False, error, delivery_id


def get_deliveries(run_id: str = None, app_id: str = None,
                   status: str = None, limit: int = 50) -> List[Dict]:
    """获取投递记录"""
    ensure_tables()
    db = get_db()
    try:
        cur = db.cursor()
        conditions = []
        params = []
        if run_id:
            conditions.append('run_id = %s')
            params.append(run_id)
        if app_id:
            conditions.append('app_id = %s')
            params.append(app_id)
        if status:
            conditions.append('status = %s')
            params.append(status)

        where = ' AND '.join(conditions) if conditions else '1=1'
        cur.execute(f"""
            SELECT * FROM human_input_form_deliveries
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT %s
        """, params + [limit])
        rows = cur.fetchall()
        return [{
            'id': r['id'],
            'run_id': r['run_id'],
            'app_id': r['app_id'],
            'node_id': r['node_id'],
            'email': r['email'],
            'subject': r['subject'] or '',
            'form_url': r['form_url'] or '',
            'status': r['status'] or 'pending',
            'error': r['error'] or '',
            'delivered_at': r['delivered_at'].isoformat() if r['delivered_at'] else None,
            'submitted_at': r['submitted_at'].isoformat() if r['submitted_at'] else None,
            'created_at': r['created_at'].isoformat() if r['created_at'] else None,
        } for r in rows]
    finally:
        db.close()


# ============================================================
# 多渠道投递：Slack / 飞书 (Feishu/Lark) Webhook
# ============================================================

def send_slack_webhook(webhook_url: str, app_name: str, node_message: str,
                       form_url: str, fields: List[Dict]) -> tuple:
    """
    发送 Slack Incoming Webhook 消息。

    参数:
        webhook_url: Slack Incoming Webhook URL
        app_name: 应用名称
        node_message: 节点提示信息
        form_url: 表单链接
        fields: 表单字段列表

    返回: (是否成功, 错误信息)
    """
    if not webhook_url:
        return False, '未提供 Slack Webhook URL'

    # 构建 Slack Block Kit 消息
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"⏸ {app_name} - 需要您的输入"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": node_message}
        }
    ]

    # 字段列表
    if fields:
        field_text = "*需要填写的字段：*\n"
        for f in fields:
            required = ' • *必填*' if f.get('required') else ''
            field_text += f"• {f.get('label', f.get('name', ''))}{required}\n"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": field_text}
        })

    # 按钮
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "📝 打开表单填写"},
                "url": form_url,
                "style": "primary"
            }
        ]
    })

    payload = json.dumps({
        "text": f"[{app_name}] 工作流等待您的输入",
        "blocks": blocks,
    }).encode('utf-8')

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = resp.read().decode('utf-8')
            # Slack 返回 "ok" 表示成功
            if result.strip().lower() == 'ok':
                return True, None
            return True, None  # 有些 webhook 代理不返回 ok
    except Exception as e:
        return False, f'Slack Webhook 发送失败: {str(e)[:200]}'


def send_feishu_webhook(webhook_url: str, app_name: str, node_message: str,
                        form_url: str, fields: List[Dict]) -> tuple:
    """
    发送飞书 (Lark) Webhook 消息。

    支持飞书自定义机器人 Webhook 和飞书开放平台标准格式。

    返回: (是否成功, 错误信息)
    """
    if not webhook_url:
        return False, '未提供飞书 Webhook URL'

    # 构建富文本内容
    content_text = f"工作流等待您的输入\n\n{node_message}\n"
    if fields:
        content_text += "\n需要填写的字段：\n"
        for f in fields:
            required = '（必填）' if f.get('required') else ''
            content_text += f"• {f.get('label', f.get('name', ''))}{required}\n"
    content_text += f"\n👉 点击链接填写表单：{form_url}"

    # 飞书 post 消息格式
    payload = json.dumps({
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"content": f"⏸ {app_name} - 需要您的输入", "tag": "plain_text"},
                "template": "orange"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"content": node_message, "tag": "lark_md"}
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"content": "📝 打开表单填写", "tag": "plain_text"},
                            "url": form_url,
                            "type": "primary"
                        }
                    ]
                }
            ]
        }
    }).encode('utf-8')

    # 如果 webhook 是简化版（纯文本），降级为 text 格式
    if '/hook/' in webhook_url or 'webhook' in webhook_url.lower():
        # 尝试 text 格式（兼容大多数飞书 webhook）
        payload = json.dumps({
            "msg_type": "text",
            "content": {"text": content_text}
        }).encode('utf-8')

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = resp.read().decode('utf-8')
            # 飞书返回 {"StatusCode":0,"StatusMessage":"success"} 或 {"code":0}
            try:
                resp_json = json.loads(result)
                if resp_json.get('code') == 0 or resp_json.get('StatusCode') == 0:
                    return True, None
            except Exception:
                pass
            return True, None
    except Exception as e:
        return False, f'飞书 Webhook 发送失败: {str(e)[:200]}'


def deliver_human_input_multi_channel(app_id: str, run_id: str, node_id: str,
                                     channels: List[Dict], app_name: str,
                                     node_message: str, fields: List[Dict]) -> Dict[str, tuple]:
    """
    多渠道投递 Human Input 表单。

    参数:
        channels: 渠道配置列表
            [{type: 'email', target: 'user@example.com'},
             {type: 'slack', target: 'https://hooks.slack.com/...'},
             {type: 'feishu', target: 'https://open.feishu.cn/.../webhook/...'}]

    返回:
        {channel_type: (success, error)}
    """
    form_url = build_form_url(app_id, run_id)
    results = {}

    for ch in channels:
        ch_type = ch.get('type', 'email')
        target = ch.get('target', ch.get('email', ''))

        if not target:
            results[ch_type] = (False, '未提供目标地址')
            continue

        if ch_type == 'email':
            # 邮件投递
            if not get_smtp_config():
                results[ch_type] = (False, '未配置 SMTP')
                continue
            subject = f'【{app_name}】需要您的输入'
            html_body = build_email_html(app_name, node_message, form_url, fields)
            text_body = f'{app_name} 需要您的输入：\n\n{node_message}\n\n请访问：{form_url}'
            delivery_id = create_delivery(run_id, app_id, node_id, target, subject, form_url)
            success, error = send_email(target, subject, html_body, text_body)
            if delivery_id:
                update_delivery_status(delivery_id, 'sent' if success else 'failed', error)
            results[ch_type] = (success, error)

        elif ch_type == 'slack':
            success, error = send_slack_webhook(target, app_name, node_message, form_url, fields)
            results[ch_type] = (success, error)

        elif ch_type == 'feishu':
            success, error = send_feishu_webhook(target, app_name, node_message, form_url, fields)
            results[ch_type] = (success, error)

        else:
            results[ch_type] = (False, f'未知渠道类型: {ch_type}')

    return results
