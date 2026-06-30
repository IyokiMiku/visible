# 章节规划：一课一练试卷生成工具包 项目汇报

## 项目类型：项目汇报/总结
## 金字塔结构：经典结构（结论先行）
## 规划页数：16页

---

## Page 1: 封面
- **Page Type**: Cover
- **Page Title**: 一课一练试卷生成工具包
- **Selected Template**: cover/business/041.tpl

- **Content Structure**: 主标题 + 副标题"AI驱动的高职分类考试试卷批量生产系统" + 汇报信息
- **Content Density**: Light
- **Narrative Role**: 建立第一印象，传递项目定位
- **Image Requirements**: 无（纯文字封面即可）
- **Page Weight**: Core page

---

## Page 2: 目录
- **Page Type**: TOC
- **Page Title**: 目录
- **Selected Template**: toc/business/3507.tpl

- **Content Structure**: 4个章节导航：项目概览、核心流程、技术架构、成果展望
- **Content Density**: Light
- **Narrative Role**: 引导听众了解汇报结构
- **Image Requirements**: 无
- **Page Weight**: Secondary page

---

## Page 3: 项目定位与背景
- **Page Type**: Content
- **Page Title**: 我们解决什么问题
- **Selected Template**: content/business/1531.tpl

- **Content Structure**: 
  - 核心论点：职业教育分类考试需要大量高质量一课一练试卷，人工出题效率低、难规模化
  - 痛点1：传统人工出题每人每天最多出1-2套，无法覆盖多教材多考类需求
  - 痛点2：AI直接出题质量不可控——风格不统一、知识不准、格式混乱
  - 痛点3：不同省份、考类、教材的命题风格差异大，缺乏系统化管理
  - 项目回答：一套分层控制的AI试卷生产系统，把"出题"拆成可管理的流水线
- **Content Density**: Medium
- **Narrative Role**: 建立问题意识，引出解决方案
- **Image Requirements**: 无
- **Page Weight**: Core page
- **Content Page Selection Rationale**: 作为首张内容页，需要快速让听众理解"为什么做这个项目"，而非直接讲技术细节

---

## Page 4: 核心数据一览
- **Page Type**: Content
- **Page Title**: 项目规模
- **Selected Template**: content/business/1534.tpl

- **Content Structure**:
  - 数据标题：半年内从0到1，已覆盖多省多考类
  - 指标1：覆盖3个省份（重庆市、四川省、内蒙古自治区）
  - 指标2：6个考类（机械加工、汽车、电气技术、电子技术、土建、机电）
  - 指标3：56个Python脚本，10个核心生成器模块
  - 指标4：323个Word文档、224个原始文本、133个zip包已产出
  - 指标5：支持7种以上题型（单选、多选、判断、填空、简答、计算、综合）
- **Content Density**: Medium
- **Narrative Role**: 用数据建立项目可信度
- **Image Requirements**: 无（数据卡片形式）
- **Page Weight**: Core page

---

## Page 5: 分层控制理念
- **Page Type**: Content
- **Page Title**: 不只是让AI出题
- **Selected Template**: content/business/1532.tpl

- **Content Structure**:
  - 核心理念：本项目不是"把考点丢给AI"，而是7层控制体系
  - 第1层：教材目录决定一课一练主题
  - 第2层：考纲决定知识点边界和考试要求
  - 第3层：规划表决定每练题型、题量、难度、套数
  - 第4层：编写规范决定通用质量底线
  - 第5层：题型定义JSON提供当前考类的个性化画像
  - 第6层：真题风格库决定设问口吻、选项结构、解析风格
  - 第7层：质检与修复决定最终交付质量
- **Content Density**: Heavy
- **Narrative Role**: 传递项目的设计哲学，区别于简单的AI出题
- **Image Requirements**: 否
- **Page Weight**: Core page
- **Content Page Selection Rationale**: 这是项目的核心差异化点，需要清晰展示控制体系的层次关系

---

## Page 6: 过渡页 - 核心流程
- **Page Type**: Transition
- **Page Title**: 核心流程
- **Selected Template**: transition/business/507.tpl

- **Content Structure**: 章节标题，引导进入流程讲解
- **Content Density**: Light
- **Narrative Role**: 章节分隔
- **Image Requirements**: 无
- **Page Weight**: Transition page

---

## Page 7: 完整生产流程
- **Page Type**: Content
- **Page Title**: 从考纲到试卷的完整链路
- **Selected Template**: content/business/1535.tpl

- **Content Structure**:
  - 流程概览：准备资料 → 真题风格库 → 考点规划表 → AI生成试卷 → 质检修复 → Word交付 → 人工抽查
  - 关键节点1：规划表是整个流程的"总控制器"，决定每练出什么、出多少、什么难度
  - 关键节点2：生成时读取规划表+教材+真题风格+题型定义+编写规范，构建精确prompt
  - 关键节点3：质检自动检测答案自暴露、题干重复、选项失衡、解析过短等问题
  - 关键节点4：最终输出解析版Word（教师用）+原卷版Word（学生用）+原始文本+zip包
- **Content Density**: Medium
- **Narrative Role**: 让听众理解完整流程，建立对系统闭环的信心
- **Image Requirements**: 无（文字+编号流程即可）
- **Page Weight**: Core page

---

## Page 8: 规划表——试卷的DNA
- **Page Type**: Content
- **Page Title**: 一张表管住所有试卷
- **Selected Template**: content/business/1538.tpl

- **Content Structure**:
  - 核心论点：规划表是整个系统的"中央控制器"
  - 规划表8列结构：序号、考纲知识点、试卷主题、级别、题型、难度、套数、考纲标号
  - 教材目录优先原则：有教材目录时先读目录定主题，再匹配考纲知识点；没有教材才回到仅考纲模式
  - 多教材拆分规则：每本教材独立生成一个xlsx，序号从1开始，严禁混在一张表里
  - 三级标题体系：一级标题（单元）→二级标题（章）→试卷主题（节），自动生成标准化试卷标题
- **Content Density**: Heavy
- **Narrative Role**: 讲解项目的"大脑"，让听众理解为什么能规模化生产
- **Image Requirements**: 无
- **Page Weight**: Core page
- **Content Page Selection Rationale**: 规划表是项目最核心的创新点，需要详细说明其控制作用和设计规则

---

## Page 9: 真题风格蒸馏
- **Page Type**: Content
- **Page Title**: 让AI出的题像真题
- **Selected Template**: content/business/1537.tpl

- **Content Structure**:
  - 核心理念：真题只用于风格迁移，不照搬内容——模仿设问方式、选项结构、解析口吻
  - 风格库结构：风格总则 + 单选风格 + 多选风格 + 判断风格 + 填空风格 + 简答风格 + 计算风格 + 综合风格 + 代表样题
  - 技术支持：文字型PDF直接提取 + 扫描型PDF用Tesseract OCR兜底
  - 效果：生成的试卷在命题口吻上接近目标省份目标考类的真题，但不涉及知识侵权
- **Content Density**: Medium
- **Narrative Role**: 展示项目的命题质量保障机制
- **Image Requirements**: 无
- **Page Weight**: Core page

---

## Page 10: 过渡页 - 技术架构
- **Page Type**: Transition
- **Page Title**: 技术架构
- **Selected Template**: transition/business/507.tpl

- **Content Structure**: 章节标题
- **Content Density**: Light
- **Narrative Role**: 章节分隔
- **Image Requirements**: 无
- **Page Weight**: Transition page

---

## Page 11: 生成器模块架构
- **Page Type**: Content
- **Page Title**: 10个模块驱动一条生产线
- **Selected Template**: content/business/1539.tpl

- **Content Structure**:
  - 核心论点：生成器从单一脚本拆分为10个独立模块，各司其职
  - runner.py：主流程编排，解析参数、循环生成、质检保存
  - config_io.py：配置读取、API调用、token用量统计
  - planning.py：解析规划表，确定输出路径
  - prompts.py：构建生成试卷的精确提示词
  - references.py：加载教材、真题风格库参考资料
  - text_generation.py + text_processing.py：文本生成与清洗
  - quality.py：本地质检、答案分布调整、定向修复
  - docx_generation.py + postprocess.py：Word生成与后处理
- **Content Density**: Heavy
- **Narrative Role**: 展示技术架构的模块化和工程化水平
- **Image Requirements**: 无
- **Page Weight**: Core page
- **Content Page Selection Rationale**: 面向技术听众，展示系统的工程化设计和可维护性

---

## Page 12: OCR多方案支持
- **Page Type**: Content
- **Page Title**: 三套OCR方案应对不同场景
- **Selected Template**: content/business/1533.tpl

- **Content Structure**:
  - 核心挑战：教材和真题多为扫描版PDF，文本无法直接提取
  - 方案1：RapidOCR（`ocr_pdf.py`）——标准图片型PDF转文本/JSON/Markdown
  - 方案2：Tesseract OCR（`textbook_toc_scanner.py`）——教材目录结构化扫描，输出目录层级JSON
  - 方案3：真题风格OCR兜底（`extract_exam_style.py --ocr-pdf`）——对乱码PDF自动启用Tesseract
  - 缓存机制：OCR结果自动缓存到教材OCR目录，避免重复处理
  - 目录页检测算法：关键词得分+结构得分+反向惩罚，自动识别目录页码范围
- **Content Density**: Medium
- **Narrative Role**: 展示系统在资料处理上的技术深度
- **Image Requirements**: 无
- **Page Weight**: Secondary page

---

## Page 13: 质检与自动修复
- **Page Type**: Content
- **Page Title**: 六维质检+定向修复
- **Selected Template**: content/business/1536.tpl

- **Content Structure**:
  - 核心论点：生成不是终点，质检修复保证交付质量
  - 检测维度1：题量是否与规划表一致
  - 检测维度2：答案是否在题干中自暴露
  - 检测维度3：选项长度是否明显失衡
  - 检测维度4：答案分布是否过度集中
  - 检测维度5：解析是否过短或空泛
  - 检测维度6：Word格式、公式、答案/解析样式是否正常
  - 修复能力：答案分布自动调整、公式自动转换、样式批量修复
- **Content Density**: Medium
- **Narrative Role**: 回应用户对AI生成质量的顾虑
- **Image Requirements**: 无
- **Page Weight**: Core page

---

## Page 14: 过渡页 - 成果展望
- **Page Type**: Transition
- **Page Title**: 成果与展望
- **Selected Template**: transition/business/507.tpl

- **Content Structure**: 章节标题
- **Content Density**: Light
- **Narrative Role**: 章节分隔
- **Image Requirements**: 无
- **Page Weight**: Transition page

---

## Page 15: 覆盖范围与交付成果
- **Page Type**: Content
- **Page Title**: 已覆盖3省6考类
- **Selected Template**: content/business/1540.tpl

- **Content Structure**:
  - 已覆盖省份：重庆市（机械加工、汽车、电气技术、电子技术、土建）+ 四川省（汽车）+ 内蒙古自治区（机电）
  - 已产出教材：机械基础、机械制图、机械加工技术、电工技术基础与技能、电子技术基础与技能、电机与电气控制技术、计算机组装与维修、计算机网络基础、植物保护技术等
  - 交付格式：解析版docx（教师用）+ 原卷版docx（学生用）+ 原始文本 + zip打包
  - 扩展流程标准化：新增省份只需5步——放入考纲PDF、教材PDF、真题、生成风格库、生成规划表
- **Content Density**: Medium
- **Narrative Role**: 展示项目实际成果，证明系统可用性
- **Image Requirements**: 无
- **Page Weight**: Core page

---

## Page 16: 结束页
- **Page Type**: Ending
- **Page Title**: 谢谢
- **Selected Template**: ending/business/1007.tpl

- **Content Structure**: 感谢语 + 联系方式预留
- **Content Density**: Light
- **Narrative Role**: 结束汇报
- **Image Requirements**: 无
- **Page Weight**: Secondary page
