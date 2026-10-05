import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

// uni-app 构建配置：默认产物兼容 H5 / 微信小程序 App，只需安装对应编译包
export default defineConfig({
  plugins: [uni()],
  server: {
    host: true,          // 同时监听 IPv4 (0.0.0.0) + IPv6 ([::])，避免 Chrome localhost 走 IPv6 连不上
    port: 5173,
    // 开发期代理：前端 /api/* → 后端 FastAPI 8000；request.js 用相对路径 BASE='/api'
    // 这样跨机器（如手机访问笔记本 IP）也能通——浏览器永远只连 vite dev server
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, '')   // /api/recipes → /recipes
      }
    }
  }
})