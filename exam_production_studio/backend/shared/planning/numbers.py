"""中文数字与标题序号处理（阶段 C4，移植旧工具 _number_to_cn / _strip_unit_title 思路）。"""
from __future__ import annotations

import re

_CN_DIGITS = "零一二三四五六七八九"
_CN_UNITS = ["", "十", "百"]

# 一级/二级标题上的既有序号前缀，生成标题时需剥离后重新按层级编号
_LEADING_ORDER = re.compile(
    r"^\s*(?:"
    r"第\s*[一二三四五六七八九十百零\d]+\s*(?:单元|章节|章|节|篇|部分|部|课|讲)"  # 第1章 / 第一单元 / 第3节
    r"|[一二三四五六七八九十]+\s*[、.．]"                          # 一、 二．
    r"|[（(]\s*[一二三四五六七八九十\d]+\s*[)）]"                  # （一） (1)
    r"|\d+\s*[．.、]\s*"                                           # 1. 2、
    r"|\d+\.\d+\s*"                                                # 1.1
    r")\s*"
)


def number_to_cn(n: int) -> str:
    """1..99 → 一..九十九（用于第X单元/第X章/第X节）。超范围回退阿拉伯。"""
    if n <= 0 or n >= 100:
        return str(n)
    if n < 10:
        return _CN_DIGITS[n]
    tens, ones = divmod(n, 10)
    s = ("" if tens == 1 else _CN_DIGITS[tens]) + "十"
    if ones:
        s += _CN_DIGITS[ones]
    return s


def strip_leading_order(title: str) -> str:
    """剥离标题开头的层级/条目编号（第1章 / 一、/（一）/1. 等），保留纯名称。"""
    if not title:
        return ""
    s = str(title).strip()
    prev = None
    # 可能叠加（如「第1章 一、xxx」少见但稳妥起见循环剥离一次层级 + 一次条目）
    while s and s != prev:
        prev = s
        s = _LEADING_ORDER.sub("", s, count=1).strip()
    return s or str(title).strip()
