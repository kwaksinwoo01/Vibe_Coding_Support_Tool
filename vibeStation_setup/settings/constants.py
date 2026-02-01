"""
전역 상수 정의
Application-wide constants configuration
"""

import os
from pathlib import Path
from datetime import datetime

# ============================================================================
# Agent 및 파일 경로
# ============================================================================

# AGENT_PATH: main_agent.py 파일의 절대 경로
# 사용자가 직접 설정 가능 (GUI에서도 변경 가능)
AGENT_PATH = r"C:\Users\user\Documents\github\turbo-system\.github\agents\tool\main_agent.py"

# FAVICON_PATH: favicon.ico 파일 경로
FAVICON_PATH = r"C:\Users\user\Downloads\icon.ico"

# ============================================================================
# GitHub 저장소 설정 (사용자가 GUI에서 지정)
# ============================================================================

# GitHub 저장소 경로 (빈값 - 사용자가 입력)
GITHUB_REPO_PATH = ""

# 메인 문서 경로 (빈값 - 사용자가 입력, 예: docs_2/NextTask-2.md)
MAIN_DOCUMENT_PATH = ""

# ============================================================================
# Redis 설정
# ============================================================================

# Redis 호스트 (포트 설정을 변경한 유저를 대비해 자동 감지)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

# Redis 포트
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Redis 데이터베이스 번호
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Redis URL (환경 변수 또는 호스트/포트/DB 정보를 사용하여 생성)
# 예: redis://localhost:6379/0
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# ============================================================================
# 서버 설정
# ============================================================================

# 기본 포트
DEFAULT_PORT = 8000

# 서버 호스트
SERVER_HOST = "127.0.0.1"

# ============================================================================
# 로그 설정
# ============================================================================

# 로그 디렉토리
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 로그 파일
LOG_FILE = LOG_DIR / f"mcp_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# ============================================================================
# 설정 파일 경로
# ============================================================================

# 설정 디렉토리
CONFIG_DIR = Path(__file__).parent / "config"
CONFIG_DIR.mkdir(exist_ok=True)

# 설정 파일 (GitHub Token 등 저장)
CONFIG_FILE = CONFIG_DIR / "server_config.json"
