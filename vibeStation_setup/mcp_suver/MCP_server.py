import asyncio
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from langgraph.checkpoint.redis import RedisSaver
import redis  # 기존 from redis.asyncio import Redis 대신
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
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QScrollArea,
                             QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLabel,
                             QLineEdit, QFileDialog, QGroupBox, QMessageBox, QComboBox, QDialog,
                             QTabWidget, QToolButton, QListWidget, QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal, QProcess, Qt
from PyQt6.QtGui import QFont, QIcon
import httpx

from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# 설정 로드 함수 수정
def load_config() -> dict:
    return {
        "github_token": os.getenv("GITHUB_TOKEN", ""),
        "workflow_secret": os.getenv("WORKFLOW_SECRET", ""),
        "repo_path": os.getenv("REPO_PATH", ""),
        "main_doc": os.getenv("MAIN_DOC", ""),
        "branch": os.getenv("BRANCH", "")
    }

# 설정 저장 함수 수정 (필요 시)
def save_config(config: dict):
    # .env 파일에 쓰기 (단순 예시, 실제로는 파일 업데이트 로직 필요)
    with open(".env", "w") as f:
        for key, value in config.items():
            f.write(f"{key.upper()}={value}\n")

# ============================================================================
# 상수 정의
# ============================================================================

# AGENT_PATH: main_agent.py 파일의 절대 경로
# 사용자가 직접 설정 가능 (GUI에서도 변경 가능)
AGENT_PATH = r"C:\Users\user\Documents\github\turbo-system\.github\agents\tool\main_agent.py"

# FAVICON_PATH: favicon.ico 파일 경로
FAVICON_PATH = r"C:\Users\user\Downloads\icon.ico"


# GitHub 저장소 설정 (사용자가 GUI에서 지정)
GITHUB_REPO_PATH = ""  # 빈값 - 사용자가 입력
MAIN_DOCUMENT_PATH = ""  # 빈값 - 사용자가 입력 (예: docs_2/NextTask-2.md)

# Redis 설정 포트 설정을 변경한 유저를 대비해 자동 감지를 한다.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# 기본 포트
DEFAULT_PORT = 8000
SERVER_HOST = "127.0.0.1"

# 로그 설정
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"mcp_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# 설정 파일 경로 (GitHub Token 등 저장)
CONFIG_DIR = Path(__file__).parent / "config"
CONFIG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "server_config.json"

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

def find_available_port(start_port, end_port):
    """사용 가능한 포트 찾기"""
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((SERVER_HOST, port)) != 0:
                logger.info(f"포트 {port} 사용 가능")
                return port
    logger.warning(f"포트 범위 {start_port}-{end_port}에서 사용 가능한 포트 없음")
    return None

def check_redis_connection():
    """Redis 연결 확인"""
    try:
        import redis
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, socket_timeout=2)
        client.ping()
        logger.info(f"Redis 연결 성공: {REDIS_HOST}:{REDIS_PORT}")
        return True
    except Exception as e:
        logger.error(f"Redis 연결 실패: {e}")
        return False

def check_agent_path(path: str) -> bool:
    """main_agent.py 경로 확인"""
    if not path or not os.path.exists(path):
        logger.error(f"Agent 파일 없음: {path}")
        return False
    if not path.endswith("main_agent.py"):
        logger.error(f"잘못된 파일: {path}")
        return False
    logger.info(f"Agent 경로 확인: {path}")
    return True

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

def save_config(config: dict, config_file: Path):
    """설정을 JSON 파일에 저장"""
    try:
        import json
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"설정 저장 실패: {e}")
        return False

def load_config(config_file: Path) -> dict:
    """설정을 JSON 파일에서 로드"""
    try:
        import json
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"설정 로드 실패: {e}")
    return {}

def check_git_installed() -> bool:
    """git 설치 여부 확인"""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

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

# ============================================================================
# GitHub 저장소 유틸리티
# ============================================================================

class GitHubTokenHelpDialog(QDialog):
    """GitHub Token 생성법 도움말 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub Token 생성 가이드")
        self.setGeometry(200, 200, 600, 500)
        
        layout = QVBoxLayout()
        
        # 도움말 텍스트
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>GitHub Personal Access Token 생성 방법</h2>
        
        <h3>1. GitHub 로그인</h3>
        <p><a href="https://github.com">https://github.com</a></p>
        
        <h3>2. Settings 접근</h3>
        <p>우측 상단 프로필 아이콘 클릭 → <b>Settings</b></p>
        
        <h3>3. Developer settings</h3>
        <p>좌측 메뉴 하단 <b>"Developer settings"</b> 클릭</p>
        
        <h3>4. Personal access tokens</h3>
        <p><b>"Personal access tokens"</b> → <b>"Tokens (classic)"</b> 선택</p>
        
        <h3>5. 새 토큰 생성</h3>
        <p><b>"Generate new token"</b> → <b>"Generate new token (classic)"</b> 클릭</p>
        
        <h3>6. 토큰 설정</h3>
        <ul>
        <li><b>Note:</b> "MCP Server Token" (원하는 이름)</li>
        <li><b>Expiration:</b> "No expiration" (만료 없음) 또는 원하는 기간</li>
        <li><b>Select scopes (권한):</b>
          <ul>
          <li>✓ <b>repo</b> (전체 저장소 접근)</li>
          <li>✓ <b>workflow</b> (GitHub Actions 접근)</li>
          <li>✓ <b>read:org</b> (조직 정보 읽기)</li>
          </ul>
        </li>
        </ul>
        
        <h3>7. 토큰 생성</h3>
        <p>하단 <b>"Generate token"</b> 버튼 클릭</p>
        
        <h3>⚠️ 중요</h3>
        <p style="color: red; font-weight: bold;">생성된 토큰을 복사하세요!</p>
        <p>예: <code>ghp_1234567890abcdefghijklmnopqrstuvwxyz</code></p>
        <p style="color: orange;">(이 페이지를 떠나면 다시 볼 수 없습니다!)</p>
        """)
        layout.addWidget(help_text)
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class GitHubRepositoryConfig:
    """GitHub 저장소 설정 관리"""
    
    def __init__(self, repo_path: str = "", github_token: str = ""):
        self.repo_path = repo_path
        self.repo_type = "unknown"
        self.owner = ""
        self.repo_name = ""
        self.is_valid = False
        self.branch = "main"
        self.available_branches = []
        self.github_token = github_token  # GitHub 토큰 (API 제한 해제용)
    
    def detect_repo_type(self, repo_path: str) -> str:
        """저장소 경로 타입 감지"""
        if not repo_path:
            return "unknown"
        
        repo_path = repo_path.strip()
        
        # HTTPS: https://github.com/owner/repo.git
        if repo_path.startswith(("https://github.com/", "http://github.com/")):
            return "https"
        
        # SSH: git@github.com:owner/repo.git
        if repo_path.startswith("git@github.com:"):
            return "ssh"
        
        # CLI: owner/repo (간단한 형식 - "gh repo" 명령 제거)
        parts = repo_path.split()
        clean_path = parts[-1] if parts else ""  # 마지막 부분만 추출
        if "/" in clean_path and not clean_path.startswith(("http://", "https://", "git@")):
            return "cli"
        
        # 로컬 경로: C:\path\to\repo
        if os.path.isdir(repo_path):
            return "local"
        
        return "unknown"
    
    def parse_repository(self, repo_path: str) -> bool:
        """저장소 경로 파싱"""
        self.repo_path = repo_path.strip()
        self.repo_type = self.detect_repo_type(self.repo_path)
        
        try:
            if self.repo_type == "https":
                # https://github.com/owner/repo.git
                parts = self.repo_path.replace("https://", "").replace("http://", "")
                parts = parts.replace("github.com/", "").replace(".git", "")
                owner_repo = parts.split("/")
                if len(owner_repo) >= 2:
                    self.owner = owner_repo[0]
                    self.repo_name = owner_repo[1]
                    self.is_valid = True
                    return True
            
            elif self.repo_type == "ssh":
                # git@github.com:owner/repo.git
                parts = self.repo_path.replace("git@github.com:", "").replace(".git", "")
                owner_repo = parts.split("/")
                if len(owner_repo) == 2:
                    self.owner = owner_repo[0]
                    self.repo_name = owner_repo[1]
                    self.is_valid = True
                    return True
            
            elif self.repo_type == "cli":
                # owner/repo (gh repo 명령 제거)
                parts = self.repo_path.split()
                clean_path = parts[-1] if parts else ""
                owner_repo = clean_path.split("/")
                if len(owner_repo) >= 2:
                    self.owner = owner_repo[0]
                    self.repo_name = owner_repo[1]
                    self.is_valid = True
                    return True
            
            elif self.repo_type == "local":
                # 로컬 경로에서 .git 확인
                git_dir = os.path.join(self.repo_path, ".git")
                if os.path.isdir(git_dir):
                    # git remote -v로 owner/repo 추출
                    result = subprocess.run(
                        ["git", "-C", self.repo_path, "remote", "-v"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # origin  https://github.com/owner/repo.git (fetch)
                        for line in result.stdout.split("\n"):
                            if "origin" in line and "github.com" in line:
                                # URL 추출
                                parts = line.split()
                                if len(parts) >= 2:
                                    url = parts[1]
                                    config = GitHubRepositoryConfig()
                                    if config.parse_repository(url):
                                        self.owner = config.owner
                                        self.repo_name = config.repo_name
                                        self.branch = config.branch
                                        self.is_valid = True
                                        return True
                    
                    # git symbolic-ref로 기본 브랜치 감지
                    result = subprocess.run(
                        ["git", "-C", self.repo_path, "symbolic-ref", "refs/remotes/origin/HEAD"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # refs/remotes/origin/main
                        branch_ref = result.stdout.strip()
                        if "/" in branch_ref:
                            self.branch = branch_ref.split("/")[-1]
        
        except Exception as e:
            self.is_valid = False
            return False
        
        self.is_valid = False
        return False
    
    def get_raw_content_url(self, file_path: str, branch: str = "") -> str:
        """GitHub Raw Content URL 생성 (토큰 노출 제거)"""
        if not self.is_valid:
            return ""
        
        branch = branch or self.branch
        file_path = file_path.replace("\\", "/").strip()
        
        # (변경) 쿼리 스트링에서 토큰을 제거하여 URL 노출 방지
        return f"https://raw.githubusercontent.com/{self.owner}/{self.repo_name}/{branch}/{file_path}"

    async def fetch_raw_content(self, file_path: str, branch: str = "") -> str:
        """(추가) 헤더에 토큰을 담아 안전하게 내용을 가져오는 함수"""
        url = self.get_raw_content_url(file_path, branch)
        
        # 인증 헤더 구성 (이 방식이 표준 보안 절차입니다)
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3.raw"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.text
            else:
                return f"Error: {response.status_code}"
                
    def get_web_url(self, file_path: str, branch: str = "") -> str:
        """GitHub Web URL 생성"""
        if not self.is_valid:
            return ""
        
        # 기본 브랜치 사용
        if not branch:
            branch = self.branch
        
        # URL 정규화
        file_path = file_path.replace("\\", "/").strip()
        
        # https://github.com/owner/repo/blob/branch/path/to/file
        return f"https://github.com/{self.owner}/{self.repo_name}/blob/{branch}/{file_path}"
    
    def detect_default_branch(self) -> str:
        """GitHub API로 기본 브랜치 감지"""
        if not self.is_valid:
            return "main"
        
        try:
            import urllib.request
            
            url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(request, timeout=5) as response:
                import json
                data = json.loads(response.read().decode('utf-8'))
                self.branch = data.get('default_branch', 'main')
                return self.branch
        except Exception:
            self.branch = "main"
            return "main"

    def fetch_available_branches(self, use_git: bool = False) -> list:
        """GitHub API로 활성 브랜치 목록 조회 (또는 git 명령어 사용)"""
        if not self.is_valid:
            return []
        
        # git 명령어 방식 시도
        if use_git or self.repo_type == "local":
            return self._fetch_branches_via_git()
        
        # GitHub API 방식 시도
        branches = self._fetch_branches_via_api()
        if not branches:
            # API 실패 시 git 방식으로 폴백
            branches = self._fetch_branches_via_git()
        
        return branches
    
    def _fetch_branches_via_api(self) -> list:
        """GitHub API를 통한 브랜치 조회 (최근 커밋순 정렬)"""
        try:
            import urllib.request
            import urllib.error
            import json
            from datetime import datetime
            
            # GitHub API로 브랜치 목록 조회
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/branches?per_page=100"
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            # GitHub Token이 있으면 추가 (API 제한 증가: 60 → 5000)
            if self.github_token:
                request.add_header('Authorization', f'token {self.github_token}')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                branches_data = json.loads(response.read().decode('utf-8'))
                
                # 활성 브랜치를 커밋 날짜와 함께 정렬
                branches_with_date = []
                for branch in branches_data:
                    if isinstance(branch, dict) and 'name' in branch:
                        try:
                            # 커밋 날짜 추출
                            commit_date = branch.get('commit', {}).get('commit', {}).get('committer', {}).get('date', '')
                            branches_with_date.append({
                                'name': branch['name'],
                                'date': commit_date
                            })
                        except:
                            branches_with_date.append({
                                'name': branch['name'],
                                'date': '0000-00-00T00:00:00Z'
                            })
                
                # 커밋 날짜순으로 정렬 (최신순)
                branches_with_date.sort(key=lambda x: x['date'], reverse=True)
                
                # 브랜치명만 추출
                active_branches = [b['name'] for b in branches_with_date]
                
                # 기본 브랜치 먼저 정렬
                if self.branch in active_branches:
                    active_branches.remove(self.branch)
                    active_branches.insert(0, self.branch)
                
                self.available_branches = sorted(active_branches)
                return self.available_branches
                
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"[GitHub API] 403 Forbidden - API 제한 초과 (인증 토큰 필요)")
                return []
            elif e.code == 404:
                print(f"[GitHub API] 404 Not Found - 저장소를 찾을 수 없음")
                return []
            else:
                print(f"[GitHub API] HTTP 오류: {e.code}")
                return []
        except urllib.error.URLError as e:
            print(f"[GitHub API] 네트워크 오류: {e.reason}")
            return []
        except Exception as e:
            print(f"[GitHub API] 오류: {str(e)}")
            return []

    def _fetch_branches_via_git(self) -> list:
        """git 명령어를 통한 브랜치 조회 (최근 커밋순 정렬)"""
        try:
            branches_with_date = []
            
            # 로컬 저장소인 경우
            if self.repo_type == "local" and os.path.isdir(self.repo_path):
                result = subprocess.run(
                    ["git", "-C", self.repo_path, "for-each-ref", "--sort=-committerdate", "--format=%(refname:short)|%(committerdate:iso)", "refs/remotes/origin/"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if line.strip():
                            parts = line.split("|")
                            if len(parts) >= 2:
                                branch = parts[0].replace("origin/", "")
                                if not branch.startswith("HEAD"):
                                    date = parts[1] if len(parts) > 1 else "0000-00-00"
                                    branches_with_date.append({
                                        'name': branch,
                                        'date': date
                                    })
                    
                    # 중복 제거
                    seen = set()
                    unique_branches = []
                    for b in branches_with_date:
                        if b['name'] not in seen:
                            seen.add(b['name'])
                            unique_branches.append(b)
                    
                    branches = [b['name'] for b in unique_branches]
                    self.available_branches = sorted(list(set(branches)))
                    return self.available_branches
            
            # HTTPS/SSH인 경우 - git ls-remote 사용
            elif self.repo_type in ("https", "ssh"):
                result = subprocess.run(
                    ["git", "ls-remote", "--heads", self.repo_path.replace(".git", "")],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    branches = []
                    for line in result.stdout.split("\n"):
                        if line.strip():
                            # refs/heads/branch-name
                            parts = line.split("/")
                            if len(parts) >= 3:
                                branch = parts[-1]
                                branches.append(branch)
                    
                    self.available_branches = sorted(list(set(branches)))
                    return self.available_branches
        
        except Exception as e:
            print(f"[git ls-remote] 오류: {str(e)}")
            return []
        
        return []
    
    def set_branch(self, branch_name: str):
        """브랜치 설정"""
        if branch_name:
            self.branch = branch_name
        return True

# ============================================================================
# 서버 스레드
# ============================================================================

class ServerThread(QThread):
    """FastAPI + SSE 서버 실행 스레드"""
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, port: int, agent_path: str):
        super().__init__()
        self.port = port
        self.agent_path = agent_path
        self.app = None
        self.redis_client = None
        self.checkpointer = None
        self._running = True

    def run(self):
        """서버 실행"""
        try:
            self.log_signal.emit(f"[서버] 포트 {self.port}에서 시작 중...")
            self.status_signal.emit(f"초기화 중... (Port: {self.port})")
            
            # Redis 연결 (동기 클라이언트로 변경)
            self.log_signal.emit(f"[Redis] {REDIS_HOST}:{REDIS_PORT} 연결 시도...")
            self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
            
            # RedisSaver 생성 (환경 변수 기반 redis_url 사용)
            redis_url = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
            self.checkpointer = RedisSaver(redis_url, redis_client=self.redis_client)
            
            self.log_signal.emit("[Redis] 체크포인터 초기화 완료")
            
            # FastAPI 앱 생성
            self.app = FastAPI(title="MCP Server", version="1.0.0")
            self._setup_routes()
            
            # Uvicorn 서버 실행
            self.status_signal.emit(f"실행 중 (Port: {self.port})")
            self.log_signal.emit(f"[서버] http://{SERVER_HOST}:{self.port} 리스닝 시작")
            
            config = uvicorn.Config(
                self.app, 
                host=SERVER_HOST, 
                port=self.port, 
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(config)
            asyncio.run(server.serve())
            
        except Exception as e:
            error_msg = f"서버 실행 오류: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.error_signal.emit(error_msg)
            self.status_signal.emit("오류 발생")
    
    def _setup_routes(self):
        """FastAPI 라우트 설정"""
        
        @self.app.get("/")
        async def root():
            return {
                "status": "MCP Server Running",
                "port": self.port,
                "agent_path": self.agent_path,
                "redis": f"{REDIS_HOST}:{REDIS_PORT}",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/health")
        async def health():
            redis_ok = check_redis_connection()
            agent_ok = check_agent_path(self.agent_path)
            return {
                "status": "healthy" if (redis_ok and agent_ok) else "degraded",
                "redis": redis_ok,
                "agent": agent_ok
            }
        
        @self.app.get("/sse")
        async def sse_endpoint(request: Request):
            """SSE 엔드포인트 (MCP 프로토콜)"""
            async def event_generator():
                try:
                    self.log_signal.emit("[SSE] 클라이언트 연결됨")
                    yield {"event": "connected", "data": json.dumps({"status": "ok"})}
                    
                    counter = 0
                    while self._running:
                        if await request.is_disconnected():
                            self.log_signal.emit("[SSE] 클라이언트 연결 끊김")
                            break
                        
                        # 하트비트 전송
                        counter += 1
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({"count": counter, "time": datetime.now().isoformat()})
                        }
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    error_msg = f"SSE 오류: {e}"
                    logger.error(error_msg)
                    yield {"event": "error", "data": json.dumps({"error": str(e)})}
            
            return EventSourceResponse(event_generator())
        
        @self.app.post("/execute")
        async def execute_task(request: Request):
            """에이전트 작업 실행"""
            try:
                data = await request.json()
                user_input = data.get("user_input", "")
                
                self.log_signal.emit(f"[실행] 요청: {user_input[:100]}")
                
                # main_agent.py 호출
                if not check_agent_path(self.agent_path):
                    return {"status": "error", "message": "Agent 경로 오류"}
                
                # 실제 실행은 subprocess로 처리
                result = subprocess.run(
                    [sys.executable, self.agent_path, user_input],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                self.log_signal.emit(f"[실행] 완료 (코드: {result.returncode})")
                
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
                
            except Exception as e:
                error_msg = f"실행 오류: {e}"
                logger.error(error_msg)
                self.log_signal.emit(f"[오류] {error_msg}")
                return {"status": "error", "message": str(e)}
    
    def stop(self):
        """서버 중지"""
        self._running = False
        self.log_signal.emit("[서버] 중지 요청됨")
        if self.redis_client:
            try:
                asyncio.run(self.redis_client.close())
            except:
                pass

# ============================================================================
# GUI 메인 윈도우
# ============================================================================

class SettingsDialog(QDialog):
    """설정 다이얼로그 (GitHub 저장소 연결 + 서버설정)"""
    
    def __init__(self, parent, config_file, github_repo_config, env_vars):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setGeometry(100, 100, 900, 700)
        
        self.parent_app = parent
        self.config_file = config_file
        self.github_repo_config = github_repo_config
        self.env_vars = env_vars
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        
        # 탭 위젯
        self.tabs = QTabWidget()
        
        # 탭 1: GitHub 저장소 연결
        self.github_tab = QWidget()
        self.init_github_tab()
        self.tabs.addTab(self.github_tab, "GitHub 저장소 연결")
        
        # 탭 2: 서버 설정
        self.server_tab = QWidget()
        self.init_server_tab()
        self.tabs.addTab(self.server_tab, "서버 설정")
        
        main_layout.addWidget(self.tabs)
        
        # 닫기 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
        
        # 저장된 설정 로드
        self.load_saved_settings()
    
    def load_saved_settings(self):
        """저장된 설정 로드"""
        saved_config = load_config(self.config_file)
        
        # GitHub Token 로드
        if "github_token" in saved_config:
            self.github_token_input.setText(saved_config["github_token"])
        
        # Workflow Secret 로드
        if "workflow_secret" in saved_config:
            self.workflow_secret_input.setText(saved_config["workflow_secret"])
        
        # 저장소 경로 로드
        if "repo_path" in saved_config:
            self.repo_input.setText(saved_config["repo_path"])
        
        # 메인 문서 로드
        if "main_doc" in saved_config:
            self.main_doc_input.setText(saved_config["main_doc"])
        
        # 브랜치 로드
        if "branch" in saved_config:
            self.branch_combo.setCurrentText(saved_config["branch"])

        # Redis URL 로드
        if "redis_url" in saved_config:
            self.redis_url_input.setText(saved_config["redis_url"])

        # Agent 경로 로드
        if "agent_path" in saved_config:
            self.agent_path_input.setText(saved_config["agent_path"])

        # 문서 검색 옵션 로드
        if "docs2_filter" in saved_config:
            self.docs2_filter_checkbox.setChecked(bool(saved_config["docs2_filter"]))
        if "docs_filter" in saved_config:
            self.docs_filter_checkbox.setChecked(bool(saved_config["docs_filter"]))
        if "keyword_filter" in saved_config:
            self.keyword_filter_checkbox.setChecked(bool(saved_config["keyword_filter"]))
    
    def init_github_tab(self):
        """GitHub 저장소 연결 탭 초기화"""
        layout = QVBoxLayout()
        
        # GitHub 저장소 설정 그룹
        github_group = QGroupBox("GitHub 저장소 설정")
        github_layout = QVBoxLayout()
        
        # 저장소 경로 + GitHub Token
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("저장소 경로:"))
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("https://github.com/owner/repo.git")
        row1.addWidget(self.repo_input)
        detect_repo_btn = QPushButton("연결")
        detect_repo_btn.clicked.connect(self.connect_github_repo)
        row1.addWidget(detect_repo_btn)
        github_layout.addLayout(row1)
        
        # GitHub Token + 도움말
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("GitHub Token:"))
        self.github_token_input = QLineEdit()
        self.github_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.github_token_input.setPlaceholderText("ghp_...")
        self.github_token_input.textChanged.connect(self.on_token_changed)
        row2.addWidget(self.github_token_input)
        
        # Token 도움말 버튼
        help_btn = QToolButton()
        help_btn.setText("?")
        help_btn.clicked.connect(self.show_token_help)
        row2.addWidget(help_btn)
        github_layout.addLayout(row2)
        
        # 저장소 정보 라벨
        self.repo_info_label = QLabel("저장소: 연결 안됨")
        self.repo_info_label.setStyleSheet("color: #888; font-size: 9pt;")
        github_layout.addWidget(self.repo_info_label)
        
        # Workflow Secret
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Workflow Secret:"))
        self.workflow_secret_input = QLineEdit()
        self.workflow_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        row3.addWidget(self.workflow_secret_input)
        github_layout.addLayout(row3)
        
        # 브랜치 선택
        row4 = QVBoxLayout()
        branch_label = QLabel("브랜치:")
        branch_label_desc = QLabel("(최근 커밋순 | GitHub Token 필요)")
        branch_label_desc.setStyleSheet("color: #888; font-size: 8pt;")
        row4.addWidget(branch_label)
        row4.addWidget(branch_label_desc)
        
        self.branch_combo = QComboBox()
        self.branch_combo.setEnabled(False)
        self.branch_combo.setEditable(True)
        
        # ✅ 브랜치 선택 시 이벤트 핸들러 연결
        self.branch_combo.currentTextChanged.connect(self.on_branch_selected)
        
        row4.addWidget(self.branch_combo)
        github_layout.addLayout(row4)

        
        # 메인 문서
        row5 = QVBoxLayout()
        doc_label = QLabel("메인 문서:")
        doc_label_desc = QLabel("(GitHub 저장소 기준 상대 경로 또는 로컬 파일 경로)")
        doc_label_desc.setStyleSheet("color: #888; font-size: 8pt;")
        row5.addWidget(doc_label)
        row5.addWidget(doc_label_desc)
        
        doc_input_layout = QHBoxLayout()
        self.main_doc_input = QLineEdit()
        self.main_doc_input.setPlaceholderText("docs_2/NextTask-2.md")
        doc_input_layout.addWidget(self.main_doc_input)
        
        validate_doc_btn = QPushButton("검증")
        validate_doc_btn.clicked.connect(self.validate_main_document)
        doc_input_layout.addWidget(validate_doc_btn)
        
        find_doc_btn = QPushButton("찾기")
        find_doc_btn.clicked.connect(self.find_main_document_in_github)
        doc_input_layout.addWidget(find_doc_btn)
        row5.addLayout(doc_input_layout)
        github_layout.addLayout(row5)

        # 문서 검색 옵션
        doc_filter_layout = QHBoxLayout()
        doc_filter_layout.addWidget(QLabel("검색 옵션:"))
        self.docs2_filter_checkbox = QCheckBox("docs_2")
        self.docs2_filter_checkbox.setChecked(True)
        doc_filter_layout.addWidget(self.docs2_filter_checkbox)
        self.docs_filter_checkbox = QCheckBox("docs")
        self.docs_filter_checkbox.setChecked(False)
        doc_filter_layout.addWidget(self.docs_filter_checkbox)
        self.keyword_filter_checkbox = QCheckBox("키워드 필터 사용(NextTask/WPD/PRD/Task)")
        self.keyword_filter_checkbox.setChecked(True)
        doc_filter_layout.addWidget(self.keyword_filter_checkbox)
        doc_filter_layout.addStretch()
        github_layout.addLayout(doc_filter_layout)

        # 문서 검색 결과 리스트
        results_group = QGroupBox("문서 검색 결과")
        results_layout = QVBoxLayout()
        self.doc_results_list = QListWidget()
        self.doc_results_list.setMinimumHeight(120)
        self.doc_results_list.itemDoubleClicked.connect(self._on_document_double_clicked)
        results_layout.addWidget(self.doc_results_list)

        results_btn_layout = QHBoxLayout()
        apply_doc_btn = QPushButton("선택 적용")
        apply_doc_btn.clicked.connect(self._on_apply_button_clicked)
        results_btn_layout.addStretch()
        results_btn_layout.addWidget(apply_doc_btn)
        results_layout.addLayout(results_btn_layout)

        results_group.setLayout(results_layout)
        github_layout.addWidget(results_group)
        
        # 설정 저장 버튼
        save_config_btn = QPushButton("GitHub 설정 저장")
        save_config_btn.clicked.connect(self.save_github_config)
        github_layout.addWidget(save_config_btn)
        
        github_group.setLayout(github_layout)
        layout.addWidget(github_group)
        
        # Agent 설정 그룹
        config_group = QGroupBox("Agent 설정")
        config_layout = QVBoxLayout()
        
        # Agent 경로
        agent_layout = QHBoxLayout()
        agent_layout.addWidget(QLabel("Agent 경로:"))
        self.agent_path_input = QLineEdit(AGENT_PATH)
        self.agent_path_input.setReadOnly(True)
        agent_layout.addWidget(self.agent_path_input)
        browse_agent_btn = QPushButton("변경")
        browse_agent_btn.clicked.connect(self.browse_agent_path)
        agent_layout.addWidget(browse_agent_btn)
        config_layout.addLayout(agent_layout)
        
        # Redis URL
        redis_url_layout = QHBoxLayout()
        redis_url_layout.addWidget(QLabel("Redis URL:"))
        self.redis_url_input = QLineEdit(self.env_vars["REDIS_URL"])
        redis_url_layout.addWidget(self.redis_url_input)
        config_layout.addLayout(redis_url_layout)
        
        # 적용 버튼
        apply_env_btn = QPushButton("환경 변수 적용")
        apply_env_btn.clicked.connect(self.apply_env_vars)
        config_layout.addWidget(apply_env_btn)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 설정 로그 출력
        log_group = QGroupBox("설정 로그")
        log_layout = QVBoxLayout()
        self.settings_log_viewer = QTextEdit()
        self.settings_log_viewer.setReadOnly(True)
        self.settings_log_viewer.setStyleSheet(
            "background-color: #1e1e1e; color: #dcdcdc; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 9pt; padding: 5px;"
        )
        log_layout.addWidget(self.settings_log_viewer)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        self.github_tab.setLayout(layout)
    
    def init_server_tab(self):
        """서버 설정 탭 초기화"""
        layout = QVBoxLayout()
        
        # 추후 확장용
        placeholder = QLabel("서버 설정 옵션 (추후 추가 예정)")
        placeholder.setStyleSheet("color: #888; font-size: 12pt; padding: 50px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)
        
        self.server_tab.setLayout(layout)
    
    def show_token_help(self):
        """GitHub Token 도움말 표시"""
        dialog = GitHubTokenHelpDialog(self)
        dialog.exec()
    
    def on_token_changed(self, text):
        """GitHub Token 입력시 브랜치 활성화"""
        if text.strip():
            self.branch_combo.setEnabled(True)
        else:
            self.branch_combo.setEnabled(False)
    
    def connect_github_repo(self):
        """GitHub 저장소 연결 및 브랜치 조회"""
        repo_path = self.repo_input.text().strip()
        if not repo_path:
            self.log("저장소 경로를 입력하세요.")
            return
        
        self.log(f"[GitHub] 저장소 연결 시도: {repo_path}")
        
        if self.github_repo_config.parse_repository(repo_path):
            self.log(f"✓ GitHub 저장소 연결 성공: {self.github_repo_config.owner}/{self.github_repo_config.repo_name}")
            self.log(f"  타입: {self.github_repo_config.repo_type}")
            self.repo_info_label.setText(
                f"저장소: {self.github_repo_config.owner}/{self.github_repo_config.repo_name} "
                f"({self.github_repo_config.repo_type})"
            )
            
            # GitHub Token 설정
            token = self.github_token_input.text().strip()
            if token:
                self.github_repo_config.github_token = token
                self.log("[GitHub] Token 지원 API 호출 (제한: 60 -> 5000)")
            
            # 브랜치 목록 조회
            self.log("[GitHub] 활성 브랜치 조회 중...")
            self.log("  방법 1: GitHub API 시도...")
            branches = self.github_repo_config.fetch_available_branches(use_git=False)
            
            if not branches:
                self.log("  GitHub API 실패 - 대체 방법 시도")
                self.log("  방법 2: git ls-remote 명령어 시도...")
                branches = self.github_repo_config.fetch_available_branches(use_git=True)
            
            if branches:
                # 최근 5개만 표시
                top_branches = branches[:5]
                
                self.log(f"✓ 활성 브랜치 총 {len(branches)}개 발견 (최근 5개 표시):")
                for i, branch in enumerate(top_branches, 1):
                    self.log(f"  {i}. {branch}")
                
                if len(branches) > 5:
                    self.log(f"  ... 외 {len(branches) - 5}개 (직접 입력 가능)")
                
                # 브랜치 콤보박스 업데이트 (드롭다운 방식)
                self.branch_combo.blockSignals(True)
                self.branch_combo.clear()
                self.branch_combo.addItems(top_branches)
                self.branch_combo.setEnabled(True)
                
                # 현재 브랜치 선택 (시그널 활성화 전에 설정)
                if self.github_repo_config.branch in top_branches:
                    self.branch_combo.setCurrentText(self.github_repo_config.branch)
                else:
                    self.branch_combo.setCurrentText(top_branches[0])
                
                self.branch_combo.blockSignals(False)
                
                # 초기 브랜치 적용 (시그널 활성화 후 수동 호출)
                initial_branch = self.branch_combo.currentText()
                self.github_repo_config.set_branch(initial_branch)
                self.log(f"✓ 브랜치 선택 준비 완료: {initial_branch}")
                self.log("  팁: 다른 브랜치는 콤보박스에서 직접 입력할 수 있습니다")
            else:
                self.log("⚠ 경고: 브랜치를 조회할 수 없습니다")
                self.log("  해결책:")
                self.log("  1. GitHub Token을 입력하세요")
                self.log("  2. 또는 git을 설치하고 PATH에 추가하세요")
                self.log("  3. 또는 로컬 저장소 경로로 변경하세요")
                self.log("  임시 해결: 브랜치를 수동으로 입력할 수 있습니다")
                
                # 수동 입력 활성화
                self.branch_combo.setEnabled(True)
                self.branch_combo.setEditable(True)
                self.branch_combo.lineEdit().setText("main")
        else:
            self.log("✗ GitHub 저장소 연결 실패. 경로 형식을 확인하세요.")
            self.repo_info_label.setText("저장소: 연결 실패")
            self.branch_combo.setEnabled(False)
            self.branch_combo.clear()

    def on_branch_selected(self, branch_name: str):
        """브랜치 선택 시 호출되는 함수"""
        if not branch_name or not branch_name.strip():
            return
        
        branch_name = branch_name.strip()
        
        # github_repo_config에 브랜치 적용
        if self.github_repo_config.is_valid:
            self.github_repo_config.set_branch(branch_name)
            self.log(f"")
            self.log(f"============================================================")
            self.log(f"[브랜치 선택] {branch_name}")
            self.log(f"============================================================")
            
            # 전역 환경 변수에도 반영
            global GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH
            os.environ["GITHUB_BRANCH"] = branch_name
            
            # 메인 문서 경로가 있으면 자동 검증
            main_doc = self.main_doc_input.text().strip()
            if main_doc:
                self.log(f"✓ 메인 문서 자동 검증 시작: {main_doc}")
                self.validate_main_document()
        else:
            self.log(f"⚠ 브랜치 선택됨: {branch_name} (저장소 먼저 연결하세요)")


    def validate_main_document(self):
        """메인 문서 경로 검증 (자동 브랜치 폴백 포함)"""
        main_doc = self.main_doc_input.text().strip()
        
        if not main_doc:
            self.log("메인 문서 경로를 입력하세요.")
            return False
        
        if not self.github_repo_config.is_valid:
            self.log("GitHub 저장소를 먼저 연결하세요.")
            return False
        
        # 현재 선택된 브랜치 확인 (UI 우선)
        current_branch = self.branch_combo.currentText().strip()
        if not current_branch:
            current_branch = self.github_repo_config.branch
        
        self.log(f"")
        self.log(f"[검증 시작] 문서: {main_doc}")
        self.log(f"[검증] 선택된 브랜치: {current_branch}")
        
        # 시도할 브랜치 목록 (현재 → main → 기본 브랜치)
        branches_to_try = [current_branch]
        if "main" not in branches_to_try:
            branches_to_try.append("main")
        if self.github_repo_config.branch not in branches_to_try:
            branches_to_try.append(self.github_repo_config.branch)
        
        self.log(f"[검증] 브랜치별 순차 검색 시작...")
        
        # 브랜치별 순차 시도
        for branch in branches_to_try:
            raw_url = self.github_repo_config.get_raw_content_url(main_doc, branch)
            
            if not raw_url:
                self.log(f"  ✗ {branch}: URL 생성 실패")
                continue
            
            self.log(f"  시도 중: {branch}")
            
            try:
                import urllib.request
                import urllib.error
                
                request = urllib.request.Request(raw_url)
                request.add_header('User-Agent', 'Mozilla/5.0')
                
                # GitHub Token 인증 헤더 추가
                if self.github_repo_config.github_token:
                    request.add_header('Authorization', f'token {self.github_repo_config.github_token}')
                
                with urllib.request.urlopen(request, timeout=5) as response:
                    if response.status == 200:
                        content = response.read().decode('utf-8')
                        self.log(f"  ✓ 파일 발견! (브랜치: {branch}, 크기: {len(content)} bytes)")
                        
                        # 브랜치 자동 변경
                        if branch != current_branch:
                            self.branch_combo.setCurrentText(branch)
                            self.github_repo_config.set_branch(branch)
                            self.log(f"  ✓ 브랜치 자동 변경: {current_branch} → {branch}")
                        
                        self.log(f"")
                        self.log(f"✓✓✓ 검증 성공! ✓✓✓")
                        self.log(f"============================================================")
                        return True
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    self.log(f"  ✗ {branch}: 파일 없음 (404)")
                else:
                    self.log(f"  ✗ {branch}: HTTP {e.code}")
            except Exception as e:
                self.log(f"  ✗ {branch}: {str(e)}")
        
        # 모든 브랜치에서 실패
        self.log(f"")
        self.log(f"✗✗✗ 검증 실패 ✗✗✗")
        self.log(f"  시도한 브랜치: {', '.join(branches_to_try)}")
        self.log(f"  파일 경로: {main_doc}")
        self.log(f"")
        self.log(f"  해결책:")
        self.log(f"  1. '찾기' 버튼으로 전체 검색")
        self.log(f"  2. 브랜치를 수동으로 변경")
        self.log(f"  3. 파일 경로를 다시 확인")
        self.log(f"============================================================")
        return False
    
    def find_main_document_in_github(self):
        """GitHub 저장소에서 메인 문서 찾기"""
        if not self.github_repo_config.is_valid:
            self.log("GitHub 저장소를 먼저 연결하세요.")
            return
        
        current_branch = self.branch_combo.currentText() or self.github_repo_config.branch
        
        self.log(f"[GitHub] 문서 파일 검색 중 (브랜치: {current_branch})...")
        self.log("  마크다운 파일 찾기 (NextTask, WPD, PRD 등)...")
        
        try:
            import urllib.request
            import json
            
            # GitHub API: 트리 조회
            api_url = f"https://api.github.com/repos/{self.github_repo_config.owner}/{self.github_repo_config.repo_name}/git/trees/{current_branch}?recursive=1"
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            if self.github_repo_config.github_token:
                request.add_header('Authorization', f'token {self.github_repo_config.github_token}')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                tree_data = json.loads(response.read().decode('utf-8'))
                
                # 마크다운 파일 수집
                markdown_files = [
                    item['path']
                    for item in tree_data.get('tree', [])
                    if item.get('type') == 'blob' and item.get('path', '').endswith('.md')
                ]

                # 키워드 필터 적용
                if self.keyword_filter_checkbox.isChecked():
                    keywords = ['nexttask', 'wpd', 'prd', 'task']
                    markdown_files = [
                        path for path in markdown_files
                        if any(keyword in path.lower() for keyword in keywords)
                    ]

                # docs_2 / docs 필터 적용
                selected_prefixes = []
                if self.docs2_filter_checkbox.isChecked():
                    selected_prefixes.append('docs_2/')
                if self.docs_filter_checkbox.isChecked():
                    selected_prefixes.append('docs/')

                if selected_prefixes:
                    markdown_files = [
                        path for path in markdown_files
                        if any(path.startswith(prefix) for prefix in selected_prefixes)
                    ]
                
                # 결과 리스트 갱신
                self.doc_results_list.clear()

                if markdown_files:
                    for file_path in markdown_files:
                        self.doc_results_list.addItem(file_path)

                    self.log(f"\n✓ 발견된 문서 파일 ({len(markdown_files)}개)")

                    # 첫 번째 항목 기본 선택
                    first_file = markdown_files[0]
                    self.doc_results_list.setCurrentRow(0)
                    self.main_doc_input.setText(first_file)
                    self.log(f"✓ 기본 선택: {first_file}")
                    self.log("  리스트에서 다른 문서를 선택한 뒤 '선택 적용'을 누르세요")
                else:
                    self.log(f"✗ 마크다운 문서를 찾을 수 없습니다.")
                    self.log(f"  docs_2/ 디렉토리에 파일이 없을 수 있습니다.")
        
        except Exception as e:
            self.log(f"✗ 오류: {str(e)}")
            self.log(f"  수동으로 파일 경로를 입력하거나 GitHub Token을 확인하세요")

    def apply_selected_document(self, item=None):
        """검색 결과에서 선택한 문서를 메인 문서로 적용"""
        if item is None:
            item = self.doc_results_list.currentItem()

        if not item:
            self.log("선택된 문서가 없습니다.")
            return

        selected_path = item.text()
        self.main_doc_input.setText(selected_path)
        self.log(f"✓ 문서 선택됨: {selected_path}")

    def _on_document_double_clicked(self, item):
        """리스트 항목 더블클릭 이벤트 핸들러"""
        self.apply_selected_document(item)

    def _on_apply_button_clicked(self):
        """선택 적용 버튼 클릭 이벤트 핸들러"""
        # 통합: 선택 적용 + 설정 저장까지 수행
        self.save_github_config()
    
    def save_github_config(self):
        """GitHub 설정 저장"""
        # 문서 검색 결과에서 선택된 항목이 있으면 먼저 적용
        current_item = self.doc_results_list.currentItem() if self.doc_results_list else None
        if current_item is not None:
            selected_path = current_item.text().strip()
            if selected_path:
                self.main_doc_input.setText(selected_path)
                self.log(f"✓ 문서 선택됨(저장): {selected_path}")

        repo_path = self.repo_input.text().strip()
        main_doc = self.main_doc_input.text().strip()

        if not repo_path:
            self.log("저장소 경로가 비어 있습니다. 그래도 설정은 저장합니다.")

        if not main_doc:
            self.log("메인 문서 경로가 비어 있습니다. 그래도 설정은 저장합니다.")
        
        # 브랜치 설정 (UI에서 선택된 브랜치 우선)
        selected_branch = self.branch_combo.currentText().strip()
        if selected_branch:
            if self.github_repo_config.is_valid:
                self.github_repo_config.set_branch(selected_branch)
            self.log(f"  저장할 브랜치: {selected_branch}")
        else:
            self.log(f"  경고: 브랜치가 선택되지 않음")
        
        # Raw GitHub URL 생성
        raw_url = ""
        if self.github_repo_config.is_valid and main_doc:
            raw_url = self.github_repo_config.get_raw_content_url(main_doc)
            if not raw_url:
                self.log("Raw URL을 생성할 수 없습니다. 저장소 설정을 확인하세요.")
        
        # 설정 파일에 저장
        config = load_config(self.config_file)
        config["github_token"] = self.github_token_input.text().strip()
        config["workflow_secret"] = self.workflow_secret_input.text().strip()
        config["repo_path"] = repo_path
        config["main_doc"] = main_doc
        config["branch"] = selected_branch or self.github_repo_config.branch
        config["redis_url"] = self.redis_url_input.text().strip()
        config["agent_path"] = self.agent_path_input.text().strip()
        config["docs2_filter"] = self.docs2_filter_checkbox.isChecked()
        config["docs_filter"] = self.docs_filter_checkbox.isChecked()
        config["keyword_filter"] = self.keyword_filter_checkbox.isChecked()
        save_config(config, self.config_file)
        
        # 전역 변수 업데이트
        global GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH
        GITHUB_REPO_PATH = repo_path
        MAIN_DOCUMENT_PATH = main_doc
        
        self.log(f"✓ GitHub 설정 저장됨")
        self.log(f"  저장소: {repo_path}")
        self.log(f"  브랜치: {selected_branch or self.github_repo_config.branch}")
        self.log(f"  메인 문서: {main_doc}")
        if raw_url:
            self.log(f"  Raw GitHub URL: {raw_url}")
        self.log(f"  저장 위치: {self.config_file}")
    
    def browse_agent_path(self):
        """Agent 경로 변경"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "main_agent.py 파일 선택",
            str(Path(AGENT_PATH).parent),
            "Python Files (*.py)"
        )
        
        if file_path and file_path.endswith("main_agent.py"):
            self.agent_path_input.setText(file_path)
            self.parent_app.agent_path = file_path
            self.log(f"✓ Agent 경로 변경됨: {file_path}")
        elif file_path:
            self.log("✗ main_agent.py 파일을 선택하세요.")
    
    def apply_env_vars(self):
        """환경 변수 적용 및 저장"""
        # 환경 변수 업데이트
        self.env_vars["GITHUB_TOKEN"] = self.github_token_input.text().strip()
        self.env_vars["WORKFLOW_SHARED_SECRET"] = self.workflow_secret_input.text().strip()
        self.env_vars["REDIS_URL"] = self.redis_url_input.text().strip()
        
        # 시스템 환경 변수 설정
        os.environ["GITHUB_TOKEN"] = self.env_vars["GITHUB_TOKEN"]
        os.environ["WORKFLOW_SHARED_SECRET"] = self.env_vars["WORKFLOW_SHARED_SECRET"]
        os.environ["REDIS_URL"] = self.env_vars["REDIS_URL"]
        
        # 설정 파일에 저장
        config = load_config(self.config_file)
        config["github_token"] = self.env_vars["GITHUB_TOKEN"]
        config["workflow_secret"] = self.env_vars["WORKFLOW_SHARED_SECRET"]
        save_config(config, self.config_file)
        
        self.log("✓ 환경 변수 적용 및 저장됨")
        self.log(f"  저장 위치: {self.config_file}")
        
        # GitHub Token을 github_repo_config에도 적용
        if self.env_vars["GITHUB_TOKEN"]:
            self.github_repo_config.github_token = self.env_vars["GITHUB_TOKEN"]
            self.log("✓ GitHubReporter 활성화됨")
        else:
            self.log("⚠ GitHubReporter 비활성화됨 (토큰 없음)")
    
    def log(self, message: str):
        """로그 출력 (부모 앱의 로그 뷰어 사용)"""
        if hasattr(self, "settings_log_viewer") and self.settings_log_viewer is not None:
            self.settings_log_viewer.append(message)
        self.parent_app.log(message)

class MCPServerApp(QMainWindow):
    """MCP 서버 제어 GUI"""
    
    def __init__(self):
        super().__init__()
        self.server_thread = None
        self.current_port = None
        self.agent_path = AGENT_PATH
        self.github_repo_config = GitHubRepositoryConfig()
        self.config_file = CONFIG_FILE

        saved_config = load_config(self.config_file)
        self.env_vars = {
            "GITHUB_TOKEN": saved_config.get("github_token", os.getenv("GITHUB_TOKEN", "")),
            "WORKFLOW_SHARED_SECRET": saved_config.get("workflow_secret", os.getenv("WORKFLOW_SHARED_SECRET", "")),
            "REDIS_URL": os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
        }

        self.initUI()
        self.check_prerequisites()

    def initUI(self):
        """UI 초기화"""
        self.setWindowTitle("MCP Server Controller v1.0")
        self.setGeometry(100, 100, 900, 650)

        # 메뉴바
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("설정")
        settings_action = settings_menu.addAction("환경설정")
        settings_action.triggered.connect(self.show_settings_dialog)

        main_layout = QVBoxLayout()

        # === 로그 뷰어 ===
        log_group = QGroupBox("서버 로그")
        log_layout = QVBoxLayout()
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet(
            "background-color: #1e1e1e; color: #dcdcdc; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 10pt; padding: 5px;"
        )
        log_layout.addWidget(self.log_viewer)

        log_btn_layout = QHBoxLayout()
        clear_log_btn = QPushButton("로그 지우기")
        clear_log_btn.clicked.connect(self.log_viewer.clear)
        save_log_btn = QPushButton("로그 저장")
        save_log_btn.clicked.connect(self.save_log)
        log_btn_layout.addWidget(clear_log_btn)
        log_btn_layout.addWidget(save_log_btn)
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # === 명령 입력 ===
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Redis CLI:"))
        self.redis_cmd_input = QLineEdit("KEYS checkpoint:*")
        cmd_layout.addWidget(self.redis_cmd_input)
        run_cmd_btn = QPushButton("실행")
        run_cmd_btn.clicked.connect(self.run_redis_command)
        cmd_layout.addWidget(run_cmd_btn)
        main_layout.addLayout(cmd_layout)

        term_cmd_layout = QHBoxLayout()
        term_cmd_layout.addWidget(QLabel("터미널:"))
        self.terminal_cmd_input = QLineEdit("echo Hello World")
        term_cmd_layout.addWidget(self.terminal_cmd_input)
        run_term_btn = QPushButton("실행")
        run_term_btn.clicked.connect(self.run_terminal_command)
        term_cmd_layout.addWidget(run_term_btn)
        main_layout.addLayout(term_cmd_layout)

        agent_input_layout = QHBoxLayout()
        agent_input_layout.addWidget(QLabel("Agent 작업:"))
        self.agent_input = QLineEdit("Create a work plan for step 5")
        agent_input_layout.addWidget(self.agent_input)
        run_agent_btn = QPushButton("실행")
        run_agent_btn.clicked.connect(self.run_agent_test)
        agent_input_layout.addWidget(run_agent_btn)
        main_layout.addLayout(agent_input_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.statusBar().showMessage(f"로그 파일: {LOG_FILE}")

        # === 상태 그룹 ===
        status_group = QGroupBox("서버")
        status_layout = QHBoxLayout()

        status_left = QVBoxLayout()
        self.url_label = QLabel("서버 URL: 아직 시작되지 않음")
        self.url_label.setStyleSheet("color: #888; font-size: 10pt;")
        self.status_label = QLabel("● 서버 정지됨")
        self.status_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #FF6B6B;")
        status_left.addWidget(self.url_label)
        status_left.addWidget(self.status_label)

        status_right = QVBoxLayout()
        self.start_btn = QPushButton("🚀 서버 시작")
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-size: 12pt; padding: 10px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn = QPushButton("⏹ 서버 중지")
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; "
            "font-size: 12pt; padding: 10px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #da190b; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )

        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        status_right.addWidget(self.start_btn)
        status_right.addWidget(self.stop_btn)

        status_layout.addLayout(status_left)
        status_layout.addStretch()
        status_layout.addLayout(status_right)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

    def show_settings_dialog(self):
        """설정 다이얼로그 표시"""
        dialog = SettingsDialog(self, self.config_file, self.github_repo_config, self.env_vars)
        dialog.exec()

    def check_prerequisites(self):
        """사전 요구사항 확인"""
        self.log("\n[체크] 사전 요구사항 확인 중...")

        if check_redis_connection():
            self.log(" Redis 연결 정상")
        else:
            self.log(" Redis 연결 실패 (서버가 실행되지 않았거나 설정 오류)")

        if check_agent_path(self.agent_path):
            self.log(f"✓ Agent 파일 존재: {self.agent_path}")
        else:
            self.log(f"✗ Agent 파일 없음: {self.agent_path}")
            self.log("  → 환경설정에서 경로를 설정하세요")

    def start_server(self):
        """서버 시작"""
        self.log("\n" + "=" * 60)
        self.log("[시작] 서버 시작 중...")

        if not check_agent_path(self.agent_path):
            QMessageBox.critical(
                self,
                "오류",
                f"Agent 파일을 찾을 수 없습니다:\n{self.agent_path}\n\n경로를 다시 설정하세요."
            )
            return

        target_port = DEFAULT_PORT
        self.log(f" 고정 포트 {target_port} 사용")

        if not self._is_port_available(target_port):
            self.log(f" 포트 {target_port}가 사용 중입니다")
            QMessageBox.critical(self, "오류", f"포트 {target_port}가 이미 사용 중입니다.")
            return

        self.current_port = target_port
        self.server_thread = ServerThread(target_port, self.agent_path)
        self.server_thread.log_signal.connect(self.log)
        self.server_thread.error_signal.connect(self.log_error)
        self.server_thread.status_signal.connect(self.update_status)
        self.server_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.update_status(f"실행 중 (Port: {target_port})")

    def _is_port_available(self, port: int) -> bool:
        """포트 사용 가능 여부 확인"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((SERVER_HOST, port)) != 0

    def run_agent_test(self):
        """Agent 작업 실행"""
        user_input = self.agent_input.text().strip()
        if not user_input:
            self.log("Agent 작업을 입력하세요.")
            return
        self.log(f"[Agent] 실행: {user_input}")
        result = run_agent_command(user_input, self.agent_path, self.env_vars)
        self.log(f"[Agent 결과]\n{result}")

    def run_redis_command(self):
        """Redis CLI 명령 실행"""
        command = self.redis_cmd_input.text().strip()
        if not command:
            self.log("Redis 명령을 입력하세요.")
            return
        self.log(f"[Redis CLI] 실행: {command}")
        result = run_redis_cli_command(command)
        self.log(f"[Redis CLI 결과]\n{result}")

    def run_terminal_command(self):
        """터미널 명령 실행"""
        command = self.terminal_cmd_input.text().strip()
        if not command:
            self.log("터미널 명령을 입력하세요.")
            return
        self.log(f"[터미널] 실행: {command}")
        result = run_terminal_command(command)
        self.log(f"[터미널 결과]\n{result}")

    def stop_server(self):
        """서버 중지"""
        if self.server_thread and self.server_thread.isRunning():
            self.log("\n[중지] 서버 중지 중...")
            self.server_thread.stop()
            self.server_thread.wait(3000)
            if self.server_thread.isRunning():
                self.log(" 강제 종료")
                self.server_thread.terminate()
            else:
                self.log(" 정상 종료")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.update_status("서버 정지됨")
        self.current_port = None

    def log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self.log_viewer.append(formatted)
        logger.info(message)

    def log_error(self, message: str):
        """오류 로그"""
        self.log_viewer.append(f"<span style='color:#FF6B6B;'>{message}</span>")
        logger.error(message)

    def update_status(self, status: str):
        """상태 업데이트"""
        if "실행 중" in status:
            color = "#4CAF50"
            icon = "●"
        elif "초기화" in status:
            color = "#FFA726"
            icon = "◐"
        elif "오류" in status:
            color = "#FF6B6B"
            icon = "✗"
        else:
            color = "#888"
            icon = "○"

        self.status_label.setText(f"{icon} {status}")
        self.status_label.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; color: {color};"
        )

        if self.current_port:
            self.url_label.setText(f"서버 URL: http://localhost:{self.current_port}/")
        else:
            self.url_label.setText("서버 URL: 아직 시작되지 않음")

    def save_log(self):
        """로그 파일로 저장"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "로그 저장",
            str(LOG_DIR / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
            "Text Files (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_viewer.toPlainText())
                self.log(f"로그 저장됨: {file_path}")
            except Exception as e:
                self.log_error(f"로그 저장 실패: {e}")

    def closeEvent(self, event):
        """종료 시 서버 중지"""
        if self.server_thread and self.server_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "종료 확인",
                "서버가 실행 중입니다. 종료하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_server()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    try:
        logger.info("MCP Server GUI 시작")
        
        # PyQt6 애플리케이션
        app = QApplication(sys.argv)
        app.setApplicationName("MCP Server Controller")
        app.setOrganizationName("TurboSystem")
        
        # 메인 윈도우
        window = MCPServerApp()
        window.show()
        
        # 이벤트 루프 실행
        exit_code = app.exec()
        logger.info(f"애플리케이션 종료 (코드: {exit_code})")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"치명적 오류: {e}\n{traceback.format_exc()}")
        sys.exit(1)