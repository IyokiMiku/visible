"""ShuangxiDriver（考点双析卷，阶段六 6.3）。

规划/映射/2×拉题借考纲共享；assemble 走奇偶拆分（偶→教师、奇→学生，4 份）。
"""
from __future__ import annotations

from pathlib import Path

from engine.drivers.base import PaperQuestions
from engine.drivers.common import CommonDriver
from engine.steps import split as step_split


class ShuangxiDriver(CommonDriver):
    type = "shuangxi"
    flow_nodes = ["读取资料", "解析考纲", "生成规划", "知识点匹配", "拉题与补题", "奇偶分卷", "质检导出", "内容审阅", "格式装配"]

    def assemble(self, ctx, paper_no: int, qs: PaperQuestions) -> list[Path]:
        # paper_no 作为 seq：教师卷号=seq*2-1、学生卷号=seq*2
        return step_split.assemble_split(ctx, paper_no, qs)
