# -*- coding: utf-8 -*-
"""
NodeBase —— 节点执行抽象基类

所有工作流节点实现应继承此类，并实现 execute 方法。
节点通过 NodeFactory.register() 注册到全局注册表。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class NodeBase(ABC):
    """
    节点执行抽象基类。

    子类必须实现:
    - node_type: 类属性，节点类型标识（如 'llm', 'code'）
    - execute(data, context, model_cfg): 执行节点逻辑
    """

    node_type: str = ''

    @abstractmethod
    def execute(self, data: Dict[str, Any], context: Dict[str, Any],
                model_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行节点逻辑。

        参数:
            data: 节点配置数据
            context: 工作流上下文变量
            model_cfg: 应用级模型配置

        返回:
            节点执行结果字典（将合并到上下文）
        """
        raise NotImplementedError

    def __call__(self, data: Dict[str, Any], context: Dict[str, Any],
                 model_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """便捷调用方式：node(data, context, model_cfg)"""
        return self.execute(data, context, model_cfg)


class FunctionNode(NodeBase):
    """
    函数式节点适配器。

    将普通函数适配为 NodeBase 实例，便于统一注册和调用。
    """

    def __init__(self, node_type: str, func):
        self.node_type = node_type
        self._func = func

    def execute(self, data: Dict[str, Any], context: Dict[str, Any],
                model_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._func(data, context, model_cfg)
