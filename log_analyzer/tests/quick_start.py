#!/usr/bin/env python3
"""启动服务后就返回，让用户在浏览器测试."""

import subprocess
import time
import requests
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

WEB_DIR = os.path.join(PROJECT_DIR, "web")
API_BASE = "http://localhost:8000"


def clean_port():
    try:
        output = subprocess.check_output(['lsof', '-ti:8000'], stderr=subprocess.STDOUT, text=True).strip()
        if output:
            for pid in output.split():
                subprocess.run(['kill', '-9', pid], check=True, stderr=subprocess.PIPE)
    except Exception:
        pass

    time.sleep(2)


def start_server():
    os.chdir(WEB_DIR)
    proc = subprocess.Popen(
        ['uvicorn', 'app:app', '--host', '0.0.0.0', '--port', '8000'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"服务启动中 (PID: {proc.pid})...")
    time.sleep(7)
    return proc


def test_api():
    print("\n--- 测试 API ---")
    try:
        r = requests.get(f"{API_BASE}/api/health", timeout=8)
        print(f"健康检查: {r.status_code}")
        print(f"响应: {r.text}")

        r2 = requests.get(
            f"{API_BASE}/api/auth/current",
            headers={"X-User-Id": "test_user"}
        )
        print(f"用户识别: {r2.status_code}")
        return True
    except Exception as e:
        print(f"测试错误: {e}")
        return False


def main():
    print("\n=== Log Analyzer 服务启动 ===\n")
    clean_port()
    server_proc = start_server()
    ok = test_api()

    print("\n" + "="*60)
    if ok:
        print("✅ 服务已启动成功！")
        print("\n请在浏览器访问:")
        print("   http://localhost:8000")
        print("\n你现在可以在前端界面上传和测试文件了！")
    else:
        print("⚠️  服务可能启动有问题，请检查浏览器是否可以访问")

    print("="*60)
    print("\n这个脚本会一直运行，按 Ctrl+C 停止服务")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except Exception:
            server_proc.kill()
        print("服务已停止")


if __name__ == "__main__":
    main()
