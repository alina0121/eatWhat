<!-- mine.vue —— 我的页（对齐「第一版 UI」p-me）
  结构：资料头（头像+昵称+副标题，点击弹账号弹窗）→ 统计条(本周做了多少顿 / 我的菜谱 / 收藏餐厅)
        → 干饭成员(各自口味偏好维护) → 功能菜单行(图标 + 标题 + 副标题 + ›)
  注：邮箱绑定 / 退出登录 / 注销账户已归拢到 account-settings 账户设置页
-->
<template>
  <view class="tab-page">
    <view class="page-header">
      <text class="page-title">我的</text>
    </view>

    <scroll-view class="tab-scroll" scroll-y>
      <!-- 资料头 -->
      <view class="section">
        <!-- 点整行打开「账号」弹窗（未登录）；已登录直接进「账户设置」 -->
        <view class="pro" @tap="openAccount">
          <view class="ava"><text class="ava-em">{{ userAvatar || curName.slice(0, 1) }}</text></view>
          <view class="pro-c">
            <view class="pro-nm">
              <text class="pname">{{ curName }}</text>
              <!-- 仅当后端返回 role=admin 才显示；eat_admin 只是管理台口令会话标记，不代表账号身份 -->
              <text class="u-role" v-if="userRole === 'admin'">管理员</text>
            </view>
            <text class="pmail">一人食 · 主打快手菜</text>
          </view>
          <text class="newlink">{{ isLogin ? '账号' : '去登录' }}</text>
        </view>
      </view>

      <!-- 统计条 -->
      <view class="section">
        <view class="stat-bar">
          <view class="sc" @tap="nav('/pages/mine-records/mine-records')">
            <text class="st-num">{{ weekCount }}</text><text class="st-lab">本周做了多少顿</text>
          </view>
          <view class="sc" @tap="nav('/pages/recipe/recipe')">
            <text class="st-num">{{ myRecipes }}</text><text class="st-lab">我的菜谱</text>
          </view>
          <view class="sc" @tap="nav('/pages/shop/shop')">
            <text class="st-num">{{ shopCount }}</text><text class="st-lab">收藏餐厅</text>
          </view>
        </view>
      </view>

      <!-- 干饭成员 -->
      <view class="section">
        <view class="sec-head">
          <text class="sec-title">干饭成员</text>
          <text class="newlink" @tap="addDiner">＋ 成员</text>
        </view>
        <view class="card row" v-for="d in diners" :key="d.id">
          <view class="row-top">
            <text class="name">{{ d.name }}</text>
            <text class="sp"></text>
            <text class="op" @tap="editDiner(d)">口味</text>
            <text class="op danger" @tap="delDiner(d)">✕</text>
          </view>
          <view class="row-bottom" v-if="d.tags && d.tags.length">
            <text class="t-pill" v-for="t in d.tags" :key="t">{{ t }}</text>
          </view>
        </view>
      </view>

      <!-- 功能菜单 -->
      <view class="section">
        <view class="menu">
          <view class="mrow" @tap="nav('/pages/mine-tastes/mine-tastes')">
            <text class="ic">🏷️</text><view class="m1"><text class="mt">口味标签</text><text class="ms">菜谱筛选 · 成员偏好 · 推荐</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-ingredients/mine-ingredients')">
            <text class="ic">🧺</text><view class="m1"><text class="mt">食材库</text><text class="ms">菜谱可选食材 · 独立维护</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-ref/mine-ref')">
            <text class="ic">📚</text><view class="m1"><text class="mt">参考菜谱</text><text class="ms">管理员精选 · 可加入吃这些或我的菜谱</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-tips/mine-tips')">
            <text class="ic">👨‍🍳</text><view class="m1"><text class="mt">厨房技巧</text><text class="ms">大家的技巧 · 新增/修改需审核</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-records/mine-records')">
            <text class="ic">📋</text><view class="m1"><text class="mt">饮食记录</text><text class="ms">日历 · 统计 · 去重</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-weight/mine-weight')">
            <text class="ic">⚖️</text><view class="m1"><text class="mt">体重记录</text><text class="ms">曲线图 · 历史数据维护</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-data/mine-data')">
            <text class="ic">📊</text><view class="m1"><text class="mt">我的数据</text><text class="ms">计数 · 本月干饭 · 体重趋势</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="goAccountSettings">
            <text class="ic">⚙️</text><view class="m1"><text class="mt">账户设置</text><text class="ms">邮箱绑定 · 退出登录 · 注销账户</text></view><text class="ar">›</text>
          </view>
          <!-- #ifdef H5 -->
          <!-- 管理端页面仅 H5 存在（见 pages.json 条件编译），故入口也只在 H5 渲染 -->
          <view class="mrow" v-if="isPc" @tap="nav('/pages/admin/admin')">
            <text class="ic">🖥️</text><view class="m1"><text class="mt">管理端（PC）</text><text class="ms">审核 · 图库 · 食材 · 餐厅 · 配置</text></view><text class="ar">›</text>
          </view>
          <!-- #endif -->
        </view>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <custom-tab current="mine" />

    <!-- 居中弹窗（自绘遮罩，兼容 H5/App/小程序）
     注释：uni.showModal 的 editable 在 H5 不支持且无法自定义样式，故用自定义弹窗承载输入。 -->
    <view class="mask" v-if="form.show" @tap="form.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">{{ form.title }}</text>
        <!-- tags 模式：chip 点选 -->
        <template v-if="form.mode === 'tags'">
          <view class="tag-grid">
            <view v-for="t in allTags" :key="t" class="t-chip" :class="{ on: tagSel.includes(t) }" @tap="toggleTag(t)">{{ t }}</view>
          </view>
          <text class="d-sub">已选 {{ tagSel.length }} 项</text>
        </template>
        <!-- 其他模式：input -->
        <template v-else>
          <input v-model="form.val" :placeholder="form.hint" class="dfi" :focus="form.show" />
        </template>
        <view class="d-btns">
          <button class="pbtn ghost" @tap="form.show = false">取消</button>
          <button class="pbtn" @tap="saveForm">{{ form.mode === 'tags' ? '保存口味' : '确定' }}</button>
        </view>
      </view>
    </view>

    <!-- 账号弹窗：仅未登录时弹出（已登录点资料头直接进「账户设置」页） -->
    <view class="mask" v-if="accountDialog.show" @tap="accountDialog.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">账号</text>
        <text class="d-sub">还没登录 · 登录后菜谱 / 冰箱 / 干饭记录可跨端带走</text>
        <view class="d-btns">
          <button class="pbtn ghost" @tap="accountDialog.show = false">关闭</button>
          <button class="pbtn" @tap="accountDialog.show = false; goLogin()">去登录</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { dinerApi, recordApi, recipeApi, shopApi, tasteApi, authApi } from '@/api'
import request from '@/utils/request'

export default {
  data() {
    return { diners: [], curName: '', userRole: '', weekCount: 0, myRecipes: 0, shopCount: 0, isPc: false,
             allTags: [], tagSel: [],   // 口味标签池（来自 tasteApi）+ 当前选中
             form: { show: false, mode: '', title: '', val: '', hint: '', id: null },
             // 登录态 / 账号弹窗（已登录点资料头直接进 account-settings 页；未登录弹引导）
             isLogin: false,
             userEmail: '', userAvatar: '',
             accountDialog: { show: false }, }
  },
  async onShow() {
    // 昵称占位：未登录时显示「未登录」，避免与任何真实账号混淆
    this.curName = uni.getStorageSync('eat_user') || '未登录'
    // PC 管理端入口：仅桌面宽屏可见（>=1024px），移动端不显示
    // 小程序/App 无 window 对象，统一走 uni 的窗口信息 API（各端均支持）
    try {
      const info = uni.getWindowInfo ? uni.getWindowInfo() : uni.getSystemInfoSync()
      this.isPc = !!(info && info.windowWidth >= 1024)
    } catch (e) { this.isPc = false }
    this.load()
    await this.loadUserEmail()
    // 从登录页带「bind」意图返回 → 直接进「账户设置」页（绑定弹窗在那边自动弹出）
    if (uni.getStorageSync('eat_open_bind_after_login')) {
      uni.removeStorageSync('eat_open_bind_after_login')
      if (this.isLogin) uni.navigateTo({ url: '/pages/account-settings/account-settings' })
    }
  },
  methods: {
    async load() {
      try {
        const [diners, records, recipes, shops, tags] = await Promise.all([
          dinerApi.list(), recordApi.list(), recipeApi.list(), shopApi.list(), tasteApi.list().catch(() => [])
        ])
        this.diners = diners
        // 口味标签池（用于干饭成员口味维护 chip 选点）
        this.allTags = (tags || []).map((t) => t.name).filter(Boolean)
        // 统计条（取自真实数据，实时算）
        this.weekCount = this.countThisWeek(records)
        this.myRecipes = recipes.filter((r) => r.source === 'my').length
        this.shopCount = shops.length
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // 本周（周一起）做了多少顿
    countThisWeek(records) {
      const now = new Date()
      const day = (now.getDay() + 6) % 7 // 周一=0
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - day)
      return records.filter((r) => {
        if (!r.date) return false
        const d = new Date(r.date)
        return !isNaN(d) && d >= start
      }).length
    },
    // 两个入口统一走居中弹窗（mode: diner 新增成员 / tags 编辑口味）
    addDiner() {
      this.form = { show: true, mode: 'diner', title: '添加成员', val: '', hint: '姓名', id: null }
    },
    editDiner(d) {
      this.tagSel = [...(d.tags || [])]   // 回填当前成员已选口味
      this.form = { show: true, mode: 'tags', title: '编辑口味', val: '', hint: '', id: d.id }
    },
    toggleTag(t) {
      const i = this.tagSel.indexOf(t)
      if (i >= 0) this.tagSel.splice(i, 1)
      else this.tagSel.push(t)
      this.tagSel = [...this.tagSel]
    },
    async saveForm() {
      const v = (this.form.val || '').trim()
      if (this.form.mode === 'diner') {
        if (!v) return uni.showToast({ title: '姓名不能为空', icon: 'none' })
        await dinerApi.create({ name: v, tags: [] })
      } else if (this.form.mode === 'tags') {
        // 口味 chip 点选结果（全来自 tasteApi 维护的标签）
        await dinerApi.updateTags(this.form.id, [...this.tagSel])
      }
      this.form.show = false
      this.load()
    },
    // 移除干饭成员：二次确认，失败要提示
    delDiner(d) {
      uni.showModal({
        title: '移除成员', content: `移除「${d.name}」？其口味偏好设置将一并删除。`, confirmText: '移除', confirmColor: '#e64340',
        success: async (res) => {
          if (!res.confirm) return
          try { await dinerApi.del(d.id); this.load() } catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
        },
      })
    },
    nav(url) {
      // 餐厅/菜谱是 tab 页，用 reLaunch；其余二级页 navigateTo
      if (url.includes('/shop/shop') || url.includes('/recipe/recipe')) return uni.reLaunch({ url })
      uni.navigateTo({ url })
    },

    // ---------- 登录态 / 资料头 ----------

    async loadUserEmail() {
      this.isLogin = !!uni.getStorageSync(request.TOKEN_KEY)
      if (!this.isLogin) { this.userEmail = ''; this.userRole = ''; this.curName = '未登录'; this.userAvatar = ''; return }
      try {
        const me = await authApi.me()
        this.userEmail = me.email || ''
        this.userRole = me.role || ''
        this.userAvatar = me.avatar || ''
        // 昵称以账号里的为准（本地 eat_user 可能是上一账号或手填残留）
        if (me.nickname) { this.curName = me.nickname; uni.setStorageSync('eat_user', me.nickname) }
      } catch (e) {
        // token 失效（request.js 已清 token）→ 回到未登录态
        this.isLogin = !!uni.getStorageSync(request.TOKEN_KEY)
        this.userEmail = ''
        this.userRole = ''
        this.curName = '未登录'
        this.userAvatar = ''
      }
    },
    // 点资料头：已登录直接进「账户设置」（改头像/昵称/邮箱/退出/注销都在那）；未登录弹引导弹窗
    openAccount() {
      if (this.isLogin) return this.goAccountSettings()
      this.accountDialog = { show: true }
    },
    // 账号弹窗 / 菜单行 → 「账户设置」页（绑定邮箱、退出登录、注销都在那边）
    goAccountSettings() {
      this.accountDialog.show = false
      uni.navigateTo({ url: '/pages/account-settings/account-settings' })
    },
    // 去登录页（H5/App 邮箱验证码登录）；redirect 用于回跳后自动接续原意图
    goLogin(redirect = '') {
      uni.navigateTo({ url: `/pages/login/login${redirect ? `?redirect=${redirect}` : ''}` })
    },
  }
}
</script>

<style lang="scss" scoped>
.page-header { display:flex; align-items:baseline; gap:16rpx; padding:20rpx var(--nav-safe-right) 20rpx 24rpx; padding-top:calc(env(safe-area-inset-top) + 20rpx); }
.page-title { font-size:44rpx; font-weight:700; }
.section { padding: 12rpx 24rpx; }
.sec-head { display:flex; align-items:center; justify-content:space-between; margin:6rpx 0 16rpx; }
.sec-title { font-size:32rpx; font-weight:700; }
.newlink { color:var(--brand); font-size:26rpx; }

/* 居中弹窗 */
.mask { position:fixed; left:0; top:0; right:0; bottom:0; background:rgba(0,0,0,0.45); z-index:999; display:flex; align-items:center; justify-content:center; padding:48rpx; }
.dialog { width:100%; max-width:560rpx; background:var(--card); border-radius:20rpx; padding:32rpx; }
.d-title { font-size:32rpx; font-weight:700; display:block; margin-bottom:20rpx; }
.dfi { background:var(--bg); border-radius:12rpx; height:84rpx; line-height:84rpx; padding:0 16rpx; margin-bottom:24rpx; font-size:28rpx; width:100%; box-sizing:border-box; color:var(--text); }
.d-btns { display:flex; gap:16rpx; justify-content:flex-end; flex-wrap:wrap; }
/* 弹窗内口味 chip 网格：6列 × 最多2行，超出滚动 */
.tag-grid { display:grid; grid-template-columns:repeat(6, 1fr); gap:10rpx; max-height:200rpx; overflow-y:auto; align-content:start; margin-bottom:12rpx; }
.t-chip { text-align:center; font-size:24rpx; padding:10rpx 4rpx; border:1rpx solid var(--border); border-radius:10rpx; background:var(--bg); }
.t-chip.on { background:var(--brand); color:#fff; border-color:var(--brand); }

/* 账号弹窗（未登录引导） */
.d-sub { font-size:22rpx; color:var(--text-2); display:block; margin-bottom:12rpx; }

/* 资料头 */
.pro { display:flex; align-items:center; gap:20rpx; background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); padding:26rpx 24rpx; }
.ava { width:92rpx; height:92rpx; border-radius:50%; background:linear-gradient(135deg,#4b3fe3,#8b5cf6); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.ava-em { font-size:40rpx; color:#fff; font-weight:600; }
.pro-c { flex:1; min-width:0; display:flex; flex-direction:column; gap:4rpx; }
.pro-nm { display:flex; align-items:center; gap:10rpx; }
.pname { font-size:34rpx; font-weight:700; }
.pmail { font-size:24rpx; color:var(--text-2); }
.u-role { font-size:20rpx; color:var(--brand); background:#efeaff; padding:2rpx 12rpx; border-radius:999rpx; }

/* 统计条 */
.stat-bar { display:flex; background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); overflow:hidden; }
.sc { flex:1; display:flex; flex-direction:column; align-items:center; gap:6rpx; padding:22rpx 0; }
.sc + .sc { border-left:1rpx solid var(--border); }
.st-num { font-size:40rpx; font-weight:700; color:var(--brand); }
.st-lab { font-size:22rpx; color:var(--text-2); text-align:center; }

/* 干饭成员 */
.row { margin-bottom:16rpx; }
.row-top { display:flex; align-items:center; gap:12rpx; }
.name { font-weight:600; font-size:30rpx; }
.sp { flex:1; }
.op { color:var(--brand); font-size:24rpx; padding:4rpx 8rpx; }
.op.danger { color:var(--danger); }
.row-bottom { display:flex; flex-wrap:wrap; gap:8rpx; margin-top:10rpx; }
.t-pill { font-size:20rpx; color:var(--text-2); background:var(--bg); padding:3rpx 12rpx; border-radius:999rpx; }

/* 功能菜单 */
.menu { background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); overflow:hidden; }
.mrow { display:flex; align-items:center; gap:18rpx; padding:24rpx 24rpx; }
.mrow + .mrow { border-top:1rpx solid var(--border); }
.ic { font-size:34rpx; }
.m1 { flex:1; min-width:0; display:flex; flex-direction:column; gap:3rpx; }
.mt { font-size:30rpx; font-weight:600; }
.ms { font-size:22rpx; color:var(--text-2); }
.ar { color:var(--text-2); font-size:30rpx; }
.tab-pad { height:40rpx; }
</style>