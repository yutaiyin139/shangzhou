# -*- coding: utf-8 -*-
"""
LLM Tracing 集成模块 —— 对齐 Dify 1.17 Tracing 功能

支持后端:
- Langfuse (开源自托管)
- LangSmith (Anthropic 官方)
- Opik (Comet 开源)
- 自定义 Webhook

使用方式:
    from utils.tracing import trace_llm_call

    with trace_llm_call(model="gpt-4", messages=messages, run_id=run_id) as trace:
        result = call_llm(...)
        trace.set_output(result)
"""

import os
import json
import time
import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================

def get_tracing_config():
    """获取 Tracing 配置（从环境变量或 system_settings 表）"""
    config = {
        'backend': os.environ.get('TRACING_BACKEND', ''),  # langfuse / langsmith / opik / webhook
        'enabled': os.environ.get('TRACING_ENABLED', 'false').lower() in ('true', '1', 'yes'),
    }

    # Langfuse
    if config['backend'] == 'langfuse':
        config['langfuse'] = {
            'public_key': os.environ.get('LANGFUSE_PUBLIC_KEY', ''),
            'secret_key': os.environ.get('LANGFUSE_SECRET_KEY', ''),
            'host': os.environ.get('LANGFUSE_HOST', 'https://cloud.langfuse.com'),
        }
    # LangSmith
    elif config['backend'] == 'langsmith':
        config['langsmith'] = {
            'api_key': os.environ.get('LANGSMITH_API_KEY', ''),
            'project': os.environ.get('LANGSMITH_PROJECT', 'entropy-boat'),
            'endpoint': os.environ.get('LANGSMITH_ENDPOINT', 'https://api.smith.langchain.com'),
        }
    # Opik
    elif config['backend'] == 'opik':
        config['opik'] = {
            'api_key': os.environ.get('OPIK_API_KEY', ''),
            'workspace': os.environ.get('OPIK_WORKSPACE', 'entropy-boat'),
            'project': os.environ.get('OPIK_PROJECT', 'entropy-boat'),
            'url': os.environ.get('OPIK_URL', 'https://www.comet.com/opik/api'),
        }
    # 自定义 Webhook
    elif config['backend'] == 'webhook':
        config['webhook'] = {
            'url': os.environ.get('TRACING_WEBHOOK_URL', ''),
            'headers': json.loads(os.environ.get('TRACING_WEBHOOK_HEADERS', '{}')),
        }

    return config


# ============================================================
# Trace 上下文
# ============================================================

class LLMTrace:
    """单次 LLM 调用的 Trace 记录"""

    def __init__(self, trace_id='', run_id='', model='', node_id='', node_type=''):
        self.trace_id = trace_id or f'trace_{int(time.time() * 1000)}'
        self.run_id = run_id
        self.model = model
        self.node_id = node_id
        self.node_type = node_type
        self.messages = []
        self.output = ''
        self.start_time = time.time()
        self.end_time = None
        self.duration_ms = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.error = None
        self.metadata = {}

    def set_input(self, messages):
        """设置输入消息"""
        self.messages = messages if isinstance(messages, list) else []

    def set_output(self, content, usage=None):
        """设置输出内容和 token 用量"""
        self.output = content or ''
        if usage:
            self.input_tokens = usage.get('prompt_tokens', 0) or usage.get('input_tokens', 0)
            self.output_tokens = usage.get('completion_tokens', 0) or usage.get('output_tokens', 0)
            self.total_tokens = usage.get('total_tokens', 0)

    def set_error(self, error):
        """记录错误"""
        self.error = str(error)[:500]

    def set_metadata(self, **kwargs):
        """设置额外元数据"""
        self.metadata.update(kwargs)

    def finish(self):
        """完成 trace 记录"""
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)

    def to_dict(self):
        """序列化为 dict"""
        return {
            'trace_id': self.trace_id,
            'run_id': self.run_id,
            'model': self.model,
            'node_id': self.node_id,
            'node_type': self.node_type,
            'messages': self.messages,
            'output': self.output[:5000] if self.output else '',
            'duration_ms': self.duration_ms,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'error': self.error,
            'metadata': self.metadata,
        }


# ============================================================
# 后端适配器
# ============================================================

class BaseTracingAdapter:
    """Tracing 后端基类"""

    def send_trace(self, trace: LLMTrace):
        raise NotImplementedError

    def send_event(self, event_type, data):
        pass


class LangfuseAdapter(BaseTracingAdapter):
    """Langfuse 后端适配器"""

    def __init__(self, config):
        self.config = config.get('langfuse', {})
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            from langfuse import Langfuse
            self.client = Langfuse(
                public_key=self.config.get('public_key', ''),
                secret_key=self.config.get('secret_key', ''),
                host=self.config.get('host', 'https://cloud.langfuse.com'),
            )
        except ImportError:
            logger.warning('[Tracing] langfuse 包未安装，运行: pip install langfuse')
        except Exception as e:
            logger.warning(f'[Tracing] Langfuse 初始化失败: {e}')

    def send_trace(self, trace: LLMTrace):
        if not self.client:
            return
        try:
            generation = self.client.generation(
                name=f'llm-{trace.node_type or "call"}',
                trace_id=trace.trace_id,
                model=trace.model,
                input=trace.messages,
                output=trace.output[:2000] if trace.output else '',
                start_time=trace.start_time,
                end_time=trace.end_time,
                usage={
                    'input': trace.input_tokens,
                    'output': trace.output_tokens,
                    'total': trace.total_tokens,
                    'unit': 'TOKENS',
                },
                metadata={
                    'run_id': trace.run_id,
                    'node_id': trace.node_id,
                    'node_type': trace.node_type,
                    **trace.metadata,
                },
            )
            self.client.flush()
        except Exception as e:
            logger.warning(f'[Tracing] Langfuse 发送失败: {e}')

    def send_event(self, event_type, data):
        if not self.client:
            return
        try:
            self.client.event(
                name=event_type,
                trace_id=data.get('trace_id', ''),
                metadata=data,
            )
        except Exception:
            pass


class LangSmithAdapter(BaseTracingAdapter):
    """LangSmith 后端适配器"""

    def __init__(self, config):
        self.config = config.get('langsmith', {})
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            from langsmith import Client
            self.client = Client(
                api_key=self.config.get('api_key', ''),
                api_url=self.config.get('endpoint', 'https://api.smith.langchain.com'),
            )
        except ImportError:
            logger.warning('[Tracing] langsmith 包未安装，运行: pip install langsmith')
        except Exception as e:
            logger.warning(f'[Tracing] LangSmith 初始化失败: {e}')

    def send_trace(self, trace: LLMTrace):
        if not self.client:
            return
        try:
            self.client.create_run(
                name=f'llm-{trace.node_type or "call"}',
                run_type='llm',
                inputs={'messages': trace.messages},
                outputs={'output': trace.output[:2000]} if trace.output else None,
                extra={
                    'metadata': {
                        'model': trace.model,
                        'run_id': trace.run_id,
                        'node_id': trace.node_id,
                        'node_type': trace.node_type,
                        'duration_ms': trace.duration_ms,
                        'total_tokens': trace.total_tokens,
                        **trace.metadata,
                    },
                },
                project_name=self.config.get('project', 'entropy-boat'),
                trace_id=trace.trace_id,
                id=trace.trace_id,
            )
        except Exception as e:
            logger.warning(f'[Tracing] LangSmith 发送失败: {e}')


class OpikAdapter(BaseTracingAdapter):
    """Opik (Comet) 后端适配器"""

    def __init__(self, config):
        self.config = config.get('opik', {})
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            import opik
            opik.configure(
                api_key=self.config.get('api_key', ''),
                workspace_name=self.config.get('workspace', 'entropy-boat'),
                url=self.config.get('url', 'https://www.comet.com/opik/api'),
            )
            from opik import Opik
            self.client = Opik(project_name=self.config.get('project', 'entropy-boat'))
        except ImportError:
            logger.warning('[Tracing] opik 包未安装，运行: pip install opik')
        except Exception as e:
            logger.warning(f'[Tracing] Opik 初始化失败: {e}')

    def send_trace(self, trace: LLMTrace):
        if not self.client:
            return
        try:
            self.client.trace(
                id=trace.trace_id,
                name=f'llm-{trace.node_type or "call"}',
                type='llm',
                inputs={'messages': trace.messages},
                outputs={'output': trace.output[:2000]} if trace.output else None,
                metadata={
                    'model': trace.model,
                    'run_id': trace.run_id,
                    'node_id': trace.node_id,
                    'node_type': trace.node_type,
                    'duration_ms': trace.duration_ms,
                    'total_tokens': trace.total_tokens,
                    **trace.metadata,
                },
                usage={
                    'prompt_tokens': trace.input_tokens,
                    'completion_tokens': trace.output_tokens,
                    'total_tokens': trace.total_tokens,
                },
            )
            self.client.flush()
        except Exception as e:
            logger.warning(f'[Tracing] Opik 发送失败: {e}')


class WebhookAdapter(BaseTracingAdapter):
    """自定义 Webhook 后端适配器"""

    def __init__(self, config):
        self.config = config.get('webhook', {})

    def send_trace(self, trace: LLMTrace):
        url = self.config.get('url', '')
        if not url:
            return
        try:
            import urllib.request
            payload = json.dumps(trace.to_dict(), ensure_ascii=False, default=str).encode('utf-8')
            headers = {'Content-Type': 'application/json'}
            headers.update(self.config.get('headers', {}))
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass
        except Exception as e:
            logger.warning(f'[Tracing] Webhook 发送失败: {e}')


class NoOpAdapter(BaseTracingAdapter):
    """空操作适配器（Tracing 未启用时）"""

    def send_trace(self, trace: LLMTrace):
        pass

    def send_event(self, event_type, data):
        pass


# ============================================================
# 全局实例
# ============================================================

_adapter = None
_adapter_lock = threading.Lock()


def get_adapter():
    """获取全局 Tracing 适配器（延迟初始化）"""
    global _adapter
    if _adapter is not None:
        return _adapter

    with _adapter_lock:
        if _adapter is not None:
            return _adapter

        config = get_tracing_config()
        if not config['enabled'] or not config['backend']:
            _adapter = NoOpAdapter()
            return _adapter

        backend = config['backend'].lower()
        if backend == 'langfuse':
            _adapter = LangfuseAdapter(config)
        elif backend == 'langsmith':
            _adapter = LangSmithAdapter(config)
        elif backend == 'opik':
            _adapter = OpikAdapter(config)
        elif backend == 'webhook':
            _adapter = WebhookAdapter(config)
        else:
            logger.warning(f'[Tracing] 未知后端: {backend}，禁用 Tracing')
            _adapter = NoOpAdapter()

        return _adapter


def reset_adapter():
    """重置适配器（用于测试或配置变更后）"""
    global _adapter
    with _adapter_lock:
        _adapter = None


# ============================================================
# 便捷函数
# ============================================================

@contextmanager
def trace_llm_call(model='', messages=None, run_id='', node_id='', node_type='', **metadata):
    """
    LLM 调用追踪上下文管理器

    用法:
        with trace_llm_call(model="gpt-4", messages=msgs, run_id=run_id) as trace:
            result = call_llm(...)
            trace.set_output(result['content'], result.get('usage'))
    """
    trace = LLMTrace(
        run_id=run_id,
        model=model,
        node_id=node_id,
        node_type=node_type,
    )
    if messages:
        trace.set_input(messages)
    if metadata:
        trace.set_metadata(**metadata)

    try:
        yield trace
    except Exception as e:
        trace.set_error(e)
        raise
    finally:
        trace.finish()
        try:
            get_adapter().send_trace(trace)
        except Exception:
            pass


def trace_event(event_type, **data):
    """发送自定义事件"""
    try:
        get_adapter().send_event(event_type, data)
    except Exception:
        pass


def is_tracing_enabled():
    """检查 Tracing 是否已启用"""
    config = get_tracing_config()
    return config['enabled'] and bool(config['backend'])
