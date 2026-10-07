# -*- coding: utf-8 -*-
"""
SMTP 发邮件服务：标准库 smtplib + email.message，零依赖。
配置全部从 configs 表读（smtp_host / smtp_port / smtp_user / smtp_pass / smtp_from）。
没配或发失败 → 降级到后端日志打印验证码，开发期可用。
"""
import logging
import random
import smtplib
import time
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

logger = logging.getLogger(__name__)


def _get_cfg(conn) -> dict:
    """从 configs 表读 SMTP 配置，返回 dict。"""
    rows = conn.execute(
        "SELECT key, value FROM configs WHERE key IN ("
        "'smtp_host','smtp_port','smtp_user','smtp_pass','smtp_from','otp_expire_min')"
    ).fetchall()
    cfg = {r["key"]: r["value"] for r in rows}
    # 端口转 int
    try:
        cfg["smtp_port"] = int(cfg.get("smtp_port") or 465)
    except ValueError:
        cfg["smtp_port"] = 465
    try:
        cfg["otp_expire_min"] = int(cfg.get("otp_expire_min") or 10)
    except ValueError:
        cfg["otp_expire_min"] = 10
    return cfg


def is_smtp_configured(conn) -> bool:
    """SMTP 是否完整配置（host + user + pass）。"""
    cfg = _get_cfg(conn)
    return bool(cfg.get("smtp_host") and cfg.get("smtp_user") and cfg.get("smtp_pass"))


def generate_otp() -> str:
    """生成 6 位数字验证码。"""
    return f"{random.randint(0, 999999):06d}"


def send_otp_email(conn, to_email: str, code: str, purpose: str = "login") -> bool:
    """
    发送验证码邮件。成功返回 True，失败降级到日志打印也返回 True（开发期友好）。
    purpose: login | bind | reset — 决定邮件文案
    """
    cfg = _get_cfg(conn)
    expire_min = cfg.get("otp_expire_min", 10)

    # 邮件文案
    purpose_text = {
        "login": "登录「吃啥好呀」",
        "bind": "绑定邮箱到「吃啥好呀」账号",
        "reset": "重置「吃啥好呀」密码",
    }.get(purpose, "验证「吃啥好呀」操作")

    body = (
        f"您好！\n\n"
        f"您正在{purpose_text}，验证码是：\n\n"
        f"    【{code}】\n\n"
        f"验证码 {expire_min} 分钟内有效，请勿泄露给他人。\n"
        f"如果不是您本人操作，请忽略此邮件。\n\n"
        f"——吃啥好呀 Team 🧑‍🍳"
    )

    # 没配 SMTP → 日志打印（开发期能用）
    if not is_smtp_configured(conn):
        logger.warning(
            "[email] SMTP 未配置，验证码仅打印日志。"
            f" to={to_email} purpose={purpose} code={code}"
        )
        print(f"📧 [OTP] to={to_email} purpose={purpose} code={code}")
        return True

    # 正常发邮件
    try:
        msg = MIMEText(body, "plain", "utf-8")
        from_name = cfg.get("smtp_from") or cfg.get("smtp_user", "")
        # From 必须用 formataddr 拼装。
        # 踩过的坑：写成 f"{Header(name, 'utf-8')} <{addr}>" 时，Header.__str__ 返回的是
        # 「原文」而不是 encoded-word，于是这个带中文的整串交给 policy 序列化时会被整体
        # base64 成一个 encoded-word，把 <地址> 也吞进去（From: =?utf-8?b?...?=），
        # 地址结构被破坏 → QQ 回 550 The "From" header is missing or invalid。
        # formataddr 只对显示名做 RFC2047 编码，地址保持裸露，格式才合法。
        msg["From"] = formataddr((from_name, cfg["smtp_user"]))
        msg["To"] = to_email
        msg["Subject"] = Header(f"【吃啥好呀】验证码 {code}", "utf-8")

        host = cfg["smtp_host"]
        port = cfg["smtp_port"]
        user = cfg["smtp_user"]
        pwd = cfg["smtp_pass"]

        # 465 = SSL；587 / 25 = STARTTLS
        if port == 465:
            smtp = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            smtp = smtplib.SMTP(host, port, timeout=10)
            smtp.starttls()

        smtp.login(user, pwd)
        smtp.sendmail(user, [to_email], msg.as_string())
        smtp.quit()
        logger.info(f"[email] OTP sent to={to_email} purpose={purpose}")
        return True
    except Exception as e:
        # 发失败 → 降级日志
        logger.warning(f"[email] SMTP 发件失败，降级日志。to={to_email} err={e}")
        print(f"📧 [OTP FALLBACK] to={to_email} purpose={purpose} code={code}  (SMTP err: {e})")
        return True  # 对调用方来说，验证码已生成并入库，只是没发出去
