import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
import easyocr
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import json
from tools.font_render_utils import render_char_to_image, batch_render_all_chars

# 默认配置
DEFAULT_OUTPUT_DIR = os.path.join('tools', 'ocr_chars')  # 图片输出目录
DEFAULT_THREADS = 8  # 并发线程数
DEFAULT_IMG_SIZE = 160
DEFAULT_FONT_SIZE = 140

def render_char_to_image(font_path, char, out_path, img_size=DEFAULT_IMG_SIZE, font_size=DEFAULT_FONT_SIZE):
    """
    居中渲染+二值化+放大图片+加粗字符
    """
    font = ImageFont.truetype(font_path, font_size)
    img = Image.new('L', (img_size, img_size), color=255)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), char, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (img.width - w) // 2 - bbox[0]
    y = (img.height - h) // 2 - bbox[1]
    # 加粗：多次偏移绘制
    offsets = [(0,0), (1,0), (0,1), (-1,0), (0,-1)]
    for dx, dy in offsets:
        draw.text((x+dx, y+dy), char, font=font, fill=0)
    # 也可尝试Pillow 8.2+的stroke_width参数（如有支持）
    # draw.text((x, y), char, font=font, fill=0, stroke_width=2, stroke_fill=0)
    # 二值化处理，但保存为'L'模式而非'1'模式，避免OpenCV读取问题
    img = img.point(lambda p: 0 if p < 128 else 255, 'L')
    img.save(out_path)

def batch_render_all_chars(font_path, output_dir):
    """
    批量渲染字体中所有字符
    """
    font = TTFont(font_path)
    cmap = font.getBestCmap()
    char_files = []
    for char_code in cmap:
        char = chr(char_code)
        out_path = os.path.join(output_dir, f"U{char_code:04X}.png")
        render_char_to_image(font_path, char, out_path)
        char_files.append((char, out_path))
    return char_files

def ocr_image(image_path, reader):
    """
    OCR识别单个图片
    """
    try:
        result = reader.readtext(image_path, detail=0)
        text = ''.join(result) if result else ''
        return text.strip()
    except Exception as e:
        print(f"OCR错误 {image_path}: {e}")
        return ""

def build_mapping_from_images(char_files, threads=DEFAULT_THREADS):
    """
    从图片构建映射表
    """
    # 用EasyOCR识别，支持中英文+数字+单字图片
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    
    mapping = {}
    def ocr_task(item):
        char, img_path = item
        real_char = ocr_image(img_path, reader)
        return char, real_char
    
    # 单线程模式用于调试
    if threads <= 1:
        for char, img_path in char_files:
            real_char = ocr_image(img_path, reader)
            mapping[char] = real_char
            print(f"{repr(char)} -> {repr(real_char)}")
    else:
        # 多线程模式
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_char = {executor.submit(ocr_task, item): item[0] for item in char_files}
            for future in as_completed(future_to_char):
                try:
                    char, real_char = future.result()
                    mapping[char] = real_char
                    print(f"{repr(char)} -> {repr(real_char)}")
                except Exception as e:
                    print(f"处理错误: {e}")
    
    return mapping

def save_mapping(mapping, out_path):
    """
    保存映射表到JSON文件
    """
    # 按照 key 的 Unicode 码点值升序排序
    sorted_mapping = dict(sorted(mapping.items(), key=lambda x: ord(x[0])))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_mapping, f, ensure_ascii=False, indent=2)
    print(f"映射表已保存到: {out_path}，按Unicode码点升序排序")

def generate_ocr_mapping(font_path, output_path, output_dir=DEFAULT_OUTPUT_DIR, threads=DEFAULT_THREADS):
    """
    生成OCR映射表
    
    参数:
        font_path: 字体文件路径
        output_path: 映射表输出路径
        output_dir: 字符图片输出目录
        threads: 并发线程数
    
    返回:
        bool: 是否成功生成映射表
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        print("--- 批量渲染字体字符为图片 ---")
        char_files = batch_render_all_chars(font_path, output_dir)
        print(f"共渲染 {len(char_files)} 个字符图片")
        
        print("--- 多线程OCR识别 ---")
        mapping = build_mapping_from_images(char_files, threads=threads)
        save_mapping(mapping, output_path)
        return True
    except Exception as e:
        print(f"生成OCR映射表失败: {e}")
        return False

def main():
    """
    命令行入口
    """
    import argparse
    parser = argparse.ArgumentParser(description='字体OCR映射生成工具')
    parser.add_argument('--font', default=os.path.join('cache', 'fonts', 'e26e946d8b2ccb7.otf'), help='字体文件路径')
    parser.add_argument('--output', default=os.path.join('tools', 'ocr_mapping.json'), help='映射表输出路径')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR, help='字符图片输出目录')
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS, help='并发线程数')
    args = parser.parse_args()
    
    generate_ocr_mapping(args.font, args.output, args.output_dir, args.threads)

if __name__ == "__main__":
    main()