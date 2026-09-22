// 从 Dify 提取厂商图标并生成前端可用的 data URI 映射
const fs = require('fs');
const path = require('path');

const iconDir = path.resolve(__dirname, '../dify-1.17.1/web/app/components/base/icons/src/public/llm');

// 系统使用的 provider 映射
const providers = {
  openai: 'OpenaiSmall',
  anthropic: 'Anthropic',
  google: 'Gemini',
  deepseek: 'Deepseek',
  tongyi: 'Tongyi',
  zhipu: 'Zhipuai',
  baichuan: 'Baichuan',
  minimax: null,
  moonshot: null,
  hunyuan: null,
  doubao: null,
  baidu_qianfan: null,
};

function extractBase64Image(obj) {
  // 递归搜索所有 image 节点的 base64 数据
  if (!obj) return null;
  if (obj.name === 'image') {
    const href = obj.attributes?.['xlink:href'] || '';
    if (href.includes('base64,')) {
      return href.split('base64,')[1];
    }
  }
  for (const child of obj.children || []) {
    const result = extractBase64Image(child);
    if (result) return result;
  }
  return null;
}

function extractSvgPaths(obj) {
  const paths = [];
  function collect(node) {
    if (node.name === 'path') {
      const d = node.attributes?.d;
      const fill = node.attributes?.fill || 'currentColor';
      if (d) paths.push({ d, fill });
    }
    for (const child of node.children || []) collect(child);
  }
  for (const child of obj.children || []) collect(child);
  return paths;
}

const results = {};

for (const [provider, iconName] of Object.entries(providers)) {
  if (!iconName) continue;

  const filePath = path.join(iconDir, `${iconName}.json`);
  if (!fs.existsSync(filePath)) {
    console.log(`MISSING: ${provider} -> ${iconName}`);
    continue;
  }

  try {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const icon = data.icon || {};
    const attrs = icon.attributes || {};
    const w = attrs.width || '24';
    const h = attrs.height || '24';
    const vb = attrs.viewBox || `0 0 ${w} ${h}`;

    // 先尝试提取 base64 PNG
    const b64 = extractBase64Image(icon);
    if (b64) {
      results[provider] = `data:image/png;base64,${b64}`;
      console.log(`IMG: ${provider} (${b64.length} chars)`);
    } else if (icon.children) {
      // 构建内联 SVG
      const paths = extractSvgPaths(icon);
      const children = paths.map(p => `<path d="${p.d}" fill="${p.fill}"/>`).join('');
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="${vb}">${children}</svg>`;
      const b64Svg = Buffer.from(svg).toString('base64');
      results[provider] = `data:image/svg+xml;base64,${b64Svg}`;
      console.log(`SVG: ${provider} (${paths.length} paths)`);
    } else {
      console.log(`EMPTY: ${provider}`);
    }
  } catch (e) {
    console.error(`ERROR: ${provider}: ${e.message}`);
  }
}

// 生成 JS 文件
const output = `// 自动生成的厂商图标映射（从 Dify 1.17.1 提取）
// 用于模型页卡片图标显示

export const PROVIDER_ICONS = ${JSON.stringify(results, null, 2)};

export function getProviderIcon(providerName) {
  return PROVIDER_ICONS[providerName] || null;
}
`;

fs.writeFileSync(path.resolve(__dirname, 'src/provider_icons.js'), output, 'utf-8');
console.log(`\n已生成 src/provider_icons.js，共 ${Object.keys(results).length} 个图标`);
