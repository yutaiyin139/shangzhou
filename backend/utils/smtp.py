# -*- coding: utf-8 -*-
"""
SMTP 邮件发送工具

功能:
    - send_reset_email(): 发送密码重置邮件
    - test_smtp_connection(): 测试 SMTP 连接
    - send_email(): 通用邮件发送
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def _build_message(to_email, subject, html_content, from_email=None):
    """构建邮件消息"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email or '熵舟智能体工作台 <noreply@shangzhou.local>'
    msg['To'] = to_email
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    return msg


def send_email(to_email, subject, html_content, smtp_config):
    """
    发送邮件

    参数:
        to_email: 收件人邮箱
        subject: 邮件主题
        html_content: HTML 内容
        smtp_config: { host, port, user, password, from_email, use_tls }

    返回:
        bool: 是否发送成功
    """
    host = smtp_config.get('host', '')
    port = int(smtp_config.get('port', 587))
    user = smtp_config.get('user', '')
    password = smtp_config.get('password', '')
    from_email = smtp_config.get('from_email') or user
    use_tls = smtp_config.get('use_tls', True)

    if not host or not user:
        raise ValueError('SMTP 未配置：缺少 host 或 user')

    msg = _build_message(to_email, subject, html_content, from_email)

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        server.login(user, password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        raise Exception(f'SMTP 发送失败: {str(e)}')


def send_reset_email(to_email, username, reset_token):
    """
    发送密码重置邮件

    参数:
        to_email: 收件人邮箱
        username: 用户名
        reset_token: 重置令牌
    """
    from config import get_db

    # 读取 SMTP 配置
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r"SELECT key_name, key_value FROM system_settings WHERE key_name LIKE 'smtp_%'")
        rows = cur.fetchall()
        config = {row['key_name']: row['key_value'] for row in rows}
    finally:
        db.close()

    if not config.get('smtp_host'):
        raise ValueError('SMTP 未配置，无法发送重置邮件')

    smtp_config = {
        'host': config.get('smtp_host', ''),
        'port': int(config.get('smtp_port', 587)),
        'user': config.get('smtp_user', ''),
        'password': config.get('smtp_password', ''),
        'from_email': config.get('smtp_from', config.get('smtp_user', '')),
        'use_tls': config.get('smtp_use_tls', '1') == '1',
    }

    reset_url = f'http://localhost:3000/#/reset-password?token={reset_token}'
    html_content = f'''
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #1D2129; margin-bottom: 20px;">熵舟·智能体工作台 — 密码重置</h2>
        <p style="color: #4E5969; font-size: 14px;">您好 {username}，</p>
        <p style="color: #4E5969; font-size: 14px;">我们收到了您的密码重置请求。请点击下方链接重置密码：</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="display: inline-block; padding: 12px 32px; background: linear-gradient(90deg, #2E63F0, #4A86F8); color: #fff; text-decoration: none; border-radius: 8px; font-size: 14px;">重置密码</a>
        </div>
        <p style="color: #86909C; font-size: 12px;">此链接 1 小时内有效。如非本人操作，请忽略此邮件。</p>
        <p style="color: #86909C; font-size: 12px;">如果按钮无法点击，请复制以下链接到浏览器：<br>{reset_url}</p>
        <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;">
        <p style="color: #C9CDD4; font-size: 11px;">熵舟·智能体工作台 — 链接无限可能，开启智能未来</p>
    </div>
    '''
    send_email(to_email, '熵舟·智能体工作台 — 密码重置', html_content, smtp_config)


def test_smtp_connection(config):
    """
    测试 SMTP 连接

    参数:
        config: { smtp_host, smtp_port, smtp_user, smtp_password, smtp_from, to_email }
    """
    smtp_config = {
        'host': config.get('smtp_host', ''),
        'port': int(config.get('smtp_port', 587)),
        'user': config.get('smtp_user', ''),
        'password': config.get('smtp_password', ''),
        'from_email': config.get('smtp_from', config.get('smtp_user', '')),
        'use_tls': str(config.get('use_tls', '1')) == '1',
    }

    to_email = config.get('to_email') or smtp_config['from_email']
    html_content = f'''
    <div style="font-family: sans-serif; padding: 20px;">
        <h2>SMTP 测试成功</h2>
        <p>这是一封测试邮件，发送时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p>如果您的收到此邮件，说明 SMTP 配置正确。</p>
    </div>
    '''
    send_email(to_email, '熵舟·SMTP 测试邮件', html_content, smtp_config)
