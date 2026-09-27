# -*- coding: utf-8 -*-
"""让 pytest 无论从仓库根、backend/ 还是 backend/tests/ 启动都能导入被测模块。

历史坑：多数测试脚本自己写了 sys.path.insert(0, '.')，这种相对路径依赖当前工作目录，
导致同一份用例换个目录启动就 ModuleNotFoundError: No module named 'config'。
本文件把 backend/ 与 tests/ 两个目录无条件加入 sys.path，脚本内的相对写法已改为绝对路径。

运行方式说明：
  - unittest 风格的文件（e2e_model_provider_check.py 等）：pytest 与 python 直跑都可以；
  - 顶层语句式的自检脚本（e2e_keyword_check.py 等）设计为 `python tests/xxx.py` 直跑，
    它们在被 pytest 收集时会立即执行，属于预期行为，不要把它们当常规断言用例看。
"""
import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_TESTS_DIR)

for _p in (_BACKEND_DIR, _TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
