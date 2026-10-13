<!-- family.vue —— 家庭页（原我的页「干饭成员」区块升级为家庭功能）
  创建家庭（起名）/ 凭 6 位家庭 ID 加入对方的家庭 / 已加入展示（ID 复制、成员、退出）。
  家庭成员共享「吃这些」候选：吃这些页顶部切换「我的 / 家庭空间」，人人可加/删/启停计时，
  缺货代入与回退记在加者自己的待采购上（谁加的记谁的账）。
-->
<template>
  <view class="npage">
    <view class="nheader">
      <text class="back" @tap="uni.navigateBack()">‹</text>
      <text class="ntitle">家庭</text>
      <text class="add"></text>
    </view>

    <scroll-view class="nscroll" scroll-y>
      <view class="inner">
        <!-- 说明卡 -->
        <view class="card intro">
          <text class="i-title">🏠 家庭空间</text>
          <text class="i-sub">和家人共用一份「吃这些」候选：把 6 位家庭 ID 发给对方，TA 加入后就能一起看候选、加菜删菜，缺的食材会自动代入加菜人的待采购。</text>
        </view>

        <!-- 未加入：创建 / 加入 -->
        <template v-if="!family">
          <view class="card">
            <text class="c-title">创建家庭空间</text>
            <view class="f-row">
              <input v-model="createName" placeholder="给家庭起个名字，如：幸福一家" class="dfi grow" />
              <button class="pbtn sm" @tap="create">创建</button>
            </view>
          </view>
          <view class="card">
            <text class="c-title">加入对方的家庭</text>
            <view class="f-row">
              <input v-model="joinCode" placeholder="输入 6 位家庭 ID" class="dfi grow code" maxlength="6" />
              <button class="pbtn sm" @tap="join">加入</button>
            </view>
          </view>
        </template>

        <!-- 已加入：家庭卡 -->
        <template v-else>
          <view class="card fam">
            <view class="row-top">
              <text class="name">🏠 {{ family.name }}</text>
              <text class="sp"></text>
              <text class="code" @tap="copyCode">ID {{ family.code }} ⧉</text>
            </view>
            <view class="members">
              <view class="mem" v-for="m in family.members" :key="m.user_id">
                <text class="m-ava">{{ m.avatar || (m.nickname || '成').slice(0, 1) }}</text>
                <text class="m-name">{{ m.nickname || '成员' }}{{ m.user_id === family.owner_id ? ' · 创建者' : '' }}</text>
              </view>
            </view>
            <view class="fam-tip">把 ID {{ family.code }} 发给家人，TA 在「我的 → 家庭」页粘贴即可加入</view>
            <button class="pbtn ghost danger leave" @tap="leave">{{ isOwner ? '解散家庭' : '退出家庭' }}</button>
          </view>
        </template>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { familyApi, getCurUser } from '@/api'

export default {
  data() {
    return {
      family: null,                 // 我的家庭空间（null=未加入）
      createName: '', joinCode: ''
    }
  },
  onShow() { this.load() },
  computed: {
    // 模板「解散/退出」按钮文案用：owner_id 是当前登录用户 id 才算创建者
    isOwner() { return this.checkOwner() },
  },
  methods: {
    async load() {
      // 家庭空间（未登录接口会 401，静默处理为未加入）
      try { const r = await familyApi.mine(); this.family = r.family || null } catch (e) { this.family = null }
    },
    copyCode() {
      if (!this.family) return
      uni.setClipboardData({
        data: this.family.code,
        success: () => uni.showToast({ title: '家庭 ID 已复制', icon: 'success' })
      })
    },
    async create() {
      const name = (this.createName || '').trim()
      if (!name) return uni.showToast({ title: '先给家庭起个名字吧', icon: 'none' })
      try {
        this.family = await familyApi.create(name)
        this.createName = ''
        uni.showToast({ title: '家庭空间已创建', icon: 'success' })
      } catch (e) { uni.showToast({ title: e.message || '创建失败', icon: 'none' }) }
    },
    async join() {
      const code = (this.joinCode || '').trim()
      if (!code) return uni.showToast({ title: '请输入 6 位家庭 ID', icon: 'none' })
      try {
        this.family = await familyApi.join(code)
        this.joinCode = ''
        uni.showToast({ title: '已加入家庭空间', icon: 'success' })
      } catch (e) { uni.showToast({ title: e.message || '加入失败', icon: 'none' }) }
    },
    leave() {
      if (!this.family) return
      const isOwner = this.checkOwner()
      uni.showModal({
        title: isOwner ? '解散家庭' : '退出家庭',
        content: isOwner
          ? `解散「${this.family.name}」后，家庭候选池将清空，所有成员都会被移出。确定解散？`
          : `退出「${this.family.name}」后，将看不到家庭候选池。确定退出？`,
        confirmColor: '#e64340',
        success: async (res) => {
          if (!res.confirm) return
          try {
            const r = await familyApi.leave()
            this.family = null
            uni.showToast({ title: r.dissolved ? '家庭已解散' : '已退出家庭', icon: 'none' })
          } catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
        }
      })
    },
    checkOwner() {
      // owner_id 是当前登录用户 id 才算创建者
      return !!this.family && this.family.owner_id === getCurUser()
    },
  }
}
</script>

<style>
.npage { min-height: 100vh; background: var(--bg); display: flex; flex-direction: column; }
.nheader { display: flex; align-items: center; gap: 12rpx; padding: calc(env(safe-area-inset-top) + 16rpx) var(--nav-safe-right) 16rpx 24rpx; position: sticky; top: 0; background: var(--surface); z-index: 10; }
.back { font-size: 44rpx; color: var(--brand); padding-right: 20rpx; white-space: nowrap; }
.ntitle { flex: 1; text-align: center; font-size: 34rpx; font-weight: 700; }
.add { font-size: 28rpx; color: var(--brand); padding: 12rpx 24rpx; }
.nscroll { flex: 1; }
.inner { padding: 16rpx 24rpx 120rpx; }

.card { background: var(--card); border: 1rpx solid var(--border); border-radius: 14rpx; padding: 24rpx; margin-bottom: 12rpx; }
.intro .i-title { font-size: 30rpx; font-weight: 700; display: block; margin-bottom: 10rpx; }
.intro .i-sub { font-size: 24rpx; color: var(--text-2); line-height: 1.6; display: block; }

.c-title { font-size: 28rpx; font-weight: 600; display: block; margin-bottom: 16rpx; }
.f-row { display: flex; align-items: center; gap: 16rpx; }
.grow { flex: 1; }
.dfi { background: var(--bg); border-radius: 12rpx; height: 84rpx; line-height: 84rpx; padding: 0 16rpx; font-size: 28rpx; width: 100%; box-sizing: border-box; color: var(--text); }
.f-row .dfi { width: auto; margin-bottom: 0; }
.dfi.code { letter-spacing: 6rpx; text-transform: uppercase; }
.pbtn { padding: 16rpx 32rpx; border-radius: 12rpx; background: var(--brand); color: #fff; font-size: 28rpx; border: none; flex-shrink: 0; }
.pbtn.sm { padding: 20rpx 32rpx; }
.pbtn.ghost { background: transparent; color: var(--text-2); box-shadow: inset 0 0 0 1rpx var(--border); }
.pbtn.danger { color: #e85d5d; box-shadow: inset 0 0 0 1rpx #f3c1c1; }
.leave { margin-top: 16rpx; width: 100%; }

/* 家庭卡 */
.fam .row-top { display: flex; align-items: center; gap: 12rpx; }
.fam .name { font-weight: 700; font-size: 32rpx; }
.fam .sp { flex: 1; }
.fam .code { font-size: 26rpx; color: var(--brand); padding: 6rpx 16rpx; border-radius: 999rpx; box-shadow: inset 0 0 0 2rpx var(--brand); }
.members { display: flex; flex-wrap: wrap; gap: 16rpx; margin-top: 20rpx; }
.mem { display: flex; align-items: center; gap: 10rpx; background: var(--bg); border-radius: 999rpx; padding: 8rpx 20rpx 8rpx 8rpx; }
.m-ava { width: 48rpx; height: 48rpx; border-radius: 50%; background: linear-gradient(135deg,#4b3fe3,#8b5cf6); color: #fff; font-size: 24rpx; display: flex; align-items: center; justify-content: center; }
.m-name { font-size: 24rpx; color: var(--text); }
.fam-tip { font-size: 22rpx; color: var(--text-2); margin-top: 16rpx; display: block; }
</style>
