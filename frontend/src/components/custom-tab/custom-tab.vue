<!-- custom-tab.vue —— 自定义底部导航（5 Tab），对齐「第一版 UI」底部恒定导航骨架
  当前页传 current，点击其它 tab 用 reLaunch 平滑切换。
-->
<template>
  <view class="tabbar">
    <view
      v-for="t in tabs"
      :key="t.key"
      class="tab-item"
      :class="{ on: t.key === current }"
      @tap="go(t)"
    >
      <text class="tab-emoji">{{ t.emoji }}</text>
      <text class="tab-label">{{ t.label }}</text>
    </view>
  </view>
</template>

<script>
export default {
  name: 'CustomTab',
  props: {
    current: { type: String, default: 'index' }
  },
  data() {
    return {
      tabs: [
        { key: 'index', label: '推荐', emoji: '🎯', path: '/pages/index/index' },
        { key: 'recipe', label: '菜谱', emoji: '📖', path: '/pages/recipe/recipe' },
        { key: 'fridge', label: '冰箱', emoji: '🧊', path: '/pages/fridge/fridge' },
        { key: 'shop', label: '餐厅', emoji: '🏪', path: '/pages/shop/shop' },
        { key: 'mine', label: '我的', emoji: '👤', path: '/pages/mine/mine' }
      ]
    }
  },
  methods: {
    go(t) {
      if (t.key === this.current) return
      uni.reLaunch({ url: t.path })
    }
  }
}
</script>

<style lang="scss" scoped>
.tabbar {
  display: flex;
  height: 112rpx;
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--surface);
  border-top: 1rpx solid var(--border);
  flex-shrink: 0;
}
.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  color: var(--text-2);
}
.tab-item.on {
  color: var(--brand);
}
.tab-emoji {
  font-size: 40rpx;
  line-height: 1;
}
.tab-label {
  font-size: 22rpx;
}
</style>