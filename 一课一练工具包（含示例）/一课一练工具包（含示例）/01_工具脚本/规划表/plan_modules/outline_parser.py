"""Exam-outline PDF extraction and parsing."""

import re
import sys


def extract_pdf_text(pdf_path):
    """提取 PDF 全文文本（优先用 pdfplumber，退化用 PyPDF2）"""
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except ImportError:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except ImportError:
            print("错误：需要安装 pdfplumber 或 PyPDF2")
            print("  pip install pdfplumber")
            sys.exit(1)
    return text


def parse_exam_outline(text):
    """解析考纲文本为结构化数据：课程 → 节 → 考点列表

    返回:
        courses: [{name, sections: [{name, points: [{text, level}]}]}]
        textbooks: [{name, publisher, edition}]
    """
    lines = text.split("\n")
    courses = []
    textbooks = []
    current_course = None
    current_section = None

    # 查找"考试内容及要求"之后的内容
    start_idx = 0
    for i, line in enumerate(lines):
        if "考试内容及要求" in line:
            start_idx = i + 1
            break

    # 查找参考教材
    for i, line in enumerate(lines):
        if "参考教材" in line:
            for j in range(i + 1, min(i + 20, len(lines))):
                tb_line = lines[j].strip()
                # 匹配格式: 1．《机械基础》xxx主编，高等教育出版社，2024年8月第3版。
                m = re.match(
                    r'\d+[．.]\s*《(.+?)》.+?(高等教育出版社|机械工业出版社|人民邮电出版社|中国劳动社会保障出版社|重庆大学出版社|[\u4e00-\u9fa5]+出版社)[，,]\s*(\d{4})\s*年\s*\d+\s*月第\s*(\d+)\s*版',
                    tb_line
                )
                if m:
                    pub_name = m.group(2)
                    pub_short = {"高等教育出版社": "高教", "机械工业出版社": "机工",
                                 "人民邮电出版社": "人邮", "重庆大学出版社": "重大"}.get(pub_name, pub_name[:2])
                    textbooks.append({
                        "name": m.group(1),
                        "publisher": pub_short,
                        "edition": int(m.group(4)),
                    })
            # 优先使用"特别提醒"后的教材列表（通常是更新版本）
            for j in range(i + 1, min(i + 30, len(lines))):
                if "特别提醒" in lines[j] or "2026" in lines[j]:
                    newer_textbooks = []
                    for k in range(j + 1, min(j + 10, len(lines))):
                        tb_line2 = lines[k].strip()
                        m2 = re.match(
                            r'\d+[．.]\s*《(.+?)》.+?(高等教育出版社|机械工业出版社|人民邮电出版社|中国劳动社会保障出版社|重庆大学出版社|[\u4e00-\u9fa5]+出版社)[，,]\s*(\d{4})\s*年\s*\d+\s*月第\s*(\d+)\s*版',
                            tb_line2
                        )
                        if m2:
                            pub_name2 = m2.group(2)
                            pub_short2 = {"高等教育出版社": "高教", "机械工业出版社": "机工",
                                          "人民邮电出版社": "人邮", "重庆大学出版社": "重大"}.get(pub_name2, pub_name2[:2])
                            newer_textbooks.append({
                                "name": m2.group(1),
                                "publisher": pub_short2,
                                "edition": int(m2.group(4)),
                            })
                    if newer_textbooks:
                        textbooks = newer_textbooks
                    break
            break

    # 解析课程/节/考点
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()

        # 跳过页码标记
        if re.match(r'^-+\s*\d+\s*(of|/)\s*\d+\s*-+$', line) or re.match(r'^\d+$', line):
            i += 1
            continue

        # 课程行: "课程一：机械基础" 或 "课程三：机械加工技术"
        m = re.match(r'课程[一二三四五六七八九十\d]+[：:]\s*(.+)', line)
        if m:
            current_course = {"name": m.group(1).strip(), "sections": []}
            courses.append(current_course)
            current_section = None
            i += 1
            continue

        # 节标题: "1．制图基本知识" 或 "绪论" 或 "1. 力系与平衡"
        m = re.match(r'(\d+)[．.、]\s*(.+)', line)
        if m and current_course is not None:
            sec_name = m.group(2).strip()
            # 排除考点行（以"了解/理解/掌握/熟悉/能/会"开头的不是节标题）
            if not re.match(r'(了解|理解|掌握|熟悉|能|会|认识)', sec_name):
                current_section = {"name": f"{m.group(1)}．{sec_name}", "points": []}
                current_course["sections"].append(current_section)
                i += 1
                continue

        # 独立的绪论等
        if line == "绪论" and current_course is not None:
            current_section = {"name": "绪论", "points": []}
            current_course["sections"].append(current_section)
            i += 1
            continue

        # 考点行: "（1）掌握xxx" 或 "(1) 了解xxx"
        m = re.match(r'[（(]\s*(\d+)\s*[）)]\s*(.+)', line)
        if m and current_section is not None:
            point_text = m.group(2).strip()
            # 判断认知层次
            if re.match(r'(掌握|熟练掌握)', point_text):
                level = "掌握"
            elif re.match(r'(熟悉|理解)', point_text):
                level = "理解"
            elif re.match(r'(能|会)', point_text):
                level = "应用"
            else:
                level = "了解"
            current_section["points"].append({"text": point_text, "level": level})
            i += 1
            continue

        # 到"参考教材"或"四、"时停止解析考点
        if "参考教材" in line or re.match(r'四[、.]', line):
            break

        i += 1

    return courses, textbooks
