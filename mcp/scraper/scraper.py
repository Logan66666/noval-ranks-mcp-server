#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态页面抓取工具

功能描述：
  使用Selenium自动化浏览器抓取动态渲染的网页内容
  支持无界面模式、自定义User-Agent，自动保存HTML内容到本地

模块说明：
  - 配置Chrome浏览器选项（无界面模式、禁用GPU等）
  - 自动化访问目标URL并等待动态内容渲染
  - 提取页面源码并保存为HTML文件

作者：[请替换为实际作者]
创建日期：[请替换为实际创建日期]
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_dynamic_page(url, wait_selector=None, wait_time=10):
    """
    抓取动态渲染页面源码
    :param url: 目标URL
    :param wait_selector: 等待的CSS选择器（如'.book-list'），为None则只等待固定时间
    :param wait_time: 最长等待秒数
    :return: 页面HTML源码字符串
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无界面模式
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0')

    print("正在初始化浏览器...")
    driver = webdriver.Chrome(options=chrome_options)
    print(f"正在访问页面: {url}")
    driver.get(url)

    if wait_selector:
        print(f"等待页面元素 {wait_selector} 最多 {wait_time} 秒...")
        try:
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
            )
            print("页面主要内容已加载")
        except Exception as e:
            print(f"等待页面元素超时，可能页面结构有变或加载过慢：{e}")
    else:
        print(f"固定等待 {wait_time} 秒...")
        time.sleep(wait_time)

    html_content = driver.page_source
    print(f"页面获取成功, 长度: {len(html_content)/1024:.1f} KB")
    driver.quit()
    return html_content

if __name__ == "__main__":
    url = 'https://fanqienovel.com/library/all/page_1?sort=hottes'
    # 你可以根据实际页面结构调整选择器
    selector = '.book-list'  # 示例选择器，需根据实际页面调整
    html_content = get_dynamic_page(url, wait_selector=selector, wait_time=10)
    with open(os.path.join('debug', 'dynamic_page_content.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    print('页面内容已保存到 debug/dynamic_page_content.html 文件')