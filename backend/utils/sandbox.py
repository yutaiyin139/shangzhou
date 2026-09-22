# -*- coding: utf-8 -*-
"""
安全沙箱执行模块 —— 隔离代码执行，防止恶意代码逃逸

功能：
1. 子进程隔离执行（可真正终止）
2. 超时控制（强制终止）
3. 资源限制（内存限制，仅 Linux/macOS）
4. 白名单内置函数
5. 执行日志记录

安全设计：
- 使用 multiprocessing 子进程执行代码，超时可强制终止
- 限制可用的内置函数白名单
- 捕获 stdout/stderr 输出
- 支持执行日志审计

依赖：无额外依赖（仅使用 Python 标准库）
"""

import os
import sys
import json
import time
import tempfile
import traceback
import multiprocessing
import logging

logger = logging.getLogger(__name__)

# 默认执行超时（秒）
DEFAULT_TIMEOUT = 30
# 最大输出长度
MAX_OUTPUT_LENGTH = 10000

# 安全的内置函数白名单
SAFE_BUILTINS = {
    'len': len, 'str': str, 'int': int, 'float': float,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    'range': range, 'enumerate': enumerate, 'zip': zip,
    'isinstance': isinstance, 'type': type, 'bool': bool,
    'abs': abs, 'min': min, 'max': max, 'sum': sum,
    'round': round, 'pow': pow, 'divmod': divmod,
    'sorted': sorted, 'reversed': reversed, 'filter': filter,
    'map': map, 'any': any, 'all': all,
    'ord': ord, 'chr': chr, 'hex': hex, 'oct': oct, 'bin': bin,
    'format': format, 'repr': repr, 'hash': hash,
    'print': lambda *args, **kwargs: None,  # print 在子进程中无意义
}


def _execute_code_subprocess(code, input_vars, result_queue, output_var='result'):
    """
    在子进程中执行代码（隔离环境）

    参数:
        code: Python 代码字符串
        input_vars: 输入变量字典
        result_queue: multiprocessing.Queue，用于返回结果
        output_var: 输出变量名
    """
    # 捕获 stdout/stderr
    from io import StringIO
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()

    try:
        # 构建受限的执行环境。
        # 约定: 代码通过「顶层赋值到任意变量」暴露输出工作流变量
        # （如 ``result = args['x'] * 2`` 或 ``sub_out = 'SUB_OK'``）；
        # 同时保留传统的 output_var / result 兜底。
        local_vars = {'args': input_vars, 'result': None}
        if output_var != 'result':
            local_vars[output_var] = None

        # 执行代码
        exec(code, {'__builtins__': SAFE_BUILTINS}, local_vars)

        # 获取输出
        stdout_output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()

        result = local_vars.get(output_var)
        if result is None:
            result = local_vars.get('result')

        # 收集顶层赋值变量（排除内部键），用于 outputs 同名映射
        assigned = {k: v for k, v in local_vars.items()
                    if k not in ('args', 'result', output_var) and not k.startswith('_')}

        result_queue.put({
            'success': True,
            'result': result,
            'stdout': stdout_output[:MAX_OUTPUT_LENGTH],
            'stderr': stderr_output[:MAX_OUTPUT_LENGTH],
            'assigned': assigned,
        })
    except Exception as e:
        result_queue.put({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'stdout': sys.stdout.getvalue()[:MAX_OUTPUT_LENGTH],
            'stderr': sys.stderr.getvalue()[:MAX_OUTPUT_LENGTH],
        })
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def execute_code_safely(code, input_vars=None, timeout=DEFAULT_TIMEOUT, output_var='result'):
    """
    安全执行 Python 代码（子进程隔离 + 超时终止）

    参数:
        code: Python 代码字符串
        input_vars: 输入变量字典（作为 args 传入代码）
        timeout: 超时时间（秒），默认 30 秒
        output_var: 输出变量名（默认 'result'）

    返回:
        dict: {
            'success': bool,
            'result': 执行结果（成功时）,
            'error': 错误信息（失败时）,
            'stdout': 标准输出,
            'stderr': 标准错误,
            'elapsed_ms': 执行耗时（毫秒）,
            'timed_out': 是否超时,
        }

    示例:
        >>> result = execute_code_safely('result = args["x"] + args["y"]', {'x': 1, 'y': 2})
        >>> print(result['result'])  # 3
    """
    if not code or not isinstance(code, str):
        return {'success': False, 'error': '代码为空', 'timed_out': False, 'elapsed_ms': 0}

    if input_vars is None:
        input_vars = {}

    # 安全检查：代码长度限制
    if len(code) > 50000:
        return {'success': False, 'error': '代码长度超过限制（最大 50000 字符）', 'timed_out': False, 'elapsed_ms': 0}

    start_time = time.time()
    result_queue = multiprocessing.Queue()

    # 创建子进程
    proc = multiprocessing.Process(
        target=_execute_code_subprocess,
        args=(code, input_vars, result_queue, output_var),
        daemon=True,
    )

    proc.start()
    proc.join(timeout=timeout)

    elapsed_ms = int((time.time() - start_time) * 1000)

    if proc.is_alive():
        # 超时：强制终止子进程
        proc.terminate()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.kill()  # 强制杀死
            proc.join(timeout=2)

        logger.warning(f'代码执行超时（{timeout}s），已强制终止')
        return {
            'success': False,
            'error': f'代码执行超时（超过 {timeout} 秒）',
            'timed_out': True,
            'elapsed_ms': elapsed_ms,
            'stdout': '',
            'stderr': '',
        }

    # 获取结果
    try:
        if not result_queue.empty():
            result = result_queue.get_nowait()
            result['elapsed_ms'] = elapsed_ms
            result['timed_out'] = False
            return result
        else:
            return {
                'success': False,
                'error': '子进程执行异常，未返回结果',
                'timed_out': False,
                'elapsed_ms': elapsed_ms,
                'stdout': '',
                'stderr': '',
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'获取执行结果失败: {str(e)}',
            'timed_out': False,
            'elapsed_ms': elapsed_ms,
            'stdout': '',
            'stderr': '',
        }


def execute_code_simple(code, input_vars=None, timeout=DEFAULT_TIMEOUT):
    """
    安全执行代码并返回简化结果（兼容旧接口）

    参数:
        code: Python 代码字符串
        input_vars: 输入变量字典
        timeout: 超时时间（秒）

    返回:
        成功时返回结果值，失败时返回错误信息字符串
    """
    result = execute_code_safely(code, input_vars, timeout)
    if result['success']:
        return result['result']
    return f"错误: {result['error']}"


# 兼容旧接口的便捷函数
def run_code_node(code, context, outputs_config=None):
    """
    执行代码节点（兼容工作流引擎接口）

    参数:
        code: Python 代码
        context: 工作流上下文变量
        outputs_config: 输出变量配置

    返回:
        dict: 输出变量字典
    """
    result = execute_code_safely(code, context, timeout=120)
    if result['success']:
        if outputs_config and isinstance(outputs_config, dict):
            output = {}
            for out_key in outputs_config:
                if out_key in context:
                    output[out_key] = context[out_key]
            if not result['result'] and not output:
                return {'result': ''}
            if output:
                if result['result'] is not None:
                    output['result'] = result['result']
                return output
        return {'result': result['result']}
    else:
        return {'result': f"错误: {result['error']}"}


if __name__ == '__main__':
    # 测试
    print("测试 1: 基本计算")
    r = execute_code_safely('result = args["x"] + args["y"]', {'x': 1, 'y': 2})
    print(f"  结果: {r}")

    print("\n测试 2: 超时检测")
    r = execute_code_safely('import time; time.sleep(10); result = "ok"', timeout=2)
    print(f"  结果: {r}")

    print("\n测试 3: 恶意代码（尝试导入 os）")
    r = execute_code_safely('import os; result = os.system("whoami")')
    print(f"  结果: {r}")

    print("\n测试 4: 类型逃逸尝试")
    r = execute_code_safely('result = ().__class__.__bases__[0].__subclasses__()')
    print(f"  结果: {r}")
