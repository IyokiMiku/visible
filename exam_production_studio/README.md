# 出卷集成工作台 / Exam Production Studio

统一"学科网 API 拉题 → 不足 AI 补题"的出卷工作台，支持三类试卷：**一课一练 / 考纲百套卷 / 考点双析卷**。
所有业务变量经界面设置，路径/命令行参数由后端生成；凭据外置到 `settings` 表与 `.env`，源码不留明文。

## 目录结构

```
exam_production_studio/
├── backend/
│   ├── main.py              FastAPI 入口（同时托管前端 dist）
│   ├── config.py            密钥/配置加载（settings 表 > .env > 默认）
│   ├── db.py                SQLite 建表与读写
│   ├── routers/             projects/resources/flow/review/qc/artifacts/settings/ws
│   ├── engine/              context/registry/runner/review/repo + drivers/ + steps/
│   └── shared/              xueke_api / docx / qc / ai / ocr（去硬编码共享模块）
├── frontend/                Vue3 + Element Plus + Vite（构建产物在 dist/）
├── configs/{kaogang_100,shuangxi,yikeyilian}/  类型配置 + 模板 + 编写规范 + 题型定义
├── data/                    studio.db + projects/{id}/ 产物树
└── .env.example             环境变量样例（无真实值）
```

## 环境变量（`.env`）

复制 `.env.example` 为 `.env` 并按需填写（也可改在「全局设置」页填写，存入 `settings` 表）：

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | LLM 凭据（AI 补题/映射） |
| `XKW_COOKIE` / `XKW_APP_KEY` / `XKW_SIGN` | 学科网凭据（拉题） |
| `VISION_*` | 视觉模型（预留，暂不启用） |
| `STUDIO_DB` | SQLite 路径，默认 `data/studio.db` |

> 未配置 LLM/学科网凭据时系统可离线跑通：拉题命中 0 → AI 补题；AI 未配置 → 生成占位题并标记「待人工确认」。

## 一键启动（推荐，自动建 venv / 装依赖）

- Windows：双击或运行 `start.bat`
- macOS / Linux：`chmod +x start.sh && ./start.sh`

脚本会在首次运行时自动创建 `.venv`、安装前后端依赖，然后同时启动后端(:8000)与前端(:5173)。
浏览器打开 http://localhost:5173 即可。

VS Code 调试：打开项目后在「运行和调试」选择 **调试后端 (uvicorn)** 即可断点调试（配置见 `.vscode/launch.json`；前端另开终端 `npm run dev`）。

## 打包分发到其他电脑（源码包，可调试）

不要直接拷贝 `.venv` 和 `frontend/node_modules`（含本机绝对路径/平台二进制，跨机不可用）。
用打包脚本生成**干净源码包**：

```bat
.\package.bat
```

会在上级目录生成 `exam_production_studio_src.zip`（已排除 `.venv` / `node_modules` / `dist` / `data\studio.db` / `data\projects` / `__pycache__` / `.env`，约 0.5 MB）。

目标 Windows 电脑上：
1. 安装 **Python 3.10+** 和 **Node 18+**（仅一次）；
2. 解压该 zip；
3. 运行 `exam_production_studio\start.bat`——**首次运行会自动创建 venv 并安装前后端依赖**（需联网，几分钟），之后即可正常运行与断点调试。

## 运行（开发模式 · 手动）

```bash
# 后端（项目根创建 venv，已含 backend/requirements.txt）
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python -m uvicorn main:app --app-dir backend --port 8000

# 前端（代理 /api、/ws → :8000）
cd frontend && npm install && npm run dev
```

- 前端开发地址：http://localhost:5173
- 后端 API/文档：http://127.0.0.1:8000/docs

## 运行（集成单服务）

```bash
cd frontend && npm run build          # 产出 frontend/dist
.venv\Scripts\python -m uvicorn main:app --app-dir backend --port 8000
# 浏览器访问 http://127.0.0.1:8000/ （FastAPI 直接托管前端）
```

## 打包（可选，9.2）

- 前端：`npm run build` → `frontend/dist`，由 FastAPI 静态托管。
- 后端：可用 PyInstaller 打包 `backend/main.py`（需把 `configs/`、`frontend/dist` 作为数据文件一并打入）。

## 验证基线（设计文档 §10.3）

- 三类型各跑通：创建项目 → 流程执行 →（命中一次待确认暂停）→ 质检 → 输出归档。
- 卷号范围 `3,7,12` 仅生成 3 套；双析卷生成 教师/学生 各（解析版+原卷版）共 4 份。
- 所有设置经界面提交，无需手改文件。

## 学科网真实拉题（已接通 HTTP 层）

`shared/xueke_api/` 已移植考纲百套卷「学科网API拉题移植版」的真实接口（`query_questions` HTTP 调用、
`api_pull_core` 分页/校验/题型重分类、`html_content_converter` 题干/选项/答案/解析解析）。
课程ID、题型ID、知识点ID 已可由 `kpoint_resolver` 基于本地映射数据 `configs/xueke_mapping/`
（源自考纲百套卷「学科网映射」：大类 md + knowledge_points 知识点树）**自动解析**：

- **课程ID**：按 `course` 名在大类映射表中解析 courseId（如「电工技术基础与技能」→ 10002）。
- **题型ID**：按题型名同义匹配真实题型表（单项选择题→1000201 等）。
- **知识点ID**：映射阶段按考点名在知识点树中字符串/关键词匹配；未命中且配置 LLM 时 AI 兜底；
  仍未命中则该卷进入待确认(AI_MATCH)。已解析的 kpointId 落库 `papers.kpoint_id` 并写入映射表 xlsx。

因此启用真实拉题通常**只需配置 `XKW_COOKIE`**（外加课程在映射数据中存在）。可选覆盖项：
`ai_options.xueke_course_id`、`ai_options.xueke_type_ids`（手动指定时优先于自动解析）。

> 注：随附映射数据覆盖 8 大类；知识点树覆盖大部分课程，少数课程仅有索引（缺树），
> 这类课程的考点解析将走 AI 兜底/待确认。

## 接入 TODO（线上启用真实能力）

- `shared/ocr/vision.py`：接入视觉 OCR（配置 `VISION_*` 并启用）。
- `configs/shuangxi/`：如有正式双析卷模板/编写规范，替换当前借用考纲的基线。

## 待确认（review）阻塞策略

四类待确认 `AI_MATCH / AI_GENERATE / RULE_CONFLICT / QC_FAIL` **均为阻塞型**：命中即暂停流程，
需在「待确认事项」确认后 `resume` 才继续；每卷产物在暂停前已生成并落库，恢复时跳过已完成卷。
