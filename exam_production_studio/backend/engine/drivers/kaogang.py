"""KaogangDriver（考纲百套卷，阶段六 6.1）。含细目表；拉题 ×1。"""
from __future__ import annotations

from pathlib import Path

from engine.drivers.common import CommonDriver
from engine.steps import mesh as step_mesh


class KaogangDriver(CommonDriver):
    type = "kaogang_100"
    flow_nodes = ["读取资料", "解析考纲", "生成规划", "知识点匹配", "细目表", "拉题与补题", "质检导出"]

    def gen_mesh(self, ctx) -> list[Path]:
        return step_mesh.gen_mesh(ctx)
