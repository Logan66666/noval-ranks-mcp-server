import os
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

DEFAULT_IMG_SIZE = 100
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
    offsets = [(0,0), (1,0), (0,1), (-1,0), (0,-1)]
    for dx, dy in offsets:
        draw.text((x+dx, y+dy), char, font=font, fill=0)
    img = img.point(lambda p: 0 if p < 128 else 255, 'L')
    img.save(out_path)

def batch_render_all_chars(font_path, output_dir, img_size=DEFAULT_IMG_SIZE, font_size=DEFAULT_FONT_SIZE):
    """
    批量渲染字体中所有字符
    """
    font = TTFont(font_path)
    cmap = font.getBestCmap()
    char_files = []
    os.makedirs(output_dir, exist_ok=True)
    for char_code in cmap:
        char = chr(char_code)
        out_path = os.path.join(output_dir, f"U{char_code:04X}.png")
        render_char_to_image(font_path, char, out_path, img_size, font_size)
        char_files.append((char, out_path))
    return char_files 