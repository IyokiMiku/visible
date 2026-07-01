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
    """调用 Chat Completions，返回文本内容。

    若处于流程追踪上下文（trace.begin 已开启），会把本次调用的 prompt/响应/用量落盘，供排查。
    """
    import time as _time

    from . import trace

    cfg = config.get_llm_config()
    if not cfg.get("api_key"):
        raise LLMNotConfigured("未配置 LLM api_key（请在全局设置或 .env 填写 LLM_API_KEY）")

    import openai
    from openai import OpenAI

    from shared.config_errors import ConfigError

    used_model = model or cfg.get("model") or "gpt-4o"
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg.get("base_url") or None)
    t0 = _time.monotonic()

    def _elapsed_ms() -> int:
        return int((_time.monotonic() - t0) * 1000)

    def _log(response: str | None = None, error: str | None = None, usage: Any = None) -> None:
        try:
            trace.log_call(
                messages=messages, response=response, error=error, model=used_model,
                temperature=temperature, max_tokens=max_tokens, usage=usage,
                elapsed_ms=_elapsed_ms(),
            )
        except Exception:  # noqa: BLE001 - 追踪失败绝不能影响主流程
            pass

    try:
        resp = client.chat.completions.create(
            model=used_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except openai.AuthenticationError as e:
        _log(error=f"AuthenticationError: {e}")
        raise ConfigError("llm", "api_key", "大模型 API 密钥无效或已过期，请在全局设置检查") from e
    except openai.APIConnectionError as e:
        _log(error=f"APIConnectionError: {e}")
        raise ConfigError("llm", "base_url", "无法连接大模型接口地址，请检查 base_url 或网络") from e
    except openai.NotFoundError as e:
        _log(error=f"NotFoundError: {e}")
        raise ConfigError("llm", "model", "大模型名称不存在或不可用，请检查 model") from e
    except openai.OpenAIError as e:
        _log(error=f"OpenAIError: {e}")
        raise ConfigError("llm", None, f"大模型调用失败：{e}") from e

    content = resp.choices[0].message.content or ""
    usage = None
    try:
        if resp.usage is not None:
            usage = resp.usage.model_dump() if hasattr(resp.usage, "model_dump") else dict(resp.usage)
    except Exception:  # noqa: BLE001
        usage = None
    _log(response=content, usage=usage)
    return content


def complete(prompt: str, *, system: str = "", **kwargs: Any) -> str:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return call_api(messages, **kwargs)
