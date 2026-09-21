<!-- mine-ref.vue —— 参考菜谱列表页
  我的 → 参考菜谱：只展示「参考」来源菜谱，点卡片进入详情可「＋ 候选 / ＋ 存进我的菜谱」。
  覆盖方形封面，非 tab 页用导航栈 navigateTo 进入详情。-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="nav-back" @tap="uni.navigateBack()">‹ 返回</text>
      <text class="ntitle">参考菜谱</text>
      <view class="nright"></view>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="scroll-inner">
        <view class="sec-tit">管理员精选 · 可加入吃这些或我的菜谱</view>
        <view class="ref-list">
          <view class="ref-card" v-for="r in refs" :key="r.id" @tap="open(r)">
            <view class="ref-cover" :class="coverCls(r)">
              <text class="ref-em">{{ r.em }}</text>
            </view>
            <view class="ref-info">
              <view class="ref-name">{{ r.name }}</view>
              <view class="ref-meta">{{ r.time }}分钟 · {{ r.diff }}</view>
              <view class="ref-tags">
                <text class="t-pill" v-for="t in r.tags" :key="t">{{ t }}</text>
              </view>
            </view>
          </view>
        </view>
        <view class="section-empty" v-if="!refs.length">
          <text class="empty-tip">暂无参考菜谱</text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { recipeApi } from '@/api'

// 渐变封面 color 池（按 id 轮换，与菜谱页 rec-cover 一致）
const covers = [
  'linear-gradient(135deg,#f59e0b,#f97316)', 'linear-gradient(135deg,#10b981,#059669)',
  'linear-gradient(135deg,#3b82f6,#2563eb)', 'linear-gradient(135deg,#ec4899,#f43f5e)',
  'linear-gradient(135deg,#8b5cf6,#6366f1)', 'linear-gradient(135deg,#14b8a6,#0d9488)'
]

export default {
  data() {
    return { refs: [] }
  },
  onShow() { this.load() },
  methods: {
    async load() {
      try {
        const list = await recipeApi.list()
        this.refs = list.filter((r) => r.source === 'admin')
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    coverCls(r) { return covers[r.id % covers.length] },
    open(r) { uni.navigateTo({ url: `/pages/recipe-detail/recipe-detail?id=${r.id}` }) }
  }
}
</script>

<style lang="scss" scoped>
.npage { min-height: 100vh; background: var(--bg); display: flex; flex-direction: column; }
.nheader { display: flex; align-items: center; padding: 20rpx 24rpx; padding-top: calc(env(safe-area-inset-top) + 20rpx); background: var(--card); }
.nav-back { font-size: 30rpx; color: var(--brand); white-space: nowrap; flex-shrink: 0; padding-right: 20rpx; }
.ntitle { flex: 1; text-align: center; font-size: 34rpx; font-weight: 700; }
.nright { width: 100rpx; flex-shrink: 0; }
.nscroll { flex: 1; }
.scroll-inner { box-sizing: border-box; padding: 0 24rpx; }
.sec-tit { font-size: 26rpx; color: var(--text-2); padding: 24rpx 4rpx 4rpx; }
.ref-list { padding-bottom: 20rpx; }
.ref-card { display: flex; gap: 20rpx; align-items: center; background: var(--card); border: 1rpx solid var(--border); border-radius: 16rpx; padding: 20rpx; margin-top: 20rpx; }
.ref-cover { width: 112rpx; height: 112rpx; border-radius: 14rpx; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ref-em { font-size: 52rpx; }
.ref-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6rpx; }
.ref-name { font-size: 30rpx; font-weight: 700; }
.ref-meta { font-size: 24rpx; color: var(--text-2); }
.ref-tags { display: flex; flex-wrap: wrap; gap: 8rpx; }
.t-pill { font-size: 20rpx; color: var(--brand); background: #efeaff; padding: 2rpx 12rpx; border-radius: 999rpx; }
.section-empty { padding: 60rpx 0; text-align: center; }
.empty-tip { color: var(--text-2); font-size: 26rpx; }
</style>