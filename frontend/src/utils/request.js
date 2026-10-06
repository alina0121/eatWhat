// request.js —— 底层网络封装（基于 uni.request，一套代码跑 H5 / 小程序 / App）
// 背端 FastAPI 已放开 CORS；小程序后续需配置合法域名（见 manifest / 部署说明）

// 各端 BASE 取值不同，用 uni-app 条件编译区分：
//  - H5：相对路径 '/api'，走 Vite dev server 代理（见 vite.config.js），
//        浏览器只连当前 origin，天然无 CORS；生产构建由 Nginx 反代 /api 即可
//  - 小程序 / App：uni.request 不支持相对路径，必须绝对地址，
//        且小程序要求 HTTPS + 后台配置 request 合法域名（无代理层可用）
// 部署时只需改 MP_BASE 一行：换成已备案的 HTTPS 域名
const MP_BASE = 'https://api.example.com/api'

// #ifdef H5
const BASE = '/api'
// #endif

// #ifndef H5
const BASE = MP_BASE
// #endif

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