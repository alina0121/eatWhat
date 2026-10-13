<!-- vip.vue —— 会员中心：会员态 / 免费额度 / 套餐开通
  数据源：GET /payments/plans（套餐、开关、会员态、额度使用，后端现算）
  支付：pay_mode=mock 沙箱下单即开通（联调）；pay_mode=wxpay 调 wx.requestVirtualPayment（仅小程序）
  超额引导：业务接口 403 VIP_REQUIRED 由 request.js 统一弹窗跳到本页
-->
<template>
  <view class="vpage">
    <view class="vheader">
      <text class="back" @tap="back">‹</text>
      <text class="vtitle">会员中心</text>
      <text class="vsub">免费够用 · 会员无限</text>
    </view>

    <scroll-view class="vscroll" scroll-y>
      <view class="wrap">
        <!-- 会员状态卡 -->
        <view class="hero" :class="{ member: info.is_member }">
          <view class="h-l">
            <text class="h-t">{{ heroTitle }}</text>
            <text class="h-s">{{ heroSub }}</text>
          </view>
          <text class="h-crown">{{ info.is_member ? '👑' : '🍽' }}</text>
        </view>

        <!-- 未开启会员体系提示（管理后台可开） -->
        <view v-if="!info.enabled" class="hint">会员体系未开启，当前全部功能免费使用</view>

        <!-- 免费额度 -->
        <view class="sec">
          <text class="sec-h">免费额度</text>
          <view class="card">
            <view v-for="q in quotaList" :key="q.kind" class="qrow">
              <text class="q-name">{{ q.name }}</text>
              <view class="q-bar">
                <view class="q-fill" :style="{ width: q.pct + '%' }" :class="{ warn: q.warn, full: q.over }"></view>
              </view>
              <text class="q-num" :class="{ over: q.over }">{{ q.used }}/{{ q.max == null ? '∞' : q.max }}</text>
            </view>
            <view class="qrow days">
              <text class="q-name">干饭记录回看</text>
              <text class="q-num">{{ viewText(info.quota.records_view_days) }}</text>
            </view>
            <view class="qrow days">
              <text class="q-name">体重回看</text>
              <text class="q-num">{{ viewText(info.quota.weights_view_days) }}</text>
            </view>
          </view>
        </view>

        <!-- 套餐（会员体系关闭时隐藏，避免误购） -->
        <view class="sec" v-if="info.enabled">
          <text class="sec-h">开通会员</text>
          <view
            v-for="(p, id) in planList" :key="id"
            class="plan" :class="{ sel: selPlan === id }"
            @tap="selPlan = id"
          >
            <view class="p-l">
              <text class="p-name">{{ p.name }}</text>
              <text class="p-days">{{ p.days }} 天 · 全部额度无限 + 全历史回看 + 数据导出</text>
            </view>
            <view class="p-r">
              <text v-if="p.hot" class="p-hot">划算</text>
              <text class="p-price">¥{{ fen2yuan(p.price_fen) }}</text>
            </view>
          </view>

          <view v-if="info.pay_mode === 'wxpay'" class="paytip">
            <text>iOS 走 Apple 支付（≥¥1），安卓走微信支付；未登录请先登录</text>
          </view>

          <button class="buybtn" :disabled="buying" @tap="buy">
            {{ buying ? '处理中…' : (info.is_member ? '续费会员' : '立即开通') }}
          </button>

          <!-- #ifndef MP-WEIXIN -->
          <view v-if="info.pay_mode === 'wxpay'" class="hint">H5 暂不支持拉起支付，请在微信小程序内开通</view>
          <!-- #endif -->
          <view v-if="info.pay_mode === 'mock'" class="hint">沙箱模式：下单即开通，用于联调（管理后台可切 wxpay）</view>
        </view>

        <view class="pad"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { paymentApi } from '@/api'
import request from '@/utils/request'

export default {
  data() {
    return {
      info: { enabled: false, pay_mode: 'mock', is_member: false, member_until: 0, logged_in: false, plans: {}, quota: {} },
      selPlan: 'yearly',
      buying: false,
    }
  },
  computed: {
    planList() {
      // 过滤掉配置不完整的套餐（没填价格/天数的不展示）
      const out = {}
      Object.entries(this.info.plans || {}).forEach(([id, p]) => {
        if (p && p.price_fen && p.days) out[id] = p
      })
      return out
    },
    quotaList() {
      const names = { recipes: '菜谱', ingredients: '食材', shops: '餐厅收藏', tips: '厨房技巧' }
      const q = this.info.quota || {}
      const isMember = this.info.is_member
      return Object.keys(names).map((kind) => {
        const it = q[kind] || { used: 0, max: null }
        const used = it.used || 0
        // 会员直接展示 ∞ 不再显示进度条压力；免费版按使用率分色（<80 紫 / ≥80 橙 / 满 红）
        const max = isMember ? null : (it.max != null && it.max > 0 ? it.max : null)
        const pct = max ? Math.min(100, Math.round((used / max) * 100)) : 0
        return { kind, name: names[kind], used, max, pct,
                 warn: max != null && pct >= 80 && used < max, over: max != null && used >= max }
      })
    },
    heroTitle() {
      return this.info.is_member ? '会员生效中' : '开通会员'
    },
    heroSub() {
      if (this.info.is_member) {
        const d = new Date(this.info.member_until * 1000)
        return `到期时间 ${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      }
      return '无限菜谱食材 · 全历史回看 · 数据导出'
    },
  },
  onShow() {
    this.load()
  },
  methods: {
    back() { uni.navigateBack() },
    fen2yuan(fen) {
      return (Number(fen || 0) / 100).toFixed(fen % 100 === 0 ? 0 : 2)
    },
    viewText(days) {
      if (this.info.is_member) return '全历史'
      if (this.info.enabled && (days == null || days <= 0)) return '不限'
      return days == null || days <= 0 ? '不限' : `最近 ${days} 天（会员不限）`
    },
    async load() {
      try {
        this.info = await paymentApi.plans()
        if (!this.planList[this.selPlan]) {
          const ids = Object.keys(this.planList)
          this.selPlan = ids.find((id) => this.info.plans[id].hot) || ids[0] || ''
        }
      } catch (e) {
        uni.showToast({ title: e.message || '加载失败', icon: 'none' })
      }
    },
    async buy() {
      if (this.buying) return
      if (!this.selPlan) return uni.showToast({ title: '没有可开通的套餐', icon: 'none' })
      if (!this.info.logged_in) {
        return uni.showModal({
          title: '请先登录', content: '登录后才能开通会员', confirmText: '去登录',
          success: (r) => { if (r.confirm) uni.navigateTo({ url: '/pages/login/login' }) },
        })
      }
      // 沙箱模式：二次确认后直接开通
      if (this.info.pay_mode !== 'wxpay') {
        return uni.showModal({
          title: '沙箱开通',
          content: '当前为 mock 模式，点击确定直接开通（不产生真实扣款）',
          success: (r) => { if (r.confirm) this.mockPay() },
        })
      }
      return this.wxPay()
    },
    async mockPay() {
      this.buying = true
      try {
        const res = await paymentApi.order(this.selPlan)
        if (res.paid) {
          uni.showToast({ title: '已开通', icon: 'success' })
          this.load()
        }
      } catch (e) {
        uni.showToast({ title: e.message || '开通失败', icon: 'none' })
      } finally {
        this.buying = false
      }
    },
    // 真实虚拟支付：下单拿 sign_data → wx.requestVirtualPayment → 成功/失败都查单对账
    // #ifdef MP-WEIXIN
    async wxPay() {
      this.buying = true
      try {
        // 记录支付环境（iOS 走 Apple 通道，费率不同，后端按 env 对账分渠道）
        const env = (uni.getSystemInfoSync().platform === 'ios') ? 1 : 0
        const order = await paymentApi.order(this.selPlan, env)
        if (order.paid) {  // 后端已判支付完成（如重复下单补偿）
          uni.showToast({ title: '已开通', icon: 'success' }); this.load(); return
        }
        await new Promise((resolve, reject) => {
          wx.requestVirtualPayment({
            ...order.sign_data,
            sign: order.sign,
            success: resolve,
            fail: reject,
          })
        })
        // success 回调可能丢失（官方文档），以后端查单结果为准
        const st = await paymentApi.orderStatus(order.out_trade_no)
        if (st.status === 'paid') {
          uni.showToast({ title: '已开通', icon: 'success' })
        } else {
          uni.showToast({ title: '支付确认中，稍后自动生效', icon: 'none' })
        }
        this.load()
      } catch (e) {
        const msg = (e && e.errMsg) || e.message || ''
        if (msg.indexOf('cancel') < 0) uni.showToast({ title: msg || '支付未完成', icon: 'none' })
      } finally {
        this.buying = false
      }
    },
    // #endif
    // #ifndef MP-WEIXIN
    async wxPay() {
      uni.showToast({ title: '请在微信小程序内开通', icon: 'none' })
    },
    // #endif
  },
}
</script>

<style scoped>
.vpage { display: flex; flex-direction: column; height: 100vh; background: #F5F5F7; }
.vheader { display: flex; align-items: center; gap: 16rpx; padding: calc(env(safe-area-inset-top) + 24rpx) 32rpx 24rpx; background: #fff; border-bottom: 1rpx solid var(--border, #eee); }
.back { font-size: 56rpx; line-height: 1; color: #333; padding: 0 12rpx; }
.vtitle { font-size: 34rpx; font-weight: 700; color: #222; }
.vsub { margin-left: auto; font-size: 22rpx; color: #999; }
.vscroll { flex: 1; min-height: 0; }
.wrap { padding: 24rpx 32rpx; }

.hero { display: flex; align-items: center; justify-content: space-between; padding: 40rpx 36rpx; border-radius: 24rpx; background: linear-gradient(135deg, #4b3fe3, #8b5cf6); color: #fff; }
.hero.member { background: linear-gradient(135deg, #b45309, #f59e0b); }
.h-t { display: block; font-size: 40rpx; font-weight: 800; }
.h-s { display: block; margin-top: 10rpx; font-size: 24rpx; opacity: 0.85; }
.h-crown { font-size: 72rpx; }

.sec { margin-top: 32rpx; }
.sec-h { display: block; margin-bottom: 16rpx; font-size: 28rpx; font-weight: 700; color: #333; }
.card { background: #fff; border-radius: 20rpx; padding: 8rpx 28rpx; }
.qrow { display: flex; align-items: center; gap: 20rpx; padding: 24rpx 0; border-bottom: 1rpx solid #f2f2f2; }
.qrow:last-child { border-bottom: none; }
.qrow.days { justify-content: space-between; }
.q-name { width: 180rpx; font-size: 26rpx; color: #444; }
.q-bar { flex: 1; height: 12rpx; border-radius: 6rpx; background: #f0f0f0; overflow: hidden; }
.q-fill { height: 100%; border-radius: 6rpx; background: #4b3fe3; }
.q-fill.warn { background: #f59e0b; }
.q-fill.full { background: #ef4444; }
.q-num { width: 140rpx; text-align: right; font-size: 24rpx; color: #888; }
.q-num.over { color: #ef4444; font-weight: 700; }

.plan { display: flex; align-items: center; justify-content: space-between; background: #fff; border-radius: 20rpx; padding: 30rpx 30rpx; margin-bottom: 20rpx; border: 3rpx solid transparent; }
.plan.sel { border-color: #4b3fe3; background: #f6f5ff; }
.p-name { display: block; font-size: 30rpx; font-weight: 700; color: #222; }
.p-days { display: block; margin-top: 8rpx; font-size: 22rpx; color: #999; }
.p-r { display: flex; align-items: center; gap: 14rpx; }
.p-hot { font-size: 20rpx; color: #fff; background: #f59e0b; border-radius: 8rpx; padding: 4rpx 12rpx; }
.p-price { font-size: 38rpx; font-weight: 800; color: #b45309; }

.buybtn { margin-top: 12rpx; background: linear-gradient(135deg, #4b3fe3, #8b5cf6); color: #fff; font-size: 32rpx; font-weight: 700; border-radius: 48rpx; line-height: 96rpx; }
.buybtn[disabled] { opacity: 0.6; }
.paytip, .hint { margin-top: 16rpx; font-size: 22rpx; color: #999; text-align: center; }
.pad { height: calc(env(safe-area-inset-bottom) + 40rpx); }
</style>
