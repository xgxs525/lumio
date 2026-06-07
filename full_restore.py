import os

templates_dir = r"I:\Xuguang-NexaOffice\templates"

# 用户文件管理页面
user_files_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的文件 - 序办</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 18px;
            font-weight: 700;
            color: white;
        }
        
        .nav-links {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .nav-item {
            position: relative;
        }
        
        .nav-item a {
            color: white;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 15px;
            border-radius: 20px;
            transition: all 0.3s;
            display: block;
        }
        
        .nav-item a:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .nav-item.has-dropdown:hover .dropdown {
            display: block;
        }
        
        .dropdown {
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
        }
        
        .dropdown li {
            list-style: none;
        }
        
        .dropdown li a {
            color: #333;
            padding: 10px 20px;
            border-radius: 0;
        }
        
        .dropdown li a:hover {
            background: #f5f5f5;
        }
        
        .lang-select {
            color: white;
            font-size: 14px;
            cursor: pointer;
            padding: 8px 12px;
            border-radius: 20px;
            transition: all 0.3s;
        }
        
        .lang-select:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .page-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .page-header h1 {
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .page-header p {
            color: rgba(255, 255, 255, 0.85);
            font-size: 16px;
        }
        
        .main-content {
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .user-menu {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .menu-item {
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
        }
        
        .menu-item.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .menu-item:hover:not(.active) {
            background: #f5f5f5;
        }
        
        .file-list {
            max-height: 600px;
            overflow-y: auto;
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            margin-bottom: 15px;
            transition: all 0.3s;
        }
        
        .file-item:hover {
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-color: #667eea;
        }
        
        .file-info {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .file-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .file-details h4 {
            color: #333;
            font-size: 16px;
            margin-bottom: 5px;
        }
        
        .file-details p {
            color: #999;
            font-size: 13px;
        }
        
        .file-actions {
            display: flex;
            gap: 10px;
        }
        
        .action-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .action-btn.download {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .action-btn.download:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .action-btn.delete {
            background: #fef2f2;
            color: #ef4444;
        }
        
        .action-btn.delete:hover {
            background: #fee2e2;
        }
        
        .upload-area {
            text-align: center;
            padding: 40px;
            border: 2px dashed #e5e7eb;
            border-radius: 12px;
            margin-bottom: 30px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.05);
        }
        
        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        .upload-text {
            color: #666;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">📊 序办</div>
        <div class="nav-links">
            <div class="nav-item"><a href="/">首页</a></div>
            <div class="nav-item"><a href="/ai">AI助手</a></div>
            <div class="nav-item.has-dropdown">
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
            <div class="nav-item.has-dropdown">
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
        <h1>📁 我的文件</h1>
        <p>管理您上传和保存的Excel文件</p>
    </div>

    <div class="main-content">
        <div class="upload-area">
            <div class="upload-icon">📤</div>
            <div class="upload-text">点击或拖拽文件上传</div>
        </div>

        <div class="file-list">
            <div class="file-item">
                <div class="file-info">
                    <div class="file-icon">📊</div>
                    <div class="file-details">
                        <h4>员工信息表.xlsx</h4>
                        <p>2.5 MB · 上传于2026-06-07</p>
                    </div>
                </div>
                <div class="file-actions">
                    <button class="action-btn download">下载</button>
                    <button class="action-btn delete">删除</button>
                </div>
            </div>
            
            <div class="file-item">
                <div class="file-info">
                    <div class="file-icon">📊</div>
                    <div class="file-details">
                        <h4>销售数据汇总.xlsx</h4>
                        <p>3.2 MB · 上传于2026-06-06</p>
                    </div>
                </div>
                <div class="file-actions">
                    <button class="action-btn download">下载</button>
                    <button class="action-btn delete">删除</button>
                </div>
            </div>
            
            <div class="file-item">
                <div class="file-info">
                    <div class="file-icon">📊</div>
                    <div class="file-details">
                        <h4>年度财务报表.xlsx</h4>
                        <p>1.8 MB · 上传于2026-06-05</p>
                    </div>
                </div>
                <div class="file-actions">
                    <button class="action-btn download">下载</button>
                    <button class="action-btn delete">删除</button>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

# 处理记录页面
user_history_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>处理记录 - 序办</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 18px;
            font-weight: 700;
            color: white;
        }
        
        .nav-links {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .nav-item {
            position: relative;
        }
        
        .nav-item a {
            color: white;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 15px;
            border-radius: 20px;
            transition: all 0.3s;
            display: block;
        }
        
        .nav-item a:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .nav-item.has-dropdown:hover .dropdown {
            display: block;
        }
        
        .dropdown {
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
        }
        
        .dropdown li {
            list-style: none;
        }
        
        .dropdown li a {
            color: #333;
            padding: 10px 20px;
            border-radius: 0;
        }
        
        .dropdown li a:hover {
            background: #f5f5f5;
        }
        
        .lang-select {
            color: white;
            font-size: 14px;
            cursor: pointer;
            padding: 8px 12px;
            border-radius: 20px;
            transition: all 0.3s;
        }
        
        .lang-select:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .page-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .page-header h1 {
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .page-header p {
            color: rgba(255, 255, 255, 0.85);
            font-size: 16px;
        }
        
        .main-content {
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .history-list {
            max-height: 600px;
            overflow-y: auto;
        }
        
        .history-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            margin-bottom: 15px;
            transition: all 0.3s;
        }
        
        .history-item:hover {
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .history-info {
            flex: 1;
        }
        
        .history-info h4 {
            color: #333;
            font-size: 16px;
            margin-bottom: 8px;
        }
        
        .history-details {
            display: flex;
            gap: 20px;
            color: #666;
            font-size: 14px;
        }
        
        .history-status {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .status-badge {
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }
        
        .status-badge.success {
            background: #dcfce7;
            color: #166534;
        }
        
        .status-badge.pending {
            background: #fef9c3;
            color: #854d0e;
        }
        
        .status-badge.failed {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .action-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">📊 序办</div>
        <div class="nav-links">
            <div class="nav-item"><a href="/">首页</a></div>
            <div class="nav-item"><a href="/ai">AI助手</a></div>
            <div class="nav-item.has-dropdown">
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
            <div class="nav-item.has-dropdown">
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
        <h1>📋 处理记录</h1>
        <p>查看您的Excel文件处理历史</p>
    </div>

    <div class="main-content">
        <div class="history-list">
            <div class="history-item">
                <div class="history-info">
                    <h4>文件拆分 - 员工信息表.xlsx</h4>
                    <div class="history-details">
                        <span>处理类型: 按列拆分</span>
                        <span>处理时间: 2026-06-07 14:30</span>
                        <span>生成文件: 5个</span>
                    </div>
                </div>
                <div class="history-status">
                    <span class="status-badge success">成功</span>
                    <button class="action-btn">查看结果</button>
                </div>
            </div>
            
            <div class="history-item">
                <div class="history-info">
                    <h4>数据清洗 - 销售数据.xlsx</h4>
                    <div class="history-details">
                        <span>处理类型: 数据清洗</span>
                        <span>处理时间: 2026-06-06 10:15</span>
                        <span>处理行数: 1,234行</span>
                    </div>
                </div>
                <div class="history-status">
                    <span class="status-badge success">成功</span>
                    <button class="action-btn">查看结果</button>
                </div>
            </div>
            
            <div class="history-item">
                <div class="history-info">
                    <h4>格式转换 - 报告.xls</h4>
                    <div class="history-details">
                        <span>处理类型: 格式转换</span>
                        <span>处理时间: 2026-06-05 16:45</span>
                        <span>转换格式: xls→xlsx</span>
                    </div>
                </div>
                <div class="history-status">
                    <span class="status-badge success">成功</span>
                    <button class="action-btn">查看结果</button>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

# 我的模板页面
user_templates_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的模板 - 序办</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 18px;
            font-weight: 700;
            color: white;
        }
        
        .nav-links {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .nav-item {
            position: relative;
        }
        
        .nav-item a {
            color: white;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 15px;
            border-radius: 20px;
            transition: all 0.3s;
            display: block;
        }
        
        .nav-item a:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .nav-item.has-dropdown:hover .dropdown {
            display: block;
        }
        
        .dropdown {
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
        }
        
        .dropdown li {
            list-style: none;
        }
        
        .dropdown li a {
            color: #333;
            padding: 10px 20px;
            border-radius: 0;
        }
        
        .dropdown li a:hover {
            background: #f5f5f5;
        }
        
        .lang-select {
            color: white;
            font-size: 14px;
            cursor: pointer;
            padding: 8px 12px;
            border-radius: 20px;
            transition: all 0.3s;
        }
        
        .lang-select:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .page-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .page-header h1 {
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .page-header p {
            color: rgba(255, 255, 255, 0.85);
            font-size: 16px;
        }
        
        .main-content {
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .template-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .template-card {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .template-card:hover {
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transform: translateY(-4px);
        }
        
        .template-preview {
            height: 150px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            color: white;
        }
        
        .template-info {
            padding: 20px;
        }
        
        .template-info h4 {
            color: #333;
            font-size: 16px;
            margin-bottom: 8px;
        }
        
        .template-info p {
            color: #999;
            font-size: 13px;
            margin-bottom: 15px;
        }
        
        .template-actions {
            display: flex;
            gap: 10px;
        }
        
        .action-btn {
            flex: 1;
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .action-btn.use {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .action-btn.use:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .action-btn.delete {
            background: #fef2f2;
            color: #ef4444;
        }
        
        .action-btn.delete:hover {
            background: #fee2e2;
        }
        
        .upload-btn {
            width: 100%;
            padding: 40px;
            border: 2px dashed #e5e7eb;
            border-radius: 12px;
            background: transparent;
            font-size: 16px;
            color: #666;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 30px;
        }
        
        .upload-btn:hover {
            border-color: #667eea;
            color: #667eea;
            background: rgba(102, 126, 234, 0.05);
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">📊 序办</div>
        <div class="nav-links">
            <div class="nav-item"><a href="/">首页</a></div>
            <div class="nav-item"><a href="/ai">AI助手</a></div>
            <div class="nav-item.has-dropdown">
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
            <div class="nav-item.has-dropdown">
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
        <h1>📄 我的模板</h1>
        <p>管理您保存的Excel模板</p>
    </div>

    <div class="main-content">
        <button class="upload-btn">📤 上传新模板</button>
        
        <div class="template-grid">
            <div class="template-card">
                <div class="template-preview">📊</div>
                <div class="template-info">
                    <h4>财务报表模板</h4>
                    <p>保存于2026-06-05</p>
                    <div class="template-actions">
                        <button class="action-btn use">使用</button>
                        <button class="action-btn delete">删除</button>
                    </div>
                </div>
            </div>
            
            <div class="template-card">
                <div class="template-preview">📊</div>
                <div class="template-info">
                    <h4>员工信息登记表</h4>
                    <p>保存于2026-06-03</p>
                    <div class="template-actions">
                        <button class="action-btn use">使用</button>
                        <button class="action-btn delete">删除</button>
                    </div>
                </div>
            </div>
            
            <div class="template-card">
                <div class="template-preview">📊</div>
                <div class="template-info">
                    <h4>销售数据分析表</h4>
                    <p>保存于2026-06-01</p>
                    <div class="template-actions">
                        <button class="action-btn use">使用</button>
                        <button class="action-btn delete">删除</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

# 账号设置页面
user_settings_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>账号设置 - 序办</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 18px;
            font-weight: 700;
            color: white;
        }
        
        .nav-links {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .nav-item {
            position: relative;
        }
        
        .nav-item a {
            color: white;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 15px;
            border-radius: 20px;
            transition: all 0.3s;
            display: block;
        }
        
        .nav-item a:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .nav-item.has-dropdown:hover .dropdown {
            display: block;
        }
        
        .dropdown {
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
        }
        
        .dropdown li {
            list-style: none;
        }
        
        .dropdown li a {
            color: #333;
            padding: 10px 20px;
            border-radius: 0;
        }
        
        .dropdown li a:hover {
            background: #f5f5f5;
        }
        
        .lang-select {
            color: white;
            font-size: 14px;
            cursor: pointer;
            padding: 8px 12px;
            border-radius: 20px;
            transition: all 0.3s;
        }
        
        .lang-select:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .page-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .page-header h1 {
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .page-header p {
            color: rgba(255, 255, 255, 0.85);
            font-size: 16px;
        }
        
        .main-content {
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
            max-width: 700px;
            margin: 0 auto;
        }
        
        .settings-section {
            margin-bottom: 40px;
        }
        
        .settings-section h3 {
            color: #333;
            font-size: 20px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        .form-group label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 10px;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 15px;
            transition: all 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn {
            padding: 14px 32px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-danger {
            background: #ef4444;
            color: white;
        }
        
        .btn-danger:hover {
            background: #dc2626;
        }
        
        .avatar-section {
            display: flex;
            align-items: center;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .avatar {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            color: white;
        }
        
        .avatar-actions button {
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">📊 序办</div>
        <div class="nav-links">
            <div class="nav-item"><a href="/">首页</a></div>
            <div class="nav-item"><a href="/ai">AI助手</a></div>
            <div class="nav-item.has-dropdown">
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
            <div class="nav-item.has-dropdown">
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
        <h1>⚙️ 账号设置</h1>
        <p>管理您的个人信息和偏好设置</p>
    </div>

    <div class="main-content">
        <div class="settings-section">
            <h3>个人资料</h3>
            
            <div class="avatar-section">
                <div class="avatar">👤</div>
                <div class="avatar-actions">
                    <button class="btn btn-primary">更换头像</button>
                </div>
            </div>
            
            <div class="form-group">
                <label>用户名</label>
                <input type="text" value="Excel用户">
            </div>
            
            <div class="form-group">
                <label>邮箱</label>
                <input type="email" value="user@example.com">
            </div>
            
            <button class="btn btn-primary">保存更改</button>
        </div>
        
        <div class="settings-section">
            <h3>安全设置</h3>
            
            <div class="form-group">
                <label>当前密码</label>
                <input type="password" placeholder="请输入当前密码">
            </div>
            
            <div class="form-group">
                <label>新密码</label>
                <input type="password" placeholder="请输入新密码">
            </div>
            
            <div class="form-group">
                <label>确认新密码</label>
                <input type="password" placeholder="请再次输入新密码">
            </div>
            
            <button class="btn btn-primary">修改密码</button>
        </div>
        
        <div class="settings-section">
            <h3>危险操作</h3>
            <button class="btn btn-danger">删除账号</button>
        </div>
    </div>
</body>
</html>
'''

# 工具页面内容生成函数
def generate_tool_page(title, icon, description, features):
    features_html = ''.join([f'<li>{f}</li>' for f in features])
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 序办</title>
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
        
        .upload-area {{
            border: 2px dashed #e5e7eb;
            border-radius: 12px;
            padding: 60px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 40px;
        }}
        
        .upload-area:hover {{
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.05);
        }}
        
        .upload-icon {{
            font-size: 56px;
            margin-bottom: 15px;
        }}
        
        .upload-text {{
            font-size: 18px;
            color: #666;
            margin-bottom: 10px;
        }}
        
        .upload-hint {{
            font-size: 14px;
            color: #999;
        }}
        
        .btn {{
            width: 100%;
            padding: 16px;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
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
            padding: 15px 0;
            border-bottom: 1px solid #f0f0f0;
            color: #666;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 15px;
        }}
        
        .features-list li:last-child {{
            border-bottom: none;
        }}
        
        .features-list li::before {{
            content: '✓';
            color: #10b981;
            font-weight: bold;
            font-size: 20px;
        }}
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">📊 序办</div>
        <div class="nav-links">
            <div class="nav-item"><a href="/">首页</a></div>
            <div class="nav-item"><a href="/ai">AI助手</a></div>
            <div class="nav-item.has-dropdown">
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
            <div class="nav-item.has-dropdown">
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
        <div class="upload-area">
            <div class="upload-icon">📤</div>
            <div class="upload-text">点击或拖拽上传Excel文件</div>
            <div class="upload-hint">支持 xlsx, xls 格式</div>
        </div>
        
        <button class="btn btn-primary">开始{title}</button>
        
        <div style="margin-top: 40px;">
            <h3 style="color: #333; margin-bottom: 20px; font-size: 20px;">功能特点</h3>
            <ul class="features-list">
                {features_html}
            </ul>
        </div>
    </div>
</body>
</html>
'''

# 写入用户页面
pages_to_write = [
    ('user_files.html', user_files_content),
    ('user_history.html', user_history_content),
    ('user_templates.html', user_templates_content),
    ('user_settings.html', user_settings_content),
]

for filename, content in pages_to_write:
    filepath = os.path.join(templates_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'已恢复 {filename}')

# 工具页面配置
tools = [
    ('ai.html', 'AI助手', '🤖', '智能AI帮您处理Excel数据', ['智能分析数据', '公式生成建议', '数据可视化建议', '自然语言操作']),
    ('tools.html', '工具中心', '🛠️', 'Excel工具集合', ['文件拆分', '数据清洗', '格式转换', '图表生成']),
    ('split.html', '文件拆分', '✂️', 'Excel文件智能拆分', ['按列值拆分', '按行数拆分', '按工作表拆分', '批量处理']),
    ('clean.html', '数据清洗', '🧹', '智能清洗Excel数据', ['去除空行', '删除重复值', '格式统一', '数据验证']),
    ('convert.html', '格式转换', '🔄', 'Excel格式相互转换', ['xlsx转xls', 'xls转xlsx', 'Excel转CSV', '批量转换']),
    ('beautify.html', '美化排版', '✨', '让您的表格美观专业', ['自动美化', '套用样式', '颜色搭配', '字体优化']),
    ('formulas.html', '公式大全', '🔢', 'Excel常用公式速查', ['财务公式', '统计公式', '文本公式', '日期公式']),
    ('statistics.html', '数据分析', '📊', '专业的数据统计分析', ['数据透视', '统计计算', '趋势分析', '报表生成']),
    ('charts.html', '图表生成', '📈', '一键生成专业图表', ['柱状图', '折线图', '饼图', '散点图']),
    ('batch.html', '批量处理', '📦', '一次性处理多个文件', ['批量拆分', '批量转换', '批量清洗', '批量美化']),
    ('templates.html', '模板中心', '📄', '精美Excel模板下载', ['财务报表', '人事管理', '销售数据', '项目管理']),
    ('tutorial.html', '教程中心', '📚', '学习Excel使用技巧', ['基础操作', '高级技巧', '公式教程', 'VBA入门']),
    ('dedup.html', '去重对比', '🔍', 'Excel数据去重对比', ['删除重复数据', '文件对比', '差异高亮', '批量去重']),
    ('login.html', '登录', '🔐', '登录您的账号', ['安全登录', '记住密码', '第三方登录', '快速注册']),
]

for filename, title, icon, description, features in tools:
    filepath = os.path.join(templates_dir, filename)
    content = generate_tool_page(title, icon, description, features)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'已恢复 {filename}')

print('\n所有页面恢复完成！🎉')
