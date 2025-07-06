#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说API客户端

功能描述：
  提供与番茄小说API交互的客户端功能，支持获取书籍列表数据
  包含请求参数封装、HTTP请求发送、响应解析等核心逻辑

模块说明：
  - get_book_list: 主接口函数，获取书籍列表数据
  - main: 命令行入口函数，执行数据获取并保存

作者：[请替换为实际作者]
创建日期：[请替换为实际创建日期]
"""

import requests
import json
import os
from urllib.parse import urlencode

def get_book_list():
    """
    获取番茄小说书籍列表
    
    返回:
        tuple: (数据字典, 保存的文件路径)，如果失败则返回 (None, None)
    """
    url = "https://fanqienovel.com/api/author/library/book_list/v0/"
    
    # 请求参数
    params = {
        'page_count': 20,
        'page_index': 0,
        'gender': -1,   # 性别，-1表示全部,0表示女性，1表示男性
        'category_id': -1,  # 分类，-1表示全部
        'creation_status': -1,  # 创作状态，-1表示全部，0表示已完结，1表示连载中
        'word_count': -1,   # 书籍总字数，-1表示字数不限
        'book_type': -1,    # 必填
        'sort': 0   # 排序方式，0表示最热，1表示最新，2表示字数最多
    }
    
    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        # 发送GET请求前，打印完整URL
        full_url = url + '?' + urlencode(params)
        print(f"请求URL: {full_url}")
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()  # 检查HTTP错误
        
        # 获取JSON数据
        data = response.json()
        
        # 确保debug目录存在
        os.makedirs('debug', exist_ok=True)
        
        # 保存原始数据
        output_file = os.path.join('debug', 'raw_api_data.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"原始API数据已保存到: {output_file}")
        except Exception as e:
            print(f"保存API数据失败: {e}")
            return data, None
        
        return data, output_file
        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print(f"响应内容: {response.text[:500]}...")  # 显示前500个字符
        return None, None
    except Exception as e:
        print(f"未知错误: {e}")
        return None, None

def main():
    """
    主函数
    """
    print("正在获取番茄小说书籍列表...")
    
    # 获取数据
    raw_data, saved_file = get_book_list()
    
    if raw_data is None:
        print("获取数据失败")
        return
    
    # 显示原始数据
    print("获取数据成功！")
    print(f"原始数据: {json.dumps(raw_data, ensure_ascii=False)[:500]}...")
    print(f"数据已保存到: {saved_file}")

if __name__ == "__main__":
    main()