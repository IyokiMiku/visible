"""
文件配对打包工具

功能：
  将同名的（解析版）和（原卷版）两个文件打包成一个 zip 文件。
  zip 文件名为两个文件的共同部分。

用法：
  python zip.py
  按提示选择目录，自动配对并打包。
"""

import os
import re
import zipfile


def find_pairs(directory):
    """在目录中查找（解析版）/（原卷版）配对文件"""
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    pairs = {}
    pattern = re.compile(r'^(.+?)(?:[（(](解析版|原卷版)[）)])')

    for f in files:
        match = pattern.match(f)
        if match:
            base_name = match.group(1).strip()
            variant = match.group(2)
            if base_name not in pairs:
                pairs[base_name] = {}
            pairs[base_name][variant] = f

    complete_pairs = {k: v for k, v in pairs.items() if "解析版" in v and "原卷版" in v}
    return complete_pairs


def create_zips(directory, pairs):
    """为每对文件创建 zip"""
    created = []
    for base_name, variants in pairs.items():
        zip_name = f"{base_name}.zip"
        zip_path = os.path.join(directory, zip_name)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for variant_type, filename in variants.items():
                file_path = os.path.join(directory, filename)
                zf.write(file_path, filename)

        created.append((zip_name, list(variants.values())))

    return created


def main():
    print("=" * 50)
    print("  文件配对打包工具（解析版 + 原卷版 → zip）")
    print("=" * 50)
    print()

    directory = input("请输入文件所在目录路径（直接回车则使用当前目录）：").strip().strip('"')
    if not directory:
        directory = os.environ.get("EXAM_TOOL_WORKDIR") or os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(directory):
        print(f"目录不存在: {directory}")
        return

    pairs = find_pairs(directory)

    if not pairs:
        print("\n未找到（解析版）/（原卷版）配对文件。")
        print("请确保文件命名格式如：")
        print("  XXX（解析版）.docx")
        print("  XXX（原卷版）.docx")
        return

    print(f"\n找到 {len(pairs)} 对文件：")
    for i, (base_name, variants) in enumerate(pairs.items(), 1):
        print(f"  {i}. {base_name}")
        for v_type, fname in variants.items():
            print(f"     - {fname}")

    confirm = input(f"\n确认打包？(y/n): ").strip().lower()
    if confirm != "y":
        print("已取消。")
        return

    created = create_zips(directory, pairs)

    print(f"\n打包完成！共生成 {len(created)} 个 zip 文件：")
    for zip_name, files in created:
        print(f"  ✔ {zip_name}")
        for f in files:
            print(f"      ← {f}")

    input("\n按 Enter 退出...")


if __name__ == "__main__":
    main()
