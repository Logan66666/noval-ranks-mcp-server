import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.font_ocr_mapping_paddle import batch_paddle_easyocr_images

if __name__ == "__main__":
    image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools', 'ocr_chars')
    print("开始批量识别 ocr_chars 目录下所有图片...")
    results = batch_paddle_easyocr_images(image_dir)
    print("\n识别结果汇总：")
    for fname, text in results.items():
        print(f"{fname}: {repr(text)}")
    # 保存为json，key按Unicode码点升序
    output_path = os.path.join(os.path.dirname(__file__), 'ocr_results.json')
    sorted_results = dict(sorted(results.items(), key=lambda x: int(x[0][1:5], 16) if x[0].startswith('U') else float('inf')))
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_results, f, ensure_ascii=False, indent=2)
    print(f"\n识别结果已保存到: {output_path}") 