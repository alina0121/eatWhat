<!-- mine-weight.vue —— 体重：最新概览(环比) + 近30天曲线(体重/体脂, 带数据点) + 记一笔/编辑/删除 -->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="back">‹</text>
      <text class="ntitle">体重</text>
      <text class="add" @tap="add()">＋ 记一笔</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <!-- 新增/编辑内联表单（H5/App/小程序通用；注释：uni.showModal(editable) 在 H5 不支持） -->
      <view class="section" v-if="showForm">
        <view class="form">
          <input v-model="f.weight" type="digit" placeholder="体重(kg)" class="fi" />
          <input v-model="f.fat" type="digit" placeholder="体脂(% 可省)" class="fi" />
          <input v-model="f.date" placeholder="日期 YYYY-MM-DD(可省)" class="fi" />
          <view class="form-btns">
            <button class="pbtn ghost" @tap="showForm = false">取消</button>
            <button class="pbtn" @tap="save">{{ editingId ? '保存修改' : '保存' }}</button>
          </view>
        </view>
      </view>

      <!-- 最新值概览 -->
      <view class="section">
        <view class="card ov">
          <view class="ov-main">
            <text class="ov-val">{{ latestText }}</text>
            <text class="ov-unit">kg 当前</text>
          </view>
          <view class="ov-fat" v-if="latestFat != null">
            <text class="ov-val2">{{ latestFat }}<text class="ov-unit2">% 体脂</text></text>
          </view>
          <view class="ov-diff">
            <text class="d-emoji">{{ diffEmoji }}</text>
            <text class="d-txt">{{ diffText }}</text>
          </view>
        </view>
      </view>

      <!-- 曲线图 -->
      <view class="section">
        <view class="card">
          <view class="legend">
            <text class="lg"><text class="dot w"></text>体重(kg)</text>
            <text class="lg"><text class="dot f"></text>体脂(%)</text>
          </view>
          <view class="cmeta">近 {{ weights.length || 0 }} 条记录趋势</view>
          <svg :viewBox="`0 0 ${W} ${H}`" class="chart">
            <!-- 横向辅助网格 -->
            <line v-for="gy in gridY" :key="gy" :x1="pad" :y1="gy" :x2="W - pad" :y2="gy" stroke="#eee" stroke-width="1"/>
            <!-- 折线 -->
            <path v-for="s in charts" :key="s.key" :d="s.path" fill="none" :stroke="s.color" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            <!-- 数据点 -->
            <g v-for="p in sPoints" :key="'g'+p.key">
              <circle v-for="pt in p.pts" :key="'p'+pt.i" :cx="pt.x" :cy="pt.y" r="3.5" :fill="p.color" stroke="#fff" stroke-width="1.5"/>
            </g>
            <!-- X 轴日期(首/末) -->
            <text v-if="weights.length" :x="pad" :y="H-4" font-size="9" fill="#999">{{ weights[0].date }}</text>
            <text v-if="weights.length" :x="W-pad" :y="H-4" font-size="9" fill="#999" text-anchor="end">{{ weights[weights.length-1].date }}</text>
          </svg>
          <view v-if="!weights.length" class="empty">还没有记录，点击右上角记一笔</view>
        </view>
      </view>

      <!-- 列表（点条目可修改） -->
      <view class="section">
        <view class="card wrow" v-for="w in weights" :key="w.id" @tap="add(w)">
          <view>
            <text class="wdate">{{ w.date }}</text>
            <text class="wval">{{ w.weight }} kg</text>
          </view>
          <view class="wright">
            <text class="fat" v-if="w.fat">体脂 {{ w.fat }}%</text>
            <text class="op edit">改</text>
            <text class="op danger" @tap.stop="del(w)">✕</text>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { weightApi } from '@/api'

// 归一化坐标：把一个数值序列映射到图的 [(pad,pad)~(W-pad,H-pad)] 区域
function layout(vals, W, H, pad) {
  if (!vals.length) return []
  const min = Math.min(...vals), max = Math.max(...vals), span = (max - min) || 1
  const n = vals.length
  return vals.map((v, i) => {
    const x = pad + (n === 1 ? (W - pad) / 2 : (W - 2 * pad) * i / (n - 1))
    const y = pad + (1 - (v - min) / span) * (H - 2 * pad)
    return { x: +x.toFixed(1), y: +y.toFixed(1), i }
  })
}

export default {
  data() {
    return {
      weights: [], W: 320, H: 150, pad: 26,
      // 内联表单状态（新增/编辑复用；H5 下 uni.showModal(editable) 不支持，故用页内表单）
      showForm: false, editingId: null, f: { weight: '', fat: '', date: '' },
      series: [
        { key: 'w', color: '#4b3fe3', get: (r) => Number(r.weight) },
        { key: 'f', color: '#f5a623', get: (r) => (r.fat == null ? NaN : Number(r.fat)) }
      ]
    }
  },
  computed: {
    charts() {
      return this.series.map((s) => {
        const pts = layout(this.weights.map(s.get), this.W, this.H, this.pad)
        return {
          ...s,
          path: pts.map((p, i) => (i === 0 ? 'M' : 'L') + p.x + ' ' + p.y).join(' ')
        }
      })
    },
    // 数据点坐标（供所有系列圆点渲染）
    sPoints() {
      return this.charts.map((s) => {
        const pts = layout(this.weights.map(s.get), this.W, this.H, this.pad)
        return { key: s.key, color: s.color, pts }
      })
    },
    gridY() { return this.charts.length ? [this.pad + 30, this.pad + 60, this.H - this.pad - 30] : [] },
    // —— 最新概览 ——
    latestW() { return this.weights.length ? this.weights[this.weights.length - 1].weight : null },
    latestFat() { return this.weights.length ? this.weights[this.weights.length - 1].fat : null },
    diffEmoji() {
      if (this.weights.length < 2) return '—'
      const d = this.weights[this.weights.length - 1].weight - this.weights[this.weights.length - 2].weight
      return d > 0.1 ? '📈' : d < -0.1 ? '📉' : '➖'
    },
    diffText() {
      if (this.weights.length < 2) return '再记一笔看变化'
      const d = this.weights[this.weights.length - 1].weight - this.weights[this.weights.length - 2].weight
      if (Math.abs(d) < 0.1) return '与上次持平'
      return (d > 0 ? '较上次 +' : '较上次 ') + d.toFixed(1) + ' kg'
    },
    latestText() {
      const v = this.latestW
      return v == null ? '—' : v
    }
  },
  onShow() { this.load() },
  methods: {
    back() { uni.navigateBack() },
    async load() {
      try {
        this.weights = (await weightApi.list()).map((r) => ({
          ...r, weight: Number(r.weight), fat: r.fat != null ? Number(r.fat) : null
        }))
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // 打开表单：无参=新增；传 w=编辑回填（点条目可修改）
    add(w) {
      this.showForm = true
      this.editingId = w ? w.id : null
      this.f = w
        ? { weight: String(w.weight), fat: w.fat != null ? String(w.fat) : '', date: w.date }
        : { weight: '', fat: '', date: new Date().toISOString().slice(0, 10) }
    },
    async save() {
      if (!this.f.weight || isNaN(Number(this.f.weight))) return uni.showToast({ title: '体重必须为数字', icon: 'none' })
      const data = { date: this.f.date || new Date().toISOString().slice(0, 10), weight: Number(this.f.weight) }
      if (this.f.fat && !isNaN(Number(this.f.fat))) data.fat = Number(this.f.fat)
      if (this.editingId) await weightApi.update(this.editingId, data)
      else await weightApi.create(data)
      this.showForm = false
      this.load()
    },
    async del(w) {
      await weightApi.del(w.id)
      this.load()
    }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) 24rpx 16rpx; }
.back { font-size:48rpx; font-weight:600; }
.ntitle { font-size:36rpx; font-weight:700; flex:1; }
.add { color:var(--brand); font-size:26rpx; }
.nscroll { flex:1; }
.section { padding:12rpx 24rpx; }

/* 内联表单 */
.form { margin-bottom:16rpx; padding:20rpx; background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); }
.fi { background:var(--bg); border-radius:10rpx; height:76rpx; line-height:76rpx; padding:0 16rpx; margin-bottom:12rpx; font-size:26rpx; width:100%; box-sizing:border-box; color:var(--text); }
.form-btns { display:flex; gap:16rpx; justify-content:flex-end; }

/* 最新概览 */
.ov { display:flex; align-items:center; gap:24rpx; margin-bottom:16rpx; }
.ov-main { display:flex; align-items:baseline; gap:8rpx; }
.ov-val { font-size:64rpx; font-weight:700; color:var(--brand); line-height:1; }
.ov-unit { font-size:22rpx; color:var(--text-2); }
.ov-fat { margin-left:auto; text-align:right; }
.ov-val2 { font-size:28rpx; font-weight:600; color:var(--warning); }
.ov-unit2 { font-size:20rpx; color:var(--text-2); }
.ov-diff { display:flex; flex-direction:column; align-items:flex-end; gap:2rpx; }
.d-emoji { font-size:28rpx; }
.d-txt { font-size:22rpx; color:var(--text-2); }

.legend { display:flex; gap:24rpx; margin-bottom:8rpx; font-size:22rpx; color:var(--text-2); align-items:center; }
.lg { display:flex; align-items:center; gap:8rpx; }
.dot { width:16rpx; height:16rpx; border-radius:50%; }
.dot.w { background:var(--brand); }
.dot.f { background:var(--warning); }
.cmeta { font-size:22rpx; color:var(--text-2); margin-bottom:8rpx; }
.chart { width:100%; height:300rpx; }
.empty { color:var(--text-2); text-align:center; padding:40rpx 0; }
.wrow { margin-bottom:16rpx; display:flex; align-items:center; justify-content:space-between; }
.wdate { color:var(--text-2); font-size:24rpx; margin-right:16rpx; }
.wval { font-size:32rpx; font-weight:700; }
.wright { display:flex; align-items:center; gap:16rpx; }
.fat { font-size:22rpx; color:var(--warning); }
.op { font-size:24rpx; }
.op.edit { color:var(--brand); }
.danger { color:var(--danger); }
</style>