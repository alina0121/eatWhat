<!-- admin.vue —— 吃啥 · PC 管理端（桌面宽屏：左侧菜单 + 右侧内容区）
  复用现有移动端同一套 API（tipApi/recipeApi/coverApi/ingredientApi/catApi/configApi），
  并新增 adminApi（密码登录 + 统计聚合）。入口在「我的」页仅 PC 宽屏显示，移动端不可见。
  登录口令在配置表 admin_passcode（默认 123456），仅门控管理台，不影响移动端。
-->
<template>
  <view class="admin">
    <!-- 顶部 header -->
    <view class="ahead main" v-if="isAdmin">
      <text class="ah-l">🍜 管理</text>
      <!-- 导航 tab 栏（嵌入 header 内） -->
      <view class="asider">
        <view class="nav" v-for="m in menus" :key="m.k" :class="{ on: sec === m.k }" @tap="onNav(m)">
          <text class="nav-ic">{{ m.ic }}</text>
          <text class="nav-t">{{ m.t }}</text>
        </view>
      </view>
      <view class="ah-r">
        <text class="ah-user">{{ curName }}</text>
        <view class="ah-role" :class="{ off: !isAdmin }">{{ isAdmin ? '管理员' : '未登录' }}</view>
      </view>
    </view>
    <view class="ahead" v-else>
      <text class="ah-l">🍜 管理</text>
    </view>

    <!-- 登录门：密码登录（默认口令 123456，存配置表，改库可换） -->
    <view class="gate" v-if="!isAdmin">
      <text class="gate-ic">🔒</text>
      <text class="gate-t">管理端功能需输入管理员口令</text>
      <input class="gate-in" v-model="loginCode" password placeholder="请输入口令" style="text-align:center" />
      <view class="gate-act">
        <view class="pbtn" @tap="doLogin">登 录</view>
      </view>
      <text class="gate-hint">提示：默认口令 123456（后台配置 admin_passcode）</text>
    </view>

    <view class="abody" v-if="isAdmin">
      <!-- 内容区 -->
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
            <view class="sec-act"><view class="pbtn" @tap="openUserAdd">＋ 新增用户</view></view>
          </view>
          <view class="row card" v-for="u in users" :key="u.id">
            <view class="uico">{{ u.role === 'admin' ? '👑' : '🙂' }}</view>
            <!-- 展示名以后端 nickname 为准（老数据可能只在 name 里）；邮箱一并显示，方便管理和核对账号 -->
            <view class="uc">
              <text class="sn">{{ u.nickname || u.name || ('用户' + u.id) }}</text>
              <text class="sm">{{ (u.role === 'admin' ? '管理员' : '普通用户') + (u.email ? ' · ' + u.email : ' · 未绑定邮箱') }}</text>
            </view>
            <view class="sp"></view>
            <!-- 置灰规则：id=1（内置 admin）所有操作禁；自己这条行全禁（不管当前 role 是什么，自己不能升/降/删自己） -->
            <view class="pbtn ghost" @tap="toggleRole(u)"
                    :class="{ dis: u.id === 1 || u.id === curAdminId }"
                    >
              {{ u.role === 'admin' ? '设为普通' : '设为管理' }}
            </view>
            <view class="pbtn ghost" @tap="editUser(u)" :class="{ dis: u.id === 1 }" >✎</view>
            <view class="pbtn danger" @tap="delUser(u)"
                    :class="{ dis: u.id === 1 || u.id === curAdminId }"
                    >✕</view>
          </view>
          <text class="none" v-if="!users.length">还没有用户</text>
        </template>

        <!-- ============ 1.5 会员管理 ============ -->
        <template v-if="sec === 'vip'">
          <view class="sec-h">
            <text class="sh-t">会员管理</text>
            <view class="sec-act"><view class="pbtn ghost" @tap="loadVip">↻ 刷新</view></view>
          </view>
          <view class="kpis" v-if="vipData">
            <view class="kpi card" v-for="k in vipKpis" :key="k.t">
              <text class="kpi-ic">{{ k.ic }}</text>
              <text class="kpi-num">{{ k.v }}</text>
              <text class="kpi-t">{{ k.t }}</text>
            </view>
          </view>

          <!-- 会员列表（含过期） -->
          <text class="sh-t block" style="margin-top:24rpx">会员（{{ vipMembers.length }}）</text>
          <view class="row card" v-for="m in vipMembers" :key="m.id">
            <view class="uico">{{ m.expires_at > nowSec ? '👑' : '⏳' }}</view>
            <view class="uc">
              <text class="sn">{{ m.nickname || m.name || ('用户' + m.id) }}</text>
              <text class="sm">{{ m.email || '未绑定邮箱' }} · {{ m.expires_at > nowSec ? '生效中' : '已过期' }} · 至 {{ fmtTs(m.expires_at) }}</text>
            </view>
            <view class="sp"></view>
            <view class="pbtn ghost" @tap="grantVip(m)">＋赠送</view>
            <view class="pbtn danger" v-if="m.expires_at > nowSec" @tap="revokeVip(m)">✕取消</view>
          </view>
          <text class="none" v-if="vipData && !vipMembers.length">还没有会员（订单支付后自动生成，也可在下方手工赠送）</text>

          <!-- 订单流水 -->
          <text class="sh-t block" style="margin-top:24rpx">订单流水（最近 100 笔）</text>
          <view class="row card" v-for="o in (vipData ? vipData.orders : [])" :key="o.out_trade_no">
            <view class="uico">{{ o.status === 'paid' ? '✅' : (o.status === 'refunded' ? '↩️' : '⌛') }}</view>
            <view class="uc">
              <text class="sn">{{ (o.nickname || ('用户' + o.user_id)) + ' · ' + planName(o.plan_id) + ' ¥' + fen2yuan(o.price_fen) }}</text>
              <text class="sm">{{ o.out_trade_no }} · {{ o.env === 1 ? 'iOS' : '安卓/其他' }} · {{ o.paid_at ? fmtTs(o.paid_at) : '未支付' }}</text>
            </view>
            <view class="sp"></view>
            <text class="sm">{{ o.status }}</text>
          </view>
          <text class="none" v-if="vipData && !vipData.orders.length">暂无订单</text>
        </template>

        <!-- ============ 1. 厨房技巧审核 ============ -->
        <template v-if="sec === 'tips'">
          <view class="sec-h"><text class="sh-t">厨房技巧审核</text><text class="sh-s">对待审核内容「通过 / 退回」</text></view>
          <view class="fbar">
            <input class="fsearch" v-model="tipQ" placeholder="搜索标题 / 内容…" />
            <view class="seg">
              <text v-for="s in tipSts" :key="s.k" class="sell" :class="{ on: tipSt === s.k }" @tap="tipSt = s.k">{{ s.t }}</text>
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
                <view class="pbtn ok" @tap="approve(t)">✓ 通过</view>
                <view class="pbtn danger" @tap="reject(t)">✕ 退回</view>
              </view>
            </view>
            <text class="none" v-if="!filterTips.length">暂无可审核的技巧</text>
            <view class="pbtn ghost more" v-if="filterTips.length > shownTips.length" @tap="tipLimit += 20">加载更多（{{ shownTips.length }}/{{ filterTips.length }}）</view>
          </view>
        </template>

        <!-- ============ 2. 参考菜谱 ============ -->
        <template v-if="sec === 'ref'">
          <view class="sec-h">
            <text class="sh-t">参考菜谱</text>
            <view class="sec-act">
              <text class="sh-note">可录入 / 编辑 / 删除</text>
              <view class="pbtn" @tap="openModal('ref')">＋ 录入</view>
            </view>
          </view>
          <view class="fbar">
            <input class="fsearch" v-model="refQ" placeholder="按菜名搜索…" />
            <text class="fcount">共 {{ filterRefs.length }} 条</text>
          </view>
          <view class="grid">
            <view class="rcard" v-for="r in shownRefs" :key="r.id">
              <view class="rcover" :style="{ background: r.coverGrad || '' }"><text class="rem">{{ r.em }}</text></view>
              <view class="rinfo"><text class="rn">{{ r.name }}</text><text class="rm">{{ r.time }}分钟 · {{ r.diff }}</text></view>
              <view class="raction">
                <view class="pbtn ghost" @tap="editRef(r)">✎ 编辑</view>
                <view class="pbtn danger" @tap="delRef(r)">✕ 删除</view>
              </view>
            </view>
            <text class="none" v-if="!filterRefs.length">还没有参考菜谱</text>
            <view class="pbtn ghost more" v-if="filterRefs.length > shownRefs.length" @tap="refLimit += 20">加载更多（{{ shownRefs.length }}/{{ filterRefs.length }}）</view>
          </view>
        </template>

        <!-- ============ 3. 食材大类（只管公共层 scope=public） ============ -->
        <template v-if="sec === 'cat'">
          <view class="sec-h">
            <text class="sh-t">食材大类</text>
            <text class="sh-s">公共大类池；用户端会自动合并自己补录的</text>
            <view class="sec-act"><view class="pbtn" @tap="openModal('cat')">＋ 新增大类</view></view>
          </view>
          <view class="row card" v-for="c in cats" :key="c.id">
            <text class="cic">{{ c.icon }}</text>
            <text class="inm">{{ c.name }}</text>
            <view class="sp"></view>
            <view class="pbtn ghost" @tap="moveCat(c, 'up')">↑</view>
            <view class="pbtn ghost" @tap="moveCat(c, 'down')">↓</view>
            <view class="pbtn ghost" @tap="editCat(c)">✎</view>
            <view class="pbtn danger" @tap="delCat(c)">✕</view>
          </view>
          <text class="none" v-if="!cats.length">还没有公共大类</text>
        </template>

        <!-- ============ 5. 食材库（只管公共层 scope=public） ============ -->
        <template v-if="sec === 'ing'">
          <view class="sec-h">
            <text class="sh-t">食材库</text>
            <text class="sh-s">公共食材池；用户补录的不在管理端出现</text>
            <view class="sec-act"><view class="pbtn" @tap="openModal('ing')">＋ 新录</view></view>
          </view>
          <view class="grp" v-for="g in ingGroups" :key="g.cat">
            <text class="grp-t">{{ g.cat }}</text>
            <view class="row card" v-for="it in g.items" :key="it.id">
              <text class="r-ic">{{ it.icon || catIcon(it.cat) }}</text>
              <text class="inm">{{ it.name }}</text>
              <view class="sp"></view>
              <view class="pbtn ghost" @tap="openIngEdit(it)">✎</view>
              <view class="pbtn danger" @tap="delIng(it)">✕</view>
            </view>
          </view>
          <text class="none" v-if="!ingredients.length">公共食材库为空</text>
        </template>

        <!-- ============ 6. 系统配置 ============ -->
        <template v-if="sec === 'config'">
          <view class="sec-h">
            <text class="sh-t">系统配置</text>
            <text class="sh-s">配置表驱动 · 修改输入框后失焦即自动保存</text>
          </view>

          <!-- 1. 基础配置 -->
          <view class="gsec">
            <text class="g-h">基础配置</text>
            <view class="cfg-card">
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">厨房技巧审核</text><text class="cfg-rs">新增/修改技巧需管理员审核</text></view>
                <switch :checked="audit" @change="onAudit" />
              </view>
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">临期阈值（天）</text><text class="cfg-rs">在库食材剩余 ≤ 该天数视为临期</text></view>
                <input class="cfg-num w120" type="number" v-model="expiry" @blur="saveNum('expiry_threshold_days', expiry)" />
              </view>
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">管理员口令</text><text class="cfg-rs">登录管理端使用，保存后立即生效</text></view>
                <input class="cfg-num w200" v-model="passcode" @blur="save('admin_passcode', passcode)" />
              </view>
            </view>
          </view>

          <!-- 2. 图标池 -->
          <view class="gsec">
            <text class="g-h">图标池</text>
            <text class="g-s">逗号分隔 emoji；录入表单的候选图标从这里取</text>
            <view class="cfg-card">
              <view class="cfg-col">
                <text class="cfg-rt">食材图标池</text>
                <textarea class="cfg-pool" v-model="ingPool" @blur="savePool('ingredient_icon_pool', 'ingPool', 'ingIcons')" />
                <view class="cfg-prev"><text v-for="ic in ingIcons" :key="ic" class="cfg-pic">{{ ic }}</text></view>
              </view>
              <view class="cfg-col">
                <text class="cfg-rt">大类图标池</text>
                <textarea class="cfg-pool" v-model="catPool" @blur="savePool('cat_icon_pool', 'catPool', 'catIcons')" />
                <view class="cfg-prev"><text v-for="ic in catIcons" :key="ic" class="cfg-pic">{{ ic }}</text></view>
              </view>
              <view class="cfg-col">
                <text class="cfg-rt">菜谱图标池</text>
                <textarea class="cfg-pool" v-model="recipePool" @blur="savePool('recipe_emoji_pool', 'recipePool', 'recipeIcons')" />
                <view class="cfg-prev"><text v-for="ic in recipeIcons" :key="ic" class="cfg-pic">{{ ic }}</text></view>
              </view>
              <view class="cfg-col">
                <text class="cfg-rt">餐厅图标池</text>
                <textarea class="cfg-pool" v-model="shopPool" @blur="savePool('shop_icon_pool', 'shopPool', 'shopIcons')" />
                <view class="cfg-prev"><text v-for="ic in shopIcons" :key="ic" class="cfg-pic">{{ ic }}</text></view>
              </view>
              <view class="cfg-col cfg-col-last">
                <text class="cfg-rt">封面渐变池</text>
                <text class="cfg-rs">| 分隔 linear-gradient；菜谱封面预设</text>
                <textarea class="cfg-pool cfg-pool-grad" v-model="gradPool" @blur="save('cover_grad_pool', gradPool)" />
                <view class="cfg-prev"><view v-for="(g,i) in gradList" :key="i" class="cfg-pgrad" :style="{ background: g }"></view></view>
              </view>
            </view>
          </view>

          <!-- 3. 邮件服务 -->
          <view class="gsec">
            <text class="g-h">邮件服务 · SMTP</text>
            <text class="g-s">用于发送邮箱验证码（登录 / 绑定 / 注销）。QQ 邮箱填「设置 → 账户 → 开启 SMTP 服务」生成的那串授权码，不是登录密码。</text>
            <view class="cfg-card">
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">服务器 Host</text><text class="cfg-rs">QQ 邮箱：smtp.qq.com</text></view>
                <input class="cfg-num w220" v-model="smtpHost" @blur="save('smtp_host', smtpHost)" placeholder="smtp.qq.com" />
              </view>
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">端口 Port</text><text class="cfg-rs">465 = SSL，587 = STARTTLS</text></view>
                <input class="cfg-num w120" type="number" v-model="smtpPort" @blur="save('smtp_port', smtpPort)" placeholder="465" />
              </view>
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">发件邮箱 User</text><text class="cfg-rs">完整邮箱地址</text></view>
                <input class="cfg-num w260" v-model="smtpUser" @blur="save('smtp_user', smtpUser)" placeholder="your_mail@qq.com" />
              </view>
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">授权码 Pass</text><text class="cfg-rs">邮箱设置里生成的授权码（非登录密码）</text></view>
                <input class="cfg-num w260" type="password" v-model="smtpPass" @blur="save('smtp_pass', smtpPass)" placeholder="16 位授权码" />
              </view>
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">发件人名称 From</text><text class="cfg-rs">收件人看到的发件人名</text></view>
                <input class="cfg-num w220" v-model="smtpFrom" @blur="save('smtp_from', smtpFrom)" placeholder="吃啥好呀" />
              </view>
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">验证码有效期（分钟）</text><text class="cfg-rs">超时需重新获取</text></view>
                <input class="cfg-num w120" type="number" v-model="otpExpire" @blur="saveNum('otp_expire_min', otpExpire)" />
              </view>
              <view class="cfg-row">
                <view class="cfg-rc"><text class="cfg-rt">当前状态</text><text class="cfg-rs">{{ smtpReady ? '已配置，验证码会真实发信' : '未配置完整（缺 Host / User / Pass），验证码降级为后端日志打印' }}</text></view>
                <text class="cfg-badge" :class="{ on: smtpReady }">{{ smtpReady ? '已启用' : '未启用' }}</text>
              </view>
            </view>
          </view>

          <!-- 4. 登录与安全 -->
          <view class="gsec">
            <text class="g-h">登录与安全</text>
            <view class="cfg-card">
              <view class="cfg-col">
                <text class="cfg-rt">JWT 签名密钥</text>
                <text class="cfg-rs">用于签发登录 token，上线务必改成随机长串；改动后已发 token 全部失效</text>
                <input class="cfg-num cfg-num-full" v-model="jwtSecret" @blur="save('jwt_secret', jwtSecret)" placeholder="随机长字符串" />
              </view>
              <view class="cfg-col">
                <text class="cfg-rt">微信小程序 AppID</text>
                <text class="cfg-rs">填好后小程序登录走真实 openid（不再 mock）</text>
                <input class="cfg-num cfg-num-full" v-model="mpAppid" @blur="save('mp_appid', mpAppid)" placeholder="wx1234567890abcdef" />
              </view>
              <view class="cfg-col cfg-col-last">
                <text class="cfg-rt">微信小程序 AppSecret</text>
                <text class="cfg-rs">微信公众平台「开发 → 开发管理」里获取</text>
                <input class="cfg-num cfg-num-full" type="password" v-model="mpSecret" @blur="save('mp_secret', mpSecret)" placeholder="AppSecret" />
              </view>
            </view>
          </view>
        </template>

      </view>
    </view>

    <!-- ============ 通用弹窗（自绘 mask；按 modal.mode 切换表单） ============ -->
    <view class="mask" v-if="modal.show" @tap="closeModal">
      <view class="dialog" @click.stop>
        <!-- 录入 / 编辑参考菜谱 -->
        <template v-if="modal.mode === 'ref'">
          <text class="d-title">{{ form.id ? '编辑参考菜谱' : '录入参考菜谱' }}</text>
          <input v-model="form.name" placeholder="菜名 *" class="di" />
          <view class="d-sub">菜品 emoji <text class="t-12">点选候选或手动输入</text></view>
          <view class="icon-grid">
            <view v-for="ic in recipeIcons" :key="ic" class="icell" :class="{ on: form.em === ic }" @tap="form.em = ic">{{ ic }}</view>
          </view>
          <input v-model="form.em" placeholder="或手动输入，如 🍲" class="di" />
          <view class="dl-row"><text class="dl-l">耗时</text><input v-model.number="form.time" type="number" placeholder="分钟" class="di" /></view>
          <view class="dl-row"><text class="dl-l">难度</text><input v-model="form.diff" placeholder="简单/中等/较难" class="di" /></view>
          <input v-model="form.tagsText" placeholder="口味标签，逗号分隔" class="di" />
          <input v-model="form.ingText" placeholder="所需食材，逗号分隔（如：鸡蛋,番茄）" class="di" />
          <textarea v-model="form.stepsText" placeholder="步骤，每行一步" class="dt" />
          <view class="d-sub">封面渐变 <text class="t-12">点选预设</text></view>
          <view class="g-grid">
            <view class="gcell gcell-empty" :class="{ on: !refCoverGrad }" @tap="refCoverGrad = ''">空</view>
            <view v-for="g in grads" :key="g" class="gcell" :class="{ on: refCoverGrad === g }" :style="{ background: g }" @tap="refCoverGrad = g"></view>
          </view>
        </template>

        <!-- 公共食材大类 -->
        <template v-if="modal.mode === 'cat'">
          <text class="d-title">{{ form.id ? '改公共大类' : '录公共大类' }}</text>
          <input v-model="form.name" placeholder="大类名，如：豆制品" class="di" />
          <view class="d-sub">图标点选</view>
          <view class="icon-grid">
            <view v-for="ic in catIcons" :key="ic" class="icell" :class="{ on: form.icon === ic }" @tap="form.icon = ic">{{ ic }}</view>
          </view>
        </template>

        <!-- 公共食材 -->
        <template v-if="modal.mode === 'ing'">
          <text class="d-title">{{ form.id ? '改公共食材' : '录公共食材' }}</text>
          <input v-model="form.name" placeholder="食材名，如：老抽" class="di" />
          <view class="d-sub">图标 <text class="t-12">选专属 emoji（空则用大类图标）</text></view>
          <view class="icon-grid">
            <view class="icell" :class="{ on: !form.icon }" @tap="form.icon = ''">✕</view>
            <view v-for="ic in ingIcons" :key="ic" class="icell" :class="{ on: form.icon === ic }" @tap="form.icon = ic">{{ ic }}</view>
          </view>
          <view class="d-sub">归类到大类</view>
          <view class="chip-row">
            <view v-for="c in cats" :key="c.id" class="chip" :class="{ on: form.cat === c.name }" @tap="form.cat = c.name">{{ c.icon }} {{ c.name }}</view>
          </view>
        </template>

        <!-- 用户新增/编辑 -->
        <template v-if="modal.mode === 'user'">
          <text class="d-title">{{ form.id ? '编辑用户' : '新增用户' }}</text>
          <input v-model="form.name" placeholder="用户名 *" class="di" />
          <view class="chip-row">
            <view class="chip" :class="{ on: form.role === 'user' }" @tap="form.role = 'user'">🙂 普通用户</view>
            <view class="chip" :class="{ on: form.role === 'admin' }" @tap="form.role = 'admin'">👑 管理员</view>
          </view>
        </template>

        <view class="d-btns">
          <view class="pbtn ghost" @tap="closeModal">取消</view>
          <view class="pbtn" v-if="['ref','cat','ing','user'].includes(modal.mode)" @tap="save">保存</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { tipApi, recipeApi, ingredientApi, catApi, configApi, adminApi } from '@/api'
// request 仅用于取管理台令牌的存储键常量（ADMIN_TOKEN_KEY）
import request from '@/utils/request'

const DEFAULT_GRAD = 'linear-gradient(135deg,#4b3fe3,#8b5cf6)'

export default {
  data() {
    return {
      menus: [
        { k: 'stats', ic: '📊', t: '统计' },
        { k: 'users', ic: '👥', t: '用户管理' },
        { k: 'vip', ic: '👑', t: '会员' },
        { k: 'tips', ic: '👨‍🍳', t: '厨房技巧审核' },
        { k: 'ref', ic: '📚', t: '参考菜谱' },
        { k: 'cat', ic: '🗂️', t: '食材大类' },
        { k: 'ing', ic: '🧺', t: '食材库' },
        { k: 'config', ic: '⚙️', t: '系统配置' }
      ],
      DEFAULT_GRAD,
      sec: 'stats', curName: '', isAdmin: false, curAdminId: 0,
      // 会员管理（切到「会员」页签时加载）
      vipData: null, vipKpis: [], vipMembers: [], nowSec: 0, planNames: {},
      // 登录
      loginCode: '',
      // 统计（仅公共资源计数）
      stats: { cards: {} },
      // 各列表数据
      tips: [], refs: [], cats: [], ingredients: [], users: [],
      // 图标池只读缓存：仅用于录入表单的候选图标点选（编辑入口在「系统配置」独立页）
      catIcons: [], catPool: '',
      ingIcons: [], ingPool: '',
      recipeIcons: [], recipePool: '',
      gradPool: '',
      // 搜索 / 筛选 / 分页
      tipQ: '', tipSt: 'all', tipLimit: 20, tipSts: [
        { k: 'all', t: '全部' }, { k: 'pending', t: '待审核' }, { k: 'approved', t: '已公开' }, { k: 'rejected', t: '未通过' }
      ],
      refQ: '', refLimit: 20,
      modal: { show: false, mode: '', id: null },
      form: {},
      // 系统配置（inline 自 admin-config.vue）
      audit: true, expiry: '3', passcode: '',
      shopPool: '', shopIcons: [],
      smtpHost: '', smtpPort: '465', smtpUser: '', smtpPass: '', smtpFrom: '', otpExpire: '10',
      jwtSecret: '', mpAppid: '', mpSecret: '',
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
        { ic: '👨‍🍳', t: '技巧总数', k: c.tips_total || 0 },
        { ic: '⏳', t: '技巧待审', k: c.tips_pending || 0 }
      ]
    },
    // 系统配置
    gradList() { return (this.gradPool || '').split('|').map((s) => s.trim()).filter(Boolean) },
    smtpReady() { return !!(this.smtpHost && this.smtpUser && this.smtpPass) },
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
    // 公共食材按大类分组（展示顺序跟随 cats 排序）
    ingGroups() {
      const catsOrder = {}
      this.cats.forEach((c) => { catsOrder[c.name] = true })
      const byCat = {}
      this.ingredients.forEach((it) => { (byCat[it.cat] = byCat[it.cat] || []).push(it) })
      const keyed = Object.keys(byCat).sort((a, b) => {
        const oa = a in catsOrder, ob = b in catsOrder
        if (oa && ob) return this.cats.findIndex((c) => c.name === a) - this.cats.findIndex((c) => c.name === b)
        if (oa) return -1
        if (ob) return 1
        return a.localeCompare(b, 'zh')
      })
      return keyed.map((cat) => ({ cat, items: byCat[cat] }))
    },
    // 渐变预设列表：从 gradPool（|分隔）解析；空则回退 DEFAULT_GRAD
    grads() {
      if (!this.gradPool) return [DEFAULT_GRAD]
      const arr = this.gradPool.split('|').map(s => s.trim()).filter(Boolean)
      return arr.length ? arr : [DEFAULT_GRAD]
    }
  },
  onShow() {
    this.curName = uni.getStorageSync('eat_user') || '我'
    // 收紧写接口后：管理台必须持有有效令牌才能写。
    // 本地 eat_admin 标记可以被任何用户手搓伪造，因此这里必须经后端校验令牌
    // 确实是管理员令牌（stats 仅管理员可读）：校验失败一律清会话回到登录门。
    const tok = uni.getStorageSync(request.ADMIN_TOKEN_KEY)
    if (!(uni.getStorageSync('eat_admin') === '1' && !!tok)) {
      this._resetAdminSession()
      this.isAdmin = false
      return
    }
    adminApi.stats()
      .then(() => {
        this.isAdmin = true
        // 读当前 admin 的 uid（后端 admin_login 返回；用于自降级/自删按钮置灰）
        this.curAdminId = Number(uni.getStorageSync('eat_admin_uid') || 0)
        this.loadAll()
      })
      .catch(() => {
        this._resetAdminSession()
        this.isAdmin = false
      })
  },
  methods: {
    _resetAdminSession() {
      uni.removeStorageSync('eat_admin')
      uni.removeStorageSync(request.ADMIN_TOKEN_KEY)
      uni.removeStorageSync('eat_admin_uid')
      this.curAdminId = 0
    },

    // 根据大类名称查 icon（emoji），查不到回退 🥗
    catIcon(catName) {
      const c = this.cats.find((c) => c.name === catName)
      return (c && c.icon) || '🥗'
    },
    // 顶部导航 tab：切换右侧内容区
    onNav(m) {
      this.sec = m.k
      if (m.k === 'config') this.loadConfigs()
      if (m.k === 'vip') this.loadVip()
    },
    // —— 会员管理 ——
    fmtTs(ts) {
      if (!ts) return '-'
      const d = new Date(ts * 1000)
      return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
    },
    fen2yuan(fen) { return (Number(fen || 0) / 100).toFixed(fen % 100 === 0 ? 0 : 2) },
    planName(id) { return (this.planNames && this.planNames[id]) || id },
    async loadVip() {
      try {
        const [vip, planCfg] = await Promise.all([
          adminApi.vip(),
          configApi.get('vip_plans').catch(() => ({ value: '{}' })),
        ])
        this.vipData = vip
        this.nowSec = Math.floor(Date.now() / 1000)
        this.vipMembers = vip.members
        try { this.planNames = JSON.parse(planCfg.value || '{}') } catch (e) { this.planNames = {} }
        const k = vip.kpi
        this.vipKpis = [
          { ic: '👑', v: k.member_count, t: '生效中会员' },
          { ic: '⏳', v: k.expired_count, t: '已过期' },
          { ic: '🧾', v: k.order_count, t: '已支付订单' },
          { ic: '💰', v: '¥' + this.fen2yuan(k.revenue_fen), t: '累计收入' + (k.revenue_ios_fen ? `（iOS ¥${this.fen2yuan(k.revenue_ios_fen)}）` : '') },
        ]
      } catch (e) { this._err(e) }
    },
    grantVip(m) {
      uni.showModal({
        title: `赠送会员（${m.nickname || m.name || '用户' + m.id}）`,
        content: '', editable: true, placeholderText: '天数，叠加到当前到期时间，如 30',
        success: (r) => {
          if (!r.confirm) return
          const days = Number(r.content)
          adminApi.grantVip(m.id, days)
            .then(() => { uni.showToast({ title: '已赠送', icon: 'success' }); this.loadVip() })
            .catch(this._err)
        },
      })
    },
    revokeVip(m) {
      uni.showModal({
        title: '取消会员', content: `确认取消「${m.nickname || '用户' + m.id}」的会员？即时失效，订单留痕。`,
        success: (r) => {
          if (!r.confirm) return
          adminApi.revokeVip(m.id)
            .then(() => { uni.showToast({ title: '已取消', icon: 'success' }); this.loadVip() })
            .catch(this._err)
        },
      })
    },
    // —— 系统配置 ——
    splitIcons(v) { return (v || '').split(/[,，]/).map((s) => s.trim()).filter(Boolean) },
    async loadConfigs() {
      try {
        const keys = ['audit_enabled', 'expiry_threshold_days', 'admin_passcode',
          'ingredient_icon_pool', 'cat_icon_pool', 'recipe_emoji_pool', 'shop_icon_pool', 'cover_grad_pool',
          'smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_from', 'otp_expire_min',
          'jwt_secret', 'mp_appid', 'mp_secret']
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
        this.smtpHost = v.smtp_host; this.smtpPort = v.smtp_port || '465'
        this.smtpUser = v.smtp_user; this.smtpPass = v.smtp_pass
        this.smtpFrom = v.smtp_from; this.otpExpire = v.otp_expire_min || '10'
        this.jwtSecret = v.jwt_secret; this.mpAppid = v.mp_appid; this.mpSecret = v.mp_secret
      } catch (e) { uni.showToast({ title: e.message || '加载失败', icon: 'none' }) }
    },
    async save(key, val) {
      try { await configApi.set(key, String(val == null ? '' : val).trim()); uni.showToast({ title: '已保存', icon: 'none', duration: 700 }) }
      catch (e) {
        const msg = e.message || ''
        if (msg.indexOf('请先登录') >= 0) {
          uni.removeStorageSync('eat_admin'); uni.removeStorageSync(request.ADMIN_TOKEN_KEY)
          uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
          setTimeout(() => uni.reLaunch({ url: '/pages/admin/admin' }), 800); return
        }
        uni.showToast({ title: '保存失败：' + msg, icon: 'none' })
      }
    },
    saveNum(key, val) { const n = Number(val); if (!Number.isFinite(n) || n <= 0) return uni.showToast({ title: '请输入正整数', icon: 'none' }); this.save(key, String(n)) },
    savePool(key, poolField, iconsField) { this[iconsField] = this.splitIcons((this[poolField] || '').trim()); this.save(key, (this[poolField] || '').trim()) },
    onAudit(e) { this.audit = e.detail.value; configApi.set('audit_enabled', this.audit ? '1' : '0').then(() => uni.showToast({ title: '已保存', icon: 'none', duration: 700 })).catch((err) => uni.showToast({ title: err.message || '保存失败', icon: 'none' })) },
    // —— 登录门 ——
    async doLogin() {
      const code = (this.loginCode || '').trim()
      if (!code) return uni.showToast({ title: '请输入口令', icon: 'none' })
      try {
        // 后端校验口令后签发管理员令牌；写接口靠它通过 get_write_user（与用户端 eat_token 相互独立）
        const r = await adminApi.login(code)
        uni.setStorageSync('eat_admin', '1')
        uni.setStorageSync(request.ADMIN_TOKEN_KEY, r.token || '')
        // 存 admin uid，用于用户管理列表里「自降级/自删」按钮置灰（防止把自己踢下台锁死）
        uni.setStorageSync('eat_admin_uid', String(r.user_id || ''))
        this.curAdminId = Number(r.user_id || 0)
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
        // 食材库 / 大类双层模型：管理端只读公共层（scope=public），用户端合并自己的补录
        const [tips, refs, cats, ingredients, users, st] = await Promise.all([
          tipApi.list(true),
          recipeApi.list('admin'),
          catApi.list(1, true),
          ingredientApi.list(1, true),
          adminApi.users(),
          adminApi.stats()
        ])
        // 后端 tips 返回 cat / pub，admin 模板用 category / public，这里做字段名对齐
        this.tips = tips.map((t) => ({ ...t, category: t.cat || '', public: t.pub ? 1 : 0 }))
        this.refs = refs
        this.cats = cats.map((c) => ({ id: c.id, name: c.name, icon: c.icon || '🥗' }))
        this.ingredients = ingredients.map((x) => ({ id: x.id, name: x.name, cat: x.cat || '其他', icon: x.icon || '' }))
        this.users = users
        this.stats = st || this.stats
        // 图标池：仅读取用于录入表单的候选图标（编辑入口在「系统配置」独立页）
        const [cp, ip, rp, gp] = await Promise.all([
          configApi.get('cat_icon_pool'), configApi.get('ingredient_icon_pool'),
          configApi.get('recipe_emoji_pool'), configApi.get('cover_grad_pool'),
        ])
        this.catPool = cp.value || ''
        this.catIcons = (cp.value || '').split(/[,，]/).map(s => s.trim()).filter(Boolean)
        this.ingPool = ip.value || ''
        this.ingIcons = (ip.value || '').split(/[,，]/).map(s => s.trim()).filter(Boolean)
        this.recipePool = rp.value || ''
        this.recipeIcons = (rp.value || '').split(/[,，]/).map(s => s.trim()).filter(Boolean)
        this.gradPool = gp.value || ''
      } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
    },
    // —— 用户管理 ——
    // 写操作统一错误提示：后端 401/403（如删除自己被自保护拦截）必须弹出来，不能静默吞掉
    _err(e) { uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' }) },
    openUserAdd() { this.form = { id: null, name: '', role: 'user' }; this.modal = { show: true, mode: 'user', id: null } },
    editUser(u) { this.form = { id: u.id, name: u.nickname || u.name || '', role: u.role }; this.modal = { show: true, mode: 'user', id: u.id } },
    toggleRole(u) {
      const role = u.role === 'admin' ? 'user' : 'admin'
      if (u.id === 1 && role === 'user') return uni.showToast({ title: '内置管理员不可降级', icon: 'none' })
      adminApi.updateUser(u.id, { role }).then(this.loadAll).catch(this._err)
    },
    delUser(u) {
      if (u.id === 1) return uni.showToast({ title: '内置管理员不可删除', icon: 'none' })
      const label = u.nickname || u.name || ('用户' + u.id)
      const mail = u.email ? `（${u.email}）` : ''
      uni.showModal({ title: '删除用户', content: `删除「${label}」${mail}？`, confirmText: '删除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) adminApi.delUser(u.id).then(this.loadAll).catch(this._err) } })
    },
    // —— 食材大类（只管公共层） ——
    openCatAdd() { this.form = { id: null, name: '', icon: '🥗' }; this.modal = { show: true, mode: 'cat', id: null } },
    editCat(c) { this.form = { id: c.id, name: c.name, icon: c.icon }; this.modal = { show: true, mode: 'cat', id: c.id } },
    moveCat(c, dir) { catApi.move(c.id, dir, 1, true).then(this.loadAll).catch(this._err) },
    delCat(c) {
      uni.showModal({ title: '删除公共大类', content: `删除「${c.name}」？引用它的食材会退回「其他」。`, confirmText: '删除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) catApi.del(c.id, 1, true).then(this.loadAll).catch(this._err) } })
    },
    // —— 食材库（只管公共层） ——
    openIngEdit(it) { this.form = { id: it.id, name: it.name, cat: it.cat, icon: it.icon || '' }; this.modal = { show: true, mode: 'ing', id: it.id } },
    delIng(it) {
      uni.showModal({ title: '移除公共食材', content: `从公共食材库移除「${it.name}」？用户自己补录的不受影响。`, confirmText: '移除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) ingredientApi.del(it.id, 1, true).then(this.loadAll).catch(this._err) } })
    },
    // —— 技巧审核 ——
    statusText(s) { return { pending: '⏳ 待审核', approved: '✅ 已公开', rejected: '🚫 未通过' }[s] || '' },
    async approve(t) { try { await tipApi.approve(t.id); this.loadAll() } catch (e) { this._err(e) } },
    async reject(t) { try { await tipApi.reject(t.id); this.loadAll() } catch (e) { this._err(e) } },
    // —— 参考菜谱 编辑/删除 ——
    editRef(r) {
      // cover 直接存渐变字符串（旧 "emoji|grad" 格式兼容：取 | 后半段）
      let grad = r.cover || ''
      if (grad.includes('|')) grad = grad.split('|', 1)[1] || ''
      this.form = {
        id: r.id, name: r.name, em: r.em, time: r.time || 0, diff: r.diff || '简单',
        tagsText: (r.tags || []).join('、'),
        ingText: (r.ing || []).map((i) => i.name || i).join('、'),
        stepsText: (r.steps || []).join('\n'),
      }
      this.refCoverGrad = grad || ''
      this.modal = { show: true, mode: 'ref', id: r.id }
    },
    delRef(r) {
      uni.showModal({
        title: '删除参考菜谱', content: `删除「${r.name}」？若已加入「吃这些」会一并移除。`, confirmText: '删除', confirmColor: '#e64340',
        success: (res) => { if (res.confirm) recipeApi.del(r.id).then(this.loadAll).catch(this._err) }
      })
    },
    // —— 弹窗 ——
    // （食材大类的增删改/排序统一用上面「公共层」区块的方法，均带 user=1 & admin=1 —— 公共大类必须传 admin=1，
    //   否则后端 _get_row 返回 403「公共大类不能改」，表现为删不掉/移不动。此前此处存在一组同名方法把
    //   正确版本覆盖掉了（对象字面量后者生效），已删除。）
    openModal(mode) {
      if (mode === 'ref') {
        this.form = { id: null, name: '', em: '🍲', time: 20, diff: '简单', tagsText: '', ingText: '', stepsText: '' }
        this.refCoverGrad = ''
      }
      else if (mode === 'cat') { this.form = { id: null, name: '', icon: '🥗' } }
      else if (mode === 'ing') { this.form = { id: null, name: '', cat: (this.cats[0] && this.cats[0].name) || '其他', icon: '' } }
      this.modal = { show: true, mode, id: null }
    },
    closeModal() { this.modal = { show: false, mode: '', id: null } },
    save() {
      const mode = this.modal.mode
      if (mode === 'cat') {
        const name = (this.form.name || '').trim()
        if (!name) return uni.showToast({ title: '名称不能为空', icon: 'none' })
        const body = { name, icon: this.form.icon || '🥗' }
        const p = this.form.id
          ? catApi.update(this.form.id, body, 1, true)
          : catApi.create(body, 1, true)
        return p.then(() => { this.closeModal(); this.loadAll() }).catch((e) => uni.showToast({ title: e.message, icon: 'none' }))
      }
      if (mode === 'ing') {
        const name = (this.form.name || '').trim()
        if (!name) return uni.showToast({ title: '名称不能为空', icon: 'none' })
        const body = { name, cat: this.form.cat || '其他', icon: this.form.icon || '' }
        const p = this.form.id
          ? ingredientApi.update(this.form.id, body, 1, true)
          : ingredientApi.create(body, 1, true)
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
      const data = {
        source: 'admin',
        name, em: this.form.em || '🍲',
        cover: this.refCoverGrad || '',
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
.ahead { display: flex; align-items: center; gap: 20px; padding: 16px 24px; background: #4b3fe3; color: #fff; }
.ah-l { font-size: 18px; font-weight: 700; flex-shrink: 0; }
/* header 内嵌导航 tab 栏：紧贴 logo 右边 */
.asider { display: flex; align-items: center; gap: 2px; flex: 1; overflow-x: auto; min-width: 0; }
.nav { display: flex; align-items: center; gap: 6px; padding: 8px 16px; cursor: pointer; color: rgba(255,255,255,.8); font-size: 14px; border-bottom: 2px solid transparent; white-space: nowrap; flex-shrink: 0; transition: color .15s, border-color .15s, background-color .15s; border-radius: 6px 6px 0 0; }
.nav:hover { color: #fff; background: rgba(255,255,255,.1); }
.nav.on { color: #fff; border-bottom-color: #fff; background: rgba(255,255,255,.15); }
.nav-ic { font-size: 15px; }
.ah-r { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.ah-user { font-size: 14px; opacity: .9; }
.ah-role { font-size: 12px; background: #ffd166; color: #4b3fe3; padding: 2px 10px; border-radius: 999px; }
.ah-role.off { background: #fff2f2; color: #e64340; }

/* abody 现在是纯内容容器，不再含导航 */
.abody { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.acont { flex: 1; min-width: 0; overflow: auto; padding: 24px 32px; box-sizing: border-box; }

/* 登录门 */
.gate { margin: 60px auto; padding: 40px; background: #fff; border: 1px solid #e5e6eb; border-radius: 16px; text-align: center; max-width: 440px; }
.gate-ic { font-size: 44px; display: block; }
.gate-t { display: block; color: #555; font-size: 15px; margin: 12px 0 20px; }
.gate-in { border: 1px solid #d8dae0; border-radius: 10px; height: 46px; line-height: 46px; font-size: 18px; letter-spacing: 4px; width: 100%; box-sizing: border-box; }
.gate-act { margin-top: 24px; }
.gate-hint { display: block; color: #aaa; font-size: 12px; margin-top: 14px; }



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

/* 通用按钮（用 <view> 而非 <button>，彻底规避 uni-button 默认样式/定位/::after 问题）
   @tap 在 uni-app H5 端会同时映射 click + touchend，小程序端也原生支持。 */
.pbtn { background: #4b3fe3; color: #fff; font-size: 13px; padding: 8px 16px; border-radius: 8px; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  width: auto; height: auto; line-height: 1.2; white-space: nowrap;
  margin: 0; text-align: center;
  flex-shrink: 0; flex-grow: 0; flex-basis: auto; box-sizing: border-box;
  transition: filter .1s ease-out, background-color .12s ease-out, box-shadow .1s ease-out, color .12s ease-out, border-color .12s ease-out;
  -webkit-user-select: none; user-select: none; -webkit-tap-highlight-color: transparent; }
/* 悬停 / 按下反馈（不变形，避免 transform:scale 导致 click 在松手瞬间丢失） */
.pbtn:hover { filter: brightness(1.08); }
.pbtn:active { filter: brightness(.86); box-shadow: inset 0 2px 6px rgba(0, 0, 0, .2); }
.pbtn.ghost { background: #fff; color: #4b3fe3; border: 1px solid #4b3fe3; }
.pbtn.ghost:hover { background: #f3f1ff; }
.pbtn.ghost:active { background: #e7e3ff; }
.pbtn.danger { background: #fff; color: #e64340; border: 1px solid #e64340; }
.pbtn.danger:hover { background: #fff2f1; }
.pbtn.danger:active { background: #ffe3e1; }
.pbtn.ok { background: #07c160; }
.pbtn.dis { opacity: .5; cursor: not-allowed; pointer-events: none; }

/* 区块头部：给相对定位 + 最小 z-index，防止被下方元素意外盖住 */
.sec-h { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; position: relative; z-index: 1; }

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
.r-ic { font-size: 20px; margin-right: 6px; }
.inm { font-size: 14px; }
.grp { margin-bottom: 16px; }
.grp-t { display: block; font-size: 12px; color: #888; margin-bottom: 8px; }
/* 通用 名称/描述 双行（用户行复用） */
.sn { font-size: 14px; font-weight: 700; }
.sm { font-size: 12px; color: #888; }

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
/* 封面渐变选择器的「空」格：无背景，选中即封面留白 */
.gcell-empty { display: flex; align-items: center; justify-content: center; background: #f6f6f8; color: #999; font-size: 14px; }
.icon-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; max-height: 280px; overflow-y: auto; align-content: start; }
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
/* ===== 系统配置 ===== */
.gsec { margin-bottom: 24px; }
.g-h { font-size: 16px; font-weight: 700; display: block; margin-bottom: 4px; }
.g-s { font-size: 12px; color: #999; display: block; margin-bottom: 12px; line-height: 1.6; }

.cfg-card { background: #fff; border: 1px solid #e5e6eb; border-radius: 12px; padding: 4px 20px; }

.cfg-row { display: flex; align-items: center; gap: 16px; padding: 12px 0; }
.cfg-row + .cfg-row { border-top: 1px solid #e5e6eb; }
.cfg-rc { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.cfg-rt { font-size: 14px; font-weight: 600; color: #333; }
.cfg-rs { font-size: 12px; color: #999; line-height: 1.5; }

.cfg-col { padding: 14px 0; display: flex; flex-direction: column; gap: 6px; }
.cfg-col + .cfg-col { border-top: 1px solid #e5e6eb; }
.cfg-col-last { padding-bottom: 18px; }

.cfg-num { background: #fff; border: 1px solid #d8dae0; border-radius: 8px; height: 32px; line-height: 32px; padding: 0 12px; font-size: 13px; color: #333; box-sizing: border-box; }
.cfg-num-full { width: 100%; }
.w120 { width: 120px; } .w200 { width: 200px; } .w220 { width: 220px; } .w260 { width: 260px; }

.cfg-pool { background: #fff; border: 1px solid #d8dae0; border-radius: 8px; width: 100%; box-sizing: border-box; min-height: 55px; padding: 10px 12px; font-size: 12px; color: #333; font-family: monospace; }
.cfg-pool-grad { min-height: 75px; }
.cfg-prev { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.cfg-pic { background: #f3f4f7; border-radius: 6px; padding: 2px 8px; font-size: 13px; }
.cfg-pgrad { width: 28px; height: 17px; border-radius: 4px; }

.cfg-badge { font-size: 12px; padding: 3px 10px; border-radius: 999px; background: #fdecea; color: #c0392b; flex: none; }
.cfg-badge.on { background: #e8f8ef; color: #0a8f4d; }

/* ============ 响应式（必须放样式最末尾：媒体查询不增加优先级，
   同优先级下后写的基础规则会覆盖它，放中间等于白写） ============ */
/* 窄屏：隐藏左 logo 和右侧用户名/角色徽章，菜单 tab 栏占满整行显示更多项
   （只作用于带菜单的主 header；登录门的 header 没有菜单，logo 保留） */
@media (max-width: 1100px) {
  .ahead.main .ah-l, .ahead.main .ah-r { display: none; }
  .ahead.main { padding: 12px; gap: 0; }
}
/* 手机端（≤700px）：整页 flex 布局保持不变，只收紧内边距 + KPI 改两列 + 行内按钮换行，
   避免 4 列 KPI 卡被压扁、一行塞不下多个操作按钮导致溢出错乱 */
@media (max-width: 700px) {
  .acont { padding: 14px 12px; }
  .kpis { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .kpi { padding: 12px 14px; gap: 10px; }
  .row { flex-wrap: wrap; }               /* 名称一行、操作按钮折到下一行，不再横向溢出 */
  .fsearch { width: 100%; }               /* 搜索框占满整行 */
  .rcard { width: 100%; }                 /* 菜谱卡占满整行 */
  .gate { margin: 30px auto; padding: 24px; }
}
</style>