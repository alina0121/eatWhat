/* ------------------------------------------------------------------
   吃啥 · 前端逻辑（第二迭代：跑通「吃这些 + 待采购」）
   同源访问：页面由 FastAPI 托管，接口路径相对（/recipes 等）。
   ------------------------------------------------------------------ */
"use strict";

/* ---- 轻量 API client ---- */
async function api(method, url, body) {
  const opt = { method, headers: {} };
  if (body !== undefined) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const res = await fetch(url, opt);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}
const API = {
  recipes: p => api("GET", "/recipes" + (p ? "?" + new URLSearchParams(p) : "")),
  createRecipe: b => api("POST", "/recipes", b),
  copyRecipe: id => api("POST", `/recipes/${id}/copy-to-mine`),
  candidates: () => api("GET", "/candidates"),
  addCandidate: b => api("POST", "/candidates", b),
  removeCandidate: id => api("DELETE", "/candidates/" + id),
  timerStart: id => api("POST", `/candidates/${id}/timer/start`),
  timerPause: id => api("POST", `/candidates/${id}/timer/pause`),
  timerCancel: id => api("POST", `/candidates/${id}/timer/cancel`),
  inStock: () => api("GET", "/fridge/in_stock"),
  addStock: b => api("POST", "/fridge/in_stock", b),
  updStock: (id, b) => api("PUT", `/fridge/in_stock/${id}`, b),
  delStock: id => api("DELETE", `/fridge/in_stock/${id}`),
  purchase: () => api("GET", "/fridge/purchase"),
  addPurchase: b => api("POST", "/fridge/purchase", b),
  delPurchase: id => api("DELETE", `/fridge/purchase/${id}`),
  shops: () => api("GET", "/shops"),
  diners: () => api("GET", "/diners"),
  createDiner: b => api("POST", "/diners", b),
  updDiner: (id, b) => api("PUT", `/diners/${id}`, b),
  updDinerTags: (id, b) => api("PUT", `/diners/${id}/tags`, b),
  delDiner: id => api("DELETE", `/diners/${id}`),
  tips: q => api("GET", "/tips" + (q ? "?" + new URLSearchParams(q) : "")),
  createTip: b => api("POST", "/tips", b),
  updTip: (id, b) => api("PUT", `/tips/${id}`, b),
  delTip: (id, author) => api("DELETE", `/tips/${id}?author=${encodeURIComponent(author)}`),
  tipApprove: id => api("POST", `/tips/${id}/approve`),
  tipReject: id => api("POST", `/tips/${id}/reject`),
  records: p => api("GET", "/records" + (p ? "?" + new URLSearchParams(p) : "")),
  calendar: () => api("GET", "/records/calendar"),
  createRecord: b => api("POST", "/records", b),
  updRecord: (id, b) => api("PUT", `/records/${id}`, b),
  delRecord: id => api("DELETE", `/records/${id}`),
  weights: () => api("GET", "/weights"),
  createWeight: b => api("POST", "/weights", b),
  updWeight: (id, b) => api("PUT", `/weights/${id}`, b),
  delWeight: id => api("DELETE", `/weights/${id}`),
  configs: () => api("GET", "/configs"),
  setConfig: (k, v) => api("PUT", `/configs/${k}`, { value: v }),
};

/* ---- 全局状态 ---- */
const state = {
  tab: "recommend",
  recipes: [],        // 全部菜谱
  candidates: [],     // 吃这些
  inStock: [],        // 在库
  purchase: [],       // 待采购
  candSet: new Set(), // 已在吃这些的 ref_id（避免同款重复进入）
  shops: [],          // 餐厅收藏
  diners: [],         // 干饭成员
  tips: [],           // 厨房技巧
  weights: [],        // 体重记录
  recordsCal: {},     // 饮食记录（按天聚合）
  configs: {},        // 配置表
  selectedDiners: [], // 已选干饭成员 id
  activeTags: [],     // 口味筛选生效标签（并集；选中成员自动并入，可手动增删）
  recom: { recipes: [], shop: null }, // 「为您推荐」随机结果
  adminMode: false,   // 管理员审核（演示）开关
};
// 当前用户（MVP 用名字，存 localStorage 以便不同角色演示）
let currentUser = lkey("user", "小明");
function lkey(k, d) { try { return localStorage.getItem(k) ?? d; } catch (e) { return d; } }
function lset(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ---- 计时实时走表：1 秒刷新运行中的候选显示 ---- */
const runnerBase = {};   // inboxId -> {elapsed, at}
const tickers = {};      // inboxId -> setInterval
function startTicker(id, elapsed) {
  stopTicker(id);
  runnerBase[id] = { elapsed, at: Date.now() };
  tickers[id] = setInterval(() => {
    const el = document.getElementById(`tick-${id}`);
    if (el) el.textContent = fmt(runnerBase[id].elapsed + (Date.now() - runnerBase[id].at) / 1000);
  }, 1000);
}
function stopTicker(id) { if (tickers[id]) { clearInterval(tickers[id]); delete tickers[id]; } }
function stopAllTickers() { Object.keys(tickers).forEach(stopTicker); }
function fmt(s) {
  const t = Math.floor(s);
  const m = Math.floor(t / 60), ss = t % 60;
  return `${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

/* ---- 数据加载 ---- */
async function loadRecipes() {
  state.recipes = await API.recipes();
  // 新建保存后回到列表；编辑参考菜谱不做
}
async function loadCandidates() {
  const list = await API.candidates();
  state.candidates = list;
  state.candSet = new Set(list.map(c => `${c.kind}:${c.ref_id}`));
  list.forEach(c => {
    if (c.timer && c.timer.running) startTicker(c.id, c.timer.elapsed);
  });
}
async function loadFridge() {
  state.inStock = await API.inStock();
  state.purchase = await API.purchase();
}
async function loadShops() { state.shops = await API.shops(); }
async function loadDiners() { state.diners = await API.diners(); }
async function loadTips() {
  // 管理员模式看全部（含他人待审/私密）以便审核；否则只看自己 + 已公开通过
  state.tips = await API.tips(state.adminMode ? { admin: true } : { viewer: currentUser });
}
async function loadWeights() { state.weights = await API.weights(); }
async function loadRecords() { state.recordsCal = await API.calendar(); }
async function loadConfigs() {
  const arr = await API.configs();
  state.configs = {}; arr.forEach(c => state.configs[c.key] = c.value);
}

/* ---- 监听导航 ---- */
$("nav").addEventListener("click", e => {
  const btn = e.target.closest("[data-tab]");
  if (!btn) return;
  state.tab = btn.dataset.tab;
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("on", b === btn));
  stopAllTickers();
  render();
});

/* ---- 干饭/页面渲染统一入口 ---- */
async function render() {
  const page = $("page");
  stopAllTickers();
  if (state.tab === "recipes" || state.tab === "recommend") { await loadRecipes(); await loadCandidates(); }
  if (state.tab === "fridge") { await loadFridge(); }
  if (state.tab === "recommend") { await loadShops(); await loadDiners(); }
  if (state.tab === "me") { await loadDiners(); await loadTips(); await loadWeights(); await loadRecords(); await loadConfigs(); }
  page.innerHTML = pageHTML();
  if (state.tab === "me") drawWeightChart(); // 体重画布实时曲线在 innerHTML 之后绘制
}

/* ---- 各 Tab 模板 ---- */
function pageHTML() {
  switch (state.tab) {
    case "recommend": return recommendHTML();
    case "recipes": return recipesHTML();
    case "fridge": return fridgeHTML();
    case "shops": return shopsHTML();
    case "me": return meHTML();
  }
}
/* ================= 推荐 Tab：转盘 + 口味筛选 + 为您推荐 ================= */

// 快捷口味筛选的标签全集：菜谱 + 餐厅 + 干饭成员偏好的并集去重
function allTags() {
  const s = new Set();
  state.recipes.forEach(r => (r.tags || []).forEach(t => s.add(t)));
  state.shops.forEach(sh => (sh.tags || []).forEach(t => s.add(t)));
  state.diners.forEach(d => (d.tags || []).forEach(t => s.add(t)));
  return [...s];
}
// 干饭成员缺省头像 emoji 调色板（成员模型无独立 em，派生稳定头像提升观感，不落库）
const DEM = ['👤', '👩', '🧔', '👧', '👨', '👱', '🧒'];
// 菜谱渐变封面背景类（k1~k4，按 id 稳定取色）
const KC = ['k1', 'k2', 'k3', 'k4'];
// 归集干饭成员选中的口味（并集，选中即自动带上他/她的口味）
function dinerSelectedTags() {
  const s = new Set();
  state.selectedDiners.forEach(id => {
    const d = state.diners.find(x => x.id === id);
    (d?.tags || []).forEach(t => s.add(t));
  });
  return [...s];
}
// 「🌤 不限 / 清空」：清空成员选择与口味筛选
function clearDiners() { state.selectedDiners = []; state.activeTags = []; render(); }
// 选中/取消干饭成员：口味过滤 = 当前选中成员口味的并集（联动后仍可手动取消）
function toggleDiner(id) {
  const i = state.selectedDiners.indexOf(id);
  if (i >= 0) state.selectedDiners.splice(i, 1); else state.selectedDiners.push(id);
  state.activeTags = dinerSelectedTags();
  render();
}
// 手动勾选/取消快捷口味 chip
function toggleTag(t) {
  const i = state.activeTags.indexOf(t);
  if (i >= 0) state.activeTags.splice(i, 1); else state.activeTags.push(t);
  render();
}
/* ---- 转盘「帮我选一个」：独立结果页 wheel（对齐第一版设计） ---- */
// 抽一题：菜谱 + 餐厅混合池（盲抽，不随口味筛选），带类型徽章
function pickOnce() {
  const all = [...state.recipes.map(r => ({
    kind: "recipe", id: r.id, em: r.em, name: r.name,
    sub: `${r.time} · ${(r.tags || []).join("/")}`
  })), ...state.shops.map(s => ({
    kind: "shop", id: s.id, em: "🏪", name: s.name,
    sub: [s.type ? s.type : "", s.price ? s.price : ""].filter(Boolean).join(" · ")
  }))];
  if (!all.length) { alert("还没有可抽的内容，先去菜谱/餐厅加一些吧"); return false; }
  state.spin = all[0 | Math.random() * all.length];
  return true;
}
// 点击 Hero「帮我选一个」：抽一题并进入独立结果页
function spin() { if (pickOnce()) { state.recView = "result"; render(); } }
// 结果页「再抽一次」：换新一题，候选按钮由渲染按 candSet 自动复位「＋ 候选」
function shuffle() { pickOnce(); render(); }
// 结果页「＋候选」→ 入吃这些（已在吃这些则由 candSet 显示「✓ 已选」
function spinAddCandidate() { if (state.spin) addCandidate(state.spin.kind, state.spin.id); }
// 结果页返回首页
function closeResult() { state.recView = "main"; render(); }
/* ---- 为您推荐：餐厅 1 家 + 菜谱（含 62px 渐变封面与「一人份」）---- */
// 「换一个」：轮换窗口步进
function reroll() { state.recOff = (state.recOff || 0) + 1; render(); }

function recommendHTML() {
  state.recView = state.recView || "main";
  state.recOff = state.recOff || 0;
  if (state.recView === "result") return resultViewHTML();

  // 干饭成员 chips：emoji + 姓名；「不限/清空」在无选择时高亮（横滑 chiprow）
  const allNone = state.selectedDiners.length === 0;
  const dchips = `<button class="chip ${allNone ? "on" : ""}" onclick="clearDiners()">🌤 不限 / 清空</button>` +
    (state.diners.map((d, i) =>
      `<button class="chip ${state.selectedDiners.includes(d.id) ? "on" : ""}"
          onclick="toggleDiner(${d.id})">${DEM[i % DEM.length]} ${esc(d.name)}</button>`).join("") ||
     `<button class="chip" onclick="goMe()">＋ 去「我的」完善干饭成员</button>`);

  // 快捷口味筛选 chips（横滑，并集过滤）
  const tchips = allTags().map(t =>
    `<button class="chip ${state.activeTags.includes(t) ? "on" : ""}"
        onclick="toggleTag('${esc(t)}')">${esc(t)}</button>`).join("") ||
    `<span class="t-13" style="padding:6px 2px">暂无口味标签，可到菜谱/餐厅/干饭成员里加</span>`;

  // 为您推荐：餐厅按轮换取 1 家；菜谱按口味过滤后轮换窗口（最多 3 道）
  const tags = state.activeTags;
  const shop = state.shops.length ? state.shops[state.recOff % state.shops.length] : null;
  let recs = tags.length ? state.recipes.filter(r => (r.tags || []).some(t => tags.includes(t))) : state.recipes.slice();
  let show = recs;
  if (recs.length > 3) { const off = state.recOff % recs.length; show = recs.concat(recs).slice(off, off + 3); }
  const K = ['k1', 'k2', 'k3', 'k4'];

  const shopC = shop ? `
    <div class="shop"><span class="em">🏪</span>
      <div style="flex:1"><div class="sn">${esc(shop.name)}</div>
        <div class="sm">${esc(shop.type || "")} · ⭐${shop.star}</div></div>
      ${candBtn("shop:" + shop.id, `addCandidate('shop',${shop.id})`)}
    </div>` : "";

  const recC = show.map((r, i) => `
    <div class="rec-card"><div class="cover ${K[i % 4]}">${r.em}</div>
      <div style="flex:1"><div class="c-name">${esc(r.name)}</div>
        <div class="c-meta">${r.time} · ${esc(r.diff)} · 一人份</div>
        <div class="tags">${(r.tags || []).map(t => `<span class="tg">${esc(t)}</span>`).join("")}</div></div>
      ${candBtn("recipe:" + r.id, `addCandidate('recipe',${r.id})`)}
    </div>`).join("");

  const recList = (shopC + recC) ||
    `<div class="t-13" style="padding:16px;text-align:center">没有匹配口味的菜谱，换个口味或点「换一个」看看</div>`;

  // 首页：Hero 转盘 → 跟谁一起吃 → 快捷筛一下 → 为您推荐
  return `<div class="topbar"><div class="brand">吃啥 🍽</div></div>
    <div class="hero">
      <div class="lab">选择困难？交给我</div>
      <div class="dice">🎲</div>
      <button class="btn" onclick="spin()">帮 我 选 一 个</button>
      <div class="sub">从你的菜谱 + 收藏餐厅里随机挑</div>
    </div>
    <div class="sec-tit">跟谁一起吃？ <span class="t-13">选上就带上他/她的口味</span></div>
    <div class="chiprow" id="today-diners">${dchips}</div>
    <div class="sec-tit">快捷筛一下</div>
    <div class="chiprow" id="today-quick">${tchips}</div>
    <div class="sec-tit">为您推荐<span class="link" style="margin-left:8px" onclick="reroll()">换一个</span></div>
    <div class="rec-list" id="today-rec">${recList}</div>`;
}

// 转盘独立结果页（wheel 圆盘 + 类型徽章 + 候选/再抽一次并排）
function resultViewHTML() {
  const p = state.spin;
  const isRecipe = !!(p && p.kind === "recipe");
  const inCand = p ? state.candSet.has(p.kind + ":" + p.id) : false;
  return `<div class="topbar"><button class="back" onclick="closeResult()">‹</button><div class="ptit">今日搭配</div></div>
    <div class="result-hero">
      <div class="wheel"><div class="inner">${p ? p.em : "🎲"}</div></div>
      <div style="text-align:center;margin-top:8px">
        <span class="tbadge ${isRecipe ? "my" : "ref"}">${isRecipe ? "菜谱" : "餐厅"}</span></div>
      <div class="result-tit">帮你抽中了「${p ? esc(p.name) : "—"}」</div>
      <div class="result-sub">${p ? esc(p.sub) : ""}</div>
    </div>
    <div class="actions row">
      <button class="pbtn primary" style="flex:1" ${inCand ? "disabled" : ""}
          onclick="spinAddCandidate()">${inCand ? "✓ 已选" : "＋ 候选"}</button>
      <button class="pbtn ghost" style="flex:1" onclick="shuffle()">&#8635; 再抽一次</button>
    </div>`;
}
function goMe() { state.tab = "me"; syncNav(); render(); }
function syncNav() { document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("on", b.dataset.tab === state.tab)); }
// 候选按钮：已在吃这些则「✓ 已选」禁用
function candBtn(key, onclick) {
  const inCand = state.candSet.has(key);
  return inCand
    ? `<button class="pbtn on sm" disabled>✓ 已选</button>`
    : `<button class="pbtn brand sm" onclick="${onclick}">＋ 候选</button>`;
}

/* ================= 餐厅 Tab ================= */
function shopsHTML() {
  const list = state.shops.map(s =>
    `<div class="card"><div class="card-row">
      <span class="type-badge" style="background:#fff0e0">🏪</span>
      <div class="inbox-src"><div class="name">${esc(s.name)}</div>
        <div class="sub">${esc(s.type)} · ⭐${s.star} · 到达${s.arr_min}分钟(${esc(s.transport)})</div></div>
      <span class="spacer" style="flex:1"></span>
      ${candBtn("shop:" + s.id, `addCandidate('shop',${s.id})`)}
    </div><div class="line2">${(s.must || []).map(m => `<span class="badge gray">招牌 · ${esc(m)}</span>`).join(" ")}</div></div>`).join("") ||
    `<div class="empty">还没有收藏的餐厅。餐厅管理入口在后续迭代完善。</div>`;
  return `<h2 class="title">🏪 餐厅</h2>${list}`;
}

/* ================= 我的 Tab：用户 / 干饭成员 / 厨房技巧 ================= */
function meHTML() {
  // 用户切换 + 管理员审核开关
  const userBox = `<div class="card"><div class="form">
      <label>当前用户（用于演示『只能改自己 / 管理员审核』）</label>
      <input id="me_user" value="${esc(currentUser)}" onchange="setMeUser()">
      <label style="display:flex;align-items:center;gap:8px;margin-top:10px">
        <input type="checkbox" id="me_admin" ${state.adminMode ? "checked" : ""} onchange="toggleAdmin()" style="width:auto">
        ⚙ 管理员审核（演示）
      </label>
    </div></div>`;

  // 干饭成员（用餐人）管理
  const diners = state.diners.map(d =>
    `<div class="card"><div class="card-row">
      <span class="emo">👤</span>
      <div class="inbox-src">
        <div class="name">${esc(d.name)}</div>
        <div class="sub">${(d.tags || []).map(t => `<span class="badge gray">${esc(t)}</span>`).join(" ")}</div>
      </div>
      <button class="pbtn ghost sm" onclick="openDinerModal(${d.id})">✎ 改</button>
      <button class="pbtn danger sm" onclick="delDiner(${d.id})">✕</button>
    </div></div>`).join("");

  // 厨房技巧列表
  const tips = state.tips.map(t => tipCard(t)).join("") ||
    `<div class="empty">还没有技巧。点「＋ 我来加」贡献一条～</div>`;

  return `<h2 class="title">👤 我的</h2>
    ${userBox}
    <div class="section-title">干饭成员<span class="spacer"></span>
      <button class="pbtn brand sm" onclick="openDinerModal()">＋ 新增</button></div>
    ${diners || `<div class="empty">还没有干饭成员。</div>`}
    <div class="section-title">厨房技巧<span class="spacer"></span>
      <button class="pbtn brand sm" onclick="openTipModal()">＋ 我来加</button></div>
    ${tips}

    <div class="section-title">体重记录</div>
    ${weightBlock()}

    <div class="section-title">干饭记录（饮食记录）</div>
    ${recordBlock()}

    <div class="section-title">设置</div>
    ${settingsBlock()}`;
}

/* ============ 体重记录（含实时曲线） ============ */
function weightBlock() {
  const list = state.weights.map(w =>
    `<div class="card"><div class="card-row">
      <span class="emo">⚖️</span>
      <div class="inbox-src"><div class="name">${w.weight.toFixed(1)} kg</div>
        <div class="sub">${esc(w.date)}${w.body_fat ? " · 体脂 " + w.body_fat.toFixed(1) + "%" : ""}</div></div>
      <button class="pbtn ghost sm" onclick="promptEditWeight(${w.id})">✎ 改</button>
      <button class="pbtn danger sm" onclick="delWeight(${w.id})">✕</button>
    </div></div>`).join("");
  // 体重/体脂实时曲线（canvas，派生数据，不落库）
  const chart = state.weights.length > 1 ? `<canvas id="wchart" height="120"></canvas>` : "";
  return `<div class="card"><div class="card-row">
      <input type="date" id="w_date" style="flex:1">
      <input id="w_weight" type="number" step="0.1" placeholder="体重kg" style="width:70px">
      <input id="w_bfat" type="number" step="0.1" placeholder="体脂%" style="width:70px">
      <button class="pbtn brand sm" onclick="addWeight()">＋ 记录</button>
    </div></div>
    ${chart}
    ${list || `<div class="empty">还没有体重记录。</div>`}`;
}
function drawWeightChart() {
  const cv = $("wchart"); if (!cv) return;
  const ctx = cv.getContext("2d"); ctx.clearRect(0, 0, cv.width, cv.height);
  const ws = state.weights; const n = ws.length;
  const cvw = cv.clientWidth || 300, H = 118, P = 12;
  cv.width = cvw * (window.devicePixelRatio || 1); cv.height = H * (window.devicePixelRatio || 1);
  ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
  const vals = ws.map(w => w.weight);
  const min = Math.min(...vals), max = Math.max(...vals), span = (max - min) || 1;
  const X = i => P + i * (cvw - 2 * P) / (n - 1);
  const Y = v => H - P - (v - min) / span * (H - 2 * P);
  ctx.strokeStyle = "#4b3fe3"; ctx.lineWidth = 2; ctx.beginPath();
  ws.forEach((w, i) => i ? ctx.lineTo(X(i), Y(w.weight)) : ctx.moveTo(X(i), Y(w.weight)));
  ctx.stroke();
  ws.forEach((w, i) => { ctx.fillStyle = "#4b3fe3"; ctx.beginPath();
    ctx.arc(X(i), Y(w.weight), 3, 0, 7); ctx.fill(); });
  ctx.fillStyle = "#8a8aa0"; ctx.font = "10px sans-serif";
  ctx.fillText(ws[0].date.slice(5).replace("-", "/"), P, H - 2);
  ctx.fillText(ws[n - 1].date.slice(5).replace("-", "/"), cvw - 40, H - 2);
}
function addWeight() {
  const date = $("w_date").value, weight = Number($("w_weight").value);
  if (!date || !weight) return alert("日期和体重必填");
  const bfat = $("w_bfat").value ? Number($("w_bfat").value) : null;
  createWeight({ date, weight, body_fat: bfat });
}
function promptEditWeight(id) {
  const w = state.weights.find(x => x.id === id); if (!w) return;
  const nd = prompt("日期", w.date); if (nd === null) return;
  const nw = prompt("体重kg", w.weight);
  const nb = prompt("体脂%(可空)", w.body_fat ?? "");
  updWeight(id, { date: nd.trim() || w.date, weight: Number(nw) || w.weight,
    body_fat: nb ? Number(nb) : null });
}
async function createWeight(b) { try { await API.createWeight(b); await loadWeights(); render(); } catch (e) { alert(e.message); } }
async function updWeight(id, b) { try { await API.updWeight(id, b); await loadWeights(); render(); } catch (e) { alert(e.message); } }
async function delWeight(id) { if (!confirm("删除这条体重记录？")) return;
  try { await API.delWeight(id); await loadWeights(); render(); } catch (e) { alert(e.message); } }

/* ============ 干饭记录（饮食记录，日历聚合 + 记账） ============ */
const TYPE_LABEL = { cook: "自己做", out: "餐厅", delivery: "外卖" };
function recordBlock() {
  const dates = Object.keys(state.recordsCal).sort().reverse();
  let allN = 0, stat = { cook: 0, out: 0, delivery: 0 };
  dates.forEach(d => state.recordsCal[d].forEach(r => { allN++; stat[r.type] = (stat[r.type] || 0) + 1; }));
  const statRow = allN ?
    `<div class="card"><div class="sub">共 ${allN} 次：自己做 ${stat.cook} · 餐厅 ${stat.out} · 外卖 ${stat.delivery}</div></div>` : "";
  const dayList = dates.map(d => `
    <div class="card">
      <div class="sub" style="margin-bottom:4px">${esc(d)}</div>
      ${state.recordsCal[d].map(r => `<div class="card-row" style="justify-content:space-between">
        <span class="name">${esc(r.name)} <span class="badge ${r.type === "cook" ? "purple" : r.type === "out" ? "orange" : "gray"}">${TYPE_LABEL[r.type]}</span></span>
        <span class="rowbtns">
          <button class="pbtn ghost sm" onclick="editRecord(${r.id})">✎ 改</button>
          <button class="pbtn danger sm" onclick="delRecord(${r.id})">✕</button>
        </span>
      </div>`).join("")}
    </div>`).join("") || `<div class="empty">还没有干饭记录，记一笔吧。</div>`;
  return `<div class="card"><div class="card-row">
      <input type="date" id="rc_date" value="${todayISO()}" style="flex:1">
      <input id="rc_name" placeholder="吃了什么" style="flex:1">
      <select id="rc_type"><option value="cook">自己做</option><option value="out">餐厅</option><option value="delivery">外卖</option></select>
      <button class="pbtn brand sm" onclick="addRecord()">＋ 记一笔</button>
    </div></div>
    ${statRow}
    ${dayList}`;
}
function todayISO() {
  const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}
function addRecord() {
  const date = $("rc_date").value, name = $("rc_name").value.trim(), type = $("rc_type").value;
  if (!date || !name) return alert("日期和吃了什么必填");
  createRecord({ date, name, type });
}
let editingRecord = null;
function editRecord(id) {
  // 复用内联表单：填入记录值后点「记一笔」即保存
  const found = Object.values(state.recordsCal).flat().find(r => r.id === id); if (!found) return;
  editingRecord = id; $("rc_date").value = found.date; $("rc_name").value = found.name;
  $("rc_type").value = found.type; $("rc_date").focus();
}
async function createRecord(b) {
  try {
    if (editingRecord) { await API.updRecord(editingRecord, b); editingRecord = null; }
    else await API.createRecord(b);
    await loadRecords(); render();
  } catch (e) { alert(e.message); }
}
async function delRecord(id) { if (!confirm("删除这条记录？")) return;
  try { await API.delRecord(id); await loadRecords(); render(); } catch (e) { alert(e.message); } }

/* ============ 设置（配置表驱动） ============ */
function settingsBlock() {
  const audit = state.configs.audit_enabled === "1";
  const threshold = state.configs.expiry_threshold_days || "3";
  return `<div class="card"><div class="form">
    <label style="display:flex;align-items:center;gap:8px">
      <input type="checkbox" ${audit ? "checked" : ""} onchange="setAudit(this.checked)" style="width:auto">
      厨房技巧需管理员审核
    </label>
    <label>临期预警阈值（天）——在库剩余天数低于此即标「临期」</label>
    <div class="card-row">
      <input id="cfg_threshold" type="number" value="${esc(threshold)}" style="flex:1">
      <button class="pbtn brand sm" onclick="saveThreshold()">保存</button>
    </div>
  </div></div>`;
}
async function setAudit(on) {
  try { await API.setConfig("audit_enabled", on ? "1" : "0"); await loadConfigs(); render(); }
  catch (e) { alert(e.message); }
}
async function saveThreshold() {
  try { await API.setConfig("expiry_threshold_days", $("cfg_threshold").value); await loadConfigs(); render(); }
  catch (e) { alert(e.message); }
}

/* 厨房技巧卡片：态标签 + 标题/两行摘要 + 点开展开全文
   → 自己可 编辑/删除；管理员模式可 通过/退回 */
function tipCard(t) {
  const own = t.author === currentUser;
  const st = t.status === "approved" ? '<span class="pill ok">✅ 已公开</span>'
    : t.status === "pending" ? '<span class="pill warn">⏳ 待审核</span>'
    : '<span class="pill bad">🚫 未通过</span>';
  const pub = t.pub ? "" : '<span class="badge gray">仅自己</span>';
  const ops = [];
  if (own) {
    ops.push(`<button class="pbtn ghost sm" onclick="openTipModal(${t.id})">✎ 编辑</button>`);
    ops.push(`<button class="pbtn danger sm" onclick="delTip(${t.id})">✕ 删除</button>`);
  }
  if (state.adminMode) {
    ops.push(`<button class="pbtn ok sm" style="background:#e6f6ee;color:var(--ok)" onclick="approveTip(${t.id})">通过</button>`);
    ops.push(`<button class="pbtn warn sm" style="background:#fff4e0;color:#e8890c" onclick="rejectTip(${t.id})">退回</button>`);
  }
  return `<div class="card">
    <div class="card-row">${st}${pub}<span class="badge gray">${esc(t.cat)}</span></div>
    <div class="name" style="margin:6px 0 2px">${esc(t.title)}</div>
    <div class="sub">${esc(t.content)}</div>
    ${ops.length ? `<div class="rowbtns" style="margin-top:8px">${ops.join("")}</div>` : ""}
  </div>`;
}
function setMeUser() { currentUser = $("me_user").value.trim() || "小明"; lset("user", currentUser); loadTips().then(render); }
async function toggleAdmin() { state.adminMode = $("me_admin").checked; await loadTips(); render(); }

/* 干饭成员 弹窗 */
let editingDiner = null;
function openDinerModal(id) {
  editingDiner = id ?? null;
  const d = id && state.diners.find(x => x.id === id);
  $("dn_name").value = d ? d.name : "";
  $("dn_tags").value = d ? (d.tags || []).join("、") : "";
  $("dinerModal").classList.add("open");
}
function closeDinerModal() { $("dinerModal").classList.remove("open"); }
async function saveDiner() {
  const tags = $("dn_tags").value.split(/[,、，]/).map(s => s.trim()).filter(Boolean);
  const name = $("dn_name").value.trim();
  if (!name) return alert("填一下姓名");
  try {
    if (editingDiner) await API.updDiner(editingDiner, { name, tags });
    else await API.createDiner({ name, tags });
    closeDinerModal(); await loadDiners(); render();
  } catch (e) { alert(e.message); }
}
async function delDiner(id) {
  if (!confirm("删除该干饭成员？")) return;
  try { await API.delDiner(id); await loadDiners(); render(); }
  catch (e) { alert(e.message); }
}

/* 厨房技巧 弹窗（新增 + 编辑回填） */
let editingTip = null;
function openTipModal(id) {
  editingTip = id ?? null;
  const t = id && state.tips.find(x => x.id === id);
  $("tipModalTitle").textContent = id ? "编辑技巧" : "＋ 我来加";
  $("tp_title").value = t ? t.title : "";
  $("tp_content").value = t ? t.content : "";
  $("tp_cat").value = t ? t.cat : "其他";
  $("tp_pub").checked = t ? !!t.pub : true;
  $("tipModal").classList.add("open");
}
function closeTipModal() { $("tipModal").classList.remove("open"); }
async function saveTip() {
  const body = {
    title: $("tp_title").value.trim(),
    content: $("tp_content").value.trim(),
    cat: $("tp_cat").value,
    author: currentUser,
    pub: $("tp_pub").checked,
  };
  if (!body.title || !body.content) return alert("标题和内容都要填");
  try {
    if (editingTip) await API.updTip(editingTip, body);
    else await API.createTip(body);
    closeTipModal(); await loadTips(); render();
  } catch (e) { alert(e.message); }
}
async function delTip(id) {
  const t = state.tips.find(x => x.id === id);
  if (!confirm(`删除「${t?.title}」？`)) return;
  try { await API.delTip(id, currentUser); await loadTips(); render(); }
  catch (e) { alert(e.message); }
}
async function approveTip(id) { try { await API.tipApprove(id); await loadTips(); render(); } catch (e) { alert(e.message); } }
async function rejectTip(id) { try { await API.tipReject(id); await loadTips(); render(); } catch (e) { alert(e.message); } }

/* ---- 菜谱 Tab：吃这些 + 按口味筛 + 全部菜谱 ---- */
function recipesHTML() {
  const inbox = state.candidates.map(c => inboxCard(c)).join("") ||
    `<div class="empty">吃这些还是空的，去下面挑几道菜加入吧 ☝️</div>`;
  // 按口味筛 chips（横滑）：全部 / 快手 / 辣 / 素 / 下饭 / 我的菜谱 / 参考菜谱
  const cat = state.recipeCat || "";
  const taste = [["", "全部"], ["快手", "快手"], ["辣", "🌶 辣"], ["素", "素"], ["下饭", "下饭"]]
    .map(([v, l]) => `<button class="chip ${cat === v ? "on" : ""}" onclick="catSel('${v}')">${l}</button>`).join("");
  const srcChip = `<button class="chip ${cat === "my" ? "on" : ""}" onclick="catSel('my')">我的菜谱</button>
    <button class="chip ${cat === "ref" ? "on" : ""}" onclick="catSel('ref')">参考菜谱</button>`;
  // 全部菜谱：按当前筛选过滤（口味标签 / 我的 / 参考）
  const recList = state.recipes.filter(r => !cat
    ? true
    : cat === "my" ? r.source !== "admin"
    : cat === "ref" ? r.source === "admin"
    : (r.tags || []).includes(cat)
  ).map(r => recipeCard(r)).join("") ||
    `<div class="empty">还没有菜谱，点「全部菜谱」旁的「＋ 新建菜谱」创建第一道。</div>`;

  return `<div class="topbar"><div class="ptit">吃这些</div></div>
    ${inbox}
    ${state.candidates.length ? `<div class="sec-tit">待采购（缺货自动代入）</div>${purchaseMini()}` : ""}
    <div class="sec-tit">按口味筛</div>
    <div class="chiprow">${taste}${srcChip}</div>
    <div class="sec-tit">全部菜谱 <span class="t-13 link" style="margin-left:8px" onclick="openRecipeModal()">＋ 新建菜谱</span></div>
    <div class="rec-list">${recList}</div>`;
}
// 切换「按口味筛」（点同项取消回到全部）
function catSel(v) { state.recipeCat = (state.recipeCat || "") === v ? "" : v; render(); }

/* 吃这些候选卡片：两行 eat-row（第一行 emoji+名称+徽章+✕，第二行 计时+记一笔） */
function inboxCard(c) {
  const isRecipe = c.kind === "recipe";
  const badge = isRecipe ? `<span class="tbadge my">菜谱</span>` : `<span class="tbadge ref">餐厅</span>`;
  const timer = c.timer;
  let ctl;
  if (!timer) {
    ctl = `<button class="tbtn on" onclick="timerStart(${c.id})">▶ 计时</button>`;
  } else if (timer.running) {
    ctl = `<b class="rtime">⏱ <span id="tick-${c.id}">${fmt(timer.elapsed)}</span></b>
      <button class="tbtn" onclick="timerPause(${c.id})">⏸ 停止</button>
      <button class="tbtn" onclick="timerCancel(${c.id})">⏹ 取消</button>`;
  } else {
    ctl = `<b class="rtime muted">⏱ ${fmt(timer.elapsed)}</b>
      <button class="tbtn on" onclick="timerStart(${c.id})">▶ 继续</button>
      <button class="tbtn" onclick="timerCancel(${c.id})">⏹ 取消</button>`;
  }
  return `<div class="eat-row">
    <span class="dx">${esc(c.em)}</span>
    <div class="tl-col">
      <div class="tl-top"><span class="in">${esc(c.name)}</span>${badge}
        <span class="rm-btn" onclick="removeCandidate(${c.id})">✕</span></div>
      <div class="tl-bot">${ctl}
        <button class="tbtn" style="font-weight:600" onclick="recordFromCandidate(${c.id})">📝 记一笔</button></div>
    </div>
  </div>`;
}

/* 对应吃这些的待采购速览（精简：只看被代入的） */
function purchaseMini() {
  const list = state.purchase.map(p =>
    `<div class="card"><div class="card-row"><span class="emo">🛒</span>
      <span class="name">${esc(p.name)}</span>
      <span class="pill dim">${q(p.qty)}${esc(p.unit)}</span>
      <span class="spacer" style="flex:1"></span>
      <button class="pbtn danger sm" onclick="delPurchase(${p.id})">✕</button></div></div>`).join("");
  return list || `<div class="empty">没有缺货要买，冰箱都齐了 🎉</div>`;
}
const q = v => (Number(v) % 1 === 0 ? Math.round(v) : Number(v).toFixed(1));

/* 全部菜谱卡片：渐变封面 + 我的/参考徽章 + 一人份 + 标签（对齐第一版设计） */
function recipeCard(r) {
  const inCand = state.candSet.has("recipe:" + r.id);
  const btn = inCand
    ? `<button class="pbtn on sm" disabled>✓ 已选</button>`
    : `<button class="pbtn brand sm" onclick="addCandidate('recipe',${r.id})">＋ 候选</button>`;
  const badge = r.source === "admin"
    ? `<span class="tbadge ref">参考</span>`
    : `<span class="tbadge my">我的</span>`;
  return `<div class="rec-card"><div class="cover ${KC[Math.abs(r.id) % 4]}">${esc(r.em)}</div>
    <div style="flex:1"><div class="c-name">${esc(r.name)} ${badge}</div>
      <div class="c-meta">${r.time} · ${esc(r.diff)} · 一人份</div>
      <div class="tags">${(r.tags || []).map(t => `<span class="tg">${esc(t)}</span>`).join("")}</div></div>
    ${btn}
    ${r.source === "admin" ? `<button class="pbtn ghost sm" onclick="copyToMy(${r.id})">📥 存我的</button>` : ""}
  </div>`;
}

/* ---- 冰箱 Tab：待采购 + 在库 ---- */
function fridgeHTML() {
  return `<h2 class="title">🧊 冰箱</h2>
    <div class="section-title">待采购（缺货自动代入 + 手工可加）</div>
    ${fridgePurchase()}
    <div class="section-title">在库</div>
    ${fridgeInStock()}`;
}
function fridgePurchase() {
  const rows = state.purchase.map(p =>
    `<div class="card"><div class="card-row">
      <span class="emo">🛒</span>
      <div class="inbox-src"><div class="name">${esc(p.name)}</div>
        <div class="sub">待买 ${q(p.qty)}${esc(p.unit)}</div></div>
      <button class="pbtn danger sm" onclick="delPurchase(${p.id})">✕ 移除</button>
    </div></div>`).join("");
  return rows + `<div class="card"><div class="card-row">
      <div class="inbox-src"><input id="pur_name" placeholder="想买什么"></div>
      <input id="pur_qty" type="number" value="1" style="width:58px">
      <input id="pur_unit" value="份" style="width:50px">
      <button class="pbtn brand sm" onclick="addPurchase()">＋ 采购</button>
    </div></div>`;
}
function fridgeInStock() {
  return state.inStock.map(it => {
    const pill = !it.buy
      ? `<span class="pill dim">无保质期</span>`
      : it.status === "已过期" ? `<span class="pill bad">已过期</span>`
      : it.status === "临期" ? `<span class="pill warn">临期 · 剩 ${it.remain} 天</span>`
      : `<span class="pill ok">充足 · 剩 ${it.remain} 天</span>`;
    return `<div class="card">
      <div class="card-row">
        <span class="emo">📦</span>
        <div class="inbox-src"><div class="name">${esc(it.name)}</div></div>
        <button class="pbtn ghost sm" onclick="editStock(${it.id})">✎ 改</button>
        <button class="pbtn danger sm" onclick="delStock(${it.id})">✕</button>
      </div>
      <div class="line2">${esc(it.cat)} · ${q(it.qty)}${esc(it.unit)}${it.store ? " · " + esc(it.store) : ""} ${pill}</div>
    </div>`;
  }).join("") + `<div class="card"><div class="card-row">
      <div class="inbox-src">
        <input id="st_name" placeholder="食材名"><input id="st_qty" type="number" value="1" style="width:58px;margin-top:6px">
        <input id="st_unit" value="份" style="width:50px;margin-left:4px">
        <select id="st_cat" style="margin-left:4px"><option>其他</option><option>蔬菜</option><option>肉类</option><option>调料</option><option>主食</option></select>
      </div>
      <button class="pbtn brand sm" onclick="addStock()">＋ 入库存</button>
    </div></div>`;
}

/* ---- 菜谱：新建/编辑 弹窗 ---- */
let editingRecipe = null;
function openRecipeModal() {
  editingRecipe = null;
  $("recipeModalTitle").textContent = "新建菜谱";
  ["rp_name","rp_em","rp_time","rp_diff","rp_tags","rp_steps"].forEach(id => $id_input_clear(id));
  $("rp_em").value = "🍽"; $("rp_time").value = 20; $("rp_diff").value = "简单";
  $("rp_ings").innerHTML = ingRowHTML();
  $("recipeModal").classList.add("open");
}
function $id_input_clear(id) { const el = $(id); el.value = ""; }
function ingRowHTML(it = { name: "", qty: 1, unit: "份" }) {
  return `<div class="ing-row">
    <input placeholder="食材名" class="ing-name" value="${esc(it.name)}">
    <input type="number" class="ing-qty" value="${it.qty}" style="width:58px">
    <input class="ing-unit" value="${esc(it.unit)}" style="width:50px">
    <button class="pbtn danger sm" onclick="this.closest('.ing-row').remove()">✕</button>
  </div>`;
}
$("rp_add_ing").addEventListener("click", () =>
  $("rp_ings").insertAdjacentHTML("beforeend", ingRowHTML()));
function closeModal() { $("recipeModal").classList.remove("open"); }
$("rp_cancel").addEventListener("click", closeModal);
$("recipeModal").addEventListener("click", e => { if (e.target === $("recipeModal")) closeModal(); });
$("rp_save").addEventListener("click", saveRecipe);

async function saveRecipe() {
  const ing = [...document.querySelectorAll("#rp_ings .ing-row")].map(r => ({
    name: r.querySelector(".ing-name").value.trim(),
    qty: Number(r.querySelector(".ing-qty").value) || 1,
    unit: r.querySelector(".ing-unit").value.trim() || "份",
  })).filter(i => i.name);
  const body = {
    source: "my",
    name: $("rp_name").value.trim(),
    em: $("rp_em").value.trim() || "🍽",
    time: Number($("rp_time").value) || 0,
    diff: $("rp_diff").value,
    tags: $("rp_tags").value.split(/[,，]/).map(s => s.trim()).filter(Boolean),
    ing,
    steps: $("rp_steps").value.split("\n").map(s => s.trim()).filter(Boolean),
  };
  if (!body.name) return alert("请填菜谱名称");
  try { await API.createRecipe(body); closeModal(); await loadRecipes(); render(); }
  catch (e) { alert("保存失败：" + e.message); }
}

/* ---- 事件：候选 / 计时 / 待采购 / 在库 ---- */
async function addCandidate(kind, refId) {
  try { await API.addCandidate({ kind, ref_id: refId }); await render(); }
  catch (e) { alert(e.message); }
}
async function removeCandidate(cid) {
  if (!confirm("确定把这道从「吃这些」移除？代入的待采购会按量回退。")) return;
  try { await API.removeCandidate(cid); await render(); }
  catch (e) { alert(e.message); }
}
async function timerStart(cid) { try { await API.timerStart(cid); await render(); } catch (e) { alert(e.message); } }
async function timerPause(cid) { try { await API.timerPause(cid); await render(); } catch (e) { alert(e.message); } }
async function timerCancel(cid) { try { await API.timerCancel(cid); await render(); } catch (e) { alert(e.message); } }
// 「存进我的菜谱」：参考菜谱(source=admin)复制一份为我的菜谱（可编辑）
async function copyToMy(id) {
  try { await API.copyRecipe(id); await render(); alert("已存入我的菜谱"); }
  catch (e) { alert(e.message); }
}
// 吃这些「记一笔」：直接把候选记为一次饮食记录（菜谱→自己做，餐厅→餐厅）
async function recordFromCandidate(cid) {
  const c = state.candidates.find(x => x.id === cid);
  if (!c) return;
  try {
    await API.createRecord({ date: todayISO(), name: c.name, type: c.kind === "recipe" ? "cook" : "out" });
    await render();
  } catch (e) { alert(e.message); }
}

async function addPurchase() {
  const name = $("pur_name").value.trim();
  if (!name) return alert("填一下要买什么");
  try {
    await API.addPurchase({ name, qty: Number($("pur_qty").value) || 1, unit: $("pur_unit").value.trim() || "份" });
    await render();
  } catch (e) { alert(e.message); }
}
async function delPurchase(id) {
  try { await API.delPurchase(id); await render(); } catch (e) { alert(e.message); }
}

function addStock() {
  const n = $("st_name"), g = $("st_qty"), u = $("st_unit"), c = $("st_cat");
  const body = { name: n.value.trim(), cat: c.value, qty: Number(g.value) || 1, unit: u.value.trim() || "份", store: "", buy: "", days: 7 };
  if (!body.name || !confirm(`入库存「${body.name} ×${body.qty}${body.unit}」？`)) return;
  (async () => {
    try { await API.addStock(body); await render(); } catch (e) { alert(e.message); }
  })();
}
function editStock(id) {
  promptEditStock(id);
}

/* 简单版行内编辑：用 prompt 凑合，保持本迭代功能完整 */
function promptEditStock(id) {
  const it = state.inStock.find(x => x.id === id);
  if (!it) return;
  const name = prompt("食材名", it.name);
  if (name === null) return;
  const qty = prompt("数量", it.qty);
  const days = prompt("保质期(天)", it.days);
  const body = {
    name: name.trim() || it.name,
    cat: it.cat, qty: Number(qty) || it.qty, unit: it.unit,
    store: it.store, buy: it.buy, days: Number(days) || it.days,
  };
  (async () => { try { await API.updStock(id, body); await render(); } catch (e) { alert(e.message); } })();
}
async function delStock(id) {
  if (!confirm("确定删除该食材？")) return;
  try { await API.delStock(id); await render(); } catch (e) { alert(e.message); }
}

/* ---- 启动 ---- */
render();