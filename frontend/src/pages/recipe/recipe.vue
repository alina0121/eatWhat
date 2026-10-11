<!-- recipe.vue —— 「菜谱」页
  对齐「第一版 UI」：
  - 「吃这些」候选收件箱已迁至底部「候选」tab（pages/cands/cands）
  - 「按口味筛」横滑 chips
  - 菜谱列表 tab 切换：我的菜谱 / 优选餐厅 / 参考菜谱（渐变封面 +「+候选」+「＋ 新建」）
-->
<template>
  <view class="tab-page">
    <view class="page-header">
      <text class="page-title">选菜</text>
    </view>

    <scroll-view class="tab-scroll" scroll-y>
      <!-- ============ 按口味筛（独立节标题 + 横滑单行，菜谱/餐厅通用） ============ -->
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

      <!-- ============ 全部：tab 切换（我的菜谱 / 优选餐厅 / 参考菜谱） ============ -->
      <view class="section">
        <view class="rec-tabs">
          <view class="rec-tab" :class="{ on: tab === 'my' }" @tap="tab = 'my'">我的菜谱<text class="rec-tab-cnt">({{ myCount }})</text></view>
          <view class="rec-tab" :class="{ on: tab === 'shop' }" @tap="tab = 'shop'">优选餐厅<text class="rec-tab-cnt">({{ shopCount }})</text></view>
          <view class="rec-tab" :class="{ on: tab === 'ref' }" @tap="tab = 'ref'">参考菜谱<text class="rec-tab-cnt">({{ refCount }})</text></view>
          <view class="flex-sp"></view>
          <text class="newlink" v-if="tab === 'my'" @tap="newRecipe">＋ 新建</text>
          <text class="newlink" v-else-if="tab === 'shop'" @tap="openForm()">＋ 新增餐厅</text>
        </view>

        <!-- 优选餐厅 -->
        <template v-if="tab === 'shop'">
          <view class="rec-list">
            <view class="rec-card" v-for="s in shownShops" :key="s.id">
              <view class="rec-cover" @tap="openShop(s)">
                <text class="rec-em">{{ s.icon || '🏪' }}</text>
              </view>
              <view class="rec-info" @tap="openShop(s)">
                <view class="rec-name">
                  <text>{{ s.name }}</text>
                  <text class="badge b-shop">餐厅</text>
                </view>
                <view class="rec-meta">{{ s.type }}<text v-if="s.price"> · {{ s.price }}</text><text class="rec-star" v-if="s.star">{{ starStr(s) }}</text></view>
                <view class="rec-tags">
                  <text class="t-pill" v-for="(m, i) in shopPills(s)" :key="'p' + i">{{ m }}</text>
                </view>
              </view>
              <text class="edit-link" @tap.stop="openForm(s)">✎</text>
              <text
                class="pbtn small"
                :class="{ added: inShopCands(s) }"
                @tap="toggleShopCand(s)"
              >{{ inShopCands(s) ? '✓ 已选' : '+ 候选' }}</text>
            </view>
          </view>
          <view class="section-empty" v-if="!shownShops.length">
            <text class="empty-tip">{{ shops.length ? '没有匹配当前口味的餐厅，换个标签试试' : '还没有收藏餐厅，点右上角「＋ 新增餐厅」开始吧' }}</text>
          </view>
        </template>

        <!-- 我的菜谱 / 参考菜谱 -->
        <template v-else>
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
                <view class="rec-meta">{{ r.time }}分钟 · {{ r.diff }}<text class="rec-star" v-if="r.star">{{ starStr(r) }}</text></view>
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
            <text class="empty-tip">{{ tab === 'ref' ? '暂无参考菜谱' : '还没有自己的菜谱，点右上角「＋ 新建」开始吧' }}</text>
          </view>
        </template>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <!-- 新增 / 编辑餐厅共用表单（原独立餐厅页已并入本 tab） -->
    <view class="mask" v-if="formShow" @tap="formShow = false"></view>
    <view class="form" v-if="formShow">
      <view class="form-head">
        <text class="form-title">{{ form.id ? '编辑餐厅' : '新增餐厅' }}</text>
        <text class="close" @tap="formShow = false">✕</text>
      </view>
      <!-- emoji 候选 + 实时预览 -->
      <view class="f-row">
        <text class="f-l">图标</text>
        <view class="form-emoji-row">
          <text class="form-emoji-preview">{{ form.icon || '🏪' }}</text>
          <view class="form-emoji-grid">
            <view v-for="e in shopIcons" :key="e" class="form-emoji-cell" :class="{ on: form.icon === e }" @tap="form.icon = e">{{ e }}</view>
          </view>
        </view>
      </view>
      <view class="f-row"><text class="f-l">名称</text><input class="f-i" v-model="form.name" placeholder="餐厅名" /></view>
      <view class="f-row"><text class="f-l">类型</text><input class="f-i" v-model="form.type" placeholder="中餐/西餐…" /></view>
      <view class="f-row"><text class="f-l">人均</text><input class="f-i" v-model="form.price" placeholder="¥" /></view>
      <view class="f-row"><text class="f-l">到达耗时(分)</text><input class="f-i" type="number" v-model.number="form.arr_min" /></view>
      <view class="f-row"><text class="f-l">交通工具</text><input class="f-i" v-model="form.transport" placeholder="步行/骑车/开车" /></view>
      <view class="f-row star-row">
        <text class="f-l">星级</text>
        <view class="stars">
          <text
            v-for="i in 5"
            :key="i"
            class="st"
            :class="{ on: i <= (form.star || 0) }"
            @tap="form.star = form.star === i ? 0 : i"
          >★</text>
        </view>
      </view>
      <view class="f-row"><text class="f-l">招牌菜</text><input class="f-i" v-model="form.mustText" placeholder="逗号分隔" /></view>
      <view class="f-row">
        <text class="f-l">口味标签</text>
        <view class="ftags">
          <text
            class="fchip"
            :class="{ on: (form.tags || []).includes(t) }"
            v-for="t in allTasteTags"
            :key="t"
            @tap="toggleFormTag(t)"
          >{{ t }}</text>
          <text class="fchip-tip" v-if="!allTasteTags.length">暂无标签，去「我的 → 口味标签」维护</text>
        </view>
      </view>
      <view class="f-row"><text class="f-l">备注</text><input class="f-i" v-model="form.note" placeholder="选填，餐厅详情页显示" /></view>
      <view class="form-foot">
        <text class="pbtn" @tap="saveShop">保存</text>
        <text class="pbtn ghost danger" v-if="form.id" @tap="delShop">删除</text>
      </view>
    </view>

    <custom-tab current="recipe" />
  </view>
</template>

<script>
import { recipeApi, candidateApi, tasteApi, shopApi, configApi } from '@/api'

const emptyShopForm = () => ({
  id: null, name: '', type: '中餐', price: '', arr_min: 0, transport: '步行', mustText: '', star: 0, icon: '🏪', note: '', tags: []
})

export default {
  data() {
    return {
      cands: [],        // 吃这些候选（用于 ✓已选 状态）
      recipes: [],      // 全部菜谱
      shops: [],        // 收藏餐厅（优选餐厅 tab）
      tab: 'my',       // 当前 tab：my=我的菜谱（默认） / shop=优选餐厅 / ref=参考菜谱
      selKey: '',       // 当前筛选：'' 全部 / tag 名
      filterList: [],   // 横滑筛选项 [{key,label}]
      allTasteTags: [], // 用户维护的口味标签全量（来自 tasteApi）
      formShow: false,  // 餐厅新增/编辑表单弹层
      form: emptyShopForm(),
      shopIcons: []     // 餐厅 emoji 候选池（configApi）
    }
  },
  computed: {
    // 按 tab 先筛 source，再按 selKey 筛 tag
    shownRecipes() {
      const source = this.tab === 'ref' ? 'admin' : 'my'
      const list = this.recipes.filter((r) => r.source === source)
      if (!this.selKey) return list
      return list.filter((r) => (r.tags || []).includes(this.selKey))
    },
    // 优选餐厅：按 selKey 筛口味标签
    shownShops() {
      if (!this.selKey) return this.shops
      return this.shops.filter((s) => (s.tags || []).includes(this.selKey))
    },
    refCount() { return this.recipes.filter((r) => r.source === 'admin').length },
    myCount() { return this.recipes.filter((r) => r.source === 'my').length },
    shopCount() { return this.shops.length }
  },
  watch: {
    // tab 切换：重置筛选关键字 + 重建 filterList（只聚合当前 tab 的 tag）
    tab() {
      this.selKey = ''
      this.buildFilterList()
    }
  },
  onLoad(q) {
    // 支持 ?tab=shop 直达优选餐厅（如「我的」页收藏餐厅入口）
    if (q && q.tab) this.tab = q.tab
  },
  onShow() {
    this.load()
  },
  methods: {
    async load() {
      try {
        const [cands, recipes, tags, shops, pool] = await Promise.all([candidateApi.list(), recipeApi.list(), tasteApi.list().catch(() => []), shopApi.list().catch(() => []), configApi.get('shop_icon_pool').catch(() => ({ value: '' }))])
        this.cands = cands
        this.recipes = recipes
        this.shops = shops || []
        // 餐厅 emoji 候选池（configApi.get 返回 {key,value}，取 .value）
        this.shopIcons = (pool.value || '🏪,🍜,🍲,🍣,🏮,🥟,🍢,🌮,🍕,🥘,🍱,🍛').split(/[,，]/).map((x) => x.trim()).filter(Boolean)
        // 缓存用户维护的口味标签名（用于筛选 chip + recipe-edit 的 tag 候选）
        this.allTasteTags = (tags || []).map((t) => t.name).filter(Boolean)
        this.buildFilterList()
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    // 组装横滑筛选项：「全部」+ 用户维护的口味标签 + 当前 tab 内容实际用到的 tag
    buildFilterList() {
      const list = [{ key: '', label: '全部' }]
      const keys = new Set([''])
      // 1. 用户维护的口味标签优先
      this.allTasteTags.forEach((t) => { if (!keys.has(t)) { keys.add(t); list.push({ key: t, label: t }) } })
      // 2. 当前 tab 内容实际用到的 tag 补齐
      const source = this.tab === 'ref' ? 'admin' : 'my'
      const items = this.tab === 'shop'
        ? this.shops
        : this.recipes.filter((r) => r.source === source)
      items.forEach((r) => (r.tags || []).forEach((t) => { if (!keys.has(t)) { keys.add(t); list.push({ key: t, label: t }) } }))
      this.filterList = list
    },
    inCands(r) {
      return this.cands.some((c) => c.kind === 'recipe' && c.ref_id === r.id)
    },
    // 封面背景：编辑里选了渐变就用渐变；选「空」就留空白，不再回退默认渐变
    coverStyle(r) {
      return { background: r.coverGrad || '' }
    },
    // 喜好星级文本：「 · ★★★☆☆」；未评（0 星）不显示
    starStr(r) {
      const n = r.star || 0
      return n > 0 ? ' · ' + '★'.repeat(n) + '☆'.repeat(5 - n) : ''
    },
    openDetailById(r) {
      uni.navigateTo({ url: `/pages/recipe-detail/recipe-detail?id=${r.id}` })
    },
    // 餐厅卡标签 pill：口味标签在前，招牌菜补位（合计最多 4 个）
    shopPills(s) {
      return [...(s.tags || []), ...(s.must || [])].slice(0, 4)
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
    newRecipe() {
      uni.navigateTo({ url: '/pages/recipe-edit/recipe-edit' })
    },
    // —— 优选餐厅：详情 / 新增编辑表单 ——
    openShop(s) {
      uni.navigateTo({ url: `/pages/shop-detail/shop-detail?id=${s.id}` })
    },
    openForm(s) {
      if (s) this.form = { ...emptyShopForm(), ...s, tags: s.tags || [], mustText: (s.must || []).join('、') }
      else this.form = emptyShopForm()
      this.formShow = true
    },
    // 表单内切换口味标签（多选）
    toggleFormTag(t) {
      const tags = this.form.tags || []
      this.form = { ...this.form, tags: tags.includes(t) ? tags.filter((x) => x !== t) : [...tags, t] }
    },
    async saveShop() {
      const data = {
        name: this.form.name, type: this.form.type, price: this.form.price,
        arr_min: this.form.arr_min, transport: this.form.transport, star: this.form.star,
        must: this.form.mustText ? this.form.mustText.split(/[，,、]/).map((x) => x.trim()).filter(Boolean) : [],
        note: this.form.note || '',
        icon: this.form.icon || '🏪',
        tags: this.form.tags || []
      }
      if (!data.name) return uni.showToast({ title: '请输入名称', icon: 'none' })
      try {
        if (this.form.id) await shopApi.update(this.form.id, data)
        else await shopApi.create(data)
        this.formShow = false
        await this.load()
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // 删除餐厅：二次确认，失败要提示
    delShop() {
      uni.showModal({
        title: '删除餐厅', content: `删除「${this.form.name}」？删除后不可恢复。`, confirmText: '删除', confirmColor: '#e64340',
        success: async (res) => {
          if (!res.confirm) return
          try {
            await shopApi.del(this.form.id)
            this.formShow = false
            await this.load()
          } catch (e) { uni.showToast({ title: e.message || '删除失败', icon: 'none' }) }
        },
      })
    },
    inShopCands(s) {
      return this.cands.some((c) => c.kind === 'shop' && c.ref_id === s.id)
    },
    // 餐厅候选只进「吃这些」，不参与采购计算
    async toggleShopCand(s) {
      if (this.inShopCands(s)) return uni.showToast({ title: '已在吃这些', icon: 'none' })
      try {
        await candidateApi.add('shop', s.id)
        await this.load()
        uni.showToast({ title: '已加入吃这些', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
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
.page-sub { font-size: 26rpx; color: var(--text-2); }

.section { padding: 12rpx 24rpx; }
.section-empty { padding: 40rpx 24rpx; text-align: center; }
.empty-tip { color: var(--text-2); font-size: 26rpx; }

.flex-sp { flex: 1; }

.badge { font-size: 20rpx; padding: 2rpx 12rpx; border-radius: 999rpx; }
.b-shop { background: #fff3e0; color: #f57c00; }

/* 节标题（对齐原型 sec-tit） */
.sec-tit {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 32rpx; font-weight: 700; margin: 6rpx 0 16rpx; padding-top: 8rpx;
}
/* tab 切换（参考 / 我的） */
.rec-tabs {
  display: flex; align-items: center; gap: 12rpx;
  margin: 6rpx 0 16rpx; padding-top: 8rpx;
}
.rec-tab {
  font-size: 32rpx; font-weight: 500; color: var(--text-2);
  padding: 12rpx 24rpx; border-radius: 999rpx;
  background: var(--bg, #f5f5f5);
  transition: all .15s;
}
.rec-tab.on {
  background: var(--brand); color: #fff; font-weight: 700;
}
.rec-tab-cnt { font-size: 24rpx; margin-left: 4rpx; opacity: .75; }
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
.rec-star { color: #f5a623; }
.rec-tags { display: flex; gap: 8rpx; margin-top: 8rpx; flex-wrap: wrap; }
.t-pill { font-size: 20rpx; color: var(--text-2); background: var(--bg); padding: 2rpx 10rpx; border-radius: 999rpx; }
.pbtn.small { font-size: 24rpx; padding: 10rpx 20rpx; flex-shrink: 0; }
.pbtn.added { background: #07c160; }

/* 默认封面渐变已内联于 coverStyle；旧 id%6 轮换样式移除 */

/* 徽章：我的=青，参考=紫（对齐 type-badge） */
.badge { font-size: 20rpx; padding: 2rpx 12rpx; border-radius: 999rpx; }
.b-my { background: #e6f6f3; color: #0f766e; }
.b-ref { background: var(--brand-soft, #efeaff); color: var(--brand); }

/* 餐厅卡：编辑入口 */
.edit-link { color: var(--brand); font-size: 28rpx; padding: 8rpx; flex-shrink: 0; }

/* 新增/编辑餐厅表单弹层（原餐厅页 form） */
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 50; }
.form { position: fixed; left: 0; right: 0; bottom: 0; background: var(--surface); border-radius: 24rpx 24rpx 0 0; padding: 24rpx; z-index: 60; padding-bottom: calc(env(safe-area-inset-bottom) + 24rpx); }
.form-head { display: flex; justify-content: space-between; align-items: center; }
.form-title { font-size: 34rpx; font-weight: 700; }
.close { color: var(--text-2); font-size: 30rpx; }
.f-row { display: flex; align-items: center; gap: 16rpx; margin-top: 20rpx; }
.f-l { width: 180rpx; color: var(--text-2); font-size: 26rpx; flex-shrink: 0; }
.f-i { flex: 1; background: var(--bg); border-radius: 12rpx; height: 76rpx; line-height: 76rpx; padding: 0 16rpx; font-size: 28rpx; box-sizing: border-box; color: var(--text); }
.star-row { align-items: center; }
.stars { display: flex; gap: 6rpx; flex: 1; }
.st { font-size: 48rpx; color: #e4e6ec; line-height: 76rpx; transition: transform .12s; }
.st.on { color: #f5a623; }
.st:active { transform: scale(1.15); }
.form-foot { display: flex; gap: 16rpx; margin-top: 24rpx; }
.pbtn.danger { background: var(--danger); }
/* emoji 候选网格：4列，末行半露暗示可下滑 */
.form-emoji-row { display: flex; align-items: center; gap: 16rpx; flex: 1; min-width: 0; }
.form-emoji-preview { font-size: 44rpx; width: 80rpx; text-align: center; flex-shrink: 0; }
.form-emoji-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6rpx; max-height: 90rpx; overflow-y: auto; align-content: start; flex: 1; }
.form-emoji-cell { height: 52rpx; text-align: center; font-size: 32rpx; line-height: 1; border: 1rpx solid var(--border); border-radius: 8rpx; background: var(--bg); display: flex; align-items: center; justify-content: center; }
.form-emoji-cell.on { background: var(--brand); border-color: var(--brand); }

/* 表单口味标签多选 chips */
.ftags { flex: 1; display: flex; flex-wrap: wrap; gap: 10rpx; }
.fchip { font-size: 24rpx; padding: 8rpx 18rpx; border-radius: 999rpx; background: var(--bg); border: 1rpx solid var(--border); color: var(--text-2); }
.fchip.on { background: var(--brand); border-color: var(--brand); color: #fff; }
.fchip-tip { font-size: 24rpx; color: var(--text-3, #b6b8c0); line-height: 76rpx; }

.tab-pad { height: 40rpx; }
</style>