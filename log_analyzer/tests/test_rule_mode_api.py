#!/usr/bin/env python3
"""
测试规则模式 API 功能
"""

import requests
import json
import time
import sys
from pathlib import Path

# API 基础 URL
API_BASE = "http://localhost:8000"

# 用户信息
USER_ID = "test_user_rule_mode"
USERNAME = "规则模式测试用户"

# 请求头
HEADERS = {
    "Content-Type": "application/json",
    "X-User-Id": USER_ID,
    "X-User_Name": USERNAME
}

def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health_check():
    """测试健康检查"""
    print_section("测试 1: 健康检查")

    try:
        response = requests.get(f"{API_BASE}/api/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        if response.status_code == 200:
            print("✓ 健康检查通过")
            return True
        else:
            print("✗ 健康检查失败")
            return False
    except Exception as e:
        print(f"✗ 健康检查异常: {e}")
        return False

def test_process_with_llm():
    """测试 LLM 模式处理"""
    print_section("测试 2: LLM 模式处理")

    # 创建测试日志文件
    test_log = Path("/tmp/test_llm_mode.log")
    test_log.write_text("""2026-06-03 10:00:00 [ERROR] [main] NullPointerException: Cannot invoke method on null object
2026-06-03 10:00:01 [ERROR] [worker] TimeoutException: Connection timeout after 30000ms
2026-06-03 10:00:02 [ERROR] [main] NullPointerException: Cannot invoke toString() on null object
2026-06-03 10:00:03 [FATAL] [main] OutOfMemoryError: Java heap space
""")

    try:
        # 上传文件
        print("1. 上传测试文件...")
        upload_data = {
            'file': ('test_llm_mode.log', open(test_log, 'rb'), 'text/plain')
        }
        upload_response = requests.post(f"{API_BASE}/api/upload", files=upload_data, headers={
            "X-User-Id": USER_ID,
            "X-User_Name": USERNAME
        })
        print(f"上传响应: {upload_response.json()}")

        if upload_response.status_code != 200:
            print("✗ 文件上传失败")
            return False

        file_path = upload_response.json()['data']['file_path']
        print(f"文件路径: {file_path}")

        # 使用 LLM 模式处理
        print("\n2. 使用 LLM 模式处理...")
        process_data = {
            "file_path": file_path,
            "chunk_size": 100,
            "force_restart": True,
            "use_llm": True  # LLM 模式
        }

        process_response = requests.post(f"{API_BASE}/api/process", json=process_data, headers=HEADERS)
        print(f"处理响应: {process_response.json()}")

        if process_response.status_code != 200:
            print("✗ LLM 模式处理失败")
            return False

        task_id = process_response.json()['data']['task_id']
        print(f"任务 ID: {task_id}")

        # 轮询任务状态
        print("\n3. 轮询任务状态...")
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)
            task_response = requests.get(f"{API_BASE}/api/task/{task_id}", headers=HEADERS)
            task_data = task_response.json()['data']
            status = task_data['status']
            progress = task_data.get('progress', 0)
            message = task_data.get('message', '')

            print(f"  尝试 {attempt + 1}/{max_attempts}: 状态={status}, 进度={progress}%, 消息={message}")

            if status == 'completed':
                print("✓ LLM 模式处理完成")
                print(f"报告数量: {len(task_data.get('reports', []))}")
                return True
            elif status == 'failed':
                print(f"✗ LLM 模式处理失败: {task_data.get('error')}")
                return False

        print("✗ LLM 模式处理超时")
        return False

    except Exception as e:
        print(f"✗ LLM 模式测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_process_with_rule_mode():
    """测试规则模式处理"""
    print_section("测试 3: 规则模式处理")

    # 创建测试日志文件
    test_log = Path("/tmp/test_rule_mode.log")
    test_log.write_text("""2026-06-03 10:00:00 [ERROR] [main] NullPointerException: Cannot invoke method on null object
2026-06-03 10:00:01 [ERROR] [worker] TimeoutException: Connection timeout after 30000ms
2026-06-03 10:00:02 [ERROR] [main] NullPointerException: Cannot invoke toString() on null object
2026-06-03 10:00:03 [FATAL] [main] OutOfMemoryError: Java heap space
""")

    try:
        # 上传文件
        print("1. 上传测试文件...")
        upload_data = {
            'file': ('test_rule_mode.log', open(test_log, 'rb'), 'text/plain')
        }
        upload_response = requests.post(f"{API_BASE}/api/upload", files=upload_data, headers={
            "X-User-Id": USER_ID,
            "X-User_Name": USERNAME
        })
        print(f"上传响应: {upload_response.json()}")

        if upload_response.status_code != 200:
            print("✗ 文件上传失败")
            return False

        file_path = upload_response.json()['data']['file_path']
        print(f"文件路径: {file_path}")

        # 使用规则模式处理
        print("\n2. 使用规则模式处理...")
        process_data = {
            "file_path": file_path,
            "chunk_size": 100,
            "force_restart": True,
            "use_llm": False  # 规则模式
        }

        process_response = requests.post(f"{API_BASE}/api/process", json=process_data, headers=HEADERS)
        print(f"处理响应: {process_response.json()}")

        if process_response.status_code != 200:
            print("✗ 规则模式处理失败")
            return False

        task_id = process_response.json()['data']['task_id']
        print(f"任务 ID: {task_id}")

        # 轮询任务状态
        print("\n3. 轮询任务状态...")
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(1)  # 规则模式应该更快
            task_response = requests.get(f"{API_BASE}/api/task/{task_id}", headers=HEADERS)
            task_data = task_response.json()['data']
            status = task_data['status']
            progress = task_data.get('progress', 0)
            message = task_data.get('message', '')

            print(f"  尝试 {attempt + 1}/{max_attempts}: 状态={status}, 进度={progress}%, 消息={message}")

            if status == 'completed':
                print("✓ 规则模式处理完成")
                print(f"报告数量: {len(task_data.get('reports', []))}")
                return True
            elif status == 'failed':
                print(f"✗ 规则模式处理失败: {task_data.get('error')}")
                return False

        print("✗ 规则模式处理超时")
        return False

    except Exception as e:
        print(f"✗ 规则模式测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_comparison():
    """测试性能对比"""
    print_section("测试 4: 性能对比")

    # 创建较大的测试日志文件
    test_log = Path("/tmp/test_performance.log")
    log_content = "\n".join([
        f"2026-06-03 10:00:{i:02d} [ERROR] [main] NullPointerException: Cannot invoke method on null object"
        for i in range(100)
    ])
    test_log.write_text(log_content)

    try:
        # 上传文件
        print("1. 上传测试文件...")
        upload_data = {
            'file': ('test_performance.log', open(test_log, 'rb'), 'text/plain')
        }
        upload_response = requests.post(f"{API_BASE}/api/upload", files=upload_data, headers={
            "X-User-Id": USER_ID,
            "X-User_Name": USERNAME
        })
        file_path = upload_response.json()['data']['file_path']

        # 测试规则模式
        print("\n2. 测试规则模式性能...")
        start_time = time.time()
        process_data = {
            "file_path": file_path,
            "chunk_size": 100,
            "force_restart": True,
            "use_llm": False
        }
        process_response = requests.post(f"{API_BASE}/api/process", json=process_data, headers=HEADERS)
        task_id = process_response.json()['data']['task_id']

        rule_mode_time = None
        for attempt in range(20):
            time.sleep(0.5)
            task_response = requests.get(f"{API_BASE}/api/task/{task_id}", headers=HEADERS)
            task_data = task_response.json()['data']
            if task_data['status'] == 'completed':
                rule_mode_time = time.time() - start_time
                print(f"  规则模式完成时间: {rule_mode_time:.2f} 秒")
                break
            elif task_data['status'] == 'failed':
                print(f"  规则模式失败: {task_data.get('error')}")
                break

        if rule_mode_time:
            print(f"✓ 规则模式性能测试完成: {rule_mode_time:.2f} 秒")
            print(f"  平均速度: {100/rule_mode_time:.1f} 条/秒")
            return True
        else:
            print("✗ 规则模式性能测试失败")
            return False

    except Exception as e:
        print(f"✗ 性能测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  规则模式 API 功能测试")
    print("="*60)

    results = []

    # 运行测试
    results.append(("健康检查", test_health_check()))
    results.append(("LLM 模式处理", test_process_with_llm()))
    results.append(("规则模式处理", test_process_with_rule_mode()))
    results.append(("性能对比", test_performance_comparison()))

    # 输出总结
    print_section("测试总结")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:20s} {status}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！规则模式功能正常工作。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查日志。")
        return 1

if __name__ == '__main__':
    sys.exit(main())