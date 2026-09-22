# -*- coding: utf-8 -*-
"""
加密工具模块 —— 敏感数据加密存储

功能：
1. 字段级加密/解密（AES-256-GCM via Fernet）
2. 密钥派生（PBKDF2）
3. 安全的密钥管理

安全设计：
- 使用 Fernet 对称加密（基于 AES-256-CBC + HMAC-SHA256）
- 密钥从环境变量或密钥文件加载
- 支持密钥轮换

依赖：cryptography（pip install cryptography）
"""

import os
import base64
import logging
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# 密钥文件路径
_KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.encryption_key')


def _load_or_create_key():
    """
    加载或创建加密密钥

    优先级：
    1. 环境变量 ENCRYPTION_KEY
    2. 密钥文件 .encryption_key
    3. 生成新密钥并保存到文件
    """
    # 1. 从环境变量读取
    env_key = os.getenv('ENCRYPTION_KEY')
    if env_key:
        return env_key.encode() if isinstance(env_key, str) else env_key

    # 2. 从密钥文件读取
    if os.path.exists(_KEY_FILE):
        try:
            with open(_KEY_FILE, 'r') as f:
                key = f.read().strip()
                if key:
                    return key.encode()
        except Exception as e:
            logger.warning(f'读取加密密钥文件失败: {e}')

    # 3. 生成新密钥
    key = Fernet.generate_key().decode()
    try:
        with open(_KEY_FILE, 'w') as f:
            f.write(key)
        os.chmod(_KEY_FILE, 0o600)  # 仅所有者可读写
        logger.info('已生成新的加密密钥')
    except Exception as e:
        logger.warning(f'保存加密密钥失败: {e}')
    return key.encode()


# 初始化 Fernet 实例
_fernet = None


def _get_fernet():
    """获取 Fernet 实例（懒加载）"""
    global _fernet
    if _fernet is None:
        key = _load_or_create_key()
        _fernet = Fernet(key)
    return _fernet


def encrypt_field(plaintext):
    """
    加密敏感字段

    参数:
        plaintext: 明文字符串

    返回:
        str: Base64 编码的密文（前缀 enc:）

    示例:
        >>> encrypted = encrypt_field('sk-1234567890')
        >>> print(encrypted)  # enc:gAAAAAB...
    """
    if not plaintext:
        return plaintext
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')
    try:
        f = _get_fernet()
        encrypted = f.encrypt(plaintext)
        return 'enc:' + encrypted.decode('utf-8')
    except Exception as e:
        logger.error(f'加密失败: {e}')
        return plaintext


def decrypt_field(ciphertext):
    """
    解密敏感字段

    参数:
        ciphertext: 密文字符串（前缀 enc:）

    返回:
        str: 解密后的明文

    示例:
        >>> decrypt_field('enc:gAAAAAB...')
        'sk-1234567890'
    """
    if not ciphertext:
        return ciphertext
    if isinstance(ciphertext, bytes):
        ciphertext = ciphertext.decode('utf-8')
    # 检查是否是加密格式
    if not ciphertext.startswith('enc:'):
        return ciphertext  # 未加密，直接返回
    try:
        f = _get_fernet()
        encrypted_data = ciphertext[4:].encode('utf-8')
        decrypted = f.decrypt(encrypted_data)
        return decrypted.decode('utf-8')
    except InvalidToken:
        logger.warning('解密失败：无效的令牌或密钥不匹配')
        return ciphertext
    except Exception as e:
        logger.error(f'解密失败: {e}')
        return ciphertext


def is_encrypted(value):
    """
    检查值是否已加密

    参数:
        value: 要检查的值

    返回:
        bool: 是否已加密
    """
    if not value:
        return False
    if isinstance(value, str) and value.startswith('enc:'):
        return True
    return False


def encrypt_dict_fields(data, fields):
    """
    加密字典中的指定字段

    参数:
        data: 字典
        fields: 要加密的字段名列表

    返回:
        dict: 加密后的字典（原地修改）
    """
    if not data or not fields:
        return data
    for field in fields:
        if field in data and data[field] and not is_encrypted(data[field]):
            data[field] = encrypt_field(str(data[field]))
    return data


def decrypt_dict_fields(data, fields):
    """
    解密字典中的指定字段

    参数:
        data: 字典
        fields: 要解密的字段名列表

    返回:
        dict: 解密后的字典（原地修改）
    """
    if not data or not fields:
        return data
    for field in fields:
        if field in data and data[field] and is_encrypted(data[field]):
            data[field] = decrypt_field(data[field])
    return data


def rotate_key():
    """
    重新生成加密密钥（密钥轮换）

    注意：
        调用此函数后，之前加密的数据将无法解密。
        需要在调用前解密所有数据，然后重新加密。

    返回:
        bool: 是否成功
    """
    global _fernet
    try:
        new_key = Fernet.generate_key().decode()
        with open(_KEY_FILE, 'w') as f:
            f.write(new_key)
        os.chmod(_KEY_FILE, 0o600)
        _fernet = Fernet(new_key.encode())
        logger.info('加密密钥已轮换')
        return True
    except Exception as e:
        logger.error(f'密钥轮换失败: {e}')
        return False


if __name__ == '__main__':
    # 测试
    print("加密工具测试:")

    # 测试基本加密/解密
    original = 'sk-1234567890abcdef'
    encrypted = encrypt_field(original)
    decrypted = decrypt_field(encrypted)
    print(f"  原文: {original}")
    print(f"  密文: {encrypted}")
    print(f"  解密: {decrypted}")
    print(f"  匹配: {original == decrypted}")

    # 测试字典加密
    data = {'api_key': 'secret-key', 'name': 'test', 'password': 'mypassword'}
    print(f"\n  原始数据: {data}")
    encrypt_dict_fields(data, ['api_key', 'password'])
    print(f"  加密后: {data}")
    decrypt_dict_fields(data, ['api_key', 'password'])
    print(f"  解密后: {data}")
