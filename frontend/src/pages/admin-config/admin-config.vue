<!-- admin-config.vue —— 吃啥 · 系统配置（独立页，仅 H5/PC）
  从 admin.vue 的系统配置区整体拆出：系统级参数不再和业务数据（用户/技巧/菜谱/食材/餐厅）混在一起。
  入口：管理端左侧菜单「系统配置」。
  写入方式：input 用 v-model 绑本地 state，blur 时按 key 落库（configs 表），避免 :value + $event.target.value 取不到值的问题。
-->
<template>
  <view class="cpage">
    <view class="cheader">
      <text class="back" @tap="back">‹</text>
      <text class="ctitle">系统配置</text>
      <text class="csub">配置表驱动 · 修改即生效</text>
    </view>

    <scroll-view class="cscroll" scroll-y>
      <view class="wrap">

        <!-- ============ 1. 基础配置 ============ -->
        <view class="gsec">
          <text class="g-h">基础配置</text>
          <view class="card">
            <view class="row">
              <view class="rc"><text class="rt">厨房技巧审核</text><text class="rs">新增/修改技巧需管理员审核</text></view>
              <switch :checked="audit" @change="onAudit" />
            </view>
            <view class="row">
              <view class="rc"><text class="rt">临期阈值（天）</text><text class="rs">在库食材剩余 ≤ 该天数视为临期</text></view>
              <input class="num w120" type="number" v-model="expiry" @blur="saveNum('expiry_threshold_days', expiry)" />
            </view>
            <view class="row">
              <view class="rc"><text class="rt">管理员口令</text><text class="rs">登录管理端使用，保存后立即生效</text></view>
              <input class="num w200" v-model="passcode" @blur="save('admin_passcode', passcode)" />
            </view>
          </view>
        </view>

        <!-- ============ 2. 图标池 ============ -->
        <view class="gsec">
          <text class="g-h">图标池</text>
          <text class="g-s">逗号分隔 emoji；录入表单的候选图标从这里取</text>
          <view class="card">
            <view class="col">
              <text class="rt">食材图标池</text>
              <textarea class="pool" v-model="ingPool" @blur="savePool('ingredient_icon_pool', 'ingPool', 'ingIcons')" />
              <view class="prev"><text v-for="ic in ingIcons" :key="ic" class="p-ic">{{ ic }}</text></view>
            </view>
            <view class="col">
              <text class="rt">大类图标池</text>
              <textarea class="pool" v-model="catPool" @blur="savePool('cat_icon_pool', 'catPool', 'catIcons')" />
              <view class="prev"><text v-for="ic in catIcons" :key="ic" class="p-ic">{{ ic }}</text></view>
            </view>
            <view class="col">
              <text class="rt">菜谱图标池</text>
              <textarea class="pool" v-model="recipePool" @blur="savePool('recipe_emoji_pool', 'recipePool', 'recipeIcons')" />
              <view class="prev"><text v-for="ic in recipeIcons" :key="ic" class="p-ic">{{ ic }}</text></view>
            </view>
            <view class="col">
              <text class="rt">餐厅图标池</text>
              <textarea class="pool" v-model="shopPool" @blur="savePool('shop_icon_pool', 'shopPool', 'shopIcons')" />
              <view class="prev"><text v-for="ic in shopIcons" :key="ic" class="p-ic">{{ ic }}</text></view>
            </view>
            <view class="col last">
              <text class="rt">封面渐变池</text>
              <text class="rs">| 分隔 linear-gradient；菜谱封面预设</text>
              <textarea class="pool grad" v-model="gradPool" @blur="save('cover_grad_pool', gradPool)" />
              <view class="prev"><view v-for="(g,i) in gradList" :key="i" class="p-grad" :style="{ background: g }"></view></view>
            </view>
          </view>
        </view>

        <!-- ============ 3. 邮件服务（SMTP） ============ -->
        <view class="gsec">
          <text class="g-h">邮件服务 · SMTP</text>
          <text class="g-s">用于发送邮箱验证码（登录 / 绑定 / 注销）。QQ 邮箱填「设置 → 账户 → 开启 SMTP 服务」生成的那串授权码，不是登录密码。</text>
          <view class="card">
            <view class="row">
              <view class="rc"><text class="rt">服务器 Host</text><text class="rs">QQ 邮箱：smtp.qq.com</text></view>
              <input class="num w220" v-model="smtpHost" @blur="save('smtp_host', smtpHost)" placeholder="smtp.qq.com" />
            </view>
            <view class="row">
              <view class="rc"><text class="rt">端口 Port</text><text class="rs">465 = SSL，587 = STARTTLS</text></view>
              <input class="num w120" type="number" v-model="smtpPort" @blur="save('smtp_port', smtpPort)" placeholder="465" />
            </view>
            <view class="row">
              <view class="rc"><text class="rt">发件邮箱 User</text><text class="rs">完整邮箱地址</text></view>
              <input class="num w260" v-model="smtpUser" @blur="save('smtp_user', smtpUser)" placeholder="your_mail@qq.com" />
            </view>
            <view class="row">
              <view class="rc"><text class="rt">授权码 Pass</text><text class="rs">邮箱设置里生成的授权码（非登录密码）</text></view>
              <input class="num w260" type="password" v-model="smtpPass" @blur="save('smtp_pass', smtpPass)" placeholder="16 位授权码" />
            </view>
            <view class="row">
              <view class="rc"><text class="rt">发件人名称 From</text><text class="rs">收件人看到的发件人名</text></view>
              <input class="num w220" v-model="smtpFrom" @blur="save('smtp_from', smtpFrom)" placeholder="吃啥好呀" />
            </view>
            <view class="row">
              <view class="rc"><text class="rt">验证码有效期（分钟）</text><text class="rs">超时需重新获取</text></view>
              <input class="num w120" type="number" v-model="otpExpire" @blur="saveNum('otp_expire_min', otpExpire)" />
            </view>
            <view class="row">
              <view class="rc"><text class="rt">当前状态</text><text class="rs">{{ smtpReady ? '已配置，验证码会真实发信' : '未配置完整（缺 Host / User / Pass），验证码降级为后端日志打印' }}</text></view>
              <text class="badge" :class="{ on: smtpReady }">{{ smtpReady ? '已启用' : '未启用' }}</text>
            </view>
          </view>
        </view>

        <!-- ============ 4. 登录与安全 ============ -->
        <view class="gsec">
          <text class="g-h">登录与安全</text>
          <view class="card">
            <view class="col">
              <text class="rt">JWT 签名密钥</text>
              <text class="rs">用于签发登录 token，上线务必改成随机长串；改动后已发 token 全部失效</text>
              <input class="num full" v-model="jwtSecret" @blur="save('jwt_secret', jwtSecret)" placeholder="随机长字符串" />
            </view>
            <view class="col">
              <text class="rt">微信小程序 AppID</text>
              <text class="rs">填好后小程序登录走真实 openid（不再 mock）</text>
              <input class="num full" v-model="mpAppid" @blur="save('mp_appid', mpAppid)" placeholder="wx1234567890abcdef" />
            </view>
            <view class="col last">
              <text class="rt">微信小程序 AppSecret</text>
              <text class="rs">微信公众平台「开发 → 开发管理」里获取</text>
              <input class="num full" type="password" v-model="mpSecret" @blur="save('mp_secret', mpSecret)" placeholder="AppSecret" />
            </view>
          </view>
        </view>

        <view class="tail">修改输入框后失焦（点别处）即自动保存</view>
        <view class="pad"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { configApi } from '@/api'

export default {
  data() {
    return {
      audit: true, expiry: '3', passcode: '',
      ingPool: '', ingIcons: [],
      catPool: '', catIcons: [],
      recipePool: '', recipeIcons: [],
      shopPool: '', shopIcons: [],
      gradPool: '',
      smtpHost: '', smtpPort: '465', smtpUser: '', smtpPass: '', smtpFrom: '', otpExpire: '10',
      jwtSecret: '', mpAppid: '', mpSecret: '',
    }
  },
  computed: {
    gradList() {
      return (this.gradPool || '').split('|').map((s) => s.trim()).filter(Boolean)
    },
    smtpReady() {
      return !!(this.smtpHost && this.smtpUser && this.smtpPass)
    },
  },
  onLoad() { this.load() },
  methods: {
    back() { uni.navigateBack() },

    splitIcons(v) {
      return (v || '').split(/[,，]/).map((s) => s.trim()).filter(Boolean)
    },

    async load() {
      try {
        const keys = [
          'audit_enabled', 'expiry_threshold_days', 'admin_passcode',
          'ingredient_icon_pool', 'cat_icon_pool', 'recipe_emoji_pool', 'shop_icon_pool', 'cover_grad_pool',
          'smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_from', 'otp_expire_min',
          'jwt_secret', 'mp_appid', 'mp_secret',
        ]
        const res = await Promise.all(keys.map((k) => configApi.get(k).catch(() => ({ value: '' }))))
        const v = {}
        keys.forEach((k, i) => { v[k] = (res[i] && res[i].value != null) ? String(res[i].value) : '' })

        this.audit = v.audit_enabled === '1' || v.audit_enabled === 'true'
        this.expiry = v.expiry_threshold_days || '3'
        this.passcode = v.admin_passcode
        this.ingPool = v.ingredient_icon_pool; this.ingIcons = this.splitIcons(this.ingPool)
        this.catPool = v.cat_icon_pool; this.catIcons = this.splitIcons(this.catPool)
        this.recipePool = v.recipe_emoji_pool; this.recipeIcons = this.splitIcons(this.recipePool)
        this.shopPool = v.shop_icon_pool; this.shopIcons = this.splitIcons(this.shopPool)
        this.gradPool = v.cover_grad_pool
        this.smtpHost = v.smtp_host
        this.smtpPort = v.smtp_port || '465'
        this.smtpUser = v.smtp_user
        this.smtpPass = v.smtp_pass
        this.smtpFrom = v.smtp_from
        this.otpExpire = v.otp_expire_min || '10'
        this.jwtSecret = v.jwt_secret
        this.mpAppid = v.mp_appid
        this.mpSecret = v.mp_secret
      } catch (e) {
        uni.showToast({ title: e.message || '加载失败', icon: 'none' })
      }
    },

    // 通用保存：key 落库，成功给一次轻提示
    async save(key, val) {
      try {
        await configApi.set(key, String(val == null ? '' : val).trim())
        uni.showToast({ title: '已保存', icon: 'none', duration: 700 })
      } catch (e) {
        uni.showToast({ title: e.message || '保存失败', icon: 'none' })
      }
    },
    saveNum(key, val) {
      const n = Number(val)
      if (!Number.isFinite(n) || n <= 0) return uni.showToast({ title: '请输入正整数', icon: 'none' })
      this.save(key, String(n))
    },
    onAudit(e) {
      this.audit = e.detail.value
      configApi.set('audit_enabled', this.audit ? '1' : '0')
        .then(() => uni.showToast({ title: '已保存', icon: 'none', duration: 700 }))
        .catch((err) => uni.showToast({ title: err.message || '保存失败', icon: 'none' }))
    },
    // 图标池：保存后同步刷新预览数组
    savePool(key, poolField, iconsField) {
      const raw = (this[poolField] || '').trim()
      this[iconsField] = this.splitIcons(raw)
      this.save(key, raw)
    },
  },
}
</script>

<style lang="scss" scoped>
.cpage { display:flex; flex-direction:column; height:100vh; background:var(--bg); }
.cheader { display:flex; align-items:baseline; gap:16rpx; padding:calc(env(safe-area-inset-top) + 20rpx) var(--nav-safe-right) 20rpx 24rpx; }
.back { font-size:48rpx; font-weight:600; }
.ctitle { font-size:40rpx; font-weight:700; }
.csub { font-size:24rpx; color:var(--text-2); }
.cscroll { flex:1; min-height:0; }

.wrap { padding:0 24rpx; max-width:1100px; margin:0 auto; }
.gsec { margin-bottom:28rpx; }
.g-h { font-size:30rpx; font-weight:700; display:block; }
.g-s { font-size:22rpx; color:var(--text-2); display:block; margin:6rpx 0 12rpx; line-height:1.6; }
.card { background:var(--card); border:1rpx solid var(--border); border-radius:16rpx; padding:8rpx 20rpx; }

.row { display:flex; align-items:center; gap:20rpx; padding:18rpx 0; }
.row + .row { border-top:1rpx solid var(--border); }
.rc { flex:1; min-width:0; display:flex; flex-direction:column; gap:4rpx; }
.rt { font-size:26rpx; font-weight:600; }
.rs { font-size:22rpx; color:var(--text-2); line-height:1.5; }

.col { padding:18rpx 0; display:flex; flex-direction:column; gap:8rpx; }
.col + .col { border-top:1rpx solid var(--border); }
.col.last { padding-bottom:22rpx; }

.num { background:var(--bg); border:1rpx solid var(--border); border-radius:10rpx; height:70rpx; line-height:70rpx; padding:0 16rpx; font-size:26rpx; color:var(--text); box-sizing:border-box; flex:none; }
.num.full { width:100%; flex:1 1 auto; }
.w120 { width:120px; } .w220 { width:220px; } .w260 { width:260px; }

.pool { background:var(--bg); border:1rpx solid var(--border); border-radius:10rpx; width:100%; box-sizing:border-box; min-height:110rpx; padding:12rpx 16rpx; font-size:24rpx; color:var(--text); }
.pool.grad { min-height:150rpx; }
.prev { display:flex; flex-wrap:wrap; gap:8rpx; margin-top:6rpx; }
.p-ic { background:var(--bg); border-radius:8rpx; padding:4rpx 10rpx; font-size:26rpx; }
.p-grad { width:56rpx; height:34rpx; border-radius:8rpx; }

.badge { font-size:22rpx; padding:6rpx 16rpx; border-radius:999rpx; background:#fdecea; color:#c0392b; flex:none; }
.badge.on { background:#e8f8ef; color:#0a8f4d; }

.tail { text-align:center; font-size:22rpx; color:var(--text-2); padding:8rpx 0 20rpx; }
.pad { height:40rpx; }
</style>
