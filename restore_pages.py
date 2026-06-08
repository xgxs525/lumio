import os

templates_dir = os.path.join(os.path.dirname(__file__), "templates")

# 工具页面内容
tool_page = '''<!DOCTYPE html>
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
        
        .main-content {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
        }}
        
        .tool-section {{
            margin-bottom: 30px;
        }}
        
        .tool-section:last-child {{
            margin-bottom: 0;
        }}
        
        .tool-title {{
            font-size: 20px;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .tool-desc {{
            color: #666;
            line-height: 1.6;
            margin-bottom: 20px;
        }}
        
        .upload-area {{
            border: 2px dashed #d1d5db;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .upload-area:hover {{
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.05);
        }}
        
        .upload-icon {{
            font-size: 48px;
            margin-bottom: 15px;
        }}
        
        .upload-text {{
            font-size: 16px;
            color: #666;
            margin-bottom: 10px;
        }}
        
        .upload-hint {{
            font-size: 14px;
            color: #999;
        }}
        
        .btn {{
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 20px;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .features-list {{
            list-style: none;
            padding: 0;
        }}
        
        .features-list li {{
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
            color: #666;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .features-list li:last-child {{
            border-bottom: none;
        }}
        
        .features-list li::before {{
            content: '✓';
            color: #10b981;
            font-weight: bold;
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
                    <li><a href="/split">文件拆分</a></li>
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
        <h1>{icon} {title}</h1>
        <p>{description}</p>
    </div>

    <div class="main-content">
        <div class="tool-section">
            <div class="upload-area">
                <div class="upload-icon">📁</div>
                <div class="upload-text">拖拽Excel文件到这里或点击上传</div>
                <div class="upload-hint">支持 .xlsx, .xls 格式</div>
            </div>
            <button class="btn btn-primary">开始{title}</button>
        </div>
        
        <div class="tool-section">
            <h3 class="tool-title">✨ 功能特点</h3>
            <ul class="features-list">
                {features}
            </ul>
        </div>
    </div>
</body>
</html>
'''

# 用户页面内容
user_page = '''<!DOCTYPE html>
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
        
        .main-content {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        .user-menu {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        .menu-item {{
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
        }}
        
        .menu-item.active {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .menu-item:hover:not(.active) {{
            background: #f5f5f5;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
        }}
        
        .empty-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        
        .empty-text {{
            font-size: 18px;
            color: #666;
            margin-bottom: 10px;
        }}
        
        .empty-hint {{
            font-size: 14px;
            color: #999;
        }}
        
        .file-list {{
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .file-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin-bottom: 10px;
            transition: all 0.3s;
        }}
        
        .file-item:hover {{
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        
        .file-info {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .file-icon {{
            font-size: 32px;
        }}
        
        .file-name {{
            font-weight: 500;
            color: #333;
        }}
        
        .file-meta {{
            font-size: 12px;
            color: #999;
        }}
        
        .file-actions {{
            display: flex;
            gap: 10px;
        }}
        
        .action-btn {{
            padding: 8px 15px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .action-btn.download {{
            background: #667eea;
            color: white;
        }}
        
        .action-btn.download:hover {{
            background: #5a6fd6;
        }}
        
        .action-btn.delete {{
            background: #fef2f2;
            color: #ef4444;
        }}
        
        .action-btn.delete:hover {{
            background: #fee2e2;
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
                    <li><a href="/split">文件拆分</a></li>
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
        <h1>{icon} {title}</h1>
        <p>{description}</p>
    </div>

    <div class="main-content">
        <div class="empty-state">
            <div class="empty-icon">{empty_icon}</div>
            <div class="empty-text">暂无{title_lower}</div>
            <div class="empty-hint">快来体验我们的功能吧！</div>
        </div>
    </div>
</body>
</html>
'''

# 工具页面配置
tools = [
    ('ai.html', 'AI助手', '🤖', '智能AI帮您处理Excel任务', ['智能问答', '公式生成', '数据分析', '图表建议']),
    ('tools.html', '工具中心', '🛠️', 'Excel工具集合', ['文件拆分', '数据清洗', '去重对比', '格式转换']),
    ('split.html', '文件拆分', '✂️', 'Excel文件智能拆分', ['按列拆分', '按行拆分', '按工作表拆分', '批量处理']),
    ('clean.html', '数据清洗', '🧹', '智能清洗Excel数据', ['去除空值', '删除重复', '格式统一', '数据验证']),
    ('convert.html', '格式转换', '🔄', 'Excel格式相互转换', ['xlsx转xls', 'xls转csv', 'csv转xlsx', '批量转换']),
    ('beautify.html', '美化排版', '✨', '让您的表格美观专业', ['自动格式', '颜色美化', '字体优化', '样式套用']),
    ('formulas.html', '公式大全', '🔢', 'Excel常用公式速查', ['财务公式', '统计公式', '文本公式', '日期公式']),
    ('statistics.html', '数据分析', '📊', '专业的数据统计分析', ['数据透视', '统计分析', '趋势预测', '可视化']),
    ('charts.html', '图表生成', '📈', '一键生成专业图表', ['柱状图', '折线图', '饼图', '散点图']),
    ('batch.html', '批量处理', '📦', '一次性处理多个文件', ['批量拆分', '批量转换', '批量清洗', '批量美化']),
    ('templates.html', '模板中心', '📑', '精美Excel模板下载', ['财务报表', '人事表格', '销售报表', '项目管理']),
    ('tutorial.html', '教程中心', '📚', '学习Excel使用技巧', ['基础操作', '高级技巧', '公式教程', 'VBA入门']),
]

# 用户页面配置
user_pages = [
    ('user_files.html', '我的文件', '📁', '管理您上传的文件', '📂'),
    ('user_history.html', '处理记录', '📋', '查看历史处理记录', '📝'),
    ('user_templates.html', '我的模板', '📄', '您保存的Excel模板', '📑'),
    ('user_member.html', '会员中心', '⭐', '会员专属功能', '👤'),
    ('user_settings.html', '账号设置', '⚙️', '管理您的账号信息', '🔧'),
]

# 生成工具页面
for filename, title, icon, description, features in tools:
    filepath = os.path.join(templates_dir, filename)
    features_html = '\n'.join([f'<li>{f}</li>' for f in features])
    content = tool_page.format(
        title=title,
        icon=icon,
        description=description,
        features=features_html
    )
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'已恢复 {filename}')

# 生成用户页面
for filename, title, icon, description, empty_icon in user_pages:
    filepath = os.path.join(templates_dir, filename)
    content = user_page.format(
        title=title,
        title_lower=title.lower(),
        icon=icon,
        description=description,
        empty_icon=empty_icon
    )
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'已恢复 {filename}')

print('\n所有页面已恢复！')
