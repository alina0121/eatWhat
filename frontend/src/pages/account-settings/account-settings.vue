<!-- account-settings.vue —— 账户设置
  归拢账户相关功能：邮箱绑定（绑定/解绑）· 退出登录 · 注销账户（双确认）
  入口：「我的」页功能菜单 → 账户设置；登录页 redirect=bind 回来也会自动落到这里弹绑定弹窗
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="goBack">‹</text>
      <text class="ntitle">账户设置</text>
      <text class="ph"></text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="inner">
        <!-- 未登录：引导去登录 -->
        <template v-if="!isLogin">
          <view class="card empty">
            <text class="e-title">还未登录</text>
            <text class="e-sub">登录后菜谱 / 冰箱 / 干饭记录可跨端带走，邮箱可用于验证码登录</text>
            <button class="pbtn" @tap="goLogin">去登录</button>
          </view>
        </template>

        <template v-else>
          <!-- 账号信息卡：头像(emoji) / 昵称 / 邮箱，头像和昵称可点修改 -->
          <view class="card acc">
            <view class="acc-row" @tap="avatarForm.show = true">
              <text class="acc-lab">头像</text>
              <text class="acc-val"><text class="ava-dot">{{ avatar || curName.slice(0, 1) }}</text></text>
              <text class="edit-link">✎</text>
            </view>
            <view class="acc-row" @tap="openNick">
              <text class="acc-lab">昵称</text>
              <text class="acc-val">{{ curName }}</text>
              <text class="edit-link">✎</text>
            </view>
            <view class="acc-row">
              <text class="acc-lab">邮箱</text>
              <text class="acc-val">{{ userEmail || '未绑定' }}</text>
            </view>
          </view>

          <!-- 邮箱绑定 / 退出登录 -->
          <view class="menu">
            <view class="mrow" @tap="openBindEmail">
              <text class="ic">📧</text>
              <view class="m1">
                <text class="mt">{{ userEmail ? '更换 / 解绑邮箱' : '绑定邮箱' }}</text>
                <text class="ms">{{ userEmail ? '已绑定 ' + maskEmail(userEmail) : '绑定后可用邮箱验证码登录' }}</text>
              </view>
              <text class="ar">›</text>
            </view>
            <view class="mrow" @tap="doLogout">
              <text class="ic">🚪</text>
              <view class="m1"><text class="mt">退出登录</text><text class="ms">退出后需重新登录才能写数据</text></view>
              <text class="ar">›</text>
            </view>
          </view>

          <!-- 注销账户（危险区域；管理员账号不可自助注销，与后端拦截保持一致） -->
          <view class="danger-zone" v-if="userRole !== 'admin'" @tap="confirmDelete">
            <text class="danger-ic">⚠️</text>
            <view class="danger-info">
              <text class="danger-title">注销账户</text>
              <text class="danger-sub">物理删除你的所有数据，不可恢复</text>
            </view>
            <text class="ar">›</text>
          </view>
          <text class="tip" v-else>管理员账号不可自助注销</text>
        </template>
      </view>
    </scroll-view>

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

    <!-- 昵称编辑弹窗 -->
    <view class="mask" v-if="nickForm.show" @tap="nickForm.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">修改昵称</text>
        <input v-model="nickForm.val" placeholder="新的昵称" class="dfi" :focus="nickForm.show" maxlength="20" />
        <view class="d-btns">
          <button class="pbtn ghost" @tap="nickForm.show = false">取消</button>
          <button class="pbtn" @tap="saveNickname">保存</button>
        </view>
      </view>
    </view>

    <!-- 头像 emoji 候选弹窗（4列 × 两行半网格，候选来自食材图标池 ingredient_icon_pool） -->
    <view class="mask" v-if="avatarForm.show" @tap="avatarForm.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">选择头像</text>
        <view class="emoji-grid">
          <view v-for="em in iconPool" :key="em" class="e-cell" :class="{ on: em === avatar }" @tap="saveAvatar(em)">{{ em }}</view>
        </view>
        <text class="d-sub" v-if="!iconPool.length">图标池为空 · 请管理员在「系统配置 → ingredient_icon_pool」补充</text>
        <view class="d-btns">
          <button class="pbtn ghost" @tap="avatarForm.show = false">取消</button>
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
import { authApi, configApi } from '@/api'
import request from '@/utils/request'

export default {
  data() {
    return {
      isLogin: false, curName: '', userEmail: '', userRole: '', avatar: '',
      // 头像 emoji 候选池（来自 configs.ingredient_icon_pool，与食材图标同池）
      iconPool: [],
      // 昵称编辑 / 头像选择 / 邮箱绑定 / 注销 弹窗
      nickForm: { show: false, val: '' },
      avatarForm: { show: false },
      emailCd: 0, emailDialog: { show: false, email: '', code: '' },
      deleteDialog: { show: false, step: 1, val: '' },
    }
  },
  async onShow() {
    await this.loadUserEmail()
    this.loadIconPool()
    // 从登录页带「bind」意图返回 → 自动弹出绑定弹窗，省去用户再点一次
    if (uni.getStorageSync('eat_open_bind_after_login')) {
      uni.removeStorageSync('eat_open_bind_after_login')
      if (this.isLogin && !this.userEmail) this.emailDialog = { show: true, email: '', code: '' }
    }
  },
  methods: {
    goBack() { uni.navigateBack() },
    goLogin() { uni.navigateTo({ url: '/pages/login/login?redirect=bind' }) },
    async loadUserEmail() {
      this.isLogin = !!uni.getStorageSync(request.TOKEN_KEY)
      if (!this.isLogin) { this.userEmail = ''; this.userRole = ''; this.curName = ''; this.avatar = ''; return }
      try {
        const me = await authApi.me()
        this.userEmail = me.email || ''
        this.userRole = me.role || ''
        this.avatar = me.avatar || ''
        this.curName = me.nickname || uni.getStorageSync('eat_user') || ''
      } catch (e) {
        // token 失效（request.js 已清 token）→ 回到未登录态
        this.isLogin = !!uni.getStorageSync(request.TOKEN_KEY)
        this.userEmail = ''; this.userRole = ''; this.curName = ''; this.avatar = ''
      }
    },
    // 头像 emoji 候选池：与食材图标同源（configs.ingredient_icon_pool，逗号分隔）
    async loadIconPool() {
      try {
        const r = await configApi.get('ingredient_icon_pool')
        this.iconPool = (r.value || '').split(',').map((s) => s.trim()).filter(Boolean)
      } catch (e) { this.iconPool = [] }
    },
    // 昵称修改：PUT /auth/profile（后端截断 20 字）
    openNick() { this.nickForm = { show: true, val: this.curName } },
    async saveNickname() {
      const v = (this.nickForm.val || '').trim()
      if (!v) return uni.showToast({ title: '昵称不能为空', icon: 'none' })
      try {
        await authApi.updateProfile({ nickname: v })
        this.curName = v
        uni.setStorageSync('eat_user', v)
        this.nickForm.show = false
        uni.showToast({ title: '已保存', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '保存失败', icon: 'none' })
      }
    },
    // 头像修改：点选 emoji 直接保存（users.avatar 存 emoji 字符）
    async saveAvatar(em) {
      try {
        await authApi.updateProfile({ avatar: em })
        this.avatar = em
        this.avatarForm.show = false
        uni.showToast({ title: '头像已更新', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '保存失败', icon: 'none' })
      }
    },
    maskEmail(email) {
      if (!email) return ''
      const [u, d] = email.split('@')
      if (u.length <= 2) return u[0] + '***@' + d
      return u[0] + '***' + u.slice(-1) + '@' + d
    },
    openBindEmail() {
      // 未登录 → 跳到登录页，登录成功后自动回来弹出绑定弹窗
      if (!uni.getStorageSync(request.TOKEN_KEY)) return this.goLogin()
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
    // 退出登录：清掉本地 token / 用户身份，返回「我的」（其 onShow 会刷新为未登录态）
    doLogout() {
      uni.showModal({
        title: '退出登录？',
        content: '退出后需要重新用邮箱验证码登录',
        success: (r) => {
          if (!r.confirm) return
          uni.removeStorageSync(request.TOKEN_KEY)
          uni.removeStorageSync(request.USER_KEY)
          uni.removeStorageSync('curUser')
          uni.removeStorageSync('eat_user')
          // 置「主动退出」标记：小程序端据此不再自动静默微信登录，
          // 直到用户下次主动登录（login.vue 落态时会清掉该标记）
          uni.setStorageSync(request.LOGOUT_FLAG, '1')
          this.isLogin = false
          this.userEmail = ''; this.userRole = ''; this.curName = ''
          uni.showToast({ title: '已退出', icon: 'none' })
          setTimeout(() => uni.navigateBack(), 600)
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

<style>
.npage { min-height: 100vh; background: var(--bg); display: flex; flex-direction: column; }
.nheader { display: flex; align-items: center; gap: 12rpx; padding: calc(env(safe-area-inset-top) + 16rpx) var(--nav-safe-right) 16rpx 24rpx; position: sticky; top: 0; background: var(--surface); z-index: 10; }
.back { font-size: 44rpx; color: var(--brand); padding-right: 20rpx; white-space: nowrap; }
.ntitle { flex: 1; text-align: center; font-size: 34rpx; font-weight: 700; }
.ph { width: 64rpx; }
.nscroll { flex: 1; }
.inner { padding: 16rpx 24rpx 120rpx; }
.tip { font-size: 24rpx; color: var(--text-2); display: block; padding: 24rpx 12rpx; }

/* 账号信息卡：头像 / 昵称 / 邮箱信息行 */
.acc-row { display: flex; align-items: center; gap: 12rpx; padding: 14rpx 0; }
.acc-row + .acc-row { border-top: 1rpx solid var(--border); }
.acc-lab { font-size: 26rpx; color: var(--text-2); width: 88rpx; flex: none; }
.acc-val { font-size: 28rpx; font-weight: 600; flex: 1; min-width: 0; word-break: break-all; }
.edit-link { font-size: 28rpx; color: var(--brand); flex: none; }
/* 头像小圆底（emoji 直接展示在渐变圆里，与「我的」页资料头同款） */
.ava-dot { display: inline-flex; width: 72rpx; height: 72rpx; border-radius: 50%; background: linear-gradient(135deg,#4b3fe3,#8b5cf6); align-items: center; justify-content: center; font-size: 36rpx; font-weight: 400; }

/* 头像 emoji 候选：4列 × 两行半（对齐全局 emoji 网格规范），点选即保存 */
.emoji-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10rpx; max-height: 200rpx; overflow-y: auto; align-content: start; margin-bottom: 12rpx; }
.e-cell { text-align: center; font-size: 44rpx; height: 76rpx; line-height: 76rpx; border: 1rpx solid var(--border); border-radius: 10rpx; background: var(--bg); }
.e-cell.on { background: var(--brand); border-color: var(--brand); }

/* 未登录空态 */
.empty { display: flex; flex-direction: column; align-items: center; gap: 14rpx; padding: 48rpx 32rpx; text-align: center; }
.e-title { font-size: 32rpx; font-weight: 700; }
.e-sub { font-size: 24rpx; color: var(--text-2); }

/* 功能菜单 */
.menu { background: var(--card); border: 1rpx solid var(--border); border-radius: var(--radius-lg,16rpx); overflow: hidden; margin-bottom: 20rpx; }
.mrow { display: flex; align-items: center; gap: 18rpx; padding: 24rpx 24rpx; }
.mrow + .mrow { border-top: 1rpx solid var(--border); }
.ic { font-size: 34rpx; }
.m1 { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3rpx; }
.mt { font-size: 30rpx; font-weight: 600; }
.ms { font-size: 22rpx; color: var(--text-2); }
.ar { color: var(--text-2); font-size: 30rpx; }

/* 注销危险区 */
.danger-zone { display: flex; align-items: center; gap: 18rpx; padding: 24rpx; background: #fff5f5; border: 1rpx solid #ffd6d6; border-radius: var(--radius-lg,16rpx); }
.danger-ic { font-size: 36rpx; }
.danger-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4rpx; }
.danger-title { font-size: 28rpx; font-weight: 600; color: #e74c3c; }
.danger-sub { font-size: 22rpx; color: #c0392b; }

/* 弹窗 */
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 48rpx; }
.dialog { width: 100%; max-width: 600rpx; background: var(--surface); border-radius: 20rpx; padding: 36rpx 32rpx; }
.d-title { font-size: 32rpx; font-weight: 700; display: block; margin-bottom: 24rpx; }
.d-title.danger { color: #e74c3c; }
.d-sub { font-size: 22rpx; color: var(--text-2); display: block; margin-bottom: 12rpx; }
.danger-bold { color: #e74c3c; font-weight: 600; }
.dfi { background: var(--bg); border-radius: 12rpx; height: 84rpx; line-height: 84rpx; padding: 0 16rpx; margin-bottom: 16rpx; font-size: 28rpx; width: 100%; box-sizing: border-box; color: var(--text); }
.d-btns { display: flex; gap: 16rpx; justify-content: flex-end; margin-top: 16rpx; flex-wrap: wrap; }
.pbtn.danger { background: #e74c3c; color: #fff; }
.pbtn.danger[disabled] { opacity: .4; }
.pbtn.sm { font-size: 24rpx; padding: 10rpx 20rpx; }
/* 邮箱弹窗里的 flex 行 */
.dflex { display: flex; gap: 12rpx; align-items: center; }
.flex1 { flex: 1; }
</style>
