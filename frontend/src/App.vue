<!-- App.vue —— 应用根组件：只放全局样式，不放页面内容 -->
<script>
export default {
  onLaunch() {
    // 应用启动钩子：预留（后续在这里读取配置表、初始化用户态）
  }
}
</script>

<style lang="scss">
/* 全局基础样式：内屏高度固定，内容区滚动，底部自定义导航恒定 */

/* 设计令牌（CSS 变量）必须写在这里，不能写在 uni.scss：
   uni.scss 会被注入到每个页面/组件的 <style lang="scss">，
   若在那里写 page{} 规则，带 scoped 的页面会编译成 page[data-v-xxx]，
   小程序下 page 元素没有 data-v 属性 → 变量全部失效、颜色丢失。
   App.vue 的样式不带 scoped，编译进 app.wxss 全局生效，
   变量再由 page 沿 DOM 继承给所有后代（含自定义组件）。 */
page {
  --brand: #4b3fe3;
  --surface: #ffffff;
  --bg: #f5f5f7;
  --card: #ffffff;
  --border: #e6e6eb;
  --text: #1a1a1f;
  --text-2: #8a8a93;
  --danger: #e74c3c;
  --warning: #f5a623;
  --success: #07c160;

  height: 100%;
  background: var(--bg);
  color: var(--text);
  font-size: 28rpx;
  line-height: 1.5;
}

/* 所有 tab 页面统一取 h-screen 布局：header + scroll 内容 + 底部导航 */
.tab-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  /* #ifdef H5 */
  /* H5 用 dvh 跟随可视高度，规避移动端地址栏伸缩；小程序不支持该单位，故条件编译隔离 */
  height: 100dvh;
  /* #endif */
  overflow: hidden;
}

.tab-scroll {
  flex: 1;
  min-height: 0;
}

/* 通用卡片 / 按钮 / 标签，对齐第一版 UI token */
.card {
  background: var(--card);
  border: 1rpx solid var(--border);
  border-radius: var(--radius-lg, 16rpx);
  padding: 20rpx;
}

.pbtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 14rpx 26rpx;
  border-radius: 999rpx;
  background: var(--brand);
  color: #fff;
  font-size: 26rpx;
  border: none;
  box-sizing: border-box;
  line-height: 1.4;
  /* uni-app 对原生 button 有默认 margin/width/::after 边框，压平避免宽度溢出右侧被遮挡 */
  width: auto;
  margin: 0;
}
button.pbtn::after { border: none; }
.pbtn.ghost {
  background: transparent;
  color: var(--brand);
  box-shadow: inset 0 0 0 2rpx var(--brand);
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 10rpx 24rpx;
  border-radius: 999rpx;
  background: var(--card);
  border: 2rpx solid var(--border);
  font-size: 26rpx;
  color: var(--text);
}
.chip.on {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
</style>