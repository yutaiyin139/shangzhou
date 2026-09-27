# -*- coding: utf-8 -*-
"""
Agent 策略抽象层 —— 对齐 Dify 1.17 agent_v2 运行时

支持策略：
- react: ReAct 循环（推理 + 工具调用），文本格式解析
- function_call: 函数调用（OpenAI tools 协议），原生工具调用
- plan_execute: 规划-执行（先规划步骤，再逐步执行）

统一接口：
    strategy = get_strategy("react")
    result = strategy.run(messages, tools, context, llm_config)
    # result = {"output": str, "tool_calls": [...], "thought_chain": [...], "tokens": int}
"""

import json
import logging
import re
import time
from config import get_db

logger = logging.getLogger('szagent.agent_strategies')


# ============================================================
# 策略注册表
# ============================================================

_STRATEGIES = {}


def register_strategy(name):
    """策略注册装饰器"""
    def decorator(cls):
        _STRATEGIES[name] = cls()
        return cls
    return decorator


def get_strategy(name: str):
    """获取策略实例"""
    strategy = _STRATEGIES.get(name)
    if not strategy:
        raise ValueError(f"未知策略: {name}，可用策略: {list(_STRATEGIES.keys())}")
    return strategy


def list_strategies():
    """列出所有可用策略"""
    return {
        'react': {
            'name': 'ReAct',
            'name_zh': '推理+行动',
            'description': 'Reasoning + Acting 循环，LLM 通过文本格式决定调用工具或直接回答',
            'supports_tools': True,
            'supports_thought_chain': True,
        },
        'function_call': {
            'name': 'Function Call',
            'name_zh': '函数调用',
            'description': '使用 OpenAI tools 协议，LLM 原生函数调用能力',
            'supports_tools': True,
            'supports_thought_chain': True,
        },
        'plan_execute': {
            'name': 'Plan & Execute',
            'name_zh': '规划+执行',
            'description': '先规划完整步骤，再逐步执行，适合复杂多步任务',
            'supports_tools': True,
            'supports_thought_chain': True,
        },
    }


# ============================================================
# 基础策略类
# ============================================================

class BaseStrategy:
    """策略基类"""

    def run(self, messages, tools, context, llm_config, on_thought=None):
        """
        执行策略

        参数:
            messages: list[dict] — OpenAI 格式消息列表
            tools: list[dict] — 工具定义列表
            context: dict — 工作流上下文
            llm_config: dict — LLM 配置 {model, api_key, base_url, temperature, max_tokens}
            on_thought: callable — 可选的流式回调函数，每步思考时调用
                       签名: on_thought(event_dict) -> None
                       事件格式: {"type": "thought"|"tool_call"|"reasoning", "content": str, "tool_name": str, ...}

        返回:
            dict — {output, tool_calls, thought_chain, tokens, iterations}
        """
        raise NotImplementedError

    def _emit_thought(self, on_thought, event_type, content, **kwargs):
        """统一的思考事件发射（供子类调用）"""
        if not on_thought:
            return
        try:
            event = {'type': event_type, 'content': content}
            event.update(kwargs)
            on_thought(event)
        except Exception:
            pass  # 回调异常不影响主流程

    def _call_llm(self, messages, llm_config, tools=None):
        """调用 LLM（非流式，OpenAI 兼容）"""
        import json
        from utils.llm import build_openai_url
        from engine.nodes.llm import _http_request
        api_url = build_openai_url(llm_config.get('base_url', '').rstrip('/'), 'chat/completions')
        payload = json.dumps({
            'model': llm_config.get('model', ''),
            'messages': messages,
            'temperature': llm_config.get('temperature', 0.7),
            'max_tokens': llm_config.get('max_tokens', 2048),
            'stream': False,
        }).encode('utf-8')
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + llm_config.get('api_key', '')}
        try:
            resp = _http_request(api_url, data=payload, headers=headers, method='POST', timeout=120)
            result = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            raise Exception(f'模型 API 连接失败，请检查网络连接。URL: {api_url}, 错误: {e}') from e
        content = ''
        total_tokens = 0
        if result.get('choices'):
            content = result['choices'][0].get('message', {}).get('content', '') or ''
        if result.get('usage'):
            total_tokens = result['usage'].get('total_tokens', 0)
        return {'content': content, 'total_tokens': total_tokens}

    def _execute_tool(self, tool_name, tool_input, tools, context):
        """执行工具"""
        from engine.nodes.agent import _execute_agent_tool
        return _execute_agent_tool(tool_name, tool_input, tools, context)

    def _build_tool_descriptions(self, tools):
        """构建工具描述文本"""
        from engine.nodes.agent import _build_tool_descriptions
        return _build_tool_descriptions(tools)


# ============================================================
# ReAct 策略（文本格式解析）
# ============================================================

@register_strategy('react')
class ReActStrategy(BaseStrategy):
    """
    ReAct 策略 —— 推理 + 行动循环

    LLM 通过文本格式输出：
    - Action: 工具名 / Action Input: JSON → 调用工具
    - Final Answer: 文本 → 返回最终答案
    """

    def run(self, messages, tools, context, llm_config, on_thought=None):
        max_iterations = llm_config.get('max_iterations', 5)
        tool_descriptions = self._build_tool_descriptions(tools)

        # 构建系统提示词
        system_msg = messages[0] if messages and messages[0].get('role') == 'system' else None
        system_content = system_msg['content'] if system_msg else '你是一个智能助手，可以使用工具来帮助用户解决问题。'

        if tool_descriptions:
            system_content += '\n\n你可以使用以下工具：\n' + tool_descriptions
        system_content += '\n\n请按照以下格式回复：\n'
        system_content += '如果需要调用工具，回复：\n'
        system_content += 'Action: 工具名称\n'
        system_content += 'Action Input: 工具输入参数（JSON格式）\n\n'
        system_content += '如果已有最终答案，回复：\n'
        system_content += 'Final Answer: 你的最终回答'

        # 重建消息列表
        react_messages = [{'role': 'system', 'content': system_content}]
        for msg in messages:
            if msg.get('role') != 'system':
                react_messages.append(msg)

        tool_calls_history = []
        thought_chain = []
        total_tokens = 0
        final_answer = ''
        observation = ''

        for iteration in range(max_iterations):
            # 构建当前消息
            current_messages = list(react_messages)
            if observation:
                current_messages.append({'role': 'user', 'content': f'Observation: {observation}'})

            # 调用 LLM
            llm_result = self._call_llm(current_messages, llm_config)
            total_tokens += llm_result.get('total_tokens', 0)
            llm_response = llm_result.get('content', '')

            # 解析响应
            parsed = self._parse_response(llm_response)

            if parsed.get('type') == 'final_answer':
                final_answer = parsed.get('content', '')
                thought_chain.append({
                    'position': len(thought_chain),
                    'thought': llm_response,
                    'tool_name': '',
                    'tool_input': '',
                    'tool_output': '',
                    'step_type': 'reasoning',
                })
                self._emit_thought(on_thought, 'reasoning', llm_response, step_type='final_answer')
                self._emit_thought(on_thought, 'done', final_answer, iterations=len(thought_chain), tokens=total_tokens)
                break
            elif parsed.get('type') == 'action':
                action_name = parsed.get('action', '')
                action_input = parsed.get('action_input', {})

                # 发射"思考中"事件
                self._emit_thought(on_thought, 'reasoning', llm_response, step_type='action', tool_name=action_name)

                tool_result = self._execute_tool(action_name, action_input, tools, context)
                observation = str(tool_result)

                tool_calls_history.append({
                    'tool': action_name,
                    'input': action_input,
                    'output': observation,
                })
                thought_chain.append({
                    'position': len(thought_chain),
                    'thought': llm_response,
                    'tool_name': action_name,
                    'tool_input': json.dumps(action_input, ensure_ascii=False) if isinstance(action_input, (dict, list)) else str(action_input),
                    'tool_output': observation[:2000],
                    'step_type': 'tool_call',
                })

                # 发射"工具调用"事件
                self._emit_thought(on_thought, 'tool_call', observation,
                    tool_name=action_name,
                    tool_input=tool_calls_history[-1]['input'],
                    tool_output=observation[:2000])
            else:
                # 无法解析，作为最终答案
                final_answer = llm_response
                thought_chain.append({
                    'position': len(thought_chain),
                    'thought': llm_response,
                    'tool_name': '',
                    'tool_input': '',
                    'tool_output': '',
                    'step_type': 'reasoning',
                })
                self._emit_thought(on_thought, 'reasoning', llm_response, step_type='unknown_parse')
                self._emit_thought(on_thought, 'done', final_answer, iterations=len(thought_chain), tokens=total_tokens)
                break
        else:
            final_answer = final_answer or f'达到最大迭代次数 {max_iterations}，未能完成任务。'
            self._emit_thought(on_thought, 'reasoning', final_answer, step_type='max_iterations')
            self._emit_thought(on_thought, 'done', final_answer, iterations=len(thought_chain), tokens=total_tokens)

        return {
            'output': final_answer,
            'tool_calls': tool_calls_history,
            'thought_chain': thought_chain,
            'tokens': total_tokens,
            'iterations': len(thought_chain),
        }

    def _parse_response(self, response):
        """解析 ReAct 格式的 LLM 响应"""
        if not response:
            return {'type': 'unknown', 'content': ''}

        response = response.strip()

        # 尝试 JSON 格式
        try:
            if response.startswith('{') or response.startswith('['):
                parsed = json.loads(response)
                if isinstance(parsed, dict):
                    if 'action' in parsed:
                        return {
                            'type': 'action',
                            'action': parsed.get('action', ''),
                            'action_input': parsed.get('action_input', parsed.get('input', {}))
                        }
                    elif 'final_answer' in parsed or 'answer' in parsed:
                        return {
                            'type': 'final_answer',
                            'content': parsed.get('final_answer', parsed.get('answer', ''))
                        }
        except json.JSONDecodeError:
            pass

        # 文本格式解析
        lines = response.split('\n')
        result = {}
        for line in lines:
            line = line.strip()
            if line.lower().startswith('action:'):
                result['action'] = line[7:].strip()
            elif line.lower().startswith('action input:'):
                input_str = line[13:].strip()
                try:
                    result['action_input'] = json.loads(input_str)
                except json.JSONDecodeError:
                    result['action_input'] = input_str
            elif line.lower().startswith('final answer:'):
                result['final_answer'] = line[13:].strip()

        if 'final_answer' in result:
            return {'type': 'final_answer', 'content': result['final_answer']}
        elif 'action' in result:
            return {
                'type': 'action',
                'action': result['action'],
                'action_input': result.get('action_input', {})
            }
        return {'type': 'unknown', 'content': response}


# ============================================================
# Function Call 策略（OpenAI tools 协议）
# ============================================================

@register_strategy('function_call')
class FunctionCallStrategy(BaseStrategy):
    """
    Function Call 策略 —— 使用 OpenAI tools 协议

    通过 OpenAI 原生的 tools/function calling 能力，
    LLM 返回 tool_calls 字段表示需要调用的工具。
    """

    def run(self, messages, tools, context, llm_config, on_thought=None):
        max_iterations = llm_config.get('max_iterations', 5)
        total_tokens = 0
        tool_calls_history = []
        thought_chain = []
        final_answer = ''

        # 转换工具定义为 OpenAI tools 格式
        openai_tools = self._convert_to_openai_tools(tools)

        for iteration in range(max_iterations):
            # 调用 LLM（带 tools）
            llm_result = self._call_llm_with_tools(messages, llm_config, openai_tools)
            total_tokens += llm_result.get('total_tokens', 0)
            message = llm_result.get('message', {})

            # 检查是否有工具调用
            tool_calls = message.get('tool_calls', [])

            if not tool_calls:
                # 无工具调用，返回最终答案
                final_answer = message.get('content', '')
                thought_chain.append({
                    'position': len(thought_chain),
                    'thought': final_answer,
                    'tool_name': '',
                    'tool_input': '',
                    'tool_output': '',
                    'step_type': 'reasoning',
                })
                self._emit_thought(on_thought, 'reasoning', final_answer, step_type='final_answer')
                self._emit_thought(on_thought, 'done', final_answer, iterations=len(thought_chain), tokens=total_tokens)
                break

            # 执行工具调用
            messages.append(message)

            # 发射"思考中"事件（含工具调用计划）
            tool_plan = ', '.join(tc.get('function', {}).get('name', '?') for tc in tool_calls)
            self._emit_thought(on_thought, 'reasoning', f'计划调用工具: {tool_plan}',
                step_type='tool_plan', tool_names=tool_plan)

            # 支持并行工具调用（多工具同时执行）
            parallel = llm_config.get('parallel_tool_calls', True)
            if parallel and len(tool_calls) > 1:
                # 并行执行
                from concurrent.futures import ThreadPoolExecutor, as_completed
                tool_results_map = {}
                with ThreadPoolExecutor(max_workers=min(len(tool_calls), 4)) as executor:
                    future_to_tc = {}
                    for tc in tool_calls:
                        function = tc.get('function', {})
                        tool_name = function.get('name', '')
                        try:
                            tool_input = json.loads(function.get('arguments', '{}'))
                        except json.JSONDecodeError:
                            tool_input = {}
                        future = executor.submit(self._execute_tool_safe, tool_name, tool_input, tools, context)
                        future_to_tc[future] = (tc, tool_name, tool_input)
                    for future in as_completed(future_to_tc):
                        tc, tool_name, tool_input = future_to_tc[future]
                        tool_result = future.result()
                        observation = str(tool_result)
                        tool_results_map[tc.get('id', '')] = (tc, tool_name, tool_input, observation)
            else:
                # 串行执行
                tool_results_map = {}
                for tc in tool_calls:
                    function = tc.get('function', {})
                    tool_name = function.get('name', '')
                    try:
                        tool_input = json.loads(function.get('arguments', '{}'))
                    except json.JSONDecodeError:
                        tool_input = {}
                    tool_result = self._execute_tool_safe(tool_name, tool_input, tools, context)
                    observation = str(tool_result)
                    tool_results_map[tc.get('id', '')] = (tc, tool_name, tool_input, observation)

            # 按原始顺序处理结果
            for tc in tool_calls:
                tid = tc.get('id', '')
                if tid not in tool_results_map:
                    continue
                _, tool_name, tool_input, observation = tool_results_map[tid]

                tool_calls_history.append({
                    'tool': tool_name,
                    'input': tool_input,
                    'output': observation,
                })
                thought_chain.append({
                    'position': len(thought_chain),
                    'thought': f'调用工具: {tool_name}',
                    'tool_name': tool_name,
                    'tool_input': json.dumps(tool_input, ensure_ascii=False),
                    'tool_output': observation[:2000],
                    'step_type': 'tool_call',
                })

                # 发射"工具调用"事件
                self._emit_thought(on_thought, 'tool_call', observation,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=observation[:2000])

                # 添加工具结果到消息
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tid,
                    'content': observation[:2000],
                })
        else:
            final_answer = final_answer or f'达到最大迭代次数 {max_iterations}，未能完成任务。'
            self._emit_thought(on_thought, 'reasoning', final_answer, step_type='max_iterations')
            self._emit_thought(on_thought, 'done', final_answer, iterations=len(thought_chain), tokens=total_tokens)

        return {
            'output': final_answer,
            'tool_calls': tool_calls_history,
            'thought_chain': thought_chain,
            'tokens': total_tokens,
            'iterations': len(thought_chain),
        }

    def _convert_to_openai_tools(self, tools):
        """转换工具定义为 OpenAI tools 格式（增强：参数校验 + 必填字段补全）"""
        openai_tools = []
        for tool in tools:
            parameters = tool.get('parameters', {'type': 'object', 'properties': {}})
            # 确保 parameters 格式正确
            if not isinstance(parameters, dict):
                parameters = {'type': 'object', 'properties': {}}
            if 'type' not in parameters:
                parameters['type'] = 'object'
            if 'properties' not in parameters:
                parameters['properties'] = {}
            openai_tools.append({
                'type': 'function',
                'function': {
                    'name': tool.get('name', ''),
                    'description': tool.get('description', ''),
                    'parameters': parameters,
                }
            })
        return openai_tools

    def _execute_tool_safe(self, tool_name, tool_input, tools, context):
        """安全执行工具（带重试和错误格式化）"""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                result = self._execute_tool(tool_name, tool_input, tools, context)
                return result
            except Exception as e:
                if attempt < max_retries:
                    import time
                    time.sleep(0.5 * (attempt + 1))
                    continue
                error_msg = f'工具 {tool_name} 执行失败: {str(e)[:300]}'
                return error_msg

    def _call_llm_with_tools(self, messages, llm_config, tools=None):
        """调用 LLM（带 tools 参数）"""
        from utils.llm import build_openai_url

        model = llm_config.get('model', '')
        api_key = llm_config.get('api_key', '')
        base_url = llm_config.get('base_url', '').rstrip('/')
        temperature = llm_config.get('temperature', 0.7)
        max_tokens = llm_config.get('max_tokens', 2048)

        payload_dict = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': False,
        }
        if tools:
            payload_dict['tools'] = tools

        payload = json.dumps(payload_dict).encode('utf-8')
        api_url = build_openai_url(base_url, 'chat/completions')
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}

        from engine.nodes.llm import _http_request
        resp = _http_request(api_url, data=payload, headers=headers, method='POST', timeout=120)
        result = json.loads(resp.read().decode('utf-8'))

        content = ''
        tool_calls = []
        if 'choices' in result and result['choices']:
            msg = result['choices'][0].get('message', {})
            content = msg.get('content', '')
            tool_calls = msg.get('tool_calls', [])

        total_tokens = result.get('usage', {}).get('total_tokens', 0) if 'usage' in result else 0

        return {
            'message': {'content': content, 'tool_calls': tool_calls},
            'total_tokens': total_tokens,
        }


# ============================================================
# Plan & Execute 策略
# ============================================================

@register_strategy('plan_execute')
class PlanExecuteStrategy(BaseStrategy):
    """
    Plan & Execute 策略 —— 先规划，再执行

    阶段 1: 规划 —— LLM 分析任务，输出步骤列表
    阶段 2: 执行 —— 逐步执行每个步骤，可调用工具
    """

    def run(self, messages, tools, context, llm_config, on_thought=None):
        max_iterations = llm_config.get('max_iterations', 5)
        total_tokens = 0
        tool_calls_history = []
        thought_chain = []

        # 获取用户任务
        user_msg = None
        system_msg = None
        for msg in messages:
            if msg.get('role') == 'user':
                user_msg = msg.get('content', '')
            elif msg.get('role') == 'system':
                system_msg = msg.get('content', '')

        if not user_msg:
            return {
                'output': '未提供任务描述',
                'tool_calls': [],
                'thought_chain': [],
                'tokens': 0,
                'iterations': 0,
            }

        # 阶段 1: 规划
        plan_prompt = self._build_plan_prompt(system_msg, user_msg, tools)
        plan_messages = [
            {'role': 'system', 'content': plan_prompt},
            {'role': 'user', 'content': f'请为以下任务制定执行计划：\n{user_msg}'}
        ]

        plan_result = self._call_llm(plan_messages, llm_config)
        total_tokens += plan_result.get('total_tokens', 0)
        plan_text = plan_result.get('content', '')

        # 解析计划步骤
        steps = self._parse_plan(plan_text)
        thought_chain.append({
            'position': 0,
            'thought': f'规划阶段：\n{plan_text}',
            'tool_name': '',
            'tool_input': '',
            'tool_output': '',
            'step_type': 'planning',
        })
        self._emit_thought(on_thought, 'reasoning', f'规划阶段：\n{plan_text}',
            step_type='planning', plan_steps=steps)

        # 阶段 2: 逐步执行
        final_answer = ''
        step_results = []

        for i, step in enumerate(steps[:max_iterations]):
            step_prompt = self._build_step_prompt(system_msg, step, step_results, tools)
            step_messages = [
                {'role': 'system', 'content': step_prompt},
                {'role': 'user', 'content': f'执行步骤 {i+1}: {step}'}
            ]

            step_result = self._call_llm(step_messages, llm_config)
            total_tokens += step_result.get('total_tokens', 0)
            step_output = step_result.get('content', '')

            # 检查是否需要调用工具
            tool_used = None
            if tools:
                # 简单判断：如果输出包含工具调用标记
                action_match = re.search(r'Action:\s*(.+?)\nAction Input:\s*(.+?)(?:\n|$)', step_output, re.DOTALL)
                if action_match:
                    tool_name = action_match.group(1).strip()
                    try:
                        tool_input = json.loads(action_match.group(2).strip())
                    except json.JSONDecodeError:
                        tool_input = action_match.group(2).strip()

                    tool_result = self._execute_tool(tool_name, tool_input, tools, context)
                    tool_used = {
                        'tool': tool_name,
                        'input': tool_input,
                        'output': str(tool_result),
                    }
                    tool_calls_history.append(tool_used)
                    step_output = str(tool_result)

            step_results.append({'step': step, 'result': step_output})
            thought_chain.append({
                'position': len(thought_chain),
                'thought': f'执行步骤 {i+1}: {step}',
                'tool_name': tool_used['tool'] if tool_used else '',
                'tool_input': json.dumps(tool_used['input'], ensure_ascii=False) if tool_used else '',
                'tool_output': tool_used['output'][:2000] if tool_used else '',
                'step_type': 'execution',
            })

            # 发射"步骤执行"事件
            self._emit_thought(on_thought, 'reasoning' if not tool_used else 'tool_call',
                f'执行步骤 {i+1}: {step}\n结果: {step_output[:500]}',
                step_type='execution', step_index=i+1, total_steps=len(steps))

        # 生成最终答案
        summary_prompt = self._build_summary_prompt(user_msg, step_results)
        summary_messages = [
            {'role': 'system', 'content': summary_prompt},
            {'role': 'user', 'content': '请基于以上执行结果，给出最终回答。'}
        ]
        summary_result = self._call_llm(summary_messages, llm_config)
        total_tokens += summary_result.get('total_tokens', 0)
        final_answer = summary_result.get('content', '')

        thought_chain.append({
            'position': len(thought_chain),
            'thought': '汇总执行结果',
            'tool_name': '',
            'tool_input': '',
            'tool_output': '',
            'step_type': 'summary',
        })
        self._emit_thought(on_thought, 'reasoning', '汇总执行结果...', step_type='summary')
        self._emit_thought(on_thought, 'done', final_answer, iterations=len(steps), tokens=total_tokens)

        return {
            'output': final_answer,
            'tool_calls': tool_calls_history,
            'thought_chain': thought_chain,
            'tokens': total_tokens,
            'iterations': len(steps),
        }

    def _build_plan_prompt(self, system_msg, user_msg, tools):
        """构建规划阶段的 prompt（增强：输出 JSON 格式 + 工具绑定）"""
        prompt = system_msg or '你是一个任务规划专家。'
        prompt += '\n\n你的任务是分析用户的需求，制定一个清晰的执行计划。'
        # 优先使用 JSON 格式输出（更可靠解析）
        prompt += '\n请按以下 JSON 格式输出：\n'
        prompt += '```json\n{\n  "steps": ["步骤一描述", "步骤二描述", ...]\n}\n```\n'
        prompt += '\n或者使用列表格式：\n'
        prompt += '1. 步骤一描述\n'
        prompt += '2. 步骤二描述\n'
        prompt += '...'
        if tools:
            tool_names = [t.get('name', '') for t in tools]
            prompt += f'\n\n可用工具：{", ".join(tool_names)}'
            prompt += '\n请在计划中考虑使用这些工具。'
        return prompt

    def _parse_plan(self, plan_text):
        """解析计划文本为步骤列表（增强：支持 JSON 格式）"""
        # 尝试 JSON 格式解析
        try:
            # 提取 JSON 代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', plan_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
            else:
                # 尝试直接解析
                json_start = plan_text.find('{')
                json_end = plan_text.rfind('}')
                if json_start >= 0 and json_end > json_start:
                    parsed = json.loads(plan_text[json_start:json_end + 1])
                else:
                    parsed = None
            if parsed and isinstance(parsed, dict):
                steps = parsed.get('steps', [])
                if isinstance(steps, list) and steps:
                    return [str(s).strip() for s in steps if str(s).strip()]
        except (json.JSONDecodeError, ValueError):
            pass

        # 回退到文本格式解析
        steps = []
        lines = plan_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('```'):
                continue
            # 匹配 "1. xxx" 或 "- xxx" 或 "* xxx"
            match = re.match(r'^[\d]+\.\s*(.+)$', line)
            if match:
                steps.append(match.group(1).strip())
            elif line.startswith('- ') or line.startswith('* '):
                steps.append(line[2:].strip())
        return steps if steps else [plan_text.strip()]

    def _build_step_prompt(self, system_msg, step, previous_results, tools):
        """构建步骤执行的 prompt"""
        prompt = system_msg or '你是一个任务执行专家。'
        prompt += f'\n\n当前步骤：{step}'
        if previous_results:
            prompt += '\n\n已完成步骤：'
            for i, r in enumerate(previous_results):
                prompt += f'\n{i+1}. {r["step"]} → {r["result"][:200]}'
        if tools:
            prompt += '\n\n如需调用工具，使用格式：\nAction: 工具名\nAction Input: JSON参数'
        return prompt

    def _build_summary_prompt(self, user_msg, step_results):
        """构建汇总阶段的 prompt"""
        prompt = '你是一个结果汇总专家。\n\n'
        prompt += f'原始任务：{user_msg}\n\n'
        prompt += '执行结果：\n'
        for i, r in enumerate(step_results):
            prompt += f'{i+1}. {r["step"]}\n   结果：{r["result"][:300]}\n\n'
        prompt += '请基于以上结果，给出简洁、准确的最终回答。'
        return prompt


# ============================================================
# 配置版本管理
# ============================================================

class ConfigRevisionManager:
    """Agent 配置版本管理器"""

    @staticmethod
    def save_revision(agent_id, config: dict, strategy: str = '', change_note: str = '',
                      created_by: str = None):
        """保存配置快照；created_by 存 dify_accounts.id（登录 token 里的 user_id）"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''INSERT INTO agent_config_revisions (agent_id, config_json, strategy, change_note, created_by)
                    VALUES (%s, %s, %s, %s, %s)''',
                (agent_id, json.dumps(config, ensure_ascii=False), strategy, change_note,
                 str(created_by) if created_by else None)
            )
            db.commit()
            return cur.lastrowid
        except Exception as e:
            # 以前这里静默 pass：快照一行都没写进去，前端却收到“已保存版本”，
            # 等到版本列表永远是空才发现。至少留一条日志。
            logger.warning('保存智能体配置快照失败 (agent_id=%s): %s', agent_id, str(e)[:200])
        finally:
            db.close()
        return None

    @staticmethod
    def list_revisions(agent_id: int, limit: int = 20):
        """获取配置版本列表"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''SELECT id, agent_id, config_json, strategy, change_note, created_by, created_at
                    FROM agent_config_revisions
                    WHERE agent_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s''',
                (agent_id, limit)
            )
            rows = cur.fetchall()
            for r in rows:
                if r.get('created_at'):
                    r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if r.get('config_json'):
                    try:
                        r['config'] = json.loads(r['config_json'])
                    except Exception:
                        r['config'] = {}
                    del r['config_json']
            return rows
        except Exception:
            return []
        finally:
            db.close()

    @staticmethod
    def get_revision(revision_id: int):
        """获取指定版本"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''SELECT id, agent_id, config_json, strategy, change_note, created_by, created_at
                    FROM agent_config_revisions
                    WHERE id = %s''',
                (revision_id,)
            )
            row = cur.fetchone()
            if row:
                if row.get('created_at'):
                    row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if row.get('config_json'):
                    row['config'] = json.loads(row['config_json'])
                    del row['config_json']
            return row
        except Exception:
            return None
        finally:
            db.close()

    @staticmethod
    def rollback_to_revision(agent_id: int, revision_id: int):
        """回滚到指定版本"""
        revision = ConfigRevisionManager.get_revision(revision_id)
        if not revision or revision.get('agent_id') != agent_id:
            return None
        return revision.get('config', {})


# ============================================================
# 便捷函数
# ============================================================

def execute_agent_strategy(strategy_name: str, messages: list, tools: list, context: dict, llm_config: dict, on_thought=None):
    """
    便捷函数：执行指定策略

    参数:
        strategy_name: 策略名称 (react / function_call / plan_execute)
        messages: OpenAI 格式消息列表
        tools: 工具定义列表
        context: 工作流上下文
        llm_config: LLM 配置
        on_thought: 可选的流式回调函数（每步思考时调用）

    返回:
        dict — {output, tool_calls, thought_chain, tokens, iterations}
    """
    strategy = get_strategy(strategy_name)
    return strategy.run(messages, tools, context, llm_config, on_thought=on_thought)
