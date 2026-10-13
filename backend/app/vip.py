# -*- coding: utf-8 -*-
"""
会员（VIP）核心逻辑：配置读取、会员态判定、免费额度、历史回看限制。

所有可调参数都在 configs 表（管理后台「系统配置」页可改，改完即生效）：
  vip_enabled   '1' 开启会员体系 / '0' 关闭（关闭 = 一切限制解除，全免费）
  vip_pay_mode  'mock' 沙箱模式（下单即开通，联调用）/ 'wxpay' 微信虚拟支付
  free_quota    JSON 免费额度：{"recipes":20,"ingredients":50,"shops":10,"tips":10,
                              "records_view_days":60,"weights_view_days":90}
  vip_plans     JSON 套餐：{"monthly":{"name":"连续包月","price_fen":600,"days":30},
                           "yearly":{"name":"年卡","price_fen":4500,"days":365}}

会员数据放独立的 vip_members 表 —— 不动 users 表结构：
init_db 对「列集合与 SCHEMA 不一致」的表是整表删除重建的，
往 users 上加列会导致线上用户数据（登录关系/角色）被清空。
"""
import time
from typing import Optional

from fastapi import Depends, HTTPException

from .db import get_db, jload
from .routers.configs import get_config

# 额度维度 ↔ 计数 SQL（只数「自己创建」的；管理员的公共层不计入）
_KIND_COUNT_SQL = {
    "recipes": "SELECT COUNT(*) FROM recipes WHERE user_id=? AND source='my'",
    "ingredients": "SELECT COUNT(*) FROM ingredients WHERE user_id=? AND scope='user'",
    "shops": "SELECT COUNT(*) FROM shops WHERE user_id=?",
    "tips": "SELECT COUNT(*) FROM tips WHERE user_id=?",
}


def get_vip_cfg(conn) -> dict:
    """读会员相关配置，JSON 字段解析失败时回退默认值（配置写坏了不至于全站崩）。"""
    enabled = get_config(conn, "vip_enabled", "0") == "1"
    pay_mode = get_config(conn, "vip_pay_mode", "mock")
    quota = jload(get_config(conn, "free_quota", ""), {}) or {
        "recipes": 20, "ingredients": 50, "shops": 10, "tips": 10,
        "records_view_days": 60, "weights_view_days": 90,
    }
    plans = jload(get_config(conn, "vip_plans", ""), {}) or {}
    return {"enabled": enabled, "pay_mode": pay_mode, "quota": quota, "plans": plans}


def is_admin(conn, uid: int) -> bool:
    if uid <= 0:
        return False
    row = conn.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    return bool(row and row["role"] == "admin")


def member_until(conn, uid: int) -> int:
    """会员到期时间戳（秒）；非会员/游客返回 0。"""
    if uid <= 0:
        return 0
    row = conn.execute("SELECT expires_at FROM vip_members WHERE user_id=?", (uid,)).fetchone()
    return int(row["expires_at"]) if row else 0


def is_member(conn, uid: int) -> bool:
    return member_until(conn, uid) > int(time.time())


def check_quota(conn, uid: int, kind: str) -> None:
    """新增前额度校验：超了直接 403（detail.code=VIP_REQUIRED，前端统一拦截引导）。

    放行条件：会员功能未开启 / 管理员 / 已是会员 / 额度未用完。
    """
    if uid <= 0:
        return  # 未登录用户走不到写接口（get_write_user 已拦），这里兜底不拦
    cfg = get_vip_cfg(conn)
    if not cfg["enabled"] or is_member(conn, uid) or is_admin(conn, uid):
        return
    max_n = cfg["quota"].get(kind)
    if not max_n or max_n <= 0:   # 没配额度或 0 = 不限
        return
    used = conn.execute(_KIND_COUNT_SQL[kind], (uid,)).fetchone()[0]
    if used >= max_n:
        raise HTTPException(
            status_code=403,
            detail={"code": "VIP_REQUIRED", "kind": kind, "used": used, "max": max_n,
                    "msg": f"免费额度已用完（{used}/{max_n}），开通会员无限量使用"},
        )


def require_quota(kind: str):
    """（保留占位）额度依赖工厂——当前各写接口在函数体内直调 check_quota，更直观。"""
    raise NotImplementedError


def view_days(conn, uid: int, kind: str) -> Optional[int]:
    """历史回看限制（天）：None = 不限；非会员返回配置的天数。

    kind ∈ records_view_days / weights_view_days（对应 free_quota 里的键）。
    """
    if uid <= 0:
        return None  # 游客本来就是空态，无需限制
    cfg = get_vip_cfg(conn)
    if not cfg["enabled"] or is_member(conn, uid) or is_admin(conn, uid):
        return None
    return cfg["quota"].get(kind) or None


def view_cutoff(conn, uid: int, kind: str) -> Optional[str]:
    """回看截止日期 'YYYY-MM-DD'（含当天）；None = 不限。读接口用 date >= cutoff 过滤。"""
    days = view_days(conn, uid, kind)
    if not days:
        return None
    import datetime
    d = datetime.date.today() - datetime.timedelta(days=days)
    return d.isoformat()


def quota_usage(conn, uid: int) -> dict:
    """各维度额度使用情况（会员页/管理端展示用）。返回 {"recipes": {"used":3,"max":20}, ...}。"""
    cfg = get_vip_cfg(conn)
    usage = {}
    for kind, sql in _KIND_COUNT_SQL.items():
        used = conn.execute(sql, (uid,)).fetchone()[0] if uid > 0 else 0
        usage[kind] = {"used": used, "max": cfg["quota"].get(kind)}
    return usage


def extend_member(conn, uid: int, days: int) -> int:
    """开通/续费：从「当前到期」或「现在」中较晚者起加 days 天（续费叠加不缩水）。返回新到期。"""
    now = int(time.time())
    base = max(now, member_until(conn, uid))
    new_until = base + int(days) * 86400
    conn.execute(
        "INSERT INTO vip_members(user_id, expires_at, updated_at) VALUES(?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET expires_at=excluded.expires_at, updated_at=excluded.updated_at",
        (uid, new_until, now),
    )
    return new_until
