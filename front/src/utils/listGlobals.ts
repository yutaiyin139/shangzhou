/**
 * 列表页「内联 onclick → window 函数」的登记工具。
 *
 * 背景：工作流应用 / 我的应用 / 单智能体 / 多智能体这 4 个列表页，卡片是字符串拼出来的，
 * 卡片里 ⋮ 菜单只能写内联 onclick，也就只能调 window 上的函数。问题是 4 个页面登记的
 * 函数**同名**（confirmDelete / toggleCardMenu / openEditModal / openDebug …），
 * 而每个函数闭包里读的是自己那一份数组（apps / agents）。
 *
 * keep-alive 下 onMounted 一辈子只跑一次，于是变成“谁最后挂载谁占着 window”：
 * 从别的列表页切回工作流页时，点卡片「删除」调到的是上一个页面的闭包 ——
 * 确认框里显示的是别人的应用名，点确认又因为下标越界（或 -1）静默 return，
 * 表现就是“删不掉”；更坏的情况是下标恰好有效，删掉一个不相干的应用。
 *
 * 所以登记必须跟着“当前可见的页面”走：每个视图在 onMounted 与 onActivated 各登记一次，
 * 后激活者覆盖前者，window 上永远是正在被操作的那个页面的实现。
 */
export function registerListGlobals(fns: Record<string, unknown>): void {
  const w = window as unknown as Record<string, unknown>
  for (const name in fns) {
    w[name] = fns[name]
  }
}
