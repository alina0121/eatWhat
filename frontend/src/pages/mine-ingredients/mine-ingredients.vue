<!-- mine-ingredients.vue —— 食材库管理（菜谱选食材的独立来源）+ 食材大类维护
  两个 Tab：
    「食材」按大类分组，可新增/改名/改大类/删除；
    「大类」维护分类实体（增/删/改名/换图标/上下排序），改动全站动态生效。
  弹窗自绘遮罩（H5 不支持 uni.showModal editable）。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="uni.navigateBack()">‹</text>
      <view class="segs">
        <view class="seg" :class="{ on: tab === 'ing' }" @tap="tab = 'ing'">食材</view>
        <view class="seg" :class="{ on: tab === 'cat' }" @tap="tab = 'cat'">大类</view>
      </view>
      <text class="add" @tap="openAdd()">＋ {{ tab === 'cat' ? '大类' : '新增' }}</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="inner">
        <!-- 食材 Tab：按大类分组 -->
        <template v-if="tab === 'ing'">
          <text class="tip" v-if="!groups.length">食材库还没内容，点「＋ 新增」添加，或直接在编菜谱时用「＋ 收录」。</text>
          <view class="grp" v-for="g in groups" :key="g.cat">
            <text class="grp-t">{{ g.cat }}</text>
            <view class="card grow" v-for="it in g.items" :key="it.id">
              <text class="iname">{{ it.name }}</text>
              <text class="sp"></text>
              <text class="op" @tap="openEditIng(it)">✎ 改</text>
              <text class="op danger" @tap="delIng(it)">✕</text>
            </view>
          </view>
        </template>

        <!-- 大类 Tab：维护分类实体 -->
        <template v-else>
          <text class="tip" v-if="!cats.length">还没有大类，点「＋ 大类」添加一个。</text>
          <view class="card cgrow" v-for="c in cats" :key="c.id">
            <text class="cic">{{ c.icon }}</text>
            <text class="iname">{{ c.name }}</text>
            <text class="sp"></text>
            <text class="op" @tap="moveCat(c, 'up')">↑</text>
            <text class="op" @tap="moveCat(c, 'down')">↓</text>
            <text class="op" @tap="openEditCat(c)">✎</text>
            <text class="op danger" @tap="delCat(c)">✕</text>
          </view>
        </template>
      </view>
    </scroll-view>

    <!-- 弹窗：mode=ing 编辑食材；mode=cat 新增/编辑大类 -->
    <view class="mask" v-if="form.show" @tap="form.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">{{ form.mode === 'cat' ? (form.id ? '改大类' : '新增大类') : (form.id ? '改食材' : '新增食材') }}</text>

        <!-- 大类模式：名称 + 图标点选 -->
        <template v-if="form.mode === 'cat'">
          <input v-model="form.name" placeholder="大类名，如：豆制品" class="dfi" :focus="form.show" />
          <text class="d-sub">图标点选</text>
          <view class="icon-grid">
            <view v-for="ic in icons" :key="ic" class="icell" :class="{ on: form.icon === ic }" @tap="form.icon = ic">{{ ic }}</view>
          </view>
        </template>

        <!-- 食材模式：名称 + 归类到大类 -->
        <template v-else>
          <input v-model="form.name" placeholder="食材名，如：老抽" class="dfi" :focus="form.show" />
          <text class="d-sub">归类到大类</text>
          <view class="cat-wrap">
            <view v-for="c in cats" :key="c.id" class="chip" :class="{ on: form.cat === c.name }" @tap="form.cat = c.name">{{ c.icon }} {{ c.name }}</view>
          </view>
        </template>

        <view class="d-btns">
          <button class="pbtn ghost" @tap="form.show = false">取消</button>
          <button class="pbtn" @tap="save">保存</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { ingredientApi, catApi } from '@/api'

// 大类图标候选（Emoji 池，供新增大类点选）
const icons = ['🥬', '🍎', '🥩', '🦐', '🍄', '🥚', '🍚', '🧂', '🥗', '🌰', '🫘', '🧀', '🍞', '🍜', '🥛', '🌶', '🥜', '🍇']

export default {
  data() {
    return {
      tab: 'ing', icons,
      cats: [],        // [{id,name,icon,sort}] 大类，动态加载
      list: [],        // [{id,name,cat}] 食材
      form: { show: false, mode: 'ing', id: null, name: '', cat: '其他', icon: '🥗' }
    }
  },
  computed: {
    // 食材按大类分组；顺序跟随大类编排，只显示有大类的（空大类不出现，避免噪音）
    groups() {
      const catsOrder = {}
      this.cats.forEach((c) => { catsOrder[c.name] = true })
      const byCat = {}
      this.list.forEach((it) => { (byCat[it.cat] = byCat[it.cat] || []).push(it) })
      const keyed = Object.keys(byCat).sort((a, b) => {
        const oa = a in catsOrder, ob = b in catsOrder
        if (oa && ob) return this.cats.findIndex((c) => c.name === a) - this.cats.findIndex((c) => c.name === b)
        if (oa) return -1
        if (ob) return 1
        return a.localeCompare(b, 'zh')
      })
      return keyed.map((cat) => ({ cat, items: byCat[cat] }))
    }
  },
  onShow() { this.load() },
  methods: {
    async load() {
      try {
        const [cats, list] = await Promise.all([catApi.list(), ingredientApi.list()])
        this.cats = cats.map((c) => ({ id: c.id, name: c.name, icon: c.icon || '🥗', sort: c.sort }))
        this.list = list.map((x) => ({ id: x.id, name: x.name, cat: x.cat || '其他' }))
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    openAdd() {
      if (this.tab === 'cat') this.form = { show: true, mode: 'cat', id: null, name: '', cat: '其他', icon: '🥗' }
      else this.form = { show: true, mode: 'ing', id: null, name: '', cat: this.firstCat(), icon: '🥗' }
    },
    openEditIng(it) { this.form = { show: true, mode: 'ing', id: it.id, name: it.name, cat: it.cat, icon: '🥗' } },
    openEditCat(c) { this.form = { show: true, mode: 'cat', id: c.id, name: c.name, cat: '其他', icon: c.icon } },
    firstCat() { return (this.cats[0] && this.cats[0].name) || '其他' },
    async save() {
      const name = (this.form.name || '').trim()
      if (!name) return uni.showToast({ title: '名称不能为空', icon: 'none' })
      try {
        if (this.form.mode === 'cat') {
          if (this.form.id) await catApi.update(this.form.id, { name, icon: this.form.icon })
          else await catApi.create({ name, icon: this.form.icon })
        } else {
          if (this.form.id) await ingredientApi.update(this.form.id, { name, cat: this.form.cat })
          else await ingredientApi.create({ name, cat: this.form.cat })
        }
        this.form.show = false
        this.load()
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    async moveCat(c, dir) {
      await catApi.move(c.id, dir)
      this.load()
    },
    delIng(it) {
      uni.showModal({
        title: '移除食材',
        content: `从食材库移除「${it.name}」？（不影响已用它的菜谱/库存，只是不再可选）`,
        confirmText: '移除', confirmColor: '#e64340',
        success: async (res) => {
          if (!res.confirm) return
          try { await ingredientApi.del(it.id); this.load() } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
        }
      })
    },
    delCat(c) {
      uni.showModal({
        title: '删除大类',
        content: `删除「${c.name}」？该大类下的食材与冰箱项会自动退回「其他」。`,
        confirmText: '删除', confirmColor: '#e64340',
        success: async (res) => {
          if (!res.confirm) return
          try { await catApi.del(c.id); this.load() } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
        }
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; min-height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) 24rpx 16rpx; position:sticky; top:0; background:var(--surface); z-index:10; }
.back { font-size:44rpx; color:var(--text); font-weight:600; }
.segs { flex:1; display:flex; background:var(--bg); border-radius:999rpx; padding:6rpx; margin:0 auto; max-width:280rpx; }
.seg { flex:1; text-align:center; font-size:26rpx; color:var(--text-2); padding:10rpx 0; border-radius:999rpx; }
.seg.on { background:var(--card); color:var(--brand); font-weight:600; box-shadow:0 2rpx 8rpx rgba(0,0,0,0.06); }
.add { color:var(--brand); font-size:26rpx; }
.nscroll { flex:1; }
/* 水平留白放内层 wrapper（border-box），避免 scroll-view 内容右缘被裁 */
.inner { box-sizing:border-box; width:100%; padding:0 24rpx; }
.tip { display:block; color:var(--text-2); font-size:24rpx; padding:40rpx 0; text-align:center; }
.grp { margin-bottom:24rpx; }
.grp-t { display:block; font-size:24rpx; color:var(--text-2); margin:8rpx 4rpx 10rpx; }
.grow { display:flex; align-items:center; gap:12rpx; padding:20rpx 24rpx; margin-bottom:12rpx; }
.cgrow { display:flex; align-items:center; gap:14rpx; padding:18rpx 24rpx; margin-bottom:12rpx; }
.cic { font-size:34rpx; }
.iname { font-weight:600; font-size:28rpx; }
.sp { flex:1; }
.op { color:var(--brand); font-size:24rpx; padding:4rpx 8rpx; }
.op.danger { color:var(--danger); }

/* 弹窗 */
.mask { position:fixed; left:0; top:0; right:0; bottom:0; background:rgba(0,0,0,0.45); z-index:999; display:flex; align-items:center; justify-content:center; padding:48rpx; }
.dialog { width:100%; max-width:560rpx; background:var(--card); border-radius:20rpx; padding:32rpx; }
.d-title { font-size:32rpx; font-weight:700; display:block; margin-bottom:20rpx; }
.d-sub { font-size:24rpx; color:var(--text-2); display:block; margin:8rpx 0 12rpx; }
.dfi { background:var(--bg); border-radius:12rpx; height:84rpx; line-height:84rpx; padding:0 16rpx; margin-bottom:16rpx; font-size:28rpx; width:100%; box-sizing:border-box; color:var(--text); }
.d-btns { display:flex; gap:16rpx; justify-content:flex-end; margin-top:8rpx; }
.icon-grid { display:grid; grid-template-columns:repeat(6, 1fr); gap:12rpx; }
.icell { aspect-ratio:1; display:flex; align-items:center; justify-content:center; font-size:40rpx; background:var(--bg); border-radius:12rpx; border:2rpx solid transparent; }
.icell.on { border-color:var(--brand); background:#efeaff; }
.cat-wrap { display:flex; gap:12rpx; flex-wrap:wrap; }
.chip { font-size:24rpx; color:var(--text-2); background:var(--bg); border:1rpx solid var(--border); border-radius:999rpx; padding:10rpx 20rpx; }
.chip.on { background:var(--brand); color:#fff; border-color:var(--brand); }
</style>