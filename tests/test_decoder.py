import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp.decoder.decoder import FontDecoder

# 测试用本地字体文件和HTML文件路径
FONT_PATH = os.path.join('cache', 'fonts', 'e26e946d8b2ccb7.otf')
HTML_PATH = os.path.join('debug', 'dynamic_page_content.html')


def test_font_mapping():
    """
    测试字体文件的映射解析功能
    """
    if not os.path.exists(FONT_PATH):
        print(f"字体文件不存在: {FONT_PATH}")
        return
    with open(FONT_PATH, 'rb') as f:
        font_data = f.read()
    decoder = FontDecoder()
    mapping = decoder.parse_font_mapping(font_data)
    print(f"映射表长度: {len(mapping)}")
    for k, v in list(mapping.items())[:10]:
        print(f"映射: {repr(k)} -> {repr(v)}")


def test_decrypt_text():
    """
    测试解密功能
    """
    decoder = FontDecoder()
    # 假设已更新映射
    if not os.path.exists(HTML_PATH):
        print(f"HTML文件不存在: {HTML_PATH}")
        return
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html_content = f.read()
    decoder.update_font_mapping(html_content=html_content)
    # 假设有乱码文本
    encrypted_text = '赤流星划际'  # 示例乱码
    decrypted = decoder.decrypt_text(encrypted_text)
    print(f"原文: {encrypted_text} -> 解密后: {decrypted}")


if __name__ == "__main__":
    print("--- 测试字体映射解析 ---")
    test_font_mapping()
    print("\n--- 测试解密功能 ---")
    test_decrypt_text()
