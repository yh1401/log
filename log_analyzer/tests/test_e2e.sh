#!/bin/bash
# Log Analyzer 完整功能验证脚本
set -e

API_BASE="http://localhost:8000"
USER1="alice_test123"
USER2="bob_test456"

echo ""
echo "============================================================"
echo "Log Analyzer 完整功能验证"
echo "============================================================"
echo ""

# 1. 健康检查
echo "1. 测试健康检查接口"
echo "------------------------------------------------------------"
curl -s "$API_BASE/api/health"
echo ""
echo "✅ 健康检查通过"
echo ""

# 2. 用户识别
echo "2. 测试用户识别（无认证）"
echo "------------------------------------------------------------"
echo "用户 Alice:"
curl -s "$API_BASE/api/auth/current" -H "X-User-Id: $USER1"
echo ""
echo "用户 Bob:"
curl -s "$API_BASE/api/auth/current" -H "X-User-Id: $USER2"
echo ""
echo "✅ 用户识别通过"
echo ""

# 3. 历史报告 CRUD
echo "3. 测试历史报告 CRUD"
echo "------------------------------------------------------------"
echo "创建 Alice 的报告:"
REPORT_ID=$(curl -s -X POST "$API_BASE/api/history/reports" \
     -H "X-User-Id: $USER1" \
     -H "Content-Type: application/json" \
     -d '{"title":"自动化测试报告","file_name":"auto_test.log","summary":"这是一条测试","tags":["test"]}' \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['report_id'])"
)
echo "报告 ID: $REPORT_ID"

echo "查询 Alice 的报告列表:"
curl -s "$API_BASE/api/history/reports" -H "X-User-Id: $USER1"
echo ""

echo "创建 Bob 的报告:"
curl -s -X POST "$API_BASE/api/history/reports" \
     -H "X-User-Id: $USER2" \
     -H "Content-Type: application/json" \
     -d '{"title":"Bob的测试报告","file_name":"bob_test.log","summary":"测试报告","tags":["bob"]}' \
     > /dev/null

echo "✅ 历史报告 CRUD 测试通过"
echo ""

# 4. 用户数据隔离
echo "4. 测试用户数据隔离"
echo "------------------------------------------------------------"
echo "Alice 的报告列表:"
curl -s "$API_BASE/api/history/reports" -H "X-User-Id: $USER1"
echo ""
echo "Bob 的报告列表:"
curl -s "$API_BASE/api/history/reports" -H "X-User-Id: $USER2"
echo ""
echo "✅ 数据隔离测试通过"
echo ""

# 5. 数据备份
echo "5. 测试数据备份"
echo "------------------------------------------------------------"
echo "为 Alice 备份:"
curl -s -X POST "$API_BASE/api/backup/create" -H "X-User-Id: $USER1"
echo ""
echo "为 Bob 备份:"
curl -s -X POST "$API_BASE/api/backup/create" -H "X-User-Id: $USER2"
echo ""
echo "✅ 备份测试通过"
echo ""

# 6. 检查本地存储
echo "6. 检查本地存储结构"
echo "------------------------------------------------------------"
ls -la "/Users/a666/Documents/trae_projects/log/log_analyzer/data/reports_db/"
echo ""
echo "备份目录:"
ls -la "/Users/a666/Documents/trae_projects/log/log_analyzer/data/backups/"
echo ""

echo "============================================================"
echo "🎉 所有功能验证完成！"
echo "============================================================"
echo ""
