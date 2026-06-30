"""驱动注册与获取。

注意：此处只在包初始化时导入轻量的 base（数据结构/协议）。
具体驱动（依赖 steps → shared）改为在 get_driver 内惰性导入，避免
shared.* 反向 import engine.drivers.base 时触发循环导入。
"""
from __future__ import annotations

from .base import ModeDriver, PaperQuestions, QCResult, Question

__all__ = ["get_driver", "ModeDriver", "PaperQuestions", "QCResult", "Question"]


def get_driver(ctx) -> ModeDriver:
    t = ctx.paper_type
    if t == "kaogang_100":
        from .kaogang import KaogangDriver
        return KaogangDriver()
    if t == "shuangxi":
        from .shuangxi import ShuangxiDriver
        return ShuangxiDriver()
    if t == "yikeyilian":
        from .yikeyilian import YikeyilianDriver
        return YikeyilianDriver()
    raise KeyError(f"未知试卷类型: {t}")
