"""Generate planning topics from parsed outlines or textbook TOC items."""

import re


def assess_importance(section):
    """根据考点内容判断节的重要程度

    规则：
      - 含≥2个"掌握"级考点 → 极重要
      - 含≥1个"掌握"级或≥2个"理解/应用"级 → 重要
      - 其余 → 标准
    """
    points = section["points"]
    if not points:
        return "标准"

    master_count = sum(1 for p in points if p["level"] == "掌握")
    understand_count = sum(1 for p in points if p["level"] in ("理解", "应用"))

    if master_count >= 2:
        return "极重要"
    elif master_count >= 1 or understand_count >= 2:
        return "重要"
    else:
        return "标准"


def assess_point_importance(point):
    """根据单个考点的认知层次判断重要程度"""
    if point["level"] == "掌握":
        return "极重要"
    if point["level"] in ("理解", "应用"):
        return "重要"
    return "标准"



def make_theme_from_point(point_text):
    """根据单个考纲知识点生成兜底试卷主题名"""
    theme = point_text.strip()

    # 去掉常见认知层次动词，让主题聚焦在考点本身；“认识”常可直接形成主题，保留。
    theme = re.sub(r'^(熟练掌握|掌握|熟悉|理解|了解|能|会)', '', theme).strip()

    # 主题取考点的核心前半句，避免把多个要求都塞进标题。
    theme = re.split(r'[，,；;。]|及|和|与', theme, maxsplit=1)[0].strip()

    # 标题中常见的“的”多为连接词，去掉后更像主题名。
    theme = theme.replace("的", "")

    return theme or point_text.strip()


def collect_point_records(courses):
    """收集所有考点，供 AI 批量生成主题"""
    records = []
    for course_idx, course in enumerate(courses, 1):
        for sec_idx, section in enumerate(course["sections"]):
            for point_idx, point in enumerate(section["points"], 1):
                records.append({
                    "id": f"{course_idx}-{sec_idx}-{point_idx}",
                    "course": course["name"],
                    "section": section["name"],
                    "point": point["text"],
                })
    return records


def generate_topics(courses, default_qt="单选5+填空3+综合2", default_diff="80:10:10", theme_map=None):
    """将解析的课程结构转化为规划表的主题行列表。

    每个扫描到的考点单独生成行；极重要考点生成两卷，序号连续递增。
    """
    topics = []
    seq = 1

    for course_idx, course in enumerate(courses, 1):
        course_header = f"课程{'一二三四五六七八九十'[course_idx - 1]}：{course['name']}"
        topics.append({"type": "course", "text": course_header})

        for sec_idx, section in enumerate(course["sections"]):
            # 节标题行
            topics.append({"type": "section", "text": section["name"]})

            if not section["points"]:
                continue

            for point_idx, point in enumerate(section["points"], 1):
                importance = assess_point_importance(point)
                exam_ref = f"课程{course_idx}§{sec_idx}({point_idx})"
                point_id = f"{course_idx}-{sec_idx}-{point_idx}"
                theme_base = (theme_map or {}).get(point_id) or make_theme_from_point(point["text"])
                copy_suffixes = ["一", "二"] if importance == "极重要" else [None]

                for copy_suffix in copy_suffixes:
                    if copy_suffix:
                        theme = f"{theme_base}（{copy_suffix}）"
                    else:
                        theme = theme_base

                    topics.append({
                        "type": "topic",
                        "seq": seq,
                        "knowledge": point["text"],
                        "theme": theme,
                        "level": importance,
                        "question_types": default_qt,
                        "difficulty": default_diff,
                        "sets": 1,
                        "exam_ref": exam_ref,
                    })
                    seq += 1

    return topics


def _highest_level(points):
    order = {"掌握": 3, "理解": 2, "应用": 2, "了解": 1}
    if not points:
        return "标准"
    best = max(points, key=lambda p: order.get(p.get("level"), 0))
    return assess_point_importance(best)



def generate_topics_from_textbook_toc(toc_items, matches, textbook, default_qt="单选5+填空3+综合2", default_diff="80:10:10"):
    """按教材目录生成规划表 topics，B列写匹配到的考纲知识点。"""
    topics = []
    seq = 1
    current_chapter = None
    topics.append({"type": "course", "text": f"教材：《{textbook.get('name', '未命名教材')}》"})
    for item in toc_items:
        if item["chapter"] != current_chapter:
            current_chapter = item["chapter"]
            topics.append({"type": "section", "text": current_chapter})
        points = matches.get(item["id"], [])
        knowledge = "；".join(p["text"] for p in points) if points else f"待补充：教材目录主题“{item['theme']}”未在考纲中精确匹配"
        exam_ref = "；".join(p["exam_ref"] for p in points) if points else "待人工确认"
        level = _highest_level(points)
        copy_suffixes = ["一", "二"] if level == "极重要" else [None]
        for copy_suffix in copy_suffixes:
            theme = f"{item['theme']}（{copy_suffix}）" if copy_suffix else item["theme"]
            topics.append({
                "type": "topic",
                "seq": seq,
                "knowledge": knowledge,
                "theme": theme,
                "level": level,
                "question_types": default_qt,
                "difficulty": default_diff,
                "sets": 1,
                "exam_ref": exam_ref,
            })
            seq += 1
    return topics
