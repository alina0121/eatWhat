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
          <picker mode="date" :value="f.date" @change="f.date = $event.detail.value">
            <view class="fi date-fi" :class="{ on: f.date }">
              <text class="date-txt">{{ f.date || '选择日期' }}</text>
              <text class="date-ar">›</text>
            </view>
          </picker>
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

      <!-- 曲线图：小程序 WXML 不支持内联 <svg>，故改用绝对定位的 view 绘制 -->
      <view class="section">
        <view class="card">
          <view class="legend">
            <text class="lg"><text class="dot w"></text>体重(kg)</text>
            <text class="lg"><text class="dot f"></text>体脂(%)</text>
          </view>
          <view class="cmeta">近 {{ weights.length || 0 }} 条记录趋势</view>
          <view class="chart">
            <!-- 横向辅助网格 -->
            <view v-for="gy in gridY" :key="'g'+gy" class="gridline" :style="{ top: gy + 'rpx' }"></view>
            <!-- 折线：每条线段 = 起点 + 长度 + 旋转角，拼出连续折线 -->
            <view
              v-for="s in chartSegs"
              :key="s.k"
              class="seg"
              :style="{ left: s.x + 'rpx', top: s.y + 'rpx', width: s.len + 'rpx', background: s.color, transform: 'rotate(' + s.deg + 'deg)' }"
            ></view>
            <!-- 数据点 -->
            <view
              v-for="p in chartDots"
              :key="p.k"
              class="pt"
              :style="{ left: p.x + 'rpx', top: p.y + 'rpx', background: p.color }"
            ></view>
            <!-- X 轴日期(首/末) -->
            <text v-if="weights.length" class="xlab l">{{ weights[0].date }}</text>
            <text v-if="weights.length" class="xlab r">{{ weights[weights.length - 1].date }}</text>
          </view>
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

// 归一化坐标：把一个数值序列映射到图的 [(pad,pad)~(W-pad,H-pad)] 区域（单位 rpx）
// 无效值（如缺失的体脂记录）返回 null，供折线在断点处跳过连线
function layout(vals, W, H, pad) {
  const nums = vals.filter((v) => Number.isFinite(v))
  if (!nums.length) return []
  const min = Math.min(...nums), max = Math.max(...nums), span = (max - min) || 1
  const n = vals.length
  return vals.map((v, i) => {
    if (!Number.isFinite(v)) return null
    const x = pad + (n === 1 ? (W - pad) / 2 : (W - 2 * pad) * i / (n - 1))
    const y = pad + (1 - (v - min) / span) * (H - 2 * pad)
    return { x: +x.toFixed(1), y: +y.toFixed(1), i }
  })
}

export default {
  data() {
    return {
      // W/H/pad 与 .chart 的 rpx 尺寸严格对应，保证旋转角不失真
      weights: [], W: 640, H: 300, pad: 36,
      // 内联表单状态（新增/编辑复用；H5 下 uni.showModal(editable) 不支持，故用页内表单）
      showForm: false, editingId: null, f: { weight: '', fat: '', date: '' },
      series: [
        { key: 'w', color: '#4b3fe3', get: (r) => Number(r.weight) },
        { key: 'f', color: '#f5a623', get: (r) => (r.fat == null ? NaN : Number(r.fat)) }
      ]
    }
  },
  computed: {
    // 各系列的归一化点（含 null 断点）
    seriesPts() {
      return this.series.map((s) => ({
        key: s.key,
        color: s.color,
        pts: layout(this.weights.map(s.get), this.W, this.H, this.pad)
      }))
    },
    // 折线段：仅相邻两个有效点之间连线（缺体脂处自然断开）
    // 每条线用「起点 + 长度 + 旋转角」描述，模板里以绝对定位 + rotate 渲染；
    // 角度在 rpx 坐标空间计算，因 rpx→px 是等比缩放，旋转角与渲染结果一致
    chartSegs() {
      const out = []
      this.seriesPts.forEach((s) => {
        for (let i = 1; i < s.pts.length; i++) {
          const a = s.pts[i - 1], b = s.pts[i]
          if (!a || !b) continue
          const dx = b.x - a.x, dy = b.y - a.y
          out.push({
            k: s.key + '-' + i,
            color: s.color,
            x: a.x,
            y: a.y,
            len: +Math.sqrt(dx * dx + dy * dy).toFixed(1),
            deg: +(Math.atan2(dy, dx) * 180 / Math.PI).toFixed(2)
          })
        }
      })
      return out
    },
    // 数据点圆点（left/top 各减半径 5rpx，使圆心落在坐标点上）
    chartDots() {
      const out = []
      this.seriesPts.forEach((s) => {
        s.pts.forEach((p) => {
          if (!p) return
          out.push({ k: s.key + '-' + p.i, color: s.color, x: +(p.x - 5).toFixed(1), y: +(p.y - 5).toFixed(1) })
        })
      })
      return out
    },
    // 3 条横向辅助网格线，把绘图区四等分
    gridY() {
      if (!this.weights.length) return []
      const s = (this.H - 2 * this.pad) / 4
      return [+(this.pad + s).toFixed(1), +(this.pad + 2 * s).toFixed(1), +(this.pad + 3 * s).toFixed(1)]
    },
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
        // 后端返回 body_fat，前端内部用 fat；此处做字段名对齐
        this.weights = (await weightApi.list()).map((r) => ({
          ...r,
          weight: Number(r.weight),
          fat: r.body_fat != null ? Number(r.body_fat) : null
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
      // 后端字段名是 body_fat，不是 fat
      const data = {
        date: this.f.date || new Date().toISOString().slice(0, 10),
        weight: Number(this.f.weight),
        body_fat: (this.f.fat !== '' && this.f.fat != null && !isNaN(Number(this.f.fat))) ? Number(this.f.fat) : null
      }
      if (this.editingId) await weightApi.update(this.editingId, data)
      else await weightApi.create(data)
      this.showForm = false
      this.load()
    },
    // 删除体重记录：二次确认，失败要提示
    del(w) {
      uni.showModal({
        title: '删除记录', content: `删除 ${w.date} 的体重记录？`, confirmText: '删除', confirmColor: '#e64340',
        success: async (res) => {
          if (!res.confirm) return
          try { await weightApi.del(w.id); this.load() } catch (e) { uni.showToast({ title: e.message || '删除失败', icon: 'none' }) }
        },
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) var(--nav-safe-right) 16rpx 24rpx; }
.back { font-size:48rpx; font-weight:600; }
.ntitle { font-size:36rpx; font-weight:700; flex:1; }
.add { color:var(--brand); font-size:26rpx; }
.nscroll { flex:1; }
.section { padding:12rpx 24rpx; }

/* 内联表单 */
.form { margin-bottom:16rpx; padding:20rpx; background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); }
.fi { background:var(--bg); border-radius:10rpx; height:76rpx; line-height:76rpx; padding:0 16rpx; margin-bottom:12rpx; font-size:26rpx; width:100%; box-sizing:border-box; color:var(--text); }
.date-fi { display:flex; align-items:center; justify-content:space-between; border:1rpx solid var(--border); line-height:1; }
.date-fi.on { border-color:var(--brand); }
.date-txt { font-size:26rpx; color:var(--text); }
.date-fi.on .date-txt { color:var(--brand); }
.date-ar { font-size:28rpx; color:#aaa; font-weight:300; line-height:1; }
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

/* 图表容器用固定 rpx 尺寸：保证宽高比恒定，rotate 角度才与渲染一致；
   rpx→px 为等比缩放，故 640rpx 始终能放进卡片（卡片内宽约 662rpx）。
   不用 <svg>：小程序 WXML 不支持内联 SVG 标签。 */
.chart { position:relative; width:640rpx; height:300rpx; margin:0 auto; }
.gridline { position:absolute; left:36rpx; right:36rpx; height:1rpx; background:#eee; }
.seg { position:absolute; height:3rpx; border-radius:2rpx; transform-origin:0 50%; }
.pt { position:absolute; width:10rpx; height:10rpx; border-radius:50%; border:2rpx solid #fff; box-sizing:border-box; }
.xlab { position:absolute; bottom:0; font-size:18rpx; color:#999; }
.xlab.l { left:36rpx; }
.xlab.r { right:36rpx; }

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
