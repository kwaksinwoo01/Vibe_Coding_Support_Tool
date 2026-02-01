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

# Import configuration management from common module
sys.path.insert(0, str(Path(__file__).parent.parent))
from vibeStation_setup.settings.config_manager import load_config, save_config
from settings.settings_method import check_agent_path, find_available_port, check_git_installed
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QScrollArea,
                             QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLabel,
                             QLineEdit, QFileDialog, QGroupBox, QMessageBox, QComboBox, QDialog,
                             QTabWidget, QToolButton, QListWidget, QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal, QProcess, Qt
from PyQt6.QtGui import QFont, QIcon
import httpx


from settings.constants import (
    AGENT_PATH, FAVICON_PATH, GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH,
    REDIS_HOST, REDIS_PORT, REDIS_DB, DEFAULT_PORT, SERVER_HOST,
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
            return "오류: redis-cli.exe를 찾을 수 없습니다. Redis가 설치되었는지 확인하세요."
        
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
            return result.stdout.strip()
        else:
            return f"오류: {result.stderr.strip()}"
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
            return result.stdout.strip()
        else:
            return f"오류: {result.stderr.strip()}"
    except Exception as e:
        return f"실행 실패: {str(e)}"

def run_agent_command(user_input: str, agent_path: str, env_vars: dict = None) -> str:
    """main_agent.py 직접 실행 (터미널 명령 대신)"""
    try:
        if not os.path.exists(agent_path):
            return f"오류: Agent 파일을 찾을 수 없습니다: {agent_path}"
        
        # 환경 변수 설정
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # GitHub 설정 추가 (Agent가 접근할 수 있도록)
        if GITHUB_REPO_PATH:
            env['GITHUB_REPO_PATH'] = GITHUB_REPO_PATH
        if MAIN_DOCUMENT_PATH:
            env['MAIN_DOCUMENT_PATH'] = MAIN_DOCUMENT_PATH
        
        # Python subprocess로 직접 실행
        result = subprocess.run(
            [sys.executable, agent_path, user_input],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.dirname(agent_path),
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"오류: {result.stderr.strip()}"
    except Exception as e:
        return f"실행 실패: {str(e)}"
