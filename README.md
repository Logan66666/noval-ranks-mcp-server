# 番茄小说API客户端

这个项目包含用于获取番茄小说书籍列表的Python脚本，并专门处理返回数据中的中文编码问题。

## 文件说明

- `fanqie_api_client.py` - 完整版客户端，包含详细的错误处理和数据展示
- `simple_client.py` - 简化版客户端，专注于编码问题处理
- `requirements.txt` - 项目依赖

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方法1：使用完整版客户端

```bash
python fanqie_api_client.py
```

这个脚本会：
- 获取番茄小说的书籍列表
- 处理中文编码问题
- 在控制台显示书籍信息
- 将处理后的数据保存到 `book_list.json`

### 方法2：使用简化版客户端

```bash
python simple_client.py
```

这个脚本会：
- 获取书籍列表
- 专门处理Unicode编码问题
- 显示前5本书的信息
- 将清理后的数据保存到 `clean_data.json`

## 编码问题处理

脚本主要解决以下编码问题：

1. **Unicode转义序列**: 将 `\uXXXX` 格式转换为正确的中文字符
2. **响应编码**: 强制使用UTF-8编码解析响应
3. **控制台显示**: 在Windows下设置正确的控制台编码

## API接口

**URL**: `https://fanqienovel.com/api/author/library/book_list/v0/`

**参数**:
- `gender`: 性别筛选 (-1表示全部)
- `category_id`: 分类ID (-1表示全部)
- `creation_status`: 创作状态 (-1表示全部)
- `word_count`: 字数筛选 (-1表示全部)
- `book_type`: 书籍类型 (-1表示全部)
- `sort`: 排序方式 (0表示默认)

## 输出文件

- `book_list.json` - 完整版脚本的输出文件
- `clean_data.json` - 简化版脚本的输出文件

两个文件都包含处理后的JSON数据，确保中文内容正确显示。

## 注意事项

1. 确保网络连接正常
2. 某些防火墙可能会阻止请求
3. API可能有访问频率限制
4. 如果遇到编码问题，可以尝试不同的编码处理方法

## 故障排除

如果遇到编码显示问题：

1. 确保终端/控制台支持UTF-8编码
2. 在Windows下，脚本会自动设置控制台编码
3. 查看生成的JSON文件确认数据是否正确处理