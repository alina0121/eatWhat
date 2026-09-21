// main.js —— uni-app(Vue3) 应用入口（H5 / 小程序 / App 共用）
import { createSSRApp } from 'vue'
import App from './App.vue'

export function createApp() {
  const app = createSSRApp(App)
  return { app }
}