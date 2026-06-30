"""题目规范化处理。"""
from __future__ import annotations

import re
from typing import Any


def strip_html_noise(text: str) -> str:
    """清理 HTML 标签、连续空白和常见网页噪声。"""
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_question(raw: dict[str, Any]) -> dict[str, Any]:
    """将 API 返回题目整理为统一字段。"""
    options = raw.get("options") or []
    if isinstance(options, str):
        options = [line.strip() for line in options.splitlines() if line.strip()]
    return {
        "source_url": raw.get("source_url", ""),
        "question_type": str(raw.get("question_type", "")).strip(),
        "stem": strip_html_noise(str(raw.get("stem", ""))),
        "options": [strip_html_noise(str(option)) for option in options],
        "answer": strip_html_noise(str(raw.get("answer", ""))),
        "analysis": strip_html_noise(str(raw.get("analysis", ""))),
        "knowledge_points": raw.get("knowledge_points") or [],
        "status": "normalized",
        "issues": [],
    }
