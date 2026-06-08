import os

# 基础模板内容
base_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 序光</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        /* 导航栏 */
        .navbar {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .logo {{
            font-size: 18px;
            font-weight: 700;
            color: white;
        }}
        
        .nav-links {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .nav-item {{
            position: relative;
        }}
        
        .nav-item a {{
            color: white;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 15px;
            border-radius: 20px;
            transition: all 0.3s;
            display: block;
        }}
        
        .nav-item a:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}
        
        .nav-item.has-dropdown:hover .dropdown {{
            display: block;
        }}
        
        .dropdown {{
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            padding: 8px 0;
            min-width: 150px;
            z-index: 100;
            margin-top: 5px;
        }}
        
        .dropdown li {{
            list-style: none;
        }}
        
        .dropdown li a {{
            color: #333;
            padding: 10px 20px;
            border-radius: 0;
        }}
        
        .dropdown li a:hover {{
            background: #f5f5f5;
        }}
        
        /* 语言选择器 */
        .lang-select {{
            color: white;
            font-size: 14px;
            cursor: pointer;
            padding: 8px 12px;
            border-radius: 20px;
            transition: all 0.3s;
        }}
        
        .lang-select:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}
        
        /* 页面标题 */
        .page-header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .page-header h1 {{
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .page-header p {{
            color: rgba(255, 255, 255, 0.85);
            font-size: 16px;
        }}
        
        /* 主内容区 */
        .main-content {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
            max-width: 1000px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">📊 序光</div>
        <div class="nav-links">
            <div class="nav-item"><a href="/">首页</a></div>
            <div class="nav-item"><a href="/ai">AI助手</a></div>
            <div class="nav-item has-dropdown">
                <a href="/tools">工具</a>
                <ul class="dropdown">
                    <li><a href="/tools/clean">数据清洗</a></li>
                    <li><a href="/dedup">去重对比</a></li>
                    <li><a href="/convert">格式转换</a></li>
                    <li><a href="/beautify">美化排版</a></li>
                    <li><a href="/formulas">公式大全</a></li>
                    <li><a href="/statistics">数据分析</a></li>
                    <li><a href="/charts">图表生成</a></li>
                    <li><a href="/batch">批量处理</a></li>
                </ul>
            </div>
            <div class="nav-item"><a href="/templates">模板</a></div>
            <div class="nav-item"><a href="/pricing">定价</a></div>
            <div class="nav-item"><a href="/tutorial">教程</a></div>
            <div class="nav-item has-dropdown">
                <a href="#">用户</a>
                <ul class="dropdown">
                    <li><a href="/user/files">我的文件</a></li>
                    <li><a href="/user/history">处理记录</a></li>
                    <li><a href="/user/templates">我的模板</a></li>
                    <li><a href="/user/member">会员中心</a></li>
                    <li><a href="/user/settings">账号设置</a></li>
                </ul>
            </div>
            <div class="lang-select">🌐 简体中文</div>
        </div>
    </nav>

    <div class="page-header">
        <h1>{icon} {header}</h1>
        <p>{description}</p>
    </div>

    <div class="main-content">
        <h2 style="color: #333; margin-bottom: 20px;">功能开发中...</h2>
        <p style="color: #666;">敬请期待！</p>
    </div>
</body>
</html>
'''

# 要修复的文件列表
pages = [
    ('ai.html', 'AI助手', '🤖', '智能AI为您处理Excel数据'),
    ('batch.html', '批量处理', '📦', '一次性处理多个Excel文件'),
    ('beautify.html', '美化排版', '✨', '让您的表格美观专业'),
    ('charts.html', '图表生成', '📈', '一键生成专业数据分析图表'),
    ('clean.html', '数据清洗', '🧹', '智能清洗Excel数据'),
    ('convert.html', '格式转换', '🔄', 'Excel格式相互转换'),
    ('formulas.html', '公式大全', '🔢', 'Excel常用公式速查'),
    ('home.html', '首页', '🏠', '序光'),
    ('index.html', '首页', '🏠', '序光'),
    ('pricing.html', '定价', '💰', '查看会员价格和权益'),
    ('split.html', '文件拆分', '✂️', 'Excel文件智能拆分'),
    ('statistics.html', '数据分析', '📊', '专业的数据统计分析'),
    ('templates.html', '模板', '📑', '精美Excel模板下载'),
    ('tools.html', '工具', '🛠️', 'Excel工具集合'),
    ('tutorial.html', '教程', '📚', '学习Excel使用技巧'),
    ('user_files.html', '我的文件', '📁', '管理您上传的文件'),
    ('user_history.html', '处理记录', '📋', '查看历史处理记录'),
    ('user_member.html', '会员中心', '⭐', '会员专属功能'),
    ('user_settings.html', '账号设置', '⚙️', '管理您的账号信息'),
    ('user_templates.html', '我的模板', '📄', '您保存的Excel模板'),
]

templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

for filename, title, icon, description in pages:
    filepath = os.path.join(templates_dir, filename)
    
    content = base_template.format(
        title=title,
        header=title,
        icon=icon,
        description=description
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'已修复 {filename}')

print('\n所有文件修复完成！')
