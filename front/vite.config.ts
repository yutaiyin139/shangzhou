import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// 熵舟·智能体工作台 前端构建配置
export default defineConfig({
  plugins: [vue()],
  // 统一配置源：读取项目根目录的 .env（与后端共用一份）。
  // 安全：Vite 只会将 `VITE_` 前缀的变量注入前端产物，根 .env 中的
  // DB_PASSWORD / JWT_SECRET / ENCRYPTION_KEY 等无此前缀，不会泄露到浏览器包内。
  envDir: path.resolve(__dirname, '..'),
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    // 开发环境代理：/api 请求转发到 Flask 后端
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    chunkSizeWarningLimit: 1024
  }
})
