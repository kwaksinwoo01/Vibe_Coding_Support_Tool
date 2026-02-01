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
    DEFAULT_PORT, SERVER_HOST,
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
