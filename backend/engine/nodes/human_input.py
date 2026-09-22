# -*- coding: utf-8 -*-
"""
Human Input 节点 —— 暂停工作流执行，等待用户输入。

工作流程：
1. 工作流执行到 Human Input 节点时暂停
2. 前端检测到暂停状态，显示输入表单
3. 用户填写并提交表单
4. 工作流从暂停处继续执行
"""


def _node_human_input(data, context, model_cfg=None):
    """
    Human Input 节点

    节点数据结构:
    - message: 提示信息（显示给用户）
    - form_fields: 表单字段列表 [{name, label, type, required, placeholder}]
    - output: 输出变量名（默认 'human_input'）
    - email: 接收邮箱（可选，配置后发送表单链接邮件）
    """
    # 获取配置
    message = data.get('message', '请输入信息：')
    form_fields = data.get('form_fields', [])
    output_var = data.get('output', 'human_input')
    email = data.get('email', '')

    # 变量替换
    for k, v in context.items():
        if k.startswith('__'):
            continue
        if isinstance(v, (str, int, float)):
            message = message.replace('{{' + k + '}}', str(v))

    # 构建表单配置
    form_config = {
        'message': message,
        'fields': form_fields,
    }
    if email:
        form_config['email'] = email

    # 返回特殊标记，表示需要暂停等待用户输入
    return {
        '_human_input_wait': True,
        '_human_input_config': form_config,
        '_human_input_output_var': output_var,
        '_human_input_node_id': data.get('_node_id', ''),
    }
