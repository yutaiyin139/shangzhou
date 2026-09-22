# -*- coding: utf-8 -*-
"""HTML 原型页面 → Vue 组件 批量转换脚本
规则：
- <div class="layout"> 外壳替换为 <AppShell active-key="X" main-class="Y">
- 页面内联 <style> 迁移到 <style>（全局样式，兼容 innerHTML 动态渲染；body 选择器改写为 .page-root）
- 页面内联 <script> 整体放入 onMounted；initShell 行删除
- onclick="CODE" → data-action="CODE"（根元素 click 委托 + eval 执行）
- location.href='xxx.html' → location.hash='#/xxx'；href="xxx.html" → href="#/xxx"
- fetch('http://localhost:5000 → fetch('
"""
import re, os, html as html_mod

ROOT = r'd:\qoder-workspaces\shangzhou\front\legacy'
OUT = os.path.join(r'd:\qoder-workspaces\shangzhou\front', 'src', 'views')

# 文件名 → 路由路径
PAGE_ROUTES = {
    'account-info.html': '/account-info',
    'agent-chat.html': '/agent-chat',
    'agent-config.html': '/agent-config',
    'agent-detail.html': '/agent-detail',
    'agent-logs.html': '/agent-logs',
    'agent-monitor.html': '/agent-monitor',
    'app-templates.html': '/app-templates',
    'chatflow-studio.html': '/chatflow-studio',
    'connectors.html': '/connectors',
    'functions.html': '/functions',
    'home.html': '/home',
    'knowledge-create.html': '/knowledge-create',
    'knowledge-detail.html': '/knowledge-detail',
    'knowledge-process.html': '/knowledge-process',
    'knowledge.html': '/knowledge',
    'mcp.html': '/mcp',
    'models.html': '/models',
    'multi-agent-edit.html': '/multi-agent-edit',
    'multi-agent.html': '/multi-agent',
    'my-agents.html': '/my-agents',
    'permissions.html': '/permissions',
    'roles.html': '/roles',
    'single-agent-edit.html': '/single-agent-edit',
    'single-agent.html': '/single-agent',
    'skill-detail.html': '/skill-detail',
    'skills.html': '/skills',
    'template-studio.html': '/template-studio',
    'tools.html': '/tools',
    'users.html': '/users',
    'workflow-app.html': '/workflow-app',
    'workflow-studio.html': '/workflow-studio',
}

def to_comp(name):
    return name.replace('.html', '').replace('-', '_').title().replace('_', '') + 'View'

def to_active_key(name):
    return name.replace('.html', '')

def convert(fname):
    path = os.path.join(ROOT, fname)
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    # ---- 1. 提取 <style> ----
    styles = re.findall(r'<style>(.*?)</style>', html, re.S)
    css = '\n'.join(styles)
    # 无外壳页面使用组件专属根类名，避免同名 .page-root 全局规则跨页面污染
    root_cls = fname.replace('.html', '') + '-root'
    # 编辑器型全屏页标志：原型 html,body 带 overflow:hidden（内部自滚动）
    editor_full_page = bool(re.search(r'html\s*,\s*body', css))
    # body/html,body 选择器改写为组件根类，避免影响整个应用
    # 先处理 html,body{...}，再处理独立的 body{...}（类名中的 -body 不误伤）
    css = re.sub(r'html\s*,\s*body\s*\{([^}]*)\}', lambda mo: '.' + root_cls + '{' + mo.group(1) + '}', css)
    css = re.sub(r'(?<![\w-])body\s*\{([^}]*)\}', lambda mo: '.' + root_cls + '{' + mo.group(1) + '}', css)

    # ---- 2. 提取 body 内容 ----
    m = re.search(r'<body>(.*)</body>', html, re.S)
    if not m:
        print('SKIP(no body):', fname); return
    body = m.group(1)

    # ---- 3. 提取页面脚本（最后一个无 src 的 <script>）----
    scripts = re.findall(r'<script>(.*?)</script>', body, re.S)
    js = '\n'.join(scripts)
    # 移除 body 中所有 script 块与 app.js 引用
    body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.S)
    body = re.sub(r'<script[^>]*src="[^"]*"[^>]*>\s*</script>', '', body, flags=re.S)

    # ---- 4. 提取 main 内容与外壳信息 ----
    m = re.search(r'<main class="main([^"]*)"[^>]*>(.*?)</main>', body, re.S)
    if m:
        main_class = m.group(1).strip()
        content = m.group(2).strip()
        # main 之后的剩余 HTML（模态框等，位于 layout 外壳外）
        tail = body[m.end():]
        tail = re.sub(r'^\s*(</div>\s*){1,4}', '', tail)
        if tail.strip():
            content += '\n' + tail.strip()
        shell = True
    else:
        # 编辑器类全屏页面：无标准外壳，body 整体作为内容
        main_class = ''
        content = body.strip()
        shell = False

    # ---- 5. 外壳剩余标签清理（topbar/sidebar 已在 main 匹配外）----
    # main 外的 <div class="layout"> 等残留不再处理，模板只取 main 内容

    # ---- 6. 链接与跳转 hash 化（支持空格与 query 参数）----
    def route_for(html_path):
        if html_path in PAGE_ROUTES:
            return PAGE_ROUTES[html_path]
        if html_path == 'index.html':
            return '/login'
        return '/' + html_path.replace('.html', '')

    # JS 内 location.href = 'xxx.html...'（允许空格）
    js = re.sub(
        r"location\.href\s*=\s*'([A-Za-z0-9\-]+\.html)([^']*)'",
        lambda mo: "location.hash = '" + route_for(mo.group(1)) + mo.group(2) + "'",
        js
    )
    js = re.sub(
        r'location\.href\s*=\s*"([A-Za-z0-9\-]+\.html)([^"]*)"',
        lambda mo: 'location.hash = "' + route_for(mo.group(1)) + mo.group(2) + '"',
        js
    )
    # 模板内 onclick 中的 location.href
    content = re.sub(
        r'onclick="location\.href\s*=\s*\'([A-Za-z0-9\-]+\.html)([^\']*)\'"',
        lambda mo: "data-action=\"location.hash = '" + route_for(mo.group(1)) + mo.group(2) + "'\"",
        content
    )
    # 模板内 href="xxx.html..." → href="#/xxx..."
    content = re.sub(
        r'href="([A-Za-z0-9\-]+\.html)([^"]*)"',
        lambda mo: 'href="#' + route_for(mo.group(1)) + mo.group(2) + '"',
        content
    )
    content = re.sub(
        r"href='([A-Za-z0-9\-]+\.html)([^']*)'",
        lambda mo: "href='#" + route_for(mo.group(1)) + mo.group(2) + "'",
        content
    )

    # ---- 7. fetch 地址代理化 ----
    js = js.replace("'http://localhost:5000", "'")
    js = js.replace('"http://localhost:5000', '"')
    content = content.replace("'http://localhost:5000", "'")
    content = content.replace('"http://localhost:5000', '"')

    # ---- 8. 删除 initShell 调用行 ----
    js = re.sub(r'^\s*initShell\([^)]*\);\s*$', '', js, flags=re.M)

    # ---- 9. onclick → data-action ----
    def fix_onclick(mo):
        code = mo.group(1).strip()
        if not code or code.startswith('return') or code.startswith('javascript'):
            return ''
        code = re.sub(r';\s*return\s+false\s*;?$', '', code)
        code = re.sub(r'^\s*return\s+false\s*;?\s*', '', code)
        if not code.strip():
            return ''
        return ' data-action="' + html_mod.escape(code, quote=True) + '"'
    content = re.sub(r'\sonclick="([^"]*)"', fix_onclick, content)

    # ---- 10. 生成 Vue 组件 ----
    comp = to_comp(fname)
    active_key = to_active_key(fname)
    if shell:
        main_attr = ' main-class="' + main_class + '"' if main_class else ''
        template = (
            '<template>\n'
            '  <AppShell id="page-root" active-key="' + active_key + '"' + main_attr + '>\n'
            + re.sub(r'^', '    ', content, flags=re.M) + '\n'
            '  </AppShell>\n'
            '</template>\n'
        )
    else:
        template = (
            '<template>\n'
            '  <div id="page-root" class="page-root ' + root_cls + '">\n'
            + re.sub(r'^', '    ', content, flags=re.M) + '\n'
            '  </div>\n'
            '</template>\n'
        )
    script = (
        '<script setup>\n'
        'import { onMounted } from \'vue\'\n'
        'import AppShell from \'../components/AppShell.vue\'\n'
        'import { toast, openModal, closeModal } from \'../utils/global\'\n'
        '\n'
        '/* 根元素点击委托：data-action 属性中的代码在 onMounted 闭包内执行 */\n'
        'function onRootClick(e){\n'
        '  var el = e.target && e.target.closest ? e.target.closest(\'[data-action]\') : null;\n'
        '  if (!el) return;\n'
        '  var code = el.getAttribute(\'data-action\');\n'
        '  if (!code) return;\n'
        '  try { eval(code); } catch(err){ console.error(\'[page action]\', err); }\n'
        '}\n'
        '\n'
        'onMounted(function(){\n'
        '  var root = document.querySelector(\'#page-root\');\n'
        '  if (root) root.addEventListener(\'click\', onRootClick);\n'
        + re.sub(r'^', '  ', js.rstrip(), flags=re.M) + '\n'
        '})\n'
        '</script>\n'
    )
    style = '<style>\n' + css.strip() + '\n</style>\n'

    # 无外壳的全屏页面：补充根布局样式（绑定组件专属类，防止跨页污染）
    # 编辑器型（html,body 有 overflow:hidden）：固定视口高度+内部滚动
    # 内容型（仅 body{background:#fff}）：自然滚动+白底
    if not shell:
        if editor_full_page:
            extra = '.' + root_cls + '{ height:100vh; display:flex; flex-direction:column; overflow:hidden; }\n'
        else:
            extra = '.' + root_cls + '{ min-height:100vh; }\n'
        style = style.replace('</style>', extra + '</style>', 1)

    out = os.path.join(OUT, comp + '.vue')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(template + script + style)
    print('OK:', fname, '->', comp + '.vue', '(route:', PAGE_ROUTES.get(fname, '/') + ')')

def main():
    os.makedirs(OUT, exist_ok=True)
    # 已手工精细化转换的页面跳过
    skip = {'home.html', 'models.html'}
    for fname in PAGE_ROUTES:
        if fname in skip:
            continue
        convert(fname)

if __name__ == '__main__':
    main()
