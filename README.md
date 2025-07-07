# 番茄小说榜单爬取与解码工具

> 本服务支持MCP协议，可自动注册为MCP Tool，支持自动发现与调用。

这个项目是一个用于爬取番茄小说网站榜单数据并解码加密文本的工具。由于番茄小说网站使用了字体加密技术来保护文本内容，本工具通过OCR技术和字体映射来解密这些内容，使其可读。



## 项目功能

- 从番茄小说API获取书籍列表数据
- 动态抓取网页获取字体文件
- 使用OCR技术生成字体映射表
- 解码加密的文本内容
- 提供OCR校验页面进行人工校验
- 输出解码后的完整数据

## 项目结构

```
noval-ranks-mcp-server/
├── mcp/                    # 核心模块目录
│   ├── api/                # API交互模块
│   ├── scraper/            # 网页抓取模块
│   └── decoder/            # 字体解码模块
├── tools/                  # 工具目录
│   ├── ocr_review/         # OCR校验工具
│   ├── ocr_chars/          # 字符图片目录
│   └── font_ocr_mapping_*.py  # OCR映射工具
├── cache/                  # 缓存目录
│   ├── fonts/              # 字体文件缓存
│   └── mappings/           # 映射表缓存
├── output/                 # 输出目录
├── debug/                  # 调试数据目录
├── logs/                   # 日志目录
├── main.py                 # 主程序入口
└── requirements.txt        # 依赖库列表
```

## 环境要求

- Python 3.7+
- Chrome浏览器（用于动态页面抓取）
- ChromeDriver（与Chrome版本匹配）
- 若要使用MCP功能，需安装uvx工具包

## 安装步骤

1. 克隆或下载项目到本地

2. 安装Python依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 安装Chrome浏览器和ChromeDriver
   - 下载Chrome浏览器: https://www.google.com/chrome/
   - 下载ChromeDriver: https://chromedriver.chromium.org/downloads
     (确保ChromeDriver版本与Chrome浏览器版本匹配)
   - 将ChromeDriver添加到系统PATH中

4. 创建必要的目录结构（如果不存在）
   ```bash
   mkdir -p cache/fonts cache/mappings output debug logs
   ```

## 使用方法

### 基本使用

运行主程序以获取并解码番茄小说榜单数据:

```bash
python main.py
```

这将执行完整的工作流程:
1. 从API获取书籍列表
2. 抓取动态页面获取字体URL
3. 下载字体文件
4. 生成OCR映射表
5. 解码API数据
6. 保存解码后的数据到`output/decoded_api_data.json`

### 命令行参数

主程序支持以下命令行参数:

- `--force-ocr-mapping`: 强制重新生成OCR映射表，即使已存在
- `--ocr-mapping-dir=PATH`: 指定OCR映射表存储目录（默认: cache/mappings）
- `--api-data-file=PATH`: 指定API数据文件路径（默认: debug/raw_api_data.json）
- `--review-html`: 生成并打开OCR人工校验页面

示例:

```bash
# 强制重新生成OCR映射表
python main.py --force-ocr-mapping

# 指定自定义映射目录和API数据文件
python main.py --ocr-mapping-dir=my_mappings --api-data-file=my_data.json

# 启动OCR校验页面
python main.py --review-html
```

## API参数说明

### 调用API模块

当前，API模块通过`mcp/api/client.py`中的`get_book_list()`函数提供服务。在`main.py`中，该函数被直接调用：

```python
from mcp.api.client import get_book_list

# 调用API获取书籍列表
book_data, api_data_file = get_book_list()
```

### API参数详解

`get_book_list()`函数支持以下参数来向番茄小说API发送请求：

| 参数名 | 默认值 | 说明 | 可选值 |
|-------|-------|------|-------|
| page_count | 20 | 每页显示的书籍数量 | 正整数，建议范围：10-50 |
| page_index | 0 | 页码索引，从0开始 | 0, 1, 2, ... |
| gender | -1 | 性别筛选 | -1(全部), 0(女性), 1(男性) |
| category_id | -1 | 分类ID | -1(全部), 或具体分类ID |
| creation_status | -1 | 创作状态 | -1(全部), 0(已完结), 1(连载中) |
| word_count | -1 | 书籍总字数筛选 | -1(不限), 或其他具体值 |
| book_type | -1 | 书籍类型 | -1(全部), 或其他具体类型ID |
| sort | 0 | 排序方式 | 0(最热), 1(最新), 2(字数最多) |

### 自定义API参数

您可以通过直接向`get_book_list()`函数传递参数来自定义API请求：

```python
# 不带参数调用，使用所有默认值
book_data, api_file = get_book_list()

# 获取女性向、已完结的小说，按最新排序
book_data, api_file = get_book_list(gender=0, creation_status=0, sort=1)

# 获取每页10本小说，男性向，第2页数据
book_data, api_file = get_book_list(page_count=10, page_index=1, gender=1)

# 获取字数最多的前20本小说
book_data, api_file = get_book_list(sort=2)
```

### OCR校验页面

OCR校验页面是一个基于Flask的Web应用，用于人工校验和修正OCR识别结果:

```bash
python main.py --review-html
```

这将:
1. 启动Flask服务器（端口5001）
2. 自动在浏览器中打开校验页面
3. 显示字符图片和OCR识别结果
4. 允许人工修正识别错误
5. 保存修正后的映射表

#### 重启Flask服务器

如果需要重启Flask服务器:

1. 使用任务管理器方式:
   - 按下`Ctrl+Alt+Delete`，选择"任务管理器"
   - 在"详细信息"或"进程"选项卡中找到`python.exe`进程
   - 右键点击并选择"结束任务"
   - 重新运行`python main.py --review-html`

2. 使用命令行方式:
   - 查找Flask进程:
     ```bash
     Get-Process -Name python | Where-Object {$_.CommandLine -like "*server.py*"}
     ```
   - 终止进程:
     ```bash
     taskkill /F /PID 进程ID
     ```
   - 重新启动:
     ```bash
     python main.py --review-html
     ```
     或直接启动服务器:
     ```bash
     python tools/ocr_review/server.py
     ```

## 工作原理

1. **API数据获取**: 通过HTTP请求获取番茄小说的书籍列表数据
2. **动态页面抓取**: 使用Selenium控制Chrome浏览器抓取动态加载的页面内容
3. **字体解析**: 从HTML中提取字体URL，下载并解析字体文件
4. **OCR映射**: 将字体中的字形渲染为图片，使用OCR技术识别字符
5. **文本解码**: 使用映射表将加密文本转换为可读内容
6. **人工校验**: 通过Web界面校验OCR结果，提高解码准确率

## 故障排除

### 常见问题

1. **字体下载失败**
   - 检查网络连接
   - 确认字体URL是否有效
   - 尝试使用代理服务器

2. **OCR识别不准确**
   - 使用`--force-ocr-mapping`重新生成映射表
   - 使用`--review-html`进行人工校验
   - 尝试调整字符渲染参数

3. **Flask服务器启动失败**
   - 检查端口5001是否被占用
   - 确认logs目录存在且有写入权限
   - 查看logs/ocr_server.log文件了解详细错误

4. **图片加载问题**
   - 确保ocr_chars目录中的图片文件存在
   - 检查浏览器开发者工具中的网络请求
   - 重启Flask服务器

### 日志文件

- API和解码日志: 控制台输出
- OCR服务器日志: `logs/ocr_server.log`

## 依赖库说明

- **requests**: HTTP请求库，用于API交互
- **selenium**: 浏览器自动化工具，用于抓取动态页面
- **beautifulsoup4**: HTML解析库，用于提取页面内容
- **fonttools**: 字体处理库，用于解析字体文件
- **lxml**: XML/HTML解析库，用于更快的页面解析
- **easyocr**: OCR识别库，用于字符识别

## 注意事项

- 本工具仅用于学习和研究目的
- 请遵守网站的使用条款和robots.txt规则
- 频繁请求可能导致IP被临时封禁
- OCR识别结果可能存在误差，建议进行人工校验

## **在MCP客户端中使用**

本项目支持作为MCP（Model Control Protocol）服务运行，允许您从MCP客户端直接调用API服务。

### 环境准备

在使用MCP功能前，请确保您已安装：

1. 最新版本的uvx工具包
   ```bash
   pip install uvx
   ```

2. 推荐配置方式：无需手动设置PYTHONPATH，只需在MCP服务配置中指定cwd字段为项目根目录。

### MCP服务配置（推荐）

```json
{
  "mcpServers": {
    "novel-ranks": {
      "command": "python",
      "args": ["-m", "mcp.api.client", "--mcp"],
      "cwd": "D:/path/noval-ranks-mcp-server"  // 这里填写你的项目根目录
    }
  }
}
```
- `cwd`：指定服务启动时的工作目录，推荐为你的项目根目录。

---

### MCP Tool声明

| Tool名称         | 功能描述           | 输入参数（JSON） | 返回值（JSON） |
|------------------|--------------------|------------------|----------------|
| get_book_list    | 获取番茄小说榜单   | 见下方参数说明   | 见下方返回说明 |

#### get_book_list

- **功能**：获取番茄小说榜单数据
- **参数**（均为可选，省略则用默认值）：

  | 参数名           | 类型   | 默认值 | 说明           |
  |------------------|--------|--------|----------------|
  | page_count       | int    | 20     | 每页数量       |
  | page_index       | int    | 0      | 页码索引       |
  | gender           | int    | -1     | 性别筛选       |
  | category_id      | int    | -1     | 分类ID         |
  | creation_status  | int    | -1     | 创作状态       |
  | word_count       | int    | -1     | 字数筛选       |
  | book_type        | int    | -1     | 书籍类型       |
  | sort             | int    | 0      | 排序方式       |

- **返回值**：

  ```json
  {
    "success": true,
    "data": { ... }  // API返回的原始数据
  }
  ```
  失败时：
  ```json
  {
    "success": false,
    "error": "错误信息"
  }
  ```

- **调用示例**：

  ```bash
  echo '{"gender":0,"sort":1}' | uvx mcp-client-call novel-ranks
  ```

---

### Python代码调用示例

```python
import json
import subprocess

def call_novel_ranks_api(params=None):
    if params is None:
        params = {}
    cmd = ["uvx", "mcp-client-call", "novel-ranks"]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(json.dumps(params))
    if process.returncode != 0:
        raise Exception(f"MCP调用失败: {stderr}")
    return json.loads(stdout)

# 示例
result = call_novel_ranks_api({"gender": 0, "sort": 1})
print(result)
```