// api/index.js —— 业务 API 客户端：按后端路由模块聚合，对接全 API 面
// 后端路由清单（FastAPI）：
//   /recipes  /shops  /candidates  /fridge  /tips  /records  /weights  /configs
// 派生数据（临期状态/计时elapsed/统计）由后端实时现算，前端只消费结果，不落库。
// 多用户隔离：身份完全由请求头 Authorization Bearer token 决定（后端 get_optional_user 解析）；
//   下面 URL 上的 ?user=N 是历史遗留，后端已不再读取，保留只为不改动各页调用点。
//   未登录（无 token）时后端按 user=0 游客处理，各页天然空态，不再回退 1 号账号。
import req from '@/utils/request'

/** 当前用户 id（localStorage 无值时为 0=未登录；0 不代表任何真实账号） */
export const getCurUser = () => {
  try {
    const v = uni.getStorageSync('curUser')
    const n = Number(v)
    return Number.isFinite(n) && n > 0 ? n : 0
  } catch (e) { return 0 }
}

export const recipeApi = {
  list: (source) => req.get(`/recipes${source ? `?source=${source}` : ''}`),
  get: (id) => req.get(`/recipes/${id}`),
  create: (data) => req.post('/recipes', data),
  update: (id, data) => req.put(`/recipes/${id}`, data),
  del: (id) => req.del(`/recipes/${id}`),
  copyToMine: (id) => req.post(`/recipes/${id}/copy-to-mine`)
}

export const shopApi = {
  list: () => req.get('/shops'),
  get: (id) => req.get(`/shops/${id}`),
  create: (data) => req.post('/shops', data),
  update: (id, data) => req.put(`/shops/${id}`, data),
  del: (id) => req.del(`/shops/${id}`)
}

export const fridgeApi = {
  inStock: (user = getCurUser()) => req.get(`/fridge/in_stock?user=${user}`),
  addStock: (data, user = getCurUser()) => req.post(`/fridge/in_stock?user=${user}`, data),
  updateStock: (id, data, user = getCurUser()) => req.put(`/fridge/in_stock/${id}?user=${user}`, data),
  delStock: (id, user = getCurUser()) => req.del(`/fridge/in_stock/${id}?user=${user}`),
  purchase: (user = getCurUser()) => req.get(`/fridge/purchase?user=${user}`),
  addPurchase: (data, user = getCurUser()) => req.post(`/fridge/purchase?user=${user}`, data),
  updatePurchase: (id, data, user = getCurUser()) => req.put(`/fridge/purchase/${id}?user=${user}`, data),
  delPurchase: (id, user = getCurUser()) => req.del(`/fridge/purchase/${id}?user=${user}`),
  toStock: (id, user = getCurUser()) => req.post(`/fridge/purchase/${id}/to-stock?user=${user}`)
}

// 食材库：双层模型——公共（scope=public）+ 用户私有补录（scope=user）
// 默认 list 返回合并视图（public + 自己的 user）；public_only=true 管理端只看公共
export const ingredientApi = {
  list: (user = getCurUser(), publicOnly = false) =>
    req.get(`/ingredients?user=${user}${publicOnly ? '&public_only=1' : ''}`),
  create: (data, user = getCurUser(), isPublic = false) =>
    req.post(`/ingredients?user=${user}${isPublic ? '&public=1' : ''}`, data),
  update: (id, data, user = getCurUser(), admin = false) =>
    req.put(`/ingredients/${id}?user=${user}${admin ? '&admin=1' : ''}`, data),
  del: (id, user = getCurUser(), admin = false) =>
    req.del(`/ingredients/${id}?user=${user}${admin ? '&admin=1' : ''}`)
}

// 食材大类：同 ingredients 双层模型
export const catApi = {
  list: (user = getCurUser(), publicOnly = false) =>
    req.get(`/categories?user=${user}${publicOnly ? '&public_only=1' : ''}`),
  create: (data, user = getCurUser(), isPublic = false) =>
    req.post(`/categories?user=${user}${isPublic ? '&public=1' : ''}`, data),
  update: (id, data, user = getCurUser(), admin = false) =>
    req.put(`/categories/${id}?user=${user}${admin ? '&admin=1' : ''}`, data),
  move: (id, dir, user = getCurUser(), admin = false) =>
    req.post(`/categories/${id}/move?user=${user}${admin ? '&admin=1' : ''}`, { dir }),
  del: (id, user = getCurUser(), admin = false) =>
    req.del(`/categories/${id}?user=${user}${admin ? '&admin=1' : ''}`)
}

// 封面图库：管理员维护的固定封面（emoji+渐变），菜谱编辑时点选，渲染用之

// 吃这些候选：space=mine 个人池 / family 家庭共享池（列表、加候选都带空间；
// 计时与移除按候选 id 操作，家庭池内成员都可操作，归属由后端判定）
export const candidateApi = {
  list: (space = 'mine') => req.get(`/candidates?space=${space}`),
  add: (kind, refId, user = getCurUser(), space = 'mine') =>
    req.post(`/candidates?user=${user}`, { kind, ref_id: refId, space }),
  remove: (id, user = getCurUser()) => req.del(`/candidates/${id}?user=${user}`),
  timerStart: (id) => req.post(`/candidates/${id}/timer/start`),
  timerPause: (id) => req.post(`/candidates/${id}/timer/pause`),
  timerCancel: (id) => req.post(`/candidates/${id}/timer/cancel`)
}

// 家庭空间：创建/凭 6 位 ID 加入/我的家庭/退出（创建者退出=解散）
export const familyApi = {
  mine: () => req.get('/families/mine'),
  create: (name) => req.post('/families', { name }),
  join: (code) => req.post('/families/join', { code }),
  leave: () => req.post('/families/leave')
}

export const tasteApi = {
  list: () => req.get('/taste-tags'),
  create: (name) => req.post('/taste-tags', { name }),
  update: (id, name) => req.put(`/taste-tags/${id}`, { name }),
  del: (id) => req.del(`/taste-tags/${id}`),
  reorder: (ids) => req.put('/taste-tags/reorder', ids)
}

export const tipApi = {
  // 归属由后端按 token 判定：普通列表自动只带「自己的 + 他人已公开通过的」
  // admin=true 时返回全部（含他人未审核/私密），供管理端审核用
  list: (admin = false) => req.get(`/tips?admin=${admin ? 1 : 0}`),
  create: (data) => req.post('/tips', data),
  update: (id, data) => req.put(`/tips/${id}`, data),
  del: (id) => req.del(`/tips/${id}`),
  approve: (id) => req.post(`/tips/${id}/approve`),
  reject: (id) => req.post(`/tips/${id}/reject`)
}

export const recordApi = {
  list: (start, end, date) => {
    if (date) return req.get(`/records?date=${date}`)
    if (start && end) return req.get(`/records?start=${start}&end=${end}`)
    return req.get('/records')
  },
  calendar: () => req.get('/records/calendar'),
  create: (data) => req.post('/records', data),
  update: (id, data) => req.put(`/records/${id}`, data),
  del: (id) => req.del(`/records/${id}`)
}

export const weightApi = {
  list: () => req.get('/weights'),
  create: (data) => req.post('/weights', data),
  update: (id, data) => req.put(`/weights/${id}`, data),
  del: (id) => req.del(`/weights/${id}`)
}

export const configApi = {
  list: () => req.get('/configs'),
  get: (key) => req.get(`/configs/${key}`),
  set: (key, value) => req.put(`/configs/${key}`, { value })
}

// 会员/支付：套餐与会员态（/payments/plans）、mock 或虚拟支付下单、订单列表
export const paymentApi = {
  plans: () => req.get('/payments/plans'),
  order: (planId, env = 0) => req.post('/payments/order', { plan_id: planId, env }),
  orderStatus: (no) => req.get(`/payments/order/${no}/status`),
  orders: () => req.get('/payments/orders')
}

// 管理端：密码登录 + 公共资源统计 + 用户管理（仅公共信息，个人数据在上管理端）
export const adminApi = {
  login: (code) => req.post('/admin/login', { code }),
  stats: () => req.get('/admin/stats'),
  users: () => req.get('/admin/users'),
  createUser: (data) => req.post('/admin/users', data),
  updateUser: (id, data) => req.put(`/admin/users/${id}`, data),
  delUser: (id) => req.del(`/admin/users/${id}`),
  // 会员管理：总览（KPI+会员+订单）、手工赠送/取消
  vip: () => req.get('/admin/vip'),
  grantVip: (user_id, days) => req.post('/admin/vip/grant', { user_id, days }),
  revokeVip: (user_id) => req.post('/admin/vip/revoke', { user_id })
}

// 用户端「我的数据」总览：个人数据聚合（仅用户端使用，管理端不做个人数据）
export const mineApi = {
  stats: () => req.get('/mine/stats')
}
// 登录体系：微信 code / 邮箱验证码 / 绑定 / 注销
export const authApi = {
  // 微信小程序登录（wx.login code 换 token）
  // 没配 mp_appid/secret 时 body 会带 mock_openid（storage 里的稳定 uuid），后端优先用它
  login: (code, nickname, avatar) => {
    const body = { code, nickname, avatar }
    // #ifdef MP-WEIXIN
    const devOpenid = uni.getStorageSync('eat_dev_mock_openid')
    if (devOpenid) body.mock_openid = devOpenid
    // #endif
    return req.post('/auth/login', body)
  },
  // 邮箱验证码登录 / 自动注册（H5/App 端）
  loginEmail: (email, code, nickname) => req.post('/auth/login-email', { email, code, nickname }),
  // 发邮箱验证码（purpose: login | bind | reset）
  sendEmailCode: (email, purpose = 'login') => req.post('/auth/send-email-code', { email, purpose }),
  // 当前用户
  me: () => req.get('/auth/me'),
  updateProfile: (data) => req.put('/auth/profile', data),
  // 绑定 / 解绑邮箱
  bindEmail: (email, code) => req.post('/auth/bind-email', { email, code }),
  unbindEmail: () => req.post('/auth/unbind-email'),
  // 注销账户（物理删除所有数据）
  deleteMe: () => req.del('/auth/me'),
}
