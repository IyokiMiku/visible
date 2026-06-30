"""LLM 调用（阶段四 shared/ai，源 config_io.call_api 去硬编码）。

key/base_url/model 全部来自 config.get_llm_config()，源码无明文。
无 key 时抛出 LLMNotConfigured，由调用方决定降级或报错。
"""
from __future__ import annotations

from typing import Any

import config


class LLMNotConfigured(RuntimeError):
    """未配置 LLM api_key。"""


def is_configured() -> bool:
    return bool(config.get_llm_config().get("api_key"))


def call_api(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: str | None = None,
) -> str:
    """调用 Chat Completions，返回文本内容。"""
    cfg = config.get_llm_config()
    if not cfg.get("api_key"):
        raise LLMNotConfigured("未配置 LLM api_key（请在全局设置或 .env 填写 LLM_API_KEY）")

    from openai import OpenAI

    client = OpenAI(api_key=cfg["api_key"], base_url=cfg.get("base_url") or None)
    resp = client.chat.completions.create(
        model=model or cfg.get("model") or "gpt-4o",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def complete(prompt: str, *, system: str = "", **kwargs: Any) -> str:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return call_api(messages, **kwargs)
