"""规划表校验器（CD3，硬拦截）。

对 LLM/解析得到的行做确定性规则校验；命中「严重」问题即拦截（不放行、进闸门复核）。
语义类判断（如“内容相近”）代码无法确定，标记为 need_human（仅人工确认可放行），不算严重。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from shared.planning.schema import LEVELS

SEVERE = "严重"
WARN = "警告"
HUMAN = "待人工"

_END_PERIOD = re.compile(r"[。.．]\s*$")


@dataclass
class Issue:
    severity: str
    code: str
    detail: str
    row_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "code": self.code, "detail": self.detail, "row_index": self.row_index}


@dataclass
class ValidateResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def severe(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == SEVERE]

    @property
    def blocked(self) -> bool:
        """存在严重问题 → 硬拦截，不允许放行。"""
        return len(self.severe) > 0

    def to_dict(self) -> dict[str, Any]:
        return {"blocked": self.blocked, "issues": [i.to_dict() for i in self.issues]}


def _core_topic_len(topic: str) -> int:
    """主题核心长度（不含（一）(二) 后缀）。"""
    core = re.sub(r"[（(][一二三四五六七八九十\d]+[)）]\s*$", "", topic).strip()
    return len(core)


# ---------------- 一课一练（含考点双析卷）扁平表 ----------------
def validate_yikeyilian(rows: list[dict[str, Any]], *, topic_max: int = 10,
                        require_critical_pairs: bool = True) -> ValidateResult:
    """校验扁平考点行。require_critical_pairs：一课一练=True（极重要须成对拆行）；
    考点双析卷=False（拆分在教师/学生奇偶层面，主题不拆（一）（二））。"""
    res = ValidateResult()
    if not rows:
        res.issues.append(Issue(SEVERE, "empty", "规划表为空"))
        return res

    # A 序号连续从 1
    nos = [r.get("paper_no") for r in rows]
    if any(n is None for n in nos):
        res.issues.append(Issue(SEVERE, "seq_missing", "存在缺少序号的考点行"))
    else:
        expected = list(range(1, len(rows) + 1))
        if nos != expected:
            res.issues.append(Issue(SEVERE, "seq_not_continuous", f"序号非从1连续：{nos[:3]}...{nos[-2:]}"))

    for i, r in enumerate(rows):
        level = r.get("level", "")
        if level not in LEVELS:
            res.issues.append(Issue(SEVERE, "bad_level", f"级别非法：{level!r}", i))
        # B 去尾句号
        if _END_PERIOD.search(str(r.get("point_name", ""))):
            res.issues.append(Issue(SEVERE, "point_end_period", "考纲知识点末尾含句号", i))
        # C 字数
        if _core_topic_len(str(r.get("topic", ""))) > topic_max:
            res.issues.append(Issue(WARN, "topic_too_long", f"试卷主题核心>{topic_max}字：{r.get('topic')}", i))
        if not str(r.get("topic", "")).strip():
            res.issues.append(Issue(SEVERE, "topic_empty", "试卷主题为空", i))

    # 极重要必须成对（同知识点连续两行，主题带（一）（二））——仅一课一练
    if require_critical_pairs:
        _check_critical_pairs(rows, res)
    return res


def validate_shuangxi(rows: list[dict[str, Any]], *, topic_max: int = 12) -> ValidateResult:
    """考点双析卷：扁平逐行校验（序号连续/级别/去尾句号/主题字数），不要求极重要成对。"""
    return validate_yikeyilian(rows, topic_max=topic_max, require_critical_pairs=False)


def _check_critical_pairs(rows: list[dict[str, Any]], res: ValidateResult) -> None:
    i = 0
    n = len(rows)
    while i < n:
        if rows[i].get("level") == "极重要":
            # 期望与下一行成对：同 point_name，主题分别 (一)(二)
            if i + 1 >= n or rows[i + 1].get("level") != "极重要" \
               or rows[i + 1].get("point_name") != rows[i].get("point_name"):
                res.issues.append(Issue(SEVERE, "critical_not_paired",
                                        f"极重要考点未成对拆分：{rows[i].get('topic')}", i))
                i += 1
                continue
            t1, t2 = str(rows[i].get("topic", "")), str(rows[i + 1].get("topic", ""))
            if not (re.search(r"[（(]一[)）]\s*$", t1) and re.search(r"[（(]二[)）]\s*$", t2)):
                res.issues.append(Issue(WARN, "critical_suffix",
                                        f"极重要两行主题应带（一）（二）：{t1}/{t2}", i))
            i += 2
        else:
            i += 1


# ---------------- 考纲百套卷 10 列 + 映射 ----------------
def validate_kaogang(rows: list[dict[str, Any]]) -> ValidateResult:
    res = ValidateResult()
    if not rows:
        res.issues.append(Issue(SEVERE, "empty", "规划表为空"))
        return res
    for i, r in enumerate(rows):
        # A⊃B⊃C⊃D：各层非空
        for key, name in (("course", "知识模块"), ("theme", "专题"), ("point_name", "考点名称")):
            if not str(r.get(key, "")).strip():
                res.issues.append(Issue(SEVERE, "hierarchy_missing", f"缺{name}", i))
        # D 末尾无句号
        for ln in str(r.get("knowledge", "")).splitlines():
            if _END_PERIOD.search(ln):
                res.issues.append(Issue(SEVERE, "knowledge_end_period", f"知识点末尾含句号：{ln}", i))
                break
    return res


def validate_volume_numbers(paper_nos: list[int]) -> ValidateResult:
    """卷号全局：无重复、无跳号（1..N 连续）。"""
    res = ValidateResult()
    if not paper_nos:
        res.issues.append(Issue(SEVERE, "empty", "无卷号"))
        return res
    if len(set(paper_nos)) != len(paper_nos):
        dup = sorted({n for n in paper_nos if paper_nos.count(n) > 1})
        res.issues.append(Issue(SEVERE, "vol_dup", f"卷号重复：{dup}"))
    s = sorted(paper_nos)
    if s != list(range(s[0], s[0] + len(s))):
        res.issues.append(Issue(SEVERE, "vol_gap", "卷号存在跳号"))
    return res


def validate_mapping(map_rows: list[dict[str, Any]], all_vols: set[str],
                     tree_level_of=None) -> ValidateResult:
    """映射表校验：禁 L1、A 列覆盖全部试卷、聚合ID为其来源并集去重（结构层面）。

    tree_level_of：可选 id->level 查询；提供时校验 AI匹配未落到 L1（level==1）。
    """
    res = ValidateResult()
    covered = {r.get("vol") for r in map_rows}
    missing = all_vols - covered
    if missing:
        res.issues.append(Issue(SEVERE, "vol_not_covered", f"映射表未覆盖试卷：{sorted(missing)[:5]}"))
    for i, r in enumerate(map_rows):
        method = r.get("method")
        ids = r.get("ids") or []
        if method == "AI匹配" and not ids:
            res.issues.append(Issue(SEVERE, "ai_match_no_id", f"{r.get('vol')} 标 AI匹配 但无 ID", i))
        if method == "AI生成" and ids:
            res.issues.append(Issue(WARN, "ai_gen_has_id", f"{r.get('vol')} 标 AI生成 却有 ID", i))
        if tree_level_of and method == "AI匹配":
            l1 = [x for x in ids if tree_level_of(x) == 1]
            if l1:
                res.issues.append(Issue(SEVERE, "map_hit_l1", f"{r.get('vol')} 命中 L1 根节点：{l1}", i))
    return res
