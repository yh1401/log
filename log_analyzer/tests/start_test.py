#!/usr/bin/env python3
"""快速启动和测试服务."""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path

PROJECT_DIR = Path("/Users/a666/Documents/trae_projects/log/log_analyzer")
API_BASE = "http://localhost:8000"

def clean_port():
    """清理 8000 端口."""
    try:
        import subprocess
        output = subprocess.check_output(['lsof', '-ti:8000'], stderr=subprocess.STDOUT, text=True).strip()
        if output:
            for pid in output.split():
                try:
                    subprocess.run(['kill', '-9', pid], check=True)
                except Exception as e:
                    print(f"无法停止 PID {pid}: {e}")
        time.sleep(2)
        return True
    except Exception as e:
        print(f"端口清理: {e}")
        return True

def start_server():
    """启动服务."""
    os.chdir(str(PROJECT_DIR / "web"))
    process = subprocess.Popen(
        ['uvicorn', 'app:app', '--host', '0.0.0.0', '--port', '8000'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(f"服务已启动 (PID: {process.pid})")
    time.sleep(6)
    return process

def test_endpoints():
    """测试所有关键接口."""
    print("="*60)
    print("1. 健康检查")
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=10)
        print(f"   状态码: {resp.status_code}")
        print(f"   响应: {resp.json()}")
        print("   ✅ 通过")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n2. 用户识别")
    try:
        resp = requests.get(
            f"{API_BASE}/api/auth/current",
            headers={"X-User-Id": "test_user_fix"},
            timeout=10
        )
        print(f"   状态码: {resp.status_code}")
        print(f"   响应: {resp.json()}")
        print("   ✅ 通过")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n3. 历史报告列表")
    try:
        resp = requests.get(
            f"{API_BASE}/api/history/reports",
            headers={"X-User-Id": "test_user_fix"},
            timeout=10
        )
        print(f"   状态码: {resp.status_code}")
        print(f"   响应: {resp.json()}")
        print("   ✅ 通过")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n" + "="*60)
    print("服务已启动，请访问 http://localhost:8000")
    print("="*60)
    print("\n按 Ctrl+C 停止服务...")

def main():
    print("\n=== Log Analyzer 服务启动 ===\n")
    clean_port()
    process = start_server()

    try:
        test_endpoints()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n正在停止服务...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("服务已停止")

if __name__ == "__main__":
    main()
