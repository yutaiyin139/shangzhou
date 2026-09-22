# -*- coding: utf-8 -*-
"""
Code 节点执行模块

负责执行代码节点（Python3），支持：
- 输入变量提取与注入
- 安全沙箱子进程隔离执行
- 输出变量配置映射
- 超时控制
"""


def _node_code(data, context, model_cfg=None):
    """执行代码节点（Python3）—— 安全沙箱隔离执行"""
    code = data.get('code', '')
    # 提取输入变量
    input_vars = {}
    for k, v in context.items():
        if k.startswith('__'):
            continue  # 引擎内部键（如 __flat_owner__）不作为脚本入参
        if isinstance(v, (str, int, float, bool, list, dict)):
            input_vars[k] = v

    # 安全加固：使用子进程隔离沙箱执行
    from utils.sandbox import execute_code_safely
    timeout = data.get('timeout', 120)  # 默认 120 秒超时
    result = execute_code_safely(code, input_vars, timeout=timeout)

    if not result['success']:
        return {'result': f"代码执行错误: {result['error']}"}

    # 根据 outputs 配置提取输出变量。
    # 沙箱约定: 代码通过「顶层赋值到与 outputs 同名的变量」暴露输出
    # （如 ``result = args['x'] * 2``），而非通过 return。
    outputs_config = data.get('outputs', {})
    if outputs_config and isinstance(outputs_config, dict):
        output = {}
        for out_key in outputs_config:
            # 1) 沙箱顶层赋值变量（assigned，如 sub_out = 'SUB_OK'）
            value = result.get('assigned', {}).get(out_key)
            # 2) 沙箱直接返回的 dict 结果 {out_key: ...}
            if value is None and isinstance(result['result'], dict) and out_key in result['result']:
                value = result['result'][out_key]
            # 3) 执行前的输入变量（code 节点可能透传）
            if value is None and out_key in input_vars:
                value = input_vars[out_key]
            if value is not None:
                output[out_key] = value
        if output:
            return output
        # 兜底：沙箱直接返回的标量结果
        if result['result'] is not None:
            return {'result': result['result']}
        return {'result': ''}
    else:
        # 兼容旧格式，只返回 result
        return {'result': result['result'] if result['result'] is not None else ''}
