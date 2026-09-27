# -*- coding: utf-8 -*-
"""跨模块引用一致性守卫。

动机：workflow_runner 拆分后留下多例"函数内 from X import name，但 name 已不在 X"的死引用。
这类问题 py_compile/vue-tsc/导入期都看不见，只有真实调用那一次才 500；已确认的第一例是
POST /api/workflows/runs/<id>/stop（导入不存在的 _cancel_workflow_task）。

本用例把全仓 `from <module> import <name>` 真解析一遍：出现新的死引用即失败；
下方白名单是已知待修的历史欠账，修掉一条就请从名单里删一条（名单里的条目若已消失也会提醒）。
"""
import io
import os
import re
import sys
import unittest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

SKIP_DIRS = {'venv_libs', '__pycache__', 'logs', 'cache', 'data', '.pytest_cache'}

# 已知历史欠账：'<被导入模块>.<名字>' -> 主要受影响功能（修好后删除对应条目）
# 2026-09 已将拆分遗留的 6 条全部修完，名单保持为空：新出现的死引用一律失败。
KNOWN_DEAD_IMPORTS = {
}

_PAREN = re.compile(r'^\s*from\s+([A-Za-z_][\w\.]*)\s+import\s*\(\s*([^)]*)\)', re.M | re.S)
_PLAIN = re.compile(r'^\s*from\s+([A-Za-z_][\w\.]*)\s+import\s+([^\n(#]*)$', re.M)


def _collect_references():
    """返回 [(文件, 行号, 模块, 名字)]，只收录能成功 import 的模块（模块自身坏掉另说）。"""
    refs = []
    for dirpath, dirnames, filenames in os.walk(BACKEND):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith('.py'):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, BACKEND)
            src = io.open(path, encoding='utf-8', errors='replace').read()
            blocks = []
            for m in _PAREN.finditer(src):
                blocks.append((m.group(1), m.group(2), m.start()))
            for m in _PLAIN.finditer(src):
                blocks.append((m.group(1), m.group(2), m.start()))
            for mod, body, pos in blocks:
                if mod.startswith('routes.'):
                    continue          # 路由包按包名动态注册，另行核对
                # 多行 import 里可能夹着注释行，先剔除再切名字，否则注释会被当成符号名
                cleaned = re.sub(r'#[^\n]*', '', body)
                names = [n.strip().split(' as ')[0].strip()
                         for n in cleaned.replace('\n', ' ').split(',')]
                for name in names:
                    if name and not name.startswith('*'):
                        refs.append((rel, src[:pos].count('\n') + 1, mod, name))
    return refs


class ImportConsistencyTest(unittest.TestCase):

    def test_no_new_dead_cross_module_references(self):
        """全仓不得出现解析不到的跨模块名字（白名单外的新死引用一律失败）"""
        import importlib
        missing = {}
        for rel, line, mod, name in _collect_references():
            try:
                imported = importlib.import_module(mod)
            except Exception:
                continue          # 模块本身导入失败由其它用例/启动日志负责
            if getattr(imported, name, None) is None:
                key = '%s.%s' % (mod, name)
                missing.setdefault(key, []).append('%s:%s' % (rel, line))

        new_dead = {k: v for k, v in missing.items() if k not in KNOWN_DEAD_IMPORTS}
        self.assertEqual(
            [], sorted(new_dead),
            '出现新的跨模块死引用（只在真实调用时才 500）：%s' % new_dead)

        fixed = [k for k in KNOWN_DEAD_IMPORTS if k not in missing]
        if fixed:
            print('\n  [提示] 这些历史欠账已修好，请从 KNOWN_DEAD_IMPORTS 移除：%s' % ', '.join(fixed))


if __name__ == '__main__':
    unittest.main(verbosity=2)
