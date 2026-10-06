<!-- mine-tastes.vue —— 口味标签维护（全局唯一来源）
  用户自己增/删/改名，所有地方的口味 chips 都从这里取。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="uni.navigateBack()">‹</text>
      <text class="ntitle">口味标签</text>
      <text class="add" @tap="openAdd()">＋ 新增</text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="inner">
        <text class="tip" v-if="!list.length">还没有标签，点「＋ 新增」添加常用口味。<text class="t-12">菜谱筛选、成员偏好、推荐都从这里取</text></text>
        <view class="card grow" v-for="(it, idx) in list" :key="it.id">
          <text class="iname">{{ it.name }}</text>
          <text class="sp"></text>
          <text class="op" @tap="move(it, -1)" v-if="idx > 0">↑</text>
          <text class="op" @tap="move(it, 1)" v-if="idx < list.length - 1">↓</text>
          <text class="op" @tap="openEdit(it)">✎</text>
          <text class="op danger" @tap="del(it)">✕</text>
        </view>
      </view>
    </scroll-view>

    <!-- 弹窗 -->
    <view class="mask" v-if="form.show" @tap="form.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">{{ form.id ? '改标签名' : '新增口味标签' }}</text>
        <input v-model="form.name" placeholder="如：麻辣、清淡、快手" class="dfi" :focus="form.show" />
        <view class="d-btns">
          <button class="pbtn ghost" @tap="form.show = false">取消</button>
          <button class="pbtn" @tap="save">保存</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { tasteApi } from '@/api'

export default {
  data() {
    return {
      list: [],
      form: { show: false, id: null, name: '' }
    }
  },
  onShow() { this.load() },
  methods: {
    async load() {
      try { this.list = await tasteApi.list() } catch (e) { this.list = [] }
    },
    openAdd() { this.form = { show: true, id: null, name: '' } },
    openEdit(it) { this.form = { show: true, id: it.id, name: it.name } },
    async move(it, dir) {
      const idx = this.list.findIndex((x) => x.id === it.id)
      const nIdx = idx + dir
      if (idx < 0 || nIdx < 0 || nIdx >= this.list.length) return
      const ids = this.list.map((x) => x.id)
      ;[ids[idx], ids[nIdx]] = [ids[nIdx], ids[idx]]
      ;[this.list[idx], this.list[nIdx]] = [this.list[nIdx], this.list[idx]]
      await tasteApi.reorder(ids)
    },
    async save() {
      const name = (this.form.name || '').trim()
      if (!name) return uni.showToast({ title: '标签名不能为空', icon: 'none' })
      try {
        if (this.form.id) await tasteApi.update(this.form.id, name)
        else await tasteApi.create(name)
        this.form.show = false
        await this.load()
      } catch (e) {
        uni.showToast({ title: e.message || '保存失败', icon: 'none' })
      }
    },
    async del(it) {
      uni.showModal({
        title: '删除标签', content: `确定删除「${it.name}」吗？`, success: async (res) => {
          if (!res.confirm) return
          try {
            await tasteApi.del(it.id)
            await this.load()
          } catch (e) {
            uni.showToast({ title: e.message || '删除失败', icon: 'none' })
          }
        }
      })
    }
  }
}
</script>

<style>
.npage { min-height: 100vh; background: var(--bg); display: flex; flex-direction: column; }
.nheader { display: flex; align-items: center; gap: 12rpx; padding: calc(env(safe-area-inset-top) + 16rpx) var(--nav-safe-right) 16rpx 24rpx; position: sticky; top: 0; background: var(--surface); z-index: 10; }
.back { font-size: 44rpx; color: var(--brand); padding-right: 20rpx; white-space: nowrap; }
.ntitle { flex: 1; text-align: center; font-size: 34rpx; font-weight: 700; }
.add { font-size: 28rpx; color: var(--brand); padding: 12rpx 24rpx; border-radius: 999rpx; box-shadow: inset 0 0 0 2rpx var(--brand); }
.nscroll { flex: 1; }
.inner { padding: 16rpx 24rpx 120rpx; }
.tip { font-size: 24rpx; color: var(--text-2); display: block; padding: 24rpx 12rpx; }
.card { background: var(--card); border: 1rpx solid var(--border); border-radius: 14rpx; padding: 20rpx 24rpx; margin-bottom: 12rpx; display: flex; align-items: center; gap: 16rpx; }
.grow .iname { font-size: 30rpx; }
.sp { flex: 1; }
.op { font-size: 26rpx; color: var(--text-2); padding: 8rpx 16rpx; border-radius: 8rpx; }
.op.danger { color: #e85d5d; }

.mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog { width: 600rpx; background: var(--surface); border-radius: 20rpx; padding: 36rpx 32rpx; }
.d-title { font-size: 32rpx; font-weight: 700; display: block; margin-bottom: 24rpx; }
.dfi { background: var(--bg); border-radius: 12rpx; height: 84rpx; line-height: 84rpx; padding: 0 16rpx; margin-bottom: 16rpx; font-size: 28rpx; width: 100%; box-sizing: border-box; color: var(--text); }
.d-btns { display: flex; gap: 16rpx; justify-content: flex-end; margin-top: 16rpx; }
.pbtn { padding: 16rpx 32rpx; border-radius: 12rpx; background: var(--brand); color: #fff; font-size: 28rpx; border: none; }
.pbtn.ghost { background: transparent; color: var(--text-2); box-shadow: inset 0 0 0 1rpx solid var(--border); }
.t-12 { font-size: 22rpx; color: var(--text-2); margin-left: 8rpx; }
</style>
