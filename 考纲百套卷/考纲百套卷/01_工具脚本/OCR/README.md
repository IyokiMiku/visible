# OCR 方案说明与部署

本目录用于处理图片型 PDF 的文字提取，服务于“真题风格库”建设。

## 对网页方案的判断

你给的网页主要介绍的是 **GLM-5 + GLM-OCR** 的文档解析方案：

1. 用 GLM-OCR 对扫描版/复杂排版 PDF 做高精度版面识别，输出结构化 JSON；
2. 再用 GLM-5 根据标题、段落、列表等结构生成 QA 数据集；
3. 后续还可结合 RAG、Agent 校验、长上下文生成跨章节问答。

这个方向对“企业文档自动生成 QA 数据集”很强，但对你当前的目标——**从图片型真题 PDF 中提取少量样题，蒸馏成真题风格库**——有点偏重。

### 适合的部分

- GLM-OCR 做版面结构识别的思路是对的；
- 对扫描版 PDF，结构化 OCR 比普通逐字 OCR 更适合保留题号、选项、段落；
- “OCR 后再蒸馏为风格/QA”的流程与你的真题风格库思路一致。

### 不适合直接照搬的部分

- GLM-OCR 通常需要较重的部署环境，可能依赖 GPU、vLLM、Linux/WSL 或容器；
- Windows 本地直接部署成本较高；
- 你的需求不需要生成完整 QA 数据集，也不需要全量解析所有 PDF；
- 全量 OCR 仍会消耗较大，并且会把很多无关内容带入后续 prompt。

## 本目录采用的落地策略

首版采用更轻量、可在 Windows 本地运行的 OCR 管线：

```text
图片型 PDF
  ↓ PyMuPDF 按页转图片
页面图片
  ↓ RapidOCR 本地识别
按页 txt/json/md
  ↓ 人工抽取/校对少量代表题
真题样本.txt
  ↓ ../extract_exam_style.py 蒸馏
03_项目数据/参考资料/真题风格/*.txt
```

这样做的好处：

- 不需要一开始部署重型 GLM-OCR；
- 可以先把图片型 PDF 变成可搜索文本；
- OCR 结果只作为“摘录样题”的辅助，不直接作为最终知识依据；
- 后续如果你有 GPU/WSL 环境，再把 GLM-OCR 接入为高级后端。

## 安装

在 `OCR/` 目录下执行：

```bash
pip install -r requirements.txt
```

如果安装 `rapidocr-onnxruntime` 失败，可以先升级 pip：

```bash
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
```

## 使用方法

### 1. OCR 整个 PDF

```bash
python ocr_pdf.py --pdf "../真题PDF/2024年真题.pdf" --output-dir "output/2024真题"
```

输出：

```text
output/2024真题/
├── pages/          # 每页图片
├── json/           # 每页 OCR 结构化结果
├── txt/            # 每页纯文本
├── combined.txt    # 全部页合并文本
└── combined.md     # 带页码的合并文本
```

### 2. 只 OCR 指定页

```bash
python ocr_pdf.py --pdf "../真题PDF/2024年真题.pdf" --pages 1,3,5-8 --output-dir "output/2024真题_抽样"
```

### 3. 从 OCR 结果中人工整理样题

打开：

```text
output/2024真题_抽样/combined.md
```

人工复制 5～20 道代表题，保存为：

```text
真题样本.txt
```

建议只保留：

- 题干；
- 选项；
- 答案；
- 必要时保留解析；
- 不需要整卷全文。

### 4. 蒸馏成真题风格库

回到上一级 `wyy/` 目录，执行：

```bash
python 01_工具脚本/真题风格/extract_exam_style.py --sample "OCR/真题样本.txt" --category "重庆市汽车类" --output "03_项目数据/参考资料/真题风格/重庆市汽车类_风格总结.txt"
```

之后 `create.py` 会自动匹配并加载该风格库。

## 何时考虑 GLM-OCR

如果后续你发现 RapidOCR 对你的真题 PDF 效果不够，且你有以下环境：

- NVIDIA GPU；
- WSL2/Linux 或 Docker；
- 能接受较大的模型下载和部署成本；

可以考虑把 GLM-OCR 作为高级 OCR 后端。建议仍然保持当前流程：

```text
GLM-OCR 只负责抽取代表页结构化文本 → 人工校对少量样题 → 蒸馏风格库
```

不要把整本 PDF 的 GLM-OCR 结果直接塞进出题 prompt。
