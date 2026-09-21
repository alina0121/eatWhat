<!-- recipe.vue —— 「菜谱 / 吃这些」页
  对齐「第一版 UI」：
  - 顶部标题「吃这些」+ 「按口味筛」横滑 chips
  - 顶部候选收件箱（eat-row 两行卡）：emoji + 菜名 + 类型徽章 + ✕ 移除 + 计时(▶⏸⏹)
  - 候选移除 → 后端按量回退待采购（COOK 一致）；菜谱候选加入 → 缺货代入待采购
  - 计时多道并行：行内直接开始/暂停/取消，running 实时走表
  - 全部菜谱列表（渐变封面）+「+候选」按钮 +「＋ 新建菜谱」
-->
<template>
  <view class="tab-page">
    <!-- 顶部标题（对齐原型 topbar：仅「吃这些」，无计数） -->
    <view class="page-header">
      <text class="page-title">吃这些</text>
    </view>

    <scroll-view class="tab-scroll" scroll-y>
      <!-- ============ 候选收件箱「吃这些」 ============ -->
      <view class="section" v-if="cands.length">
        <view class="cand card" v-for="c in cands" :key="c.id" @tap="openDetail(c)">
          <!-- 第一行：emoji + 菜名 + 类型徽章 -->
          <view class="cand-top">
            <text class="cand-em">{{ c.em }}</text>
            <view class="cand-name">
              <text class="cand-title">{{ c.name }}</text>
              <text class="badge" :class="c.kind === 'shop' ? 'b-shop' : 'b-recipe'">
                {{ c.kind === 'shop' ? '餐厅' : '菜谱' }}
              </text>
            </view>
          </view>
          <!-- 第二行：计时(仅菜谱) + 记一笔 + ✕（对齐原型 tl-bot 布局）
               餐厅是外出用餐、不需在厨房计时，故仅菜谱候选显示计时区 -->
          <view class="cand-bottom">
            <template v-if="c.kind !== 'shop'">
              <template v-if="c.timer && c.timer.running">
                <text class="rtime run">⏱ {{ fmt(c.timer.elapsed) }}</text>
                <text class="tbtn on" @tap.stop="pauseTimer(c)">⏸ 停止</text>
                <text class="tbtn" @tap.stop="cancelTimer(c)">⏹ 取消</text>
              </template>
              <template v-else-if="c.timer">
                <text class="rtime muted">⏱ {{ fmt(c.timer.elapsed) }}</text>
                <text class="tbtn on" @tap.stop="resumeTimer(c)">▶ 继续</text>
                <text class="tbtn" @tap.stop="cancelTimer(c)">⏹ 取消</text>
              </template>
              <template v-else>
                <text class="tbtn on" @tap.stop="startTimer(c)">▶ 计时</text>
              </template>
            </template>
            <text class="tbtn" :class="{ done: dinedToday(c) }" @tap.stop="recordOne(c)">
              {{ dinedToday(c) ? '✓ 已记' : '📝 记一笔' }}
            </text>
            <view class="flex-sp"></view>
            <text class="rm-btn" @tap.stop="removeCand(c)">✕</text>
          </view>
        </view>
      </view>
      <view class="section-empty" v-else>
        <text class="empty-tip">还没想好吃啥，从下面「全部菜谱」或推荐里加几道，点「候选」即可，缺的食材会自动进待采购。</text>
      </view>

      <!-- ============ 按口味筛（独立节标题 + 横滑单行） ============ -->
      <view class="section">
        <view class="sec-tit">按口味筛</view>
        <scroll-view scroll-x class="chips">
          <view
            v-for="f in filterList"
            :key="f.key"
            class="chip"
            :class="{ on: selKey === f.key }"
            @tap="selKey = f.key"
          >{{ f.label }}</view>
        </scroll-view>
      </view>

      <!-- ============ 全部菜谱（标题行右侧为新建入口） ============ -->
      <view class="section">
        <view class="sec-tit">
          全部菜谱
          <text class="newlink" @tap="newRecipe">＋ 新建菜谱</text>
        </view>
        <view class="rec-list">
          <view class="rec-card" v-for="r in shownRecipes" :key="r.id">
            <view class="rec-cover" :style="coverStyle(r)" @tap="openDetailById(r)">
              <text class="rec-em">{{ r.em }}</text>
            </view>
            <view class="rec-info" @tap="openDetailById(r)">
              <view class="rec-name">
                <text>{{ r.name }}</text>
                <text class="badge" :class="r.source === 'admin' ? 'b-ref' : 'b-my'">
                  {{ r.source === 'admin' ? '参考' : '我的' }}
                </text>
              </view>
              <view class="rec-meta">{{ r.time }}分钟 · {{ r.diff }}</view>
              <view class="rec-tags">
                <text class="t-pill" v-for="t in r.tags" :key="t">{{ t }}</text>
              </view>
            </view>
            <text
              class="pbtn small"
              :class="{ added: inCands(r) }"
              @tap="toggleCand(r)"
            >{{ inCands(r) ? '✓ 已选' : '+ 候选' }}</text>
          </view>
        </view>
        <view class="section-empty" v-if="!shownRecipes.length">
          <text class="empty-tip">没有符合条件的菜谱</text>
        </view>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <custom-tab current="recipe" />
  </view>
</template>

<script>
import { recipeApi, candidateApi, recordApi } from '@/api'

// 默认封面渐变（未选固定封面时按 id 轮换），与后端默认种子色彩一致
const WHEEL = [
  'linear-gradient(135deg,#4b3fe3,#8b5cf6)',
  'linear-gradient(135deg,#ec4899,#f97316)',
  'linear-gradient(135deg,#06b6d4,#3b82f6)',
  'linear-gradient(135deg,#10b981,#a3e635)',
  'linear-gradient(135deg,#8b5cf6,#d946ef)',
  'linear-gradient(135deg,#f59e0b,#ef4444)'
]

export default {
  data() {
    return {
      cands: [],        // 吃这些候选（含 timer）
      recipes: [],      // 全部菜谱
      records: [],      // 饮食记录（用于「记一笔」当日去重）
      selKey: '',       // 当前筛选：'' 全部 / 'my' 'admin' 来源 / tag 名
      filterList: [],   // 横滑筛选项 [{key,label}]（预设 + 动态 tag）
      tick: null,       // 计时间隔句柄
      today: ''         // 今天日期 YYYY-MM-DD
    }
  },
  computed: {
    shownRecipes() {
      // 筛选：来源（我的/参考）按 source，其余按口味 tag 精确匹配
      if (this.selKey === 'my') return this.recipes.filter((r) => r.source === 'my')
      if (this.selKey === 'admin') return this.recipes.filter((r) => r.source === 'admin')
      if (!this.selKey) return this.recipes
      return this.recipes.filter((r) => (r.tags || []).includes(this.selKey))
    }
  },
  onShow() {
    this.today = new Date().toISOString().slice(0, 10)
    this.load()
    // 启动实时走表：每秒对 running 的候选 elapsed+1（与后端同公式，保持一致）
    this.tick = setInterval(() => {
      this.cands.forEach((c) => {
        if (c.timer && c.timer.running) c.timer.elapsed += 1
      })
    }, 1000)
  },
  onHide() {
    clearInterval(this.tick)
  },
  onUnload() {
    clearInterval(this.tick)
  },
  methods: {
    async load() {
      try {
        const [cands, recipes, records] = await Promise.all([candidateApi.list(), recipeApi.list(), recordApi.list()])
        this.cands = cands
        this.recipes = recipes
        this.records = records
        this.buildFilterList()
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    // 组装横滑筛选项：对齐第一版预设（全部/快手/🌶辣/素/下饭/来源）+ 动态口味 tag
    buildFilterList() {
      const preset = [
        { key: '', label: '全部' },
        { key: '快手', label: '快手' },
        { key: '辣', label: '🌶 辣' },
        { key: '素', label: '素' },
        { key: '下饭', label: '下饭' },
        { key: 'my', label: '我的菜谱' },
        { key: 'admin', label: '参考菜谱' }
      ]
      const presetKeys = preset.map((f) => f.key)
      const list = [...preset]
      this.recipes.forEach((r) => (r.tags || []).forEach((t) => {
        if (!presetKeys.includes(t) && !list.some((f) => f.key === t)) list.push({ key: t, label: t })
      }))
      this.filterList = list
    },
    fmt(sec) {
      sec = Math.max(0, Math.floor(sec))
      const h = String(Math.floor(sec / 3600)).padStart(2, '0')
      const m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0')
      const s = String(sec % 60).padStart(2, '0')
      return `${h}:${m}:${s}`
    },
    // —— 「记一笔」：当天已记录则置灰，样式与原型 recBtn 一致 ——
    dinedToday(c) {
      // 相同菜名在当天已有记录即视为已记（对齐原型按 name+当天去重）
      return this.records.some((r) => r.date === this.today && r.name === c.name)
    },
    async recordOne(c) {
      if (this.dinedToday(c)) return
      // 类型：菜谱→自己做 cook，餐厅→外卖 out
      const type = c.kind === 'shop' ? 'out' : 'cook'
      try {
        await recordApi.create({ name: c.name, date: this.today, type })
        await this.load()
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    inCands(r) {
      return this.cands.some((c) => c.kind === 'recipe' && c.ref_id === r.id)
    },
    // 封面背景：优先用所选的固定封面渐变（后端 coverGrad）；未选则按 id 轮换默认渐变
    coverStyle(r) {
      return { background: r.coverGrad || WHEEL[(r.id % WHEEL.length)] }
    },
    openDetailById(r) {
      uni.navigateTo({ url: `/pages/recipe-detail/recipe-detail?id=${r.id}` })
    },
    // —— 候选：加入 / 移除（后端处理待采购代入与回退）——
    async toggleCand(r) {
      if (this.inCands(r)) {
        const c = this.cands.find((x) => x.kind === 'recipe' && x.ref_id === r.id)
        await this.removeCand(c)
        return
      }
      try {
        await candidateApi.add('recipe', r.id)
        await this.load()
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    async removeCand(c) {
      try {
        await candidateApi.remove(c.id)
        await this.load()
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    // —— 计时：多道并行，行内操作 ——
    async startTimer(c) {
      await candidateApi.timerStart(c.id)
      await this.load()
    },
    async resumeTimer(c) {
      await candidateApi.timerStart(c.id)
      await this.load()
    },
    async pauseTimer(c) {
      try {
        await candidateApi.timerPause(c.id)
        await this.load()
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    async cancelTimer(c) {
      await candidateApi.timerCancel(c.id)
      await this.load()
    },
    // —— 详情 / 新建（本轮先占位，后续独立页面）——
    openDetail(c) {
      // 从中吃这些进入 → viewOnly（详情显示「开始做」/计时，不显示候选/编辑）
      if (c.kind === 'recipe' && c.ref_id) {
        uni.navigateTo({ url: `/pages/recipe-detail/recipe-detail?id=${c.ref_id}&from=eat` })
      } else if (c.kind === 'shop' && c.ref_id) {
        uni.navigateTo({ url: `/pages/shop-detail/shop-detail?id=${c.ref_id}` })
      }
    },
    newRecipe() {
      uni.navigateTo({ url: '/pages/recipe-edit/recipe-edit' })
    }
  }
}
</script>

<style lang="scss" scoped>
.page-header {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
  padding: 20rpx 24rpx;
  padding-top: calc(env(safe-area-inset-top) + 20rpx);
}
.page-title { font-size: 44rpx; font-weight: 700; }
.page-sub { font-size: 26rpx; color: var(--text-2); }

.section { padding: 12rpx 24rpx; }
.section-empty { padding: 40rpx 24rpx; text-align: center; }
.empty-tip { color: var(--text-2); font-size: 26rpx; }

/* 候选卡（对齐原型 eat-row：第一行 emoji+菜名+徽章，第二行计时/记一笔/✕） */
.cand { margin-bottom: 16rpx; }
.cand-top { display: flex; align-items: center; gap: 16rpx; }
.cand-em { font-size: 48rpx; }
.cand-name { flex: 1; display: flex; align-items: center; gap: 12rpx; }
.cand-title { font-size: 30rpx; font-weight: 600; }
.cand-bottom { display: flex; align-items: center; margin-top: 18rpx; gap: 12rpx; }
.flex-sp { flex: 1; }
.rm-btn { color: var(--text-2); font-size: 30rpx; padding: 8rpx; }

/* 计时（原型 tbtn / rtime） */
.rtime { font-variant-numeric: tabular-nums; font-size: 28rpx; margin-right: 6rpx; }
.rtime.run { color: var(--brand); font-weight: 600; }
.rtime.muted { color: var(--text-2); }
.tbtn {
  font-size: 24rpx; color: var(--text-2); padding: 8rpx 18rpx;
  border-radius: 999rpx; box-shadow: inset 0 0 0 2rpx var(--border);
}
.tbtn.on { color: var(--brand); box-shadow: inset 0 0 0 2rpx var(--brand); background: var(--brand-soft, #efeaff); }
.tbtn.done { color: var(--text-2); opacity: .5; box-shadow: none; background: var(--surface); }

.badge { font-size: 20rpx; padding: 2rpx 12rpx; border-radius: 999rpx; }
.b-recipe { background: #efeaff; color: var(--brand); }
.b-shop { background: #fff3e0; color: #f57c00; }

/* 节标题（对齐原型 sec-tit） */
.sec-tit {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 32rpx; font-weight: 700; margin: 6rpx 0 16rpx; padding-top: 8rpx;
}
.newlink { color: var(--brand); font-size: 26rpx; font-weight: 400; flex-shrink: 0; }

/* 口味筛选横滑单行 */
.chips { white-space: nowrap; width: 100%; }
.chips .chip { margin-right: 12rpx; }

/* 菜谱列表（对齐原型 rec-list：横向卡片行） */
.rec-list { display: flex; flex-direction: column; gap: 20rpx; }
.rec-card {
  display: flex; align-items: center; gap: 20rpx;
  background: var(--card); border: 1rpx solid var(--border); border-radius: var(--radius-lg,16rpx);
  padding: 20rpx;
}
.rec-cover {
  width: 124rpx; height: 124rpx; border-radius: 24rpx; flex: 0 0 124rpx;
  display: flex; align-items: center; justify-content: center;
}
.rec-em { font-size: 60rpx; }
.rec-info { flex: 1; min-width: 0; }
.rec-name { font-size: 30rpx; font-weight: 600; display: flex; align-items: center; gap: 10rpx; }
.rec-meta { font-size: 22rpx; color: var(--text-2); margin-top: 4rpx; }
.rec-tags { display: flex; gap: 8rpx; margin-top: 8rpx; flex-wrap: wrap; }
.t-pill { font-size: 20rpx; color: var(--text-2); background: var(--bg); padding: 2rpx 10rpx; border-radius: 999rpx; }
.pbtn.small { font-size: 24rpx; padding: 10rpx 20rpx; flex-shrink: 0; }
.pbtn.added { background: #07c160; }

/* 默认封面渐变已内联于 coverStyle；旧 id%6 轮换样式移除 */

/* 徽章：我的=青，参考=紫（对齐 type-badge） */
.badge { font-size: 20rpx; padding: 2rpx 12rpx; border-radius: 999rpx; }
.b-my { background: #e6f6f3; color: #0f766e; }
.b-ref { background: var(--brand-soft, #efeaff); color: var(--brand); }

.tab-pad { height: 40rpx; }
</style>