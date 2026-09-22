<!-- mine-data.vue —— 用户端「我的数据」总览
  集中展示**个人数据**（我的菜谱/参考菜谱/在库/待采购/候选/餐厅/干饭/体重），
  与管理端「公共资源统计」互为对照：个人数据只在用户端看，不上管理端。
  数据来自后端 /mine/stats 实时聚合，前端只消费结果、不落冗余。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="back">‹</text>
      <text class="ntitle">我的数据</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="section">
        <view class="sub">计数概览 <text class="sub-s">个人数据 · 实时统计</text></view>
        <view class="kpis">
          <view class="kpi" v-for="k in kpis" :key="k.ic">
            <text class="kpi-ic">{{ k.ic }}</text>
            <view class="kpi-t">
              <text class="kpi-num">{{ k.k }}</text>
              <text class="kpi-lbl">{{ k.t }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 干饭分布 -->
      <view class="section">
        <view class="card">
          <view class="c-head">
            <text class="c-t">🍚 本月干饭分布</text>
            <text class="c-ms">{{ stats.monthly.month }}</text>
          </view>
          <view class="hbars">
            <view class="hbar" v-for="d in dryDist" :key="d.label">
              <text class="hbar-lbl">{{ d.label }}</text>
              <view class="hbar-track"><view class="hbar-fill" :style="{ width: d.w + '%' }"></view></view>
              <text class="hbar-num">{{ d.count }}</text>
            </view>
            <text class="empty" v-if="!dryDist.length">本月还没有干饭记录</text>
          </view>
        </view>
      </view>

      <!-- 体重趋势 -->
      <view class="section">
        <view class="card">
          <view class="c-head"><text class="c-t">⚖️ 体重趋势</text><text class="c-ms">最近 {{ weightTrend.length }} 次</text></view>
          <view class="wtrack">
            <view class="wcol" v-for="w in weightTrend" :key="w.date">
              <view class="wbar" :style="{ height: w.h + 'px' }"></view>
              <text class="wnum">{{ w.weight }}</text>
              <text class="wdate">{{ w.date.slice(5) }}</text>
            </view>
          </view>
          <text class="empty" v-if="!weightTrend.length">还没有体重记录，去「体重记录」记一笔吧</text>
        </view>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>
  </view>
</template>

<script>
import { mineApi } from '@/api'

export default {
  data() {
    return {
      stats: { cards: {}, monthly: { month: '', dist: [] }, weight_trend: [] }
    }
  },
  computed: {
    kpis() {
      const c = this.stats.cards || {}
      return [
        { ic: '🍲', t: '我的菜谱', k: c.recipes_my ?? 0 },
        { ic: '📚', t: '参考菜谱', k: c.recipes_ref ?? 0 },
        { ic: '🧊', t: '冰箱在库', k: c.fridge_in ?? 0 },
        { ic: '🛒', t: '待采购', k: c.purchase ?? 0 },
        { ic: '📥', t: '吃这些候选', k: c.inbox ?? 0 },
        { ic: '🏪', t: '收藏餐厅', k: c.shops ?? 0 },
        { ic: '🍚', t: '干饭记录', k: c.records_total ?? 0 },
        { ic: '⚖️', t: '体重记录', k: c.weights ?? 0 }
      ]
    },
    // 本月干饭分布（宽条比例）
    dryDist() {
      const d = this.stats.monthly?.dist || []
      const mx = d.reduce((a, b) => Math.max(a, b.count || 0), 1)
      return d.map((x) => ({ ...x, w: ((x.count || 0) / mx) * 100 }))
    },
    // 体重趋势（归一化柱高）
    weightTrend() {
      const t = (this.stats.weight_trend || []).slice()
      if (!t.length) return []
      const vals = t.map((x) => x.weight)
      const mn = Math.min(...vals)
      const span = (Math.max(...vals) - mn) || 1
      return t.map((x) => ({ date: x.date, weight: x.weight, h: Math.round(30 + ((x.weight - mn) / span) * 66) }))
    }
  },
  onShow() { this.load() },
  methods: {
    back() { uni.navigateBack() },
    async load() {
      try { this.stats = await mineApi.stats() }
      catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    }
  }
}
</script>

<style lang="scss" scoped>
.npage { min-height: 100vh; background: #f6f7fb; padding-top: calc(env(safe-area-inset-top) + 88rpx); }
.nheader { position: fixed; top: 0; left: 0; right: 0; z-index: 10; height: 88rpx; display: flex; align-items: center; background: var(--brand, #4b3fe3); color: #fff; padding-top: env(safe-area-inset-top); box-sizing: content-box; }
.back { width: 88rpx; text-align: center; font-size: 44rpx; }
.ntitle { flex: 1; font-size: 32rpx; font-weight: 700; }
.add { padding-right: 24rpx; font-size: 26rpx; }
.nscroll { height: 100vh; }
.section { margin: 16rpx 24rpx; }
.sub { font-size: 26rpx; font-weight: 700; color: #333; margin: 8rpx 0 16rpx; display: flex; align-items: baseline; gap: 14rpx; }
.sub-s { font-size: 20rpx; color: #999; font-weight: 400; }

.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16rpx; }
.kpi { background: var(--card, #fff); border: 1rpx solid var(--border, #e8eaf0); border-radius: 20rpx; padding: 22rpx 12rpx; display: flex; flex-direction: column; align-items: center; gap: 10rpx; }
.kpi-ic { font-size: 40rpx; }
.kpi-t { display: flex; flex-direction: column; align-items: center; }
.kpi-num { font-size: 34rpx; font-weight: 800; color: var(--brand, #4b3fe3); line-height: 1.1; }
.kpi-lbl { font-size: 20rpx; color: #666; }

.card { background: var(--card, #fff); border: 1rpx solid var(--border, #e8eaf0); border-radius: 20rpx; padding: 24rpx; }
.c-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20rpx; }
.c-t { font-size: 28rpx; font-weight: 700; }
.c-ms { font-size: 22rpx; color: #999; }
.empty { display: block; color: #aaa; font-size: 24rpx; padding: 30rpx 0; text-align: center; }

.hbars { display: flex; flex-direction: column; gap: 16rpx; }
.hbar { display: flex; align-items: center; gap: 16rpx; }
.hbar-lbl { width: 84rpx; font-size: 24rpx; color: #555; flex-shrink: 0; }
.hbar-track { flex: 1; background: #f0f1f6; border-radius: 999rpx; height: 24rpx; }
.hbar-fill { height: 24rpx; border-radius: 999rpx; background: linear-gradient(90deg, #4b3fe3, #8b5cf6); }
.hbar-num { width: 48rpx; font-size: 26rpx; font-weight: 700; text-align: right; }

.wtrack { display: flex; align-items: flex-end; justify-content: space-between; gap: 8rpx; height: 200rpx; padding: 0 8rpx; box-sizing: border-box; }
.wcol { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 8rpx; }
.wbar { width: 34rpx; max-width: 70%; border-radius: 8rpx 8rpx 0 0; background: linear-gradient(180deg, #10b981, #34d399); }
.wnum { font-size: 20rpx; color: #333; }
.wdate { font-size: 20rpx; color: #999; }
.tab-pad { height: 40rpx; }
</style>