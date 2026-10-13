# -*- coding: utf-8 -*-
"""
payments 路由：会员套餐 / 下单 / 对账 / 订单列表。

支付模式（configs: vip_pay_mode，管理后台可切）：
- mock：沙箱模式，下单即标记已付并开通 —— 本地开发与联调用，无需任何微信资质。
- wxpay：微信虚拟支付。前端拿 pay_params 调 wx.requestVirtualPayment，
  服务端以 /xpay/query_order 查单对账（官方明确：前端 success 回调可能丢失，查单为准）。

所有可调参数（开关/模式/套餐/额度）都在 configs 表，管理后台「系统配置」页维护。
"""
import random
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from ..db import get_db
from .. import wxpay
from ..vip import get_vip_cfg, is_member, member_until, extend_member, quota_usage
from .auth import get_current_user, get_optional_user

router = APIRouter(prefix="/payments", tags=["payments"])


class OrderIn(BaseModel):
    plan_id: str
    # 支付环境：0 安卓/其他，1 iOS（仅记录，用于对账分渠道费率）
    env: int = 0


def _plan_or_404(cfg: dict, plan_id: str) -> dict:
    plan = cfg["plans"].get(plan_id)
    if not plan or not plan.get("price_fen") or not plan.get("days"):
        raise HTTPException(404, f"套餐不存在或配置不完整: {plan_id}")
    return plan


def _gen_trade_no(uid: int) -> str:
    return f"EAT{uid}{int(time.time())}{random.randint(100, 999)}"


def _credit_order(conn, order: dict) -> bool:
    """把一笔已支付订单的会员时长发放到账（幂等：credited 标记防重复续期）。

    对账/回调/前端轮询可能并发或反复触发，只有第一次真正 extend。
    """
    if order["status"] != "paid" or order["credited"]:
        return False
    extend_member(conn, order["user_id"], order["plan_days"])
    conn.execute("UPDATE orders SET credited=1 WHERE id=?", (order["id"],))
    return True


@router.get("/plans")
def get_plans(user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    """会员页渲染数据：开关/模式/会员态/套餐/额度使用。游客也能看（引导登录后购买）。"""
    cfg = get_vip_cfg(conn)
    return {
        "enabled": cfg["enabled"],
        "pay_mode": cfg["pay_mode"],
        "is_member": is_member(conn, user),
        "member_until": member_until(conn, user),
        "logged_in": user > 0,
        "plans": cfg["plans"],
        "quota": quota_usage(conn, user),
    }


@router.post("/order")
def create_order(body: OrderIn,
                 uid: int = Depends(get_current_user),
                 conn: Connection = Depends(get_db)):
    """下单。mock 模式：直接开通；wxpay 模式：建 pending 单 + 返回拉起支付参数。"""
    cfg = get_vip_cfg(conn)
    if not cfg["enabled"]:
        raise HTTPException(400, "会员功能未开启")
    plan = _plan_or_404(cfg, body.plan_id)

    no = _gen_trade_no(uid)
    now = int(time.time())
    conn.execute(
        "INSERT INTO orders(user_id,out_trade_no,plan_id,price_fen,plan_days,status,env,created_at) "
        "VALUES(?,?,?,?,?,'pending',?,?)",
        (uid, no, body.plan_id, plan["price_fen"], plan["days"], 1 if body.env == 1 else 0, now),
    )

    # ---- mock：沙箱模式，下单即支付（不碰微信，联调闭环用） ----
    if cfg["pay_mode"] != "wxpay":
        conn.execute(
            "UPDATE orders SET status='paid', paid_at=?, wx_transaction_id=? WHERE out_trade_no=?",
            (int(time.time()), f"mock_{no}", no),
        )
        row = dict(conn.execute("SELECT * FROM orders WHERE out_trade_no=?", (no,)).fetchone())
        _credit_order(conn, row)
        return {"paid": True, "out_trade_no": no,
                "member_until": member_until(conn, uid), "mock": True, "ok": True}

    # ---- wxpay：真实虚拟支付 ----
    if not wxpay.configured(conn):
        raise HTTPException(400, "虚拟支付未配置（管理后台补 wxpay_offer_id / wxpay_pay_key）")
    # signData 字段以官方 wx.requestVirtualPayment 文档为准；拉起后前端轮询 /payments/order/{no}/status 对账
    sign_data = {
        "mode": "short_series_goods",          # 工具类虚拟商品
        "env": 1 if body.env == 1 else 0,
        "offerId": conn.execute("SELECT value FROM configs WHERE key='wxpay_offer_id'").fetchone()[0],
        "productId": body.plan_id,
        "outTradeNo": no,
        "buyQuantity": 1,
        "timestamp": now,
        "nonceStr": f"{random.randint(10**8, 10**9 - 1)}",
        "totalAmount": plan["price_fen"],      # 单位：分
        "currencyType": "CNY",
    }
    return {"paid": False, "out_trade_no": no, "sign_data": sign_data,
            "sign": wxpay.sign_data_signature(conn, sign_data), "ok": True}


@router.get("/order/{out_trade_no}/status")
def order_status(out_trade_no: str,
                 uid: int = Depends(get_current_user),
                 conn: Connection = Depends(get_db)):
    """查单对账：wxpay 模式先调微信 /xpay/query_order 校正本地状态，再返回订单。

    前端支付 success / fail 之后都应调一次这里，以后端状态为准。
    """
    row = conn.execute(
        "SELECT * FROM orders WHERE out_trade_no=? AND user_id=?", (out_trade_no, uid)
    ).fetchone()
    if not row:
        raise HTTPException(404, "订单不存在")
    row = dict(row)

    cfg = get_vip_cfg(conn)
    if cfg["pay_mode"] == "wxpay" and row["status"] == "pending" and wxpay.configured(conn):
        try:
            resp = wxpay.query_order(conn, out_trade_no)
            # 微信应答字段名以官方文档核对；这里按通用结构判「已支付」
            if str(resp.get("errcode", "0")) == "0" and resp.get("order_status") in (1, "PAID", "paid"):
                conn.execute(
                    "UPDATE orders SET status='paid', paid_at=?, wx_transaction_id=? WHERE id=?",
                    (int(time.time()), str(resp.get("transaction_id", "")), row["id"]),
                )
                row["status"] = "paid"
        except Exception as e:  # 查单失败不阻塞：返回本地状态，前端可重试
            row["reconcile_error"] = str(e)

    if _credit_order(conn, row):
        row["credited_now"] = True  # 本次调用完成了发放（前端据此提示开通成功）
    return row


@router.post("/notify")
def pay_notify(request: dict, conn: Connection = Depends(get_db)):
    """微信虚拟支付推送回调（报文/验签方式以微信后台配置的消息推送为准）。

    前端 success 回调可能丢失，发货以这里的推送 + /xpay/query_order 查单双保险为准。
    """
    no = str(request.get("OutTradeNo") or request.get("out_trade_no") or "")
    if not no:
        raise HTTPException(400, "缺少单号")
    row = conn.execute("SELECT * FROM orders WHERE out_trade_no=?", (no,)).fetchone()
    if not row:
        raise HTTPException(404, "订单不存在")
    if row["status"] == "pending":
        conn.execute(
            "UPDATE orders SET status='paid', paid_at=?, wx_transaction_id=? WHERE id=?",
            (int(time.time()), str(request.get("TransactionId", "")), row["id"]),
        )
        row = dict(conn.execute("SELECT * FROM orders WHERE id=?", (row["id"],)).fetchone())
        _credit_order(conn, row)
    return {"errcode": 0}  # 微信约定：回 0 表示接收成功，否则会重推


@router.get("/orders")
def my_orders(uid: int = Depends(get_current_user), conn: Connection = Depends(get_db)):
    """我的订单（最近 50 条，新的在前）。"""
    rows = conn.execute(
        "SELECT out_trade_no, plan_id, price_fen, plan_days, status, env, created_at, paid_at "
        "FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 50", (uid,)
    ).fetchall()
    return [dict(r) for r in rows]
