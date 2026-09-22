# -*- coding: utf-8 -*-
"""
工作流节点执行模块

每个节点类型对应一个子模块，包含该节点的执行函数。
新增节点只需创建子模块并在此处导出即可。

使用方式:
    from nodes import _node_llm, _node_code
    # 或
    from engine.node_factory import NodeFactory
    result = NodeFactory.execute('llm', data, context, model_cfg)
"""

from .llm import _node_llm
from .code import _node_code
from .if_else import _node_ifelse
from .http_request import _node_http_request
from .tool import _node_tool
from .mcp import _node_mcp
from .knowledge_retrieval import _node_knowledge_retrieval
from .agent import _node_agent
from .iteration import _node_iteration
from .loop import _node_loop
from .sub_graph import _node_sub_graph
from .batch_task import _node_batch_task
from .human_input import _node_human_input
from .variable_aggregator import _node_variable_aggregator
from .question_classifier import _node_question_classifier
from .parameter_extractor import _node_parameter_extractor
from .document_extractor import _node_document_extractor
from .template_transform import _node_template_transform
from .list_operator import _node_list_operator

__all__ = [
    '_node_llm',
    '_node_code',
    '_node_ifelse',
    '_node_http_request',
    '_node_tool',
    '_node_mcp',
    '_node_knowledge_retrieval',
    '_node_agent',
    '_node_iteration',
    '_node_loop',
    '_node_sub_graph',
    '_node_batch_task',
    '_node_human_input',
    '_node_variable_aggregator',
    '_node_question_classifier',
    '_node_parameter_extractor',
    '_node_document_extractor',
    '_node_template_transform',
    '_node_list_operator',
]
