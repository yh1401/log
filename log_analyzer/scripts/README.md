# 脚本说明

本目录包含日志分析系统的部署和启动脚本。

## 📁 文件列表

| 文件 | 说明 | 适用系统 |
|------|------|----------|
| `install.sh` | 自动安装脚本 | Linux / macOS |
| `install.bat` | 自动安装脚本 | Windows |
| `start.sh` | 启动服务脚本 | Linux / macOS |
| `start.bat` | 启动服务脚本 | Windows |
| `build.sh` | 打包脚本 | Linux / macOS |

## 🚀 使用方法

### 安装依赖

#### Linux / macOS
```bash
# 在项目根目录执行
./scripts/install.sh
```

#### Windows
```cmd
# 在项目根目录执行
scripts\install.bat
```

### 启动服务

#### Linux / macOS
```bash
# 在项目根目录执行
./scripts/start.sh
```

#### Windows
```cmd
# 在项目根目录执行
scripts\start.bat
```

### 打包项目

#### Linux / macOS
```bash
# 在项目根目录执行
./scripts/build.sh
```

打包完成后，会在 `dist/` 目录生成压缩包，可以发送给同事部署。

## 📋 脚本功能说明

### install.sh / install.bat
- 检查 Python 版本
- 创建虚拟环境
- 安装项目依赖
- 提供启动指引

### start.sh / start.bat
- 检查虚拟环境是否存在
- 激活虚拟环境
- 启动 Web 服务
- 显示访问地址

### build.sh
- 清理旧的打包文件
- 复制必要的项目文件
- 排除运行时生成的文件
- 创建跨平台压缩包
- 设置脚本执行权限

## ⚠️ 注意事项

1. **执行权限**: Linux/macOS 下需要先赋予脚本执行权限
   ```bash
   chmod +x scripts/*.sh
   ```

2. **Python 版本**: 需要 Python 3.8 或更高版本

3. **网络连接**: 安装依赖时需要网络连接

4. **端口占用**: 确保 8000 端口未被占用
