from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "01_工具脚本"))

from 质检.rules import (  # noqa: E402
    _check_answer_stem_leak,
    _check_formula_signature_pair,
    _check_image_context_signature_pair,
    _check_kpoint_density,
    _is_number_substitute_pair,
    check_question_structured,
)


def test_number_substitute_pair_detects_same_template_with_different_values():
    left = "电阻R1=10Ω，R2=20Ω，R3=30Ω，求总电阻"
    right = "电阻R1=15Ω，R2=25Ω，R3=35Ω，求总电阻"

    matched, reason = _is_number_substitute_pair(left, right)

    assert matched
    assert "数字" in reason


def test_answer_stem_leak_detects_cross_paper_answer_exposure():
    issues = _check_answer_stem_leak(
        [{"question_no": 1, "answer": "并联电阻总阻值小于任一支路电阻"}],
        [{"question_no": 2, "stem": "下列关于并联电阻总阻值小于任一支路电阻的说法正确的是"}],
        "A卷",
        "B卷",
    )

    assert len(issues) == 1
    assert issues[0]["code"] == "answer_stem_leak"


def test_kpoint_density_detects_repeated_kpoint_across_papers():
    issues = _check_kpoint_density(
        [{"_kpoint_ids": ["87644"]} for _ in range(3)],
        [{"_kpoint_ids": ["87644"]} for _ in range(3)],
        "A卷",
        "B卷",
    )

    assert len(issues) == 1
    assert issues[0]["code"] == "kpoint_density_high"


def test_formula_signature_detects_same_formula_structure():
    matched, reason = _check_formula_signature_pair(
        {"stem": "由{{math:I=U/R}}计算电流。"},
        {"stem": "根据{{math:A=B/C}}求未知量。"},
    )

    assert matched
    assert "公式" in reason


def test_image_context_signature_detects_same_image_question_context():
    matched, reason = _check_image_context_signature_pair(
        {"stem": "[图片]观察电路图判断开关闭合后的灯泡状态。"},
        {"stem": "[图片]观察电路图判断开关闭合后的灯泡状态。"},
    )

    assert matched
    assert "图表" in reason


def test_formula_signature_detects_plain_text_formula_structure():
    matched, reason = _check_formula_signature_pair(
        {"stem": "已知电压和电阻，按 I=U/R 计算电流。"},
        {"stem": "根据 A=B/C 求未知量。"},
    )

    assert matched
    assert "公式" in reason


def test_formula_signature_ignores_non_formula_text():
    matched, reason = _check_formula_signature_pair(
        {"stem": "下列关于安全用电的说法正确的是。"},
        {"stem": "下列关于电工工具的说法正确的是。"},
    )

    assert not matched
    assert reason == ""


def test_image_signature_prefers_same_stem_image_hash():
    matched, reason = _check_image_context_signature_pair(
        {"stem": "观察下图回答。", "image_refs": {"stem": [{"sha256": "abc123", "byte_size": 10}], "answer": [], "analysis": []}},
        {"stem": "根据图片判断。", "image_refs": {"stem": [{"sha256": "abc123", "byte_size": 10}], "answer": [], "analysis": []}},
    )

    assert matched
    assert "哈希" in reason


def test_image_signature_does_not_match_different_stem_image_hashes():
    matched, reason = _check_image_context_signature_pair(
        {"stem": "观察下图回答。", "image_refs": {"stem": [{"sha256": "abc123"}], "answer": [], "analysis": []}},
        {"stem": "观察下图回答。", "image_refs": {"stem": [{"sha256": "def456"}], "answer": [], "analysis": []}},
    )

    assert not matched
    assert reason == ""


def test_missing_required_image_detects_image_cue_without_docx_image():
    issues = check_question_structured({
        "question_no": 3,
        "question_type": "单选题",
        "stem": "如图所示，已知R1=5Ω，R2=10Ω，求CD间电压变化范围。",
        "options": ["A. 0~15 V", "B. 0~25 V", "C. 2.5~15 V", "D. 5~30 V"],
        "answer": "D",
        "analysis": "当分别取0Ω和25Ω时，可得UCD的值分别为5V和30V。",
    })

    assert any(issue["code"] == "missing_required_image" for issue in issues)


def test_missing_required_image_ignores_question_with_real_image_ref():
    issues = check_question_structured({
        "question_no": 3,
        "question_type": "单选题",
        "stem": "如图所示，已知R1=5Ω，R2=10Ω，求CD间电压变化范围。",
        "options": ["A. 0~15 V", "B. 0~25 V", "C. 2.5~15 V", "D. 5~30 V"],
        "answer": "D",
        "analysis": "见图分析。",
        "image_refs": {"stem": [{"sha256": "abc123"}], "answer": [], "analysis": []},
    })

    assert not any(issue["code"] == "missing_required_image" for issue in issues)
