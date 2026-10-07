<!-- login.vue —— 登录页（三种入口统一在这里）
  1. 微信小程序端：「微信一键登录」按钮（wx.login → openid 唯一建号），也可用邮箱登录
  2. H5 / App 端：邮箱验证码登录（没有微信 openid，用邮箱建号）
  3. 邮箱未注册时自动注册（后端 /auth/login-email 已实现 upsert）
  进入方式：我的页「未登录」入口 / 绑定邮箱时未登录自动跳到这里。
  登录成功后回跳来源页；带 redirect=bind 时回「我的」自动弹出绑定邮箱弹窗。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="back">‹</text>
      <text class="ntitle">登录</text>
      <text class="ph"></text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="hero">
        <text class="hero-em">🍚</text>
        <text class="hero-t">吃啥好呀</text>
        <text class="hero-s">登录后菜谱 / 冰箱 / 干饭记录可跨端带走</text>
      </view>

      <view class="section">
        <!-- #ifdef MP-WEIXIN -->
        <!-- 微信一键登录：openid 唯一，一人一号；登录后再绑定邮箱即可跨端用邮箱登录 -->
        <button class="pbtn wx-btn" :disabled="loading" @tap="wxLogin">微信一键登录</button>
        <view class="or"><text class="or-t">或 用邮箱验证码登录</text></view>
        <!-- #endif -->

        <view class="fcard">
          <text class="flab">邮箱</text>
          <input v-model="email" class="dfi" type="text" placeholder="you@example.com" :disabled="loading" />

          <text class="flab mt">验证码</text>
          <view class="dflex">
            <input v-model="code" class="dfi flex1" type="number" maxlength="6" placeholder="6 位数字" :disabled="loading" />
            <button class="pbtn sm ghost" :disabled="cd > 0 || loading" @tap="sendCode">{{ cd > 0 ? cd + 's' : '获取验证码' }}</button>
          </view>

          <button class="pbtn login-btn" :disabled="loading" @tap="doLogin">{{ loading ? '登录中…' : '登录 / 注册' }}</button>

          <text class="tip" v-if="hint">{{ hint }}</text>
          <text class="tip" v-else>未配置 SMTP 时，验证码会打印在后端控制台日志里</text>
        </view>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>
  </view>
</template>

<script>
import { authApi } from '@/api'
import request from '@/utils/request'

export default {
  data() {
    return {
      email: '',
      code: '',
      cd: 0,
      loading: false,
      hint: '',
      redirect: ''   // 来源场景：bind=绑定邮箱时被拦下；空=普通登录
    }
  },
  onLoad(options) {
    this.redirect = (options && options.redirect) || ''
  },
  methods: {
    back() {
      if (getCurrentPages().length > 1) uni.navigateBack()
      else uni.reLaunch({ url: '/pages/mine/mine' })
    },
    // 统一落登录态：token + 用户信息 + 兼容既有键（curUser / eat_user）
    applyLogin(r) {
      uni.setStorageSync(request.TOKEN_KEY, r.token)
      uni.setStorageSync(request.USER_KEY, r)
      uni.setStorageSync('curUser', r.user_id)
      if (r.nickname) uni.setStorageSync('eat_user', r.nickname)
      // 清掉「已退出」标记，恢复自动登录能力
      uni.removeStorageSync(request.LOGOUT_FLAG)
    },
    // 登录成功后的收尾：回跳来源页；来源是绑定邮箱则回「我的」自动弹绑定框
    afterLogin() {
      if (this.redirect === 'bind') uni.setStorageSync('eat_open_bind_after_login', '1')
      setTimeout(() => {
        if (getCurrentPages().length > 1) uni.navigateBack()
        else uni.reLaunch({ url: '/pages/mine/mine' })
      }, 700)
    },
    // 微信一键登录（仅小程序端）：wx.login 拿 code → 后端换 openid 建号 → 落 token
    async wxLogin() {
      this.loading = true
      try {
        const { code } = await new Promise((res, rej) =>
          uni.login({ provider: 'weixin', success: res, fail: rej })
        )
        const r = await authApi.login(code)
        this.applyLogin(r)
        uni.showToast({ title: r.is_new ? '登录成功' : '欢迎回来', icon: 'success' })
        this.afterLogin()
      } catch (e) {
        uni.showToast({ title: e.message || '微信登录失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    async sendCode() {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(this.email.trim())) {
        uni.showToast({ title: '邮箱格式不正确', icon: 'none' }); return
      }
      try {
        const r = await authApi.sendEmailCode(this.email.trim(), 'login')
        this.hint = r.hint || '验证码已发送'
        uni.showToast({ title: '验证码已发送', icon: 'none' })
        this.cd = 60
        const t = setInterval(() => {
          this.cd--
          if (this.cd <= 0) clearInterval(t)
        }, 1000)
      } catch (e) {
        uni.showToast({ title: e.message || '发送失败', icon: 'none' })
      }
    },
    async doLogin() {
      const email = this.email.trim()
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
        uni.showToast({ title: '邮箱格式不正确', icon: 'none' }); return
      }
      if (!/^\d{6}$/.test(this.code)) {
        uni.showToast({ title: '请输入 6 位验证码', icon: 'none' }); return
      }
      this.loading = true
      try {
        // 昵称默认取邮箱 @ 前缀
        const r = await authApi.loginEmail(email, this.code, email.split('@')[0])
        // 落 token + 用户信息，后续请求自动带 Authorization
        this.applyLogin(r)
        uni.showToast({ title: r.is_new ? '注册并登录成功' : '登录成功', icon: 'success' })
        this.afterLogin()
      } catch (e) {
        uni.showToast({ title: e.message || '登录失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) var(--nav-safe-right) 16rpx 24rpx; }
.back { font-size:48rpx; font-weight:600; }
.ntitle { flex:1; text-align:center; font-size:36rpx; font-weight:700; }
.ph { width:48rpx; }
.nscroll { flex:1; }

.hero { display:flex; flex-direction:column; align-items:center; gap:8rpx; padding:60rpx 24rpx 20rpx; }
.hero-em { font-size:96rpx; }
.hero-t { font-size:44rpx; font-weight:700; }
.hero-s { font-size:24rpx; color:var(--text-2); }

.section { padding:12rpx 24rpx; }
/* 微信一键登录按钮（仅小程序端渲染）+ 分隔提示 */
.wx-btn { width:100%; padding:22rpx 0; font-size:30rpx; background:#07c160; }
.wx-btn[disabled] { opacity:.5; }
.or { display:flex; justify-content:center; margin:24rpx 0; }
.or-t { font-size:22rpx; color:var(--text-2); }
.fcard { background:var(--card); border:1rpx solid var(--border); border-radius:20rpx; padding:28rpx 24rpx; }
.flab { font-size:24rpx; color:var(--text-2); }
.flab.mt { display:block; margin-top:24rpx; }
.dfi { background:var(--bg); border-radius:12rpx; height:84rpx; line-height:84rpx; padding:0 20rpx; font-size:28rpx; width:100%; box-sizing:border-box; color:var(--text); margin-top:10rpx; }
.dflex { display:flex; gap:12rpx; align-items:center; }
.flex1 { flex:1; }
.pbtn.sm { font-size:24rpx; padding:10rpx 20rpx; margin-top:10rpx; }
.pbtn[disabled] { opacity:.5; }
.login-btn { width:100%; margin-top:40rpx; padding:22rpx 0; font-size:30rpx; }
.tip { display:block; margin-top:18rpx; font-size:22rpx; color:var(--text-2); text-align:center; line-height:1.5; }
.tab-pad { height:40rpx; }
</style>
