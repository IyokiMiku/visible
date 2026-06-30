"""生成器路径常量。"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "02_配置资源" / "config.json"
SPEC_PATH = BASE_DIR / "02_配置资源" / "编写规范" / "编写规范.md"
TEMPLATE_PATH = BASE_DIR / "02_配置资源" / "模板和资源" / "template.docx"
SEPARATOR_PATH = BASE_DIR / "02_配置资源" / "模板和资源" / "separator.png"
QUESTION_TYPES_DIR = BASE_DIR / "02_配置资源" / "题型定义"
REF_DIR = BASE_DIR / "03_项目数据" / "参考资料"
USAGE_FILE = BASE_DIR / ".token_usage.json"
