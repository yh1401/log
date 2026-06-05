# 日志分析系统 - 快速部署指南

## 📦 压缩包内容

本压缩包已包含所有必要的代码和配置文件，支持跨平台部署（Linux / macOS / Windows）。

## 🚀 快速部署步骤

### Linux / macOS

```bash
# 1. 解压压缩包
unzip log_analyzer_v1.0.0_*.zip
cd log_analyzer

# 2. 运行安装脚本（自动创建虚拟环境并安装依赖）
chmod +x scripts/*.sh
./scripts/install.sh

# 3. 启动服务
./scripts/start.sh
```

### Windows

```cmd
# 1. 解压压缩包（右键 -> 解压到当前文件夹）
# 进入 log_analyzer 目录

# 2. 运行安装脚本
scripts\install.bat

# 3. 启动服务
scripts\start.bat
```

## 📡 访问服务

服务启动后，打开浏览器访问：

```
http://localhost:8000
```

局域网内其他用户访问：

```
http://<服务器IP>:8000
```

## 🔧 手动部署（可选）

如果自动脚本失败，可以手动执行以下命令：

### Linux / macOS

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
cd web
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Windows

```cmd
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
cd web
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📁 目录结构

```
log_analyzer/
├── scripts/              # 部署脚本目录
│   ├── install.sh       # Linux/macOS 安装脚本
│   ├── install.bat      # Windows 安装脚本
│   ├── start.sh         # Linux/macOS 启动脚本
│   ├── start.bat        # Windows 启动脚本
│   ├── build.sh         # 打包脚本
│   └── README.md        # 脚本说明文档
├── web/                  # Web 服务代码
│   ├── app.py           # 主应用
│   └── static/          # 静态文件
├── docs/                 # 文档目录
├── config/               # 配置文件
├── requirements.txt      # Python 依赖
└── README.md            # 项目说明
```

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Linux / macOS / Windows
- **内存**: 建议 4GB 以上
- **磁盘空间**: 至少 500MB 可用空间

## 🌟 功能列表

- ✅ 日志文件上传分析
- ✅ ZIP 文件自动解压
- ✅ 服务器路径读取
- ✅ HTML 报告在线预览
- ✅ Markdown 报告查看
- ✅ 任务进度实时显示
- ✅ 任务终止功能
- ✅ 历史报告管理
- ✅ 用户数据隔离

## ⚠️ 注意事项

1. **端口占用**: 确保 8000 端口未被占用
2. **防火墙**: 如需外网访问，请开放 8000 端口
3. **权限**: Linux/macOS 下可能需要 `chmod +x scripts/*.sh` 赋予执行权限
4. **Python版本**: 确保系统已安装 Python 3.8+

## 📞 技术支持

如遇到问题，请检查：
1. Python 版本是否正确
2. 虚拟环境是否成功创建
3. 依赖是否完整安装
4. 端口是否被占用

## 📝 更新日志

- 2026-06-05: 优化项目结构，添加 scripts 目录
- 2026-06-05: 创建跨平台打包脚本
- 2026-06-05: 添加 HTML 报告预览功能
- 2026-06-05: 添加任务终止功能
- 2026-06-05: 优化并发性能
