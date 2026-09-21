<!-- shop-detail.vue —— 餐厅详情查看 -->
<template>
  <view class="page">
    <view class="navbar">
      <text class="nav-back" @tap="uni.navigateBack()">‹ 返回</text>
      <text class="nav-title">餐厅详情</text>
    </view>
    <scroll-view scroll-y class="body" v-if="s">
      <view class="inner">
      <!-- hero 大封面（对齐原型 hero-img，彩色+emoji） -->
      <view class="hero" :class="'k' + (s.id % 4 + 1)"><text class="em">{{ s.em || '🏪' }}</text></view>
      <view class="d-title">
        <text class="name">{{ s.name }}</text>
        <text class="type">{{ s.type }}</text>
      </view>
      <view class="d-meta">{{ s.type }} · {{ s.price || '—' }} · ⭐ {{ s.star || '新' }}</view>
      <view class="block" v-if="s.arr_min || s.transport">
        <text class="b-title">到达信息</text>
        <text class="info-line">🚇 到达：{{ s.arr_min }} 分钟{{ s.transport ? ' · ' + s.transport : '' }}</text>
      </view>
      <view class="block" v-if="s.must && s.must.length">
        <text class="b-title">招牌菜</text>
        <text class="tg" v-for="(m, i) in s.must" :key="i">{{ m }}</text>
      </view>
      <view class="block">
        <text class="b-title">备注</text>
        <text class="info-line">{{ s.note || '暂无备注' }}</text>
      </view>
      <view class="bottom-pad"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { shopApi } from '@/api'
export default {
  data() { return { s: null } },
  onLoad(q) { this.id = Number(q.id); this.load() },
  methods: {
    async load() { try { this.s = await shopApi.get(this.id) } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) } }
  }
}
</script>

<style lang="scss" scoped>
.page { min-height:100vh; background:var(--bg); }
.navbar { display:flex; align-items:center; padding:20rpx 24rpx; padding-top:calc(env(safe-area-inset-top) + 20rpx); background:var(--surface); position:sticky; top:0; z-index:10; }
.nav-back { font-size:30rpx; color:var(--brand); white-space:nowrap; flex-shrink:0; padding-right:20rpx; }
.nav-title { flex:1; text-align:center; font-size:32rpx; font-weight:600; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; padding:0 12rpx; }
.body { padding-bottom:40rpx; }
.inner { box-sizing:border-box; width:100%; padding:0 24rpx; }
.hero { height:320rpx; border-radius:var(--radius-lg,16rpx); display:flex; align-items:center; justify-content:center; margin-top:16rpx; }
.hero .em { font-size:140rpx; }
.k1 { background: linear-gradient(135deg,#4b3fe3,#8b5cf6); }
.k2 { background: linear-gradient(135deg,#ec4899,#f97316); }
.k3 { background: linear-gradient(135deg,#06b6d4,#3b82f6); }
.k4 { background: linear-gradient(135deg,#10b981,#a3e635); }
.d-title { display:flex; align-items:center; gap:14rpx; margin-top:20rpx; }
.name { font-size:40rpx; font-weight:700; }
.type { font-size:24rpx; color:var(--text-2); background:var(--card); padding:4rpx 14rpx; border-radius:999rpx; }
.d-meta { color:var(--warning); margin-top:10rpx; font-size:26rpx; }
.block { background:var(--card); border-radius:var(--radius-lg,16rpx); padding:24rpx; margin-top:20rpx; }
.b-title { font-size:28rpx; font-weight:600; display:block; margin-bottom:12rpx; }
.tg { display:inline-block; font-size:24rpx; background:var(--bg); padding:4rpx 14rpx; border-radius:999rpx; margin:0 8rpx 8rpx 0; }
.info-line { display:block; font-size:28rpx; color:var(--text-2); }
.bottom-pad { height:60rpx; }
</style>