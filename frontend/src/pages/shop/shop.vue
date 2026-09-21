<!-- shop.vue —— 餐厅页：收藏列表 + 新增/编辑共用表单（含到达耗时/交通工具） -->
<template>
  <view class="tab-page">
    <view class="page-header">
      <text class="page-title">我的餐厅</text>
      <text class="newlink" @tap="openForm()">＋ 收藏</text>
    </view>

    <scroll-view class="tab-scroll" scroll-y>
      <view class="section">
        <view class="card row" v-for="s in shops" :key="s.id" @tap="openDetail(s)">
          <view class="row-top">
            <text class="em">{{ s.em || '🏪' }}</text>
            <view class="name-wrap">
              <text class="name">{{ s.name }}</text>
            </view>
            <text class="sp"></text>
            <text class="star">⭐ {{ s.star || '新' }}</text>
          </view>
          <view class="row-bottom">
            <text class="sm">{{ s.type }}<text v-if="s.price"> · {{ s.price }}</text></text>
            <text class="sp"></text>
            <text class="edit-btn" @tap.stop="openForm(s)">✎ 编辑</text>
            <text
              class="pbtn small"
              :class="{ off: inCand(s.id) }"
              @tap.stop="toggleCand(s)"
            >{{ inCand(s.id) ? '✓ 已选' : '＋ 候选' }}</text>
          </view>
        </view>
        <view class="section-empty" v-if="!shops.length"><text class="empty-tip">还没有收藏餐厅</text></view>
      </view>
      <view class="tab-pad"></view>
    </scroll-view>

    <!-- 新增 / 编辑共用表单 -->
    <view class="mask" v-if="formShow" @tap="formShow = false"></view>
    <view class="form" v-if="formShow">
      <view class="form-head">
        <text class="form-title">{{ form.id ? '编辑餐厅' : '收藏餐厅' }}</text>
        <text class="close" @tap="formShow = false">✕</text>
      </view>
      <view class="f-row"><text class="f-l">名称</text><input class="f-i" v-model="form.name" placeholder="餐厅名" /></view>
      <view class="f-row"><text class="f-l">类型</text><input class="f-i" v-model="form.type" placeholder="中餐/西餐…" /></view>
      <view class="f-row"><text class="f-l">人均</text><input class="f-i" v-model="form.price" placeholder="¥" /></view>
      <view class="f-row"><text class="f-l">到达耗时(分)</text><input class="f-i" type="number" v-model.number="form.arr_min" /></view>
      <view class="f-row"><text class="f-l">交通工具</text><input class="f-i" v-model="form.transport" placeholder="步行/骑车/开车" /></view>
      <view class="f-row"><text class="f-l">招牌菜</text><input class="f-i" v-model="form.mustText" placeholder="逗号分隔" /></view>
      <view class="form-foot">
        <text class="pbtn" @tap="save">保存</text>
        <text class="pbtn ghost danger" v-if="form.id" @tap="del">删除</text>
      </view>
    </view>

    <custom-tab current="shop" />
  </view>
</template>

<script>
import { shopApi, candidateApi } from '@/api'

const emptyForm = () => ({
  id: null, name: '', type: '中餐', price: '', arr_min: 0, transport: '步行', mustText: '', star: 0
})

export default {
  data() {
    return { shops: [], cands: [], formShow: false, form: emptyForm() }
  },
  onShow() { this.load() },
  methods: {
    async load() {
      try {
        const [shops, cands] = await Promise.all([shopApi.list(), candidateApi.list()])
        this.shops = shops
        this.cands = cands
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    inCand(id) {
      return this.cands.some((c) => c.kind === 'shop' && c.ref_id === id)
    },
    // 餐厅候选只进「吃这些」，不参与采购计算
    async toggleCand(s) {
      if (this.inCand(s.id)) return uni.showToast({ title: '已在吃这些', icon: 'none' })
      try {
        await candidateApi.add('shop', s.id)
        this.cands = await candidateApi.list().catch(() => this.cands)
        uni.showToast({ title: '已加入吃这些', icon: 'success' })
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    openDetail(s) { uni.navigateTo({ url: `/pages/shop-detail/shop-detail?id=${s.id}` }) },
    openForm(s) {
      if (s) this.form = { ...emptyForm(), ...s, mustText: (s.must || []).join('、') }
      else this.form = emptyForm()
      this.formShow = true
    },
    async save() {
      const data = {
        name: this.form.name, type: this.form.type, price: this.form.price,
        arr_min: this.form.arr_min, transport: this.form.transport, star: this.form.star,
        must: this.form.mustText ? this.form.mustText.split(/[，,、]/).map((x) => x.trim()).filter(Boolean) : []
      }
      if (!data.name) return uni.showToast({ title: '请输入名称', icon: 'none' })
      try {
        if (this.form.id) await shopApi.update(this.form.id, data)
        else await shopApi.create(data)
        this.formShow = false
        this.load()
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    async del() {
      await shopApi.del(this.form.id)
      this.formShow = false
      this.load()
    }
  }
}
</script>

<style lang="scss" scoped>
.page-header { display:flex; align-items:baseline; justify-content:space-between; padding:20rpx 24rpx; padding-top:calc(env(safe-area-inset-top) + 20rpx); }
.page-title { font-size:44rpx; font-weight:700; }
.newlink { color:var(--brand); font-size:26rpx; }
.section { padding: 12rpx 24rpx; }
.row { margin-bottom:16rpx; }
.row-top { display:flex; align-items:center; gap:14rpx; }
.em { font-size:40rpx; }
.name-wrap { display:flex; align-items:center; gap:10rpx; flex:1; min-width:0; }
.name { font-weight:600; font-size:30rpx; }
.sp { flex:1; }
.star { color:#f5a623; font-size:26rpx; }
.row-bottom { display:flex; align-items:center; gap:12rpx; margin-top:12rpx; font-size:24rpx; color:var(--text-2); }
.edit-btn { font-size:24rpx; color:var(--brand); padding:6rpx 10rpx; flex-shrink:0; }
.pbtn.small { font-size:24rpx; padding:10rpx 20rpx; flex-shrink:0; }
.pbtn.off { background:#e6e6eb; color:#fff; }
.section-empty { padding:24rpx; text-align:center; }
.empty-tip { color:var(--text-2); font-size:26rpx; }
.tab-pad { height:40rpx; }

.mask { position:fixed; inset:0; background:rgba(0,0,0,.4); z-index:50; }
.form { position:fixed; left:0; right:0; bottom:0; background:var(--surface); border-radius:24rpx 24rpx 0 0; padding:24rpx; z-index:60; padding-bottom:calc(env(safe-area-inset-bottom) + 24rpx); }
.form-head { display:flex; justify-content:space-between; align-items:center; }
.form-title { font-size:34rpx; font-weight:700; }
.close { color:var(--text-2); font-size:30rpx; }
.f-row { display:flex; align-items:center; gap:16rpx; margin-top:20rpx; }
.f-l { width:180rpx; color:var(--text-2); font-size:26rpx; font-size:26rpx; }
.f-i { flex:1; background:var(--bg); border-radius:12rpx; height:76rpx; line-height:76rpx; padding:0 16rpx; font-size:28rpx; box-sizing:border-box; color:var(--text); }
.form-foot { display:flex; gap:16rpx; margin-top:24rpx; }
.pbtn.danger { background:var(--danger); }
</style>