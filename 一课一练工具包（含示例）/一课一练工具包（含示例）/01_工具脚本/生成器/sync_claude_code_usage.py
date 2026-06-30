"""同步 Claude Code 对话 token 用量到项目 .token_usage.json。

Claude Code 会把每次模型响应写入本机 transcript JSONL，其中 assistant 消息包含 usage。
本脚本读取当前会话或最近会话的 transcript，只追加尚未同步过的 assistant usage，
并把它们单独累计到 .token_usage.json 的 claude_code 分组。
"""
import json
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "02_配置资源" / "config.json"
USAGE_FILE = BASE_DIR / ".token_usage.json"
CLAUDE_PROJECT_DIR = Path.home() / ".claude" / "projects" / "C--Users-zxxk-Desktop-wyy"


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _new_bucket(currency="元"):
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "api_calls": 0,
        "prompt_cost": 0.0,
        "completion_cost": 0.0,
        "total_cost": 0.0,
        "currency": currency,
    }


def _ensure_bucket(bucket, currency="元"):
    bucket.setdefault("prompt_tokens", 0)
    bucket.setdefault("completion_tokens", 0)
    bucket.setdefault("total_tokens", bucket.get("prompt_tokens", 0) + bucket.get("completion_tokens", 0))
    bucket.setdefault("api_calls", 0)
    bucket.setdefault("prompt_cost", 0.0)
    bucket.setdefault("completion_cost", 0.0)
    bucket.setdefault("total_cost", bucket.get("prompt_cost", 0.0) + bucket.get("completion_cost", 0.0))
    bucket.setdefault("currency", currency)
    return bucket


def _ensure_usage_root(data, config):
    today = time.strftime("%Y-%m-%d")
    currency = config.get("token_price_currency", "元")
    if data.get("date") != today:
        data = {"date": today}

    # 兼容旧版：旧 top-level 统计视为“生成试卷 API”。
    if "paper_generation" not in data:
        data["paper_generation"] = {
            "prompt_tokens": data.get("prompt_tokens", 0),
            "completion_tokens": data.get("completion_tokens", 0),
            "total_tokens": data.get("total_tokens", 0),
            "api_calls": data.get("api_calls", 0),
            "prompt_cost": data.get("prompt_cost", 0.0),
            "completion_cost": data.get("completion_cost", 0.0),
            "total_cost": data.get("total_cost", 0.0),
            "currency": data.get("currency", currency),
        }

    data["paper_generation"] = _ensure_bucket(data.get("paper_generation", {}), currency)
    data["claude_code"] = _ensure_bucket(data.get("claude_code", {}), currency)
    data["claude_code"].setdefault("cache_creation_input_tokens", 0)
    data["claude_code"].setdefault("cache_read_input_tokens", 0)
    data["claude_code"].setdefault("uncached_input_tokens", 0)
    data["claude_code"].setdefault("synced_message_uuids", [])
    data["claude_code"].setdefault("synced_transcripts", {})
    data["currency"] = currency
    return data


def _pricing(config):
    currency = config.get("token_price_currency", "元")
    input_price = float(config.get("claude_code_input_price_per_1m_tokens", config.get("input_price_per_1m_tokens", 0)) or 0)
    output_price = float(config.get("claude_code_output_price_per_1m_tokens", config.get("output_price_per_1m_tokens", 0)) or 0)
    cache_creation_price = float(config.get("claude_code_cache_creation_price_per_1m_tokens", input_price) or 0)
    cache_read_price = float(config.get("claude_code_cache_read_price_per_1m_tokens", input_price) or 0)
    return input_price, output_price, cache_creation_price, cache_read_price, currency


def _find_transcript(session_id):
    if session_id:
        path = CLAUDE_PROJECT_DIR / f"{session_id}.jsonl"
        if path.exists():
            return path
    files = list(CLAUDE_PROJECT_DIR.glob("*.jsonl"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def _read_hook_session_id():
    try:
        raw = sys.stdin.read()
        if raw.strip():
            payload = json.loads(raw)
            return payload.get("session_id") or payload.get("sessionId")
    except Exception:
        pass
    return None


def _rollup_totals(data):
    paper = _ensure_bucket(data.get("paper_generation", {}), data.get("currency", "元"))
    chat = _ensure_bucket(data.get("claude_code", {}), data.get("currency", "元"))
    data["prompt_tokens"] = paper["prompt_tokens"] + chat["prompt_tokens"]
    data["completion_tokens"] = paper["completion_tokens"] + chat["completion_tokens"]
    data["total_tokens"] = paper["total_tokens"] + chat["total_tokens"]
    data["api_calls"] = paper["api_calls"] + chat["api_calls"]
    data["prompt_cost"] = paper["prompt_cost"] + chat["prompt_cost"]
    data["completion_cost"] = paper["completion_cost"] + chat["completion_cost"]
    data["total_cost"] = paper["total_cost"] + chat["total_cost"]


def sync_claude_code_usage(session_id=None):
    config = _load_json(CONFIG_PATH, {})
    usage_data = _ensure_usage_root(_load_json(USAGE_FILE, {}), config)
    transcript = _find_transcript(session_id)
    if not transcript:
        return 0

    chat = usage_data["claude_code"]
    synced = set(chat.get("synced_message_uuids", []))
    input_price, output_price, cache_creation_price, cache_read_price, currency = _pricing(config)

    added = 0
    try:
        with open(transcript, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if item.get("type") != "assistant" or item.get("isSidechain"):
                    continue
                uuid = item.get("uuid")
                if not uuid or uuid in synced:
                    continue
                message = item.get("message") or {}
                u = message.get("usage") or {}
                if not u:
                    continue

                uncached_input = u.get("input_tokens", 0) or 0
                cache_creation = u.get("cache_creation_input_tokens", 0) or 0
                cache_read = u.get("cache_read_input_tokens", 0) or 0
                output_tokens = u.get("output_tokens", 0) or 0
                prompt_tokens = uncached_input + cache_creation + cache_read
                total_tokens = prompt_tokens + output_tokens

                prompt_cost = (
                    uncached_input / 1_000_000 * input_price
                    + cache_creation / 1_000_000 * cache_creation_price
                    + cache_read / 1_000_000 * cache_read_price
                )
                completion_cost = output_tokens / 1_000_000 * output_price

                chat["uncached_input_tokens"] += uncached_input
                chat["cache_creation_input_tokens"] += cache_creation
                chat["cache_read_input_tokens"] += cache_read
                chat["prompt_tokens"] += prompt_tokens
                chat["completion_tokens"] += output_tokens
                chat["total_tokens"] += total_tokens
                chat["api_calls"] += 1
                chat["prompt_cost"] += prompt_cost
                chat["completion_cost"] += completion_cost
                chat["total_cost"] += prompt_cost + completion_cost
                chat["currency"] = currency
                synced.add(uuid)
                added += 1
    except FileNotFoundError:
        return 0

    chat["synced_message_uuids"] = sorted(synced)
    chat["synced_transcripts"][transcript.name] = {
        "last_synced_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "synced_message_count": sum(1 for x in synced),
    }
    _rollup_totals(usage_data)
    _save_json(USAGE_FILE, usage_data)
    return added


if __name__ == "__main__":
    sid = None
    if "--session-id" in sys.argv:
        idx = sys.argv.index("--session-id")
        if idx + 1 < len(sys.argv):
            sid = sys.argv[idx + 1]
    sid = sid or _read_hook_session_id()
    count = sync_claude_code_usage(sid)
    print(json.dumps({"systemMessage": f"已同步 Claude Code 对话 token：新增 {count} 条模型响应。", "suppressOutput": True}, ensure_ascii=False))
