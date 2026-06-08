import os

templates_dir = os.path.join(os.path.dirname(__file__), "templates")

# 完整的用户文件管理页面 - 包含实际的上传、删除、下载功能
user_files_complete = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的文件 - 序光</title>
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
            background: transparent;
            border: none;
        }
        
        .menu-item.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .menu-item:hover:not(.active) {
            background: #f5f5f5;
        }
        
        .upload-area {
            border: 2px dashed #e5e7eb;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 30px;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.05);
        }
        
        .upload-area.dragover {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.1);
        }
        
        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        .upload-text {
            color: #666;
            font-size: 16px;
            margin-bottom: 10px;
        }
        
        .upload-hint {
            font-size: 14px;
            color: #999;
        }
        
        .file-list {
            max-height: 500px;
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
            flex: 1;
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
        
        .file-details {
            flex: 1;
        }
        
        .file-name {
            color: #333;
            font-size: 16px;
            font-weight: 500;
            margin-bottom: 5px;
        }
        
        .file-meta {
            color: #999;
            font-size: 13px;
            display: flex;
            gap: 15px;
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
        
        .action-btn.use {
            background: #10b981;
            color: white;
        }
        
        .action-btn.use:hover {
            background: #059669;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
        }
        
        .empty-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        
        .empty-text {
            font-size: 18px;
            color: #666;
            margin-bottom: 10px;
        }
        
        .empty-hint {
            font-size: 14px;
            color: #999;
        }
        
        .stats-bar {
            display: flex;
            gap: 30px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 12px;
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stat-icon {
            font-size: 24px;
        }
        
        .stat-info {
            display: flex;
            flex-direction: column;
        }
        
        .stat-number {
            font-size: 20px;
            font-weight: 700;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 12px;
            color: #999;
        }
        
        #fileInput {
            display: none;
        }
        
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            display: none;
            z-index: 1000;
        }
        
        .toast.show {
            display: block;
        }
        
        .toast.success {
            border-left: 4px solid #10b981;
        }
        
        .toast.error {
            border-left: 4px solid #ef4444;
        }
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
        <h1>📁 我的文件</h1>
        <p>管理您上传和保存的Excel文件</p>
    </div>

    <div class="main-content">
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-icon">📊</span>
                <div class="stat-info">
                    <span class="stat-number" id="totalFiles">0</span>
                    <span class="stat-label">总文件数</span>
                </div>
            </div>
            <div class="stat-item">
                <span class="stat-icon">💾</span>
                <div class="stat-info">
                    <span class="stat-number" id="totalSize">0 MB</span>
                    <span class="stat-label">总大小</span>
                </div>
            </div>
            <div class="stat-item">
                <span class="stat-icon">📅</span>
                <div class="stat-info">
                    <span class="stat-number" id="lastUpload">-</span>
                    <span class="stat-label">最后上传</span>
                </div>
            </div>
        </div>

        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📤</div>
            <div class="upload-text">点击或拖拽文件上传</div>
            <div class="upload-hint">支持 xlsx, xls, xlsm 格式，最大500MB</div>
            <input type="file" id="fileInput" accept=".xlsx,.xls,.xlsm" multiple>
        </div>

        <div class="file-list" id="fileList"></div>
        
        <div class="empty-state" id="emptyState" style="display: none;">
            <div class="empty-icon">📂</div>
            <div class="empty-text">暂无文件</div>
            <div class="empty-hint">快来上传您的第一个文件吧！</div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        // 加载文件列表
        async function loadFiles() {
            try {
                const response = await fetch('/api/user/files');
                const result = await response.json();
                
                if (result.success) {
                    displayFiles(result.files);
                    updateStats(result.stats);
                }
            } catch (error) {
                console.error('加载文件失败:', error);
                showToast('加载文件失败', 'error');
            }
        }
        
        function displayFiles(files) {
            const fileList = document.getElementById('fileList');
            const emptyState = document.getElementById('emptyState');
            
            if (files.length === 0) {
                fileList.innerHTML = '';
                emptyState.style.display = 'block';
                return;
            }
            
            emptyState.style.display = 'none';
            fileList.innerHTML = files.map(file => `
                <div class="file-item" data-id="${file.id}">
                    <div class="file-info">
                        <div class="file-icon">📊</div>
                        <div class="file-details">
                            <div class="file-name">${file.name}</div>
                            <div class="file-meta">
                                <span>${formatFileSize(file.size)}</span>
                                <span>上传于${file.uploadTime}</span>
                            </div>
                        </div>
                    </div>
                    <div class="file-actions">
                        <button class="action-btn use" onclick="useFile('${file.id}')">使用</button>
                        <button class="action-btn download" onclick="downloadFile('${file.id}')">下载</button>
                        <button class="action-btn delete" onclick="deleteFile('${file.id}')">删除</button>
                    </div>
                </div>
            `).join('');
        }
        
        function updateStats(stats) {
            document.getElementById('totalFiles').textContent = stats.totalFiles;
            document.getElementById('totalSize').textContent = formatFileSize(stats.totalSize);
            document.getElementById('lastUpload').textContent = stats.lastUpload || '-';
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        // 上传文件
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                uploadFiles(files);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                uploadFiles(e.target.files);
            }
        });
        
        async function uploadFiles(files) {
            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        showToast(`文件 ${file.name} 上传成功`, 'success');
                    } else {
                        showToast(result.error, 'error');
                    }
                } catch (error) {
                    showToast(`文件 ${file.name} 上传失败`, 'error');
                }
            }
            
            setTimeout(() => loadFiles(), 1000);
        }
        
        async function downloadFile(fileId) {
            window.location.href = `/api/download/${fileId}`;
        }
        
        async function deleteFile(fileId) {
            if (!confirm('确定要删除这个文件吗？')) return;
            
            try {
                const response = await fetch(`/api/user/files/${fileId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                if (result.success) {
                    showToast('文件删除成功', 'success');
                    loadFiles();
                } else {
                    showToast(result.error, 'error');
                }
            } catch (error) {
                showToast('删除失败', 'error');
            }
        }
        
        function useFile(fileId) {
            window.location.href = `/split?file=${fileId}`;
        }
        
        function showToast(message, type) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = `toast show ${type}`;
            
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }
        
        // 初始化
        loadFiles();
    </script>
</body>
</html>
'''

# 完整的处理记录页面
user_history_complete = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>处理记录 - 序光</title>
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
        
        .filter-bar {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .filter-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            background: #f5f5f5;
            color: #666;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .filter-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .filter-btn:hover:not(.active) {
            background: #e5e5e5;
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
            margin-bottom: 8px;
        }
        
        .history-files {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .file-tag {
            padding: 4px 12px;
            background: #f0f0f0;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
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
        
        .action-btn.delete {
            background: #ef4444;
        }
        
        .action-btn.delete:hover {
            background: #dc2626;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
        }
        
        .empty-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        
        .empty-text {
            font-size: 18px;
            color: #666;
            margin-bottom: 10px;
        }
        
        .empty-hint {
            font-size: 14px;
            color: #999;
        }
        
        .stats-bar {
            display: flex;
            gap: 30px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 12px;
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stat-icon {
            font-size: 24px;
        }
        
        .stat-info {
            display: flex;
            flex-direction: column;
        }
        
        .stat-number {
            font-size: 20px;
            font-weight: 700;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 12px;
            color: #999;
        }
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
        <h1>📋 处理记录</h1>
        <p>查看您的Excel文件处理历史</p>
    </div>

    <div class="main-content">
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-icon">📊</span>
                <div class="stat-info">
                    <span class="stat-number" id="totalOperations">0</span>
                    <span class="stat-label">总处理数</span>
                </div>
            </div>
            <div class="stat-item">
                <span class="stat-icon">✅</span>
                <div class="stat-info">
                    <span class="stat-number" id="successCount">0</span>
                    <span class="stat-label">成功</span>
                </div>
            </div>
            <div class="stat-item">
                <span class="stat-icon">❌</span>
                <div class="stat-info">
                    <span class="stat-number" id="failedCount">0</span>
                    <span class="stat-label">失败</span>
                </div>
            </div>
        </div>

        <div class="filter-bar">
            <button class="filter-btn active" data-filter="all">全部</button>
            <button class="filter-btn" data-filter="success">成功</button>
            <button class="filter-btn" data-filter="failed">失败</button>
            <button class="filter-btn" data-filter="pending">进行中</button>
        </div>

        <div class="history-list" id="historyList"></div>
        
        <div class="empty-state" id="emptyState" style="display: none;">
            <div class="empty-icon">📝</div>
            <div class="empty-text">暂无处理记录</div>
            <div class="empty-hint">快来体验我们的功能吧！</div>
        </div>
    </div>

    <script>
        // 加载处理记录
        async function loadHistory() {
            try {
                const response = await fetch('/api/user/history');
                const result = await response.json();
                
                if (result.success) {
                    displayHistory(result.records);
                    updateStats(result.stats);
                }
            } catch (error) {
                console.error('加载历史失败:', error);
            }
        }
        
        function displayHistory(records) {
            const historyList = document.getElementById('historyList');
            const emptyState = document.getElementById('emptyState');
            
            if (records.length === 0) {
                historyList.innerHTML = '';
                emptyState.style.display = 'block';
                return;
            }
            
            emptyState.style.display = 'none';
            historyList.innerHTML = records.map(record => `
                <div class="history-item" data-status="${record.status}">
                    <div class="history-info">
                        <h4>${record.operationType} - ${record.fileName}</h4>
                        <div class="history-details">
                            <span>处理时间: ${record.time}</span>
                            <span>处理行数: ${record.rowsProcessed}</span>
                            <span>生成文件: ${record.filesCount}</span>
                        </div>
                        <div class="history-files">
                            ${record.files.map(f => `<span class="file-tag">${f}</span>`).join('')}
                        </div>
                    </div>
                    <div class="history-status">
                        <span class="status-badge ${record.status}">${getStatusText(record.status)}</span>
                        <button class="action-btn" onclick="viewResult('${record.id}')">查看结果</button>
                        <button class="action-btn delete" onclick="deleteRecord('${record.id}')">删除</button>
                    </div>
                </div>
            `).join('');
        }
        
        function getStatusText(status) {
            const texts = {
                success: '成功',
                pending: '进行中',
                failed: '失败'
            };
            return texts[status] || status;
        }
        
        function updateStats(stats) {
            document.getElementById('totalOperations').textContent = stats.total;
            document.getElementById('successCount').textContent = stats.success;
            document.getElementById('failedCount').textContent = stats.failed;
        }
        
        // 筛选功能
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const filter = btn.dataset.filter;
                const items = document.querySelectorAll('.history-item');
                
                items.forEach(item => {
                    if (filter === 'all' || item.dataset.status === filter) {
                        item.style.display = 'flex';
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
        });
        
        function viewResult(recordId) {
            window.location.href = `/user/history/${recordId}`;
        }
        
        async function deleteRecord(recordId) {
            if (!confirm('确定要删除这条记录吗？')) return;
            
            try {
                const response = await fetch(`/api/user/history/${recordId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                if (result.success) {
                    loadHistory();
                }
            } catch (error) {
                console.error('删除失败:', error);
            }
        }
        
        // 初始化
        loadHistory();
    </script>
</body>
</html>
'''

# 完整的会员中心页面
user_member_complete = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>会员中心 - 序光</title>
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
        
        .user-profile {
            display: flex;
            align-items: center;
            gap: 30px;
            margin-bottom: 30px;
            padding-bottom: 30px;
            border-bottom: 2px solid #e5e7eb;
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
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .avatar:hover {
            transform: scale(1.05);
        }
        
        .user-info {
            flex: 1;
        }
        
        .user-info h2 {
            font-size: 24px;
            color: #333;
            margin-bottom: 8px;
        }
        
        .user-info .email {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        .membership-badge {
            display: inline-block;
            padding: 6px 16px;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            color: white;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .membership-badge.free {
            background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
        }
        
        .membership-badge.premium {
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        }
        
        .membership-badge.enterprise {
            background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
        }
        
        .user-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            text-align: center;
            padding: 20px;
            background: #f8fafc;
            border-radius: 12px;
        }
        
        .stat-number {
            font-size: 32px;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 14px;
            color: #666;
        }
        
        .current-plan {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 30px;
            color: white;
            margin-bottom: 30px;
        }
        
        .current-plan h3 {
            font-size: 20px;
            margin-bottom: 15px;
        }
        
        .current-plan .price {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .current-plan .period {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        
        .current-plan .expiry {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .benefits {
            margin-bottom: 30px;
        }
        
        .benefits h3 {
            font-size: 20px;
            color: #333;
            margin-bottom: 20px;
        }
        
        .benefit-list {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .benefit-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            background: #f8fafc;
            border-radius: 8px;
        }
        
        .benefit-item .icon {
            color: #10b981;
            font-size: 20px;
        }
        
        .benefit-item span {
            color: #333;
            font-size: 14px;
        }
        
        .benefit-item.disabled span {
            color: #999;
            text-decoration: line-through;
        }
        
        .benefit-item.disabled .icon {
            color: #999;
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
        
        .btn-outline {
            background: transparent;
            border: 2px solid #667eea;
            color: #667eea;
        }
        
        .btn-outline:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        
        .upgrade-options {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-top: 30px;
        }
        
        .upgrade-card {
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .upgrade-card:hover {
            border-color: #667eea;
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .upgrade-card.featured {
            border-color: #667eea;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
        }
        
        .upgrade-card h4 {
            font-size: 18px;
            color: #333;
            margin-bottom: 15px;
        }
        
        .upgrade-card .price {
            font-size: 32px;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .upgrade-card .price span {
            font-size: 14px;
            color: #999;
            font-weight: normal;
        }
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
        <h1>⭐ 会员中心</h1>
        <p>管理您的会员权益和账户信息</p>
    </div>

    <div class="main-content">
        <div class="user-profile">
            <div class="avatar" onclick="changeAvatar()">👤</div>
            <div class="user-info">
                <h2 id="username">Excel用户</h2>
                <div class="email" id="useremail">user@example.com</div>
                <span class="membership-badge premium" id="membershipBadge">高级会员</span>
            </div>
        </div>

        <div class="user-stats">
            <div class="stat-card">
                <div class="stat-number" id="totalFiles">0</div>
                <div class="stat-label">处理文件</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalSize">0</div>
                <div class="stat-label">存储使用</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="savedTemplates">0</div>
                <div class="stat-label">收藏模板</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="memberDays">0</div>
                <div class="stat-label">使用天数</div>
            </div>
        </div>

        <div class="current-plan">
            <h3>当前套餐</h3>
            <div class="price" id="currentPrice">¥29/月</div>
            <div class="period" id="currentPeriod">高级版</div>
            <div class="expiry" id="currentExpiry">有效期至: 2026年7月15日</div>
        </div>

        <div class="benefits">
            <h3>会员权益</h3>
            <div class="benefit-list">
                <div class="benefit-item">
                    <span class="icon">✓</span>
                    <span>无限文件拆分</span>
                </div>
                <div class="benefit-item">
                    <span class="icon">✓</span>
                    <span>AI智能助手</span>
                </div>
                <div class="benefit-item">
                    <span class="icon">✓</span>
                    <span>批量处理功能</span>
                </div>
                <div class="benefit-item">
                    <span class="icon">✓</span>
                    <span>高级数据清洗</span>
                </div>
                <div class="benefit-item">
                    <span class="icon">✓</span>
                    <span>专属模板库</span>
                </div>
                <div class="benefit-item">
                    <span class="icon">✓</span>
                    <span>优先技术支持</span>
                </div>
            </div>
        </div>

        <div style="display: flex; gap: 15px;">
            <button class="btn btn-primary" onclick="window.location.href='/pricing'">升级套餐</button>
            <button class="btn btn-outline" onclick="window.location.href='/user/settings'">账户设置</button>
        </div>
        
        <div class="upgrade-options">
            <div class="upgrade-card" onclick="upgradePlan('free')">
                <h4>免费版</h4>
                <div class="price">¥0 <span>/月</span></div>
                <p style="color: #666; font-size: 14px;">基础功能</p>
            </div>
            <div class="upgrade-card featured" onclick="upgradePlan('premium')">
                <h4>高级版</h4>
                <div class="price">¥29 <span>/月</span></div>
                <p style="color: #666; font-size: 14px;">推荐选择</p>
            </div>
            <div class="upgrade-card" onclick="upgradePlan('enterprise')">
                <h4>企业版</h4>
                <div class="price">¥99 <span>/月</span></div>
                <p style="color: #666; font-size: 14px;">无限使用</p>
            </div>
        </div>
    </div>

    <script>
        // 加载用户信息
        async function loadUserInfo() {
            try {
                const response = await fetch('/api/user/info');
                const result = await response.json();
                
                if (result.success) {
                    updateUserInfo(result.user);
                    updateStats(result.stats);
                    updatePlan(result.plan);
                }
            } catch (error) {
                console.error('加载用户信息失败:', error);
            }
        }
        
        function updateUserInfo(user) {
            document.getElementById('username').textContent = user.name;
            document.getElementById('useremail').textContent = user.email;
            
            const badge = document.getElementById('membershipBadge');
            badge.textContent = getMembershipText(user.level);
            badge.className = `membership-badge ${user.level}`;
        }
        
        function updateStats(stats) {
            document.getElementById('totalFiles').textContent = stats.totalFiles;
            document.getElementById('totalSize').textContent = stats.totalSize;
            document.getElementById('savedTemplates').textContent = stats.savedTemplates;
            document.getElementById('memberDays').textContent = stats.memberDays;
        }
        
        function updatePlan(plan) {
            document.getElementById('currentPrice').textContent = plan.price;
            document.getElementById('currentPeriod').textContent = plan.name;
            document.getElementById('currentExpiry').textContent = `有效期至: ${plan.expiry}`;
        }
        
        function getMembershipText(level) {
            const texts = {
                free: '免费用户',
                premium: '高级会员',
                enterprise: '企业会员'
            };
            return texts[level] || level;
        }
        
        function changeAvatar() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.onchange = (e) => {
                // TODO: 实现头像上传
                alert('头像上传功能开发中...');
            };
            input.click();
        }
        
        function upgradePlan(plan) {
            window.location.href = `/pricing?plan=${plan}`;
        }
        
        // 初始化
        loadUserInfo();
    </script>
</body>
</html>
'''

# 写入完整的用户页面
files_to_write = [
    ('user_files.html', user_files_complete),
    ('user_history.html', user_history_complete),
    ('user_member.html', user_member_complete),
]

for filename, content in files_to_write:
    filepath = os.path.join(templates_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'已恢复完整功能: {filename}')

print('\n所有用户页面已恢复完整功能！')
