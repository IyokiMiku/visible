"""刷新「专业大类 → 专业 → 课程」目录（configs/xueke_mapping/专业课程树.json）。

数据源：学科网组卷页接口 profession-big-types，一次请求即返回全国完整目录（与省份无关，
URL 里的 provinceId/courseId/majorId 只影响 selected 标记，不影响树内容）。

用法（在 backend 目录下）：
    python -m shared.xueke_api.refresh_profession_tree

需要在「全局设置」或 .env 配置学科网 Cookie（XKW_COOKIE）。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import config

TREE_URL = "https://zhijiao.xkw.com/api/v1/basic/profession-course/profession-big-types"
# 全国目录与省份无关，取任意有效省份即可；110000=北京。
_DEFAULT_PROVINCE_ID = 110000
OUTPUT_PATH = config.BASE_DIR / "configs" / "xueke_mapping" / "专业课程树.json"


def fetch_raw(cookie: str, province_id: int = _DEFAULT_PROVINCE_ID, timeout: int = 30) -> dict:
    """调用接口取原始响应（{code,data,message}）。"""
    ts = int(time.time() * 1000)
    url = f"{TREE_URL}?provinceId={province_id}&searchFlag=true&_={ts}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json, text/plain, */*")
    req.add_header("User-Agent", "Mozilla/5.0 exam-production-studio/1.0")
    req.add_header("Referer", "https://zhijiao.xkw.com/")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误：{e.reason}") from e


def to_tree(raw: dict) -> dict:
    """原始响应 → 精简目录结构（categories[].professions[].courses[]）。"""
    categories = []
    for cat in raw.get("data") or []:
        professions = []
        for prof in cat.get("professions") or []:
            courses = [
                {"courseId": c.get("courseId"), "courseName": (c.get("courseName") or "").strip()}
                for c in (prof.get("courses") or [])
                if c.get("courseId") is not None
            ]
            professions.append({
                "id": prof.get("id"),
                "name": (prof.get("name") or "").strip(),
                "courses": courses,
            })
        categories.append({
            "id": cat.get("id"),
            "name": (cat.get("name") or "").strip(),
            "professions": professions,
        })
    return {
        "source": TREE_URL,
        "note": "全国中职「专业大类 → 专业 → 课程」目录（含学科网 courseId）。全国通用静态数据，"
                "与省份无关；课程以 courseId 为准。由 refresh_profession_tree.py 生成。",
        "categories": categories,
    }


def main() -> int:
    cfg = config.get_xueke_config()
    cookie = cfg.get("cookie")
    if not cookie:
        print("未配置学科网 Cookie（请在全局设置或 .env 填写 XKW_COOKIE）", file=sys.stderr)
        return 2
    try:
        raw = fetch_raw(cookie)
    except RuntimeError as e:
        print(f"抓取失败：{e}", file=sys.stderr)
        return 1
    if raw.get("code") != 200 or not raw.get("data"):
        print(f"接口返回异常：code={raw.get('code')} message={raw.get('message')}", file=sys.stderr)
        return 1
    tree = to_tree(raw)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(tree, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_cat = len(tree["categories"])
    n_course = sum(len(p["courses"]) for c in tree["categories"] for p in c["professions"])
    print(f"已刷新：{OUTPUT_PATH}（{n_cat} 个大类，课程条目 {n_course} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
