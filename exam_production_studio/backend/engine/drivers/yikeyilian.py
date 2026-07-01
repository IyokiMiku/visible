"""YikeyilianDriver（一课一练，阶段六 6.2）。

教材目录扫描 + 8列规划 + 新增映射表；拉题走共享学科网，补题复用
build_generation_prompt（已封装在 shared.ai.ai_fill 内）。拉题 ×1。
"""
from __future__ import annotations

from engine.drivers.common import CommonDriver


class YikeyilianDriver(CommonDriver):
    type = "yikeyilian"
    flow_nodes = ["读取资料", "解析目录", "生成规划", "知识点匹配", "拉题与补题", "质检导出", "内容审阅", "格式装配"]
