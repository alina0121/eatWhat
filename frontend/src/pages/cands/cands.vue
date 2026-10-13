<!-- cands.vue —— 底部「吃这些」tab 页（候选收件箱，原菜谱页顶部迁出）
  - 空间切换：我的（个人池，候选卡可「+家庭空间」一键共享）/ 家庭空间（家庭成员共享池，人人可删/启停计时）
  - 候选卡：emoji + 菜名 + 类型徽章 + ✕ 移除 + 计时(▶⏸⏹) + 记一笔 + 「+家庭空间」共享开关（显示「✓ 家庭池」=已在池内，再点移出）
  - 候选移除 → 后端按量回退待采购（COOK 一致）；菜谱候选加入 → 缺货代入待采购
  - 计时多道并行：行内直接开始/暂停/取消，running 实时走表
  - 餐厅候选只进「吃这些」，不参与采购计算
-->
<template>
  <view class="tab-page">
    <view class="page-header">
      <text class="page-title">吃这些</text>
    </view>

    <!-- 空间切换：家庭池里的候选全家人共享（加菜入口在「我的」候选卡上） -->
    <view class="space-bar">
      <text class="chip" :class="{ on: space === 'mine' }" @tap="switchSpace('mine')">我中意</text>
      <text class="chip" :class="{ on: space === 'family' }" @tap="switchSpace('family')">家庭空间{{ family ? ' · ' + family.name : '' }}</text>
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
            <text class="tbtn fam" :class="{ in: inFam(c) }" v-if="space === 'mine' && family" @tap.stop="addToFamily(c)">{{ inFam(c) ? '✓ 家庭池' : '+家庭空间' }}</text>
            <view class="flex-sp"></view>
            <text class="rm-btn" @tap.stop="removeCand(c)">✕</text>
          </view>
        </view>
      </view>
      <!-- 空态：家庭空间未加入 / 家庭池为空 / 个人池为空 三种文案 -->
      <view class="section-empty" v-else>
        <template v-if="space === 'family'">
          <template v-if="!family">
            <text class="empty-tip">还没加入家庭空间。</text>
            <text class="empty-go" @tap="goFamily">去「我的 → 家庭」创建或加入 ›</text>
          </template>
          <template v-else>
            <text class="empty-tip">家庭候选池还是空的，在「我中意」里点候选卡上的「+家庭空间」即可共享。</text>
          </template>
        </template>
        <text class="empty-tip" v-else>还没想好吃啥，去「选菜」或「推荐」里加几道，点「+候选」即可，缺的食材会自动进待采购。</text>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <custom-tab current="cands" />
  </view>
</template>

<script>
import { candidateApi, recordApi, familyApi, getCurUser } from '@/api'

export default {
  data() {
    return {
      cands: [],   // 吃这些候选（含 timer）
      famCands: [],// 家庭池候选（「+家庭空间」按钮的 ✓已加 状态与取消用）
      records: [], // 饮食记录（用于「记一笔」当日去重）
      tick: null,  // 计时间隔句柄
      today: '',   // 今天日期 YYYY-MM-DD
      space: 'mine',         // mine 个人池 | family 家庭共享池
      family: null           // 我的家庭空间（null=未加入）
    }
  },
  onShow() {
    this.today = new Date().toISOString().slice(0, 10)
    this.load()
    // 家庭信息（空间 chip 文案与家庭池入口用；未登录静默置空）
    familyApi.mine().then((r) => { this.family = r.family || null }).catch(() => { this.family = null })
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
        const [cands, records, famCands] = await Promise.all([
          candidateApi.list(this.space),
          recordApi.list(),
          // 家庭池列表：驱动「+家庭空间」按钮的已加状态（未加入家庭时后端返回空，兜底空数组）
          candidateApi.list('family').catch(() => []),
          // 切到家庭池时顺带刷新家庭信息（他人刚建/刚加入也能及时看到）
          this.space === 'family'
            ? familyApi.mine().then((r) => { this.family = r.family || null }).catch(() => {})
            : Promise.resolve()
        ])
        this.cands = cands
        this.records = records
        this.famCands = famCands
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    switchSpace(s) {
      if (s === this.space) return
      if (s === 'family' && !this.family) {
        // 未加入家庭：引导去家庭页，不切换
        uni.showModal({
          title: '家庭空间',
          content: '还没加入家庭空间，去「我的 → 家庭」创建或凭 6 位家庭 ID 加入？',
          confirmText: '去家庭页',
          success: (res) => { if (res.confirm) this.goFamily() }
        })
        return
      }
      this.space = s
      this.load()
    },
    goFamily() {
      uni.navigateTo({ url: '/pages/family/family' })
    },
    // —— 共享开关：+家庭空间 一键加入家庭池；✓ 已加 再次点击移出（同款判断「✓ 已选」）——
    inFam(c) {
      // 同 kind + ref_id 在家庭池里唯一（后端空间查重保证）
      return this.famCands.some((f) => f.kind === c.kind && f.ref_id === c.ref_id)
    },
    async addToFamily(c) {
      try {
        if (this.inFam(c)) {
          // 取消共享：移出家庭池（若他人加的，账目由后端回退到加者）
          const f = this.famCands.find((x) => x.kind === c.kind && x.ref_id === c.ref_id)
          if (f) await candidateApi.remove(f.id)
          uni.showToast({ title: '已从家庭池移出', icon: 'none' })
        } else {
          await candidateApi.add(c.kind, c.ref_id, getCurUser(), 'family')
          uni.showToast({ title: '已加入家庭池', icon: 'success' })
        }
        this.load()
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
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

/* 空间切换 chips（我的 / 家庭空间） */
.space-bar { display: flex; align-items: center; gap: 12rpx; padding: 4rpx 24rpx 8rpx; }
.chip { font-size: 24rpx; color: var(--text-2); padding: 10rpx 24rpx; border-radius: 999rpx; box-shadow: inset 0 0 0 2rpx var(--border); }
.chip.on { color: var(--brand); box-shadow: inset 0 0 0 2rpx var(--brand); background: var(--brand-soft, #efeaff); font-weight: 600; }
.empty-go { display: block; margin-top: 16rpx; color: var(--brand); font-size: 26rpx; }

.section { padding: 12rpx 24rpx; }
.section-empty { padding: 40rpx 24rpx; text-align: center; }
.empty-tip { color: var(--text-2); font-size: 26rpx; }

/* 候选卡（对齐原型 eat-row：第一行 emoji+菜名+徽章，第二行计时/记一笔/✕） */
.cand { margin-bottom: 16rpx; }
.cand-top { display: flex; align-items: center; gap: 16rpx; }
.cand-em { font-size: 48rpx; }
.cand-name { flex: 1; display: flex; align-items: center; gap: 12rpx; }
.cand-title { font-size: 30rpx; font-weight: 600; }
.cand-bottom { display: flex; align-items: center; flex-wrap: wrap; margin-top: 18rpx; gap: 12rpx; }
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
.tbtn.fam { color: var(--brand); box-shadow: inset 0 0 0 2rpx var(--brand); }
.tbtn.fam.in { color: var(--text-2); opacity: .55; box-shadow: inset 0 0 0 2rpx var(--border); background: var(--surface); }
.tbtn.done { color: var(--text-2); opacity: .5; box-shadow: none; background: var(--surface); }

.badge { font-size: 20rpx; padding: 2rpx 12rpx; border-radius: 999rpx; }
.b-recipe { background: #efeaff; color: var(--brand); }
.b-shop { background: #fff3e0; color: #f57c00; }

.tab-pad { height: 40rpx; }
</style>
