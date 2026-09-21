<!-- mine-covers.vue —— 封面图库维护（管理员维护固定封面：emoji + 渐变主题）
  菜谱编辑时从图库点选封面；删除封面时，引用它的菜谱回退为默认（不丢数据）。
  维护项：新增 / 编辑（换 emoji、选渐变、取名）/ 上下排序 / 删除。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="uni.navigateBack()">‹</text>
      <text class="ntitle">封面图库</text>
      <text class="add" @tap="openAdd()">＋ 新增</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="inner">
        <text class="tip" v-if="!covers.length">还没有封面，点「＋ 新增」添加一个（emoji + 渐变 + 名字）。</text>
        <view class="card grow" v-for="c in covers" :key="c.id">
          <view class="cbox" :style="{ background: c.grad }"><text class="cem">{{ c.emoji }}</text></view>
          <view class="cinfo">
            <text class="iname">{{ c.name || ('封面 ' + c.id) }}</text>
            <text class="csub">{{ c.emoji }} · {{ shortGrad(c.grad) }}</text>
          </view>
          <text class="op" @tap="moveCover(c, 'up')">↑</text>
          <text class="op" @tap="moveCover(c, 'down')">↓</text>
          <text class="op" @tap="openEdit(c)">✎</text>
          <text class="op danger" @tap="delCover(c)">✕</text>
        </view>
      </view>
    </scroll-view>

    <!-- 弹窗：新增/编辑封面（emoji 输入 + 预设渐变点选 + 名字） -->
    <view class="mask" v-if="form.show" @tap="form.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">{{ form.id ? '编辑封面' : '新增封面' }}</text>
        <view class="preview" :style="{ background: form.grad }"><text class="pem">{{ form.emoji || '🍽' }}</text></view>
        <input v-model="form.emoji" placeholder="封面 Emoji，如 🍜" class="dfi" :focus="form.show" />
        <input v-model="form.name" placeholder="色调名（可选），如 海蓝" class="dfi" />
        <text class="d-sub">渐变点选</text>
        <view class="grad-grid">
          <view
            v-for="g in grads"
            :key="g"
            class="gcell"
            :class="{ on: form.grad === g }"
            :style="{ background: g }"
            @tap="form.grad = g"
          ></view>
        </view>
        <view class="d-btns">
          <button class="pbtn ghost" @tap="form.show = false">取消</button>
          <button class="pbtn" @tap="save">保存</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { coverApi } from '@/api'

// 预设渐变池（与后端默认种子一致），供新增/编辑封面点选
const grads = [
  'linear-gradient(135deg,#4b3fe3,#8b5cf6)',
  'linear-gradient(135deg,#ec4899,#f97316)',
  'linear-gradient(135deg,#06b6d4,#3b82f6)',
  'linear-gradient(135deg,#10b981,#a3e635)',
  'linear-gradient(135deg,#8b5cf6,#d946ef)',
  'linear-gradient(135deg,#f59e0b,#ef4444)',
  'linear-gradient(135deg,#f9a825,#ef6c00)',
  'linear-gradient(135deg,#34d399,#22c55e)',
  'linear-gradient(135deg,#f43f5e,#ef4444)'
]

export default {
  data() {
    return {
      grads,
      covers: [],
      form: { show: false, id: null, emoji: '🍽', name: '', grad: grads[0] }
    }
  },
  onShow() { this.load() },
  methods: {
    async load() {
      try {
        this.covers = (await coverApi.list()) || []
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    shortGrad(g) { return (g || '').replace('linear-gradient(135deg,', '').replace(')', '') },
    openAdd() {
      this.form = { show: true, id: null, emoji: '🍽', name: '', grad: grads[0] }
    },
    openEdit(c) {
      this.form = { show: true, id: c.id, emoji: c.emoji, name: c.name || '', grad: c.grad }
    },
    async save() {
      const emoji = (this.form.emoji || '').trim()
      if (!emoji) return uni.showToast({ title: '请填 Emoji', icon: 'none' })
      try {
        const body = { emoji, name: (this.form.name || '').trim(), grad: this.form.grad }
        if (this.form.id) await coverApi.update(this.form.id, body)
        else await coverApi.create(body)
        this.form.show = false
        this.load()
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    async moveCover(c, dir) {
      await coverApi.move(c.id, dir)
      this.load()
    },
    delCover(c) {
      uni.showModal({
        title: '删除封面',
        content: `删除「${c.name || c.emoji}」？使用它的菜谱会自动回到默认封面色。`,
        confirmText: '删除', confirmColor: '#e64340',
        success: async (res) => {
          if (!res.confirm) return
          try { await coverApi.del(c.id); this.load() } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
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
.ntitle { flex:1; text-align:center; font-size:34rpx; font-weight:700; padding-right:96rpx; }
.add { color:var(--brand); font-size:26rpx; }
.nscroll { flex:1; }
.inner { box-sizing:border-box; width:100%; padding:0 24rpx; }
.tip { display:block; color:var(--text-2); font-size:24rpx; padding:40rpx 0; text-align:center; }
.grow { display:flex; align-items:center; gap:16rpx; padding:18rpx 24rpx; margin-bottom:12rpx; }
.cbox { width:96rpx; height:96rpx; border-radius:18rpx; flex-shrink:0; display:flex; align-items:center; justify-content:center; }
.cem { font-size:52rpx; }
.cinfo { flex:1; min-width:0; display:flex; flex-direction:column; gap:4rpx; }
.iname { font-weight:600; font-size:28rpx; }
.csub { font-size:20rpx; color:var(--text-2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sp { flex:1; }
.op { color:var(--brand); font-size:24rpx; padding:4rpx 8rpx; }
.op.danger { color:var(--danger); }

/* 弹窗 */
.mask { position:fixed; left:0; top:0; right:0; bottom:0; background:rgba(0,0,0,0.45); z-index:999; display:flex; align-items:center; justify-content:center; padding:48rpx; }
.dialog { width:100%; max-width:560rpx; background:var(--card); border-radius:20rpx; padding:32rpx; }
.d-title { font-size:32rpx; font-weight:700; display:block; margin-bottom:20rpx; text-align:center; }
.preview { height:160rpx; border-radius:20rpx; display:flex; align-items:center; justify-content:center; margin-bottom:16rpx; }
.pem { font-size:88rpx; }
.dfi { background:var(--bg); border-radius:12rpx; height:84rpx; line-height:84rpx; padding:0 16rpx; margin-bottom:16rpx; font-size:28rpx; width:100%; box-sizing:border-box; color:var(--text); }
.d-sub { font-size:24rpx; color:var(--text-2); display:block; margin:4rpx 0 12rpx; }
.grad-grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:12rpx; }
.gcell { aspect-ratio:1; border-radius:12rpx; border:4rpx solid transparent; box-sizing:border-box; }
.gcell.on { border-color:var(--brand); }
.d-btns { display:flex; gap:16rpx; justify-content:flex-end; margin-top:16rpx; }
</style>