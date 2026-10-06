<!-- mine.vue —— 我的页（对齐「第一版 UI」p-me）
  结构：资料头（头像+昵称+副标题）→ 统计条(本周做了多少顿 / 我的菜谱 / 收藏餐厅)
        → 干饭成员(各自口味偏好维护) → 功能菜单行(图标 + 标题 + 副标题 + ›)
-->
<template>
  <view class="tab-page">
    <view class="page-header">
      <text class="page-title">我的</text>
    </view>

    <scroll-view class="tab-scroll" scroll-y>
      <!-- 资料头 -->
      <view class="section">
        <view class="pro">
          <view class="ava"><text class="ava-em">{{ curName.slice(0, 1) }}</text></view>
          <view class="pro-c">
            <view class="pro-nm">
              <text class="pname">{{ curName }}</text>
              <text class="u-role" v-if="isAdmin">管理员</text>
            </view>
            <text class="pmail">一人食 · 主打快手菜</text>
          </view>
          <text class="newlink" @tap="switchUser">切换</text>
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
          <!-- #ifdef H5 -->
          <!-- 管理端页面仅 H5 存在（见 pages.json 条件编译），故入口也只在 H5 渲染 -->
          <view class="mrow" v-if="isPc" @tap="nav('/pages/admin/admin')">
            <text class="ic">🖥️</text><view class="m1"><text class="mt">管理端（PC）</text><text class="ms">审核 · 图库 · 食材 · 餐厅 · 配置</text></view><text class="ar">›</text>
          </view>
          <!-- #endif -->

          <!-- 登录（未登录时才显示；H5/App 走邮箱验证码，小程序端启动即静默登录） -->
          <view class="mrow" v-if="!isLogin" @tap="goLogin">
            <text class="ic">🔑</text><view class="m1"><text class="mt">登录 / 注册</text><text class="ms">邮箱验证码登录，登录后可绑定邮箱</text></view><text class="ar">›</text>
          </view>

          <!-- 绑定邮箱 -->
          <view class="mrow" @tap="openBindEmail">
            <text class="ic">📧</text>
            <view class="m1">
              <text class="mt">邮箱绑定</text>
              <text class="ms">{{ !isLogin ? '未登录 · 点击去登录' : (userEmail ? '已绑定 ' + maskEmail(userEmail) : '未绑定 · H5/App 登录用') }}</text>
            </view>
            <text class="ar">›</text>
          </view>
        </view>
      </view>

      <!-- 注销账户（危险区域） -->
      <view class="section" v-if="!isAdmin">
        <view class="danger-zone" @tap="confirmDelete">
          <text class="danger-ic">⚠️</text>
          <view class="danger-info">
            <text class="danger-title">注销账户</text>
            <text class="danger-sub">物理删除你的所有数据，不可恢复</text>
          </view>
          <text class="ar">›</text>
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

    <!-- 绑定邮箱弹窗 -->
    <view class="mask" v-if="emailDialog.show" @tap="emailDialog.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">{{ userEmail ? '解绑邮箱' : '绑定邮箱' }}</text>
        <template v-if="!userEmail">
          <input v-model="emailDialog.email" placeholder="你的邮箱" class="dfi" type="email" />
          <view class="dflex">
            <input v-model="emailDialog.code" placeholder="6 位验证码" class="dfi flex1" type="number" maxlength="6" />
            <button class="pbtn sm ghost" :disabled="emailCd > 0" @tap="sendEmailCode">{{ emailCd > 0 ? emailCd + 's' : '获取验证码' }}</button>
          </view>
          <text class="d-sub">未配置 SMTP 时验证码打印在后端日志里</text>
        </template>
        <template v-else>
          <text class="d-sub">当前已绑定 {{ userEmail }}</text>
          <text class="d-sub">解绑后邮箱可重新绑定或用于新账号注册</text>
        </template>
        <view class="d-btns">
          <button class="pbtn ghost" @tap="emailDialog.show = false">取消</button>
          <button v-if="!userEmail" class="pbtn" @tap="doBindEmail">绑定</button>
          <button v-else class="pbtn" @tap="doUnbindEmail">解绑</button>
        </view>
      </view>
    </view>

    <!-- 注销确认弹窗（双确认：第一次警告，第二次输入"确认注销"） -->
    <view class="mask" v-if="deleteDialog.show" @tap="deleteDialog.step = 1">
      <view class="dialog" @tap.stop>
        <template v-if="deleteDialog.step === 1">
          <text class="d-title danger">⚠️ 确认注销？</text>
          <text class="d-sub">你的菜谱、冰箱、干饭记录、体重、厨房技巧……<text class="danger-bold">全部物理删除，不可恢复</text>。确定要继续吗？</text>
          <view class="d-btns">
            <button class="pbtn ghost" @tap="deleteDialog.show = false">再想想</button>
            <button class="pbtn danger" @tap="deleteDialog.step = 2">继续注销</button>
          </view>
        </template>
        <template v-else>
          <text class="d-title danger">最后确认</text>
          <text class="d-sub">请输入 <text class="danger-bold">"确认注销"</text> 来真的删除所有数据</text>
          <input v-model="deleteDialog.val" placeholder="输入：确认注销" class="dfi" />
          <view class="d-btns">
            <button class="pbtn ghost" @tap="deleteDialog.show = false">取消</button>
            <button class="pbtn danger" @tap="doDelete" :disabled="deleteDialog.val !== '确认注销'">确认注销</button>
          </view>
        </template>
      </view>
    </view>
  </view>
</template>

<script>
import { dinerApi, recordApi, recipeApi, shopApi, tasteApi, authApi } from '@/api'
import request from '@/utils/request'

export default {
  data() {
    return { diners: [], curName: '', isAdmin: false, weekCount: 0, myRecipes: 0, shopCount: 0, isPc: false,
             allTags: [], tagSel: [],   // 口味标签池（来自 tasteApi）+ 当前选中
             form: { show: false, mode: '', title: '', val: '', hint: '', id: null },
             // 邮箱绑定 / 注销相关
             isLogin: false,
             userEmail: '', emailCd: 0, emailDialog: { show: false, email: '', code: '' },
             deleteDialog: { show: false, step: 1, val: '' }, }
  },
  async onShow() {
    this.curName = uni.getStorageSync('eat_user') || '我'
    // 管理员演示开关：本地标记（MVP）
    this.isAdmin = uni.getStorageSync('eat_admin') === '1'
    // PC 管理端入口：仅桌面宽屏可见（>=1024px），移动端不显示
    // 小程序/App 无 window 对象，统一走 uni 的窗口信息 API（各端均支持）
    try {
      const info = uni.getWindowInfo ? uni.getWindowInfo() : uni.getSystemInfoSync()
      this.isPc = !!(info && info.windowWidth >= 1024)
    } catch (e) { this.isPc = false }
    this.load()
    await this.loadUserEmail()
    // 从登录页带「bind」意图返回 → 自动弹出邮箱弹窗，省去用户再点一次
    if (uni.getStorageSync('eat_open_bind_after_login')) {
      uni.removeStorageSync('eat_open_bind_after_login')
      if (this.isLogin) this.emailDialog = { show: true, email: '', code: '' }
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
    // 三个入口统一走居中弹窗（mode: user 切换用户 / diner 新增成员 / tags 编辑口味）
    switchUser() {
      this.form = { show: true, mode: 'user', title: '切换用户', val: this.curName, hint: '输入名字', id: null }
    },
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
      if (this.form.mode === 'user') {
        if (!v) return uni.showToast({ title: '名字不能为空', icon: 'none' })
        uni.setStorageSync('eat_user', v)
        this.curName = v
      } else if (this.form.mode === 'diner') {
        if (!v) return uni.showToast({ title: '姓名不能为空', icon: 'none' })
        await dinerApi.create({ name: v, tags: [] })
      } else if (this.form.mode === 'tags') {
        // 口味 chip 点选结果（全来自 tasteApi 维护的标签）
        await dinerApi.updateTags(this.form.id, [...this.tagSel])
      }
      this.form.show = false
      this.load()
    },
    async delDiner(d) {
      await dinerApi.del(d.id)
      this.load()
    },
    nav(url) {
      // 餐厅/菜谱是 tab 页，用 reLaunch；其余二级页 navigateTo
      if (url.includes('/shop/shop') || url.includes('/recipe/recipe')) return uni.reLaunch({ url })
      uni.navigateTo({ url })
    },

    // ---------- 邮箱绑定 / 注销 ----------

    async loadUserEmail() {
      this.isLogin = !!uni.getStorageSync(request.TOKEN_KEY)
      if (!this.isLogin) { this.userEmail = ''; return }
      try {
        const me = await authApi.me()
        this.userEmail = me.email || ''
      } catch (e) {
        // token 失效（request.js 已清 token）→ 回到未登录态
        this.isLogin = !!uni.getStorageSync(request.TOKEN_KEY)
        this.userEmail = ''
      }
    },
    maskEmail(email) {
      if (!email) return ''
      const [u, d] = email.split('@')
      if (u.length <= 2) return u[0] + '***@' + d
      return u[0] + '***' + u.slice(-1) + '@' + d
    },
    // 去登录页（H5/App 邮箱验证码登录）；redirect 用于回跳后自动接续原意图
    goLogin(redirect = '') {
      uni.navigateTo({ url: `/pages/login/login${redirect ? `?redirect=${redirect}` : ''}` })
    },
    openBindEmail() {
      // 未登录 → 跳到登录页，登录成功后自动回来弹出绑定弹窗
      if (!uni.getStorageSync(request.TOKEN_KEY)) return this.goLogin('bind')
      this.emailDialog = { show: true, email: '', code: '' }
    },
    async sendEmailCode() {
      if (!this.emailDialog.email || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(this.emailDialog.email)) {
        uni.showToast({ title: '邮箱格式不正确', icon: 'none' }); return
      }
      try {
        const r = await authApi.sendEmailCode(this.emailDialog.email, 'bind')
        uni.showToast({ title: r.hint || '验证码已发送', icon: 'none' })
        // 60s 倒计时
        this.emailCd = 60
        const t = setInterval(() => {
          this.emailCd--
          if (this.emailCd <= 0) clearInterval(t)
        }, 1000)
      } catch (e) {
        uni.showToast({ title: e.message || '发送失败', icon: 'none' })
      }
    },
    async doBindEmail() {
      if (!this.emailDialog.code || this.emailDialog.code.length !== 6) {
        uni.showToast({ title: '请输入 6 位验证码', icon: 'none' }); return
      }
      try {
        await authApi.bindEmail(this.emailDialog.email, this.emailDialog.code)
        uni.showToast({ title: '绑定成功', icon: 'success' })
        this.emailDialog.show = false
        await this.loadUserEmail()
      } catch (e) {
        uni.showToast({ title: e.message || '绑定失败', icon: 'none' })
      }
    },
    async doUnbindEmail() {
      uni.showModal({
        title: '确认解绑？',
        content: '解绑后此邮箱可重新绑定或用于新账号注册',
        success: async (r) => {
          if (!r.confirm) return
          try {
            await authApi.unbindEmail()
            uni.showToast({ title: '已解绑', icon: 'success' })
            this.emailDialog.show = false
            await this.loadUserEmail()
          } catch (e) {
            uni.showToast({ title: e.message || '解绑失败', icon: 'none' })
          }
        }
      })
    },
    confirmDelete() {
      this.deleteDialog = { show: true, step: 1, val: '' }
    },
    async doDelete() {
      if (this.deleteDialog.val !== '确认注销') return
      try {
        await authApi.deleteMe()
        // 清 token + 用户信息
        uni.removeStorageSync(request.TOKEN_KEY)
        uni.removeStorageSync(request.USER_KEY)
        uni.showToast({ title: '已注销', icon: 'success' })
        setTimeout(() => {
          uni.reLaunch({ url: '/pages/index/index' })
        }, 800)
      } catch (e) {
        uni.showToast({ title: e.message || '注销失败', icon: 'none' })
      }
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
.d-btns { display:flex; gap:16rpx; justify-content:flex-end; }
/* 弹窗内口味 chip 网格：6列 × 最多2行，超出滚动 */
.tag-grid { display:grid; grid-template-columns:repeat(6, 1fr); gap:10rpx; max-height:200rpx; overflow-y:auto; align-content:start; margin-bottom:12rpx; }
.t-chip { text-align:center; font-size:24rpx; padding:10rpx 4rpx; border:1rpx solid var(--border); border-radius:10rpx; background:var(--bg); }
.t-chip.on { background:var(--brand); color:#fff; border-color:var(--brand); }
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

/* 注销危险区 */
.danger-zone { display:flex; align-items:center; gap:18rpx; padding:24rpx; background:#fff5f5; border:1rpx solid #ffd6d6; border-radius:var(--radius-lg,16rpx); }
.danger-ic { font-size:36rpx; }
.danger-info { flex:1; min-width:0; display:flex; flex-direction:column; gap:4rpx; }
.danger-title { font-size:28rpx; font-weight:600; color:#e74c3c; }
.danger-sub { font-size:22rpx; color:#c0392b; }

/* 弹窗里注销的红色按钮 */
.d-title.danger { color:#e74c3c; }
.danger-bold { color:#e74c3c; font-weight:600; }
.pbtn.danger { background:#e74c3c; color:#fff; }
.pbtn.danger[disabled] { opacity:.4; }

/* 邮箱弹窗里的 flex 行 */
.dflex { display:flex; gap:12rpx; align-items:center; }
.flex1 { flex:1; }
.pbtn.sm { font-size:24rpx; padding:10rpx 20rpx; }
</style>