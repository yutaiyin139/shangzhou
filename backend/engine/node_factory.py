# -*- coding: utf-8 -*-
"""
NodeFactory —— 节点注册表/工厂

统一管理所有工作流节点的注册和创建。
新增节点只需：创建 nodes/xxx.py → 在 NODE_MAPPINGS 中添加映射。

使用方式:
    from engine.node_factory import NodeFactory

    # 执行节点
    result = NodeFactory.execute(node_type, data, context, model_cfg)
"""
from typing import Any, Callable, Dict, Optional


class NodeFactory:
    """节点注册表/工厂"""

    _registry: Dict[str, Callable] = {}

    @classmethod
    def register(cls, node_type: str, func: Callable):
        """
        注册一个节点执行函数。

        参数:
            node_type: 节点类型标识（如 'llm', 'code'）
            func: 执行函数，签名为 (data, context, model_cfg) -> dict
        """
        cls._registry[node_type] = func

    @classmethod
    def execute(cls, node_type: str, data: Dict[str, Any],
                context: Dict[str, Any],
                model_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行指定类型的节点。

        参数:
            node_type: 节点类型标识
            data: 节点配置数据
            context: 工作流上下文变量
            model_cfg: 应用级模型配置

        返回:
            节点执行结果字典

        抛出:
            KeyError: 节点类型未注册时
        """
        if node_type not in cls._registry:
            raise KeyError(f"未知节点类型: {node_type!r}。已注册: {list(cls._registry.keys())}")
        return cls._registry[node_type](data, context, model_cfg)

    @classmethod
    def is_registered(cls, node_type: str) -> bool:
        """检查节点类型是否已注册"""
        return node_type in cls._registry

    @classmethod
    def registered_types(cls):
        """获取所有已注册的节点类型列表"""
        return list(cls._registry.keys())


def _auto_register():
    """
    自动注册所有已实现的节点函数。
    新增节点只需在此函数中添加一行 register 调用。
    """
    # 基础节点（无需执行）
    # start：输入变量由 runner 预写入 start 节点命名空间，此处不重复输出整个上下文
    # end：解析其声明的 outputs（value_selector）后作为业务变量暴露（见 _node_end）
    NodeFactory.register('start', lambda data, ctx, cfg: {})
    NodeFactory.register('end', _node_end)
    NodeFactory.register('answer', _node_answer)
    NodeFactory.register('custom-note', lambda data, ctx, cfg: {})

    # LLM / AI 节点
    from .nodes.llm import _node_llm
    from .nodes.agent import _node_agent
    from .nodes.question_classifier import _node_question_classifier
    from .nodes.parameter_extractor import _node_parameter_extractor

    NodeFactory.register('llm', _node_llm)
    NodeFactory.register('agent', _node_agent)
    NodeFactory.register('question-classifier', _node_question_classifier)
    NodeFactory.register('question_classifier', _node_question_classifier)
    NodeFactory.register('parameter-extractor', _node_parameter_extractor)
    NodeFactory.register('parameter_extractor', _node_parameter_extractor)

    # 代码执行
    from .nodes.code import _node_code
    NodeFactory.register('code', _node_code)

    # 流程控制
    from .nodes.if_else import _node_ifelse
    from .nodes.iteration import _node_iteration
    from .nodes.loop import _node_loop
    from .nodes.sub_graph import _node_sub_graph

    NodeFactory.register('if-else', _node_ifelse)
    NodeFactory.register('if_else', _node_ifelse)
    NodeFactory.register('iteration', _node_iteration)
    NodeFactory.register('loop', _node_loop)
    NodeFactory.register('sub-graph', _node_sub_graph)
    NodeFactory.register('sub_graph', _node_sub_graph)

    # 外部调用
    from .nodes.http_request import _node_http_request
    from .nodes.tool import _node_tool
    from .nodes.mcp import _node_mcp

    NodeFactory.register('http-request', _node_http_request)
    NodeFactory.register('http_request', _node_http_request)
    NodeFactory.register('tool', _node_tool)
    NodeFactory.register('mcp', _node_mcp)

    # 知识库
    from .nodes.knowledge_retrieval import _node_knowledge_retrieval
    NodeFactory.register('knowledge-retrieval', _node_knowledge_retrieval)
    NodeFactory.register('knowledge_retrieval', _node_knowledge_retrieval)

    # 数据处理
    from .nodes.variable_aggregator import _node_variable_aggregator
    from .nodes.template_transform import _node_template_transform
    from .nodes.list_operator import _node_list_operator
    from .nodes.document_extractor import _node_document_extractor
    from .nodes.batch_task import _node_batch_task

    NodeFactory.register('variable-assigner', _node_variable_aggregator)
    NodeFactory.register('assigner', _node_variable_aggregator)
    NodeFactory.register('variable-aggregator', _node_variable_aggregator)
    NodeFactory.register('variable_aggregator', _node_variable_aggregator)
    NodeFactory.register('template-transform', _node_template_transform)
    NodeFactory.register('template_transform', _node_template_transform)
    NodeFactory.register('list-operator', _node_list_operator)
    NodeFactory.register('list_operator', _node_list_operator)
    NodeFactory.register('document-extractor', _node_document_extractor)
    NodeFactory.register('document_extractor', _node_document_extractor)
    NodeFactory.register('batch-task', _node_batch_task)
    NodeFactory.register('batch_task', _node_batch_task)

    # 人机交互
    from .nodes.human_input import _node_human_input
    NodeFactory.register('human-input', _node_human_input)

    # 触发节点
    NodeFactory.register('trigger-schedule', _node_trigger)
    NodeFactory.register('trigger-webhook', _node_trigger)

    # 数据源 / 知识索引（延迟导入，避免循环依赖）
    NodeFactory.register('datasource', _node_datasource)
    NodeFactory.register('knowledge-index', _node_knowledge_index)


# ============================================================
# 辅助函数（内部使用）
# ============================================================

def _node_end(data, context, model_cfg=None):
    """结束节点 —— 解析画布上声明的输出变量。

    工作流的最终回答来自结束节点配置的 outputs（每项 {variable, value_selector}），
    典型如 value_selector=['llm3','text'] 引用报告正文。若不解析，发布后的应用只能
    拿到首个同名扁平变量（往往是中间 LLM 输出），导致“答非所问”。
    未配置 outputs 的旧图仍返回空 dict，行为与之前一致。
    """
    outputs_cfg = data.get('outputs') or data.get('output_vars') or []
    result = {}
    for o in outputs_cfg:
        if not isinstance(o, dict):
            continue
        var_name = (o.get('variable') or o.get('name') or '').strip()
        sel = o.get('value_selector') or o.get('selector') or []
        if not sel and var_name:
            sel = [var_name]
        value = _resolve_end_selector(context, sel)
        if var_name and value is not None:
            result[var_name] = value
    # 把首个字符串型输出同时作为 answer，便于发布态/对话直接回复
    for v in result.values():
        if isinstance(v, str) and v:
            result.setdefault('answer', v)
            break
    return result


def _resolve_end_selector(context, selector):
    """命名空间感知的选择器取值：支持 ['node_id','var'] 与扁平 ['var']。"""
    if not selector:
        return None
    if isinstance(selector, str):
        selector = [p for p in selector.split('.') if p != '']
    value = context
    for key in selector:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
        if value is None:
            return None
    return value


def _node_answer(data, context, model_cfg=None):
    """Answer 节点 —— 直接回复"""
    answer = data.get('answer', '')
    for k, v in context.items():
        if k.startswith('__'):
            continue  # 引擎内部键不参与替换
        if isinstance(v, str):
            answer = answer.replace('{{' + k + '}}', v)
    return {'answer': answer, 'text': answer}


def _node_trigger(data, context=None, model_cfg=None):
    """触发节点（入参签名与其他节点保持一致，供 NodeFactory 统一调用）"""
    return {'trigger_type': data.get('type', ''),
            'trigger_time': __import__('datetime').datetime.now().isoformat()}


def _node_datasource(data, context, model_cfg=None):
    """数据源节点（延迟导入）"""
    from engine.datasource_engine import run_datasource
    return run_datasource(data, context)


def _node_knowledge_index(data, context, model_cfg=None):
    """知识索引节点（延迟导入）"""
    from engine.knowledge_index_engine import run_knowledge_index
    return run_knowledge_index(data, context)


# 模块加载时自动注册所有节点
_auto_register()
