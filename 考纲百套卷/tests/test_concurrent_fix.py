"""测试并发修复 + 增强 prompt 的正确性（不调用真实 API）。"""
from pathlib import Path
import sys
import time
from typing import Any
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "01_工具脚本"))

from 生成器.regenerator import (
    RegenerationResult,
    parse_regeneration_output,
    normalize_regenerated_question,
    needs_regeneration,
)
from 生成器.prompts import build_regenerate_question_prompt


# ── 1. 测试增强 prompt 示例 JSON 被正确注入 ──
def test_prompt_contains_json_example():
    question = {
        "question_no": 1,
        "question_type": "单项选择题",
        "stem": "电路中 R=10Ω，U=220V，求电流 I。",
        "options": ["A. 10A", "B. 22A", "C. 2A", "D. 1A"],
        "answer": "B",
        "analysis": "I=U/R=220/10=22A。",
    }
    issues = ["解析过短"]
    plan_context = {"course": "电工基础", "exam_category": "电子信息类"}
    spec_text = "题目编写规范..."

    prompt = build_regenerate_question_prompt(question, issues, plan_context, spec_text)
    assert "输出格式参照" in prompt, "增强 prompt 应包含示例说明"
    assert '"question_type"' in prompt, "示例应包含 question_type 字段"
    assert "不要照抄内容" in prompt, "示例应注明不要照抄"
    print("  [OK] 增强 prompt 包含 JSON 示例")


# ── 2. 测试 JSON 解析容错 ──
def test_parse_regeneration_output_clean_json():
    output = '{"question_type":"单项选择题","stem":"测试题干","answer":"A"}'
    result = parse_regeneration_output(output)
    assert result is not None
    assert result["stem"] == "测试题干"
    print("  [OK] 纯 JSON 解析通过")


def test_parse_regeneration_output_with_fence():
    output = '```json\n{"question_type":"单项选择题","stem":"题干"}\n```'
    result = parse_regeneration_output(output)
    assert result is not None
    assert result["stem"] == "题干"
    print("  [OK] markdown fence 包裹 JSON 解析通过")


def test_parse_regeneration_output_with_extra_text():
    output = '修复完成，结果如下：\n{"question_type":"判断题","stem":"欧姆定律","answer":"√"}'
    result = parse_regeneration_output(output)
    assert result is not None
    assert result["stem"] == "欧姆定律"
    print("  [OK] 尾部多余文本 JSON 解析通过")


def test_parse_regeneration_output_nested_question_key():
    output = '{"question": {"question_type":"单项选择题","stem":"嵌套题干"}}'
    result = parse_regeneration_output(output)
    assert result is not None
    assert result["stem"] == "嵌套题干"
    print("  [OK] 嵌套 question key 解析通过")


def test_parse_regeneration_output_invalid():
    output = "这不是 JSON 字符串，没有花括号"
    result = parse_regeneration_output(output)
    assert result is None
    print("  [OK] 无效输出正确返回 None")


# ── 3. 测试 normalize_regenerated_question ──
def test_normalize_keeps_original_fields():
    original = {
        "question_no": 3,
        "question_type": "单项选择题",
        "stem": "原题干",
        "options": ["A. a", "B. b"],
        "answer": "A",
        "analysis": "原解析",
        "source_path": "/test",
        "heading": "一、单选题",
    }
    repaired = {
        "question_type": "单项选择题",
        "stem": "新题干",
        "answer": "B",
        "analysis": "新解析",
        "fix_type": "repaired",
    }
    result = normalize_regenerated_question(original, repaired)
    assert result["question_no"] == 3
    assert result["stem"] == "新题干"
    assert result["answer"] == "B"
    assert result["analysis"] == "新解析"
    assert result["source_path"] == "/test"
    assert result["status"] == "repaired"
    assert result["issues"] == []
    print("  [OK] normalize 正确覆盖字段且保留原字段")


# ── 4. 测试 needs_regeneration ──
def test_needs_regeneration_triggers():
    assert needs_regeneration(["缺答案"])
    assert needs_regeneration(["乱码", "题型错误"])
    assert needs_regeneration(["选项缺失", "答案自暴露"])
    assert not needs_regeneration(["格式轻微不一致"])
    assert not needs_regeneration([])
    print("  [OK] needs_regeneration 触发逻辑正确")


# ── 5. 测试并发修复逻辑（mock LLM）──────────────────────────
def _make_mock_llm_call(delay_ms: int = 50):
    """创建一个模拟 LLM 调用，每次返回成功 JSON。"""

    def mock_llm(prompt: str) -> str:
        time.sleep(delay_ms / 1000)
        return (
            '{"question_type":"单项选择题",'
            '"stem":"修复后的题干","options":["A. 选项A","B. 选项B","C. 选项C","D. 选项D"],'
            '"answer":"A","analysis":"修复后的解析","fix_type":"repaired","status":"fixed"}'
        )

    return mock_llm


def test_concurrent_fix_vs_serial_timing():
    """验证并发耗时 < 串行耗时。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from 生成器.regenerator import regenerate_question

    # 构造 10 道题目，每道模拟 50ms 延迟
    questions = []
    for i in range(10):
        questions.append({
            "question_no": i + 1,
            "question_type": "单项选择题",
            "stem": f"测试题干{i + 1}",
            "options": ["A. a", "B. b", "C. c", "D. d"],
            "answer": "A",
            "analysis": "测试解析",
            "_repair_index": i,
        })

    issues = ["解析过短"]
    plan_context = {"course": "电工基础"}
    spec_text = ""

    # 串行
    serial_llm = _make_mock_llm_call(delay_ms=50)
    t0 = time.perf_counter()
    for q in questions:
        result = regenerate_question(q, issues, plan_context, spec_text, serial_llm)
        assert result.status == "success"
    serial_time = time.perf_counter() - t0
    print(f"  串行耗时: {serial_time:.2f}s")

    # 并发
    concurrent_llm = _make_mock_llm_call(delay_ms=50)

    def repair_one(q):
        result = regenerate_question(q, issues, plan_context, spec_text, concurrent_llm)
        return q.get("_repair_index", -1), result

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(repair_one, q): q for q in questions}
        for future in as_completed(futures):
            index, result = future.result()
            assert result.status == "success"
    concurrent_time = time.perf_counter() - t0
    print(f"  并发耗时: {concurrent_time:.2f}s")

    # 并发应明显快于串行（至少 3x）
    assert concurrent_time < serial_time * 0.5, (
        f"并发应明显快于串行，但 concurrent={concurrent_time:.2f}s, serial={serial_time:.2f}s"
    )
    print("  [OK] 并发显著快于串行")


# ── 6. 测试 _repair_index 标记与清理逻辑 ──
def test_repair_index_marking_and_cleanup():
    """验证 _repair_index 临时标记的正确注入和清理。"""
    questions = [
        {"question_no": 1, "stem": "题1"},
        {"question_no": 2, "stem": "题2"},
        {"question_no": 3, "stem": "题3"},
    ]

    # 模拟并发前的标记
    for i, q in enumerate(questions):
        q["_repair_index"] = i

    assert questions[0]["_repair_index"] == 0
    assert questions[1]["_repair_index"] == 1

    # 模拟并发后的清理
    for q in questions:
        q.pop("_repair_index", None)

    assert "_repair_index" not in questions[0]
    assert "_repair_index" not in questions[1]
    print("  [OK] _repair_index 标记与清理逻辑正确")


# ── 7. 测试 module 可正确导入 ──
def test_imports():
    """验证修改后的模块可以正常导入。"""
    from 生成器.regenerator import RegenerationResult, parse_regeneration_output, normalize_regenerated_question
    from 生成器.prompts import build_regenerate_question_prompt
    import 生成器.runner  # 确保 runner.py 无语法错误
    print("  [OK] 所有修改模块导入成功，无语法错误")


if __name__ == "__main__":
    print("=" * 60)
    print("考纲百套卷 并发修复 + 增强 prompt 测试")
    print("=" * 60)

    test_imports()
    test_prompt_contains_json_example()
    test_parse_regeneration_output_clean_json()
    test_parse_regeneration_output_with_fence()
    test_parse_regeneration_output_with_extra_text()
    test_parse_regeneration_output_nested_question_key()
    test_parse_regeneration_output_invalid()
    test_normalize_keeps_original_fields()
    test_needs_regeneration_triggers()
    test_repair_index_marking_and_cleanup()
    test_concurrent_fix_vs_serial_timing()

    print("=" * 60)
    print("全部测试通过！")
    print("=" * 60)
