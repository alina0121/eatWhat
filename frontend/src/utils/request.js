// request.js —— 底层网络封装（基于 uni.request，一套代码跑 H5 / 小程序 / App）
// 背端 FastAPI 已放开 CORS；小程序后续需配置合法域名（见 manifest / 部署说明）
//
// 鉴权：所有请求自动从 storage 读 token 带 Authorization: Bearer header
//       后端用 get_optional_user 宽松鉴权——有 token 解出真实 user_id，没有走默认 1
//       小程序启动时 wx.login → /auth/login → 拿 token 存 storage
//       H5 / App 端暂未接 wx.login，token 为空 → 宽松模式 user_id=1，和之前完全兼容

const MP_BASE = 'http://192.168.31.113:8000'

// #ifdef H5
const BASE = '/api'
// #endif

// #ifndef H5
const BASE = MP_BASE
// #endif

const TOKEN_KEY = 'eat_token'
const USER_KEY = 'eat_user_info'

// 防并发登录锁（小程序可能多次触发 wx.login）
let _loginPromise = null

// 小程序登录流程：wx.login 拿 code → /auth/login 换 token → 存 storage
async function ensureLogin() {
  const token = uni.getStorageSync(TOKEN_KEY)
  if (token) return token

  if (_loginPromise) return _loginPromise  // 已在登录中，等结果

  _loginPromise = (async () => {
    // #ifdef MP-WEIXIN
    try {
      const { code } = await new Promise((res, rej) => {
        uni.login({ success: res, fail: rej })
      })
      const resp = await new Promise((res, rej) => {
        uni.request({
          url: BASE + '/auth/login',
          method: 'POST',
          data: { code },
          timeout: 5000,
          success: res,
          fail: rej,
        })
      })
      if (resp.statusCode === 200 && resp.data.token) {
        uni.setStorageSync(TOKEN_KEY, resp.data.token)
        uni.setStorageSync(USER_KEY, resp.data)
        return resp.data.token
      }
    } catch (e) {
      console.warn('[auth] wx.login failed:', e)
    }
    // #endif
    return ''  // H5 或失败 → 宽松模式，user_id=1
  })()

  const tok = await _loginPromise
  _loginPromise = null
  return tok
}

function req(method, path, data) {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync(TOKEN_KEY)
    const header = { 'Content-Type': 'application/json' }
    if (token) header['Authorization'] = 'Bearer ' + token

    uni.request({
      url: BASE + path,
      method,
      data,
      header,
      timeout: 10000,
      success: (res) => {
        // token 过期（401）→ 清掉 token，下次请求会自动重新登录
        if (res.statusCode === 401) {
          uni.removeStorageSync(TOKEN_KEY)
          uni.removeStorageSync(USER_KEY)
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const msg = res.data && res.data.detail ? res.data.detail : `请求失败(${res.statusCode})`
          reject(new Error(msg))
        }
      },
      fail: (e) => reject(new Error(e.errMsg || '网络错误'))
    })
  })
}

// 应用启动时预登录一次（小程序端），尽早拿到 token
// #ifdef MP-WEIXIN
ensureLogin()
// #endif

export default {
  BASE,
  TOKEN_KEY,
  USER_KEY,
  ensureLogin,          // 暴露给 App.vue 用
  get: (p) => req('GET', p),
  post: (p, d) => req('POST', p, d),
  put: (p, d) => req('PUT', p, d),
  del: (p) => req('DELETE', p)
}
