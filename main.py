#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 主入口文件

功能描述：
  - 整合API客户端、动态抓取器和字体解码器
  - 实现从获取书籍列表到解密排名的完整流程
  - 支持OCR辅助映射，提高解码准确率

作者：[请替换为实际作者]
创建日期：[请替换为实际创建日期]
"""

import json
import os
import argparse
import hashlib
import webbrowser
import subprocess
import time
import threading
from mcp.api.client import get_book_list,search_category
from mcp.scraper.scraper import get_dynamic_page
from mcp.decoder.decoder import FontDecoder
from tools.font_ocr_mapping_paddle import generate_ocr_mapping, batch_paddle_easyocr_images, render_char_to_image

def recursive_decode(obj, decoder):
    """
    递归遍历obj中的所有字符串字段，使用decoder解密
    """
    if isinstance(obj, dict):
        return {k: recursive_decode(v, decoder) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_decode(item, decoder) for item in obj]
    elif isinstance(obj, str):
        return decoder.decrypt_text(obj)
    else:
        return obj

def ensure_char_images_exist(mapping_file_path, font_path):
    """
    确保所有映射表中的字符都有对应的图片文件
    """
    try:
        # 读取映射表
        print(f"正在检查映射表: {mapping_file_path}")
        if not os.path.exists(mapping_file_path):
            print(f"错误: 映射文件不存在: {mapping_file_path}")
            return False
            
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        # 确保ocr_chars目录存在
        ocr_chars_dir = os.path.abspath(os.path.join('tools', 'ocr_chars'))
        os.makedirs(ocr_chars_dir, exist_ok=True)
        print(f"图片输出目录: {ocr_chars_dir}")
        
        # 检查每个字符是否有对应的图片
        missing_chars = []
        total_chars = len(mapping.keys())
        print(f"映射表中共有 {total_chars} 个字符")
        
        for char in mapping.keys():
            char_code = ord(char)
            img_path = os.path.join(ocr_chars_dir, f"U{char_code:04X}.png")
            if not os.path.exists(img_path):
                missing_chars.append((char, img_path))
        
        # 如果有缺失的图片，重新生成
        if missing_chars:
            if not os.path.exists(font_path):
                print(f"错误: 字体文件不存在: {font_path}")
                return False
                
            print(f"发现 {len(missing_chars)} 个字符缺少图片，正在生成...")
            success_count = 0
            for i, (char, img_path) in enumerate(missing_chars):
                try:
                    render_char_to_image(font_path, char, img_path)
                    success_count += 1
                    if (i + 1) % 10 == 0 or i + 1 == len(missing_chars):
                        print(f"进度: {i + 1}/{len(missing_chars)} ({(i + 1) / len(missing_chars) * 100:.1f}%)")
                except Exception as e:
                    print(f"生成图片失败: {img_path}, 字符: '{char}', 错误: {e}")
            
            print(f"图片生成完成，成功: {success_count}/{len(missing_chars)}")
        else:
            print("所有字符图片已存在")
        
        return True
    except Exception as e:
        print(f"确保字符图片存在时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def open_ocr_review_html(mapping_file_path=None, font_path=None):
    """
    启动Flask服务器并打开OCR校验页面
    """
    print("\n--- 启动OCR校验页面 ---")
    
    # 确保所有字符图片存在
    if mapping_file_path and font_path:
        print(f"开始检查字符图片...")
        print(f"映射文件: {mapping_file_path}")
        print(f"字体文件: {font_path}")
        
        if not os.path.exists(mapping_file_path):
            print(f"错误: 映射文件不存在: {mapping_file_path}")
            return False
            
        if not os.path.exists(font_path):
            print(f"错误: 字体文件不存在: {font_path}")
            return False
            
        if not ensure_char_images_exist(mapping_file_path, font_path):
            print("字符图片检查失败，可能影响OCR校验页面展示")
            # 不中断流程，继续启动服务器
    else:
        print("未提供映射文件或字体文件路径，跳过字符图片检查")
    
    # 获取Flask服务器脚本路径
    server_path = os.path.abspath(os.path.join('tools', 'ocr_review', 'server.py'))
    if not os.path.exists(server_path):
        print(f"错误: Flask服务器脚本不存在: {server_path}")
        return False
    
    # 使用子进程启动Flask服务器
    try:
        print(f"启动Flask服务器: {server_path}")
        flask_process = subprocess.Popen(
            ['python', server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待服务器启动
        print("正在启动Flask服务器...")
        time.sleep(2)  # 给服务器一些启动时间
        
        # 打开浏览器访问Flask服务
        url = 'http://localhost:5001/'
        print(f"正在打开OCR校验页面: {url}")
        webbrowser.open(url)
        
        # 注册一个退出处理函数，确保主程序退出时关闭Flask服务器
        def cleanup():
            print("关闭Flask服务器...")
            flask_process.terminate()
            flask_process.wait()
        
        # 使用atexit模块注册清理函数
        import atexit
        atexit.register(cleanup)
        
        # 输出一些服务器状态信息
        print("\nFlask服务器已启动")
        print("- 图片目录: tools/ocr_chars")
        print("- 提示: 如果图片加载缓慢，可以尝试刷新页面或点击'重试加载失败的图片'按钮")
        print("- 提示: 完成校验后，点击'保存为JSON'按钮保存结果")
        print("- 按Ctrl+C退出程序...\n")
        
        # 阻止主线程退出，但允许Ctrl+C中断
        try:
            # 输出Flask服务器的输出
            while True:
                output = flask_process.stdout.readline().decode('utf-8', errors='ignore').strip()
                error = flask_process.stderr.readline().decode('utf-8', errors='ignore').strip()
                if output:
                    print(f"[Flask] {output}")
                if error:
                    print(f"[Flask Error] {error}")
                if not output and not error:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("接收到退出信号")
        
        return True
    except Exception as e:
        print(f"启动Flask服务器失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='番茄小说榜单爬取和解码任务')
    parser.add_argument('--force-ocr-mapping', action='store_true', help='强制重新生成OCR映射表，即使已存在')
    parser.add_argument('--ocr-mapping-dir', default='cache/mappings', help='OCR映射表存储目录')
    parser.add_argument('--api-data-file', default='debug/raw_api_data.json', help='API数据文件路径')
    parser.add_argument('--review-html', action='store_true', help='生成并打开OCR人工校验页面')
    args = parser.parse_args()
    
    print("开始执行番茄小说榜单爬取和解码任务...")
    
    # 1. 从API获取书籍列表
    print("\n--- 步骤 1: 从API获取书籍列表 ---")
    book_data, api_data_file = get_book_list()
    if not book_data:
        print("获取书籍列表失败或数据格式不正确")
        return
    
    # 如果指定了API数据文件，则使用指定的文件路径
    if args.api_data_file and args.api_data_file != 'debug/raw_api_data.json':
        api_data_file = args.api_data_file
        print(f"将使用指定的API数据文件: {api_data_file}")
    
    # 2. 抓取动态页面以获取字体文件信息
    print("\n--- 步骤 2: 抓取动态页面以获取字体 ---")
    target_url = 'https://fanqienovel.com/library/all/page_1?sort=hottes'
    html_content = get_dynamic_page(target_url, wait_selector='.book-list', wait_time=10)
    if not html_content:
        print("获取动态页面内容失败")
        return

    # 3. 处理字体映射
    print("\n--- 步骤 3: 处理字体映射 ---")
    temp_decoder = FontDecoder()
    font_url = temp_decoder.extract_font_url(html_content)
    if not font_url:
        print("无法从HTML提取字体URL")
        return
    
    print(f"提取到字体URL: {font_url}")
    font_data = temp_decoder.download_font(font_url)
    if not font_data:
        print("字体下载失败")
        return
    
    font_hash = hashlib.md5(font_data).hexdigest()[:16]
    font_file_path = os.path.join('cache', 'fonts', f"{font_hash}.otf")
    mapping_file_path = os.path.join(args.ocr_mapping_dir, f"{font_hash}_mapping.json")
    
    os.makedirs(os.path.dirname(font_file_path), exist_ok=True)
    os.makedirs(args.ocr_mapping_dir, exist_ok=True)
    
    if not os.path.exists(font_file_path):
        with open(font_file_path, 'wb') as f:
            f.write(font_data)
        print(f"字体已保存到: {font_file_path}")
    else:
        print(f"字体文件已存在: {font_file_path}")
    
    if not os.path.exists(mapping_file_path) or args.force_ocr_mapping:
        print("需要生成OCR映射表...")
        generate_ocr_mapping(font_file_path, mapping_file_path)
        print(f"OCR映射表已生成: {mapping_file_path}")
    else:
        print(f"OCR映射表已存在: {mapping_file_path}，跳过生成步骤")
    
    print("\n--- 步骤 4: 初始化字体解码器并更新映射 ---")
    decoder = FontDecoder(ocr_mapping_path=mapping_file_path)
    if not decoder.update_font_mapping(font_path=font_file_path):
        print("字体映射更新失败，解码结果可能不准确")

    # 5. 递归替换API数据文件中的所有文本
    print("\n--- 步骤 5: 全量递归解码API数据文件 ---")
    try:
        if not os.path.exists(api_data_file):
            print(f"API数据文件不存在: {api_data_file}")
            return
        with open(api_data_file, 'r', encoding='utf-8') as f:
            api_json = json.load(f)
        decoded_json = recursive_decode(api_json, decoder)
    except Exception as e:
        print(f"解密过程发生错误: {e}")
        return

    # 6. 保存解码后的数据
    print("\n--- 步骤 6: 保存解码后的数据 ---")
    output_filename = os.path.join('output', 'decoded_api_data.json')
    try:
        os.makedirs('output', exist_ok=True)
        # 如果是dict，按key的Unicode码点升序排序
        if isinstance(decoded_json, dict):
            sorted_json = dict(sorted(decoded_json.items(), key=lambda x: ord(x[0]) if isinstance(x[0], str) and len(x[0]) == 1 else float('inf')))
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(sorted_json, f, ensure_ascii=False, indent=2)
        else:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(decoded_json, f, ensure_ascii=False, indent=2)
        print(f"解码后的API数据已保存到 {output_filename}")
    except Exception as e:
        print(f"保存文件失败: {e}")

    if args.review_html:
        # 如果指定了--review-html参数，则启动Flask服务器并打开OCR校验页面
        open_ocr_review_html(mapping_file_path, font_file_path)
    else:
        print("\n任务完成！")

if __name__ == "__main__":
    main()