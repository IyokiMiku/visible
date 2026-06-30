"""考纲百套卷项目路径常量。"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# 配置资源
CONFIG_DIR = BASE_DIR / "02_配置资源"
CONFIG_PATH = CONFIG_DIR / "config.json"
SPEC_PATH = CONFIG_DIR / "编写规范" / "编写规范.md"
QUESTION_TYPES_DIR = CONFIG_DIR / "题型定义"
TEMPLATE_DIR = CONFIG_DIR / "模板和资源"
TEMPLATE_PATH = TEMPLATE_DIR / "template.docx"
# 新版考纲百套卷模板不再需要标识/分隔图片；该路径仅作为兼容旧脚本的可选资源。
SEPARATOR_PATH = TEMPLATE_DIR / "separator.png"

# 项目数据
DATA_DIR = BASE_DIR / "03_项目数据"
EXAM_OUTLINE_DIR = DATA_DIR / "考试说明"
RAW_DOC_DIR = DATA_DIR / "原始文档"
API_REFERENCE_DIR = DATA_DIR / "题库API"
REF_DIR = DATA_DIR / "参考资料"

# 项目文档
DOC_DIR = BASE_DIR / "05_项目文档"

# 生成输出
OUTPUT_DIR = BASE_DIR / "04_生成输出"
PLAN_DIR = OUTPUT_DIR / "生产规划"
MANUAL_PAPER_DIR = OUTPUT_DIR / "组卷待质检"
CLEAN_OUTPUT_DIR = OUTPUT_DIR / "清洗结果"
QA_REPORT_DIR = OUTPUT_DIR / "质检报告"
FINAL_OUTPUT_DIR = OUTPUT_DIR / "生成结果"
RUN_RECORD_DIR = OUTPUT_DIR / "运行记录"
INTERMEDIATE_OUTPUT_DIR = OUTPUT_DIR / "_临时"
API_RAW_OUTPUT_DIR = INTERMEDIATE_OUTPUT_DIR / "API原始结果"
RAW_QUESTION_DIR = API_RAW_OUTPUT_DIR / "原始题目"
FINAL_TEXT_DIR = INTERMEDIATE_OUTPUT_DIR / "_原始文本"
FINAL_RAW_BANK_DIR = INTERMEDIATE_OUTPUT_DIR / "_原始题库"
FINAL_CLEAN_BANK_DIR = INTERMEDIATE_OUTPUT_DIR / "_清洗后题库"


def manual_paper_dir_for_meta(meta) -> Path:
    """返回按省份/考类分类的组卷待质检目录。

    例：04_生成输出/组卷待质检/重庆市 电子信息类/
    """
    province = _safe_filename_part(getattr(meta, "province", "") or "")
    category = _safe_filename_part(getattr(meta, "exam_category", "") or "")
    if province and category:
        return MANUAL_PAPER_DIR / f"{province} {category}"
    return MANUAL_PAPER_DIR


def _safe_filename_part(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-()（）").strip()

USAGE_FILE = BASE_DIR / ".token_usage.json"


def ensure_output_dirs() -> None:
    """创建运行时需要的输出目录。"""
    for path in [
        PLAN_DIR,
        MANUAL_PAPER_DIR,
        API_RAW_OUTPUT_DIR,
        RAW_QUESTION_DIR,
        CLEAN_OUTPUT_DIR,
        QA_REPORT_DIR,
        FINAL_OUTPUT_DIR,
        RUN_RECORD_DIR,
        INTERMEDIATE_OUTPUT_DIR,
        FINAL_TEXT_DIR,
        FINAL_RAW_BANK_DIR,
        FINAL_CLEAN_BANK_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
