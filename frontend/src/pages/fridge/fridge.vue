<!-- fridge.vue —— 冰箱页：在库 + 待采购
  在库状态（充足/临期/已过期）由后端实时现算；待采购可由候选代号入，本页支持手工增删。
-->
<template>
  <view class="tab-page">
    <view class="page-header">
      <text class="page-title">冰箱</text>
    </view>

    <scroll-view class="tab-scroll" scroll-y>
      <!-- 统计头：在库种数 / 待采购项数 -->
      <view class="section">
        <view class="stat-bar">
          <view class="stat-l">
            <text class="stat-num">{{ inStock.length }}</text>
            <text class="stat-t">种在库</text>
          </view>
          <view class="stat-mid">
            <text class="stat-t">能做出大约</text>
            <text class="stat-num">{{ canMake }}</text>
            <text class="stat-t">道菜 ✅</text>
          </view>
          <view class="stat-r">
            <text class="stat-num">{{ purchase.length }}</text>
            <text class="stat-t">待采购 🛒</text>
          </view>
        </view>
      </view>

      <!-- 临期提醒 -->
      <view class="section" v-if="nearItem">
        <view class="warn-box" @tap="editStock(nearItem)">
          <text class="warn-ic">⏰</text>
          <view class="warn-c">
            <text class="warn-t">「{{ nearItem.name }}」快到期</text>
            <text class="warn-s">还有 {{ nearItem.remain }} 天 · 试着用它做道快手菜</text>
          </view>
        </view>
      </view>

      <!-- 在库 -->
      <view class="section">
        <view class="sec-head">
          <text class="sec-title">在库</text>
          <text class="newlink" @tap="addStock">＋ 新增</text>
        </view>
        <view class="card row" v-for="s in inStock" :key="s.id">
          <view class="row-top">
            <text class="em">{{ emoji(s.name) }}</text>
            <text class="name">{{ s.name }}</text>
            <text class="sp"></text>
            <text class="op" @tap="editStock(s)">✎ 改</text>
            <text class="op danger" @tap="delStock(s)">✕</text>
          </view>
          <view class="row-bottom">
            <text class="att">{{ catText(s.cat, s.store) }}<text v-if="s.qty"> · {{ s.qty }}{{ s.unit }}</text><text v-if="s.buy"> · 购 {{ s.buy }}</text></text>
            <text class="sp"></text>
            <text class="pill" :class="statusCls(s.status)">{{ s.status }}</text>
            <text v-if="s.remain !== null" class="remain">剩{{ s.remain }}天</text>
          </view>
        </view>
      </view>

      <!-- 待采购 -->
      <view class="section">
        <view class="sec-head">
          <text class="sec-title">待采购</text>
          <text class="newlink" @tap="addPurchase">＋ 加购</text>
        </view>
        <view class="card row" v-for="p in purchase" :key="p.id">
          <view class="row-top">
            <text class="em">{{ emoji(p.name) }}</text>
            <text class="name">{{ p.name }}</text>
            <text class="sp"></text>
            <text class="op" @tap="editPurchase(p)">✎ 改</text>
            <text class="op danger" @tap="delPurchase(p)">✕</text>
          </view>
          <view class="row-bottom">
            <text class="att">待采购<text v-if="p.qty > 1"> ×{{ p.qty }}</text></text>
            <text class="sp"></text>
            <text class="pill buy" @tap="toStock(p)">🛒 已采购</text>
          </view>
        </view>
        <view class="section-empty" v-if="!purchase.length"><text class="empty-tip">待采购为空</text></view>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <custom-tab current="fridge" />
  </view>
</template>

<script>
import { fridgeApi, recipeApi } from '@/api'

export default {
  data() {
    return {
      inStock: [],
      purchase: [],
      recipes: []
    }
  },
  computed: {
    // 临期提醒：取第一项「临期」的在库食材
    nearItem() {
      return this.inStock.find((s) => s.status === '临期') || null
    },
    // 能做出的菜：菜谱所需食材全部在库可覆盖（仅统计有食材清单的菜谱）
    canMake() {
      const names = new Set(this.inStock.map((s) => s.name))
      return this.recipes.filter((r) => r.ing && r.ing.length && r.ing.every((i) => names.has(i))).length
    }
  },
  onShow() {
    this.load()
  },
  methods: {
    async load() {
      try {
        const [inStock, purchase, recipes] = await Promise.all([fridgeApi.inStock(), fridgeApi.purchase(), recipeApi.list()])
        this.inStock = inStock
        this.purchase = purchase
        this.recipes = recipes
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    // 在库属性行：大类 + 存放位置（均可不显示）
    catText(cat, store) {
      const c = cat || ''
      return store || c ? [c, store].filter(Boolean).join(' · ') : ''
    },
    emoji(name) {
      // 简单兜底：默认食材图标（后续可按食材库映射）
      const map = { 鸡蛋: '🥚', 牛排: '🥩', 番茄: '🍅', 青菜: '🥬', 米: '🍚', 牛奶: '🥛', 鸡: '🍗' }
      for (const k in map) if (name.includes(k)) return map[k]
      return '🥗'
    },
    statusCls(s) {
      return s === '临期' ? 'warn' : s === '已过期' ? 'danger' : 'ok'
    },
    addStock() {
      uni.navigateTo({ url: '/pages/fridge-edit/fridge-edit?type=stock' })
    },
    editStock(s) {
      uni.navigateTo({ url: `/pages/fridge-edit/fridge-edit?type=stock&id=${s.id}` })
    },
    async delStock(s) {
      await fridgeApi.delStock(s.id)
      this.load()
    },
    addPurchase() {
      uni.navigateTo({ url: '/pages/fridge-edit/fridge-edit?type=purchase' })
    },
    editPurchase(p) {
      uni.navigateTo({ url: `/pages/fridge-edit/fridge-edit?type=purchase&id=${p.id}` })
    },
    // 「已采购」：转入在库，前端待后端成功后刷新
    async toStock(p) {
      try {
        await fridgeApi.toStock(p.id)
        this.load()
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    async delPurchase(p) {
      await fridgeApi.delPurchase(p.id)
      this.load()
    }
  }
}
</script>

<style lang="scss" scoped>
.page-header { display:flex; align-items:baseline; gap:16rpx; padding:20rpx 24rpx; padding-top:calc(env(safe-area-inset-top) + 20rpx); }
.page-title { font-size:44rpx; font-weight:700; }
.section { padding: 12rpx 24rpx; }
.sec-head { display:flex; align-items:center; justify-content:space-between; margin: 6rpx 0 16rpx; }
.sec-title { font-size:32rpx; font-weight:700; }
.newlink { color: var(--brand); font-size:26rpx; }

/* 统计头 */
.stat-bar { display:flex; align-items:center; justify-content:space-between; background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); padding:24rpx 32rpx; }
.stat-l, .stat-mid, .stat-r { display:flex; flex-direction:column; align-items:center; gap:4rpx; }
.stat-num { font-size:44rpx; font-weight:700; color:var(--brand); }
.stat-t { font-size:22rpx; color:var(--text-2); }

/* 临期提醒 */
.warn-box { display:flex; align-items:center; gap:16rpx; background:#fff6e6; border:1rpx solid #ffd591; border-radius:var(--radius-lg,16rpx); padding:18rpx 20rpx; }
.warn-ic { font-size:36rpx; }
.warn-c { display:flex; flex-direction:column; gap:2rpx; }
.warn-t { font-size:28rpx; font-weight:600; color:var(--warning); }
.warn-s { font-size:22rpx; color:var(--text-2); }

.row { margin-bottom:16rpx; }
.row-top { display:flex; align-items:center; gap:14rpx; }
.em { font-size:40rpx; }
.name { font-weight:600; font-size:30rpx; }
.sp { flex:1; }
.op { color:var(--brand); font-size:24rpx; padding:4rpx 8rpx; }
.op.danger { color:var(--danger); }
.row-bottom { display:flex; align-items:center; gap:12rpx; margin-top:12rpx; font-size:24rpx; color:var(--text-2); }
.att { font-size:22rpx; }
.pill { font-size:20rpx; padding:2rpx 14rpx; border-radius:999rpx; }
.pill.ok { background:#e8f9ef; color:var(--success); }
.pill.warn { background:#fff6e6; color:var(--warning); }
.pill.danger { background:#ffecec; color:var(--danger); }
.pill.buy { background:#efeaff; color:var(--brand); }
.remain { color:var(--text-2); }
.section-empty { padding:24rpx; text-align:center; }
.empty-tip { color:var(--text-2); font-size:26rpx; }
.tab-pad { height:40rpx; }
</style>