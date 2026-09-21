// request.js —— 底层网络封装（基于 uni.request，一套代码跑 H5 / 小程序 / App）
// 背端 FastAPI 已放开 CORS；小程序后续需配置合法域名（见 manifest / 部署说明）

// 后端基址：H5 开发默认本机 8000。切换环境改这里即可（后续可做成环境变量/配置表）
const BASE = 'http://localhost:8000'

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