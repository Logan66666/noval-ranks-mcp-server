import os
from paddleocr import PaddleOCR
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
import numpy as np
import re
from tools.font_render_utils import render_char_to_image, batch_render_all_chars
import easyocr
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import json

# 保留汉字、英文、数字
VALID_CHAR_RE = re.compile(r'[A-Za-z0-9\u4e00-\u9fff]')
SYMBOL_RE = re.compile(r'^[^A-Za-z0-9\u4e00-\u9fff]+$')  # 纯符号

def filter_valid_chars(text):
    return ''.join(VALID_CHAR_RE.findall(text))

# 默认配置
DEFAULT_OUTPUT_DIR = os.path.join('tools', 'ocr_chars')  # 图片输出目录
DEFAULT_THREADS = 2  # 并发线程数
DEFAULT_IMG_SIZE = 160
DEFAULT_FONT_SIZE = 140

# 线程本地存储
thread_local = threading.local()

def get_paddle_ocr():
    if not hasattr(thread_local, "ocr_model"):
        thread_local.ocr_model = PaddleOCR(use_angle_cls=False, lang='ch')
    return thread_local.ocr_model

def get_easyocr_reader():
    if not hasattr(thread_local, "easyocr_reader"):
        thread_local.easyocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    return thread_local.easyocr_reader

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

def paddle_ocr_image(image_path, ocr_model=None):
    if ocr_model is None:
        ocr_model = get_paddle_ocr()
    try:
        img = Image.open(image_path)
        img_arr = np.array(img)
        mean_pixel = img_arr.mean()
    except Exception as e:
        print(f"[ERROR] 无法读取图片: {image_path}, 错误: {e}")
        return '', 0.0
    result = ocr_model.predict(image_path)
    if isinstance(result, list) and len(result) > 0:
        item = result[0]
        rec_texts = item.get('rec_texts')
        rec_scores = item.get('rec_scores')
        if rec_texts and rec_scores:
            text = rec_texts[0]
            score = rec_scores[0]
            filtered = filter_valid_chars(text)
            # 置信度<0.7或为符号或多字符，置空
            if score < 0.7 or not filtered or SYMBOL_RE.match(text) or len(filtered) != 1:
                return '', score
            return filtered, score
    return '', 0.0

def easyocr_image(image_path, reader=None):
    if reader is None:
        reader = get_easyocr_reader()
    try:
        result = reader.readtext(image_path, detail=1)
        if result:
            # 取置信度最高的结果
            best = max(result, key=lambda x: x[2])
            text = best[1]
            score = best[2]
            filtered = filter_valid_chars(text)
            if score < 0.5 or not filtered or SYMBOL_RE.match(text):
                return '', score
            return filtered, score
    except Exception as e:
        print(f"[ERROR] EasyOCR识别失败: {image_path}, 错误: {e}")
    return '', 0.0

def batch_paddle_easyocr_images(image_dir, max_workers=DEFAULT_THREADS):
    files = [fname for fname in sorted(os.listdir(image_dir)) if fname.lower().endswith('.png')]
    results = {}
    paddle_scores = {}
    # 1. 先用paddle识别
    def paddle_task(img_path, fname):
        ocr_model = get_paddle_ocr()
        text, score = paddle_ocr_image(img_path, ocr_model)
        return fname, text, score
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_fname = {
            executor.submit(paddle_task, os.path.join(image_dir, fname), fname): fname
            for fname in files
        }
        for future in as_completed(future_to_fname):
            fname, text, score = future.result()
            results[fname] = text
            paddle_scores[fname] = score
            print(f"[Paddle] {fname}: {repr(text)}, score={score}")
    # 2. 对所有空值用easyocr识别

    def easyocr_task(img_path, fname):
        easyocr_reader = get_easyocr_reader()
        text, score = easyocr_image(img_path, easyocr_reader)
        return fname, text, score
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_fname = {
            executor.submit(easyocr_task, os.path.join(image_dir, fname), fname): fname
            for fname in files if not results[fname]
        }
        for future in as_completed(future_to_fname):
            fname, text, score = future.result()
            results[fname] = text
            print(f"[EasyOCR] {fname}: {repr(text)}, score={score}")
    return results

def generate_ocr_mapping(font_path, output_path, output_dir=DEFAULT_OUTPUT_DIR, threads=DEFAULT_THREADS):
    """
    生成OCR映射表，先渲染图片，再用paddle+easyocr批量识别，输出json，按字体index升序排序
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        print("--- 批量渲染字体字符为图片 ---")
        font = TTFont(font_path)
        cmap = font.getBestCmap()
        index_char_list = []
        for char_code, glyph_name in cmap.items():
            index = font.getGlyphID(glyph_name)
            char = chr(char_code)
            out_path = os.path.join(output_dir, f"U{char_code:04X}.png")
            render_char_to_image(font_path, char, out_path)
            index_char_list.append((index, char, out_path))
        print(f"共渲染 {len(index_char_list)} 个字符图片")
        print("--- 多线程OCR识别 ---")
        results = batch_paddle_easyocr_images(output_dir, max_workers=threads)
        mapping = {}
        for index, char, img_path in index_char_list:
            fname = os.path.basename(img_path)
            mapping[char] = (index, results.get(fname, ""))
        # 按index升序排序
        sorted_mapping = {char: val for char, val in sorted(mapping.items(), key=lambda x: x[1][0])}
        # 只保留char: 识别结果
        sorted_mapping = {char: val[1] for char, val in sorted_mapping.items()}
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_mapping, f, ensure_ascii=False, indent=2)
        print(f"映射表已保存到: {output_path}，按index升序排序")
        return True
    except Exception as e:
        print(f"生成OCR映射表失败: {e}")
        return False

if __name__ == "__main__":
    image_dir = os.path.join(os.path.dirname(__file__), 'ocr_chars')
    batch_paddle_easyocr_images(image_dir) 