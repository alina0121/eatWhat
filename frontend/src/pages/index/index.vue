<!-- index.vue —— 推荐页（对齐「第一版 UI」今日页）
  结构：问候 + 转盘「帮我选一个」(菜谱+餐厅混合池，抽中类型徽章/标题/副描述，
        结果操作：＋候选 与 🔄再抽一次 并排) + 「跟谁一起吃」干饭成员行(选人自动带口味)
        + 「快捷筛一下」口味 chips + 「为您推荐」[换一个]（1 餐厅 + 3 菜谱，按口味过滤）
-->
<template>
  <view class="tab-page">
    <view class="page-header">
      <text class="page-title">今天吃啥好呀 👋</text>
    </view>

    <scroll-view class="tab-scroll" scroll-y>
      <!-- ========== 转盘「帮我选一个」 ========== -->
      <view class="section">
        <view class="hero">
          <text class="hero-lab">选择困难？交给我</text>
          <!-- 再抽一次时先走一圈动画；抽中展示类型徽章+标题+副描述 -->
          <view class="wheel" :class="{ spinning: spinning }">
            <view class="wheel-inner">{{ result ? result.em : '🎲' }}</view>
          </view>
          <view class="result-mid" v-if="result">
            <text class="badge" :class="result.kind === 'shop' ? 'b-shop' : 'b-recipe'">
              {{ result.kind === 'shop' ? '餐厅' : '菜谱' }}
            </text>
            <text class="result-tit">帮你抽中了「{{ result.name }}」</text>
            <text class="result-sub">{{ result.sub }}</text>
          </view>
        </view>
        <view class="result-ops">
          <text class="pbtn" :class="{ off: pickInEat }" @tap="addResult">
            {{ pickInEat ? '✓ 已选' : '＋ 候选' }}
          </text>
          <text class="pbtn ghost" @tap="spin">🔄 再抽一次</text>
        </view>
      </view>

      <!-- ========== 跟谁一起吃（干饭成员，选上自动带口味） ========== -->
      <view class="section">
        <view class="sec-tit">跟谁一起吃？ <text class="sub-13">选上就带上他/她的口味</text></view>
        <view class="chiprow">
          <view class="chip" :class="{ on: inDiners.length === 0 }" @tap="clearDiners">🌤 不限 / 清空</view>
          <view
            class="chip"
            v-for="d in diners"
            :key="d.id"
            :class="{ on: inDiners.includes(d.id) }"
            @tap="toggleDiner(d)"
          >🧑 {{ d.name }}</view>
        </view>
      </view>

      <!-- ========== 快捷筛一下（口味 chips） ========== -->
      <view class="section">
        <view class="sec-tit">快捷筛一下</view>
        <view class="chiprow">
          <view
            class="chip"
            v-for="t in quickTags"
            :key="t"
            :class="{ on: selTags.includes(t) }"
            @tap="toggleTag(t)"
          >{{ t }}</view>
        </view>
      </view>

      <!-- ========== 为您推荐 ========== -->
      <view class="section">
        <view class="sec-tit">为您推荐
          <text class="link" @tap="shuffle()">换一个</text>
        </view>
        <view class="rec-shop" v-if="recShop" @tap="toShop(recShop)">
          <text class="em">{{ recShop.em }}</text>
          <view class="rec-info">
            <text class="rec-name2">{{ recShop.name }}</text>
            <text class="rec-sub">{{ recShop.type }} · ★{{ recShop.star || 0 }}</text>
          </view>
          <text class="pbtn small" :class="{ off: inEatCand('shop', recShop.id) }" @tap.stop="addShopCand(recShop)">
            {{ inEatCand('shop', recShop.id) ? '✓ 已选' : '＋ 候选' }}
          </text>
        </view>
        <view class="card rec" v-for="r in recRecipes" :key="r.id" @tap="toRecipe(r)">
          <view class="rec-cover" :style="cover()"><text class="rec-em">{{ r.em }}</text></view>
          <view class="rec-info">
            <text class="rec-name2">{{ r.name }}</text>
            <text class="rec-sub">{{ r.time }}分钟 · {{ r.diff }} · {{ tagsText(r) }}</text>
          </view>
          <text class="pbtn small" :class="{ off: inEatCand('recipe', r.id) }" @tap.stop="addRecipeCand(r)">
            {{ inEatCand('recipe', r.id) ? '✓ 已选' : '＋ 候选' }}
          </text>
        </view>
        <view v-if="!recRecipes.length" class="empty">
          <text class="sub-13">没有匹配口味的菜谱，换个口味或点「换一个」看看</text>
        </view>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <custom-tab current="index" />
  </view>
</template>

<script>
import { recipeApi, shopApi, dinerApi, candidateApi } from '@/api'

export default {
  data() {
    return {
      recipes: [],
      shops: [],
      diners: [],          // 干饭成员（含各自口味 tags）
      cands: [],           // 已在「吃这些」的候选（用于 ✓已选 状态）
      result: null,        // 转盘抽中的项 { kind, ref_id, name, em, sub }
      spinning: false,     // 转盘动画标记
      quickTags: ['麻辣', '家常', '清淡', '快手', '下饭', '宴客'],
      selTags: [],         // 当前生效的口味标记（手动点选 + 成员带入，取并集）
      inDiners: [],        // 已选干饭成员 id
      recShop: null,
      recRecipes: [],
      recOff: 0            // 「换一个」轮换偏移
    }
  },
  computed: {
    // 转盘结果是否已在吃这些里（按钮置灰为 ✓已选）
    pickInEat() {
      return !this.result || this.inEatCand(this.result.kind, this.result.ref_id)
    }
  },
  onShow() {
    this.load()
  },
  methods: {
    async load() {
      try {
        const [recipes, shops, diners, cands] = await Promise.all([
          recipeApi.list(), shopApi.list(), dinerApi.list(), candidateApi.list()
        ])
        this.recipes = recipes
        this.shops = shops
        this.diners = diners
        this.cands = cands
        this.recommend()
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // —— 干饭成员联动：选人时把他的口味标记取并集带入「快捷筛一下」——
    toggleDiner(d) {
      const i = this.inDiners.indexOf(d.id)
      if (i >= 0) this.inDiners.splice(i, 1)
      else this.inDiners.push(d.id)
      // 按已选成员的 tags 取并集，覆盖当前 selTags（与第一版一致，之后仍可手动点口味）
      const tags = []
      this.inDiners.forEach((id) => {
        const dd = this.diners.find((x) => x.id === id)
        ;(dd && dd.tags || []).forEach((t) => { if (!tags.includes(t)) tags.push(t) })
      })
      this.selTags = tags
      this.recommend()
    },
    // 「不限/清空」：清空成员与全部口味标记
    clearDiners() {
      this.inDiners = []
      this.selTags = []
      this.recommend()
    },
    // —— 快捷筛一下：手动点选口味标记（不影响已选成员）——
    toggleTag(t) {
      const i = this.selTags.indexOf(t)
      if (i >= 0) this.selTags.splice(i, 1)
      else this.selTags.push(t)
      this.recommend()
    },
    // —— 转盘：菜谱+餐厅混合池随机（带转盘动画）——
    spin() {
      const pool = [
        ...this.recipes.map((r) => ({ kind: 'recipe', ref_id: r.id, em: r.em, name: r.name, sub: `${r.time}分钟 · ${r.diff}` })),
        ...this.shops.map((s) => ({ kind: 'shop', ref_id: s.id, em: s.em, name: s.name, sub: `${s.type || '餐厅'}${s.star ? ' · ★' + s.star : ''}` }))
      ]
      if (!pool.length) return uni.showToast({ title: '还没有菜谱或餐厅', icon: 'none' })
      // 触发动效，短暂延迟后落地结果
      this.spinning = true
      setTimeout(() => {
        this.spinning = false
        this.result = pool[Math.floor(Math.random() * pool.length)]
      }, 420)
    },
    async addResult() {
      if (!this.result) return
      if (this.pickInEat) return
      try {
        await candidateApi.add(this.result.kind, this.result.ref_id)
        this.cands = await candidateApi.list().catch(() => this.cands)
        uni.showToast({ title: '已加入「吃这些」', icon: 'success' })
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // —— 为您推荐：按当前口味标记过滤，1 餐厅 + 3 菜谱，可「换一个」轮换——
    recommend() {
      const match = (tags) => !this.selTags.length || (tags || []).some((t) => this.selTags.includes(t))
      const rs = this.shops.filter((s) => match(s.tags))
      const rr = this.recipes.filter((r) => match(r.tags))
      this.recShop = rs.length ? rs[this.recOff % rs.length] : null
      // 菜谱做滑动窗口轮换（与第一版 slice 逻辑一致）
      const recs = rr.length ? rr.concat(rr).slice(this.recOff % rr.length, (this.recOff % rr.length) + 3) : []
      this.recRecipes = recs
    },
    // 「换一个」：轮换偏移 +1
    shuffle() { this.recOff++; this.recommend() },
    tagsText(r) { return (r.tags || []).join('、') || '家常' },
    inEatCand(kind, refId) {
      return this.cands.some((c) => c.kind === kind && c.ref_id === refId)
    },
    cover() { return { background: 'linear-gradient(135deg,#4b3fe3,#8b5cf6,#ec4899)' } },
    addRecipeCand(r) {
      candidateApi.add('recipe', r.id).then(async () => { this.cands = await candidateApi.list().catch(() => this.cands); uni.showToast({ title: '已加入吃这些', icon: 'success' }) }).catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
    },
    addShopCand(s) {
      candidateApi.add('shop', s.id).then(async () => { this.cands = await candidateApi.list().catch(() => this.cands); uni.showToast({ title: '已加入吃这些', icon: 'success' }) }).catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
    },
    toRecipe(r) { uni.navigateTo({ url: `/pages/recipe-detail/recipe-detail?id=${r.id}` }) },
    toShop(s) { uni.navigateTo({ url: `/pages/shop-detail/shop-detail?id=${s.id}` }) }
  }
}
</script>

<style lang="scss" scoped>
.page-header { padding:20rpx 24rpx; padding-top:calc(env(safe-area-inset-top) + 20rpx); }
.page-title { font-size:44rpx; font-weight:700; }
.section { padding: 12rpx 24rpx; }

/* —— 转盘 —— */
.hero { display:flex; flex-direction:column; align-items:center; padding:24rpx 0 8rpx; }
.hero-lab { font-size:26rpx; color:var(--text-2); }
.wheel {
  width:230rpx; height:230rpx; margin:18rpx 0 4rpx; border-radius:50%;
  background:conic-gradient(from 0deg, #6f6fff, #a9aeff, #6f6fff, #a9aeff, #6f6fff);
  display:flex; align-items:center; justify-content:center;
  box-shadow: 0 0 0 10rpx rgba(75,63,227,.10);
}
.wheel.spinning { animation: wheelspin .42s ease-in-out; }
@keyframes wheelspin { from { transform: rotate(0)} to { transform: rotate(360deg)} }
.wheel-inner {
  width:176rpx; height:176rpx; border-radius:50%; background:var(--card);
  display:flex; align-items:center; justify-content:center;
  box-shadow:inset 0 0 0 8rpx #efeaff; font-size:76rpx;
}
.result-mid { display:flex; flex-direction:column; align-items:center; margin-top:6rpx; }
.badge { font-size:22rpx; padding:3rpx 18rpx; border-radius:999rpx; }
.b-recipe { background:#efeaff; color:var(--brand); }
.b-shop { background:#fff3e0; color:#f57c00; }
.result-tit { font-size:36rpx; font-weight:700; margin-top:8rpx; }
.result-sub { font-size:24rpx; color:var(--text-2); margin-top:4rpx; }
.result-ops { display:flex; gap:18rpx; justify-content:center; margin:16rpx 0 4rpx; }
.pbtn.off { background:#e6e6eb; color:#fff; }

/* —— 口味 / 成员 —— */
.sec-tit { font-size:32rpx; font-weight:700; margin:20rpx 0 16rpx; }
.link { color:var(--brand); font-size:26rpx; margin-left:8rpx; font-weight:400; }
.sub-13 { font-size:22rpx; color:var(--text-2); font-weight:400; }
.chiprow { display:flex; flex-wrap:wrap; gap:12rpx; }

/* —— 为您推荐 —— */
.rec-shop { display:flex; align-items:center; gap:14rpx; background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); padding:20rpx; margin-bottom:16rpx; }
.rec { display:flex; align-items:center; gap:14rpx; margin-bottom:16rpx; }
.rec-cover { width:96rpx; height:96rpx; border-radius:12rpx; display:flex; align-items:center; justify-content:center; }
.rec-em { font-size:52rpx; }
.em { font-size:52rpx; }
.rec-info { flex:1; min-width:0; }
.rec-name2 { font-size:30rpx; font-weight:600; display:block; }
.rec-sub { font-size:22rpx; color:var(--text-2); }
.pbtn.small { font-size:24rpx; padding:10rpx 18rpx; }
.empty { text-align:center; padding:24rpx 0; }
.tab-pad { height:40rpx; }
</style>