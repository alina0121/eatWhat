# -*- coding: utf-8 -*-
"""
微信内容安全检测（msgSecCheck）。

为什么需要：小程序里有 UGC 内容时，微信提审明确要求接入内容安全接口，
否则大概率被驳回。本模块对用户提交的文本先行送检。

为什么用 urllib 而不是 requests/httpx：
项目 requirements 只依赖 fastapi/uvicorn/pydantic，为了一个同步 POST 引入
新依赖不划算，标准库足够（且与现有 sqlite3 同步阻塞风格一致）。

三条放行原则（fail-open，避免"检测故障 = 用户存不了内容"）：
1. 总开关关闭 → 放行。wx_sec_enabled 默认 '0'，本地 / H5 开发完全不受影响。
2. 未配置小程序凭证 → 放行。configs 里 mp_appid / mp_secret 为空时跳过。
3. 微信接口超时 / 报错 → 放行并打日志，不阻塞用户。
4. 无 openid → 放行。msgSecCheck v2 强制要求 openid，而 openid 需要先接
   wx.login 换 code 的登录流程（当前项目未接）。因此未接登录前本检测
   实际不会拦截，只会在接入登录后自动生效，无需再改调用方。

真正启用需要：配置 mp_appid / mp_secret → wx_sec_enabled 置 '1'
→ 接入 wx.login 让前端带 openid 上来。
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from app.routers.configs import get_config

_API_BASE = "https://api.weixin.qq.com"
# 检测是保存动作的必经环节，超时必须短，不能让用户干等
_TIMEOUT_SECONDS = 3
# access_token 内存缓存：微信侧有效期 7200s，这里提前 300s 视为过期
_TOKEN_CACHE = {"token": "", "expire_at": 0.0}


def _post_json(url: str, payload: dict = None) -> dict:
    """发一个 JSON 请求并解析 JSON 响应（同步阻塞，调用方需容忍 3s 上限）。"""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST" if data else "GET"
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_access_token(conn) -> str:
    """取接口调用凭证。命中缓存直接返回，未配置凭证返回空串。"""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expire_at"]:
        return _TOKEN_CACHE["token"]

    appid = (get_config(conn, "mp_appid", "") or "").strip()
    secret = (get_config(conn, "mp_secret", "") or "").strip()
    if not appid or not secret:
        return ""

    query = urllib.parse.urlencode(
        {"grant_type": "client_credential", "appid": appid, "secret": secret}
    )
    res = _post_json(f"{_API_BASE}/cgi-bin/token?{query}")
    token = res.get("access_token", "")
    if token:
        # 留 300s 提前量，避免边界过期
        ttl = max(int(res.get("expires_in", 7200)) - 300, 60)
        _TOKEN_CACHE["token"] = token
        _TOKEN_CACHE["expire_at"] = now + ttl
    return token


def check_text(conn, content: str, openid: str = None):
    """检测文本是否合规。

    返回 (是否放行: bool, 原因: str)。原因用于日志与前端提示。
    """
    # 原则 1：总开关默认关闭
    if get_config(conn, "wx_sec_enabled", "0") != "1":
        return True, "检测未启用"

    # 空白内容没有检测必要
    if not (content or "").strip():
        return True, "空内容"

    # 原则 4：无 openid（未接登录）时按未配置处理
    if not openid:
        return True, "缺少 openid，跳过检测"

    try:
        token = _get_access_token(conn)
        # 原则 2：未配置凭证
        if not token:
            return True, "未配置小程序凭证，跳过检测"
        res = _post_json(
            f"{_API_BASE}/wxa/msg_sec_check?access_token={urllib.parse.quote(token)}",
            {"content": content, "version": 2, "scene": 2, "openid": openid},
        )
    except Exception as exc:  # 原则 3：网络 / 解析异常一律放行
        print(f"[wxsec] 检测调用失败，按放行处理: {exc}")
        return True, f"检测异常: {exc}"

    # errcode != 0 表示调用本身失败（如 token 失效、频率超限）→ 放行
    if res.get("errcode", 0) != 0:
        print(f"[wxsec] 接口返回异常，按放行处理: {res}")
        return True, f"接口异常: {res.get('errmsg')}"

    suggest = ((res.get("result") or {}).get("suggest") or "pass").lower()
    if suggest == "pass":
        return True, "pass"
    # risky → 直接拦截。review → 交给本项目的「人工审核」流程兜底（技巧本身就要过审），
    # 故不在此拦死，避免误伤正常内容。
    if suggest == "review":
        return True, "review（转人工审核）"
    return False, "内容涉嫌违规，请修改后重试"
