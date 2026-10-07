// request.js —— 底层网络封装（基于 uni.request，一套代码跑 H5 / 小程序 / App）
// 背端 FastAPI 已放开 CORS；小程序后续需配置合法域名（见 manifest / 部署说明）
//
// 鉴权：所有请求自动从 storage 读 token 带 Authorization: Bearer header
//       后端读接口用 get_optional_user 宽松鉴权（有 token 解真实 user_id，没有=游客 0）；
//       写接口用 get_write_user 严格鉴权（未登录一律 401，见下）
//       H5 / App 端走邮箱验证码登录（登录页），小程序端启动即静默 wx.login 登录
//
// 未登录不能写：非 GET 请求被 401 时，这里统一提示「请先登录」并跳登录页，
//       避免各页自己处理导致「点了没反应」。

const MP_BASE = 'http://192.168.31.113:8000'

// #ifdef H5
const BASE = '/api'
// #endif

// #ifndef H5
const BASE = MP_BASE
// #endif

const TOKEN_KEY = 'eat_token'
const USER_KEY = 'eat_user_info'
// 管理台令牌（PC 管理端专用）：与用户 token 并存、互不影响，写接口靠它放行管理台
const ADMIN_TOKEN_KEY = 'eat_admin_token'
// 用户主动退出登录的标记：置位后小程序端不再自动静默登录（要写操作时去登录页手动登录）
const LOGOUT_FLAG = 'eat_logout'
const LOGIN_PAGE = '/pages/login/login'

// 防并发登录锁（小程序可能多次触发 wx.login）
let _loginPromise = null
// 防重复跳登录页
let _redirecting = false

// 小程序登录流程：wx.login 拿 code → /auth/login 换 token → 存 storage
async function ensureLogin() {
  const token = uni.getStorageSync(TOKEN_KEY)
  if (token) return token
  // 用户主动退出过 → 不再自动登录，等他去登录页重新登录
  if (uni.getStorageSync(LOGOUT_FLAG)) return ''

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
        // 同步用户 id / 昵称：各页（getCurUser / 「我的」昵称）都读这两个键
        uni.setStorageSync('curUser', resp.data.user_id)
        if (resp.data.nickname) uni.setStorageSync('eat_user', resp.data.nickname)
        return resp.data.token
      }
    } catch (e) {
      console.warn('[auth] wx.login failed:', e)
    }
    // #endif
    return ''  // H5 / 失败 → 未登录态（写操作会被后端 401，前端再引导登录）
  })()

  const tok = await _loginPromise
  _loginPromise = null
  return tok
}

// 未登录/登录过期时引导去登录页（写操作被拒时调用）
function redirectToLogin() {
  if (_redirecting) return
  const pages = getCurrentPages()
  const cur = pages.length ? (pages[pages.length - 1].route || '') : ''
  if (cur.indexOf('pages/login/login') >= 0) return  // 已经在登录页了
  _redirecting = true
  setTimeout(() => { _redirecting = false }, 1500)
  uni.navigateTo({ url: LOGIN_PAGE, fail: () => uni.reLaunch({ url: LOGIN_PAGE }) })
}

function req(method, path, data) {
  return new Promise(async (resolve, reject) => {
    // 小程序端：没 token 先确保登录（静默 wx.login），避免写操作因未登录被 401
    // #ifdef MP-WEIXIN
    if (!uni.getStorageSync(TOKEN_KEY)) {
      try { await ensureLogin() } catch (e) {}
    }
    // #endif

    const token = uni.getStorageSync(TOKEN_KEY)
    const header = { 'Content-Type': 'application/json' }
    if (token) header['Authorization'] = 'Bearer ' + token
    // 管理台令牌：PC 管理端登录后与会话并存，写接口靠它放行
    const adminToken = uni.getStorageSync(ADMIN_TOKEN_KEY)
    if (adminToken) header['X-Admin-Token'] = adminToken

    uni.request({
      url: BASE + path,
      method,
      data,
      header,
      timeout: 10000,
      success: (res) => {
        // token 过期/未登录（401）→ 清掉失效 token
        if (res.statusCode === 401) {
          uni.removeStorageSync(TOKEN_KEY)
          uni.removeStorageSync(USER_KEY)
          // 写操作（非 GET）被拒 → 明确提示并引导登录；管理台会话不跳用户登录页
          if (method !== 'GET' && uni.getStorageSync('eat_admin') !== '1') {
            uni.showToast({ title: '请先登录', icon: 'none' })
            redirectToLogin()
          }
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
  ADMIN_TOKEN_KEY,
  LOGOUT_FLAG,
  ensureLogin,          // 暴露给 App.vue / 登录页用
  get: (p) => req('GET', p),
  post: (p, d) => req('POST', p, d),
  put: (p, d) => req('PUT', p, d),
  del: (p) => req('DELETE', p)
}
