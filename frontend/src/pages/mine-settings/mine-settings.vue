<!-- mine-settings.vue —— 用户端设置（占位页）
  管理类配置（厨房技巧审核开关、临期阈值）已移至管理端系统配置菜单。
  本页留作用户设置占位，后续接切换身份/账号/数据导出等真实用户级设置。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="back">‹</text>
      <text class="ntitle">设置</text>
    </view>
    <view class="empty">更多设置即将上线…</view>
  </view>
</template>

<script>
export default {
  methods: {
    back() { uni.navigateBack() }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) 24rpx 16rpx; }
.back { font-size:48rpx; font-weight:600; }
.ntitle { font-size:36rpx; font-weight:700; }
.empty { flex:1; display:flex; align-items:center; justify-content:center; color:var(--text-2); font-size:26rpx; }
</style>
