<!-- mine-tips.vue —— 厨房技巧：所有用户可见+可新增；只可改/删自己的；
  新增/修改需管理员审核（audit_enabled 配置）；待审核⏳/已公开✅/未通过🚫。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="back">‹</text>
      <text class="ntitle">厨房技巧</text>
      <text class="add" @tap="openForm()">＋ 我来加</text>
    </view>

    <!-- 管理员审核演示开关 -->
    <view class="admbar">
      <text class="adm-txt">⚙ 管理员审核（演示）</text>
      <switch :checked="admin" :style="{ transform: 'scale(0.7)' }" @change="(e) => toggleAdmin(e)" />
    </view>

    <!-- 编辑表单（新增 / 编辑复用） -->
    <view class="form" v-if="showForm">
      <input v-model="form.title" placeholder="标题" class="fi" />
      <textarea v-model="form.content" placeholder="内容" class="ft" />
      <input v-model="form.category" placeholder="分类（可省）" class="fi" />
      <view class="pub-row">
        <text class="pub-lbl">公开</text>
        <switch :checked="form.public === 1" @change="(e) => (form.public = e.detail.value ? 1 : 0)" :style="{ transform: 'scale(0.7)' }" />
      </view>
      <view class="form-btns">
        <button class="pbtn ghost" @tap="showForm = false">取消</button>
        <button class="pbtn" @tap="saveForm">{{ editingId ? '保存修改' : '提交（待审核）' }}</button>
      </view>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="section">
        <view class="card trow" v-for="t in list" :key="t.id">
          <view class="trow-head">
            <text class="ttitle">{{ t.title }}</text>
            <text class="tstate" :class="t.status">{{ statusText(t.status) }}</text>
          </view>
          <text class="tcontent">{{ t.content }}</text>
          <view class="tmeta">
            <text class="tcat">{{ t.category || '未分类' }}</text>
            <text class="tauthor">{{ t.author }}</text>
          </view>
          <!-- 自己的内容可编辑/删除 -->
          <view class="tops" v-if="t.author === curName">
            <text class="op" @tap="openForm(t)">编辑</text>
            <text class="op danger" @tap="del(t)">✕ 删除</text>
          </view>
          <!-- 管理员审核操作 -->
          <view class="tops" v-if="admin && t.status === 'pending'">
            <text class="op ok" @tap="approve(t)">通过</text>
            <text class="op danger" @tap="reject(t)">退回</text>
          </view>
        </view>
        <view v-if="!list.length" class="empty">还没有技巧，点「＋ 我来加」新增</view>
      </view>
      <view class="pad"></view>
    </scroll-view>
  </view>
</template>

<script>
import { tipApi } from '@/api'

export default {
  data() {
    return {
      curName: '', admin: false,
      list: [], showForm: false, editingId: null,
      form: { title: '', content: '', category: '', public: 1 }
    }
  },
  onShow() {
    this.curName = uni.getStorageSync('eat_user') || '我'
    this.admin = uni.getStorageSync('eat_admin') === '1'
    this.load()
  },
  methods: {
    back() { uni.navigateBack() },
    async load() {
      try { this.list = await tipApi.list(this.curName, this.admin) }
      catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    toggleAdmin(e) {
      uni.setStorageSync('eat_admin', e.detail.value ? '1' : '0')
      this.admin = e.detail.value
      this.load()
    },
    statusText(s) { return { pending: '⏳ 待审核', approved: '✅ 已公开', rejected: '🚫 未通过' }[s] || '' },
    openForm(t) {
      this.showForm = true
      this.editingId = t ? t.id : null
      this.form = t ? { title: t.title, content: t.content, category: t.category || '', public: t.public } : { title: '', content: '', category: '', public: 1 }
    },
    async saveForm() {
      const d = { title: this.form.title, content: this.form.content, category: this.form.category, public: this.form.public }
      if (this.editingId) await tipApi.update(this.editingId, { ...d, author: this.curName })
      else await tipApi.create({ ...d, author: this.curName })
      this.showForm = false
      this.load()
    },
    async del(t) { await tipApi.del(t.id, this.curName); this.load() },
    async approve(t) { await tipApi.approve(t.id); this.load() },
    async reject(t) { await tipApi.reject(t.id); this.load() }
  }
}
</script>

<style lang="scss" scoped>
.npage { display:flex; flex-direction:column; height:100vh; background:var(--bg); }
.nheader { display:flex; align-items:center; gap:16rpx; padding:calc(env(safe-area-inset-top) + 16rpx) 24rpx 16rpx; }
.back { font-size:48rpx; font-weight:600; }
.ntitle { font-size:36rpx; font-weight:700; flex:1; }
.add { color:var(--brand); font-size:26rpx; }
.admbar { display:flex; align-items:center; justify-content:space-between; margin:0 24rpx; padding:10rpx 20rpx; background:#efeaff; border-radius:12rpx; }
.adm-txt { font-size:24rpx; color:var(--brand); }
.form { margin:16rpx 24rpx; padding:20rpx; background:var(--card); border:1rpx solid var(--border); border-radius:16rpx; }
.fi, .ft { background:var(--bg); border-radius:10rpx; height:76rpx; line-height:76rpx; padding:0 16rpx; margin-bottom:12rpx; font-size:26rpx; width:100%; box-sizing:border-box; color:var(--text); }
.ft { height:160rpx; line-height:1.5; padding:14rpx 16rpx; }
.pub-row { display:flex; align-items:center; justify-content:space-between; margin-bottom:12rpx; }
.pub-lbl { font-size:26rpx; }
.form-btns { display:flex; gap:16rpx; justify-content:flex-end; }
.nscroll { flex:1; }
.section { padding:12rpx 24rpx; }
.trow { margin-bottom:16rpx; }
.trow-head { display:flex; align-items:center; justify-content:space-between; gap:12rpx; }
.ttitle { font-size:30rpx; font-weight:700; flex:1; }
.tstate { font-size:20rpx; padding:2rpx 12rpx; border-radius:999rpx; }
.tstate.pending { color:var(--warning); background:#fff4e0; }
.tstate.approved { color:var(--success); background:#e6f9ef; }
.tstate.rejected { color:var(--danger); background:#fdecec; }
.tcontent { display:block; color:var(--text-2); font-size:26rpx; margin:10rpx 0; }
.tmeta { display:flex; gap:16rpx; align-items:center; font-size:22rpx; color:var(--text-2); }
.tauthor { color:var(--brand); }
.tops { display:flex; gap:16rpx; margin-top:10rpx; justify-content:flex-start; }
.op { font-size:24rpx; color:var(--brand); padding:4rpx 8rpx; }
.op.danger { color:var(--danger); }
.op.ok { color:var(--success); }
.empty { color:var(--text-2); text-align:center; padding:40rpx 0; }
.pad { height:40rpx; }
</style>