"""刷新「课程(courseId) → 顶级题型(typeId, name)」目录（configs/xueke_mapping/课程题型.json）。

数据源：学科网组卷基础数据接口 zujuan-api/base，返回全量 edu 树
（edu[].QuesBankList[] 为课程，QuesTypeList[] 为题型；pId==0 即顶级题型）。
本工具只保留中职专业课（courseType==2）的顶级题型，不含子类。

用法（在 backend 目录下）：
    python -m shared.xueke_api.refresh_course_types

需要在「全局设置」或 .env 配置学科网 Cookie（XKW_COOKIE）。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

import config

BASE_URL = "https://zhijiao.xkw.com/zujuan-api/base"
# 中职专业课标记：QuesBankList[].courseType==2（公共基础课为 1）。
_VOCATIONAL_COURSE_TYPE = 2
OUTPUT_PATH = config.BASE_DIR / "configs" / "xueke_mapping" / "课程题型.json"


def fetch_text(cookie: str, timeout: int = 30) -> str:
    """调用接口取原始响应文本（可能是 JSON，也可能是含 `var edu = [...]` 的 JS）。"""
    req = urllib.request.Request(BASE_URL, method="GET")
    req.add_header("Accept", "application/json, text/plain, */*")
    req.add_header("User-Agent", "Mozilla/5.0 exam-production-studio/1.0")
    req.add_header("Referer", "https://zhijiao.xkw.com/")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误：{e.reason}") from e


def _extract_array(text: str, var_name: str) -> list | None:
    """从 JS 文本里按 `var <name> = [ ... ]` 提取数组（括号配平扫描，容忍字符串内的括号）。"""
    marker = f"{var_name}"
    idx = text.find(marker)
    while idx != -1:
        start = text.find("[", idx)
        if start == -1:
            return None
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
        idx = text.find(marker, idx + 1)
    return None


def parse_edu(text: str) -> list:
    """把响应文本解析成 edu 列表（edu[].QuesBankList[].QuesTypeList[]）。"""
    stripped = text.lstrip()
    if stripped[:1] in "[{":
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("edu", "data", "Edu", "list"):
                val = data.get(key)
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    inner = val.get("edu") or val.get("list")
                    if isinstance(inner, list):
                        return inner
    edu = _extract_array(text, "var edu")
    if edu is None:
        edu = _extract_array(text, '"edu"')
    return edu or []


def to_course_types(edu: list) -> dict[str, Any]:
    """edu 树 → {courses:[{courseId, courseName, types:[{typeId,name}]}]}（仅中职专业课、仅顶级题型）。"""
    courses: list[dict[str, Any]] = []
    seen: set[int] = set()
    for node in edu:
        for bank in (node.get("QuesBankList") or []) if isinstance(node, dict) else []:
            if bank.get("courseType") != _VOCATIONAL_COURSE_TYPE:
                continue
            cid = bank.get("courseId")
            if cid is None or cid in seen:
                continue
            types = [
                {"typeId": t.get("ID"), "name": (t.get("Name") or "").strip()}
                for t in (bank.get("QuesTypeList") or [])
                if t.get("pId") == 0 and t.get("ID") is not None
            ]
            if not types:
                continue
            seen.add(cid)
            courses.append({
                "courseId": cid,
                "courseName": (bank.get("Name") or "").strip(),
                "types": types,
            })
    courses.sort(key=lambda c: c["courseId"])
    return {
        "source": BASE_URL,
        "note": "中职专业课「课程(courseId) → 顶级题型(typeId, name)」目录，仅顶级题型、不含子类。"
                "用于按 courseId 精确解析拉题 typeId。由 refresh_course_types.py 生成。",
        "courses": courses,
    }


def main() -> int:
    cfg = config.get_xueke_config()
    cookie = cfg.get("cookie")
    if not cookie:
        print("未配置学科网 Cookie（请在全局设置或 .env 填写 XKW_COOKIE）", file=sys.stderr)
        return 2
    try:
        text = fetch_text(cookie)
    except RuntimeError as e:
        print(f"抓取失败：{e}", file=sys.stderr)
        return 1
    edu = parse_edu(text)
    if not edu:
        print("解析失败：未能从响应中提取 edu 数据（接口结构可能已变化）", file=sys.stderr)
        return 1
    result = to_course_types(edu)
    if not result["courses"]:
        print("解析成功但未找到中职专业课（courseType==2）课程，未写入。", file=sys.stderr)
        return 1
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_course = len(result["courses"])
    n_type = sum(len(c["types"]) for c in result["courses"])
    print(f"已刷新：{OUTPUT_PATH}（{n_course} 门课程，顶级题型 {n_type} 个）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
