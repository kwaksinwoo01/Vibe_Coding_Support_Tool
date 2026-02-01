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

# ============================================================================
# GitHub Repository Configuration
# ============================================================================
# Note: GitHubTokenHelpDialog has been moved to common/dialogs.py

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
# Server Thread (Core MCP Server)
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
            
            # RedisSaver 생성 (설정된 REDIS_URL 사용)
            # 환경 변수 REDIS_URL이 설정되어 있으면 우선 사용하고, 아니면 settings.constants.REDIS_URL을 사용합니다
            redis_url = os.getenv("REDIS_URL", REDIS_URL)
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
# Example Server Startup (for standalone usage)
# ============================================================================
# UI components (SettingsDialog, MCPServerApp) have been moved to:
# - vibeStation_monitor/main_window.py
# 
# To use this server core directly:
# 
# from MCP_server import ServerThread
# 
# server = ServerThread(port=8000, agent_path="/path/to/main_agent.py")
# server.log_signal.connect(lambda msg: print(msg))
# server.error_signal.connect(lambda msg: print(f"ERROR: {msg}"))
# server.status_signal.connect(lambda msg: print(f"STATUS: {msg}"))
# server.start()
# ============================================================================

if __name__ == "__main__":
    """
    Example standalone server startup (minimal UI-free version)
    For full GUI application, use vibeStation_monitor instead.
    """
    import sys
    from PyQt6.QtWidgets import QApplication
    
    try:
        logger.info("MCP Server Core - Standalone Mode")
        
        # Check prerequisites
        if not check_redis_connection():
            logger.error("Redis connection failed. Please start Redis server first.")
            sys.exit(1)
        
        if not check_agent_path(AGENT_PATH):
            logger.error(f"Agent path not found: {AGENT_PATH}")
            logger.info("Please update AGENT_PATH in this file or use the GUI version.")
            sys.exit(1)
        
        # Find available port
        port = find_available_port(DEFAULT_PORT, DEFAULT_PORT + 100)
        if not port:
            logger.error("No available ports found")
            sys.exit(1)
        
        logger.info(f"Starting server on port {port}...")
        logger.info("For full GUI application, please use vibeStation_monitor module.")
        
        # Create minimal QApplication for QThread
        app = QApplication(sys.argv)
        
        # Start server
        server = ServerThread(port=port, agent_path=AGENT_PATH)
        server.log_signal.connect(lambda msg: logger.info(msg))
        server.error_signal.connect(lambda msg: logger.error(msg))
        server.status_signal.connect(lambda msg: logger.info(f"Status: {msg}"))
        server.start()
        
        logger.info("Server started. Press Ctrl+C to stop.")
        logger.info(f"Server URL: http://{SERVER_HOST}:{port}")
        
        # Run event loop
        sys.exit(app.exec())
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}\n{traceback.format_exc()}")
        sys.exit(1)
