<!-- fridge-edit.vue - 新增/编辑食材（对齐第一版UI设计稿 p-fridge-add）
  交互：名称+大类图标预览 / 食材大类点选 / 常用食材快捷 / 在冰箱与待采购 segs 切换。
  在冰箱：存放位置+数量+购买日期+保质期；待采购：数量。
  待采购为累加结构，本页仅支持新增（编辑走冰箱列表删除）。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="uni.navigateBack()">‹</text>
      <text class="ntitle">{{ title }}</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="scroll-inner">
      <view class="add-card">
        <text class="flabel">食材大类（点选）</text>
        <!-- 单行横滑点选 + 左右步进箭头 + 底部滑轨（对齐菜谱页「大类滑动筛选」交互） -->
        <view class="cat-wrap">
          <text class="cat-arrow" :class="{ off: catScroll <= 0 }" @tap="catStep(-1)">‹</text>
          <scroll-view class="cat-scroll" scroll-x :scroll-left="catScroll" @scroll="onCatScroll" :show-scrollbar="false">
            <view class="cat-row">
              <view v-for="c in catOpts" :key="c" class="chip" :class="{ on: form.cat === c }" @tap="form.cat = c">{{ c }}</view>
            </view>
          </scroll-view>
          <text class="cat-arrow" :class="{ off: catScroll >= catMax }" @tap="catStep(1)">›</text>
        </view>
        <view class="cat-track">
          <view class="cat-thumb" :style="{ width: catThumbW + '%', left: catThumbL + '%' }"></view>
        </view>
      </view>

      <view class="add-card">
        <text class="flabel">从食材库点选（{{ activeCat }}）</text>
        <view class="seg-tags" v-if="activeCatIngs.length">
          <view v-for="nm in activeCatIngs" :key="nm" class="chip" :class="{ on: form.name === nm }" @tap="form.name = nm">{{ nm }}</view>
        </view>
        <text class="t-12" v-if="!activeCatIngs.length">{{ activeCat }} 暂无食材，可在下方输入名称自命名或收录</text>
      </view>

      <view class="add-card">
        <text class="flabel">食材名称</text>
        <view class="name-row">
          <view class="add-preview">{{ emPreview }}</view>
          <input class="finput" v-model="form.name" placeholder="自命名，如：虾仁" />
        </view>
        <text class="t-12">点上面的食材名即选中；也可在这里自由输入</text>
        <!-- 收录进食材库：独立维护（与菜谱页「＋ 收录」一致） -->
        <view class="quick-add">
          <input class="quick-input" v-model="quickName" placeholder="新食材？输入并收录进食材库" />
          <text class="quick-btn" @tap="collectIng">＋ 收录</text>
        </view>
      </view>

      <view class="add-card">
        <text class="flabel">库存状态</text>
        <view class="segs" v-if="!id">
          <view class="seg" :class="{ on: type === 'stock' }" @tap="type = 'stock'">🧊 在冰箱</view>
          <view class="seg" :class="{ on: type === 'purchase' }" @tap="type = 'purchase'">🛒 待采购</view>
        </view>

        <view v-if="type === 'stock' || type === 'purchase'" class="stk-fields">
          <view class="field">
            <text class="flabel">数量</text>
            <input class="finput" v-model="qtyText" :placeholder="type === 'stock' ? '例：500g / 3 个' : '要买多少'" />
          </view>
          <view class="field" v-if="type === 'stock'">
            <text class="flabel">存放位置</text>
            <view class="segs">
              <view v-for="s in stores" :key="s" class="seg" :class="{ on: form.store === s }" @tap="form.store = s">{{ s }}</view>
            </view>
          </view>
          <view class="field" v-if="type === 'stock'">
            <text class="flabel">购买日期</text>
            <input class="finput" type="date" v-model="form.buy" />
          </view>
          <view class="field" v-if="type === 'stock'">
            <text class="flabel">保质期（自购买起）</text>
            <view class="segs">
              <view v-for="d in shelfOpts" :key="d.days" class="seg" :class="{ on: form.days === d.days }" @tap="form.days = d.days">{{ d.label }}</view>
            </view>
          </view>
          <text class="t-12">{{ type === 'stock' ? '当前保质期：' + form.days + ' 天' : '已选待采购：保存后记入待采购清单 🛒' }}</text>
        </view>
      </view>

      <view class="pbtn save-btn" @tap="save">保存食材</view>
      <view style="height:60rpx"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { fridgeApi, catApi, ingredientApi } from '@/api'

const stores = ['冷藏', '冷冻', '常温']
const shelfOpts = [
  { label: '1-3 天', days: 2 },
  { label: '一周内', days: 7 },
  { label: '一个月', days: 30 },
  { label: '长期', days: 90 }
]

// 后端 qty 为数字；设计稿用「500g / 3 个」混合文本，拆成 qty + unit
function parseQty(text, fallback) {
  const t = String(text || '').trim()
  if (!t) return fallback
  const m = t.match(/^([\d.]+)\s*([^\d]*)$/)
  if (m) return { qty: parseFloat(m[1]) || 1, unit: m[2] || '份' }
  const n = parseFloat(t)
  return { qty: isNaN(n) ? 1 : n, unit: '份' }
}

export default {
  data() {
    return {
      type: 'stock', id: null, stores, shelfOpts,
      cats: [],            // 食材大类 [{id,name,icon,sort}]，动态加载
      pool: [],            // 食材库 [{name, cat}]，供点选
      catScroll: 0,        // 大类横滑当前偏移(px)
      catViewW: 0,         // 大类容器可视宽度(px)
      catContentW: 0,      // 大类内容总宽(px)，用于算滑轨进度
      quickName: '',       // 快捷收录进食材库的输入
      qtyText: '',
      form: { name: '', cat: '其他', qty: 1, unit: '份', store: '冷藏', buy: '', days: 7 }
    }
  },
  computed: {
    title() {
      if (this.type === 'purchase') return this.id ? '编辑待购' : '新增待购'
      return this.id ? '编辑在库' : '新增食材'
    },
    catOpts() {           // 大类名列表（模板点选用）
      return this.cats.map((c) => c.name)
    },
    emPreview() {          // 大类图标预览（取自食材库维护的图标）
      const c = this.cats.find((x) => x.name === this.form.cat)
      return (c && c.icon) || '🥗'
    },
    activeCat() {          // 当前归类的大类（表单选中值，异常则兜底首个大类）
      const c = this.form.cat
      return this.catOpts.includes(c) ? c : (this.catOpts[0] || '其他')
    },
    activeCatIngs() {      // 当前大类下食材库可点选项（与菜谱页交互一致）
      return this.pool.filter((p) => p.cat === this.activeCat).map((p) => p.name)
    },
    catMax() {             // 大类可横向滚动的最大偏移
      return Math.max(0, this.catContentW - this.catViewW)
    },
    catThumbW() {          // 滑轨 thumb 宽度(%)：可视/内容比例，至少 8%
      return this.catContentW > 0 ? Math.max(8, (this.catViewW / this.catContentW) * 100) : 100
    },
    catThumbL() {          // 滑轨 thumb 左偏移(%)：随滚动进度滑动
      const m = this.catMax
      return m > 0 ? (this.catScroll / m) * (100 - this.catThumbW) : 0
    }
  },
  onReady() {              // 渲染完成后量取大类尺寸，供滑轨进度计算
    this.$nextTick(() => this.measureCat())
  },
  async onLoad(q) {
    this.type = q.type || 'stock'
    try {
      const [cats, ingr] = await Promise.all([catApi.list(), ingredientApi.list()])
      this.cats = cats
      this.pool = ingr.map((x) => ({ name: x.name, cat: x.cat || '其他' }))
    } catch (e) { this.cats = []; this.pool = [] }
    if (q.id) { this.id = Number(q.id); await this.load() }
    this.$nextTick(() => this.measureCat())
  },
  methods: {
    async load() {
      if (this.type === 'purchase') {
        const list = await fridgeApi.purchase()
        const item = list.find((x) => x.id === this.id)
        if (item) {
          this.form.name = item.name
          this.form.unit = item.unit
          this.qtyText = item.qty + item.unit
        }
        return
      }
      const list = await fridgeApi.inStock()
      const item = list.find((x) => x.id === this.id)
      if (item) {
        this.form = { name: item.name, cat: item.cat, qty: item.qty, unit: item.unit, store: item.store || '冷藏', buy: item.buy, days: item.days }
        this.qtyText = item.qty + item.unit
      }
    },
    // 大类滑动实时偏移（驱动滑轨 thumb 与箭头禁用态）
    onCatScroll(e) {
      this.catScroll = e.detail.scrollLeft || 0
    },
    // 左右箭头步进（不到边界才可用；滚到受控偏移后由 onCatScroll 纠正为真实值）
    catStep(dir) {
      const step = (this.catViewW * 0.8) || 200
      this.catScroll = Math.min(this.catMax, Math.max(0, this.catScroll + dir * step))
    },
    // 量取大类可视/内容宽度：可视=scroll-view，内容=内部 .cat-row
    measureCat() {
      const q = uni.createSelectorQuery().in(this)
      q.select('.cat-row').fields({ size: true }, (d) => { if (d) this.catContentW = d.width || 0 })
      q.select('.cat-scroll').fields({ size: true }, (d) => { if (d) this.catViewW = d.width || 0 })
      q.exec()
    },
    // 收录新食材进食材库：创建后重载食材池供点选（与菜谱页「＋ 收录」一致）
    async collectIng() {
      const name = (this.quickName || '').trim()
      if (!name) return uni.showToast({ title: '请输入食材名', icon: 'none' })
      try {
        await ingredientApi.create({ name, cat: this.activeCat || '其他' })
        this.quickName = ''
        const ingr = await ingredientApi.list()
        this.pool = ingr.map((x) => ({ name: x.name, cat: x.cat || '其他' }))
        uni.showToast({ title: '已收录', icon: 'success' })
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    async save() {
      if (!this.form.name.trim()) return uni.showToast({ title: '请输入名称', icon: 'none' })
      const q = parseQty(this.qtyText, { qty: this.form.qty, unit: this.form.unit })
      try {
        if (this.type === 'stock') {
          const data = {
            name: this.form.name.trim(), cat: this.form.cat, qty: q.qty, unit: q.unit,
            store: this.form.store || '', buy: this.form.buy || '', days: this.form.days || 7
          }
          if (this.id) await fridgeApi.updateStock(this.id, data)
          else await fridgeApi.addStock(data)
        } else {
          const data = { name: this.form.name.trim(), qty: q.qty, unit: q.unit }
          if (this.id) await fridgeApi.updatePurchase(this.id, data)
          else await fridgeApi.addPurchase(data)
        }
        uni.showToast({ title: '已保存', icon: 'success' })
        setTimeout(() => uni.navigateBack(), 400)
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; min-height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) 24rpx 16rpx; position:sticky; top:0; background:var(--surface); z-index:10; }
.back { font-size:44rpx; color:var(--text); font-weight:600; }
.ntitle { flex:1; text-align:center; font-size:34rpx; font-weight:700; padding-right:120rpx; }
.nscroll { flex:1; }
.scroll-inner { box-sizing:border-box; width:100%; padding:0 24rpx; }
.save-btn { width:100%; box-sizing:border-box; margin-top:8rpx; }
.add-card { background:var(--card); border:1rpx solid var(--border); border-radius:16rpx; padding:20rpx; margin-bottom:16rpx; }
.flabel { font-size:26rpx; color:var(--text-2); margin-bottom:12rpx; }
.t-12 { font-size:22rpx; color:var(--text-2); }
.quick-add { display:flex; gap:12rpx; margin-top:12rpx; align-items:center; }
.quick-input { flex:1; min-width:0; height:64rpx; line-height:64rpx; padding:0 16rpx; border:1rpx dashed var(--border); border-radius:14rpx; font-size:26rpx; background:var(--bg); box-sizing:border-box; color:var(--text); }
.quick-btn { flex-shrink:0; font-size:24rpx; color:var(--brand); padding:12rpx 20rpx; border-radius:999rpx; box-shadow:inset 0 0 0 2rpx var(--brand); }
.name-row { display:flex; gap:12rpx; align-items:center; }
.add-preview { width:76rpx; height:76rpx; border-radius:16rpx; background:var(--bg); display:flex; align-items:center; justify-content:center; font-size:40rpx; flex:0 0 76rpx; }
.finput { flex:1; width:auto; min-width:0; min-height:80rpx; padding:0 16rpx; border:1rpx solid var(--border); border-radius:14rpx; font-size:28rpx; line-height:80rpx; background:var(--card); color:var(--text); }
.seg-tags { display:flex; gap:12rpx; flex-wrap:wrap; }
.chip { font-size:24rpx; flex-shrink:0; white-space:nowrap; }
.chip.on { background:var(--brand); border-color:var(--brand); color:#fff; }
/* 大类滑动筛选：箭头 + 单行横滑 + 底部滑轨（与菜谱页一致） */
.cat-wrap { display:flex; align-items:center; gap:8rpx; margin:4rpx 0; }
.cat-arrow { flex-shrink:0; width:44rpx; height:44rpx; border-radius:50%; background:var(--bg); color:var(--text-2); display:flex; align-items:center; justify-content:center; font-size:34rpx; line-height:1; }
.cat-arrow.off { opacity:.32; }
.cat-scroll { flex:1; min-width:0; }
.cat-row { display:flex; gap:12rpx; padding:4rpx; box-sizing:border-box; }
.cat-track { position:relative; height:6rpx; background:#E5E3EE; border-radius:3rpx; margin:4rpx 0 6rpx; overflow:hidden; }
.cat-thumb { position:absolute; top:0; bottom:0; background:#bfbce8; border-radius:3rpx; transition:left .15s ease, width .15s ease; }
.segs { display:flex; gap:10rpx; }
.seg { flex:1; text-align:center; padding:14rpx 0; border:1rpx solid var(--border); border-radius:14rpx; font-size:26rpx; background:var(--card); }
.seg.on { background:var(--brand); color:#fff; border-color:var(--brand); }
.field { margin-top:20rpx; }
</style>