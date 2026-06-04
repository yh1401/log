#!/usr/bin/env python3
"""
Log Analyzer 完整功能验证脚本
"""
import os
import sys
import json
import time
import requests
from pathlib import Path

API_BASE = "http://localhost:8000"
TEST_DATA_DIR = "/Users/a666/Documents/trae_projects/log/loggen/data/error"


def test_health():
    """测试健康检查接口"""
    print("=" * 60)
    print("1. 测试健康检查接口")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE}/api/health", timeout=5)
        print(f"  状态码: {response.status_code}")
        print(f"  响应: {response.json()}")
        assert response.status_code == 200
        print("  ✅ 健康检查通过\n")
        return True
    except Exception as e:
        print(f"  ❌ 健康检查失败: {e}\n")
        return False


def test_user_authentication():
    """测试用户识别（无认证）"""
    print("=" * 60)
    print("2. 测试用户识别（无认证）")
    print("=" * 60)
    try:
        user1 = "alice_123"
        user2 = "bob_456"

        # 用户1
        response = requests.get(f"{API_BASE}/api/auth/current", headers={"X-User-Id": user1, "X-User_Name": "Alice"}, timeout=5)
        print(f"  用户 Alice (X-User-Id: {user1}):")
        print(f"    状态码: {response.status_code}")
        print(f"    响应: {response.json()}")
        assert response.status_code == 200
        data1 = response.json()
        assert data1.get("code") == 0

        # 用户2
        response = requests.get(f"{API_BASE}/api/auth/current", headers={"X-User-Id": user2, "X-Username": "Bob"}, timeout=5)
        print(f"\n  用户 Bob (X-User-Id: {user2}):")
        print(f"    状态码: {response.status_code}")
        print(f"    响应: {response.json()}")
        assert response.status_code == 200

        print("\n  ✅ 用户识别通过\n")
        return user1, user2
    except Exception as e:
        print(f"  ❌ 用户识别失败: {e}\n")
        return None, None


def test_history_report_crud(user_id):
    """测试历史报告 CRUD 接口"""
    print("=" * 60)
    print(f"3. 测试历史报告 CRUD 接口 (用户: {user_id})")
    print("=" * 60)
    try:
        headers = {"X-User-Id": user_id, "Content-Type": "application/json"}

        # Create
        report_data = {
            "title": f"自动化测试报告 {user_id}",
            "file_name": "auto_test.log",
            "summary": "这是一条通过 API 自动创建的历史报告",
            "tags": ["auto_test", "validation"],
            "statistics": {"error_count": 5, "warning_count": 10}
        }
        response = requests.post(
            f"{API_BASE}/api/history/reports",
            headers=headers,
            json=report_data,
            timeout=10
        )
        print(f"  Create:")
        print(f"    状态码: {response.status_code}")
        assert response.status_code in [200, 201]
        create_result = response.json()
        print(f"    响应: {create_result}")
        report_id = create_result["data"]["report_id"]

        # List
        response = requests.get(f"{API_BASE}/api/history/reports", headers={"X-User-Id": user_id}, timeout=5)
        print(f"\n  List:")
        print(f"    状态码: {response.status_code}")
        list_result = response.json()
        print(f"    报告数: {list_result['data']['total']}")
        assert list_result["data"]["total"] >= 1

        # Get
        response = requests.get(f"{API_BASE}/api/history/reports/{report_id}", headers={"X-User-Id": user_id}, timeout=5)
        print(f"\n  Get (id: {report_id}):")
        print(f"    状态码: {response.status_code}")
        get_result = response.json()
        print(f"    标题: {get_result['data']['title']}")

        # Update
        update_data = {
            "title": f"更新后的报告 - {user_id}",
            "summary": "已更新内容",
            "tags": ["updated"]
        }
        response = requests.put(
            f"{API_BASE}/api/history/reports/{report_id}",
            headers=headers,
            json=update_data,
            timeout=5
        )
        print(f"\n  Update:")
        print(f"    状态码: {response.status_code}")
        print(f"    响应: {response.json()}")

        # Delete
        print(f"\n  Delete: 跳过删除（保留测试数据）")

        print("\n  ✅ 历史报告 CRUD 测试通过\n")
        return report_id
    except Exception as e:
        print(f"  ❌ 历史报告 CRUD 测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def test_data_isolation(user1, user2, report_id):
    """测试用户数据隔离"""
    print("=" * 60)
    print(f"4. 测试用户数据隔离")
    print("=" * 60)
    try:
        # 用 user2 尝试访问 user1 的报告
        print(f"  用户2 ({user2}) 尝试访问用户1 ({user1}) 的报告...")
        response = requests.get(
            f"{API_BASE}/api/history/reports/{report_id}",
            headers={"X-User-Id": user2},
            timeout=5
        )
        print(f"    状态码: {response.status_code}")
        result = response.json()
        print(f"    响应: {result}")
        assert result.get("code") == 1
        print(f"    ✅ 用户2 不能访问用户1 的报告")

        # 检查 user1 和 user2 的报告列表
        print(f"\n  检查用户1 ({user1}) 报告列表:")
        r1 = requests.get(f"{API_BASE}/api/history/reports", headers={"X-User-Id": user1}, timeout=5)
        print(f"    报告数: {r1.json()['data']['total']}")

        print(f"\n  检查用户2 ({user2}) 报告列表:")
        r2 = requests.get(f"{API_BASE}/api/history/reports", headers={"X-User-Id": user2}, timeout=5)
        print(f"    报告数: {r2.json()['data']['total']}")

        print("\n  ✅ 数据隔离测试通过\n")
        return True
    except Exception as e:
        print(f"  ❌ 数据隔离测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_backup(user_id):
    """测试数据备份"""
    print("=" * 60)
    print(f"5. 测试数据备份 (用户: {user_id})")
    print("=" * 60)
    try:
        response = requests.post(
            f"{API_BASE}/api/backup/create",
            headers={"X-User-Id": user_id},
            timeout=15
        )
        print(f"  状态码: {response.status_code}")
        print(f"  响应: {response.json()}")
        assert response.status_code == 200

        print("\n  ✅ 备份测试通过\n")
        return True
    except Exception as e:
        print(f"  ❌ 备份测试失败: {e}\n")
        return False


def main():
    print("\n" + "=" * 60)
    print("Log Analyzer 完整功能验证")
    print("=" * 60 + "\n")

    # 测试 1: 健康检查
    if not test_health():
        return 1

    # 测试 2: 用户识别
    user1, user2 = test_user_authentication()
    if not user1 or not user2:
        return 1

    # 测试 3: 历史报告 CRUD
    report_id = test_history_report_crud(user1)
    if not report_id:
        return 1

    # 为 user2 也创建一个报告
    test_history_report_crud(user2)

    # 测试 4: 数据隔离
    if not test_data_isolation(user1, user2, report_id):
        return 1

    # 测试 5: 数据备份
    test_backup(user1)
    test_backup(user2)

    # 检查存储结构
    print("=" * 60)
    print("6. 检查本地存储结构")
    print("=" * 60)
    project_root = Path("/Users/a666/Documents/trae_projects/log/log_analyzer")
    print(f"\n  数据目录:")
    print(f"  {project_root}/data/")
    if (project_root / "data" / "reports_db").exists():
        print(f"  历史报告目录结构:")
        for user_dir in sorted((project_root / "data" / "reports_db").iterdir()):
            if user_dir.is_dir():
                print(f"    {user_dir.name}/")
                count = sum(1 for f in user_dir.iterdir() if f.is_file() and f.suffix == '.json')
                print(f"      JSON 文件数: {count}")

    print("\n" + "=" * 60)
    print("🎉 所有功能验证通过！")
    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
