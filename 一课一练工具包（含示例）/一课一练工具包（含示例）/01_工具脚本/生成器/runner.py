"""一课一练试卷生成器主流程。"""
import argparse
import os
import re
import sys
import time
import traceback
from pathlib import Path

from openai import OpenAI

from .config_io import (
    _load_daily_usage,
    _new_usage_summary,
    _print_token_summary,
    _record_token_usage,
    _save_daily_usage,
    call_api,
    load_config,
    load_spec,
)
from .docx_generation import generate_docx
from .exam_style import ensure_exam_style_ready
from .paths import BASE_DIR
from .planning import _get_topic_output_base, parse_planning_table
from .postprocess import _post_process
from .prompts import build_generation_prompt
from .references import get_exam_style_reference_status
from .quality import (
    MAX_REGEN_ATTEMPTS,
    _fix_answer_distribution,
    _print_qc_summary,
    _quick_check,
    _repair_qc_issues_targeted,
)
from .text_processing import (
    _clean_paper_text,
    _extract_question_summaries,
    _normalize_generated_text,
    _split_numbered_theme,
)

ALL_BATCH_SIZE = 5
ALL_BATCH_PAUSE_SECONDS = 20


def _chunk_topics(topics, batch_size=ALL_BATCH_SIZE):
    """将主题列表按小批量切分，避免 all 连续生成时 API 压力过大。"""
    return [topics[i:i + batch_size] for i in range(0, len(topics), batch_size)]


def _format_seq_ranges(seqs):
    """将序号列表格式化为 3,6-9,14 这种可复制输入的范围。"""
    nums = sorted(set(int(s) for s in seqs))
    if not nums:
        return ""

    ranges = []
    start = prev = nums[0]
    for num in nums[1:]:
        if num == prev + 1:
            prev = num
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = num
    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(ranges)


def _parse_generation_range(range_str, topics):
    """解析生成范围，支持 all、单序号、连续范围和逗号合并的多范围。"""
    text = str(range_str or "").strip()
    if not text:
        raise ValueError("生成范围不能为空")
    if text.lower() == "all":
        return [t["seq"] for t in topics], True

    selected = []
    for part in text.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = [x.strip() for x in part.split("-", 1)]
            if len(bounds) != 2 or not bounds[0] or not bounds[1]:
                raise ValueError(f"无效范围: {part}")
            start, end = int(bounds[0]), int(bounds[1])
            if start > end:
                start, end = end, start
            selected.extend(range(start, end + 1))
        else:
            selected.append(int(part))

    if not selected:
        raise ValueError("生成范围不能为空")
    return sorted(set(selected)), False


def _ask_exam_type_name(default_name="高职分类考试"):
    """询问输出文件名和标题中使用的考试类型名称。"""
    options = {
        "1": "高职分类考试",
        "2": "对口招生",
    }
    print("\n请选择试卷名称中使用的考试类型：")
    print("  1. 高职分类考试")
    print("  2. 对口招生")
    print("  3. 其他名称")
    choice = input(f"请输入编号（默认 {default_name}）: ").strip()
    if not choice:
        return default_name
    if choice in options:
        return options[choice]
    if choice == "3":
        custom_name = input("请输入考试类型名称: ").strip()
        return custom_name or default_name
    print(f"无效选择，使用默认名称：{default_name}")
    return default_name


def _topic_set_output_exists(meta, topic, set_idx, output_dir):
    """检查指定主题/套卷的解析版 DOCX 是否已经存在。"""
    sub_dir = _get_topic_output_base(meta, topic, output_dir)
    if not sub_dir.exists():
        return False

    set_suffix = f"({set_idx})" if topic["sets"] > 1 else ""
    expected_prefix = f"第{topic['seq']}练 {topic['theme']}{set_suffix} "
    for path in sub_dir.rglob(f"*第{topic['seq']}练*.docx"):
        if "_原始文本" in path.parts:
            continue
        name = path.name
        if name.startswith("~$"):
            continue
        if expected_prefix in name and "（解析版）" in name:
            return True
    return False


def _find_missing_topic_seqs(meta, topics, output_dir):
    """查找当前规划表考类下尚未生成完整解析版 DOCX 的练习序号。"""
    missing = []
    for topic in topics:
        complete = all(
            _topic_set_output_exists(meta, topic, set_idx, output_dir)
            for set_idx in range(1, topic["sets"] + 1)
        )
        if not complete:
            missing.append(topic["seq"])
    return missing


def _escape_md_table_cell(value):
    """转义 Markdown 表格单元格，避免质检详情中的竖线破坏表格。"""
    text = str(value or "").replace("\n", " ").strip()
    return text.replace("|", "\\|")


def _append_manual_review_report(report_dir, meta, topic, set_idx, issues, score):
    """将待人工审核试卷的质检遗留问题追加写入当前教材目录的质检报告。"""
    os.makedirs(report_dir, exist_ok=True)
    report_path = Path(report_dir) / "质检报告.md"
    is_new_file = not report_path.exists() or report_path.stat().st_size == 0
    set_label = f"第{set_idx}套" if topic.get("sets", 1) > 1 else ""
    paper_label = f"第{topic['seq']}练 {topic['theme']}{set_label}"
    checked_at = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(report_path, "a", encoding="utf-8") as f:
        if is_new_file:
            f.write("# 质检报告\n\n")
            f.write("本文件记录自动质检后仍需人工审核的试卷问题；新的问题会追加在文档末尾。\n\n")
        f.write(f"## {paper_label}\n\n")
        f.write(f"- 检查时间：{checked_at}\n")
        f.write(f"- 省份/类别：{meta.get('province', '')} {meta.get('category', '')}\n")
        f.write(f"- 课程：{topic.get('course', '')}\n")
        f.write(f"- 章节：{topic.get('section', '')}\n")
        f.write(f"- 本地质检评分：{score}/100\n\n")
        f.write("| 试卷序号 | 错误类型 | 具体错误名称 | 题号 | 严重程度 | 具体描述 |\n")
        f.write("|---|---|---|---|---|---|\n")
        if issues:
            for issue in issues:
                f.write(
                    "| "
                    f"{_escape_md_table_cell(topic['seq'])} | "
                    f"{_escape_md_table_cell(issue.get('severity', ''))} | "
                    f"{_escape_md_table_cell(issue.get('type', ''))} | "
                    f"{_escape_md_table_cell(issue.get('question', ''))} | "
                    f"{_escape_md_table_cell(issue.get('severity', ''))} | "
                    f"{_escape_md_table_cell(issue.get('detail', ''))} |\n"
                )
        else:
            f.write(f"| {_escape_md_table_cell(topic['seq'])} | 待人工审核 | 未记录到具体问题 |  |  | 自动质检未通过，但未保留到具体问题明细 |\n")
        f.write("\n")

    print(f"  → 待人工审核问题已追加到: {report_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="一课一练试卷生成器")
    parser.add_argument("--file", "-f", help="考点规划表 xlsx 路径")
    parser.add_argument("--range", "-r", help="生成范围，如 1-5 或 3,7,12")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--no-check", action="store_true", help="跳过质检，直接保存")
    style_group = parser.add_mutually_exclusive_group()
    style_group.add_argument("--auto-style", action="store_true", help="真题风格库缺失时自动从真题题库蒸馏（调用 API）")
    style_group.add_argument("--style-template", action="store_true", help="真题风格库缺失时只生成可人工填写的模板（不调用 API）")
    style_group.add_argument("--no-auto-style", action="store_true", help="跳过真题风格库自动检查/生成")
    args = parser.parse_args()

    # 加载配置
    config = load_config()
    spec_text = load_spec()

    # 初始化 API 客户端
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )

    # 选择规划表文件
    xlsx_path = args.file
    if not xlsx_path:
        planning_dir = BASE_DIR / "04_生成输出" / "考点规划表"
        if planning_dir.exists():
            files = sorted(
                [f for f in planning_dir.rglob("*.xlsx") if not f.name.startswith(("~", "_"))],
                key=lambda p: str(p.relative_to(planning_dir))
            )
            if not files:
                print("错误：考点规划表目录为空")
                return
            print("\n可用的考点规划表：")
            for i, f in enumerate(files, 1):
                rel = f.relative_to(planning_dir)
                print(f"  {i}. {rel}")
            choice = input("\n请输入编号选择规划表: ").strip()
            try:
                xlsx_path = str(files[int(choice) - 1])
            except (ValueError, IndexError):
                print("无效选择")
                return
        else:
            print("错误：找不到考点规划表目录")
            return

    # 解析规划表
    print(f"\n正在解析规划表: {Path(xlsx_path).name}")
    meta, topics = parse_planning_table(xlsx_path)
    print(f"  省份: {meta['province']}")
    print(f"  类别: {meta['category']}")
    print(f"  教材: {meta['textbooks']}")
    print(f"  共 {len(topics)} 个主题")

    meta["exam_type_name"] = _ask_exam_type_name()
    print(f"  考试类型名称: {meta['exam_type_name']}")

    # 生成试卷前检查当前省份/考类的真题风格库；缺失时可从真题题库自动蒸馏。
    if args.no_auto_style:
        print("\n已按参数跳过真题风格库自动检查/生成。")
    else:
        if args.auto_style:
            style_mode = "auto"
        elif args.style_template:
            style_mode = "template"
        else:
            style_mode = "ask"
        ensure_exam_style_ready(meta, client, config, mode=style_mode)

    # 输出目录
    output_dir = args.output or str(BASE_DIR / "04_生成输出" / config.get("output_dir", "生成结果"))
    os.makedirs(output_dir, exist_ok=True)

    # 确定生成范围
    if args.range:
        range_str = args.range
    else:
        print(f"\n主题列表：")
        for t in topics:
            level_mark = {"极重要": "★★", "重要": "★", "标准": "○"}.get(t["level"], "")
            sets_mark = f" ×{t['sets']}套" if t["sets"] > 1 else ""
            print(f"  {t['seq']:>3}. [{level_mark}] {t['theme']}{sets_mark}")

        missing_seqs = _find_missing_topic_seqs(meta, topics, output_dir)
        if missing_seqs:
            missing_range = _format_seq_ranges(missing_seqs)
            print(f"\n当前考类缺少的卷子序号：{missing_range}")
            print("可直接复制以上范围；也支持输入多个范围并用逗号合并，如 3,6-9,14。")
        else:
            print("\n当前考类未发现缺少的卷子。")
        range_str = input("\n请输入生成范围（如 1-5 或 3,7,12 或 3,6-9,14 或 all）: ").strip()

    # 解析范围
    try:
        selected_seqs, is_all_range = _parse_generation_range(range_str, topics)
    except ValueError as e:
        print(f"生成范围无效：{e}")
        return

    selected_topics = [t for t in topics if t["seq"] in selected_seqs]
    if not selected_topics:
        print("没有匹配的主题")
        return

    # 逐主题生成
    total_sets = sum(t["sets"] for t in selected_topics)
    print(f"\n即将生成 {len(selected_topics)} 个主题共 {total_sets} 份试卷")
    print(f"输出目录: {output_dir}")
    print(f"使用模型: {config['model']}")
    print(f"质检模式: {'跳过' if args.no_check else '生成后自动质检'}")
    print(f"真题风格: {get_exam_style_reference_status(meta)}")
    print("=" * 60)

    success_count = 0
    fail_count = 0
    regen_count = 0

    # Token 用量跟踪
    session_usage = _new_usage_summary(config=config)
    daily_usage = _load_daily_usage()

    # 编号连续主题防重复：仅在“xxx（二）”等明确续篇中参考前一篇“xxx（一）”摘要
    prev_paper_summaries = {}  # theme_base → {part_num: summaries list}

    # 记录本次实际生成 DOCX 的目录，后处理只处理这些目录，避免扫描整个生成结果目录。
    generated_output_dirs = set()

    topic_batches = _chunk_topics(selected_topics) if is_all_range else [selected_topics]
    if is_all_range and len(topic_batches) > 1:
        print(f"all 模式将按每批 {ALL_BATCH_SIZE} 个主题小批量生成，批次间暂停 {ALL_BATCH_PAUSE_SECONDS}s，以减少连续调用 API 出错。")

    for batch_idx, topic_batch in enumerate(topic_batches, 1):
        if is_all_range and len(topic_batches) > 1:
            batch_seqs = f"{topic_batch[0]['seq']}-{topic_batch[-1]['seq']}"
            print(f"\n{'-' * 60}")
            print(f"开始第 {batch_idx}/{len(topic_batches)} 批：第 {batch_seqs} 练")
            print(f"{'-' * 60}")

        for topic in topic_batch:
            for set_idx in range(1, topic["sets"] + 1):
                set_label = f"(第{set_idx}套)" if topic["sets"] > 1 else ""
                print(f"\n▶ 第{topic['seq']}练 {topic['theme']}{set_label}")
                print(f"  知识点: {topic['knowledge'][:60]}...")
                print(f"  级别: {topic['level']} | 题型: {topic['question_types']}")

                try:
                    # 只有明确的连续编号主题才做跨卷防重复：如“电阻定律（二）”参考“电阻定律（一）”。
                    # 普通主题（如“欧姆定律”）不会参考前一个不同主题的摘要。
                    theme_base, theme_part_num = _split_numbered_theme(topic['theme'])
                    existing_summaries_for_dedup = None
                    if theme_part_num and theme_part_num > 1:
                        existing_summaries_for_dedup = prev_paper_summaries.get(theme_base, {}).get(theme_part_num - 1)

                    # 构建 prompt（传入已有摘要防重复）
                    sys_prompt, user_prompt = build_generation_prompt(
                        meta, topic, set_idx, spec_text,
                        existing_summaries=existing_summaries_for_dedup
                    )

                    # 生成+质检循环
                    paper_text = None
                    accepted = False
                    needs_manual_review = False
                    best_paper_text = None
                    best_score = -1
                    for attempt in range(1, MAX_REGEN_ATTEMPTS + 1):
                        attempt_label = f"(第{attempt}次)" if attempt > 1 else ""

                        if paper_text is None:
                            # 第一次生成整卷；后续若质检不过，只在上一版基础上定向修复，不再整卷重生。
                            print(f"  正在调用 API 生成试题{attempt_label}...")
                            start_time = time.time()

                            paper_text, usage = call_api(
                                client, config["model"],
                                sys_prompt, user_prompt,
                                max_tokens=config.get("max_tokens", 8000),
                                temperature=config.get("temperature", 0.7),
                            )
                            elapsed = time.time() - start_time

                            # 累计 token 用量和费用
                            if usage:
                                cost_info = _record_token_usage(session_usage, daily_usage, usage, config)
                                token_info = f", {usage['total_tokens']} tokens"
                                if cost_info.get("total_cost", 0) > 0:
                                    token_info += f", 约 {cost_info['total_cost']:.4f} {cost_info.get('currency', '元')}"
                            else:
                                token_info = ""

                            print(f"  API 返回成功 ({elapsed:.1f}s, {len(paper_text)}字{token_info})")
                            paper_text = _normalize_generated_text(paper_text)
                        else:
                            print(f"  继续在上一版基础上定向修复{attempt_label}...")

                        # 跳过质检模式
                        if args.no_check:
                            accepted = True
                            break

                        # 自动调整答案分布（通过交换选项，不重新生成）
                        paper_text = _fix_answer_distribution(paper_text)

                        # 本地质检
                        cleaned = _clean_paper_text(paper_text)
                        severe, warnings, score, _, infos = _quick_check(cleaned)
                        _print_qc_summary(severe, warnings, score, infos)

                        # 记录三次生成中质检分数最高的一份，供最终兜底保留
                        if score > best_score:
                            best_score = score
                            best_paper_text = paper_text

                        # 定向修复质检问题：先修答案自暴露，再修其他单题问题，最后用最少改动修复查重问题。
                        if severe or warnings:
                            paper_text, severe, warnings, score, infos, fixed_rounds = _repair_qc_issues_targeted(
                                client, config, meta, topic, set_idx, spec_text,
                                paper_text, severe, warnings, score, infos,
                                session_usage, daily_usage,
                            )
                            regen_count += fixed_rounds
                            if score > best_score:
                                best_score = score
                                best_paper_text = paper_text
                            if fixed_rounds == 0 and (severe or warnings):
                                paper_text = best_paper_text or paper_text
                                accepted = True
                                needs_manual_review = True
                                print("  → 自动修复未产生有效改进，停止反复重试，保留当前最高分版本并标记待人工审核。")
                                break

                        # 评分>90且无严重/警告问题 → 自动保存，无需人工确认
                        if score > 90 and not severe and not warnings:
                            accepted = True
                            needs_manual_review = False
                            break

                        # 未通过则继续在上一版基础上定向修复，最多尝试三轮
                        if attempt < MAX_REGEN_ATTEMPTS:
                            print(f"  → 质检仍未通过，将继续只针对剩余问题修正上一版试卷（{attempt}/{MAX_REGEN_ATTEMPTS}）...")
                            time.sleep(2)
                            continue

                        # 三次均未通过：不再询问用户，保留分数最高的一份并标记待人工审核
                        paper_text = best_paper_text or paper_text
                        accepted = True
                        needs_manual_review = True
                        print(f"\n  已生成 {MAX_REGEN_ATTEMPTS} 次，最高评分 {best_score}/100。")
                        print("  → 自动保留最高分试卷，并在文件名前添加“（待人工审核）”。")
                        break

                    if not accepted:
                        print(f"  ✗ 跳过: 第{topic['seq']}练 {topic['theme']}")
                        fail_count += 1
                        continue

                    # 保存原始文本（与docx同目录结构下的_原始文本子目录）
                    txt_base = _get_topic_output_base(meta, topic, output_dir)

                    txt_dir = txt_base / "_原始文本"
                    os.makedirs(txt_dir, exist_ok=True)
                    txt_name = f"第{topic['seq']}练_{topic['theme']}{set_label}.txt"
                    with open(txt_dir / txt_name, "w", encoding="utf-8") as f:
                        f.write(_normalize_generated_text(paper_text))

                    # 生成 DOCX
                    print("  正在生成 DOCX...")
                    docx_path = generate_docx(meta, topic, set_idx, paper_text, output_dir, needs_manual_review=needs_manual_review)
                    generated_output_dirs.add(str(Path(docx_path).parent))
                    print(f"  ✓ 完成: {Path(docx_path).name}")
                    if needs_manual_review:
                        _append_manual_review_report(txt_base, meta, topic, set_idx, severe + warnings, best_score)
                    success_count += 1

                    # 记录题目摘要：只供后续同基础主题的编号续篇使用
                    paper_summaries = _extract_question_summaries(paper_text)
                    if paper_summaries and theme_part_num:
                        prev_paper_summaries.setdefault(theme_base, {})[theme_part_num] = paper_summaries

                except Exception as e:
                    print(f"  ✗ 失败: {e}")
                    traceback.print_exc()
                    fail_count += 1

                # 避免 API 限流
                if success_count + fail_count < total_sets:
                    time.sleep(2)

        if is_all_range and len(topic_batches) > 1 and batch_idx < len(topic_batches):
            print(f"\n第 {batch_idx}/{len(topic_batches)} 批完成，暂停 {ALL_BATCH_PAUSE_SECONDS}s 后继续下一批...")
            time.sleep(ALL_BATCH_PAUSE_SECONDS)

    # 汇总
    print("\n" + "=" * 60)
    print(f"生成完成！成功 {success_count} 份，失败/跳过 {fail_count} 份")
    if regen_count > 0:
        print(f"质检修复: {regen_count} 次")
    print(f"输出目录: {output_dir}")

    # Token 用量汇总
    if session_usage["api_calls"] > 0:
        _print_token_summary(session_usage, daily_usage)

    # 询问是否继续生成
    print()
    while True:
        cont = input("是否继续生成其他练习？(y=继续 / n=结束): ").strip().lower()
        if cont in ("y", "yes", "是"):
            print()
            main()
            return
        elif cont in ("n", "no", "否", ""):
            break
        print("请输入 y 或 n")

    # 后处理：生成原卷版 → 打包zip → 分类
    if generated_output_dirs:
        print("\n" + "=" * 60)
        print("正在执行后处理（原卷版生成 → 打包 → 分类）...")
        print("=" * 60)
        _post_process(output_dir, target_dirs=sorted(generated_output_dirs))
    else:
        print("\n本次没有成功生成 DOCX，跳过后处理。")

    # 最终总结
    print("\n" + "=" * 60)
    print("工作总结")
    print("=" * 60)
    print(f"  本次生成: {success_count} 份试卷")
    if fail_count > 0:
        print(f"  跳过/失败: {fail_count} 份")
    if regen_count > 0:
        print(f"  质检修复: {regen_count} 次")
    print(f"  输出目录: {output_dir}")
    if session_usage["api_calls"] > 0:
        print(f"  API 调用: {session_usage['api_calls']} 次")
        print(f"  Token 消耗: {session_usage['total_tokens']:,} tokens")
    print(f"  今日累计: {daily_usage['total_tokens']:,} tokens ({daily_usage['api_calls']} 次调用)")
    print("=" * 60)
    input("\n按 Enter 关闭...")
