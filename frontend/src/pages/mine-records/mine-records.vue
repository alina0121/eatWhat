<!-- mine-records.vue —— 饮食记录（对齐第一版UI设计稿 p-records）
  结构：顶部标题＋记一笔 / 当月日历聚合（有记录的天打点）/ 选中日明细 rec-item 列表。
  数据：后端 record 只含 date/name/type(cook|out|delivery)，类型图标按 type 映射，不读不存在的 category。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="back">‹</text>
      <text class="ntitle">饮食记录</text>
      <text class="add" @tap="openAdd">＋ 记一笔</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <!-- 本月日历聚合 -->
      <view class="section">
        <view class="cal">
          <view class="cal-head">
            <text class="cal-m" @tap="prev">‹</text>
            <!-- 点中间的年月可弹出选年月（mode=date fields=month） -->
            <picker mode="date" fields="month" :value="pickerVal" @change="onMonthPick" class="cal-ylp">
              <view class="cal-yr">{{ year }}年{{ month }}月 <text class="c-arrow">▾</text></view>
            </picker>
            <text class="cal-m" @tap="next">›</text>
          </view>
          <view class="cal-grid">
            <text class="dw" v-for="d in ['日','一','二','三','四','五','六']" :key="'w'+d">{{ d }}</text>
            <view class="d blank" v-for="i in lead" :key="'b'+i"></view>
            <view
              class="d"
              :class="{ have: hasRec(day), sel: day === selDay }"
              v-for="day in days"
              :key="'d'+day"
              @tap="pick(day)"
            >{{ day }}</view>
          </view>
        </view>
      </view>

      <!-- 选中日明细 -->
      <view class="section" v-if="selRecords.length">
        <view class="rd-tit">{{ year }}年{{ month }}月{{ selDay }}日</view>
        <view class="rec-item" v-for="(r, i) in selRecords" :key="i">
          <view class="em">{{ typeEmoji(r.type) }}</view>
          <text class="rname">{{ r.name }}</text>
          <view class="stable">{{ typeLabel(r.type) }}</view>
          <text class="op" @tap="openEdit(r)">✎</text>
          <text class="op danger" @tap="del(r)">✕</text>
        </view>
      </view>
      <text class="t-12 empty" v-else-if="loaded">这一天还没记录</text>
    </scroll-view>

    <!-- 记一笔 / 编辑：自绘遮罩弹窗（H5 不支持 uni.showModal editable 且无法自样式，故自绘） -->
    <view class="mask" v-if="form.show" @tap="closeForm">
      <view class="dialog" @tap.stop>
        <text class="d-title">{{ form.id ? '编辑记录' : '记一笔' }}</text>
        <text class="d-lab">类型</text>
        <view class="d-segs">
          <view v-for="t in typeOpts" :key="t.k" class="seg" :class="{ on: form.type === t.k }" @tap="form.type = t.k">{{ t.em }} {{ t.label }}</view>
        </view>
        <text class="d-lab">吃了什么</text>
        <input class="dfi" v-model="form.name" placeholder="例：番茄炒蛋 / 某家水煮牛肉" />
        <text class="d-lab">日期</text>
        <picker mode="date" :value="form.date" @change="onDatePick">
          <view class="dfi d-pick">{{ form.date || '选择日期' }}</view>
        </picker>
        <view class="d-btns">
          <button class="pbtn ghost" @tap="closeForm">取消</button>
          <button class="pbtn" @tap="save">保存</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { recordApi } from '@/api'

const TYPE = {
  cook: { em: '🍳', label: '自己做' },
  out: { em: '🏪', label: '餐厅' },
  delivery: { em: '🛵', label: '外卖' }
}
const typeOpts = Object.keys(TYPE).map((k) => ({ k, em: TYPE[k].em, label: TYPE[k].label }))

export default {
  data() {
    const now = new Date()
    return {
      year: now.getFullYear(), month: now.getMonth() + 1,
      lead: 0, days: [], selDay: now.getDate(),
      dayMap: {}, selRecords: [], loaded: false,
      typeOpts,
      form: { show: false, id: null, name: '', type: 'cook', date: '' }
    }
  },
  computed: {
    pickerVal() { return `${this.year}-${String(this.month).padStart(2, '0')}` }
  },
  async onLoad() {
    this.build()
    await this.load()
    this.pick(this.selDay)
  },
  methods: {
    back() { uni.navigateBack() },
    // 新增：默认落到当前选中日期
    openAdd() {
      this.form = { show: true, id: null, name: '', type: 'cook', date: this.ymd(this.year, this.month, this.selDay) }
    },
    openEdit(r) {
      this.form = { show: true, id: r.id, name: r.name, type: r.type || 'cook', date: r.date || this.ymd(this.year, this.month, this.selDay) }
    },
    closeForm() { this.form.show = false },
    onDatePick(e) { this.form.date = e.detail.value },
    onMonthPick(e) {
      // 点击年月选择器返回 YYYY-MM，跳转到该年月
      const [yy, mm] = e.detail.value.split('-').map(Number)
      this.year = yy; this.month = mm
      this.goMonth()
    },
    ymd(y, m, d) { return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}` },
    async save() {
      if (!this.form.name.trim()) return uni.showToast({ title: '吃了什么不能为空', icon: 'none' })
      const data = { date: this.form.date, name: this.form.name.trim(), type: this.form.type }
      try {
        if (this.form.id) await recordApi.update(this.form.id, data)
        else await recordApi.create(data)
        this.form.show = false
        uni.showToast({ title: '已保存', icon: 'success' })
        // 编辑改日期后，聚焦到保存的日期；否则停留当前日
        const [yy, mm] = this.form.date.split('-').map(Number)
        if (yy !== this.year || mm !== this.month) { this.year = yy; this.month = mm; await this.goMonth()
        } else { await this.load(); this.pick(this.selDay) }
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    async del(r) {
      uni.showModal({
        title: '删除记录', content: `确定删除「${r.name}」这条吗？`, confirmColor: '#e5484d',
        success: async (res) => {
          if (!res.confirm) return
          try {
            await recordApi.del(r.id)
            await this.load(); this.pick(this.selDay)
          } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
        }
      })
    },
    typeEmoji(t) { return (TYPE[t] || { em: '🍽' }).em },
    typeLabel(t) { return (TYPE[t] || { label: t || '正餐' }).label },
    build() {
      const first = new Date(this.year, this.month - 1, 1).getDay()
      const count = new Date(this.year, this.month, 0).getDate()
      this.lead = first
      this.days = Array.from({ length: count }, (_, i) => i + 1)
    },
    hasRec(day) { return !!(this.dayMap[day] && this.dayMap[day].length) },
    async load() {
      try {
        const list = await recordApi.list()
        this.dayMap = {}
        list.forEach((r) => {
          const day = Number((r.date || '').split('-')[2])
          if (!day) return
          ;(this.dayMap[day] = this.dayMap[day] || []).push(r)
        })
        this.loaded = true
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    pick(day) {
      this.selDay = day
      this.selRecords = this.dayMap[day] || []
    },
    prev() { if (this.month <= 1) return; this.month--; this.goMonth() },
    next() { if (this.month >= 12) return; this.month++; this.goMonth() },
    async goMonth() {
      this.build()
      this.selDay = 1
      await this.load()
      this.pick(1)
    }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) 24rpx 16rpx; }
.back { font-size:48rpx; font-weight:600; }
.ntitle { flex:1; text-align:center; font-size:36rpx; font-weight:700; }
.add { font-size:26rpx; color:var(--brand); }
.nscroll { flex:1; }
.section { padding:12rpx 24rpx; }
/* 日历卡片 */
.cal { background:var(--card); border:1rpx solid var(--border); border-radius:20rpx; padding:20rpx; }
.cal-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:14rpx; }
.cal-m { color:var(--brand); font-size:34rpx; padding:0 20rpx; }
.cal-ylp { flex-shrink:0; }
.cal-yr { display:flex; align-items:center; gap:8rpx; font-size:30rpx; font-weight:700; color:var(--brand); padding:6rpx 20rpx; border-radius:999rpx; box-shadow:inset 0 0 0 2rpx var(--brand); }
.c-arrow { font-size:22rpx; opacity:.7; }
.cal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:8rpx; text-align:center; }
.dw { font-size:22rpx; color:var(--text-2); padding:6rpx 0; }
.d { font-size:26rpx; padding:10rpx 0; border-radius:10rpx; }
.d.blank { cursor:default; }
.d.have { background:#efeaff; color:var(--brand); font-weight:600; }
.d.sel { background:var(--brand); color:#fff; font-weight:600; }
/* 选中日明细 */
.rd-tit { font-size:28rpx; font-weight:700; margin:20rpx 0 12rpx; }
.rec-item { display:flex; align-items:center; gap:18rpx; background:var(--card); border:1rpx solid var(--border); border-radius:16rpx; padding:18rpx; margin-bottom:12rpx; }
.em { width:52rpx; height:52rpx; border-radius:14rpx; background:#efeaff; display:flex; align-items:center; justify-content:center; font-size:28rpx; flex:0 0 52rpx; }
.rname { flex:1; font-size:28rpx; }
.stable { font-size:22rpx; color:var(--brand); background:#efeaff; padding:6rpx 16rpx; border-radius:999rpx; }
.op { font-size:30rpx; color:var(--text-2); padding:0 8rpx; flex-shrink:0; }
.op.danger { color:#e5484d; }
.empty { display:block; text-align:center; padding:40rpx 0; }
.t-12 { color:var(--text-2); font-size:24rpx; }
/* 自绘弹窗 */
.mask { position:fixed; left:0; top:0; right:0; bottom:0; background:rgba(0,0,0,0.45); z-index:999; display:flex; align-items:center; justify-content:center; padding:48rpx; }
.dialog { width:100%; max-width:560rpx; background:var(--card); border-radius:20rpx; padding:32rpx; }
.d-title { font-size:32rpx; font-weight:700; display:block; margin-bottom:20rpx; }
.d-lab { font-size:24rpx; color:var(--text-2); display:block; margin:18rpx 0 10rpx; }
.d-segs { display:flex; gap:12rpx; flex-wrap:wrap; }
.d-segs .seg { font-size:24rpx; color:var(--text-2); background:var(--bg); border:1rpx solid var(--border); border-radius:999rpx; padding:12rpx 22rpx; }
.d-segs .seg.on { background:var(--brand); color:#fff; border-color:var(--brand); font-weight:600; }
.dfi { background:var(--bg); border-radius:12rpx; height:84rpx; line-height:84rpx; padding:0 16rpx; font-size:28rpx; width:100%; box-sizing:border-box; color:var(--text); }
.d-pick { display:flex; align-items:center; color:var(--text-2); }
.d-btns { display:flex; gap:16rpx; justify-content:flex-end; margin-top:24rpx; }
</style>