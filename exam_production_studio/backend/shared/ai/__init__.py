"""shared/ai：LLM 调用 / 补题 / 映射表生成。"""
from .llm import call_api, complete, is_configured, LLMNotConfigured
from .fill import ai_fill, parse_paper_text
from .mapping import generate_mapping
from .prompts import build_generation_prompt

__all__ = [
    "call_api", "complete", "is_configured", "LLMNotConfigured",
    "ai_fill", "parse_paper_text", "generate_mapping", "build_generation_prompt",
]
