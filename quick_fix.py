import os
import re

templates_dir = r"I:\Xuguang-NexaOffice\templates"

# 获取所有HTML文件
html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]

for filename in html_files:
    filepath = os.path.join(templates_dir, filename)
    print(f"\n检查 {filename}...")
    
    try:
        # 先读取原始字节
        with open(filepath, 'rb') as f:
            raw_bytes = f.read()
        
        # 尝试解码
        content = raw_bytes.decode('utf-8', errors='replace')
        
        # 修复常见的损坏模式
        fixes = [
            # 修复lang-select闭合标签
            (r'<div class="lang-select">([^<]+?)/div>', r'<div class="lang-select">\1</div>'),
            # 修复"简体中?"
            (r'简体中\?', r'简体中文'),
            # 修复"表格差?"
            (r'表格差\?', r'表格差异'),
            # 修复其他常见的问号损坏
            (r'([\u4e00-\u9fff]{3})\?', lambda m: m.group(1) + '文' if m.group(1) == '简体中' else m.group(0)),
        ]
        
        orig_content = content
        for pattern, repl in fixes:
            content = re.sub(pattern, repl, content)
        
        # 如果有修改，保存
        if content != orig_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  → 已修复并保存")
        else:
            print(f"  → 无需修复")
            
    except Exception as e:
        print(f"  → 错误: {e}")

print("\n所有文件检查完成！")
