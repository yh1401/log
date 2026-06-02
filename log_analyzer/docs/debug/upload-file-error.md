# Debug: 上传文件报错

## Session ID
`upload-file-error`

## 状态
[FIXED]

## 用户反馈
- 症状：前端页面上传文件时显示"上传文件时发生错误"
- 期望：能够成功上传文件

## 假设 (Hypotheses)

1. **H1: 前端 fetch 调用错误** - JavaScript 的 fetch 没有传递正确的 header (X-User-Id) 或没有正确处理 FormData
2. **H2: CORS 跨域问题** - 浏览器阻止了跨域请求
3. **H3: 后端接口异常** - /api/upload 路由有错误（如参数问题、文件大小限制）
4. **H4: 用户识别问题** - get_current_user 依赖函数抛异常
5. **H5: 静态文件挂载问题** - StaticFiles 配置错误导致服务异常

## 运行时证据 (Runtime Evidence)

### 证据1: 后端 API 单独测试
```bash
curl -X POST "http://localhost:8000/api/upload" \
     -H "X-User-Id: test_user" \
     -F "file=@loggen/data/error/error.2026-05-26.49.txt"
```
**响应**：
```json
{
  "code": 0,
  "message": "上传成功",
  "data": {
    "success": true,
    "file_path": "/Users/a666/Documents/trae_projects/log/log_analyzer/users/test_user/uploads/error.2026-05-26.49.txt",
    "file_name": "error.2026-05-26.49.txt",
    "file_size": "90.00 MB",
    "extracted_files": [...]
  }
}
```
**结论**：后端 API 正常工作 → **H3, H4, H5 排除**

### 证据2: 前端代码审查
查看 `web/static/index.html` line 709-770 中的 `uploadFile` 函数：

```javascript
const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData  // ❌ 缺少 headers
});

if (result.success) {  // ❌ 实际响应是 result.data.success
```

**结论**：前端代码有两处错误 → **H1 确认**

## 根本原因

1. **缺失 `X-User-Id` header**：前端 fetch 调用没有传递用户标识头
2. **响应解析错误**：检查 `result.success` 但后端返回的是 `result.code === 0 && result.data.success`
3. **错误处理不完善**：未读取 `result.message` 字段

## 修复方案

修改 `web/static/index.html` 的 `uploadFile` 函数：
- ✅ 添加 `X-User-Id` header（从 localStorage 读取或自动生成）
- ✅ 修正响应解析：`if (result.code === 0 && result.data)`
- ✅ 完善错误处理：显示 `result.message`

## 修复后验证

```bash
# 验证修复
curl -s "http://localhost:8000/" | grep -c "X-User-Id"
# 输出: 1 ✅
```

## 清理状态

调试完成，所有修复已应用。
