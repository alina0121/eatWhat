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
        <scroll-view scroll-x class="f-cat-scroll">
          <view class="f-cat-grid">
            <view
              v-for="c in cats"
              :key="c.name"
              class="chip"
              :class="{ on: form.cat === c.name }"
              @tap="form.cat = c.name"
            >{{ c.icon || '🥗' }} {{ c.name }}</view>
          </view>
        </scroll-view>
      </view>

      <view class="add-card">
        <text class="flabel">从食材库点选（{{ activeCat }}）</text>
        <view class="seg-tags" v-if="activeCatIngs.length">
          <view
            v-for="ing in activeCatIngs"
            :key="ing.name"
            class="chip"
            :class="{ on: form.name === ing.name }"
            @tap="form.name = ing.name; form.cat = activeCat"
          >{{ ing.icon }} {{ ing.name }}</view>
        </view>
        <text class="t-12" v-if="!activeCatIngs.length">{{ activeCat }} 暂无食材，可在下方收录进食材库</text>
      </view>

      <view class="add-card">
        <text class="flabel">食材名称</text>
        <!-- 只读展示：名称只从食材库点选来，不支持自由输入 -->
        <view class="name-row" :class="{ empty: !form.name }">
          <view class="add-preview">{{ emPreview }}</view>
          <text class="name-show" v-if="form.name">{{ form.name }}</text>
          <text class="name-show ph" v-else>请先从上方食材库点选</text>
        </view>
        <text class="t-12">名称唯一来自食材库；没找到可在下方收录</text>
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
            <picker mode="date" :value="form.buy" @change="onBuyPick">
                <view class="date-pick" :class="{ on: form.buy }">
                  <view class="date-l">
                    <text class="date-txt">{{ buyLabel }}</text>
                    <text class="date-sub" v-if="form.buy">· {{ form.buy }}</text>
                  </view>
                  <text class="date-ar">›</text>
                </view>
              </picker>
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
      pool: [],            // 食材库 [{name, cat, icon}]，供点选
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
    emPreview() {          // 大类图标预览（取自食材库维护的图标）
      const c = this.cats.find((x) => x.name === this.form.cat)
      return (c && c.icon) || '🥗'
    },
    activeCat() {          // 当前归类的大类（表单选中值，异常则兜底首个大类）
      const c = this.form.cat
      const names = this.cats.map((x) => x.name)
      return names.includes(c) ? c : (names[0] || '其他')
    },
    activeCatIngs() {      // 当前大类下食材库可点选项（含 icon）
      return this.pool.filter((p) => p.cat === this.activeCat)
    },
    // 购买日期的友好显示：今天/昨天/N天前；无日期时占位
    buyLabel() {
      const v = (this.form.buy || '').trim()
      if (!v) return '选择日期'
      try {
        const bd = new Date(v + 'T00:00:00')
        if (isNaN(bd.getTime())) return v
        const now = new Date()
        const td = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        const diff = Math.round((td - bd) / 86400000)
        if (diff === 0) return '今天'
        if (diff === 1) return '昨天'
        if (diff === 2) return '前天'
        if (diff > 2 && diff < 30) return `${diff} 天前`
        return `${bd.getFullYear()}年${bd.getMonth() + 1}月${bd.getDate()}日`
      } catch (e) { return v }
    }
  },
  async onLoad(q) {
    this.type = q.type || 'stock'
    try {
      const [cats, ingr] = await Promise.all([catApi.list(), ingredientApi.list()])
      this.cats = cats
      this.pool = ingr.map((x) => ({ name: x.name, cat: x.cat || '其他', icon: (x.icon || '').trim() || this.catIconOf(x.cat) }))
    } catch (e) { this.cats = []; this.pool = [] }
    if (q.id) {
      this.id = Number(q.id)
      await this.load()
    } else if (this.type === 'stock') {
      // 新增在库：默认购买日期=今天，避免空值
      this.form.buy = this._today()
    }
  },
  methods: {
    // 今天 YYYY-MM-DD（本地时区），给新增在库作默认购买日期
    _today() {
      const d = new Date()
      const p = (n) => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
    },
    // 根据大类名查 icon（食材自身无 icon 时用大类 icon 兜底）
    catIconOf(catName) {
      const c = this.cats.find((x) => x.name === catName)
      return (c && c.icon) || '🥗'
    },
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
    // 收录新食材进食材库：创建后重载食材池供点选（与菜谱页「＋ 收录」一致）
    async collectIng() {
      const name = (this.quickName || '').trim()
      if (!name) return uni.showToast({ title: '请输入食材名', icon: 'none' })
      try {
        await ingredientApi.create({ name, cat: this.activeCat || '其他' })
        this.quickName = ''
        const ingr = await ingredientApi.list()
        this.pool = ingr.map((x) => ({ name: x.name, cat: x.cat || '其他', icon: (x.icon || '').trim() || this.catIconOf(x.cat) }))
        uni.showToast({ title: '已收录', icon: 'success' })
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // 日期 picker 回调
    onBuyPick(e) { this.form.buy = e.detail.value },
    async save() {
      const name = (this.form.name || '').trim()
      if (!name) return uni.showToast({ title: '请先从食材库点选名称', icon: 'none' })
      // 新增时名称必须在食材库（保证冰箱食材与菜谱食材同源）；编辑时允许保持原名（兼容历史数据）
      const inPool = this.pool.some((p) => p.name === name)
      if (!this.id && !inPool) return uni.showToast({ title: '该食材不在食材库，请先收录', icon: 'none' })
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
.name-row.empty .add-preview { opacity:.5; }
.name-show { flex:1; min-width:0; min-height:80rpx; display:flex; align-items:center; padding:0 16rpx; border:1rpx solid var(--border); border-radius:14rpx; font-size:28rpx; background:var(--card); color:var(--text); }
.name-show.ph { color:#aaa; }
.add-preview { width:76rpx; height:76rpx; border-radius:16rpx; background:var(--bg); display:flex; align-items:center; justify-content:center; font-size:40rpx; flex:0 0 76rpx; }
.finput { flex:1; width:auto; min-width:0; min-height:80rpx; padding:0 16rpx; border:1rpx solid var(--border); border-radius:14rpx; font-size:28rpx; line-height:80rpx; background:var(--card); color:var(--text); }
/* === 日期控件（minimal: 一行显示 + 短控件） === */
.date-pick { display:flex; align-items:center; justify-content:space-between; height:60rpx; padding:0 16rpx; border-radius:10rpx; border:1rpx solid #e4e6ec; background:#fff; transition:all .15s; }
.date-pick.on { border-color:#4b3fe3; background:#4b3fe3; }
.date-l { display:flex; align-items:center; gap:8rpx; min-width:0; flex:1; overflow:hidden; }
.date-txt { font-size:26rpx; color:#333; font-weight:500; white-space:nowrap; }
.date-sub { font-size:20rpx; color:rgba(0,0,0,.4); white-space:nowrap; flex-shrink:0; }
.date-pick.on .date-txt { color:#fff; }
.date-pick.on .date-sub { color:rgba(255,255,255,.7); }
.date-ar { font-size:28rpx; color:#aaa; font-weight:300; line-height:1; flex-shrink:0; margin-left:8rpx; }
.date-pick.on .date-ar { color:rgba(255,255,255,.8); }
.seg-tags { display:flex; gap:12rpx; flex-wrap:wrap; }
.chip { font-size:24rpx; flex-shrink:0; white-space:nowrap; }
.chip.on { background:var(--brand); border-color:var(--brand); color:#fff; }
/* 大类两行横滑（与 mine-ingredients / 首页推荐统一） */
.f-cat-scroll { white-space: nowrap; }
.f-cat-grid { display: grid; grid-template-rows: repeat(2, max-content); grid-auto-flow: column; grid-auto-columns: max-content; gap: 12rpx 10rpx; padding: 4rpx 8rpx 0; }
.f-cat-grid .chip { padding: 10rpx 20rpx; border: 1rpx solid var(--border); border-radius: 999rpx; background: var(--bg); color: var(--text-2); }
.f-cat-grid .chip.on { background: var(--brand); color: #fff; border-color: var(--brand); }
.segs { display:flex; gap:10rpx; }
.seg { flex:1; text-align:center; padding:14rpx 0; border:1rpx solid var(--border); border-radius:14rpx; font-size:26rpx; background:var(--card); }
.seg.on { background:var(--brand); color:#fff; border-color:var(--brand); }
.field { margin-top:20rpx; }
</style>