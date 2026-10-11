<!-- cands.vue —— 底部「吃这些」tab 页（候选收件箱，原菜谱页顶部迁出）
  - 候选卡：emoji + 菜名 + 类型徽章 + ✕ 移除 + 计时(▶⏸⏹) + 记一笔
  - 候选移除 → 后端按量回退待采购（COOK 一致）；菜谱候选加入 → 缺货代入待采购
  - 计时多道并行：行内直接开始/暂停/取消，running 实时走表
  - 餐厅候选只进「吃这些」，不参与采购计算
-->
<template>
  <view class="tab-page">
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
        <text class="empty-tip">还没想好吃啥，去「选菜」或「推荐」里加几道，点「+候选」即可，缺的食材会自动进待采购。</text>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <custom-tab current="cands" />
  </view>
</template>

<script>
import { candidateApi, recordApi } from '@/api'

export default {
  data() {
    return {
      cands: [],   // 吃这些候选（含 timer）
      records: [], // 饮食记录（用于「记一笔」当日去重）
      tick: null,  // 计时间隔句柄
      today: ''    // 今天日期 YYYY-MM-DD
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
        const [cands, records] = await Promise.all([candidateApi.list(), recordApi.list()])
        this.cands = cands
        this.records = records
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    fmt(sec) {
      sec = Math.max(0, Math.floor(sec))
      const h = String(Math.floor(sec / 3600)).padStart(2, '0')
      const m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0')
      const s = String(sec % 60).padStart(2, '0')
      return `${h}:${m}:${s}`
    },
    // —— 「记一笔」：当天已记录则置灰 ——
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
    // 候选点击进详情（菜谱详情 viewOnly，显示「开始做」/计时）
    openDetail(c) {
      if (c.kind === 'recipe' && c.ref_id) {
        uni.navigateTo({ url: `/pages/recipe-detail/recipe-detail?id=${c.ref_id}&from=eat` })
      } else if (c.kind === 'shop' && c.ref_id) {
        uni.navigateTo({ url: `/pages/shop-detail/shop-detail?id=${c.ref_id}` })
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.page-header {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
  padding: 20rpx var(--nav-safe-right) 20rpx 24rpx;
  padding-top: calc(env(safe-area-inset-top) + 20rpx);
}
.page-title { font-size: 44rpx; font-weight: 700; }

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

.tab-pad { height: 40rpx; }
</style>
