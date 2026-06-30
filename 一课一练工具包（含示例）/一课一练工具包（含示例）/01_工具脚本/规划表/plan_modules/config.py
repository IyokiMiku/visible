"""Shared configuration and path helpers for planning-table generation."""

import re
from pathlib import Path

from planning_assets import split_province_category as _asset_split_province_category

BASE_DIR = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "02_配置资源" / "config.json"


def split_province_category(title_prefix):
    """从标题前缀中解析省份和考类，如“重庆市机械加工类”，兼容自治区简称/全称。"""
    province, category = _asset_split_province_category(title_prefix)
    if province and category:
        return province, category
    text = (title_prefix or "").strip()
    m = re.search(r"([一-龥]+(?:省|市))([一-龥]+类)", text)
    if m:
        return m.group(1), m.group(2)
    return "", ""


def safe_path_part(text):
    """清理路径非法字符。"""
    text = (text or "").strip()
    return re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_") or "未分类"
