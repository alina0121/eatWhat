<!-- mine-settings.vue —— 设置（对齐第一版UI设计稿 p-settings 菜单行样式）
  保留真实配置表驱动的两个功能行：厨房技巧审核开关 + 临期阈值（天），改动即生效。
  其余（账号/备份等）为不入库的界面占位，等后续接真实账号时再启用。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="back">‹</text>
      <text class="ntitle">设置</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="menu">
        <view class="row">
          <text class="ic">👨‍🍳</text>
          <view class="rb"><text class="rt">厨房技巧审核</text><text class="rs">新增 / 修改技巧需管理员审核</text></view>
          <switch :checked="audit" :style="{ transform: 'scale(0.7)' }" @change="(e) => setAudit(e)" />
        </view>

        <view class="row">
          <text class="ic">⏱</text>
          <view class="rb">
            <text class="rt">临期阈值（天）</text>
            <view class="rs">在库食材剩余≤该天数视为临期</view>
          </view>
          <input class="num" type="number" :value="String(expiry)" @blur="setExpiry" />
        </view>
      </view>
      <text class="tip">配置表驱动，保存后立即生效。</text>
    </scroll-view>
  </view>
</template>

<script>
import { configApi } from '@/api'

export default {
  data() { return { audit: true, expiry: 3 } },
  async onShow() { await this.load() },
  methods: {
    back() { uni.navigateBack() },
    async load() {
      try {
        const a = await configApi.get('audit_enabled')
        const e = await configApi.get('expiry_threshold_days')
        this.audit = (a.value === '1' || a.value === true || a.value === 1)
        this.expiry = Number(e.value)
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    async setAudit(ev) {
      const on = ev.detail.value
      this.audit = on
      await configApi.set('audit_enabled', on ? '1' : '0').catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
    },
    async setExpiry(ev) {
      const v = Number(ev.detail.value)
      if (!isNaN(v) && v > 0) { this.expiry = v; await configApi.set('expiry_threshold_days', String(v)) }
    }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) 24rpx 16rpx; }
.back { font-size:48rpx; color:var(--text); font-weight:600; }
.ntitle { font-size:36rpx; font-weight:700; }
.nscroll { flex:1; }
.menu { margin:12rpx 24rpx; background:var(--card); border:1rpx solid var(--border); border-radius:20rpx; overflow:hidden; }
.row { display:flex; align-items:center; gap:20rpx; padding:24rpx; border-bottom:1rpx solid var(--border); }
.row:last-child { border-bottom:none; }
.ic { font-size:40rpx; }
.rb { flex:1; display:flex; flex-direction:column; }
.rt { font-size:28rpx; font-weight:600; }
.rs { font-size:22rpx; color:var(--text-2); margin-top:4rpx; }
.num { background:var(--bg); border-radius:10rpx; height:64rpx; line-height:64rpx; padding:0 16rpx; width:100rpx; text-align:right; font-size:26rpx; border:1rpx solid var(--border); box-sizing:border-box; }
.tip { display:block; color:var(--text-2); font-size:22rpx; margin:16rpx 32rpx; }
</style>