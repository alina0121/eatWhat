<!-- recipe-edit.vue —— 新建/编辑我的菜谱（对齐第一版UI设计稿 p-recipe-new）
  交互：菜名输入 / 耗时+难度 segs 分段 / 口味标签 chips 多选 / 所需食材从「我的食材」池勾选 / 步骤教程每行一步。
  缺货代入待采购在候选环节处理，这里仅记录结构化 ing。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="uni.navigateBack()">‹</text>
      <text class="ntitle">{{ id ? '编辑菜谱' : '新建菜谱' }}</text>
      <text class="save" @tap="save">保存</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="scroll-inner">
      <!-- 菜名：label 与输入框同一行 -->
      <view class="add-card name-row">
        <text class="flabel">菜名</text>
        <input class="finput" v-model="form.name" placeholder="请输入菜名" />
      </view>

      <!-- 封面：从管理员维护的固定封面图库点选（默认=走默认轮换渐变） -->
      <view class="add-card">
        <text class="flabel">封面 <text class="t-12">从图库点选</text></text>
        <scroll-view scroll-x class="cover-scroll" :show-scrollbar="false">
          <view class="cover-row">
            <view class="cover-item" :class="{ on: coverId === '' }" @tap="pickCover('')">
              <view class="cover-box" :style="{ background: DEFAULT_GRAD }"><text class="cover-em">🍽</text></view>
              <text class="cover-name">默认</text>
            </view>
            <view
              class="cover-item"
              v-for="c in covers"
              :key="c.id"
              :class="{ on: String(coverId) === String(c.id) }"
              @tap="pickCover(c)"
            >
              <view class="cover-box" :style="{ background: c.grad }"><text class="cover-em">{{ c.emoji }}</text></view>
              <text class="cover-name">{{ c.name || ('封面 ' + c.id) }}</text>
            </view>
          </view>
        </scroll-view>
      </view>

      <!-- 耗时 / 难度 -->
      <view class="add-card">
        <text class="flabel">耗时 / 难度</text>
        <view class="segs">
          <view v-for="t in timeOpts" :key="t" class="seg" :class="{ on: timeTick(t) }" @tap="setTime(t)">{{ t }}</view>
        </view>
        <view class="segs" style="margin-top:10rpx">
          <view v-for="d in diffOpts" :key="d" class="seg" :class="{ on: form.diff === d }" @tap="form.diff = d">{{ d }}</view>
        </view>
      </view>

      <!-- 口味标签（可多选） -->
      <view class="add-card">
        <text class="flabel">口味标签 <text class="t-12">可多选</text></text>
        <view class="seg-tags">
          <view
            v-for="t in tagOpts"
            :key="t"
            class="chip"
            :class="{ on: tags.includes(t) }"
            @tap="toggleTag(t)"
          >{{ t }}</view>
        </view>
      </view>

      <!-- 所需食材：食材大类(单行横滑点选) → 已选 tags → 当前大类食材清单点选 → 自定义收录
       交互：大类放置最上、一行横滑不全排开；大类下清单式勾选；未命中可收录 -->
      <view class="add-card">
        <text class="flabel">所需食材 <text class="t-12">已选 {{ selNames.length }} 项</text></text>

        <!-- 食材大类：单行横滑点选 + 左右步进箭头 + 底部滑动轨道滑块 -->
        <view class="cat-wrap">
          <text class="cat-arrow" :class="{ off: catScroll <= 0 }" @tap="catStep(-1)">‹</text>
          <scroll-view class="cat-scroll" scroll-x :scroll-left="catScroll" @scroll="onCatScroll" :show-scrollbar="false">
            <view class="cat-row">
              <view v-for="c in cats" :key="c" class="ctab" :class="{ on: c === activeCat }" @tap="onCat(c)">{{ c }}</view>
            </view>
          </scroll-view>
          <text class="cat-arrow" :class="{ off: catScroll >= catMax }" @tap="catStep(1)">›</text>
        </view>
        <!-- 底部滑轨：thumb 位置/长度反映当前滚动进度 -->
        <view class="cat-track">
          <view class="cat-thumb" :style="{ width: catThumbW + '%', left: catThumbL + '%' }"></view>
        </view>

        <!-- 已选 tags（× 移除） -->
        <view class="sel-tags" v-if="selNames.length">
          <view class="chk-sel" v-for="n in selNames" :key="n">{{ n }}<text class="x" @tap.stop="toggleIng(n)"> ×</text></view>
        </view>

        <!-- 当前大类食材清单（点选切换，选中同步到上方已选） -->
        <view class="ing-list">
          <view class="ing-row" v-for="n in poolFor(activeCat)" :key="n" @tap="toggleIng(n)">
            <text class="nm">{{ n }}</text>
            <text class="sp"></text>
            <text class="box" :class="{ on: selNames.includes(n) }">{{ selNames.includes(n) ? '✓' : '' }}</text>
          </view>
          <view class="empty" v-if="!poolFor(activeCat).length">
            <text>「{{ activeCat }}」还没有食材</text>
            <text class="empty-act">可先在图下方输入，点「＋ 收录」进食材库</text>
          </view>
        </view>

        <!-- 收录新食材进食材库（独立维护，不依赖冰箱库存） -->
        <view class="quick-add">
          <input class="quick-input" v-model="newIng" placeholder="没找到？输入并收录进食材库" />
          <text class="quick-btn" @tap="addIngredient">＋ 收录</text>
        </view>
      </view>

      <!-- 步骤教程：每行一步 -->
      <view class="add-card">
        <text class="flabel">步骤教程</text>
        <textarea
          class="finput steps"
          v-model="stepText"
          placeholder="每行一步，如：&#10;第一步 起火倒油&#10;第二步 下菜翻炒"
        ></textarea>
      </view>

      <view class="pbtn save-btn" @tap="save">保存到菜谱库</view>
      <view style="height:60rpx"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { recipeApi, ingredientApi, catApi, coverApi } from '@/api'

const timeOpts = ['10 分钟内', '15-30 分', '30-60 分', '60+ 分']
const diffOpts = ['简单', '中等', '较难']
const tagOpts = ['下饭', '快手', '素', '🌶 辣', '宴客']
const DEFAULT_GRAD = 'linear-gradient(135deg,#4b3fe3,#8b5cf6)'

export default {
  data() {
    return {
      id: null,
      timeOpts, diffOpts, tagOpts,
      form: { name: '', diff: '简单', time: 10 },
      tags: [],
      pool: [],           // 我的食材 [{name, cat}]
      cats: [],           // 大类列表（来自食材库维护，含空大类），顺序可变
      catIdx: 0,          // 当前选中的大类下标
      selNames: [],       // 已勾选食材名
      selMap: {},         // name -> 原菜谱已有的 qty/unit（编辑回填）
      stepText: '',
      newIng: '',          // 快捷收录新食材的输入
      covers: [],          // 封面图库（管理员维护），选择后写 recipes.cover
      coverId: '',         // 当前选中的封面 id（''=默认轮换）
      DEFAULT_GRAD,
      catScroll: 0,        // 大类横滑当前偏移(px)
      catViewW: 0,         // 大类容器可视宽度(px)
      catContentW: 0       // 大类内容总宽(px)，用于算滑轨进度
    }
  },
  computed: {
    activeCat() {          // 当前激活大类名
      return this.cats[this.catIdx] || ''
    },
    catMax() {             // 大类可横向滚动的最大偏移
      return Math.max(0, this.catContentW - this.catViewW)
    },
    catThumbW() {          // 滑轨 thumb 宽度(%)：可视/内容比例，至少 8% 便于辨识
      return this.catContentW > 0 ? Math.max(8, (this.catViewW / this.catContentW) * 100) : 100
    },
    catThumbL() {          // 滑轨 thumb 左偏移(%)：随滚动进度滑动
      const m = this.catMax
      return m > 0 ? (this.catScroll / m) * (100 - this.catThumbW) : 0
    }
  },
  async onLoad(q) {
    if (q.id) { this.id = Number(q.id); await this.load() }
    await this.loadPool()
  },
  methods: {
    async loadPool() {
      try {
        // 封面图库：管理员维护的可点选封面（emoji + 渐变）
        this.covers = (await coverApi.list()) || []
        // 大类：来自「食材库」维护的分类（含空大类，按用户编排的顺序）
        const cats = await catApi.list()
        this.cats = cats.map((c) => c.name).filter(Boolean)
        // 食材：全部食材库条目
        const list = await ingredientApi.list()
        const items = list.map((x) => ({ name: (x.name || '').trim(), cat: x.cat || '其他' })).filter((x) => x.name)
        this.pool = items
        this.catIdx = 0
      } catch (e) { this.pool = []; this.cats = [] }
    },
    // 收录新食材进食材库（一般挂当前大类下；同名由后端去重 409）
    async addIngredient() {
      const name = (this.newIng || '').trim()
      if (!name) return uni.showToast({ title: '请输入食材名', icon: 'none' })
      try {
        await ingredientApi.create({ name, cat: this.activeCat || '其他' })
        this.newIng = ''
        await this.loadPool()
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
  onReady() {             // 渲染完成后量取大类容器尺寸，供滑轨进度计算
    this.$nextTick(() => this.measureCat())
  },
  // 切换大类 chips → 选中当前大类
  onCat(c) {
    this.catIdx = this.cats.indexOf(c)
  },
  // 大类滑动的实时偏移（驱动滑轨 thumb 与箭头禁用态）
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
    // 某个大类下的食材名清单
    poolFor(cat) {
      return this.pool.filter((p) => p.cat === cat).map((p) => p.name)
    },
    // 点选/取消食材；仅记录名称，qty/unit 沿用原值或默认
    toggleIng(p) {
      const i = this.selNames.indexOf(p)
      if (i >= 0) this.selNames.splice(i, 1)
      else { this.selNames.push(p); this.selMap[p] = this.selMap[p] || { qty: 1, unit: '份' } }
      this.selNames = [...this.selNames]
    },
    // 点选封面：''=默认轮换；c 为图库封面对象时取它的 id
    pickCover(c) {
      this.coverId = (c === '' || c === null || c === undefined) ? '' : c.id
    },
    async load() {
      const r = await recipeApi.get(this.id)
      this.form = { name: r.name, diff: r.diff, time: r.time || 10 }
      this.coverId = r.cover || ''    // 回填已选封面（''=默认轮换）
      this.tags = r.tags || []
      // 步骤文本：每行一步（兼容 steps 为单对象/空的旧数据）
      const rawSteps = r.steps
      const steps = Array.isArray(rawSteps) ? rawSteps : (rawSteps ? [rawSteps] : [])
      this.stepText = steps.map((s) => (typeof s === 'string' ? s : '')).filter(Boolean).join('\n')
      // 食材：回填已勾选 names，并记录原 qty/unit 便于保存
      // 兼容旧数据：ing 可能是单对象或空，统一归一化为数组
      const rawIng = r.ing
      const ing = Array.isArray(rawIng) ? rawIng : (rawIng ? [rawIng] : [])
      const sel = []
      ing.forEach((it) => {
        if (!it || !it.name) return
        sel.push(it.name)
        this.selMap[it.name] = { qty: it.qty, unit: it.unit }
      })
      this.selNames = [...new Set(sel)]
    },
    timeTick(t) {
      if (t === '10 分钟内') return this.form.time > 0 && this.form.time <= 10
      if (t === '15-30 分') return this.form.time > 10 && this.form.time <= 30
      if (t === '30-60 分') return this.form.time > 30 && this.form.time <= 60
      return this.form.time > 60
    },
    setTime(t) {
      if (t === '10 分钟内') this.form.time = 8
      else if (t === '15-30 分') this.form.time = 20
      else if (t === '30-60 分') this.form.time = 45
      else this.form.time = 75
    },
    toggleTag(t) {
      const i = this.tags.indexOf(t)
      if (i >= 0) this.tags.splice(i, 1)
      else this.tags.push(t)
    },
    async save() {
      if (!this.form.name.trim()) return uni.showToast({ title: '请输入菜名', icon: 'none' })
      // 封面：选了图库封面则 em 用它的 emoji、cover 存 id；未选则 em 默认、cover 空（走默认轮换）
      const picked = this.covers.find((c) => String(c.id) === String(this.coverId))
      const data = {
        name: this.form.name.trim(),
        em: picked ? picked.emoji : '🍽',
        cover: picked ? String(picked.id) : '',
        time: this.form.time || 10,
        diff: this.form.diff,
        tags: this.tags,
        ing: this.selNames.map((n) => ({ name: n, qty: (this.selMap[n] && this.selMap[n].qty) || 1, unit: (this.selMap[n] && this.selMap[n].unit) || '份' })),
        steps: this.stepText.split('\n').map((x) => x.trim()).filter(Boolean)
      }
      try {
        if (this.id) await recipeApi.update(this.id, data)
        else await recipeApi.create(data)
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
.save { color:var(--brand); font-size:28rpx; }
.nscroll { flex:1; }
/* 水平留白放内层 wrapper，box-sizing:border-box 保证 width:100% 含 padding，避免 scroll-view 内容溢出导致右侧被裁 */
.scroll-inner { box-sizing:border-box; width:100%; padding:0 24rpx; }
.add-card { background:var(--card); border:1rpx solid var(--border); border-radius:16rpx; padding:20rpx; margin-bottom:16rpx; }
/* 菜名一行：label 靠左、输入框占余宽 */
.name-row { display:flex; align-items:center; }
.name-row .flabel { margin:0; flex:none; width:110rpx; }
.name-row .finput { flex:1; }
/* 封面图库选择：横滑点选 emoji+渐变卡（对齐食材大类横滑交互） */
.cover-scroll { margin-top:6rpx; }
.cover-row { display:flex; gap:16rpx; padding:6rpx 2rpx 10rpx; }
.cover-item { flex-shrink:0; display:flex; flex-direction:column; align-items:center; gap:8rpx; }
.cover-box { width:92rpx; height:92rpx; border-radius:20rpx; display:flex; align-items:center; justify-content:center; border:4rpx solid transparent; box-sizing:border-box; }
.cover-item.on .cover-box { border-color:var(--brand); }
.cover-em { font-size:48rpx; }
.cover-name { font-size:22rpx; color:var(--text-2); }
.flabel { font-size:26rpx; color:var(--text-2); margin-bottom:12rpx; display:flex; }
.flabel.sub-lbl { margin:18rpx 0 10rpx; }
.t-12 { font-size:22rpx; color:var(--text-2); margin-left:8rpx; }
.finput { width:100%; box-sizing:border-box; height:84rpx; padding:0 16rpx; border:1rpx solid var(--border); border-radius:14rpx; font-size:28rpx; line-height:84rpx; background:var(--card); color:var(--text); min-height:84rpx; }
.finput.steps { height:auto; line-height:1.5; padding:14rpx 16rpx; }
.segs { display:flex; gap:10rpx; }
.seg { flex:1; text-align:center; padding:14rpx 4rpx; border:1rpx solid var(--border); border-radius:14rpx; font-size:26rpx; background:var(--card); white-space:nowrap; overflow:hidden; }
.seg.on { background:var(--brand); color:#fff; border-color:var(--brand); }
.seg-tags { display:flex; gap:12rpx; flex-wrap:wrap; }
.chip { font-size:24rpx; color:var(--text-2); background:var(--card); border:1rpx solid var(--border); border-radius:999rpx; padding:12rpx 22rpx; white-space:nowrap; }
.chip.on { background:var(--brand); color:#fff; border-color:var(--brand); }
.sel-tags { display:flex; gap:10rpx; flex-wrap:wrap; margin-bottom:4rpx; }
.chk-sel { font-size:24rpx; color:var(--brand); background:#dcf2ee; border-radius:999rpx; padding:8rpx 18rpx; white-space:nowrap; }
.chk-sel .x { opacity:.6; }
/* 大类滑动筛选：箭头 + 横滑 + 底部滑轨（对齐设计稿「按口味筛」三层交互） */
.cat-wrap { display:flex; align-items:center; gap:8rpx; margin:10rpx 0 2rpx; }
.cat-arrow { flex-shrink:0; width:44rpx; height:44rpx; border-radius:50%; background:var(--bg); color:var(--text-2); display:flex; align-items:center; justify-content:center; font-size:34rpx; line-height:1; }
.cat-arrow.off { opacity:.32; }
.cat-scroll { flex:1; min-width:0; }
.cat-row { display:flex; gap:12rpx; padding:4rpx; box-sizing:border-box; }
.ctab { font-size:26rpx; color:var(--text-2); background:var(--card); border:1rpx solid var(--border); border-radius:999rpx; padding:10rpx 24rpx; white-space:nowrap; flex-shrink:0; }
.ctab.on { background:var(--brand); color:#fff; border-color:var(--brand); font-weight:600; }
.cat-track { position:relative; height:6rpx; background:#E5E3EE; border-radius:3rpx; margin:4rpx 0 6rpx; overflow:hidden; }
.cat-thumb { position:absolute; top:0; bottom:0; background:#bfbce8; border-radius:3rpx; transition:left .15s ease, width .15s ease; }
/* 当前大类食材清单（点选行） */
.ing-list { border:1rpx solid var(--border); border-radius:14rpx; overflow:hidden; margin:2rpx 0; }
.ing-row { display:flex; align-items:center; gap:12rpx; padding:18rpx 20rpx; border-bottom:1rpx solid var(--border); background:var(--card); }
.ing-row:last-child { border-bottom:none; }
.ing-row .nm { font-size:28rpx; }
.ing-row .box { width:40rpx; height:40rpx; border-radius:50%; border:2rpx solid var(--border); display:flex; align-items:center; justify-content:center; font-size:26rpx; color:#fff; background:var(--card); flex-shrink:0; box-sizing:border-box; }
.ing-row .box.on { background:var(--brand); border-color:var(--brand); }
.empty { display:flex; flex-direction:column; align-items:center; gap:8rpx; padding:48rpx 20rpx; color:var(--text-2); font-size:24rpx; }
.empty .empty-act { color:var(--text-2); opacity:.7; }
.quick-add { display:flex; gap:12rpx; margin-top:12rpx; align-items:center; }
.quick-input { flex:1; min-width:0; height:64rpx; line-height:64rpx; padding:0 16rpx; border:1rpx dashed var(--border); border-radius:14rpx; font-size:26rpx; background:var(--bg); box-sizing:border-box; color:var(--text); }
.quick-btn { flex-shrink:0; font-size:24rpx; color:var(--brand); padding:12rpx 20rpx; border-radius:999rpx; box-shadow:inset 0 0 0 2rpx var(--brand); }
.save-btn { width:100%; box-sizing:border-box; margin-top:8rpx; }
</style>