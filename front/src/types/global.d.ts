/* ============ 全局类型声明 ============
 *
 * 声明通过 CDN 加载的第三方库和全局变量
 */

/** pinyin-pro 拼音库（通过 CDN 加载） */
declare const pinyin: {
  pinyin: (char: string, options?: { pattern?: string; toneType?: string }) => string[][]
} | undefined
