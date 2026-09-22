# -*- coding: utf-8 -*-
"""
结构化日志系统 —— JSON 格式 + 文件轮转 + 统一配置

功能：
1. JSON 结构化日志（便于 ELK/Loki 解析）
2. 文件轮转（按大小，保留 10 个备份）
3. 控制台 + 文件双输出
4. 环境变量配置日志级别
5. 请求 ID 追踪（可选）

依赖：无额外依赖（使用 Python 标准库）
"""

import os
import sys
import logging
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
# 默认日志文件
DEFAULT_LOG_FILE = os.path.join(LOG_DIR, 'backend.log')
# 错误日志文件
ERROR_LOG_FILE = os.path.join(LOG_DIR, 'error.log')

# 日志格式
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# JSON 格式（用于生产环境）
JSON_FORMAT = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'


class JsonFormatter(logging.Formatter):
    """JSON 格式日志格式化器"""

    def format(self, record):
        import json
        log_data = {
            'time': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        # 添加异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_data['exception'] = self.formatException(record.exc_info)
        # 添加额外字段
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        return json.dumps(log_data, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    """请求 ID 过滤器（用于追踪请求）"""

    def filter(self, record):
        if not hasattr(record, 'request_id'):
            record.request_id = ''
        return True


def setup_logging(app=None):
    """
    配置全局日志系统

    环境变量：
        LOG_LEVEL: 日志级别 (DEBUG/INFO/WARNING/ERROR)，默认 INFO
        LOG_FILE: 日志文件路径，默认 logs/backend.log
        LOG_FORMAT: 输出格式 (text/json)，默认 text
        LOG_MAX_SIZE: 单个日志文件大小（字节），默认 10MB
        LOG_BACKUP_COUNT: 备份文件数量，默认 10

    参数:
        app: Flask 应用实例（可选）
    """
    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)

    # 读取环境变量
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', DEFAULT_LOG_FILE)
    log_format_type = os.getenv('LOG_FORMAT', 'text').lower()
    max_size = int(os.getenv('LOG_MAX_SIZE', 10 * 1024 * 1024))  # 10MB
    backup_count = int(os.getenv('LOG_BACKUP_COUNT', 10))

    # 选择格式化器
    if log_format_type == 'json':
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())
    root_logger.addHandler(console_handler)

    # 文件处理器（轮转）
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIdFilter())
        root_logger.addHandler(file_handler)
    except Exception as e:
        # 文件创建失败时仅使用控制台
        root_logger.warning(f'无法创建日志文件 {log_file}: {e}')

    # 错误日志文件（仅 ERROR 及以上）
    try:
        error_handler = RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(RequestIdFilter())
        root_logger.addHandler(error_handler)
    except Exception:
        pass

    # 配置 Flask 日志
    if app:
        app.logger.handlers = root_logger.handlers
        app.logger.setLevel(root_logger.level)

    # 抑制过于冗长的第三方日志
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.INFO)

    root_logger.info(f'日志系统已初始化 (级别={log_level}, 格式={log_format_type}, 文件={log_file})')


def get_logger(name):
    """
    获取命名日志器

    参数:
        name: 模块名（建议使用 __name__）

    返回:
        logging.Logger

    示例:
        >>> from utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info('操作成功')
        >>> logger.error('操作失败', exc_info=True)
    """
    return logging.getLogger(name)


def log_request_start(request):
    """记录请求开始"""
    logger = get_logger('request')
    logger.info(f'{request.method} {request.path} - 开始处理')


def log_request_end(request, response, duration_ms):
    """记录请求结束"""
    logger = get_logger('request')
    level = logging.INFO if response.status_code < 400 else logging.WARNING
    logger.log(level, f'{request.method} {request.path} - {response.status_code} ({duration_ms:.1f}ms)')


def log_error(error, context=None):
    """
    记录错误（带上下文信息）

    参数:
        error: 异常对象或错误消息
        context: 上下文字典（如 {'user_id': '123', 'action': 'login'}）
    """
    logger = get_logger('error')
    msg = str(error)
    if context:
        msg = f'{msg} | context={context}'
    logger.error(msg, exc_info=True)


# 便捷函数：快速配置（用于脚本）
def quick_setup(level='INFO'):
    """快速配置日志（用于独立脚本）"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT
    )


if __name__ == '__main__':
    # 测试
    setup_logging()

    logger = get_logger('test')
    logger.debug('这是 DEBUG 消息')
    logger.info('这是 INFO 消息')
    logger.warning('这是 WARNING 消息')
    logger.error('这是 ERROR 消息')

    try:
        1 / 0
    except Exception:
        logger.exception('捕获到异常')
