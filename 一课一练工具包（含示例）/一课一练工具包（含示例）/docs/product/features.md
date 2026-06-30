# PPT 大纲

## 概述
一课一练试卷生成工具包项目汇报——面向高职分类考试的AI驱动试卷批量生产系统。本项目已覆盖3省6考类，具备完整的规划表驱动、分层控制、自动质检的标准化试卷生产流程。本汇报按"项目概览→核心流程→技术架构→成果展望"四大章节展开，共16页。

## 大纲内容

### Page 1: 封面
- **Page Type**: Cover
- **Page Title**: 一课一练试卷生成工具包
- **Content Structure**: 主标题 + 副标题"AI驱动的高职分类考试试卷批量生产系统" + 汇报信息

### Page 2: 目录
- **Page Type**: TOC
- **Page Title**: 目录
- **Content Structure**: 4个章节导航：项目概览、核心流程、技术架构、成果展望

### Page 3: 项目定位与背景
- **Page Type**: Content
- **Page Title**: 我们解决什么问题
- **Content Structure**: 
  - 核心论点：职业教育分类考试需要大量高质量一课一练试卷，人工出题效率低、难规模化
  - 痛点1：传统人工出题每人每天最多出1-2套，无法覆盖多教材多考类需求
  - 痛点2：AI直接出题质量不可控——风格不统一、知识不准、格式混乱
  - 痛点3：不同省份、考类、教材的命题风格差异大，缺乏系统化管理
  - 项目回答：一套分层控制的AI试卷生产系统，把"出题"拆成可管理的流水线

### Page 4: 核心数据一览
- **Page Type**: Content
- **Page Title**: 项目规模
- **Content Structure**:
  - 数据标题：半年内从0到1，已覆盖多省多考类
  - 指标1：覆盖3个省份（重庆市、四川省、内蒙古自治区）
  - 指标2：6个考类（机械加工、汽车、电气技术、电子技术、土建、机电）
  - 指标3：56个Python脚本，10个核心生成器模块
  - 指标4：323个Word文档、224个原始文本、133个zip包已产出
  - 指标5：支持7种以上题型

### Page 5: 分层控制理念
- **Page Type**: Content
- **Page Title**: 不只是让AI出题
- **Content Structure**:
  - 核心理念：不是"把考点丢给AI"，而是7层控制体系
  - 第1层：教材目录决定主题
  - 第2层：考纲决定知识点边界
  - 第3层：规划表决定题型、题量、难度
  - 第4层：编写规范决定质量底线
  - 第5层：题型定义JSON提供个性化画像
  - 第6层：真题风格库决定设问方式
  - 第7层：质检修复决定交付质量

### Page 6: 过渡页 - 核心流程
- **Page Type**: Transition
- **Page Title**: 核心流程
- **Content Structure**: 章节标题，引导进入流程讲解

### Page 7: 完整生产流程
- **Page Type**: Content
- **Page Title**: 从考纲到试卷的完整链路
- **Content Structure**:
  - 流程概览：准备资料 → 真题风格库 → 考点规划表 → AI生成试卷 → 质检修复 → Word交付 → 人工抽查
  - 关键节点1：规划表是整个流程的"总控制器"
  - 关键节点2：生成时读取规划表+教材+真题风格+题型定义+编写规范
  - 关键节点3：质检自动检测6类问题
  - 关键节点4：最终输出解析版Word+原卷版Word+原始文本+zip包

### Page 8: 规划表——试卷的DNA
- **Page Type**: Content
- **Page Title**: 一张表管住所有试卷
- **Content Structure**:
  - 核心论点：规划表是整个系统的"中央控制器"
  - 8列结构：序号、考纲知识点、试卷主题、级别、题型、难度、套数、考纲标号
  - 教材目录优先原则：有教材先读目录，再匹配考纲
  - 多教材拆分规则：每本教材独立xlsx，序号从1开始

### Page 9: 真题风格蒸馏
- **Page Type**: Content
- **Page Title**: 让AI出的题像真题
- **Content Structure**:
  - 核心理念：真题只用于风格迁移，不照搬内容
  - 风格库结构：风格总则 + 7种题型风格 + 代表样题
  - 技术支持：文字型PDF直接提取 + 扫描型PDF Tesseract OCR
  - 效果：命题口吻接近目标省份真题，不涉及知识侵权

### Page 10: 过渡页 - 技术架构
- **Page Type**: Transition
- **Page Title**: 技术架构
- **Content Structure**: 章节标题

### Page 11: 生成器模块架构
- **Page Type**: Content
- **Page Title**: 10个模块驱动一条生产线
- **Content Structure**:
  - 核心论点：生成器拆分为10个独立模块
  - runner.py：主流程编排
  - config_io.py：配置与API调用
  - planning.py：规划表解析
  - prompts.py：提示词构建
  - references.py：参考资料加载
  - text_generation/processing：文本生成与清洗
  - quality.py：质检与修复
  - docx_generation/postprocess：Word生成与后处理

### Page 12: OCR多方案支持
- **Page Type**: Content
- **Page Title**: 三套OCR方案应对不同场景
- **Content Structure**:
  - 核心挑战：教材和真题多为扫描版PDF
  - 方案1：RapidOCR—标准图片型PDF
  - 方案2：Tesseract—教材目录结构化扫描
  - 方案3：真题风格OCR兜底
  - 缓存机制：避免重复OCR
  - 目录页检测算法：自动识别目录页码范围

### Page 13: 质检与自动修复
- **Page Type**: Content
- **Page Title**: 六维质检+定向修复
- **Content Structure**:
  - 核心论点：生成不是终点，质检修复保证交付质量
  - 检测维度：题量、答案自暴露、选项失衡、答案分布、解析质量、Word格式
  - 修复能力：答案分布调整、公式转换、样式批量修复

### Page 14: 过渡页 - 成果展望
- **Page Type**: Transition
- **Page Title**: 成果与展望
- **Content Structure**: 章节标题

### Page 15: 覆盖范围与交付成果
- **Page Type**: Content
- **Page Title**: 已覆盖3省6考类
- **Content Structure**:
  - 已覆盖省份：重庆、四川、内蒙古
  - 已产出教材：机械基础、机械制图、电工电子等9本以上
  - 交付格式：解析版docx + 原卷版docx + 原始文本 + zip
  - 扩展标准化：新增省份仅需5步

### Page 16: 结束页
- **Page Type**: Ending
- **Page Title**: 谢谢
- **Content Structure**: 感谢语

## 设计风格
Business 商务风格，蓝色主调，简洁专业。主色 #1a73e8，强调色 #0d9488 和 #f59e0b，中性色 #64748b。标题字体 Montserrat + Noto Sans SC，正文字体 Inter + Noto Sans SC。
