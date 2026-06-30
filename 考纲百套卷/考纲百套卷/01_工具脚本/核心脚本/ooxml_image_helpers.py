# -*- coding: utf-8 -*-
"""
ooxml_image_helpers.py — OOXML 图片插入工具

从 kaogangbaitao-v2 paper_builder.py 迁移。
在 python-docx 段落中通过原始 OOXML 插入图片，
解决 add_picture() 的 WMF 不支持、尺寸失控等问题。

命名空间约定（与 ooxml_helpers.py 保持一致）：
    W = wordprocessingml
    R = relationships
"""

from pathlib import Path
from lxml import etree
from PIL import Image as PILImage

# ===== OOXML 命名空间 =====
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
XML = '{http://www.w3.org/XML/1998/namespace}'

MIN_READABLE_W = 288000    # 0.8cm (EMU)
MIN_READABLE_H = 288000    # 0.8cm (EMU)

IMAGE_MIME = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'gif': 'image/gif', 'bmp': 'image/bmp', 'webp': 'image/webp',
    'wmf': 'image/x-wmf', 'emf': 'image/x-emf',
}


def _get_image_px(path) -> tuple[int, int]:
    """用 PIL 获取图片像素尺寸"""
    try:
        img = PILImage.open(str(path))
        w, h = img.size
        img.close()
        return w, h
    except Exception:
        return 200, 150  # 兜底


def _px_to_emu(px: int, dpi: int = 96) -> int:
    """像素转 EMU（默认 96 DPI）"""
    return int(px * 914400 / dpi)


def _option_image_size(width_px, height_px, max_w=None, max_h=None,
                       display_w=0, display_h=0):
    """计算图片合理尺寸（EMU），超出上限时等比缩小"""
    if max_w is None:
        max_w = _px_to_emu(150)  # ~4cm
    if max_h is None:
        max_h = _px_to_emu(150)

    if display_w > 0 and display_h > 0:
        effective_w = display_w
        effective_h = display_h
    else:
        effective_w = width_px
        effective_h = height_px

    if effective_w <= 0 or effective_h <= 0:
        return max_w, max_h

    natural_w = _px_to_emu(effective_w)
    natural_h = _px_to_emu(effective_h)
    aspect = effective_w / max(effective_h, 1)

    w, h = natural_w, natural_h
    if w > max_w:
        w = max_w
        h = int(w / aspect)
    if h > max_h:
        h = max_h
        w = int(h * aspect)

    return max(w, MIN_READABLE_W), max(h, MIN_READABLE_H)


def build_inline_image_element(rel_id: str, desc: str,
                                width_emu: int, height_emu: int) -> etree._Element:
    """构建 w:drawing 内嵌图片元素（OOXML 级别）"""
    drawing_xml = f'''<w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
        xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
        xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <wp:inline distT="0" distB="0" distL="0" distR="0">
        <wp:extent cx="{width_emu}" cy="{height_emu}"/>
        <wp:effectExtent l="0" t="0" r="0" b="0"/>
        <wp:docPr id="1" name="{desc}"/>
        <wp:cNvGraphicFramePr>
          <a:graphicFrameLocks noChangeAspect="1"/>
        </wp:cNvGraphicFramePr>
        <a:graphic>
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic>
              <pic:nvPicPr>
                <pic:cNvPr id="0" name="{desc}"/>
                <pic:cNvPicPr/>
              </pic:nvPicPr>
              <pic:blipFill>
                <a:blip r:embed="{rel_id}"/>
                <a:stretch><a:fillRect/></a:stretch>
              </pic:blipFill>
              <pic:spPr>
                <a:xfrm>
                  <a:off x="0" y="0"/>
                  <a:ext cx="{width_emu}" cy="{height_emu}"/>
                </a:xfrm>
                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
              </pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>'''
    return etree.fromstring(drawing_xml.encode('utf-8'))


def embed_ooxml_image(paragraph, image_path, width_px=200, height_px=60,
                       display_w=0, display_h=0, desc='image',
                       max_w_cm=4.0, max_h_cm=4.0):
    """在 python-docx 段落中嵌入 OOXML 图片（绕过 add_picture 的格式限制）

    使用 python-docx 的 part.relate_to() 建立图片关系 + 手动将图片文件
    注入 ZIP 包，然后用 OOXML 构建 <w:drawing> 插入段落。

    Returns:
        bool: 成功 True，失败 False
    """
    try:
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        from docx.opc.part import Part
        from docx.opc.packuri import PackURI
        import hashlib

        path = Path(image_path)
        if not path.exists():
            return False

        # 获取图片实际像素
        wp, hp = _get_image_px(path)
        # 计算 EMU 尺寸
        max_w_emu = int(max_w_cm * 360000)
        max_h_emu = int(max_h_cm * 360000)
        w_emu, h_emu = _option_image_size(wp, hp, max_w_emu, max_h_emu,
                                          display_w, display_h)

        # 将图片文件注入 docx 包
        package = paragraph.part.package
        ext = path.suffix.lower()
        content_type = IMAGE_MIME.get(ext, 'image/png')
        image_bytes = path.read_bytes()

        # 为图片生成唯一名称
        img_hash = hashlib.md5(image_bytes).hexdigest()[:8]
        img_name = f'image_{img_hash}{ext}'
        img_uri = f'/word/media/{img_name}'

        # 检查是否已存在同一图片
        existing_rels = {rel.target_ref for rel in paragraph.part.rels.values()
                        if rel.reltype == RT.IMAGE}
        if img_name in existing_rels:
            # 图片已存在，查找现有 rId
            for rel_id, rel in paragraph.part.rels.items():
                if rel.reltype == RT.IMAGE and rel.target_ref == f'media/{img_name}':
                    break
            else:
                rel_id = paragraph.part.relate_to(
                    f'media/{img_name}', RT.IMAGE)
        else:
            # 将图片写入包
            from docx.opc.part import Part
            img_part_name = PackURI(img_uri)
            # 检查图片是否已在包中
            if img_part_name not in {p.partname for p in package.iter_parts()}:
                image_part = Part(img_part_name, content_type,
                                  image_bytes, package)
                package.relate_to(image_part, RT.IMAGE)
            rel_id = paragraph.part.relate_to(image_part, RT.IMAGE)

        # 构建 OOXML drawing 元素
        drawing = build_inline_image_element(rel_id, desc, w_emu, h_emu)

        # 创建 w:r 包裹 drawing
        r = etree.Element(f'{W}r')
        r.append(drawing)

        # 插入到段落末尾
        paragraph._p.append(r)
        return True
    except Exception as exc:
        print(f"  → 警告：OOXML图片插入失败 {image_path}: {exc}")
        return False


def resolve_image_path(img_item):
    """解析图片条目的本地路径"""
    if isinstance(img_item, (str, Path)):
        return str(img_item).strip()
    if isinstance(img_item, dict):
        return (img_item.get('local_path')
                or img_item.get('path')
                or img_item.get('file')
                or img_item.get('url')
                or '')
    return ''


def ensure_png(img_path) -> str:
    """确保图片为 PNG 格式（转换 WMF 等不支持格式，并放大至可读分辨率）"""
    path = Path(img_path)
    if not path.exists():
        return str(path)
    suffix = path.suffix.lower()
    if suffix in ('.wmf', '.emf', '.svg', '.bmp'):
        try:
            png_path = path.with_suffix('.png')
            if not png_path.exists():
                img = PILImage.open(str(path))
                w, h = img.size
                # WMF/EMF 矢量图在 PIL 默认打开时分辨率极低（如 17×30px），
                # 需放大到至少 600px 长边，否则插入 DOCX 后会模糊或过小
                if max(w, h) < 600:
                    scale = 600 / max(w, h)
                    new_w = max(int(w * scale), 1)
                    new_h = max(int(h * scale), 1)
                    try:
                        img = img.resize((new_w, new_h), PILImage.LANCZOS)
                    except AttributeError:
                        img = img.resize((new_w, new_h), PILImage.BILINEAR)
                img.save(str(png_path), 'PNG')
                img.close()
            return str(png_path)
        except Exception:
            pass
    return str(path)
