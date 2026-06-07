# Xuguang-NexaOffice

序办是一个基于 Flask 的 AI 表格协作与办公工具平台原型，包含表格处理、模板中心、资源中心、知识库、云盘、工作台等页面与基础文件处理能力。

## 功能概览

- 表格拆分、合并、去重、清洗、格式转换、图表报表、批量处理
- AI 办公助手入口与手动处理入口
- 模板中心、自定义模板上传与管理
- 云盘、知识库、工作台、账号设置等 SaaS 平台型页面
- Flask 后端接口与 Excel 文件处理逻辑

## 本地启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

启动后访问：

```text
http://localhost:5000
```

## 目录说明

- `app.py`：Flask Web 服务与页面路由
- `excel_splitter.py`：表格拆分与处理逻辑
- `templates/`：前端页面模板
- `test_data/`：本地测试用示例文件
- `uploads/`、`output/`、`outputs/`：运行时上传文件和处理结果，已在 `.gitignore` 中排除

## 注意

当前项目处于产品原型阶段，部分登录、账号、模板、知识库和云盘能力为前端交互与本地演示逻辑，后续可继续接入数据库、真实账号系统、对象存储和权限体系。
