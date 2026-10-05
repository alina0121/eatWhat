// request.js —— 底层网络封装（基于 uni.request，一套代码跑 H5 / 小程序 / App）
// 背端 FastAPI 已放开 CORS；小程序后续需配置合法域名（见 manifest / 部署说明）

// 开发期用相对路径 + Vite dev server 代理（见 vite.config.js）：
//   前端 /api/recipes → vite 代理重写为 /recipes → 后端 8000
//   这样跨机器（如手机访问笔记本 IP）也能通——浏览器永远只连当前 origin
// 生产构建时改为全路径（如 https://xxx.com/api）
const BASE = '/api'

function req(method, path, data) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE + path,
      method,
      data,
      timeout: 10000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          // 后端错误信息统一形如 {"detail": "..."}"
          const msg = res.data && res.data.detail ? res.data.detail : `请求失败(${res.statusCode})`
          reject(new Error(msg))
        }
      },
      fail: (e) => reject(new Error(e.errMsg || '网络错误'))
    })
  })
}

export default {
  BASE,
  get: (p) => req('GET', p),
  post: (p, d) => req('POST', p, d),
  put: (p, d) => req('PUT', p, d),
  del: (p) => req('DELETE', p)
}