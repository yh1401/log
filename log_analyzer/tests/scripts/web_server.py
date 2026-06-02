#!/usr/bin/env python3
"""Web server launcher for Log Analyzer."""

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    import uvicorn
    from fastapi import FastAPI
except ImportError:
    print("📦 Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "python-multipart"])
    print("✅ Packages installed successfully!")
    print()

print("📊 Starting Log Analyzer Web Server...")
print("----------------------------------------")
print()
print("Server will be available at:")
print("  http://localhost:8000")
print()
print("Press Ctrl+C to stop the server")
print("----------------------------------------")
print()

os.chdir(str(SCRIPT_DIR))

from web.app import app

if __name__ == "__main__":
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
