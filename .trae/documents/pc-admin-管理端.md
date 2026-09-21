# PC 管理端（复用 uni-app 代码库做 PC 适配）

## Context
吃啥 App 目前是移动端 uni-app H5 + FastAPI 后端。管理员功能（厨房技巧审核、封面图库、
食材库/大类、参考菜谱、餐厅、系统配置）已存在于移动端页面并可运行，但都是「手机竖屏 + 底部
tab + 卡片流」的布局，在 PC 宽屏上体验差、也不像管理后台。

用户目标：**做一个 PC 宽屏的管理端**，复用现有 uni-app 代码库与 API，**前提是保证现有移动端功能不受影响**。

**核心设计取舍（已与用户对齐）**：不新建独立前端工程；在 uni-app 内新增一个「PC 管理台」页面，
左侧菜单 + 右侧内容区；旧移动页面一律不动，只新增页面 + 一个受宽度控制的入口，把改动面和风险降到最低。

## 方案概览
- 新增一个自包含的管理台页面 `pages/admin/admin.vue`：桌面宽屏下呈现「左侧边栏 + 右侧内容区」。
- 菜单分 6 个区：**厨房技巧审核 / 参考菜谱 / 封面图库 / 食材库 & 大类 / 餐厅 / 系统配置**。
- 全部复用现有 `src/api/index.js` 里的 API 客户端（`tipApi` `recipeApi` `coverApi`
  `ingredientApi` `catApi` `shopApi` `configApi`），**不改任何后端**。
- 管理员身份复用现有 `uni.setStorageSync('eat_admin')` 开关（MVP 无登录，沿用演示语义）。
- 入口只在 **PC 宽屏**显示（宽度判断），移动端看不到、不受任何影响。

## 改动清单

### 1. 新增 `frontend/src/pages/admin/admin.vue`（核心，自包含）
- **布局**：
  - 根节点 `min-height:100vh; display:flex; flex-direction:column` 之外，直接做**居中宽容器**
    （左右留白）的桌面布局——不要动全局 `.tab-page` / `.tab-scroll`，避免影响移动端。
  - 顶部一条管理台 header（标题「吃啥 · 管理端」+ 当前用户名/管理员徽章 + 返回）。
  - 主体：`display:flex`，左栏固定宽（图标 + 菜单项，当前高亮），右栏 `flex:1` 内容区随
    菜单 `v-if` 切换。
- **权限门**：`onShow` 读取 `eat_admin`；非管理员显示提示 + 「开启管理员（演示）」开关
  （复用 mine-tips.vue 的演示开关语义）。
- **6 个区**（复用以下现有页面/API 的模式，按管理台结构重排）：
  1. **厨房技巧审核**：`tipApi.list(viewer, admin=1)` 拉全部；pending 显示「通过/退回」
     （`tipApi.approve/reject`），已审核显示状态徽章。逻辑对齐 `pages/mine-tips/mine-tips.vue`。
  2. **参考菜谱**：`recipeApi.list('admin')` 列表；新增/编辑走 `recipeApi.create({source:'admin'})`/
     `recipeApi.update`（注意 `update` 对 `source=admin` 是 403 只读——参考菜谱只支持**新增与删除**周边无编辑？后端限制 admin 只读，故本区仅「新增 + 删除/仅维护」，编辑需删后重建）；删除 `recipeApi.del`（后端 admin 删除也 403）→ 参考菜谱仅能**新增**，需在计划里注明并尊重后端约束。
  3. **封面图库**：`coverApi.*` 全量 CRUD + 排序 + 预设渐变点选（复用 mine-covers.vue 的 emoji+渐变选择逻辑）。
  4. **食材库 & 大类**：`ingredientApi.*` + `catApi.*`；右侧分栏「食材 / 大类」两个子 Tab（复用 mine-ingredients.vue 的两 Tab + 弹窗逻辑）。
  5. **餐厅**：`shopApi.*` 列表 + 弹窗增改删（字段：名称/类型/价位/星级/招牌菜/备注/耗时/交通/标签，对齐 shop-detail）。
  6. **系统配置**：`configApi.get/set`，含**审核开关 `audit_enabled`** 和**临期阈值 `expiry_threshold_days`**（键名与后端一致）。
- 每区最小化：列表 + 关键操作；表单用页内色块弹窗（H5 不支持 uni.showModal editable，故用自绘 mask 弹窗——沿用现有约定）。

### 2. 注册路由 `frontend/src/pages.json`
- 在 `pages` 增一项 `pages/admin/admin`，`navigationStyle:"custom"`（对齐二级页约定，无原生导航栏）。

### 3. 入口（仅 PC 显示）`frontend/src/pages/mine/mine.vue`
- 在「我的」功能菜单「设置」之后加一行「🖥️ 管理端（PC）」`@tap` 跳 `admin/admin`（用 `uni.navigateTo`）。
- 用宽度判断控制**仅桌面显示**：`data` 加 `isPc`，`onShow` 里 `window.innerWidth >= 1024` 赋值；
  菜单行 `v-if="isPc"`。移动端完全不可见 → 不破坏现有功能。

## 复用点（避免重复造轮子）
- 全部数据层：`src/api/index.js` 的 `recipeApi/coverApi/ingredientApi/catApi/shopApi/configApi/tipApi`。
- 交互模式：2 源复用「大类单行横滑 + 清单点选」「自绘 mask 弹窗」；参考菜谱字段沿用 recipeApi 的 `name/em/cover/time/diff/tags/ing/steps`。
- 管理员演示语义：`eat_admin` + mine-tips 的审核开关样式。

## 明确的后端约束（尊重现有逻辑，不改后端）
- `recipes.update` / `recipes.delete` 对 `source='admin'` 均返回 403 → 参考菜谱区**只做新增**（跳过编辑/删除按钮），在界面上注明「参考菜谱仅供录入，不可编辑/删除」。

## 验证
1. 后端已跑在 8000、前端 5173（当前后台任务）。重启前端生效。
2. 浏览器（PC 视口 ≥1024 宽）打开 `http://localhost:5173/#/pages/admin/admin`：
   - 左侧 6 菜单切换，右栏内容正确；
   - 厨房技巧审核：能对 pending 通过/退回，状态徽章更新；
   - 封面图库/食材库/大类：增删改排序生效，刷新不丢；
   - 参考菜谱：能新增一条（source=admin）；无编辑/删除按钮；
   - 系统配置：开关与阈值读写生效。
3. **回归（关键）**：切换回移动端视口（<1024），确认「我的」页无「管理端」入口、原 tab 页
   （菜谱/冰箱/餐厅/我的）、mine-tips/mine-covers/mine-ingredients 均样式与交互不变、无报错。
4. 更新 `.trae/skills/eatwhat-v1-ui/SKILL.md` 与 `project_memory.md`，记录「PC 管理端」布局与入口约定。