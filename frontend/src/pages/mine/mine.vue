<!-- mine.vue —— 我的页（对齐「第一版 UI」p-me）
  结构：资料头（头像+昵称+副标题，点击弹账号弹窗）→ 统计条(本周做了多少顿 / 我的菜谱 / 收藏餐厅)
        → 功能菜单行(家庭空间 + 图标 + 标题 + 副标题 + ›)
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
            <text class="pmail">{{ userSignature || '好好吃饭好好生活' }}</text>
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
          <view class="sc" @tap="nav('/pages/recipe/recipe?tab=shop')">
            <text class="st-num">{{ shopCount }}</text><text class="st-lab">收藏餐厅</text>
          </view>
        </view>
      </view>

      <!-- 功能菜单 -->
      <view class="section">
        <view class="menu">
          <view class="mrow" @tap="nav('/pages/family/family')">
            <text class="ic">🏠</text><view class="m1"><text class="mt">家庭空间</text><text class="ms">{{ famRowSub }}</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-tastes/mine-tastes')">
            <text class="ic">🏷️</text><view class="m1"><text class="mt">口味标签</text><text class="ms">菜谱筛选 · 推荐</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-ingredients/mine-ingredients')">
            <text class="ic">🧺</text><view class="m1"><text class="mt">食材库</text><text class="ms">菜谱可选食材 · 独立维护</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-ref/mine-ref')">
            <text class="ic">📚</text><view class="m1"><text class="mt">参考菜谱</text><text class="ms">管理员精选 · 可加入吃这些或我的菜谱</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/vip/vip')">
            <text class="ic">{{ vip && vip.is_member ? '👑' : '⭐' }}</text><view class="m1"><text class="mt">会员中心</text><text class="ms">{{ vipRowSub }}</text></view><text class="ar">›</text>
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
          <view class="mrow" @tap="openAccount">
            <text class="ic">⚙️</text><view class="m1"><text class="mt">账户设置</text><text class="ms">邮箱绑定 · 退出登录 · 注销账户</text></view><text class="ar">›</text>
          </view>
          <!-- #ifdef H5 -->
          <!-- 管理端页面仅 H5 存在（见 pages.json 条件编译），故入口也只在 H5 渲染 -->
          <view class="mrow" v-if="userRole === 'admin'" @tap="nav('/pages/admin/admin')">
            <text class="ic">🖥️</text><view class="m1"><text class="mt">管理端（PC）</text><text class="ms">审核 · 图库 · 食材 · 餐厅 · 配置</text></view><text class="ar">›</text>
          </view>
          <!-- #endif -->
        </view>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <custom-tab current="mine" />

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
import { recordApi, recipeApi, shopApi, authApi, paymentApi, familyApi } from '@/api'
import request from '@/utils/request'

export default {
  data() {
    return { family: null, curName: '', userSignature: '', userRole: '', weekCount: 0, myRecipes: 0, shopCount: 0,
             // 登录态 / 账号弹窗（已登录点资料头直接进 account-settings 页；未登录弹引导）
             isLogin: false,
             userEmail: '', userAvatar: '',
             accountDialog: { show: false },
             // 会员态（/payments/plans 是公开接口，游客也能看开关态）
             vip: null, }
  },
  computed: {
    // 家庭空间菜单行副标题：已加入显示名称+成员数，未加入引导
    famRowSub() {
      if (!this.family) return '创建或加入，共享「吃这些」候选'
      const n = (this.family.members || []).length
      return `${this.family.name}${n ? ` · ${n}位成员` : ''}`
    },
    vipRowSub() {
      if (!this.vip) return '免费额度 · 开通无限量'
      if (!this.vip.enabled) return '全部功能免费使用中'
      if (this.vip.is_member) {
        const d = new Date(this.vip.member_until * 1000)
        return `会员生效中 · 至 ${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
      }
      return '免费额度 · 开通无限量'
    },
  },
  async onShow() {
    // 昵称占位：未登录时显示「未登录」，避免与任何真实账号混淆
    this.curName = uni.getStorageSync('eat_user') || '未登录'
    // 先校验登录态（失效 token 会在 /auth/me 401 时被清掉），再拉业务数据，
    // 避免带着失效 token 请求导致「显示未登录却还有数据」的错乱
    await this.loadUserEmail()
    this.load()
    this.loadVip()
    // 从登录页带「bind」意图返回 → 直接进「账户设置」页（绑定弹窗在那边自动弹出）
    if (uni.getStorageSync('eat_open_bind_after_login')) {
      uni.removeStorageSync('eat_open_bind_after_login')
      if (this.isLogin) uni.navigateTo({ url: '/pages/account-settings/account-settings' })
    }
  },
  methods: {
    // 会员态静默拉取：失败不影响我的页（未部署会员时开关关着也只是不显示会员徽标）
    async loadVip() {
      try { this.vip = await paymentApi.plans() } catch (e) {}
    },
    async load() {
      try {
        const [family, records, recipes, shops] = await Promise.all([
          familyApi.mine().catch(() => null), recordApi.list(), recipeApi.list(), shopApi.list()
        ])
        this.family = (family && family.family) || null
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
    nav(url) {
      // 菜谱页是 tab 页，用 reLaunch；其余二级页 navigateTo
      if (url.includes('/recipe/recipe')) return uni.reLaunch({ url })
      uni.navigateTo({ url })
    },

    // ---------- 登录态 / 资料头 ----------

    async loadUserEmail() {
      this.isLogin = !!uni.getStorageSync(request.TOKEN_KEY)
      if (!this.isLogin) { this.userEmail = ''; this.userRole = ''; this.curName = '未登录'; this.userAvatar = ''; this.userSignature = ''; return }
      try {
        const me = await authApi.me()
        this.userEmail = me.email || ''
        this.userRole = me.role || ''
        this.userAvatar = me.avatar || ''
        this.userSignature = me.signature || ''
        // 昵称以账号里的为准（本地 eat_user 可能是上一账号或手填残留）
        if (me.nickname) { this.curName = me.nickname; uni.setStorageSync('eat_user', me.nickname) }
      } catch (e) {
        // token 失效（request.js 已清 token）→ 回到未登录态
        this.isLogin = !!uni.getStorageSync(request.TOKEN_KEY)
        this.userEmail = ''
        this.userRole = ''
        this.curName = '未登录'
        this.userAvatar = ''
        this.userSignature = ''
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
.newlink { color:var(--brand); font-size:26rpx; }

/* 居中弹窗 */
.mask { position:fixed; left:0; top:0; right:0; bottom:0; background:rgba(0,0,0,0.45); z-index:999; display:flex; align-items:center; justify-content:center; padding:48rpx; }
.dialog { width:100%; max-width:560rpx; background:var(--card); border-radius:20rpx; padding:32rpx; }
.d-title { font-size:32rpx; font-weight:700; display:block; margin-bottom:20rpx; }
.d-btns { display:flex; gap:16rpx; justify-content:flex-end; flex-wrap:wrap; }

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