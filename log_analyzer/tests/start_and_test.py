#!/usr/bin/env python3
"""简单的服务启动器."""

import subprocess
import time
import requests
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(PROJECT_DIR, "web")
API_BASE = "http://localhost:8000"


def clean_port():
    """清理 8000 端口."""
    print("--- 清理 8000 端口 ---")
    try:
        output = subprocess.check_output(
            ['lsof', '-ti:8000'],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        if output:
            for pid in output.split():
                print(f"  停止 PID: {pid}")
                subprocess.run(['kill', '-9', pid], check=True)
    except Exception as e:
        pass

    time.sleep(2)


def start_server():
    """启动服务."""
    os.chdir(WEB_DIR)
    print("--- 启动服务 ---")
    proc = subprocess.Popen(
        ['uvicorn', 'app:app', '--host', '0.0.0.0', '--port', '8000'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(f"  服务 PID: {proc.pid}")
    print(f"  等待服务启动...")
    time.sleep(6)
    return proc


def test_health():
    """健康检查."""
    print("\n--- 1. 健康检查 ---")
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=10)
        print(f"  状态码: {resp.status_code}")
        print(f"  响应: {resp.text}")
        if resp.status_code == 200:
            return True
    except Exception as e:
        print(f"  失败: {e}")
    return False


def test_user():
    """测试用户识别."""
    print("\n--- 2. 用户识别 ---")
    try:
        resp = requests.get(
            f"{API_BASE}/api/auth/current",
            headers={"X-User-Id": "test_restart_user"},
            timeout=10
        )
        print(f"  状态码: {resp.status_code}")
        print(f"  响应: {resp.text}")
        if resp.status_code == 200:
            return True
    except Exception as e:
        print(f"  失败: {e}")
    return False


def test_reports():
    """测试历史报告列表."""
    print("\n--- 3. 历史报告列表 ---")
    try:
        resp = requests.get(
            f"{API_BASE}/api/history/reports",
            headers={"X-User-Id": "test_restart_user"},
            timeout=10
        )
        print(f"  状态码: {resp.status_code}")
        print(f"  响应: {resp.text}")
        if resp.status_code == 200:
            return True
    except Exception as e:
        print(f"  失败: {e}")
    return False


def main():
    print("="*70)
    print("  Log Analyzer 服务重启与测试")
    print("="*70)
    print()

    clean_port()
    proc = start_server()

    results = []
    results.append(("健康检查", test_health()))
    results.append(("用户识别", test_user()))
    results.append(("历史报告", test_reports()))

    print()
    print("="*70)
    print("  测试结果")
    print("="*70)
    all_pass = True
    for name, ok in results:
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"  {name}: {status}")
        if not ok:
            all_pass = False

    print()
    if all_pass:
        print("  所有核心接口测试通过！")
        print("  请访问: http://localhost:8000")
    else:
        print("  部分测试失败，请检查日志")

    print()
    print("="*70)
    print("\n按 Ctrl+C 停止服务")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("服务已停止")


if __name__ == "__main__":
    main()
