"""
전역 상수 정의
Application-wide constants configuration
"""

import os
from pathlib import Path
from datetime import datetime

# ============================================================================
# File paths
# ============================================================================

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

# 암호화된 설정 파일 (GitHub Token 등 저장)
ENCRYPTED_CONFIG_FILE = CONFIG_DIR / "encrypted_config.enc"
