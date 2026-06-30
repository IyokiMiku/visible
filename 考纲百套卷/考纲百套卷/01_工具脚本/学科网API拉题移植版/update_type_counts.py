"""更新学科网映射 .md 文件，为题型表添加第 4 列「题目数量」。

对每个 (courseId, typeId) 组合调用 API（pageSize=1）获取 totalCount，
更新对应 .md 文件中的题型表。

用法：
  python update_type_counts.py [大类文件名...]
  
  不传参数则处理全部大类 .md 文件。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# 项目根目录
BASE = Path(__file__).resolve().parent.parent.parent
MAPPING_DIR = BASE / "02_配置资源" / "学科网映射"

from query_questions import build_payload, query as api_query, DEFAULT_APP_KEY, DEFAULT_SIGN


def parse_md_tables(md_path: Path) -> list[dict[str, Any]]:
    """解析 .md 文件，提取每个课程的 courseId 和题型列表。"""
    text = md_path.read_text(encoding="utf-8")
    courses = []

    # 匹配 ### 课程名 (courseId=10002)
    course_pattern = re.compile(r'###\s+(.+?)\s*\(courseId=(\d+)\)')
    # 匹配题型表行：| 1000201 | 单选题 | yes |
    type_row_pattern = re.compile(r'\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(yes|no)\s*\|')

    current_course = None
    for line in text.split("\n"):
        cm = course_pattern.search(line)
        if cm:
            current_course = {"name": cm.group(1).strip(), "course_id": int(cm.group(2)), "types": []}
            courses.append(current_course)
            continue

        if current_course is not None and type_row_pattern.match(line):
            tm = type_row_pattern.match(line)
            current_course["types"].append({
                "type_id": int(tm.group(1)),
                "type_name": tm.group(2),
                "objective": tm.group(3),
            })

    return courses


def query_count(course_id: int, type_id: int, cookie: str | None = None) -> int | None:
    """查询指定课程+题型的总题目数（pageSize=1，只取 totalCount）。"""
    payload = build_payload(
        course_id=course_id,
        type_ids=[type_id],
        page_size=1,
    )
    result = api_query(payload, app_key=DEFAULT_APP_KEY, sign=DEFAULT_SIGN, cookie=cookie)
    if result and result.get("valid"):
        return result.get("result", {}).get("totalCount")
    return None


def update_md_file(md_path: Path, courses: list[dict], cookie: str | None = None) -> bool:
    """更新单个 .md 文件，为每个题型的第四列填入数量。"""
    text = md_path.read_text(encoding="utf-8")
    updated = False

    # 1. 更新表头：添加「题目数量」列（如果还没有）
    old_header = "| typeId | 题型 | 客观题 |"
    new_header = "| typeId | 题型 | 客观题 | 题目数量 |"
    old_sep = "|--------|------|--------|"
    new_sep = "|--------|------|--------|---------|"

    if new_header not in text:
        text = text.replace(old_header, new_header)
        updated = True
    # 分隔线可能已被扩展
    text = text.replace(old_sep, new_sep)

    # 2. 查询并填入数量
    for course in courses:
        course_id = course["course_id"]
        for t in course["types"]:
            type_id = t["type_id"]

            # 查询数量
            count = query_count(course_id, type_id, cookie)
            count_str = str(count) if count is not None else "-"
            print(f"  {course['name']} | {t['type_name']} (typeId={type_id}): {count_str}")

            # 匹配已有行（可能已有旧的数量值）
            pattern = re.compile(
                rf'\| {type_id} \| {re.escape(t["type_name"])} \| (yes|no) \|.*',
            )
            replacement = f"| {type_id} | {t['type_name']} | \\1 | {count_str} |"
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                updated = True
                text = new_text
            else:
                # 原行无第四列 → 追加
                old_row = f"| {type_id} | {t['type_name']} | {t['objective']} |"
                new_row = f"| {type_id} | {t['type_name']} | {t['objective']} | {count_str} |"
                if old_row in text:
                    text = text.replace(old_row, new_row)
                    updated = True

    if updated:
        md_path.write_text(text, encoding="utf-8")
        print(f"  [OK] {md_path.name}")
    else:
        print(f"  - 无需更新 {md_path.name}")

    return updated


def main():
    import os

    cookie = os.environ.get("XKW_COOKIE")
    if not cookie:
        # 尝试从 config.json 读取
        import json
        config_path = BASE / "02_配置资源" / "config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            cookie = config.get("xkw_cookie", "")
    if not cookie:
        print("⚠ 未找到 Cookie（环境变量 XKW_COOKIE 或 config.json xkw_cookie），将继续但 API 可能失败。")

    targets = sys.argv[1:] if len(sys.argv) > 1 else sorted(MAPPING_DIR.glob("*.md"))
    for target in targets:
        path = Path(target) if isinstance(target, str) else target
        if not path.exists():
            print(f"⚠ 文件不存在：{path}")
            continue
        print(f"\n处理：{path.name}")
        courses = parse_md_tables(path)
        if not courses:
            print("  未找到课程表头，跳过")
            continue

        update_md_file(path, courses, cookie)

    print("\n完成。")


if __name__ == "__main__":
    main()
