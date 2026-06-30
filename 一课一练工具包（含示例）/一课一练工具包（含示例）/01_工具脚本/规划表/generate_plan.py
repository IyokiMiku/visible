"""从考纲 PDF 自动生成考点规划表 xlsx

使用方法：
  python generate_plan.py                           # 交互式选择 PDF
  python generate_plan.py --pdf "考纲.pdf"          # 指定 PDF
  python generate_plan.py --pdf "考纲.pdf" --title "重庆市汽车类"  # 指定标题前缀

生成逻辑：
  1. 读取考纲 PDF，解析出 课程→节→考点 结构
  2. 按关键词（掌握/熟悉/了解）自动判定每个考点的重要性
  3. 每个扫描到的考点单独生成行；极重要考点生成两卷，序号连续递增
  4. 输出带底纹、节名称的 xlsx 规划表
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from planning_assets import (
    prepare_planning_assets,
    validate_question_plan,
)
from plan_modules.ai_client import ai_match_toc_to_outline, generate_ai_theme_map
from plan_modules.config import BASE_DIR, safe_path_part as _safe_path_part, split_province_category as _split_province_category
from plan_modules.excel_writer import write_planning_xlsx
from plan_modules.outline_parser import extract_pdf_text, parse_exam_outline
from plan_modules.textbook_toc import (
    _default_ocr_dir,
    _match_course_name,
    _resolve_textbook_pdfs,
    _textbook_info_line,
    _warn_missing_textbook_pdfs,
    load_structured_toc_items,
    ocr_textbook_toc,
    parse_pages_list,
    parse_textbook_filename,
    parse_toc_text,
    prompt_toc_pages_for_textbook,
)
from plan_modules.toc_matcher import (
    _merge_matches,
    build_local_match_candidates,
    flatten_outline_points,
    local_match_toc_to_outline,
    write_toc_match_report,
)
from plan_modules.topic_generator import generate_topics, generate_topics_from_textbook_toc


# === 教材目录驱动规划表 ===

def run_textbook_driven_plan(args, courses, textbooks, title_prefix):
    """教材目录驱动模式主流程。"""
    province, category = _split_province_category(title_prefix)
    pdfs = _resolve_textbook_pdfs(args, province, category)
    if not pdfs:
        print("错误：未找到教材 PDF。请指定 --textbook-pdf 或 --textbook-dir。")
        sys.exit(1)
    _warn_missing_textbook_pdfs(textbooks, pdfs)

    generated = []
    shared_pages = parse_pages_list(args.toc_pages)
    for pdf_path in pdfs:
        if not pdf_path.exists():
            print(f"错误：教材文件不存在 {pdf_path}")
            sys.exit(1)
        textbook = parse_textbook_filename(pdf_path)
        course_name = _match_course_name(textbook, courses)
        outline_points = flatten_outline_points(courses, course_filter=course_name)
        if not outline_points:
            outline_points = flatten_outline_points(courses)

        ocr_dir = _default_ocr_dir(args, province, category, textbook)
        pages = shared_pages or prompt_toc_pages_for_textbook(pdf_path)
        toc_text = ocr_textbook_toc(
            str(pdf_path),
            pages,
            ocr_dir,
            reuse=args.reuse_ocr,
            engine=args.ocr_engine,
            tessdata_dir=args.tessdata,
            dpi=args.toc_dpi,
            layout=args.toc_layout,
            preprocess=args.toc_preprocess,
            keep_images=args.keep_toc_images,
        )
        toc_items = load_structured_toc_items(ocr_dir) or parse_toc_text(toc_text)
        if toc_items:
            (Path(ocr_dir) / "toc_items_for_plan.json").write_text(json.dumps(toc_items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  解析目录条目：{len(toc_items)} 条")
        if not toc_items:
            print("错误：未能从教材目录 OCR 文本解析出目录条目，请检查 toc_raw.txt 或调整 --toc-pages。")
            sys.exit(1)

        local_candidates = build_local_match_candidates(toc_items, outline_points)
        local_matches = local_match_toc_to_outline(toc_items, outline_points)
        ai_matches = {} if args.no_ai_match else ai_match_toc_to_outline(toc_items, outline_points, args.ai_model)
        matches = _merge_matches(local_matches, ai_matches)
        write_toc_match_report(ocr_dir, toc_items, matches, local_candidates)
        topics = generate_topics_from_textbook_toc(toc_items, matches, textbook, args.qt, args.diff)

        title = f"{title_prefix}《一课一练》考点规划表 v1"
        config_line = f"题型：{args.qt} | 难度：{args.diff}"
        info_line = _textbook_info_line(textbook)

        if args.output and len(pdfs) == 1:
            output_path = args.output
        else:
            base_dir = BASE_DIR / "04_生成输出" / "考点规划表" / _safe_path_part(province or "未分类") / _safe_path_part(category or "未分类")
            os.makedirs(base_dir, exist_ok=True)
            safe_name = _safe_path_part(f"{title_prefix}_{textbook['name']}_一课一练考点规划表")
            output_path = str(base_dir / f"{safe_name}.xlsx")
            if os.path.exists(output_path):
                i = 2
                while True:
                    candidate = str(base_dir / f"{safe_name}_v{i}.xlsx")
                    if not os.path.exists(candidate):
                        output_path = candidate
                        break
                    i += 1

        data_rows = write_planning_xlsx(output_path, title, config_line, info_line, topics, [textbook])
        prepare_planning_assets(
            title_prefix,
            args.qt,
            total_questions=args.total_questions,
            style_mode=args.style_mode,
            type_config_mode=args.type_config_mode,
            textbooks=[textbook],
            refresh_type_config=args.refresh_type_config,
        )
        generated.append(output_path)
        matched_count = sum(1 for item in toc_items if matches.get(item["id"]))
        print(f"✓ 已生成目录驱动规划表: {output_path}")
        print(f"  目录条目 {len(toc_items)} 条，匹配考纲 {matched_count} 条，写入 {data_rows} 行")

    print("\n目录驱动规划表生成完成：")
    for path in generated:
        print(f"  - {path}")



# === 主流程 ===

def main():
    parser = argparse.ArgumentParser(description="从考纲 PDF 生成考点规划表")
    parser.add_argument("--pdf", "-p", help="考纲 PDF 文件路径")
    parser.add_argument("--title", "-t", help="规划表标题前缀（如'重庆市汽车类'）")
    parser.add_argument("--qt", default="单选5+填空3+综合2", help="默认题型配置")
    parser.add_argument("--total-questions", type=int, default=10, help="每张试卷总题量，默认10；题型配置数量合计必须等于该值")
    parser.add_argument("--diff", default="80:10:10", help="默认难度配比")
    parser.add_argument("--style-mode", choices=["auto", "template", "skip"], default="auto", help="规划表生成后真题风格库准备方式：auto调用API蒸馏，template只生成模板，skip跳过")
    parser.add_argument("--type-config-mode", choices=["auto", "template", "skip"], default="template", help="规划表生成后题型定义JSON准备方式：auto调用API总结，template生成模板，skip跳过")
    parser.add_argument("--refresh-type-config", action="store_true", help="允许覆盖已存在的题型定义JSON；默认只生成建议版不覆盖")
    parser.add_argument("--output", "-o", help="输出 xlsx 路径")
    parser.add_argument("--no-ai-theme", action="store_true", help="不调用 AI，使用规则兜底生成试卷主题")
    parser.add_argument("--ai-model", help="用于生成试卷主题的模型；默认使用 config.json 中的 model")
    parser.add_argument("--textbook-driven", action="store_true", help="启用教材目录 OCR 驱动模式：用教材目录命名试卷主题，再匹配考纲知识点")
    parser.add_argument("--textbook-dir", help="教材 PDF 所在目录；不填时按 教材/省份/考类 或 03_项目数据/参考资料/教材/省份/考类 自动查找")
    parser.add_argument("--textbook-pdf", help="只处理指定教材 PDF")
    parser.add_argument("--toc-pages", help="教材目录页范围，如 1-3 或 3,5-8；不填时每本教材单独询问")
    parser.add_argument("--ocr-output-dir", help="教材目录 OCR 缓存目录；默认 03_项目数据/参考资料/教材OCR/省份/考类/教材名")
    parser.add_argument("--reuse-ocr", action="store_true", default=True, help="复用已有 toc_raw.txt（默认启用）")
    parser.add_argument("--no-reuse-ocr", dest="reuse_ocr", action="store_false", help="强制重新 OCR 教材目录页")
    parser.add_argument("--no-ai-match", action="store_true", help="不调用 API 匹配目录与考纲，只使用本地关键词匹配")
    parser.add_argument("--ocr-engine", choices=["auto", "tesseract", "rapidocr"], default="auto", help="教材目录 OCR 引擎，默认 auto：优先 Tesseract 目录扫描器，失败回退 RapidOCR")
    parser.add_argument("--tessdata", help="Tesseract tessdata 目录（含 chi_sim.traineddata）")
    parser.add_argument("--toc-dpi", type=float, default=2.5, help="教材目录页渲染倍率，默认 2.5")
    parser.add_argument("--toc-layout", choices=["auto", "single", "double"], default="auto", help="教材目录版面：auto/single/double")
    parser.add_argument("--toc-preprocess", action="store_true", help="OCR 前对教材目录图片做灰度、对比度和二值化增强")
    parser.add_argument("--keep-toc-images", action="store_true", help="保留教材目录页渲染图片，便于人工校对")
    args = parser.parse_args()

    try:
        validate_question_plan(args.qt, args.total_questions)
    except ValueError as exc:
        print(f"错误：{exc}")
        sys.exit(1)

    # 选择 PDF
    pdf_path = args.pdf
    if not pdf_path:
        # 交互式选择
        print("请输入考纲 PDF 文件路径：")
        pdf_path = input("> ").strip().strip('"')

    if not os.path.exists(pdf_path):
        print(f"错误：找不到文件 {pdf_path}")
        sys.exit(1)

    # 标题
    title_prefix = args.title
    if not title_prefix:
        print("请输入规划表标题前缀（如'重庆市机械加工类'）：")
        title_prefix = input("> ").strip()

    # 双击运行时询问是否扫描教材目录。命令行已显式指定 --textbook-driven/--textbook-dir/--textbook-pdf 时不重复询问。
    if not args.textbook_driven and not args.textbook_dir and not args.textbook_pdf:
        print("是否需要扫描教材目录 PDF？输入 y/是 扫描教材目录；直接回车则只按考纲生成规划表：")
        answer = input("> ").strip().lower()
        if answer in ("y", "yes", "是", "需要", "扫描", "1"):
            args.textbook_driven = True
            province, category = _split_province_category(title_prefix)
            if province and category:
                textbook_dir = BASE_DIR / "03_项目数据" / "参考资料" / "教材" / province / category
                print(f"将按前缀查找教材 PDF：{textbook_dir}")
            else:
                print("警告：未能从标题前缀解析出省份和考类，请使用如'重庆市机械加工类'的格式。")

    print(f"\n正在解析考纲: {Path(pdf_path).name}")
    print("=" * 60)

    # 提取文本
    text = extract_pdf_text(pdf_path)
    if not text.strip():
        print("错误：PDF 文本为空，请确认文件可读")
        sys.exit(1)

    # 解析结构
    courses, textbooks = parse_exam_outline(text)
    print(f"解析完成：{len(courses)} 个课程")
    for c in courses:
        sec_count = len(c["sections"])
        point_count = sum(len(s["points"]) for s in c["sections"])
        print(f"  {c['name']}: {sec_count} 节, {point_count} 个考点")

    if textbooks:
        print(f"\n参考教材：")
        for tb in textbooks:
            print(f"  《{tb['name']}》{tb['publisher']}第{tb['edition']}版")

    if args.textbook_driven:
        run_textbook_driven_plan(args, courses, textbooks, title_prefix)
        return

    # 生成主题
    theme_map = None
    if args.no_ai_theme:
        print("\n已关闭 AI 主题生成，使用规则兜底生成试卷主题。")
    else:
        print(f"\n正在调用 Claude API 生成试卷主题：{args.ai_model}")
        theme_map = generate_ai_theme_map(courses, args.ai_model)
        print(f"AI 主题生成完成：{len(theme_map)} 个考点")

    topics = generate_topics(courses, args.qt, args.diff, theme_map)
    topic_count = sum(1 for t in topics if t["type"] == "topic")
    important_count = sum(1 for t in topics if t.get("level") == "极重要")
    print(f"\n共生成 {topic_count} 练（其中极重要拆分为两练的有 {important_count} 个）")

    # 构建表头信息
    title = f"{title_prefix}《一课一练》考点规划表 v1"
    config_line = f"题型：{args.qt} | 难度：{args.diff}"
    tb_str = "、".join(f"《{tb['name']}》{tb['publisher']}第{tb['edition']}版" for tb in textbooks)
    info_line = f"参考教材：{tb_str}" if tb_str else "参考教材：待填写"

    # 输出路径
    output_path = args.output
    if not output_path:
        root_dir = BASE_DIR / "04_生成输出" / "考点规划表"
        province, category = _split_province_category(title_prefix)
        if province and category:
            base_dir = root_dir / _safe_path_part(province) / _safe_path_part(category)
        else:
            base_dir = root_dir / "未分类"
        os.makedirs(base_dir, exist_ok=True)
        safe_name = _safe_path_part(title_prefix.replace("（", "(").replace("）", ")"))
        output_path = str(base_dir / f"{safe_name}_一课一练考点规划表.xlsx")
        # 避免覆盖已有文件
        if os.path.exists(output_path):
            i = 2
            while True:
                candidate = str(base_dir / f"{safe_name}_一课一练考点规划表_v{i}.xlsx")
                if not os.path.exists(candidate):
                    output_path = candidate
                    break
                i += 1

    # 生成 xlsx
    data_rows = write_planning_xlsx(output_path, title, config_line, info_line, topics, textbooks)
    print(f"\n✓ 规划表已生成: {output_path}")
    print(f"  共 {data_rows} 行数据")

    prepare_planning_assets(
        title_prefix,
        args.qt,
        total_questions=args.total_questions,
        style_mode=args.style_mode,
        type_config_mode=args.type_config_mode,
        textbooks=textbooks,
        refresh_type_config=args.refresh_type_config,
    )

    # 打印重要性统计
    levels = {}
    for t in topics:
        if t["type"] == "topic":
            lv = t["level"]
            levels[lv] = levels.get(lv, 0) + 1
    print(f"\n重要性分布：")
    for lv in ("极重要", "重要", "标准"):
        if lv in levels:
            print(f"  {lv}: {levels[lv]} 练")


if __name__ == "__main__":
    main()
