"""按知识点（kpointId）查询各类型题目数量，输出汇总表格。

对知识树中每个叶子 kpoint，逐题型查询 API totalCount，输出到 .md 文件。

用法：
  python kpoint_type_summary.py 电工技术基础与技能 [课程名2 ...]
  
  不传课程名则查询全部已映射课程。
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent.parent
KPOINT_DIR = BASE / "02_配置资源" / "学科网映射" / "knowledge_points"
OUTPUT_DIR = BASE / "05_项目文档" / "知识点题目数量"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BASE / "01_工具脚本" / "学科网API拉题移植版"))
from query_questions import build_payload, query as api_query, DEFAULT_APP_KEY, DEFAULT_SIGN
from kpoint_resolver import load_kpoint_tree, resolve_course, resolve_type


def load_cookie() -> str:
    import os
    cookie = os.environ.get("XKW_COOKIE", "")
    if not cookie:
        config_path = BASE / "02_配置资源" / "config.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            cookie = config.get("xkw_cookie", "")
    return cookie


def get_kpoint_name(kpoint_id: int, tree: list[dict]) -> str:
    for node in tree:
        if node["id"] == kpoint_id:
            return node["name"]
    return str(kpoint_id)


def get_leaf_kpoints(tree: list[dict]) -> list[int]:
    """获取知识树中所有叶子节点的 kpointId。"""
    all_ids = {node["id"] for node in tree}
    parent_ids = {node["parent_id"] for node in tree if node.get("parent_id")}
    return sorted(all_ids - parent_ids)


def get_course_types(course_name: str) -> dict[str, str]:
    """从大类 .md 文件中读取课程题型映射 {题型名: typeId}。"""
    import os
    for md_file in (BASE / "02_配置资源" / "学科网映射").glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        # 找到课程章节
        pattern = rf"###\s+{re.escape(course_name)}\s*\(courseId=\d+\)(.*?)(?=###|\Z)"
        m = re.search(pattern, text, re.S)
        if not m:
            continue
        section = m.group(1)
        types = {}
        for row_match in re.finditer(r"\|\s*(\d+)\s*\|\s*(\S+)\s*\|", section):
            type_id = row_match.group(1)
            type_name = row_match.group(2)
            types[type_name] = type_id
        return types
    return {}


def query_kpoint_type_counts(
    course_id: int,
    kpoint_ids: dict[int, str],  # {kpointId: kpoint名称}
    type_map: dict[str, str],     # {题型名: typeId}
    cookie: str,
) -> dict[int, dict[str, int]]:
    """对每个 kpointId × 每个 typeId 查询总数量。"""
    result: dict[int, dict[str, int]] = defaultdict(dict)
    total = len(kpoint_ids) * len(type_map)
    done = 0

    for kpid, kpname in kpoint_ids.items():
        for type_name, type_id_str in type_map.items():
            done += 1
            try:
                payload = build_payload(
                    course_id=course_id,
                    kpoint_ids=[kpid],
                    type_ids=[int(type_id_str)],
                    page_size=1,
                )
                resp = api_query(payload, app_key=DEFAULT_APP_KEY, sign=DEFAULT_SIGN, cookie=cookie)
                if resp and resp.get("valid"):
                    count = resp.get("result", {}).get("totalCount", 0)
                    result[kpid][type_name] = count
                else:
                    result[kpid][type_name] = -1  # API 失败
            except Exception:
                result[kpid][type_name] = -1

            if done % 50 == 0 or done == total:
                print(f"  [{done}/{total}] {kpname[:12]} {type_name}: {result[kpid].get(type_name, '?')}")

    return dict(result)


def get_all_tree_ids(tree: list[dict]) -> list[dict]:
    """返回知识树中所有节点（按 level 和 id 排序）。"""
    return sorted(tree, key=lambda n: (n["level"], n["id"]))


def rollup_parent_counts(
    tree: list[dict],
    leaf_counts: dict[int, dict[str, int]],
) -> dict[int, dict[str, int]]:
    """将叶子数量汇总到父节点（非叶节点的数量 = 所有后代叶子数量之和）。"""
    from collections import defaultdict
    
    # 构建父子关系
    children_map: dict[int, list[int]] = defaultdict(list)
    for node in tree:
        pid = node.get("parent_id")
        if pid:
            children_map[pid].append(node["id"])
    
    result = dict(leaf_counts)
    
    # 递归汇总
    def sum_children(kpid: int) -> dict[str, int]:
        if kpid in result:
            return result[kpid]
        total: dict[str, int] = defaultdict(int)
        for child_id in children_map.get(kpid, []):
            child_sum = sum_children(child_id)
            for t, c in child_sum.items():
                total[t] = total.get(t, 0) + c
        result[kpid] = dict(total)
        return result[kpid]
    
    # 从根节点开始汇总
    for node in tree:
        if node.get("parent_id") is None:
            sum_children(node["id"])
    
    return result


def render_markdown(
    course_name: str,
    course_id: int,
    tree: list[dict],
    type_map: dict[str, str],
    leaf_counts: dict[int, dict[str, int]],
) -> str:
    """生成 Markdown 汇总表（树形层级展开，显示包含关系）。"""
    all_counts = rollup_parent_counts(tree, leaf_counts)
    all_nodes = get_all_tree_ids(tree)
    type_order = list(type_map.keys())

    # 构建父子关系
    children_map: dict[int, list[int]] = {}
    for node in all_nodes:
        pid = node.get("parent_id")
        if pid:
            children_map.setdefault(pid, []).append(node["id"])

    leaf_count = sum(1 for n in all_nodes if not children_map.get(n["id"]))
    parent_count = len(all_nodes) - leaf_count

    lines = [
        f"# {course_name} 知识点题目数量汇总",
        f"",
        f"- courseId: {course_id}",
        f"- 节点总数: {len(all_nodes)}（父节点 {parent_count} + 叶节点 {leaf_count}）",
        f"- 题型: {', '.join(type_order)}",
        f"- 父节点数量 = 所有后代叶子之和",
        f"",
    ]

    # 递归渲染子树
    type_header = " | " + " | ".join(type_order) + " | 合计 |"
    type_sep = "|" + "|".join("---:" for _ in type_order) + "|-----:|"

    def render_subtree(parent_id: int | None, level: int, seq: list[int]) -> None:
        children = children_map.get(parent_id, [])
        if not children:
            return
        
        for child_id in sorted(children):
            child = next((n for n in all_nodes if n["id"] == child_id), None)
            if not child:
                continue
            seq[0] += 1
            row = all_counts.get(child_id, {})
            cells = [str(row.get(t, 0)) for t in type_order]
            total = sum(v for v in row.values() if v > 0)
            has_children = bool(children_map.get(child_id))

            if has_children:
                # 父节点：作为章节标题
                indent = "#" * min(level + 2, 5)
                lines.append(f"{indent} {child['name']} ({child_id})")
                lines.append(f"- 合计: {total} 题")
                lines.append(f"")
                lines.append(f"| 节点ID | 知识点 |{type_header}")
                lines.append(f"|--------|--------|{type_sep}")
                render_subtree(child_id, level + 1, seq)
                lines.append("")
            else:
                # 叶子节点：表格行
                lines.append(f"| {child_id} | {child['name']} | {' | '.join(cells)} | {total} |")

    seq = [0]
    # 找到根节点（L1）开始渲染
    roots = [n for n in all_nodes if n.get("parent_id") is None]
    for root in roots:
        row = all_counts.get(root["id"], {})
        total = sum(v for v in row.values() if v > 0)
        children = children_map.get(root["id"], [])
        if children:
            # 有子节点 → 作为章节标题
            indent = "#" * 2  # ## level
            lines.append(f"{indent} {root['name']} ({root['id']})")
            lines.append(f"- 合计: {total} 题")
            lines.append(f"")
            lines.append(f"| 节点ID | 知识点 |{type_header}")
            lines.append(f"|--------|--------|{type_sep}")
        render_subtree(root["id"], 1, seq)
        if children:
            lines.append("")

    return "\n".join(lines) + "\n"


def main():
    cookie = load_cookie()
    if not cookie:
        print("未找到 Cookie")
        return

    target_courses = sys.argv[1:] if len(sys.argv) > 1 else None
    if target_courses:
        print(f"目标课程: {', '.join(target_courses)}")
    else:
        print("处理全部已映射课程（可能耗时较长）")

    for md_file in sorted((BASE / "02_配置资源" / "学科网映射").glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        # 找所有课程
        for cm in re.finditer(r"###\s+(.+?)\s*\(courseId=(\d+)\)", text):
            course_name = cm.group(1).strip()
            course_id = int(cm.group(2))

            if target_courses and course_name not in target_courses:
                continue

            print(f"\n=== {course_name} (courseId={course_id}) ===")

            # 加载知识树
            tree = load_kpoint_tree(course_name)
            if not tree:
                print(f"  无知识树，跳过")
                continue

            leaf_ids = get_leaf_kpoints(tree)
            print(f"  叶子知识点: {len(leaf_ids)} 个")

            # 获取题型
            type_map = get_course_types(course_name)
            if not type_map:
                print(f"  无题型映射，跳过")
                continue
            print(f"  题型: {len(type_map)} 种")

            # 查询
            kpoint_map = {kpid: get_kpoint_name(kpid, tree) for kpid in leaf_ids}
            counts = query_kpoint_type_counts(course_id, kpoint_map, type_map, cookie)

            # 输出（含父节点汇总）
            md_content = render_markdown(course_name, course_id, tree, type_map, counts)
            # 检查是否已有文档
            out_path = OUTPUT_DIR / f"{course_name}_知识点题目数量.md"
            if out_path.exists():
                print(f"  [跳过] {out_path.name} 已存在")
                continue
            out_path.write_text(md_content, encoding="utf-8")
            print(f"  [OK] {out_path}")

    print("\n完成。")


if __name__ == "__main__":
    main()
