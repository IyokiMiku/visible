"""一课一练试卷生成器入口。"""
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent
TOOLS_DIR = BASE_DIR / "01_工具脚本"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from 生成器.runner import main


if __name__ == "__main__":
    main()
