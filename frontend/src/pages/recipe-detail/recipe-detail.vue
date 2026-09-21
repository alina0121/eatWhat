<!-- recipe-detail.vue —— 菜谱详情：对齐原型 openDish
  结构：大封面 → 名称+我的/参考徽章 → 🕐耗时·🧑🍳难度的 meta → 口味tag
       → 步骤（编号圆+文本）→ 食材清单（在库✓勾选 + 名称 + 数量）
       → 操作区：列表进入=「＋候选」+（我的→编辑菜谱 / 参考→存进我的菜谱）
                 吃这些进入 viewOnly=「🍳 开始做这道菜」（已有计时则显计时）
-->
<template>
  <view class="page">
    <view class="navbar">
      <text class="nav-back" @tap="back">‹ 返回</text>
      <view class="nav-title">
        <text>{{ r ? r.name : '菜谱详情' }}</text>
      </view>
    </view>
    <scroll-view scroll-y class="body" v-if="r">
      <view class="inner">
      <!-- 大封面 -->
      <view class="hero" :style="cover()"><text class="em">{{ r.em }}</text></view>

      <!-- 名称 + 徽章 -->
      <view class="d-title">
        <text class="name">{{ r.name }}</text>
        <text class="badge" :class="r.source === 'admin' ? 'b-ref' : 'b-my'">
          {{ r.source === 'admin' ? '参考菜谱' : '我的菜谱' }}
        </text>
      </view>
      <view class="d-meta">🕐 {{ r.time }}分钟 · 🧑‍🍳 {{ r.diff }}</view>
      <view class="tags"><text class="t-pill" v-for="t in r.tags" :key="t">{{ t }}</text></view>

      <!-- 做法步骤 -->
      <view class="block">
        <text class="b-title">做法步骤</text>
        <view class="step" v-for="(s, i) in r.steps" :key="i">
          <text class="step-no">{{ i + 1 }}</text>
          <text class="step-text">{{ s }}</text>
        </view>
      </view>

      <!-- 所需食材：在库自动 ✓（只读状态标识） -->
      <view class="block">
        <text class="b-title">所需食材 <text class="hint">✓ 表示在库有</text></text>
        <view class="ing-r" v-for="(it, i) in r.ing" :key="i">
          <text class="ck" :class="{ on: checked(it) }">{{ checked(it) ? '✓' : '' }}</text>
          <text class="nm">{{ it.name }}</text>
          <text class="sp"></text>
          <text class="qty">{{ it.qty }}{{ it.unit }}</text>
        </view>
      </view>

      <!-- 操作区 -->
      <view class="actions row">
        <template v-if="viewOnly">
          <!-- 从「吃这些」进入：开始做 / 正在计时 -->
          <template v-if="timing">
            <text class="rtime run">⏱ {{ fmt(timing.elapsed) }}</text>
            <text class="tbtn on" @tap="stopTiming">⏸ 停止</text>
            <text class="tbtn" @tap="cancelTiming">⏹ 取消</text>
          </template>
          <text v-else class="pbtn primary" style="flex:1" @tap="startCook">🍳 开始做这道菜</text>
        </template>
        <template v-else>
          <text class="pbtn primary" style="flex:1" @tap="addCand">
            {{ added ? '✓ 已在吃这些' : '＋ 候选' }}
          </text>
          <text v-if="r.source === 'admin'" class="pbtn ghost" style="flex:1" @tap="copyToMine">＋ 存进我的菜谱</text>
          <template v-else>
            <text class="pbtn ghost" style="flex:1" @tap="edit">编辑菜谱</text>
            <text class="pbtn danger" style="flex:1" @tap="del">删除</text>
          </template>
        </template>
      </view>
      <view class="bottom-pad"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { recipeApi, candidateApi, fridgeApi } from '@/api'

export default {
  data() {
    return { r: null, added: false, viewOnly: false, inStockSet: [], timing: null }
  },
  onLoad(q) {
    this.id = Number(q.id)
    this.viewOnly = q.from === 'eat'
  },
  onShow() {
    // 每次进入/返回都重新加载，保证从「编辑菜谱」保存返回后详情实时刷新（首次进入 onLoad→onShow 也会触发）
    this.load()
  },
  methods: {
    async load() {
      try {
        const [recipe, stock, cands] = await Promise.all([
          recipeApi.get(this.id), fridgeApi.inStock(), candidateApi.list()
        ])
        this.r = recipe
        this.inStockSet = stock.map((s) => s.name)
        this.added = cands.some((c) => c.kind === 'recipe' && c.ref_id === this.id)
        if (this.viewOnly) this.syncTiming(cands)
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    syncTiming(cands) {
      const c = cands.find((x) => x.kind === 'recipe' && x.ref_id === this.id)
      this.timing = c && c.timer ? c.timer : null
      if (this.timing && this.timing.running) {
        this._tick = setInterval(() => { if (this.timing) this.timing.elapsed += 1 }, 1000)
      }
    },
    onUnload() { if (this._tick) clearInterval(this._tick) },
    back() { uni.navigateBack() },
    // 大封面背景：优先用所选固定封面渐变（coverGrad）；未选走默认三色渐变
    cover() {
      return { background: (this.r && this.r.coverGrad) || 'linear-gradient(135deg,#4b3fe3,#8b5cf6,#ec4899)' }
    },
    // 在库自动✓：只读状态标识（不参与交互）
    checked(it) {
      // 只读：该食材名是否在冰箱在库存（✓ 表示有）
      return this.inStockSet.indexOf(it.name) >= 0
    },
    async addCand() {
      if (this.added) return uni.navigateBack()
      try {
        await candidateApi.add('recipe', this.id)
        uni.showToast({ title: '已加入，缺货已代购', icon: 'success' })
        this.added = true
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    async copyToMine() {
      try {
        await recipeApi.copyToMine(this.id)
        uni.showToast({ title: '已存进我的菜谱', icon: 'success' })
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    edit() { uni.navigateTo({ url: `/pages/recipe-edit/recipe-edit?id=${this.id}` }) },
    // 删除自己的菜谱：二次确认后调用后端 DELETE（参考菜谱后端会拒绝，前端也仅在 source=my 显示入口）
    del() {
      uni.showModal({
        title: '删除菜谱',
        content: `确定删除「${this.r.name}」吗？`,
        confirmText: '删除',
        confirmColor: '#e64340',
        success: async (res) => {
          if (!res.confirm) return
          try {
            await recipeApi.del(this.id)
            uni.showToast({ title: '已删除', icon: 'success' })
            setTimeout(() => uni.navigateBack(), 400)
          } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
        }
      })
    },
    // —— viewOnly：开始做 / 计时 ——
    async startCook() {
      if (!this.added) { await candidateApi.add('recipe', this.id); this.added = true }
      await candidateApi.timerStart((await this.candId()))
      this.load()
    },
    async candId() {
      const c = (await candidateApi.list()).find((x) => x.kind === 'recipe' && x.ref_id === this.id)
      return c ? c.id : null
    },
    async stopTiming() { await candidateApi.timerPause((await this.candId())); this.load() },
    async cancelTiming() {
      await candidateApi.timerCancel((await this.candId()))
      this.load()
    },
    fmt(sec) {
      sec = Math.max(0, Math.floor(sec))
      const h = String(Math.floor(sec / 3600)).padStart(2, '0')
      const m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0')
      const s = String(sec % 60).padStart(2, '0')
      return `${h}:${m}:${s}`
    }
  }
}
</script>

<style lang="scss" scoped>
.page { min-height:100vh; background:var(--bg); }
.navbar { display:flex; align-items:center; padding:20rpx 24rpx; padding-top:calc(env(safe-area-inset-top) + 20rpx); background:var(--surface); position:sticky; top:0; z-index:10; }
.nav-back { font-size:30rpx; color:var(--brand); white-space:nowrap; flex-shrink:0; padding-right:20rpx; }
.nav-title { flex:1; text-align:center; font-size:32rpx; font-weight:600; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; padding:0 12rpx; }
.body { padding-bottom:40rpx; }
/* 水平留白放内层 wrapper，border-box 保证全宽子元素不越过 scroll-view 内容右缘 */
.inner { box-sizing:border-box; width:100%; padding:0 24rpx; }
.hero { height:320rpx; border-radius:var(--radius-lg,16rpx); display:flex; align-items:center; justify-content:center; margin-top:16rpx; }
.hero .em { font-size:140rpx; }
.d-title { display:flex; align-items:center; gap:14rpx; margin-top:20rpx; }
.name { font-size:40rpx; font-weight:700; }
.d-meta { color:var(--text-2); font-size:24rpx; margin-top:8rpx; }
.tags { display:flex; gap:10rpx; margin-top:12rpx; }
.t-pill { font-size:22rpx; background:var(--card); color:var(--brand); padding:4rpx 14rpx; border-radius:999rpx; }
.badge { font-size:22rpx; padding:3rpx 14rpx; border-radius:999rpx; }
.b-my { background:#e6f6f3; color:#0f766e; }
.b-ref { background:var(--brand-soft,#efeaff); color:var(--brand); }
.block { background:var(--card); border-radius:var(--radius-lg,16rpx); padding:24rpx; margin-top:20rpx; }
.b-title { font-size:28rpx; font-weight:600; margin-bottom:16rpx; display:flex; align-items:baseline; gap:10rpx; }
.b-title .hint { font-size:20rpx; font-weight:400; color:var(--text-2); }
.step { display:flex; gap:16rpx; margin-bottom:16rpx; }
.step-no { width:44rpx; height:44rpx; border-radius:50%; background:var(--brand); color:#fff; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:24rpx; }
.step-text { flex:1; font-size:28rpx; }
.ing-r { display:flex; align-items:center; gap:16rpx; padding:14rpx 0; border-bottom:1rpx solid var(--border); font-size:28rpx; }
.ck { width:36rpx; height:36rpx; border-radius:50%; box-shadow:inset 0 0 0 2rpx var(--border); color:#fff; font-size:22rpx; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.ck.on { background:#07c160; box-shadow:none; }
.nm { flex:0 1 auto; }
.sp { flex:1; }
.qty { color:var(--text-2); }
.actions.row { display:flex; gap:16rpx; margin-top:28rpx; }
.pbtn.primary { flex:1; }
.pbtn.ghost { flex:1; }
.pbtn.danger { flex:1; color:#e64340; box-shadow:inset 0 0 0 2rpx #e64340; background:#fff5f5; }
.rtime.run { color:var(--brand); font-weight:600; font-size:30rpx; }
.tbtn { font-size:24rpx; padding:14rpx 20rpx; border-radius:999rpx; box-shadow:inset 0 0 0 2rpx var(--brand); color:var(--brand); }
.tbtn.on { background:var(--brand); color:#fff; box-shadow:none; }
.bottom-pad { height:60rpx; }
</style>