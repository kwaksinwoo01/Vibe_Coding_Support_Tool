import subprocess
import socket
import sys
import os
import logging
import json
import shutil
import traceback
from pathlib import Path
from datetime import datetime
import uvicorn
from PyQt6.QtCore import QThread, pyqtSignal
import httpx


from settings.constants import (
    AGENT_PATH, FAVICON_PATH, GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH,
    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_URL, DEFAULT_PORT, SERVER_HOST,
    LOG_DIR, LOG_FILE, CONFIG_DIR, CONFIG_FILE
)
# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 헬퍼 함수
# ============================================================================

def run_redis_cli_command(command: str) -> str:
    """Redis CLI 명령 실행 (Windows 호환)"""
    try:
        # Windows에서 Redis CLI 경로 찾기
        possible_paths = [
            r"C:\Program Files\Redis\redis-cli.exe",  # 일반 설치 경로
            r"C:\Redis\redis-cli.exe",  # 다른 설치 경로
            "redis-cli.exe"  # PATH에 있는 경우
        ]

        redis_cli_path = None
        for path in possible_paths:
            if os.path.exists(path) or shutil.which(path):
                redis_cli_path = path
                break

        if not redis_cli_path:
            return "Redis CLI를 찾을 수 없습니다. Redis가 설치되어 있는지 확인하세요."

        # Windows CMD를 통해 실행
        full_command = f'cmd /c "{redis_cli_path}" -h {REDIS_HOST} -p {REDIS_PORT} -n {REDIS_DB} {command}'
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            return result.stdout if result.stdout else result.stderr
        else:
            return f"실행 실패 (코드: {result.returncode}): {result.stderr}"

    except Exception as e:
        return f"실행 실패: {str(e)}"

def run_terminal_command(command: str) -> str:
    """일반 터미널 명령 실행 (Windows 호환)"""
    try:
        # Windows CMD를 통해 실행
        full_command = f'cmd /c "{command}"'
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            return result.stdout if result.stdout else result.stderr
        else:
            return f"실행 실패 (코드: {result.returncode}): {result.stderr}"

    except Exception as e:
        return f"실행 실패: {str(e)}"

# ============================================================================
# Agent Command Execution - REMOVED
# ============================================================================
# Agent commands are now handled by server_thread.py which uses
# the subprocess module to execute main_agent.py module directly
# using: python -m vibeStation_setup.mcp_suver.main_agent <user_input>


# ============================================================================
# Server Thread (Core MCP Server) - REMOVED: Use server_thread.py instead
# ============================================================================

# ============================================================================
# Example Server Startup (for standalone usage) - DISABLED
# ============================================================================
# ServerThread has been moved to server_thread.py
# Use: from mcp_suver.core.server_thread import ServerThread

if __name__ == "__main__":
    """
    Example standalone server startup (minimal UI-free version)
    For full GUI application, use app.py instead.
    """
    print("ServerThread has been moved to server_thread.py")
    print("Use: from mcp_suver.core.server_thread import ServerThread")
    print("Or run: python app.py")
