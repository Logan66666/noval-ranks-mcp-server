#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体反爬解码器

功能描述：
  处理网页字体反爬场景，支持动态字体URL提取、字体文件下载解析
  提供字体映射缓存、加密文本解密等核心功能

模块说明：
  - FontDecoder类：核心解码器，包含字体提取、下载、解析、解密全流程
  - fetch_html: 辅助函数，用于获取网页HTML内容
  - main: 命令行入口，支持指定URL和CSS选择器提取解密文本

作者：[请替换为实际作者]
创建日期：[请替换为实际创建日期]
"""

import os
import re
import json
import logging
import requests
from fontTools.ttLib import TTFont
from io import BytesIO
from bs4 import BeautifulSoup
import argparse
import time

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'font_decoder.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FontDecoder')

class FontDecoder:
    def __init__(self, cache_dir='cache/fonts', ocr_mapping_path=None):
        self.cache_dir = cache_dir
        self.font_mapping = {}
        self.current_font_url = None
        self.ocr_mapping = None
        if ocr_mapping_path and os.path.exists(ocr_mapping_path):
            self.ocr_mapping = self.load_ocr_mapping(ocr_mapping_path)
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"初始化字体解码器，缓存目录: {os.path.abspath(self.cache_dir)}")
        self.load_cached_mapping()
    
    def load_cached_mapping(self):
        """加载缓存的字体映射"""
        cache_file = os.path.join(self.cache_dir, 'font_mapping_cache.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                self.font_mapping = cache.get('mapping', {})
                self.current_font_url = cache.get('last_used_font', '')
                logger.info(f"从缓存加载了字体映射，包含 {len(self.font_mapping)} 个字符映射")
            except Exception as e:
                logger.error(f"加载缓存失败: {e}")
        else:
            logger.info("未找到字体映射缓存文件")
    
    def save_cached_mapping(self):
        """保存字体映射到缓存"""
        cache_file = os.path.join(self.cache_dir, 'font_mapping_cache.json')
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'last_used_font': self.current_font_url,
                    'mapping': self.font_mapping,
                    'timestamp': time.time()
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"字体映射已保存到缓存: {cache_file}")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def extract_font_url(self, html_content):
        """
        从HTML内容中提取字体URL
        
        优先查找woff2格式，其次是woff，最后是otf
        """
        logger.info("正在从HTML内容中提取字体URL")
        
        # 只查找 otf 格式
        patterns = [
            r'url\("(https?://[^\"]+?\.otf)"\)',  # 只保留 OTF
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                font_url = matches[0]
                logger.info(f"提取到字体URL: {font_url}")
                return font_url
        # 备选策略：尝试从类名推断
        class_pattern = r'class="[^"]*?font-([a-zA-Z0-9]+)[^"]*?"'
        match = re.search(class_pattern, html_content)
        if match:
            font_family = match.group(1)
            logger.info(f"从类名提取字体家族: {font_family}")
            possible_urls = [
                f"https://lf6-awef.bytetos.com/obj/awesome-font/c/{font_family}.otf",
            ]
            logger.warning(f"使用构造的字体URL: {possible_urls[0]}")
            return possible_urls[0]
        logger.error("无法提取字体URL")
        return None
    
    def download_font(self, font_url):
        """下载字体文件并返回二进制内容"""
        if not font_url:
            logger.error("没有提供字体URL")
            return None
        
        try:
            logger.info(f"正在下载字体文件: {font_url}")
            start_time = time.time()
            response = requests.get(font_url)
            response.raise_for_status()
            
            download_time = time.time() - start_time
            size_kb = len(response.content) / 1024
            logger.info(f"字体下载成功: {size_kb:.1f} KB, 耗时 {download_time:.2f}秒")
            
            return response.content
        except Exception as e:
            logger.error(f"字体下载失败: {e}")
            return None
    
    def load_ocr_mapping(self, mapping_path):
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        logger.info(f"已加载OCR映射表: {mapping_path}，共{len(mapping)}项")
        return mapping
    
    def parse_font_mapping(self, font_data, ocr_mapping=None):
        """解析字体文件，提取字符映射关系，支持OCR辅助映射"""
        logger.info("开始解析字体映射")
        start_time = time.time()
        try:
            font = TTFont(BytesIO(font_data))
            mapping = {}
            cmap = font.getBestCmap()
            num_glyphs = len(cmap)
            logger.debug(f"字体包含 {num_glyphs} 个字形")
            for char_code, glyph_name in cmap.items():
                logger.debug(f"cmap: {hex(char_code)} -> {glyph_name}")
                char = chr(char_code)
                # 优先用OCR映射
                if ocr_mapping and char in ocr_mapping:
                    mapping[char] = ocr_mapping[char]
                elif self.ocr_mapping and char in self.ocr_mapping:
                    mapping[char] = self.ocr_mapping[char]
                elif glyph_name.startswith('uni'):
                    try:
                        real_char_code = int(glyph_name[3:], 16)
                        mapping[char] = chr(real_char_code)
                    except Exception:
                        pass
                elif glyph_name.startswith('u'):
                    try:
                        real_char_code = int(glyph_name[1:], 16)
                        mapping[char] = chr(real_char_code)
                    except Exception:
                        pass
            parse_time = time.time() - start_time
            logger.info(f"解析完成! 发现 {len(mapping)} 个可映射字符, 耗时 {parse_time:.2f}秒")
            if len(mapping) == 0:
                logger.warning("未能解析出任何映射，请检查字体文件是否为页面实际加密字体")
            return mapping
        except Exception as e:
            logger.error(f"字体解析失败: {e}")
            return {}
    
    def update_font_mapping(self, font_url=None, html_content=None, font_path=None):
        """
        更新字体映射表
        :param font_url: 可选 - 字体URL
        :param html_content: 可选 - HTML内容（用于提取字体URL）
        :param font_path: 可选 - 本地字体文件路径
        """
        # 如果提供了本地字体文件路径，直接从本地加载
        if font_path and os.path.exists(font_path):
            logger.info(f"从本地加载字体文件: {font_path}")
            try:
                with open(font_path, 'rb') as f:
                    font_data = f.read()
                # 使用文件路径作为URL标识
                self.current_font_url = f"local://{os.path.basename(font_path)}"
                # 解析字体映射
                new_mapping = self.parse_font_mapping(font_data, self.ocr_mapping)
                if not new_mapping:
                    logger.error("获取字体映射失败")
                    return False
                # 更新并保存
                self.font_mapping = new_mapping
                self.save_cached_mapping()
                logger.info("从本地字体文件更新映射成功!")
                return True
            except Exception as e:
                logger.error(f"加载本地字体文件失败: {e}")
                return False
        
        # 如果没有提供字体URL，尝试从HTML内容提取
        if not font_url and html_content:
            font_url = self.extract_font_url(html_content)
        
        # 检查字体URL是否有变化
        if font_url and font_url == self.current_font_url:
            logger.info("字体URL未变化，使用现有的映射")
            return True
        
        # 下载字体文件
        font_data = self.download_font(font_url)
        if not font_data:
            logger.error("无法获取字体数据")
            return False
        
        # 解析字体映射
        new_mapping = self.parse_font_mapping(font_data, self.ocr_mapping)
        if not new_mapping:
            logger.error("获取字体映射失败")
            return False
        
        # 更新并保存
        self.current_font_url = font_url
        self.font_mapping = new_mapping
        
        # 保存到缓存
        self.save_cached_mapping()
        
        logger.info("字体映射更新成功!")
        return True
    
    def decrypt_text(self, text):
        """使用字体映射将加密文本转换为正常文本，优先用OCR映射"""
        if not text or not self.font_mapping:
            logger.warning("无法解密文本：没有字体映射或为空输入")
            return text
        result = []
        changed_chars = 0
        for char in text:
            if char in self.font_mapping:
                result.append(self.font_mapping[char])
                changed_chars += 1
            else:
                result.append(char)
        if changed_chars:
            logger.debug(f"解密文本: 替换了 {changed_chars} 个字符")
        return ''.join(result)
    
    def get_element_text(self, html_content, selector, decrypt=True):
        """
        提取页面元素的文本
        :param html_content: HTML内容
        :param selector: CSS选择器
        :param decrypt: 是否解密文本
        :return: 文本内容或None
        """
        logger.info(f"使用选择器 '{selector}' 提取元素")
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            element = soup.select_one(selector)
            
            if not element:
                logger.warning(f"未找到选择器 '{selector}' 对应的元素")
                return None
            
            text = element.get_text(strip=False)  # 保留原始格式
            
            if decrypt:
                text = self.decrypt_text(text)
                logger.debug(f"解密后的文本: {text}")
            else:
                logger.debug(f"原始文本: {text}")
            
            return text
        except Exception as e:
            logger.error(f"元素提取失败: {e}")
            return None

def fetch_html(url, headers=None):
    """获取网页HTML内容"""
    logger.info(f"正在请求页面: {url}")
    
    # 设置默认请求头
    if not headers:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
            "Referer": "https://fanqienovel.com/"
        }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info(f"页面获取成功, 长度: {len(response.text)/1024:.1f} KB")
        return response.text
    except Exception as e:
        logger.error(f"页面获取失败: {e}")
        return None

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='字体反爬虫文本提取工具')
    parser.add_argument('url', help='目标网页URL')
    parser.add_argument('selector', help='CSS选择器，用于提取目标元素')
    parser.add_argument('--output', default='output.txt', help='输出文件名')
    parser.add_argument('--cache-dir', default='cache/fonts', help='字体缓存目录')
    parser.add_argument('--verbose', action='store_true', help='启用详细日志')
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.info("启用详细日志模式")
    
    logger.info(f"开始处理页面: {args.url}")
    logger.info(f"目标元素选择器: {args.selector}")
    
    # 获取页面HTML
    html_content = fetch_html(args.url)
    if not html_content:
        logger.error("无法继续处理: 没有HTML内容")
        return
    
    # 初始化字体解码器
    decoder = FontDecoder(cache_dir=args.cache_dir)
    
    # 更新字体映射
    if not decoder.update_font_mapping(html_content=html_content):
        logger.warning("字体更新失败，使用现有映射")
    
    # 提取并解密元素文本
    normal_text = decoder.get_element_text(html_content, args.selector)
    
    if normal_text:
        logger.info(f"提取到的正常文本: {normal_text}")
        
        # 保存到文件
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(normal_text)
            logger.info(f"结果已保存到: {args.output}")
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
    else:
        logger.error("未能提取文本")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("程序发生未处理的异常")
        print(f"严重错误: {e}")

# 示例运行:
# python font_decoder.py https://fanqienovel.com/library/all/page_1?sort=hottes ".book-item-title" --output book_title.txt