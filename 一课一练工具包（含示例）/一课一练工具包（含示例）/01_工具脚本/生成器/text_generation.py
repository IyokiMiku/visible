"""分批生成辅助。"""
import re

from .config_io import _save_daily_usage, call_api
from .prompts import build_generation_prompt
from .text_processing import _extract_question_summaries

BATCH_SIZE = 5

def generate_paper_in_batches(client, model, meta, topic, set_idx, spec_text, config,
                              session_usage=None, daily_usage=None):
    """分批生成试卷：每 BATCH_SIZE 道题为一批，累积摘要传入下一批防止重复

    流程：
      1. 第1批：正常生成前 N 道题
      2. 提取已生成题目的摘要
      3. 第2批：将摘要注入 prompt，AI 生成剩余题目时会避开已有内容
      4. 合并所有批次的结果

    Returns:
        (paper_text, total_usage) 或 (None, None) 失败时
    """
    # 计算总题数
    qt_str = topic["question_types"]
    total_questions = 0
    for m in re.finditer(r'(\d+)', qt_str):
        total_questions += int(m.group(1))

    # 如果总题数 <= BATCH_SIZE，不需要分批，一次生成
    if total_questions <= BATCH_SIZE:
        sys_prompt, user_prompt = build_generation_prompt(meta, topic, set_idx, spec_text)
        paper_text, usage = call_api(
            client, model, sys_prompt, user_prompt,
            max_tokens=config.get("max_tokens", 8000),
            temperature=config.get("temperature", 0.7),
        )
        if session_usage and usage:
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                session_usage[key] += usage.get(key, 0)
            session_usage["api_calls"] += 1
        if daily_usage and usage:
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                daily_usage[key] += usage.get(key, 0)
            daily_usage["api_calls"] += 1
            _save_daily_usage(daily_usage)
        token_info = f", {usage['total_tokens']} tokens" if usage else ""
        print(f"  API 返回成功 ({len(paper_text)}字{token_info})")
        return paper_text, usage

    # 分批生成
    all_text_parts = []
    existing_summaries = []
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    batch_num = 0

    # 第1批：生成完整试卷（AI 一次性生成所有题型）
    # 但通过摘要机制，后续重新生成时可以避开已有内容
    sys_prompt, user_prompt = build_generation_prompt(
        meta, topic, set_idx, spec_text, existing_summaries=existing_summaries or None
    )
    paper_text, usage = call_api(
        client, model, sys_prompt, user_prompt,
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.7),
    )
    batch_num += 1

    if usage:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            total_usage[key] += usage.get(key, 0)
        if session_usage:
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                session_usage[key] += usage.get(key, 0)
            session_usage["api_calls"] += 1
        if daily_usage:
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                daily_usage[key] += usage.get(key, 0)
            daily_usage["api_calls"] += 1
            _save_daily_usage(daily_usage)

    token_info = f", {usage['total_tokens']} tokens" if usage else ""
    print(f"  第{batch_num}批返回成功 ({len(paper_text)}字{token_info})")

    # 提取摘要供后续（极重要双卷的第二卷）使用
    existing_summaries = _extract_question_summaries(paper_text)

    return paper_text, total_usage
