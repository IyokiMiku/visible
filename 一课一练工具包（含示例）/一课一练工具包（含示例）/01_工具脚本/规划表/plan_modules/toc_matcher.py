"""Match textbook TOC items to exam-outline points."""

import json
import re
from pathlib import Path

from plan_modules.textbook_toc import _clean_toc_title


def flatten_outline_points(courses, course_filter=None):
    """把考纲课程结构展开为可匹配的考点列表。"""
    records = []
    for course_idx, course in enumerate(courses, 1):
        if course_filter and course_filter not in course["name"] and course["name"] not in course_filter:
            continue
        for sec_idx, section in enumerate(course["sections"], 1):
            for point_idx, point in enumerate(section["points"], 1):
                records.append({
                    "id": f"{course_idx}-{sec_idx}-{point_idx}",
                    "course": course["name"],
                    "section": section["name"],
                    "text": point["text"],
                    "level": point["level"],
                    "exam_ref": f"课程{course_idx}§{sec_idx}({point_idx})",
                })
    return records


def _keyword_set(text):
    text = re.sub(r"^(熟练掌握|掌握|熟悉|理解|了解|能|会|认识)", "", text or "")
    text = re.sub(r"[，,。；;：:？！?、（）()《》<>\[\]【】\s]", "", text)
    stop = {"掌握", "熟悉", "理解", "了解", "认识", "应用", "方法", "概念", "作用", "特点", "分类", "要求", "进行", "常用"}
    units = {text[i:i + 2] for i in range(max(0, len(text) - 1))}
    units |= {text[i:i + 3] for i in range(max(0, len(text) - 2))}
    return {u for u in units if len(u) >= 2 and u not in stop}


def local_match_toc_to_outline(toc_items, outline_points):
    """本地关键词粗匹配：为每个目录项找最接近的考纲知识点。"""
    matches = {}
    for item in toc_items:
        item_text = item.get("chapter", "") + item.get("section", "") + item.get("theme", "")
        item_units = _keyword_set(item_text)
        scored = []
        for point in outline_points:
            point_units = _keyword_set(point["course"] + point["section"] + point["text"])
            shorter = min(len(item_units), len(point_units)) or 1
            score = len(item_units & point_units) / shorter
            if item.get("theme") and item["theme"] in point["text"]:
                score += 0.35
            cleaned_section = _clean_toc_title(point["section"])
            if cleaned_section and (cleaned_section in item.get("section", "") or cleaned_section in item.get("chapter", "")):
                score += 0.2
            if point.get("course") and (point["course"] in item.get("chapter", "") or item.get("chapter", "") in point["course"]):
                score += 0.1
            if score > 0:
                scored.append((score, point))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [p for score, p in scored[:3] if score >= 0.28]
        matches[item["id"]] = selected
    return matches


def build_local_match_candidates(toc_items, outline_points, limit=5):
    """生成本地匹配候选和分数，用于校对报告。"""
    report = {}
    for item in toc_items:
        item_text = item.get("chapter", "") + item.get("section", "") + item.get("theme", "")
        item_units = _keyword_set(item_text)
        scored = []
        for point in outline_points:
            point_units = _keyword_set(point["course"] + point["section"] + point["text"])
            shorter = min(len(item_units), len(point_units)) or 1
            score = len(item_units & point_units) / shorter
            if item.get("theme") and item["theme"] in point["text"]:
                score += 0.35
            cleaned_section = _clean_toc_title(point["section"])
            if cleaned_section and (cleaned_section in item.get("section", "") or cleaned_section in item.get("chapter", "")):
                score += 0.2
            if score > 0:
                scored.append({"score": round(score, 4), "point": point})
        scored.sort(key=lambda x: x["score"], reverse=True)
        report[item["id"]] = scored[:limit]
    return report


def _merge_matches(local_matches, ai_matches):
    merged = dict(local_matches or {})
    for toc_id, points in (ai_matches or {}).items():
        if points:
            merged[toc_id] = points
    return merged


def write_toc_match_report(ocr_dir, toc_items, matches, local_candidates):
    """输出目录项与考纲匹配校对报告。"""
    report = []
    for item in toc_items:
        matched = matches.get(item["id"], [])
        candidates = local_candidates.get(item["id"], []) if local_candidates else []
        report.append({
            "toc_id": item["id"],
            "chapter": item.get("chapter", ""),
            "section": item.get("section", ""),
            "theme": item.get("theme", ""),
            "source_page": item.get("source_page"),
            "book_page": item.get("page"),
            "matched": [
                {"exam_ref": p.get("exam_ref"), "course": p.get("course"), "section": p.get("section"), "text": p.get("text"), "level": p.get("level")}
                for p in matched
            ],
            "local_candidates": [
                {"score": c.get("score"), "exam_ref": c.get("point", {}).get("exam_ref"), "text": c.get("point", {}).get("text")}
                for c in candidates
            ],
            "status": "matched" if matched else "待人工确认",
        })
    ocr_dir = Path(ocr_dir)
    ocr_dir.mkdir(parents=True, exist_ok=True)
    (ocr_dir / "toc_match_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# 教材目录与考纲匹配报告\n"]
    for row in report:
        md.append(f"## {row['toc_id']} {row['chapter']} / {row['section']}")
        md.append(f"- 主题：{row['theme']}")
        md.append(f"- 来源页：PDF {row.get('source_page') or '未知'} / 书页 {row.get('book_page') or '未知'}")
        if row["matched"]:
            md.append("- 匹配考纲：")
            for p in row["matched"]:
                md.append(f"  - {p.get('exam_ref')}：{p.get('text')}")
        else:
            md.append("- 匹配考纲：待人工确认")
        md.append("")
    (ocr_dir / "toc_match_report.md").write_text("\n".join(md), encoding="utf-8")
