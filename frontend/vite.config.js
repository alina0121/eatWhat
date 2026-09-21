import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

// uni-app 构建配置：默认产物兼容 H5 / 微信小程序 App，只需安装对应编译包
export default defineConfig({
  plugins: [uni()]
})