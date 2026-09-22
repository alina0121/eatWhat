// api/index.js —— 业务 API 客户端：按后端路由模块聚合，对接全 API 面
// 后端路由清单（FastAPI）：
//   /recipes  /shops  /candidates  /fridge  /diners  /tips  /records  /weights  /configs
// 派生数据（临期状态/计时elapsed/统计）由后端实时现算，前端只消费结果，不落库。
import req from '@/utils/request'

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
  inStock: () => req.get('/fridge/in_stock'),
  addStock: (data) => req.post('/fridge/in_stock', data),
  updateStock: (id, data) => req.put(`/fridge/in_stock/${id}`, data),
  delStock: (id) => req.del(`/fridge/in_stock/${id}`),
  purchase: () => req.get('/fridge/purchase'),
  addPurchase: (data) => req.post('/fridge/purchase', data),
  updatePurchase: (id, data) => req.put(`/fridge/purchase/${id}`, data),
  delPurchase: (id) => req.del(`/fridge/purchase/${id}`),
  toStock: (id) => req.post(`/fridge/purchase/${id}/to-stock`)
}

// 食材库：菜谱选食材的独立来源（与冰箱库存解耦，单独维护）
export const ingredientApi = {
  list: () => req.get('/ingredients'),
  create: (data) => req.post('/ingredients', data),
  update: (id, data) => req.put(`/ingredients/${id}`, data),
  del: (id) => req.del(`/ingredients/${id}`)
}

// 食材大类：独立维护的实体（name/icon/sort），食材库/冰箱/编菜谱动态引用
export const catApi = {
  list: () => req.get('/categories'),
  create: (data) => req.post('/categories', data),
  update: (id, data) => req.put(`/categories/${id}`, data),
  move: (id, dir) => req.post(`/categories/${id}/move`, { dir }),
  del: (id) => req.del(`/categories/${id}`)
}

// 封面图库：管理员维护的固定封面（emoji+渐变），菜谱编辑时点选，渲染用之
export const coverApi = {
  list: () => req.get('/covers'),
  create: (data) => req.post('/covers', data),
  update: (id, data) => req.put(`/covers/${id}`, data),
  move: (id, dir) => req.post(`/covers/${id}/move`, { dir }),
  del: (id) => req.del(`/covers/${id}`)
}

export const candidateApi = {
  list: () => req.get('/candidates'),
  add: (kind, refId) => req.post('/candidates', { kind, ref_id: refId }),
  remove: (id) => req.del(`/candidates/${id}`),
  timerStart: (id) => req.post(`/candidates/${id}/timer/start`),
  timerPause: (id) => req.post(`/candidates/${id}/timer/pause`),
  timerCancel: (id) => req.post(`/candidates/${id}/timer/cancel`)
}

export const dinerApi = {
  list: () => req.get('/diners'),
  create: (data) => req.post('/diners', data),
  update: (id, data) => req.put(`/diners/${id}`, data),
  updateTags: (id, tags) => req.put(`/diners/${id}/tags`, { tags }),
  del: (id) => req.del(`/diners/${id}`)
}

export const tipApi = {
  // viewer=当前用户名；admin=true 时看全部（管理员审核演示）
  list: (viewer = '', admin = false) =>
    req.get(`/tips?viewer=${encodeURIComponent(viewer)}&admin=${admin ? 1 : 0}`),
  create: (data) => req.post('/tips', data),
  update: (id, data) => req.put(`/tips/${id}`, data),
  del: (id, author) => req.del(`/tips/${id}?author=${encodeURIComponent(author)}`),
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

// 管理端：密码登录 + 公共资源统计 + 用户管理（仅公共信息，个人数据在上管理端）
export const adminApi = {
  login: (code) => req.post('/admin/login', { code }),
  stats: () => req.get('/admin/stats'),
  users: () => req.get('/admin/users'),
  createUser: (data) => req.post('/admin/users', data),
  updateUser: (id, data) => req.put(`/admin/users/${id}`, data),
  delUser: (id) => req.del(`/admin/users/${id}`)
}