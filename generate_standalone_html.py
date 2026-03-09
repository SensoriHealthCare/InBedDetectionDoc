#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 Markdown 和 .assets 中的所有图片转换为一个独立的 HTML 文件
所有图片转换为 Base64 Data URI，无需外部资源
"""

import base64
import re
from pathlib import Path
import markdown

def get_base64_image(image_path):
    """读取图片文件并转换为 Base64 Data URI"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # 获取文件扩展名来确定 MIME 类型
    suffix = image_path.suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml'
    }
    mime_type = mime_types.get(suffix, 'image/png')
    
    base64_str = base64.b64encode(image_data).decode('utf-8')
    return f"data:{mime_type};base64,{base64_str}"

def convert_md_to_html(md_file, assets_dir):
    """将 Markdown 转换为 HTML 并嵌入所有图片"""
    
    # 读取 Markdown 文件
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 转换为 HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['extra', 'sane_lists', 'tables']
    )
    
    # 替换图片路径 - Markdown 格式
    def replace_markdown_img(match):
        alt_text = match.group(1)
        img_path = match.group(2).strip()
        
        # 定位到 .assets 文件夹中的图片
        if '.assets/' in img_path:
            filename = img_path.split('/')[-1]
            full_path = assets_dir / filename
            
            if full_path.exists():
                data_uri = get_base64_image(full_path)
                return f'<img src="{data_uri}" alt="{alt_text}" />'
        
        return match.group(0)
    
    # 这匹配 Markdown 的 ![alt](url) 格式，但由于 markdown 库已经转换了
    # 我们需要在原始内容中替换
    # 实际上让我们在 HTML 输出中替换 img 标签
    
    # 替换 HTML 中的 src 属性
    def replace_html_img_src(match):
        full_tag = match.group(0)
        src_match = re.search(r'src=["\']([^"\']+)["\']', full_tag)
        
        if src_match:
            src = src_match.group(1)
            
            # 处理相对路径
            if '.assets' in src:
                filename = src.split('/')[-1]
                full_path = assets_dir / filename
                
                if full_path.exists():
                    data_uri = get_base64_image(full_path)
                    new_tag = full_tag.replace(src, data_uri)
                    return new_tag
        
        return full_tag
    
    # 替换所有 <img> 标签中的 src
    html_content = re.sub(
        r'<img\b[^>]*?>',
        replace_html_img_src,
        html_content,
        flags=re.IGNORECASE
    )
    
    return html_content

def generate_standalone_html(md_file, output_file, assets_dir):
    """生成包含所有资源的独立 HTML 文件"""
    
    # 转换内容
    body_content = convert_md_to_html(md_file, assets_dir)
    
    # 完整的 HTML 模板，包含 CSS 样式
    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>在床检测模块</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --bg-color: #ffffff;
            --text-color: #333333;
            --border-color: #e0e0e0;
            --code-bg: #f5f5f5;
            --link-color: #0066cc;
        }}
        
        html {{
            font-size: 16px;
            background-color: var(--bg-color);
            color: var(--text-color);
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--bg-color);
            padding: 20px;
        }}
        
        #write {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px 0;
        }}
        
        h1 {{
            font-size: 2em;
            margin: 1.5em 0 0.5em 0;
            border-bottom: 3px solid var(--text-color);
            padding-bottom: 0.3em;
        }}
        
        h2 {{
            font-size: 1.6em;
            margin: 1.2em 0 0.4em 0;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.3em;
        }}
        
        h3 {{
            font-size: 1.3em;
            margin: 1em 0 0.3em 0;
        }}
        
        h4, h5, h6 {{
            margin: 0.8em 0 0.2em 0;
        }}
        
        p {{
            margin: 0.8em 0;
        }}
        
        ul, ol {{
            margin: 0.8em 0;
            padding-left: 2em;
        }}
        
        li {{
            margin: 0.4em 0;
        }}
        
        blockquote {{
            border-left: 4px solid var(--border-color);
            padding: 0.5em 1em;
            margin: 1em 0;
            background-color: #f9f9f9;
            color: #666;
        }}
        
        code {{
            background-color: var(--code-bg);
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
            font-size: 0.9em;
        }}
        
        pre {{
            background-color: var(--code-bg);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 1em;
            overflow-x: auto;
            margin: 1em 0;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            border-radius: 0;
        }}
        
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em 0;
            border-radius: 4px;
            border: 1px solid var(--border-color);
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        
        th, td {{
            border: 1px solid var(--border-color);
            padding: 0.8em;
            text-align: left;
        }}
        
        th {{
            background-color: var(--code-bg);
            font-weight: bold;
        }}
        
        tr:nth-child(even) {{
            background-color: #fafafa;
        }}
        
        a {{
            color: var(--link-color);
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid var(--border-color);
            margin: 1.5em 0;
        }}
        
        strong, b {{
            font-weight: 600;
        }}
        
        em, i {{
            font-style: italic;
        }}
        
        u {{
            text-decoration: underline;
        }}
        
        .task-list-item {{
            list-style: none;
            margin-left: 0.5em;
        }}
        
        .task-list-item input {{
            margin-right: 0.5em;
        }}
        
        @media screen and (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            #write {{
                padding: 10px 0;
            }}
            
            h1 {{
                font-size: 1.5em;
            }}
            
            h2 {{
                font-size: 1.3em;
            }}
            
            pre {{
                font-size: 0.85em;
            }}
        }}
        
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #1e1e1e;
                --text-color: #e0e0e0;
                --border-color: #404040;
                --code-bg: #2d2d2d;
                --link-color: #5ba3ff;
            }}
            
            blockquote {{
                background-color: #2d2d2d;
                color: #aaa;
            }}
            
            tr:nth-child(even) {{
                background-color: #252525;
            }}
        }}
    </style>
</head>
<body>
    <div id="write">
{body}
    </div>
</body>
</html>
"""
    
    # 填充内容
    full_html = html_template.format(body=body_content)
    
    # 保存文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✓ 独立 HTML 文件已生成: {output_file}")
    print(f"  大小: {len(full_html) / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    # 配置路径
    workspace_dir = Path(__file__).parent
    md_file = workspace_dir / 'index.md'
    assets_dir = workspace_dir / '.assets'
    output_file = workspace_dir / 'index_standalone.html'
    
    # 检查文件是否存在
    if not md_file.exists():
        print(f"错误: 找不到 {md_file}")
        exit(1)
    
    if not assets_dir.exists():
        print(f"错误: 找不到 {assets_dir}")
        exit(1)
    
    # 生成文件
    generate_standalone_html(md_file, output_file, assets_dir)
    print(f"\n文件大小很大是因为所有图片都嵌入为 Base64。")
    print(f"这个 HTML 文件可以完全独立使用，无需任何外部资源。")
