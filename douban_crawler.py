import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
import pandas as pd
from typing import List, Dict
import os


class DoubanCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def extract_all_links(self, url: str) -> List[str]:
        """提取所有讨论链接，并排除个人主页链接"""
        print(f"正在访问: {url}")

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                print(f"请求失败: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            links = []

            # 查找table下面的td下面的title里面的a标签
            tables = soup.find_all('table')
            print(f"找到 {len(tables)} 个table标签")

            for table in tables:
                tds = table.find_all('td')
                for td in tds:
                    # 查找td下的title标签
                    title = td.find('a', class_='title') or td.find('a')
                    if title and title.get('href'):
                        href = title.get('href', '')
                        if href:
                            full_url = urljoin('https://www.douban.com', href)
                            # 排除个人主页链接
                            if full_url not in links and 'https://www.douban.com/people' not in full_url:
                                links.append(full_url)
                                title_text = title.get_text(strip=True)
                                print(f"  找到链接: {title_text[:30]}... -> {full_url}")

            print(f"总共找到 {len(links)} 个有效链接")
            return links

        except Exception as e:
            print(f"提取链接失败: {e}")
            return []

    def extract_content_and_images(self, url: str) -> List[Dict]:
        """提取页面正文文字和图片，按照顺序返回"""
        print(f"正在爬取: {url}")

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                print(f"  请求失败: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            content_items = []

            # 查找主要内容区域（豆瓣讨论帖子通常在topic-doc或类似的div中）
            content_containers = [
                soup.find('div', class_='topic-doc'),
                soup.find('div', class_='topic-content'),
                soup.find('div', id='link-report'),
                soup.find('div', class_='rich-content'),
                soup.find('div', class_='article'),
            ]

            content_area = None
            for container in content_containers:
                if container:
                    content_area = container
                    break

            # 如果找不到特定容器，尝试查找包含主要内容的大div
            if not content_area:
                possible_areas = soup.find_all('div', {'class': re.compile('topic|content|doc|article')})
                if possible_areas:
                    # 选择包含最多文本内容的div
                    content_area = max(possible_areas, key=lambda x: len(x.get_text()))

            if not content_area:
                print(f"  未找到内容区域")
                return []

            # 使用更简单直接的方法：按顺序提取段落和图片
            # 先获取所有图片和文本块，然后按DOM位置排序
            all_elements = []

            # 收集所有图片及其在DOM中的位置
            for img in content_area.find_all('img'):
                img_url = img.get('src') or img.get('data-src') or img.get('data-origin') or ''
                if img_url:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = urljoin('https://www.douban.com', img_url)
                    elif not img_url.startswith('http'):
                        img_url = urljoin(url, img_url)

                    # 排除装饰性图片
                    if 'icon' not in img_url.lower() and 'avatar' not in img_url.lower() and 'emoji' not in img_url.lower():
                        # 获取元素在DOM中的位置
                        pos = 0
                        for elem in content_area.descendants:
                            if elem == img:
                                break
                            pos += 1
                        all_elements.append(('img', img_url, pos))

            # 提取文本段落：按p标签或换行符分割
            # 方法1：尝试按p标签提取
            paragraphs = content_area.find_all('p')
            if paragraphs:
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 3:
                        pos = 0
                        for elem in content_area.descendants:
                            if elem == p:
                                break
                            pos += 1
                        all_elements.append(('text', text, pos))

            # 方法2：如果p标签太少，使用换行符分割整个文本
            if len([e for e in all_elements if e[0] == 'text']) < 1:
                full_text = content_area.get_text(separator='\n', strip=True)
                if full_text:
                    # 按双换行或单换行分割段落
                    parts = re.split(r'\n\s*\n', full_text)
                    for i, part in enumerate(parts):
                        part = part.strip().replace('\n', ' ')
                        if part and len(part) > 3:
                            all_elements.append(('text', part, i * 1000))  # 用索引作为位置

            # 按位置排序
            all_elements.sort(key=lambda x: x[2])

            # 转换为结果格式
            order = 1
            for elem_type, content, _ in all_elements:
                if elem_type == 'img':
                    content_items.append({
                        'type': '图片',
                        'content': content,
                        'order': order
                    })
                    order += 1
                elif elem_type == 'text':
                    # 清理文本
                    content = re.sub(r'\s+', ' ', content).strip()
                    if len(content) > 3:
                        content_items.append({
                            'type': '文本',
                            'content': content,
                            'order': order
                        })
                        order += 1

            # 如果提取的内容太少，使用备用方法
            if len(content_items) < 2:
                # 备用方法：提取所有段落和图片
                paragraphs = content_area.find_all(['p', 'div', 'br'])
                imgs = content_area.find_all('img')

                content_items = []
                order = 1

                # 提取所有图片
                for img in imgs:
                    img_url = img.get('src') or img.get('data-src') or ''
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = urljoin('https://www.douban.com', img_url)
                        elif not img_url.startswith('http'):
                            img_url = urljoin(url, img_url)

                        if 'icon' not in img_url.lower() and 'avatar' not in img_url.lower():
                            content_items.append({
                                'type': '图片',
                                'content': img_url,
                                'order': order
                            })
                            order += 1

                # 提取文本（使用get_text获取纯文本）
                full_text = content_area.get_text(separator='\n', strip=True)
                if full_text and len(full_text) > 10:
                    # 按段落分割
                    paragraphs_text = [p.strip() for p in full_text.split('\n') if p.strip() and len(p.strip()) > 3]
                    for para in paragraphs_text:
                        content_items.append({
                            'type': '文本',
                            'content': para,
                            'order': order
                        })
                        order += 1

            print(f"  提取到 {len([x for x in content_items if x['type'] == '文本'])} 段文本, "
                  f"{len([x for x in content_items if x['type'] == '图片'])} 张图片")
            return content_items

        except Exception as e:
            print(f"  提取内容失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def crawl_all_links(self, excel_file: str = 'douban_links.xlsx',
                        output_file: str = 'douban_content.xlsx'):
        """从Excel读取链接，遍历爬取内容并保存"""

        # 读取链接
        if not os.path.exists(excel_file):
            print(f"文件不存在: {excel_file}")
            return

        df = pd.read_excel(excel_file)
        if '链接' not in df.columns:
            print(f"Excel文件中没有'链接'列")
            return

        links = df['链接'].tolist()

        # 过滤掉个人主页链接
        original_count = len(links)
        links = [link for link in links if 'https://www.douban.com/people' not in str(link)]
        filtered_count = original_count - len(links)

        if filtered_count > 0:
            print(f"\n已过滤 {filtered_count} 个个人主页链接")

        print(f"\n开始爬取 {len(links)} 个链接的内容...\n")

        all_results = []

        for idx, link in enumerate(links, 1):
            print(f"[{idx}/{len(links)}] ", end='')
            content_items = self.extract_content_and_images(link)

            if content_items:
                for item in content_items:
                    all_results.append({
                        '链接': link,
                        '序号': item['order'],
                        '类型': item['type'],
                        '内容': item['content']
                    })
            else:
                # 即使没有内容也记录链接
                all_results.append({
                    '链接': link,
                    '序号': 0,
                    '类型': '无内容',
                    '内容': ''
                })

            # 避免请求过快
            if idx < len(links):
                time.sleep(1)

        # 保存到Excel
        if all_results:
            result_df = pd.DataFrame(all_results)
            result_df.to_excel(output_file, index=False)
            print(f"\n✓ 已保存 {len(all_results)} 条记录到 {output_file}")
        else:
            print("\n✗ 没有提取到任何内容")


if __name__ == "__main__":
    crawler = DoubanCrawler()

    # 选项1: 提取链接（如果还没有提取过）
    # url = "https://www.douban.com/group/708955/discussion?start=50&type=new&tab=62502"
    # links = crawler.extract_all_links(url)
    # if links:
    #     df = pd.DataFrame({'链接': links})
    #     df.to_excel('douban_links.xlsx', index=False)
    #     print(f"\n✓ 已保存 {len(links)} 个链接到 douban_links.xlsx")

    # 选项2: 从Excel读取链接并爬取内容
    crawler.crawl_all_links('douban_links.xlsx', 'douban_content.xlsx')