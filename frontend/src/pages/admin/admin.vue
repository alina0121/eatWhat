<!-- admin.vue —— 吃啥 · PC 管理端（桌面宽屏：左侧菜单 + 右侧内容区）
  复用现有移动端同一套 API（tipApi/recipeApi/coverApi/ingredientApi/catApi/configApi），
  并新增 adminApi（密码登录 + 统计聚合）。入口在「我的」页仅 PC 宽屏显示，移动端不可见。
  登录口令在配置表 admin_passcode（默认 123456），仅门控管理台，不影响移动端。
-->
<template>
  <view class="admin">
    <!-- 顶部 header -->
    <view class="ahead">
      <text class="ah-l">🍜 吃啥 · 管理端</text>
      <view class="ah-r">
        <text class="ah-user">{{ curName }}</text>
        <view class="ah-role" :class="{ off: !isAdmin }">{{ isAdmin ? '管理员' : '未登录' }}</view>
        <text class="ah-back" @tap="back">‹ 返回 App</text>
      </view>
    </view>

    <!-- 登录门：密码登录（默认口令 123456，存配置表，改库可换） -->
    <view class="gate" v-if="!isAdmin">
      <text class="gate-ic">🔒</text>
      <text class="gate-t">管理端功能需输入管理员口令</text>
      <input class="gate-in" v-model="loginCode" password placeholder="请输入口令" style="text-align:center" />
      <view class="gate-act">
        <button class="pbtn" @click="doLogin">登 录</button>
      </view>
      <text class="gate-hint">提示：默认口令 123456（后台配置 admin_passcode）</text>
    </view>

    <view class="abody" v-if="isAdmin">
      <!-- 左侧菜单 -->
      <view class="asider">
        <view class="nav" v-for="m in menus" :key="m.k" :class="{ on: sec === m.k }" @tap="sec = m.k">
          <text class="nav-ic">{{ m.ic }}</text>
          <text class="nav-t">{{ m.t }}</text>
        </view>
      </view>

      <!-- 右侧内容区 -->
      <view class="acont">
        <!-- ============ 0. 统计（仅公共资源） ============ -->
        <template v-if="sec === 'stats'">
          <view class="sec-h"><text class="sh-t">统计</text><text class="sh-s">公共资源概况；个人数据请去用户端查看</text></view>
          <view class="kpis">
            <view class="kpi card" v-for="k in kpis" :key="k.ic">
              <text class="kpi-ic">{{ k.ic }}</text>
              <text class="kpi-num">{{ k.k }}</text>
              <text class="kpi-t">{{ k.t }}</text>
            </view>
          </view>
        </template>

        <!-- ============ 1. 用户管理 ============ -->
        <template v-if="sec === 'users'">
          <view class="sec-h">
            <text class="sh-t">用户管理</text>
            <view class="sec-act"><button class="pbtn" @click="openUserAdd">＋ 新增用户</button></view>
          </view>
          <view class="row card" v-for="u in users" :key="u.id">
            <view class="uico">{{ u.role === 'admin' ? '👑' : '🙂' }}</view>
            <view class="uc"><text class="sn">{{ u.name }}</text><text class="sm">{{ u.role === 'admin' ? '管理员' : '普通用户' }}</text></view>
            <view class="sp"></view>
            <button class="pbtn ghost" @click="toggleRole(u)">{{ u.role === 'admin' ? '设为普通' : '设为管理' }}</button>
            <button class="pbtn ghost" @click="editUser(u)">✎</button>
            <button class="pbtn danger" @click="delUser(u)" :class="{ dis: u.id === 1 }">✕</button>
          </view>
          <text class="none" v-if="!users.length">还没有用户</text>
        </template>

        <!-- ============ 1. 厨房技巧审核 ============ -->
        <template v-if="sec === 'tips'">
          <view class="sec-h"><text class="sh-t">厨房技巧审核</text><text class="sh-s">对待审核内容「通过 / 退回」</text></view>
          <view class="fbar">
            <input class="fsearch" v-model="tipQ" placeholder="搜索标题 / 内容…" />
            <view class="seg">
              <text v-for="s in tipSts" :key="s.k" class="sell" :class="{ on: tipSt === s.k }" @click="tipSt = s.k">{{ s.t }}</text>
            </view>
            <text class="fcount">共 {{ filterTips.length }} 条</text>
          </view>
          <view class="tips">
            <view class="trow card" v-for="t in shownTips" :key="t.id">
              <view class="trow-head">
                <text class="tt">{{ t.title }}</text>
                <text class="tst" :class="t.status">{{ statusText(t.status) }}</text>
              </view>
              <text class="tct">{{ t.content }}</text>
              <view class="tmeta">
                <text class="tcat">{{ t.category || '未分类' }}</text>
                <text class="tusr">{{ t.author }}</text>
              </view>
              <view class="tops" v-if="t.status === 'pending'">
                <button class="pbtn ok" @click="approve(t)">✓ 通过</button>
                <button class="pbtn danger" @click="reject(t)">✕ 退回</button>
              </view>
            </view>
            <text class="none" v-if="!filterTips.length">暂无可审核的技巧</text>
            <button class="pbtn ghost more" v-if="filterTips.length > shownTips.length" @click="tipLimit += 20">加载更多（{{ shownTips.length }}/{{ filterTips.length }}）</button>
          </view>
        </template>

        <!-- ============ 2. 参考菜谱 ============ -->
        <template v-if="sec === 'ref'">
          <view class="sec-h">
            <text class="sh-t">参考菜谱</text>
            <view class="sec-act">
              <text class="sh-note">可录入 / 编辑 / 删除</text>
              <button class="pbtn" @click="openModal('ref')">＋ 录入</button>
            </view>
          </view>
          <view class="fbar">
            <input class="fsearch" v-model="refQ" placeholder="按菜名搜索…" />
            <text class="fcount">共 {{ filterRefs.length }} 条</text>
          </view>
          <view class="grid">
            <view class="rcard" v-for="r in shownRefs" :key="r.id">
              <view class="rcover" :style="{ background: r.coverGrad || DEFAULT_GRAD }"><text class="rem">{{ r.em }}</text></view>
              <view class="rinfo"><text class="rn">{{ r.name }}</text><text class="rm">{{ r.time }}分钟 · {{ r.diff }}</text></view>
              <view class="raction">
                <button class="pbtn ghost" @click="editRef(r)">✎ 编辑</button>
                <button class="pbtn danger" @click="delRef(r)">✕ 删除</button>
              </view>
            </view>
            <text class="none" v-if="!filterRefs.length">还没有参考菜谱</text>
            <button class="pbtn ghost more" v-if="filterRefs.length > shownRefs.length" @click="refLimit += 20">加载更多（{{ shownRefs.length }}/{{ filterRefs.length }}）</button>
          </view>
        </template>

        <!-- ============ 3. 封面图库 ============ -->
        <template v-if="sec === 'covers'">
          <view class="sec-h">
            <text class="sh-t">封面图库</text>
            <view class="sec-act"><button class="pbtn" @click="openModal('cover')">＋ 新增</button></view>
          </view>
          <view class="clist">
            <view class="crow card" v-for="c in covers" :key="c.id">
              <view class="cbox" :style="{ background: c.grad }"><text class="cem">{{ c.emoji }}</text></view>
              <text class="cn">{{ c.name || ('封面 ' + c.id) }}</text>
              <view class="sp"></view>
              <button class="pbtn ghost" @click="moveCover(c, 'up')">↑</button>
              <button class="pbtn ghost" @click="moveCover(c, 'down')">↓</button>
              <button class="pbtn ghost" @click="editCover(c)">✎</button>
              <button class="pbtn danger" @click="delCover(c)">✕</button>
            </view>
            <text class="none" v-if="!covers.length">还没有封面</text>
          </view>
        </template>

        <!-- ============ 4. 食材库 & 大类 ============ -->
        <template v-if="sec === 'ing'">
          <view class="sec-h">
            <text class="sh-t">食材库 & 大类</text>
            <view class="ingu-tabs">
              <text class="ingtab" :class="{ on: ingTab === 'ing' }" @click="ingTab = 'ing'">食材</text>
              <text class="ingtab" :class="{ on: ingTab === 'cat' }" @click="ingTab = 'cat'">大类</text>
            </view>
            <view class="sec-act"><button class="pbtn" @click="openIngAdd">＋ {{ ingTab === 'cat' ? '大类' : '新增' }}</button></view>
          </view>
          <view class="fbar" v-if="ingTab === 'ing'">
            <input class="fsearch" v-model="ingQ" placeholder="按食材名搜索…" />
            <text class="fcount">共 {{ filterIngs.length }} 条</text>
          </view>
          <!-- 食材 Tab -->
          <template v-if="ingTab === 'ing'">
            <view class="grp" v-for="g in ingGroups" :key="g.cat">
              <text class="grp-t">{{ g.cat }}</text>
              <view class="row card" v-for="it in g.items" :key="it.id">
                <text class="inm">{{ it.name }}</text>
                <view class="sp"></view>
                <button class="pbtn ghost" @click="openIngEdit(it)">✎</button>
                <button class="pbtn danger" @click="delIng(it)">✕</button>
              </view>
            </view>
            <text class="none" v-if="!filterIngs.length">食材库为空</text>
          </template>
          <!-- 大类 Tab -->
          <template v-else>
            <view class="row card" v-for="c in cats" :key="c.id">
              <text class="cic">{{ c.icon }}</text>
              <text class="inm">{{ c.name }}</text>
              <view class="sp"></view>
              <button class="pbtn ghost" @click="moveCat(c, 'up')">↑</button>
              <button class="pbtn ghost" @click="moveCat(c, 'down')">↓</button>
              <button class="pbtn ghost" @click="editCat(c)">✎</button>
              <button class="pbtn danger" @click="delCat(c)">✕</button>
            </view>
            <text class="none" v-if="!cats.length">还没有大类</text>
          </template>
        </template>

        <!-- 餐厅（个人收藏）不再纳入管理端：看个人数据去用户端 -->

        <!-- ============ 6. 系统配置 ============ -->
        <template v-if="sec === 'config'">
          <view class="sec-h"><text class="sh-t">系统配置</text><text class="sh-s">配置表驱动，保存后立即生效</text></view>
          <view class="cfg card">
            <view class="cfg-row">
              <text class="cfg-ic">👨‍🍳</text>
              <view class="cfg-c"><text class="cfg-t">厨房技巧审核</text><text class="cfg-s">新增/修改技巧需管理员审核</text></view>
              <switch :checked="audit" @change="setAudit" />
            </view>
            <view class="cfg-row">
              <text class="cfg-ic">⏱</text>
              <view class="cfg-c"><text class="cfg-t">临期阈值（天）</text><text class="cfg-s">在库食材剩余≤该天数视为临期</text></view>
              <input class="num" type="number" :value="String(expiry)" @blur="setExpiry" />
            </view>
            <view class="cfg-row">
              <text class="cfg-ic">🔑</text>
              <view class="cfg-c"><text class="cfg-t">管理员口令</text><text class="cfg-s">登录管理端使用，保存后立即生效</text></view>
              <input class="num w160" :value="passcode" @blur="setPasscode" />
            </view>
          </view>
        </template>
      </view>
    </view>

    <!-- ============ 通用弹窗（自绘 mask；按 modal.mode 切换表单） ============ -->
    <view class="mask" v-if="modal.show" @click="closeModal">
      <view class="dialog" @click.stop>
        <!-- 录入 / 编辑参考菜谱 -->
        <template v-if="modal.mode === 'ref'">
          <text class="d-title">{{ form.id ? '编辑参考菜谱' : '录入参考菜谱' }}</text>
          <input v-model="form.name" placeholder="菜名 *" class="di" />
          <view class="dl-row"><text class="dl-l">Emoji</text><input v-model="form.em" placeholder="🍲" class="di" /></view>
          <view class="dl-row"><text class="dl-l">耗时</text><input v-model.number="form.time" type="number" placeholder="分钟" class="di" /></view>
          <view class="dl-row"><text class="dl-l">难度</text><input v-model="form.diff" placeholder="简单/中等/较难" class="di" /></view>
          <input v-model="form.tagsText" placeholder="口味标签，逗号分隔" class="di" />
          <input v-model="form.ingText" placeholder="所需食材，逗号分隔（如：鸡蛋,番茄）" class="di" />
          <textarea v-model="form.stepsText" placeholder="步骤，每行一步" class="dt" />
          <view class="d-sub">封面点选</view>
          <scroll-view scroll-x class="cover-scroll">
            <view class="cover-row">
              <view class="citem" :class="{ on: form.cover === '' }" @click="form.cover = ''">
                <view class="cover-box" :style="{ background: DEFAULT_GRAD }"><text class="cem">🍽</text></view>
                <text class="cover-nm">默认</text>
              </view>
              <view v-for="c in covers" :key="c.id" class="citem" :class="{ on: form.cover === String(c.id) }" @click="form.cover = String(c.id)">
                <view class="cover-box" :style="{ background: c.grad }"><text class="cem">{{ c.emoji }}</text></view>
                <text class="cover-nm">{{ c.name || c.id }}</text>
              </view>
            </view>
          </scroll-view>
        </template>

        <!-- 封面新增/编辑 -->
        <template v-if="modal.mode === 'cover'">
          <text class="d-title">{{ form.id ? '编辑封面' : '新增封面' }}</text>
          <view class="preview" :style="{ background: form.grad }"><text class="pem">{{ form.emoji || '🍽' }}</text></view>
          <input v-model="form.emoji" placeholder="Emoji，如 🍜" class="di" />
          <input v-model="form.name" placeholder="色调名（可选）" class="di" />
          <view class="d-sub">渐变点选</view>
          <view class="g-grid">
            <view v-for="g in grads" :key="g" class="gcell" :class="{ on: form.grad === g }" :style="{ background: g }" @click="form.grad = g"></view>
          </view>
        </template>

        <!-- 食材 / 大类 -->
        <template v-if="modal.mode === 'cat'">
          <text class="d-title">{{ form.id ? '改大类' : '新增大类' }}</text>
          <input v-model="form.name" placeholder="大类名，如：豆制品" class="di" />
          <view class="d-sub">图标点选</view>
          <view class="icon-grid">
            <view v-for="ic in catIcons" :key="ic" class="icell" :class="{ on: form.icon === ic }" @click="form.icon = ic">{{ ic }}</view>
          </view>
        </template>
        <template v-if="modal.mode === 'ing'">
          <text class="d-title">{{ form.id ? '改食材' : '新增食材' }}</text>
          <input v-model="form.name" placeholder="食材名，如：老抽" class="di" />
          <view class="d-sub">归类到大类</view>
          <view class="chip-row">
            <view v-for="c in cats" :key="c.id" class="chip" :class="{ on: form.cat === c.name }" @click="form.cat = c.name">{{ c.icon }} {{ c.name }}</view>
          </view>
        </template>

        <!-- 用户新增/编辑 -->
        <template v-if="modal.mode === 'user'">
          <text class="d-title">{{ form.id ? '编辑用户' : '新增用户' }}</text>
          <input v-model="form.name" placeholder="用户名 *" class="di" />
          <view class="chip-row">
            <view class="chip" :class="{ on: form.role === 'user' }" @click="form.role = 'user'">🙂 普通用户</view>
            <view class="chip" :class="{ on: form.role === 'admin' }" @click="form.role = 'admin'">👑 管理员</view>
          </view>
        </template>

        <view class="d-btns">
          <button class="pbtn ghost" @click="closeModal">取消</button>
          <button class="pbtn" v-if="['ref','cover','cat','ing','user'].includes(modal.mode)" @click="save">保存</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { tipApi, recipeApi, coverApi, ingredientApi, catApi, configApi, adminApi } from '@/api'

const DEFAULT_GRAD = 'linear-gradient(135deg,#4b3fe3,#8b5cf6)'
const grads = [
  'linear-gradient(135deg,#4b3fe3,#8b5cf6)',
  'linear-gradient(135deg,#ec4899,#f97316)',
  'linear-gradient(135deg,#06b6d4,#3b82f6)',
  'linear-gradient(135deg,#10b981,#a3e635)',
  'linear-gradient(135deg,#8b5cf6,#d946ef)',
  'linear-gradient(135deg,#f59e0b,#ef4444)',
  'linear-gradient(135deg,#f9a825,#ef6c00)',
  'linear-gradient(135deg,#34d399,#22c55e)'
]
const catIcons = ['🥬', '🍎', '🥩', '🦐', '🍄', '🥚', '🍚', '🧂', '🥗', '🌰', '🫘', '🧀']

export default {
  data() {
    return {
      menus: [
        { k: 'stats', ic: '📊', t: '统计' },
        { k: 'users', ic: '👥', t: '用户管理' },
        { k: 'tips', ic: '👨‍🍳', t: '厨房技巧审核' },
        { k: 'ref', ic: '📚', t: '参考菜谱' },
        { k: 'covers', ic: '🖼️', t: '封面图库' },
        { k: 'ing', ic: '🧺', t: '食材库 & 大类' },
        { k: 'config', ic: '⚙️', t: '系统配置' }
      ],
      DEFAULT_GRAD, grads, catIcons,
      sec: 'stats', curName: '', isAdmin: false,
      // 登录
      loginCode: '', passcode: '',
      // 统计（仅公共资源计数）
      stats: { cards: {} },
      // 各列表数据
      tips: [], refs: [], covers: [], ingredients: [], cats: [], users: [],
      audit: true, expiry: 3,
      ingTab: 'ing',
      // 搜索 / 筛选 / 分页
      tipQ: '', tipSt: 'all', tipLimit: 20, tipSts: [
        { k: 'all', t: '全部' }, { k: 'pending', t: '待审核' }, { k: 'approved', t: '已公开' }, { k: 'rejected', t: '未通过' }
      ],
      refQ: '', refLimit: 20,
      ingQ: '',
      modal: { show: false, mode: '', id: null },
      form: {}
    }
  },
  computed: {
    // 统计：公共资源计数卡
    kpis() {
      const c = this.stats.cards || {}
      return [
        { ic: '👥', t: '用户数', k: c.users || 0 },
        { ic: '📚', t: '参考菜谱', k: c.recipes_ref || 0 },
        { ic: '🧺', t: '食材库', k: c.ingredients || 0 },
        { ic: '🗂️', t: '大类', k: c.categories || 0 },
        { ic: '🖼️', t: '封面图库', k: c.covers || 0 },
        { ic: '👨‍🍳', t: '技巧总数', k: c.tips_total || 0 },
        { ic: '⏳', t: '技巧待审', k: c.tips_pending || 0 }
      ]
    },
    // 技巧：状态筛选 + 关键词
    filterTips() {
      const q = this.tipQ.trim().toLowerCase()
      return this.tips.filter((t) => {
        if (this.tipSt !== 'all' && t.status !== this.tipSt) return false
        if (!q) return true
        return String(t.title || '').toLowerCase().includes(q) || String(t.content || '').toLowerCase().includes(q)
      })
    },
    shownTips() { return this.filterTips.slice(0, this.tipLimit) },
    // 参考菜谱：关键词
    filterRefs() {
      const q = this.refQ.trim().toLowerCase()
      return this.refs.filter((r) => !q || String(r.name || '').toLowerCase().includes(q))
    },
    shownRefs() { return this.filterRefs.slice(0, this.refLimit) },
    // 食材：关键词
    filterIngs() {
      const q = this.ingQ.trim().toLowerCase()
      return this.ingredients.filter((x) => !q || String(x.name || '').toLowerCase().includes(q))
    },
    // 食材按大类分组（顺序跟随大类编排）
    ingGroups() {
      const catsOrder = {}
      this.cats.forEach((c) => { catsOrder[c.name] = true })
      const byCat = {}
      this.filterIngs.forEach((it) => { (byCat[it.cat] = byCat[it.cat] || []).push(it) })
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
  onShow() {
    this.curName = uni.getStorageSync('eat_user') || '我'
    this.isAdmin = uni.getStorageSync('eat_admin') === '1'
    if (this.isAdmin) this.loadAll()
  },
  methods: {
    back() { uni.navigateBack() },
    // —— 登录门 ——
    async doLogin() {
      const code = (this.loginCode || '').trim()
      if (!code) return uni.showToast({ title: '请输入口令', icon: 'none' })
      try {
        await adminApi.login(code)
        uni.setStorageSync('eat_admin', '1')
        this.isAdmin = true
        uni.showToast({ title: '登录成功', icon: 'success' })
        this.loadAll()
      } catch (e) {
        uni.showToast({ title: e.message, icon: 'none' })
      }
    },
    async loadAll() {
      if (!this.isAdmin) return
      try {
        const [tips, refs, covers, ingredients, cats, users, st] = await Promise.all([
          tipApi.list(this.curName, true),
          recipeApi.list('admin'),
          coverApi.list(),
          ingredientApi.list(),
          catApi.list(),
          adminApi.users(),
          adminApi.stats()
        ])
        this.tips = tips
        this.refs = refs
        this.covers = covers.map((c) => ({ ...c, grad: c.grad || DEFAULT_GRAD }))
        this.ingredients = ingredients.map((x) => ({ id: x.id, name: x.name, cat: x.cat || '其他' }))
        this.cats = cats.map((c) => ({ id: c.id, name: c.name, icon: c.icon || '🥗' }))
        this.users = users
        this.stats = st || this.stats
        // 配置
        const [a, e, p] = await Promise.all([configApi.get('audit_enabled'), configApi.get('expiry_threshold_days'), configApi.get('admin_passcode')])
        this.audit = (a.value === '1' || a.value === true || a.value === 1)
        this.expiry = Number(e.value)
        this.passcode = p.value
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // —— 用户管理 ——
    openUserAdd() { this.form = { id: null, name: '', role: 'user' }; this.modal = { show: true, mode: 'user', id: null } },
    editUser(u) { this.form = { id: u.id, name: u.name, role: u.role }; this.modal = { show: true, mode: 'user', id: u.id } },
    toggleRole(u) {
      const role = u.role === 'admin' ? 'user' : 'admin'
      if (u.id === 1 && role === 'user') return uni.showToast({ title: '内置管理员不可降级', icon: 'none' })
      adminApi.updateUser(u.id, { role }).then(this.loadAll)
    },
    delUser(u) {
      if (u.id === 1) return uni.showToast({ title: '内置管理员不可删除', icon: 'none' })
      uni.showModal({ title: '删除用户', content: `删除「${u.name}」？`, confirmText: '删除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) adminApi.delUser(u.id).then(this.loadAll) } })
    },
    // —— 技巧审核 ——
    statusText(s) { return { pending: '⏳ 待审核', approved: '✅ 已公开', rejected: '🚫 未通过' }[s] || '' },
    async approve(t) { await tipApi.approve(t.id); this.loadAll() },
    async reject(t) { await tipApi.reject(t.id); this.loadAll() },
    // —— 参考菜谱 编辑/删除 ——
    editRef(r) {
      this.form = {
        id: r.id, name: r.name, em: r.em, time: r.time || 0, diff: r.diff || '简单',
        tagsText: (r.tags || []).join('、'),
        ingText: (r.ing || []).map((i) => i.name || i).join('、'),
        stepsText: (r.steps || []).join('\n'),
        cover: r.cover === undefined || r.cover === null || r.cover === '' ? '' : String(r.cover)
      }
      this.modal = { show: true, mode: 'ref', id: r.id }
    },
    delRef(r) {
      uni.showModal({
        title: '删除参考菜谱', content: `删除「${r.name}」？若已加入「吃这些」会一并移除。`, confirmText: '删除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) recipeApi.del(r.id).then(this.loadAll) }
      })
    },
    // —— 封面 ——
    moveCover(c, dir) { coverApi.move(c.id, dir).then(this.loadAll) },
    editCover(c) { this.form = { id: c.id, emoji: c.emoji, name: c.name || '', grad: c.grad || DEFAULT_GRAD }; this.modal = { show: true, mode: 'cover', id: c.id } },
    delCover(c) {
      uni.showModal({ title: '删除封面', content: `删除「${c.name || c.emoji}」？用它的菜谱会回到默认封面色。`, confirmText: '删除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) coverApi.del(c.id).then(this.loadAll) } })
    },
    // —— 食材 / 大类 ——
    openIngAdd() {
      if (this.ingTab === 'cat') this.form = { id: null, name: '', icon: '🥗' }
      else this.form = { id: null, name: '', cat: (this.cats[0] && this.cats[0].name) || '其他', icon: '🥗' }
      this.modal = { show: true, mode: this.ingTab === 'cat' ? 'cat' : 'ing', id: null }
    },
    editCat(c) { this.form = { id: c.id, name: c.name, icon: c.icon }; this.modal = { show: true, mode: 'cat', id: c.id } },
    moveCat(c, dir) { catApi.move(c.id, dir).then(this.loadAll) },
    delCat(c) {
      uni.showModal({ title: '删除大类', content: `删除「${c.name}」？该大类下食材/冰箱项退回「其他」。`, confirmText: '删除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) catApi.del(c.id).then(this.loadAll) } })
    },
    openIngEdit(it) { this.form = { id: it.id, name: it.name, cat: it.cat }; this.modal = { show: true, mode: 'ing', id: it.id } },
    delIng(it) {
      uni.showModal({ title: '移除食材', content: `从食材库移除「${it.name}」？不影响已用的菜谱/库存。`, confirmText: '移除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) ingredientApi.del(it.id).then(this.loadAll) } })
    },
    // —— 配置 ——
    setAudit(e) { this.audit = e.detail.value; configApi.set('audit_enabled', this.audit ? '1' : '0') },
    setExpiry(e) {
      const v = Number(e.detail.value)
      if (!isNaN(v) && v > 0) { this.expiry = v; configApi.set('expiry_threshold_days', String(v)) }
    },
    setPasscode(e) {
      const v = (e.detail.value || '').trim()
      if (!v) return
      this.passcode = v
      configApi.set('admin_passcode', v)
    },
    // —— 弹窗 ——
    openModal(mode) {
      if (mode === 'cover') { this.form = { id: null, emoji: '🍽', name: '', grad: DEFAULT_GRAD } }
      else if (mode === 'ref') { this.form = { id: null, name: '', em: '🍲', time: 20, diff: '简单', tagsText: '', ingText: '', stepsText: '', cover: '' } }
      this.modal = { show: true, mode, id: null }
    },
    closeModal() { this.modal = { show: false, mode: '', id: null } },
    save() {
      const mode = this.modal.mode
      if (mode === 'cover') {
        const emoji = (this.form.emoji || '').trim()
        if (!emoji) return uni.showToast({ title: '请填 Emoji', icon: 'none' })
        const body = { emoji, name: (this.form.name || '').trim(), grad: this.form.grad || DEFAULT_GRAD }
        const p = this.form.id ? coverApi.update(this.form.id, body) : coverApi.create(body)
        return p.then(() => { this.closeModal(); this.loadAll() }).catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
      }
      if (mode === 'cat') {
        const name = (this.form.name || '').trim()
        if (!name) return uni.showToast({ title: '名称不能为空', icon: 'none' })
        const p = this.form.id ? catApi.update(this.form.id, { name, icon: this.form.icon }) : catApi.create({ name, icon: this.form.icon })
        return p.then(() => { this.closeModal(); this.loadAll() }).catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
      }
      if (mode === 'ing') {
        const name = (this.form.name || '').trim()
        if (!name) return uni.showToast({ title: '名称不能为空', icon: 'none' })
        const p = this.form.id ? ingredientApi.update(this.form.id, { name, cat: this.form.cat }) : ingredientApi.create({ name, cat: this.form.cat })
        return p.then(() => { this.closeModal(); this.loadAll() }).catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
      }
      if (mode === 'user') {
        const name = (this.form.name || '').trim()
        if (!name) return uni.showToast({ title: '请填用户名', icon: 'none' })
        if (this.form.id === 1 && this.form.role !== 'admin') return uni.showToast({ title: '内置管理员不可降级', icon: 'none' })
        const data = { name, role: this.form.role || 'user' }
        const p = this.form.id ? adminApi.updateUser(this.form.id, data) : adminApi.createUser(data)
        return p.then(() => { this.closeModal(); this.loadAll() }).catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
      }
      if (mode === 'ref') {
        return this.saveRef()
      }
    },
    // 参考菜谱：录入 或 编辑（复用同一表单；有 id 走 update）
    saveRef() {
      const name = (this.form.name || '').trim()
      if (!name) return uni.showToast({ title: '请填菜名', icon: 'none' })
      const picked = this.covers.find((c) => String(c.id) === String(this.form.cover))
      const data = {
        source: 'admin',
        name, em: picked ? picked.emoji : (this.form.em || '🍲'),
        cover: picked ? String(picked.id) : '',
        time: this.form.time || 20, diff: this.form.diff || '简单',
        tags: (this.form.tagsText || '').split(/[，,、\s]+/).filter(Boolean),
        ing: (this.form.ingText || '').split(/[，,、]+/).map((x) => x.trim()).filter(Boolean).map((n) => ({ name: n, qty: 1, unit: '份' })),
        steps: (this.form.stepsText || '').split('\n').map((x) => x.trim()).filter(Boolean)
      }
      const p = this.form.id ? recipeApi.update(this.form.id, data) : recipeApi.create(data)
      return p.then(() => { this.closeModal(); this.loadAll() }).catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
    }
  }
}
</script>

<style lang="scss" scoped>
/* 桌面管理端：整体用 px 布局（非 rpx），宽度自适应居中留白 */
.admin { min-height: 100vh; background: #f3f4f7; display: flex; flex-direction: column; }
.ahead { display: flex; align-items: center; justify-content: space-between; padding: 16px 28px; background: #4b3fe3; color: #fff; }
.ah-l { font-size: 18px; font-weight: 700; }
.ah-r { display: flex; align-items: center; gap: 12px; }
.ah-user { font-size: 14px; opacity: .9; }
.ah-role { font-size: 12px; background: #ffd166; color: #4b3fe3; padding: 2px 10px; border-radius: 999px; }
.ah-role.off { background: #fff2f2; color: #e64340; }
.ah-back { font-size: 14px; cursor: pointer; padding: 6px 12px; border: 1px solid rgba(255,255,255,.6); border-radius: 8px; }

/* 登录门 */
.gate { margin: 60px auto; padding: 40px; background: #fff; border: 1px solid #e5e6eb; border-radius: 16px; text-align: center; max-width: 440px; }
.gate-ic { font-size: 44px; display: block; }
.gate-t { display: block; color: #555; font-size: 15px; margin: 12px 0 20px; }
.gate-in { border: 1px solid #d8dae0; border-radius: 10px; height: 46px; line-height: 46px; font-size: 18px; letter-spacing: 4px; width: 100%; box-sizing: border-box; }
.gate-act { margin-top: 24px; }
.gate-hint { display: block; color: #aaa; font-size: 12px; margin-top: 14px; }

.abody { flex: 1; display: flex; min-height: 0; }
.asider { width: 200px; flex-shrink: 0; background: #fff; border-right: 1px solid #e5e6eb; padding: 12px 0; }
.nav { display: flex; align-items: center; gap: 12px; padding: 14px 22px; cursor: pointer; color: #444; font-size: 14px; }
.nav:hover { background: #f6f5ff; }
.nav.on { background: #4b3fe3; color: #fff; }
.nav-ic { font-size: 18px; }
.acont { flex: 1; min-width: 0; overflow: auto; padding: 24px 32px; box-sizing: border-box; }

.sec-h { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.sh-t { font-size: 20px; font-weight: 700; }
.sh-s { font-size: 12px; color: #999; }
.sec-act { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.sh-note { font-size: 12px; color: #b8860b; }
.ingu-tabs { display: flex; background: #fff; border: 1px solid #e5e6eb; border-radius: 8px; overflow: hidden; }
.ingtab { padding: 6px 18px; font-size: 13px; cursor: pointer; color: #666; }
.ingtab.on { background: #4b3fe3; color: #fff; }

.card { background: #fff; border: 1px solid #e5e6eb; border-radius: 12px; }
.row { display: flex; align-items: center; gap: 12px; padding: 12px 16px; margin-bottom: 10px; }
.none { display: block; color: #aaa; text-align: center; padding: 40px 0; font-size: 13px; }
.sp { flex: 1; }

/* 搜索 / 筛选 工具栏 */
.fbar { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.fsearch { background: #fff; border: 1px solid #e5e6eb; border-radius: 8px; height: 36px; line-height: 36px; padding: 0 12px; font-size: 13px; width: 240px; box-sizing: border-box; }
.fcount { font-size: 12px; color: #999; }
.seg { display: flex; background: #fff; border: 1px solid #e5e6eb; border-radius: 8px; overflow: hidden; }
.sell { padding: 6px 16px; font-size: 13px; cursor: pointer; color: #666; }
.sell.on { background: #4b3fe3; color: #fff; }
.more { display: block; margin: 16px auto 0; }

/* 通用按钮 */
.pbtn { border: none; background: #4b3fe3; color: #fff; font-size: 13px; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
.pbtn.ghost { background: #fff; color: #4b3fe3; border: 1px solid #4b3fe3; }
.pbtn.danger { background: #fff; color: #e64340; border: 1px solid #e64340; }
.pbtn.ok { background: #07c160; }

/* 统计（公共资源卡片） */
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.kpi { display: flex; align-items: center; gap: 14px; padding: 18px 20px; }
.kpi-ic { font-size: 30px; }
.kpi-num { font-size: 28px; font-weight: 800; color: #4b3fe3; }
.kpi-t { font-size: 13px; color: #666; }

/* users */
.uico { font-size: 24px; }
.uc { display: flex; flex-direction: column; }
.dis { opacity: .35; pointer-events: none; }

/* tips */
.trow { padding: 14px 18px; margin-bottom: 12px; }
.trow-head { display: flex; align-items: center; gap: 12px; }
.tt { font-size: 15px; font-weight: 700; }
.tst { font-size: 12px; padding: 2px 10px; border-radius: 999px; }
.tst.pending { color: #b45309; background: #fff4e0; }
.tst.approved { color: #0f766e; background: #e6f9ef; }
.tst.rejected { color: #e64340; background: #fdecec; }
.tct { display: block; color: #666; font-size: 13px; margin: 8px 0; }
.tmeta { display: flex; gap: 16px; font-size: 12px; color: #999; }
.tusr { color: #4b3fe3; }
.tops { display: flex; gap: 12px; margin-top: 12px; }

/* ref recipes */
.grid { display: flex; flex-wrap: wrap; gap: 16px; }
.rcard { width: 200px; background: #fff; border: 1px solid #e5e6eb; border-radius: 12px; padding: 14px; }
.rcover { height: 90px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.rem { font-size: 40px; }
.rinfo { margin-top: 10px; }
.rn { font-size: 14px; font-weight: 700; display: block; }
.rm { font-size: 12px; color: #888; }
.raction { display: flex; gap: 10px; margin-top: 12px; }
.raction .pbtn { flex: 1; }

/* covers */
.clist .crow { display: flex; align-items: center; gap: 14px; padding: 12px 16px; margin-bottom: 10px; }
.cbox { width: 56px; height: 56px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.cem { font-size: 28px; }
.cn { font-size: 14px; flex: 1; }

/* ingredients */
.cic { font-size: 20px; }
.inm { font-size: 14px; }
.grp { margin-bottom: 16px; }
.grp-t { display: block; font-size: 12px; color: #888; margin-bottom: 8px; }
/* 通用 名称/描述 双行（用户行复用） */
.sn { font-size: 14px; font-weight: 700; }
.sm { font-size: 12px; color: #888; }
/* config */
.cfg { padding: 8px 20px; max-width: 560px; }
.cfg-row { display: flex; align-items: center; gap: 16px; padding: 20px 0; border-bottom: 1px solid #f0f0f2; }
.cfg-row:last-child { border-bottom: none; }
.cfg-ic { font-size: 26px; }
.cfg-c { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.cfg-t { font-size: 14px; font-weight: 600; }
.cfg-s { font-size: 12px; color: #888; }
.num { border: 1px solid #e5e6eb; border-radius: 8px; height: 34px; width: 96px; text-align: right; padding: 0 10px; box-sizing: border-box; font-size: 13px; }
.w160 { width: 160px; text-align: left; letter-spacing: 2px; }

/* 弹窗 */
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 999; display: flex; align-items: center; justify-content: center; padding: 24px; }
.dialog { width: 100%; max-width: 460px; background: #fff; border-radius: 14px; padding: 24px; max-height: 88vh; overflow: auto; }
.d-title { font-size: 17px; font-weight: 700; display: block; margin-bottom: 16px; text-align: center; }
.di { background: #f6f6f8; border: 1px solid #e5e6eb; border-radius: 8px; height: 40px; line-height: 40px; padding: 0 12px; margin-bottom: 12px; font-size: 13px; width: 100%; box-sizing: border-box; }
.dt { background: #f6f6f8; border: 1px solid #e5e6eb; border-radius: 8px; padding: 10px 12px; font-size: 13px; width: 100%; box-sizing: border-box; height: 90px; margin-bottom: 12px; }
.dl-row { display: flex; align-items: center; gap: 10px; }
.dl-l { width: 52px; font-size: 13px; color: #666; flex-shrink: 0; }
.d-sub { font-size: 12px; color: #888; margin: 6px 0 10px; }
.d-btns { display: flex; gap: 12px; justify-content: flex-end; margin-top: 12px; }
.preview { height: 120px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-bottom: 14px; }
.pem { font-size: 60px; }
.g-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.gcell { aspect-ratio: 1; border-radius: 8px; border: 3px solid transparent; box-sizing: border-box; cursor: pointer; }
.gcell.on { border-color: #4b3fe3; }
.icon-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
.icell { aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-size: 26px; background: #f6f6f8; border-radius: 8px; border: 2px solid transparent; cursor: pointer; }
.icell.on { border-color: #4b3fe3; background: #efeaff; }
.chip-row { display: flex; flex-wrap: wrap; gap: 10px; }
.chip { font-size: 13px; color: #666; background: #f6f6f8; border: 1px solid #e5e6eb; border-radius: 999px; padding: 8px 14px; cursor: pointer; }
.chip.on { background: #4b3fe3; color: #fff; border-color: #4b3fe3; }
.cover-scroll { display: flex; }
.cover-row { display: flex; gap: 12px; }
.citem { display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer; }
.cover-box { width: 52px; height: 52px; border-radius: 8px; display: flex; align-items: center; justify-content: center; border: 3px solid transparent; box-sizing: border-box; }
.citem.on .cover-box { border-color: #4b3fe3; }
.cover-nm { font-size: 11px; color: #888; }
</style>