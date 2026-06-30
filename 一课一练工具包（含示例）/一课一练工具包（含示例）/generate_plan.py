"""Root entrypoint for generating 一课一练考点规划表.

This wrapper keeps the frequently used command short:

    python generate_plan.py --pdf "03_项目数据/考试说明/某考试说明.pdf" --title "重庆市机械加工类"

The real implementation lives in:

    01_工具脚本/规划表/generate_plan.py

规划表标题层级约定（供 create.py 生成试卷标题时识别）：
  - 两级标题模板：节标题行 + 考点行。试卷标题第三行输出为
    “第y节 节主题 第x练 试卷主题”，其中 y、x 均使用阿拉伯数字。
  - 三级标题模板：单元行 + 节标题行 + 考点行。试卷标题第二行追加试卷主题，
    第三行输出为“第X单元 单元名称 第x节 节主题 第y练”，其中 X 使用中文大写
    序号（一、二、三……），x、y 使用阿拉伯数字。
"""

from pathlib import Path
import runpy


TARGET = Path(__file__).resolve().parent / "01_工具脚本" / "规划表" / "generate_plan.py"

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
