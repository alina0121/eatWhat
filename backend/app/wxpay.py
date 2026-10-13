# -*- coding: utf-8 -*-
"""
微信小程序虚拟支付服务端对接（会员收款）。

官方能力页：/miniprogram/dev/platform-capabilities/business-capabilities/virtual-payment/
- 客户端：wx.requestVirtualPayment（内部含下单 + 拉起支付；success 回调可能丢失）
- 服务端：/xpay/* 系列接口，对账以 /xpay/query_order 查单为准（不要只信前端回调）

⚠️ 对接说明（P0 骨架）：
签名与报文字段需在「管理后台配置 wxpay_offer_id / wxpay_pay_key、小程序完成虚拟支付签约」后，
按官方文档逐字段核对再上线 —— 本文件先把鉴权与调用结构搭好，未配置时 payments 路由
会走 mock 模式（下单即开通），不影响本地与开发期联调。
"""
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request

from .routers.configs import get_config

_API = "https://api.weixin.qq.com"


def configured(conn) -> bool:
    """是否具备真实收款条件（offer_id + pay_key 已配置）。"""
    return bool(get_config(conn, "wxpay_offer_id", "")) and bool(get_config(conn, "wxpay_pay_key", ""))


def _access_token(conn) -> str:
    """小程序全局 access_token（简化实现：每次现取；量大后应加缓存）。"""
    appid = get_config(conn, "mp_appid", "")
    secret = get_config(conn, "mp_secret", "")
    if not (appid and secret):
        raise RuntimeError("mp_appid / mp_secret 未配置")
    url = f"{_API}/cgi-bin/token?grant_type=client_credential&appid={urllib.parse.quote(appid)}&secret={urllib.parse.quote(secret)}"
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    if "access_token" not in data:
        raise RuntimeError(f"获取 access_token 失败: {data}")
    return data["access_token"]


def _pay_sig(conn, uri: str, body: dict) -> str:
    """xpay 接口的 pay_sig：HMAC-SHA256(pay_key, uri&body)。字段拼接方式以官方文档核对为准。"""
    pay_key = get_config(conn, "wxpay_pay_key", "")
    payload = f"{uri}&{json.dumps(body, separators=(',', ':'), ensure_ascii=False)}"
    return hmac.new(pay_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def sign_data_signature(conn, sign_data: dict) -> str:
    """wx.requestVirtualPayment 所需的 sign（服务端用 pay_key 签）。

    ⚠️ 拼接方式以官方文档核对后再上线；此处先按「HMAC-SHA256(pay_key, JSON(signData))」占位，
    保证前端拿到完整参数结构，联调时只改这一处。
    """
    pay_key = get_config(conn, "wxpay_pay_key", "")
    payload = json.dumps(sign_data, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(pay_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def query_order(conn, out_trade_no: str) -> dict:
    """调 /xpay/query_order 查单对账。返回微信原始应答（errcode=0 视为成功）。"""
    uri = "/xpay/query_order"
    body = {"out_trade_no": out_trade_no}
    token = _access_token(conn)
    qs = urllib.parse.urlencode({
        "access_token": token,
        "pay_sig": _pay_sig(conn, uri, body),
    })
    req = urllib.request.Request(
        f"{_API}{uri}?{qs}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode())
