# SCI论文爬虫API

## 功能

- 支持从多个来源爬取SCI论文（当前已实现PubMed）
- 自动提取DOI信息
- 自动分页爬取
- FastAPI + Uvicorn 高性能异步API
- 自动生成交互式API文档
- 预留其他论文来源扩展接口

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python run.py
# 或
python api_sci.py
```

服务将运行在 `http://0.0.0.0:5009`

### 3. 访问Swagger调试界面 🎯

**Swagger UI (推荐)**: http://localhost:5009/docs

这是一个交互式API调试界面，可以直接在浏览器中测试所有接口！

**其他文档格式**:
- ReDoc: http://localhost:5009/redoc
- OpenAPI JSON: http://localhost:5009/openapi.json

📖 详细使用教程请查看: [SWAGGER_GUIDE.md](SWAGGER_GUIDE.md)

## 🎯 Swagger快速开始

### 在浏览器中调试（最简单）

1. 启动服务后，浏览器打开: http://localhost:5009/docs
2. 找到 `POST /crawl` 接口（论文爬取标签下）
3. 点击 **"Try it out"** 按钮
4. 修改请求参数：
   ```json
   {
     "source": "pubmed",
     "keyword": "artificial intelligence",
     "count": 5
   }
   ```
5. 点击 **"Execute"** 按钮
6. 查看响应结果！

✨ **无需写代码，直接在网页上测试所有接口！**

## API端点

### GET /health
健康检查

```bash
curl http://localhost:5009/health
```

### GET /info
服务信息

```bash
curl http://localhost:5009/info
```

### GET /sources
获取支持的论文来源

```bash
curl http://localhost:5009/sources
```

### POST /crawl
爬取论文（核心功能）⭐

```bash
curl -X POST http://localhost:5009/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "source": "pubmed",
    "keyword": "mental health",
    "count": 5
  }'
```

## 使用方法

### API调用示例

```python
import requests

# 爬取论文
response = requests.post('http://localhost:5009/crawl', json={
    'source': 'pubmed',
    'keyword': 'mental health',
    'count': 10
})

result = response.json()
if result['success']:
    papers = result['data']['papers']
    for paper in papers:
        print(f"DOI: {paper['doi']}")
        print(f"引用: {paper['citation']}")
        print(f"内容预览: {paper['content'][:200]}...")
```

### Python SDK使用

```python
from get_sci import SciCrawler

crawler = SciCrawler()

# 从PubMed爬取论文
papers = crawler.crawl(
    source='pubmed',
    keyword='mental health',
    count=10
)

# 查看结果
for paper in papers:
    print(f"DOI: {paper['doi']}")
    print(f"引用: {paper['citation']}")
```

## 支持的论文来源

- [x] PubMed
- [ ] Scopus（预留）
- [ ] Web of Science（预留）
- [ ] Google Scholar（预留）

## 返回数据格式

```json
{
  "success": true,
  "data": {
    "source": "pubmed",
    "keyword": "mental health",
    "requested_count": 10,
    "actual_count": 10,
    "papers": [
      {
        "doi": "10.1146/annurev-publhealth-040119-094247",
        "doi_url": "https://doi.org/10.1146/annurev-publhealth-040119-094247",
        "citation": "Annu Rev Public Health. 2020 Apr 2;41:201-221...",
        "content": "论文内容..."
      }
    ]
  }
}
```

## 注意事项

- 爬取间隔设置为1秒，避免请求过快
- 单次最多爬取100篇论文
- 单次请求最多爬取50页
- 论文内容截取前5000字符

## 技术栈

- FastAPI - 现代高性能Web框架
- Uvicorn - ASGI服务器
- BeautifulSoup4 - HTML解析
- Requests - HTTP客户端
