<!-- mine.vue —— 我的页（对齐「第一版 UI」p-me）
  结构：资料头（头像+昵称+副标题）→ 统计条(本周做了多少顿 / 我的菜谱 / 收藏餐厅)
        → 干饭成员(各自口味偏好维护) → 功能菜单行(图标 + 标题 + 副标题 + ›)
-->
<template>
  <view class="tab-page">
    <view class="page-header">
      <text class="page-title">我的</text>
    </view>

    <scroll-view class="tab-scroll" scroll-y>
      <!-- 资料头 -->
      <view class="section">
        <view class="pro">
          <view class="ava"><text class="ava-em">{{ curName.slice(0, 1) }}</text></view>
          <view class="pro-c">
            <view class="pro-nm">
              <text class="pname">{{ curName }}</text>
              <text class="u-role" v-if="isAdmin">管理员</text>
            </view>
            <text class="pmail">一人食 · 主打快手菜</text>
          </view>
          <text class="newlink" @tap="switchUser">切换</text>
        </view>
      </view>

      <!-- 统计条 -->
      <view class="section">
        <view class="stat-bar">
          <view class="sc" @tap="nav('/pages/mine-records/mine-records')">
            <text class="st-num">{{ weekCount }}</text><text class="st-lab">本周做了多少顿</text>
          </view>
          <view class="sc" @tap="nav('/pages/recipe/recipe')">
            <text class="st-num">{{ myRecipes }}</text><text class="st-lab">我的菜谱</text>
          </view>
          <view class="sc" @tap="nav('/pages/shop/shop')">
            <text class="st-num">{{ shopCount }}</text><text class="st-lab">收藏餐厅</text>
          </view>
        </view>
      </view>

      <!-- 干饭成员 -->
      <view class="section">
        <view class="sec-head">
          <text class="sec-title">干饭成员</text>
          <text class="newlink" @tap="addDiner">＋ 成员</text>
        </view>
        <view class="card row" v-for="d in diners" :key="d.id">
          <view class="row-top">
            <text class="name">{{ d.name }}</text>
            <text class="sp"></text>
            <text class="op" @tap="editDiner(d)">口味</text>
            <text class="op danger" @tap="delDiner(d)">✕</text>
          </view>
          <view class="row-bottom" v-if="d.tags && d.tags.length">
            <text class="t-pill" v-for="t in d.tags" :key="t">{{ t }}</text>
          </view>
        </view>
      </view>

      <!-- 功能菜单 -->
      <view class="section">
        <view class="menu">
          <view class="mrow" @tap="nav('/pages/mine-ref/mine-ref')">
            <text class="ic">📚</text><view class="m1"><text class="mt">参考菜谱</text><text class="ms">管理员精选 · 可加入吃这些或我的菜谱</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-tips/mine-tips')">
            <text class="ic">👨‍🍳</text><view class="m1"><text class="mt">厨房技巧</text><text class="ms">大家的技巧 · 新增/修改需审核</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-records/mine-records')">
            <text class="ic">📋</text><view class="m1"><text class="mt">饮食记录</text><text class="ms">日历 · 统计 · 去重</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-weight/mine-weight')">
            <text class="ic">⚖️</text><view class="m1"><text class="mt">体重记录</text><text class="ms">曲线图 · 历史数据维护</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-ingredients/mine-ingredients')">
            <text class="ic">🧺</text><view class="m1"><text class="mt">食材库</text><text class="ms">菜谱可选食材 · 独立维护</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-covers/mine-covers')">
            <text class="ic">🖼️</text><view class="m1"><text class="mt">封面图库</text><text class="ms">菜谱封面 · 管理员维护点选</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" @tap="nav('/pages/mine-settings/mine-settings')">
            <text class="ic">⚙️</text><view class="m1"><text class="mt">设置</text><text class="ms">账号 · 数据 · 关于</text></view><text class="ar">›</text>
          </view>
          <view class="mrow" v-if="isPc" @tap="nav('/pages/admin/admin')">
            <text class="ic">🖥️</text><view class="m1"><text class="mt">管理端（PC）</text><text class="ms">审核 · 图库 · 食材 · 餐厅 · 配置</text></view><text class="ar">›</text>
          </view>
        </view>
      </view>

      <view class="tab-pad"></view>
    </scroll-view>

    <custom-tab current="mine" />

    <!-- 居中弹窗（自绘遮罩，兼容 H5/App/小程序）
     注释：uni.showModal 的 editable 在 H5 不支持且无法自定义样式，故用自定义弹窗承载输入。 -->
    <view class="mask" v-if="form.show" @tap="form.show = false">
      <view class="dialog" @tap.stop>
        <text class="d-title">{{ form.title }}</text>
        <input v-model="form.val" :placeholder="form.hint" class="dfi" :focus="form.show" />
        <view class="d-btns">
          <button class="pbtn ghost" @tap="form.show = false">取消</button>
          <button class="pbtn" @tap="saveForm">{{ form.mode === 'tags' ? '保存口味' : '确定' }}</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { dinerApi, recordApi, recipeApi, shopApi } from '@/api'

export default {
  data() {
    return { diners: [], curName: '', isAdmin: false, weekCount: 0, myRecipes: 0, shopCount: 0, isPc: false, form: { show: false, mode: '', title: '', val: '', hint: '', id: null } }
  },
  onShow() {
    this.curName = uni.getStorageSync('eat_user') || '我'
    // 管理员演示开关：本地标记（MVP）
    this.isAdmin = uni.getStorageSync('eat_admin') === '1'
    // PC 管理端入口：仅桌面宽屏可见（>=1024px），移动端不显示
    try { this.isPc = (uni.getWindowInfo && uni.getWindowInfo().windowWidth) >= 1024 } catch (e) { this.isPc = window.innerWidth >= 1024 }
    this.load()
  },
  methods: {
    async load() {
      try {
        const [diners, records, recipes, shops] = await Promise.all([
          dinerApi.list(), recordApi.list(), recipeApi.list(), shopApi.list()
        ])
        this.diners = diners
        // 统计条（取自真实数据，实时算）
        this.weekCount = this.countThisWeek(records)
        this.myRecipes = recipes.filter((r) => r.source === 'my').length
        this.shopCount = shops.length
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // 本周（周一起）做了多少顿
    countThisWeek(records) {
      const now = new Date()
      const day = (now.getDay() + 6) % 7 // 周一=0
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - day)
      return records.filter((r) => {
        if (!r.date) return false
        const d = new Date(r.date)
        return !isNaN(d) && d >= start
      }).length
    },
    // 三个入口统一走居中弹窗（mode: user 切换用户 / diner 新增成员 / tags 编辑口味）
    switchUser() {
      this.form = { show: true, mode: 'user', title: '切换用户', val: this.curName, hint: '输入名字', id: null }
    },
    addDiner() {
      this.form = { show: true, mode: 'diner', title: '添加成员', val: '', hint: '姓名', id: null }
    },
    editDiner(d) {
      this.form = { show: true, mode: 'tags', title: '编辑口味', val: (d.tags || []).join('，'), hint: '口味，逗号分隔', id: d.id }
    },
    async saveForm() {
      const v = (this.form.val || '').trim()
      if (this.form.mode === 'user') {
        if (!v) return uni.showToast({ title: '名字不能为空', icon: 'none' })
        uni.setStorageSync('eat_user', v)
        this.curName = v
      } else if (this.form.mode === 'diner') {
        if (!v) return uni.showToast({ title: '姓名不能为空', icon: 'none' })
        await dinerApi.create({ name: v, tags: [] })
      } else if (this.form.mode === 'tags') {
        // 逗号/顿号/空格分隔多个口味
        const tags = v.split(/[，,、\s]+/).filter(Boolean)
        await dinerApi.updateTags(this.form.id, tags)
      }
      this.form.show = false
      this.load()
    },
    async delDiner(d) {
      await dinerApi.del(d.id)
      this.load()
    },
    nav(url) {
      // 餐厅/菜谱是 tab 页，用 reLaunch；其余二级页 navigateTo
      if (url.includes('/shop/shop') || url.includes('/recipe/recipe')) return uni.reLaunch({ url })
      uni.navigateTo({ url })
    }
  }
}
</script>

<style lang="scss" scoped>
.page-header { display:flex; align-items:baseline; gap:16rpx; padding:20rpx 24rpx; padding-top:calc(env(safe-area-inset-top) + 20rpx); }
.page-title { font-size:44rpx; font-weight:700; }
.section { padding: 12rpx 24rpx; }
.sec-head { display:flex; align-items:center; justify-content:space-between; margin:6rpx 0 16rpx; }
.sec-title { font-size:32rpx; font-weight:700; }
.newlink { color:var(--brand); font-size:26rpx; }

/* 居中弹窗 */
.mask { position:fixed; left:0; top:0; right:0; bottom:0; background:rgba(0,0,0,0.45); z-index:999; display:flex; align-items:center; justify-content:center; padding:48rpx; }
.dialog { width:100%; max-width:560rpx; background:var(--card); border-radius:20rpx; padding:32rpx; }
.d-title { font-size:32rpx; font-weight:700; display:block; margin-bottom:20rpx; }
.dfi { background:var(--bg); border-radius:12rpx; height:84rpx; line-height:84rpx; padding:0 16rpx; margin-bottom:24rpx; font-size:28rpx; width:100%; box-sizing:border-box; color:var(--text); }
.d-btns { display:flex; gap:16rpx; justify-content:flex-end; }

/* 资料头 */
.pro { display:flex; align-items:center; gap:20rpx; background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); padding:26rpx 24rpx; }
.ava { width:92rpx; height:92rpx; border-radius:50%; background:linear-gradient(135deg,#4b3fe3,#8b5cf6); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.ava-em { font-size:40rpx; color:#fff; font-weight:600; }
.pro-c { flex:1; min-width:0; display:flex; flex-direction:column; gap:4rpx; }
.pro-nm { display:flex; align-items:center; gap:10rpx; }
.pname { font-size:34rpx; font-weight:700; }
.pmail { font-size:24rpx; color:var(--text-2); }
.u-role { font-size:20rpx; color:var(--brand); background:#efeaff; padding:2rpx 12rpx; border-radius:999rpx; }

/* 统计条 */
.stat-bar { display:flex; background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); overflow:hidden; }
.sc { flex:1; display:flex; flex-direction:column; align-items:center; gap:6rpx; padding:22rpx 0; }
.sc + .sc { border-left:1rpx solid var(--border); }
.st-num { font-size:40rpx; font-weight:700; color:var(--brand); }
.st-lab { font-size:22rpx; color:var(--text-2); text-align:center; }

/* 干饭成员 */
.row { margin-bottom:16rpx; }
.row-top { display:flex; align-items:center; gap:12rpx; }
.name { font-weight:600; font-size:30rpx; }
.sp { flex:1; }
.op { color:var(--brand); font-size:24rpx; padding:4rpx 8rpx; }
.op.danger { color:var(--danger); }
.row-bottom { display:flex; flex-wrap:wrap; gap:8rpx; margin-top:10rpx; }
.t-pill { font-size:20rpx; color:var(--text-2); background:var(--bg); padding:3rpx 12rpx; border-radius:999rpx; }

/* 功能菜单 */
.menu { background:var(--card); border:1rpx solid var(--border); border-radius:var(--radius-lg,16rpx); overflow:hidden; }
.mrow { display:flex; align-items:center; gap:18rpx; padding:24rpx 24rpx; }
.mrow + .mrow { border-top:1rpx solid var(--border); }
.ic { font-size:34rpx; }
.m1 { flex:1; min-width:0; display:flex; flex-direction:column; gap:3rpx; }
.mt { font-size:30rpx; font-weight:600; }
.ms { font-size:22rpx; color:var(--text-2); }
.ar { color:var(--text-2); font-size:30rpx; }
.tab-pad { height:40rpx; }
</style>