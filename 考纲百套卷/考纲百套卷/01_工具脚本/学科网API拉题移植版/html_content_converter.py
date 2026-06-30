"""
学科网题库 HTML → 结构化纯文本 统一转换器

设计目标:
  所有 HTML→text 转换集中在此模块，api_to_paper.py 和 paper_builder.py 不再各自
  做 HTML 处理。转换后的输出是干净的「文本 + $...$ LaTeX」，paper_builder 的
  _normalize_unicode_math 在此基础上做 Unicode 数学符号→LaTeX 标准化。

处理顺序（关键！必须按此顺序）:
  1. Fill blanks → ____ 标记
  2. MathML   → $...$ LaTeX
  3. Sub/Sup  → 占位符标记（存活标签剥离）
  4. Images   → 提取元数据
  5. Options  → 从 stem HTML 提取选项
  6. 标签剥离 → 移除所有 HTML 标签 + 实体解码
  7. Sub/Sup  → 占位符转回文本（单字母→$X_{t}$，多字符→$X_{text}$）
  8. 图片选项检测 → 标记纯图片题
"""

import re

# ══════════════════════════════════════════════════════════════════
# 内部标记（用 null byte 包裹，确保活过 re.sub(r'<[^>]+>', '')）
# ══════════════════════════════════════════════════════════════════
_SUB_O = '\x00SO\x00'   # subscript open
_SUB_C = '\x00SC\x00'   # subscript close
_SUP_O = '\x00PO\x00'   # superscript open
_SUP_C = '\x00PC\x00'   # superscript close


# ══════════════════════════════════════════════════════════════════
# 内部工具
# ══════════════════════════════════════════════════════════════════

def _strip_html_tags(text):
    """剥离纯样式标签 + 实体解码（sub/sup 标记已提前替换为占位符，不受影响）。"""
    if not text:
        return ''
    t = re.sub(r'<img\s+[^>]*>', '', text)
    t = re.sub(r'<[^>]+>', '', t)
    t = t.replace('&nbsp;', ' ')
    t = t.replace('\u3000', ' ')
    t = t.replace('&lt;', '<')
    t = t.replace('&gt;', '>')
    t = t.replace('&amp;', '&')
    t = t.replace('&quot;', '"')
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _parse_img_tag(img_html):
    """从 <img ... /> 标签提取 {url, width?, height?}。"""
    url_m = re.search(r'src\s*=\s*"([^"]+)"', img_html, re.IGNORECASE)
    if not url_m:
        return None
    url = url_m.group(1)
    w = re.search(r'width\s*=\s*"(\d+)"', img_html, re.IGNORECASE)
    h = re.search(r'height\s*=\s*"(\d+)"', img_html, re.IGNORECASE)
    if w and h:
        return {"url": url, "width": int(w.group(1)), "height": int(h.group(1))}
    return {"url": url}


# ══════════════════════════════════════════════════════════════════
# 步骤 1: 填空下划线
# ══════════════════════════════════════════════════════════════════

def _convert_fill_blanks(html_text):
    """将各种下划线格式转为 ____ 字符（从 api_to_paper.py 搬来，逻辑不变）。"""
    if not html_text:
        return html_text

    # Pattern 1: <span class="qml-bk" type="underline" size="N">
    def replacer(m):
        size = int(m.group(1)) if m.group(1) else 6
        return '_' * size
    html_text = re.sub(
        r'<span\s+class="qml-bk"[^>]*type="underline"[^>]*size="(\d+)"[^>]*>.*?</span>',
        replacer,
        html_text,
        flags=re.IGNORECASE | re.DOTALL
    )
    # Pattern 2: <span class="qml-bk" type="underline">content</span>
    html_text = re.sub(
        r'<span\s+class="qml-bk"[^>]*type="underline"[^>]*>(.*?)</span>',
        lambda m: '_' * max(len(m.group(1).strip()), 6),
        html_text,
        flags=re.IGNORECASE | re.DOTALL
    )
    # Pattern 3: <span style="...text-decoration:underline...">
    def _css_underline_replacer(m):
        inner = m.group(1)
        nbsp_count = len(re.findall(r'&nbsp;', inner))
        inner_text = re.sub(r'<[^>]+>', '', inner).strip()
        if nbsp_count > 0:
            return '_' * min(max(nbsp_count, 4), 6)
        if inner_text:
            return inner_text
        return '_' * 4
    html_text = re.sub(
        r'<span[^>]*text-decoration\s*:\s*underline[^>]*>(.*?)</span>',
        _css_underline_replacer,
        html_text,
        flags=re.IGNORECASE | re.DOTALL
    )
    # Pattern 4: <u>...</u>
    html_text = re.sub(
        r'<u[^>]*>(.*?)</u>',
        lambda m: '_' * max(len(re.sub(r'<[^>]+>', '', m.group(1)).strip()), 4),
        html_text,
        flags=re.IGNORECASE | re.DOTALL
    )
    return html_text


# ══════════════════════════════════════════════════════════════════
# 步骤 2: MathML → $...$ LaTeX
# ══════════════════════════════════════════════════════════════════

def _convert_mathml(html_text):
    """<math latex="...">...</math> → $...$（必须在标签剥离之前执行）。

    latex 属性可能已含 $ 定界符（如 "$\beta$"）或纯 LaTeX（如 "\beta"），
    统一转为 $...$ 格式，避免双 $ 导致 bug。
    """
    if not isinstance(html_text, str) or '<math' not in html_text:
        return html_text

    def _math_replacer(m):
        latex = m.group(1).strip()
        # 全量去除 $ 定界符（学科网部分 latex 属性内部含多余 $，如
        #   $\sqrt{\left(\mathrm{L}$_{1}$ \mathrm{L}{_{2}}\right)}$，
        #   仅去首尾不足以修复，需全部移除再重新包裹）
        latex = latex.replace('$', '')
        # 统一用单 $ 包裹
        return '$' + latex + '$'

    return re.sub(
        r'<math[^>]*latex="([^"]*)"[^>]*>.*?</math>',
        _math_replacer,
        html_text,
        flags=re.DOTALL
    )


# ══════════════════════════════════════════════════════════════════
# 步骤 3: Sub/Sup → 占位符
# ══════════════════════════════════════════════════════════════════

def _convert_sub_sup_to_markers(html_text):
    """将 <sub>/<sup> 替换为 null-byte 占位符，使其存活过标签剥离。
    
    同时合并因 font-span 拆分产生的碎片化 sub/sup：
      <sub>A</sub></span><span style="..."><sub>B</sub> → <sub>AB</sub>
    
    注意: <sub>/<sup> 可能带属性（如 word-font="..."），
    不能简单 str.replace，必须用正则。
    """
    if not html_text:
        return html_text

    # 合并被 font-span 拆开的相邻 <sub> / <sup> 标签（支持带属性的标签）
    # </sub></span><span style="font-family:..."><sub word-font="..."> → 合并
    html_text = re.sub(
        r'</sub>\s*(?:</span>\s*<span[^>]*>\s*)?<sub[^>]*>',
        '', html_text, flags=re.IGNORECASE | re.DOTALL
    )
    html_text = re.sub(
        r'</sup>\s*(?:</span>\s*<span[^>]*>\s*)?<sup[^>]*>',
        '', html_text, flags=re.IGNORECASE | re.DOTALL
    )

    # 替换为 null-byte 占位符（匹配带或不带属性的标签）
    html_text = re.sub(r'<sub[^>]*>', _SUB_O, html_text, flags=re.IGNORECASE)
    html_text = html_text.replace('</sub>', _SUB_C)
    html_text = re.sub(r'<sup[^>]*>', _SUP_O, html_text, flags=re.IGNORECASE)
    html_text = html_text.replace('</sup>', _SUP_C)

    return html_text


def _resolve_sub_sup_markers(text):
    """将占位符转回 LaTeX 下标/上标格式。

    单字母模式:  X_SUB_O_ t _SUB_C_ → $X_{t}$
    多字符模式:  X_SUB_O_ text _SUB_C_ → $X_{text}$
    上标同理。
    """
    if _SUB_O not in text and _SUP_O not in text:
        return text

    # 下标: X_SUB_O_text_SUB_C_ → $X_{text}$
    text = re.sub(
        r'([A-Za-z\u0394\u03b7\u03c9\u03a9\u03c6])' + re.escape(_SUB_O) + r'\s*(.+?)\s*' + re.escape(_SUB_C),
        lambda m: '$' + m.group(1) + '_{' + m.group(2).strip() + '}$',
        text
    )

    # 上标: X_SUP_O_text_SUP_C_ → $X^{text}$
    text = re.sub(
        r'([A-Za-z\u0394\u03b7\u03c9\u03a9\u03c6])' + re.escape(_SUP_O) + r'\s*(.+?)\s*' + re.escape(_SUP_C),
        lambda m: '$' + m.group(1) + '^{' + m.group(2).strip() + '}$',
        text
    )

    # 清理残留的占位符（如有不配对的情况）
    text = text.replace(_SUB_O, '')
    text = text.replace(_SUB_C, '')
    text = text.replace(_SUP_O, '')
    text = text.replace(_SUP_C, '')

    return text


# ══════════════════════════════════════════════════════════════════
# 步骤 4: 图片提取
# ══════════════════════════════════════════════════════════════════

def _extract_images(html_text):
    """从 HTML 中提取所有 <img> 标签为 [{url, width?, height?}, ...]。"""
    imgs = []
    for m in re.finditer(r'<img\s+[^>]*>', html_text, re.IGNORECASE):
        parsed = _parse_img_tag(m.group(0))
        if parsed:
            imgs.append(parsed)
    return imgs


# ══════════════════════════════════════════════════════════════════
# 步骤 5: 选项提取
# ══════════════════════════════════════════════════════════════════

# 匹配选项的 <td> 单元格: A. <span class="qml-op">...</span>
_TD_OPTION_PATTERN = re.compile(
    r'<td[^>]*?>([A-D])[.\uff0e](?:&nbsp;)*\s*<span\s+class="qml-op"[^>]*?>(.*?)</span>\s*</td>',
    re.DOTALL | re.IGNORECASE
)


def _parse_options_from_og(og_html):
    """从 <div class="qml-og"> 的选项容器 HTML 中提取选项列表。

    返回:
      options: [{"label":"A","text":"...","images":[...]}, ...]
      has_image_only: True 如果任何选项是纯图片（无文字）
    """
    options = []
    has_image_only = False

    for m in _TD_OPTION_PATTERN.finditer(og_html):
        label = m.group(1)
        opt_html = m.group(2)

        # 提取选项内的图片
        opt_imgs = _extract_images(opt_html)

        # 先做 sub/sup 占位符替换 + MathML 转换
        opt_html = _convert_mathml(opt_html)
        opt_html = _convert_sub_sup_to_markers(opt_html)

        # 剥离标签
        opt_text = _strip_html_tags(opt_html)

        # 解析 sub/sup 占位符
        opt_text = _resolve_sub_sup_markers(opt_text)

        # 检测纯图片选项
        has_img = bool(re.search(r'<img', m.group(2)))
        if has_img and len(opt_text.strip()) < 3:
            has_image_only = True

        options.append({
            "label": label,
            "text": opt_text,
            "images": opt_imgs
        })

    return options, has_image_only


# ══════════════════════════════════════════════════════════════════
# 公开 API
# ══════════════════════════════════════════════════════════════════

def convert_stem_html(stem_html):
    """解析学科网 stem HTML，返回 (stem_text, stem_images, options)。

    返回:
      stem_text:   str — 纯文本题干（含 $...$ LaTeX）
      stem_images: [{"url":"...","width":...,"height":...}, ...]
      options:     [{"label":"A","text":"...","images":[...]}, ...] 或 None（非选择题）

    特殊标记:
      options 中含 _image_only_options: True 表示此题为纯图片选项题（应过滤）。
    """
    if not stem_html:
        return '', [], None

    # 找到选项容器 <div class="qml-og">
    og_start = re.search(r'<div\s+class="\s*qml-og\s*"', stem_html, re.IGNORECASE)

    if not og_start:
        # 非选择题：处理 stem 全文
        stem_html_processed = _convert_mathml(stem_html)
        stem_html_processed = _convert_fill_blanks(stem_html_processed)
        stem_html_processed = _convert_sub_sup_to_markers(stem_html_processed)
        stem_imgs = _extract_images(stem_html)
        stem_text = _strip_html_tags(stem_html_processed)
        stem_text = _resolve_sub_sup_markers(stem_text)
        return stem_text, stem_imgs, None

    # 选择题：切分题干和选项
    og_html = stem_html[og_start.start():]
    stem_part = stem_html[:og_start.start()]

    # 处理题干部分
    stem_part = _convert_mathml(stem_part)
    stem_part = _convert_fill_blanks(stem_part)
    stem_part = _convert_sub_sup_to_markers(stem_part)
    stem_imgs = _extract_images(stem_part)
    stem_text = _strip_html_tags(stem_part)
    stem_text = _resolve_sub_sup_markers(stem_text)

    # 处理选项部分
    options, has_image_only = _parse_options_from_og(og_html)

    if not options:
        return stem_text, stem_imgs, None

    # 注意：has_image_only 通过独立的 is_image_only_question() 检测，
    # 不在 options 列表上附加属性（list 不支持自定义属性）。

    return stem_text, stem_imgs, options


def convert_answer_html(answer_html, type_id=None):
    """从学科网 answer HTML 提取纯文本答案。

    type_id 用于区分题型:
      - 选择 (100xxxx1): 提取 qml-isop 内的字母
      - 判断 (typeFeatureIds 含 judge): 提取正确/错误
      - 其他: clean_html 后返回

    返回: str — 纯文本答案
    """
    if not answer_html:
        return ''

    ans = answer_html
    if isinstance(ans, dict):
        ans = ans.get('stem', '') or ''
    if not isinstance(ans, str):
        return str(ans)

    # 选择题型答案：<span class="qml-isop">A</span>
    an_m = re.search(r'qml-isop"[^>]*>([^<]+)<', ans)
    if an_m:
        return an_m.group(1).strip()

    # 判断题型答案：<span class="qml-an" judge="0">错误</span>
    judge_m = re.search(r'judge\s*=\s*"(\d)"', ans)
    if judge_m:
        return '正确' if judge_m.group(1) == '1' else '错误'

    # 通用：转化后剥离标签
    ans = _convert_mathml(ans)
    ans = _convert_sub_sup_to_markers(ans)
    ans = _strip_html_tags(ans)
    ans = _resolve_sub_sup_markers(ans)
    return ans


def convert_explanation_html(explanation_html):
    """从学科网 explanation HTML 提取纯文本解析。

    处理 qml-seg 分段（【详解】/【分析】/【点睛】），
    不重复添加【】前缀（题库数据自带）。

    返回: str — 纯文本解析
    """
    if not explanation_html:
        return ''

    expl = explanation_html
    if isinstance(expl, dict):
        expl = expl.get('stem', '') or ''
    if not isinstance(expl, str) or not expl.strip():
        return ''

    # 无分段结构 → 直接清理
    if 'seg-name' not in expl:
        expl = _convert_mathml(expl)
        expl = _convert_sub_sup_to_markers(expl)
        expl = _strip_html_tags(expl)
        expl = _resolve_sub_sup_markers(expl)
        return expl

    # 有分段结构：逐段提取
    segments = re.findall(
        r'<div\s+class="qml-seg"[^>]*seg-name="([^"]*)"[^>]*>(.*?)</div>',
        expl, re.IGNORECASE | re.DOTALL
    )

    if not segments:
        expl = _convert_mathml(expl)
        expl = _convert_sub_sup_to_markers(expl)
        expl = _strip_html_tags(expl)
        expl = _resolve_sub_sup_markers(expl)
        return expl

    result_parts = []
    for seg_name, seg_content in segments:
        # 先做语义转换
        seg_content = _convert_mathml(seg_content)
        seg_content = _convert_sub_sup_to_markers(seg_content)
        inner = _strip_html_tags(seg_content)
        inner = _resolve_sub_sup_markers(inner)

        if not inner:
            continue

        # 移除题库自带的【xxx】前缀（seg-name 本身已标识分段类型）
        label = f'【{seg_name}】'
        without_label = inner.replace(label, '', 1).strip()
        if not without_label or without_label == '略':
            continue

        # 保留完整文本（含【详解】前缀——这是预期输出）
        result_parts.append(inner)

    return '\n'.join(result_parts)


def is_image_only_question(stem_html):
    """快速检测是否为纯图片选项题（选项全是图片，无文字）。

    这类题目不应拉入试卷——Word 渲染无法正确处理纯图片选项。
    """
    if not stem_html:
        return False

    og_start = re.search(r'<div\s+class="\s*qml-og\s*"', stem_html, re.IGNORECASE)
    if not og_start:
        return False

    og_html = stem_html[og_start.start():]
    options, has_image_only = _parse_options_from_og(og_html)
    return has_image_only
