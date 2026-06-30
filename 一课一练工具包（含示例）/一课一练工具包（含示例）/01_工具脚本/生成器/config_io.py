"""配置、规范、API 与 token 用量工具。"""
import json
import time

from .paths import CONFIG_PATH, SPEC_PATH, USAGE_FILE as _USAGE_FILE

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_spec():
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        return f.read()

def _load_daily_usage():
    """加载当天的累计 token 用量"""
    today = time.strftime("%Y-%m-%d")
    if _USAGE_FILE.exists():
        try:
            with open(_USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") == today:
                _ensure_usage_fields(data)
                return data
        except (json.JSONDecodeError, KeyError):
            pass
    return _new_usage_summary(today)


def _new_usage_summary(date=None, config=None):
    """创建 token 用量统计结构。"""
    currency = (config or {}).get("token_price_currency", "元")
    empty = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "api_calls": 0,
        "prompt_cost": 0.0,
        "completion_cost": 0.0,
        "total_cost": 0.0,
        "currency": currency,
    }
    return {
        "date": date or time.strftime("%Y-%m-%d"),
        **empty,
        "paper_generation": dict(empty),
        "claude_code": {
            **empty,
            "uncached_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "synced_message_uuids": [],
            "synced_transcripts": {},
        },
    }


def _ensure_usage_fields(usage, config=None):
    """兼容旧版 .token_usage.json，补齐花费字段。"""
    currency = (config or {}).get("token_price_currency", usage.get("currency", "元"))

    def ensure_bucket(bucket):
        bucket.setdefault("prompt_tokens", 0)
        bucket.setdefault("completion_tokens", 0)
        bucket.setdefault("total_tokens", bucket.get("prompt_tokens", 0) + bucket.get("completion_tokens", 0))
        bucket.setdefault("api_calls", 0)
        bucket.setdefault("prompt_cost", 0.0)
        bucket.setdefault("completion_cost", 0.0)
        bucket.setdefault("total_cost", bucket.get("prompt_cost", 0.0) + bucket.get("completion_cost", 0.0))
        bucket.setdefault("currency", currency)
        return bucket

    if "paper_generation" not in usage:
        usage["paper_generation"] = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "api_calls": usage.get("api_calls", 0),
            "prompt_cost": usage.get("prompt_cost", 0.0),
            "completion_cost": usage.get("completion_cost", 0.0),
            "total_cost": usage.get("total_cost", 0.0),
            "currency": usage.get("currency", currency),
        }
    usage["paper_generation"] = ensure_bucket(usage.get("paper_generation", {}))
    usage["claude_code"] = ensure_bucket(usage.get("claude_code", {}))
    usage["claude_code"].setdefault("uncached_input_tokens", 0)
    usage["claude_code"].setdefault("cache_creation_input_tokens", 0)
    usage["claude_code"].setdefault("cache_read_input_tokens", 0)
    usage["claude_code"].setdefault("synced_message_uuids", [])
    usage["claude_code"].setdefault("synced_transcripts", {})

    paper = usage["paper_generation"]
    chat = usage["claude_code"]
    usage["prompt_tokens"] = paper["prompt_tokens"] + chat["prompt_tokens"]
    usage["completion_tokens"] = paper["completion_tokens"] + chat["completion_tokens"]
    usage["total_tokens"] = paper["total_tokens"] + chat["total_tokens"]
    usage["api_calls"] = paper["api_calls"] + chat["api_calls"]
    usage["prompt_cost"] = paper["prompt_cost"] + chat["prompt_cost"]
    usage["completion_cost"] = paper["completion_cost"] + chat["completion_cost"]
    usage["total_cost"] = paper["total_cost"] + chat["total_cost"]
    usage["currency"] = currency
    return usage


def _token_pricing(config):
    """读取每百万 token 单价：输入/上传与输出/下载可分别配置。"""
    config = config or {}
    input_price = config.get("input_price_per_1m_tokens", config.get("prompt_price_per_1m_tokens", 0))
    output_price = config.get("output_price_per_1m_tokens", config.get("completion_price_per_1m_tokens", 0))
    return float(input_price or 0), float(output_price or 0), config.get("token_price_currency", "元")


def _record_token_usage(session_usage, daily_usage, usage, config=None):
    """累计一次 API 返回的 token 用量，并按配置的单价计算花费。"""
    if not usage:
        return {"prompt_cost": 0.0, "completion_cost": 0.0, "total_cost": 0.0}

    _ensure_usage_fields(session_usage, config)
    _ensure_usage_fields(daily_usage, config)

    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    total_tokens = usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)
    input_price, output_price, currency = _token_pricing(config)
    prompt_cost = prompt_tokens / 1_000_000 * input_price
    completion_cost = completion_tokens / 1_000_000 * output_price
    total_cost = prompt_cost + completion_cost

    for target in (session_usage, daily_usage):
        bucket = target.setdefault("paper_generation", {})
        bucket.setdefault("prompt_tokens", 0)
        bucket.setdefault("completion_tokens", 0)
        bucket.setdefault("total_tokens", 0)
        bucket.setdefault("api_calls", 0)
        bucket.setdefault("prompt_cost", 0.0)
        bucket.setdefault("completion_cost", 0.0)
        bucket.setdefault("total_cost", 0.0)
        bucket.setdefault("currency", currency)
        bucket["prompt_tokens"] += prompt_tokens
        bucket["completion_tokens"] += completion_tokens
        bucket["total_tokens"] += total_tokens
        bucket["api_calls"] += 1
        bucket["prompt_cost"] += prompt_cost
        bucket["completion_cost"] += completion_cost
        bucket["total_cost"] += total_cost
        bucket["currency"] = currency
        _ensure_usage_fields(target, config)

    _save_daily_usage(daily_usage)
    return {"prompt_cost": prompt_cost, "completion_cost": completion_cost, "total_cost": total_cost, "currency": currency}

def _save_daily_usage(usage):
    """保存当天的累计 token 用量"""
    with open(_USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(usage, f, ensure_ascii=False)

def _print_token_summary(session_usage, daily_usage):
    """打印 token 用量汇总"""
    _ensure_usage_fields(session_usage)
    _ensure_usage_fields(daily_usage)
    session_currency = session_usage.get("currency", "元")
    daily_currency = daily_usage.get("currency", session_currency)

    def print_bucket(title, bucket, currency):
        print(f"  {title}:")
        print(f"    输入/上传: {bucket['prompt_tokens']:,} tokens")
        print(f"    输出/下载: {bucket['completion_tokens']:,} tokens")
        print(f"    合计: {bucket['total_tokens']:,} tokens ({bucket['api_calls']} 次调用)")
        print(f"    费用: {bucket['total_cost']:.4f} {currency} "
              f"(输入 {bucket['prompt_cost']:.4f} + 输出 {bucket['completion_cost']:.4f})")

    print(f"\n{'─' * 40}")
    print_bucket("本次会话生成试卷 API Token 消耗", session_usage["paper_generation"], session_currency)
    if session_usage.get("claude_code", {}).get("api_calls", 0):
        print_bucket("本次会话 Claude Code 对话 Token 消耗", session_usage["claude_code"], session_currency)
    print_bucket("本次会话总 Token 消耗", session_usage, session_currency)
    print_bucket("今日累计生成试卷 API Token 消耗", daily_usage["paper_generation"], daily_currency)
    print_bucket("今日累计 Claude Code 对话 Token 消耗", daily_usage["claude_code"], daily_currency)
    print_bucket("今日累计总 Token 消耗", daily_usage, daily_currency)
    print(f"{'─' * 40}")

def call_api(client, model, system_prompt, user_prompt, max_tokens=8000, temperature=0.7):
    """调用 OpenAI 兼容 API（支持 Claude 代理），返回 (文本, usage_dict)"""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            # 提取 token 用量
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) or 0,
                    "completion_tokens": getattr(response.usage, 'completion_tokens', 0) or 0,
                    "total_tokens": getattr(response.usage, 'total_tokens', 0) or 0,
                }
            return response.choices[0].message.content, usage
        except Exception as e:
            print(f"  [!] API 调用失败 (第{attempt+1}次): {e}")
            if attempt < 2:
                wait = (attempt + 1) * 10
                print(f"      等待 {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise
