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
  - mcp_handler: MCP客户端处理函数，支持MCP调用

作者：[请替换为实际作者]
创建日期：[请替换为实际创建日期]
"""

import requests
import json
import os
import sys
from urllib.parse import urlencode

def get_book_list(page_count=20, page_index=0, gender=-1, category_id=-1, 
                 creation_status=-1, word_count=-1, book_type=-1, sort=0):
    """
    获取番茄小说书籍列表
    
    参数:
        page_count (int): 每页显示的书籍数量
        page_index (int): 页码索引，从0开始
        gender (int): 性别筛选，-1表示全部，0表示女性，1表示男性
        category_id (int): 分类ID，-1表示全部
        creation_status (int): 创作状态，-1表示全部，0表示已完结，1表示连载中
        word_count (int): 书籍总字数，-1表示字数不限
        book_type (int): 书籍类型，-1表示全部
        sort (int): 排序方式，0表示最热，1表示最新，2表示字数最多
        
    返回:
        tuple: (数据字典, 保存的文件路径)，如果失败则返回 (None, None)
    """
    url = "https://fanqienovel.com/api/author/library/book_list/v0/"
    
    # 请求参数
    params = {
        'page_count': page_count,
        'page_index': page_index,
        'gender': gender,   # 性别，-1表示全部,0表示女性，1表示男性
        'category_id': category_id,  # 分类，-1表示全部
        'creation_status': creation_status,  # 创作状态，-1表示全部，0表示已完结，1表示连载中
        'word_count': word_count,   # 书籍总字数，-1表示字数不限
        'book_type': book_type,    # 必填
        'sort': sort   # 排序方式，0表示最热，1表示最新，2表示字数最多
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

def mcp_handler():
    """
    MCP客户端处理函数
    用于处理来自MCP客户端的请求，读取标准输入中的参数，调用get_book_list函数，
    并将结果以JSON格式返回到标准输出
    
    使用方式:
    python -m mcp.api.client <参数>
    """
    try:
        # 从标准输入读取参数
        input_data = json.load(sys.stdin)
        
        # 提取参数，使用默认值
        params = {
            'page_count': input_data.get('page_count', 20),
            'page_index': input_data.get('page_index', 0),
            'gender': input_data.get('gender', -1),
            'category_id': input_data.get('category_id', -1),
            'creation_status': input_data.get('creation_status', -1),
            'word_count': input_data.get('word_count', -1),
            'book_type': input_data.get('book_type', -1),
            'sort': input_data.get('sort', 0)
        }
        
        # 调用API函数
        data, _ = get_book_list(**params)
        
        # 输出结果到标准输出
        result = {
            'success': data is not None,
            'data': data
        }
        json.dump(result, sys.stdout, ensure_ascii=False)
        
    except Exception as e:
        # 返回错误信息
        error_result = {
            'success': False,
            'error': str(e)
        }
        json.dump(error_result, sys.stdout, ensure_ascii=False)

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
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        # MCP模式
        mcp_handler()
    else:
        # 常规模式
        main()