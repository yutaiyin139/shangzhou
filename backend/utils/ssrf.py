# -*- coding: utf-8 -*-
"""
SSRF 防护模块 —— 防止服务端请求伪造攻击

功能：
1. URL 安全验证（协议、主机、端口）
2. IP 地址过滤（阻止内网/私有/保留地址）
3. DNS 重绑定防护
4. 可选的域名白名单/黑名单

安全设计：
- 仅允许 http/https 协议
- 阻止访问私有网络（10.x, 192.168.x, 172.16-31.x）
- 阻止访问本地地址（127.x, ::1, localhost）
- 阻止访问链路本地地址（169.254.x, fe80::）
- 阻止访问元数据服务（169.254.169.254）

依赖：无额外依赖（仅使用 Python 标准库）
"""

import re
import socket
import ipaddress
from urllib.parse import urlparse

# 危险的协议方案（可能导致 SSRF 或本地文件读取）
BLOCKED_SCHEMES = {'file', 'gopher', 'dict', 'ftp', 'telnet', 'ldap', 'ldaps', 'tftp'}

# 允许的协议方案
ALLOWED_SCHEMES = {'http', 'https'}

# 危险的主机名模式
BLOCKED_HOST_PATTERNS = [
    r'^localhost$',
    r'^localhost\.',
    r'^127\.',
    r'^0\.0\.0\.0$',
    r'^10\.',
    r'^172\.(1[6-9]|2[0-9]|3[01])\.',
    r'^192\.168\.',
    r'^169\.254\.',
    r'^\[?::1\]?$',
    r'^\[?fc00:',
    r'^\[?fe80:',
    r'^\[?fd00:',
]

# 危险的端口
BLOCKED_PORTS = {
    22, 23, 25, 53, 110, 143, 3306, 5432, 6379, 27017,  # 常见服务端口
    9200, 11211, 5000, 8080, 8443,  # 应用服务端口（可选阻止）
}

# 元数据服务 IP
METADATA_IPS = {'169.254.169.254', '100.100.100.200', '169.254.169.255'}


def is_safe_url(url, allow_private=False, allowed_domains=None, blocked_domains=None):
    """
    检查 URL 是否安全（防止 SSRF 攻击）

    参数:
        url: 要检查的 URL
        allow_private: 是否允许私有网络地址（默认 False）
        allowed_domains: 允许的域名列表（None = 不限制）
        blocked_domains: 禁止的域名列表（None = 不限制）

    返回:
        bool: URL 是否安全

    示例:
        >>> is_safe_url('https://www.example.com/api')
        True
        >>> is_safe_url('http://127.0.0.1:6379/')
        False
        >>> is_safe_url('http://169.254.169.254/latest/meta-data/')
        False
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    # 解析 URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # 检查协议
    scheme = parsed.scheme.lower()
    if scheme in BLOCKED_SCHEMES:
        return False
    if scheme not in ALLOWED_SCHEMES:
        return False

    # 提取主机名
    hostname = parsed.hostname
    if not hostname:
        return False

    hostname_lower = hostname.lower()

    # 检查域名白名单/黑名单
    if allowed_domains:
        if not any(hostname_lower == d or hostname_lower.endswith('.' + d) for d in allowed_domains):
            return False
    if blocked_domains:
        if any(hostname_lower == d or hostname_lower.endswith('.' + d) for d in blocked_domains):
            return False

    # 检查主机名模式
    for pattern in BLOCKED_HOST_PATTERNS:
        if re.match(pattern, hostname_lower, re.IGNORECASE):
            return False

    # 检查端口
    port = parsed.port
    if port and port in BLOCKED_PORTS:
        return False

    # 如果允许私有网络，跳过 IP 检查
    if allow_private:
        return True

    # 解析 IP 地址并检查
    try:
        # 首先尝试直接解析为 IP
        addr = ipaddress.ip_address(hostname)
        if _is_blocked_ip(addr):
            return False
    except ValueError:
        # 是域名，需要 DNS 解析
        try:
            # 获取所有 IP 地址
            addrinfos = socket.getaddrinfo(
                hostname,
                port or (443 if scheme == 'https' else 80)
            )
            for addrinfo in addrinfos:
                ip_str = addrinfo[4][0]
                addr = ipaddress.ip_address(ip_str)
                if _is_blocked_ip(addr):
                    return False
        except socket.gaierror:
            # DNS 解析失败，拒绝访问
            return False
        except Exception:
            return False

    return True


def _is_blocked_ip(addr):
    """
    检查 IP 地址是否被阻止

    参数:
        addr: ipaddress.IPv4Address 或 ipaddress.IPv6Address

    返回:
        bool: 是否被阻止
    """
    if not isinstance(addr, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
        try:
            addr = ipaddress.ip_address(addr)
        except Exception:
            return True

    # 检查特殊属性
    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
        return True
    if addr.is_multicast:
        return True

    # 检查元数据服务
    if str(addr) in METADATA_IPS:
        return True

    # 检查未指定地址
    if addr == ipaddress.ip_address('0.0.0.0') or addr == ipaddress.ip_address('::'):
        return True

    return False


def validate_url_or_raise(url, error_message=None):
    """
    验证 URL 不安全时抛出异常

    参数:
        url: 要检查的 URL
        error_message: 自定义错误消息

    Raises:
        ValueError: URL 不安全时
    """
    if not is_safe_url(url):
        if error_message:
            raise ValueError(error_message)
        raise ValueError(f'URL 被安全策略禁止: {url}')


def get_safe_url(url, default=None):
    """
    获取安全的 URL，不安全时返回默认值

    参数:
        url: 要检查的 URL
        default: 不安全时的返回值

    返回:
        str or None: 安全的 URL 或默认值
    """
    if is_safe_url(url):
        return url
    return default


if __name__ == '__main__':
    # 测试用例
    test_urls = [
        ('https://www.example.com/api', True),
        ('http://www.google.com/search?q=test', True),
        ('http://127.0.0.1:6379/', False),
        ('http://localhost:5000/api', False),
        ('http://10.0.0.1/', False),
        ('http://192.168.1.1/', False),
        ('http://172.16.0.1/', False),
        ('http://169.254.169.254/latest/meta-data/', False),
        ('file:///etc/passwd', False),
        ('gopher://localhost:70/', False),
        ('dict://localhost:2628/', False),
        ('ftp://localhost/', False),
        ('http://[::1]:80/', False),
        ('http://[fc00::1]/', False),
        ('http://[fe80::1]/', False),
    ]

    print("SSRF 防护测试:")
    for url, expected in test_urls:
        result = is_safe_url(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url}: {'允许' if result else '阻止'} (期望: {'允许' if expected else '阻止'})")
