# settings/github_repository_config.py

"""
GitHub Repository Configuration
Configuration class for managing GitHub repository settings and API interactions.
"""

import os
import httpx
import urllib.request
import json
    
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
                git_dir = self._resolve_git_dir(self.repo_path)
                if git_dir and os.path.isdir(git_dir):
                    # .git/config에서 origin URL 추출
                    url = self._read_origin_url(git_dir)
                    if url and "github.com" in url:
                        config = GitHubRepositoryConfig()
                        if config.parse_repository(url):
                            self.owner = config.owner
                            self.repo_name = config.repo_name
                            self.is_valid = True

                    # .git/HEAD에서 현재 브랜치 감지
                    head_branch = self._read_head_branch(git_dir)
                    if head_branch:
                        self.branch = head_branch

                    if self.is_valid:
                        return True
        
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
        """GitHub API로 활성 브랜치 목록 조회"""
        if not self.is_valid:
            return []

        # GitHub API 방식 시도 (토큰 없이도 제한 범위 내 호출)
        branches = self._fetch_branches_via_api()
        
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
                token_display = f"{self.github_token[:10]}...{self.github_token[-5:]}" if len(self.github_token) > 15 else "***"
                print(f"[GitHub API] Token 인증 시도: {token_display}")
                request.add_header('Authorization', f'token {self.github_token}')
            else:
                print(f"[GitHub API] ⚠ Token 없음 - API 제한: 60/시간")
            
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
            if e.code == 401:
                detail = ""
                try:
                    detail = e.read().decode("utf-8")
                except Exception:
                    detail = ""
                token_status = "있음 (값이 유효하지 않을 수 있음)" if self.github_token else "없음"
                print(f"[GitHub API] 401 Unauthorized - 토큰 인증 실패 (토큰: {token_status})")
                print(f"[GitHub API] 요청 URL: https://api.github.com/repos/{self.owner}/{self.repo_name}/branches")
                if detail:
                    print(f"[GitHub API] 상세 응답: {detail}")
                print(f"[GitHub API] ➜ 해결책:")
                print(f"     1. Token이 올바른지 확인: https://github.com/settings/tokens")
                print(f"     2. Token 권한 확인: 'repo' 또는 'public_repo' 스코프 필요")
                print(f"     3. Token이 만료되었을 수 있음")
                print(f"     4. Token 값이 완전히 복사되었는지 확인 (공백 제거)")
                return []
            if e.code == 403:
                print(f"[GitHub API] 403 Forbidden - API 제한 초과 (인증 토큰 필요)")
                return []
            elif e.code == 404:
                print(f"[GitHub API] 404 Not Found - 저장소를 찾을 수 없음")
                print(f"[GitHub API] 저장소: {self.owner}/{self.repo_name}")
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

    def _resolve_git_dir(self, repo_path: str) -> str:
        """.git 디렉터리 또는 gitdir 파일을 해석"""
        git_path = os.path.join(repo_path, ".git")
        if os.path.isdir(git_path):
            return git_path
        if os.path.isfile(git_path):
            try:
                with open(git_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                if content.startswith("gitdir:"):
                    rel_path = content.replace("gitdir:", "").strip()
                    resolved = os.path.abspath(os.path.join(repo_path, rel_path))
                    return resolved
            except Exception:
                return ""
        return ""

    def _read_origin_url(self, git_dir: str) -> str:
        """.git/config에서 origin URL 추출"""
        config_path = os.path.join(git_dir, "config")
        if not os.path.isfile(config_path):
            return ""

        current_section = ""
        try:
            with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("[") and stripped.endswith("]"):
                        current_section = stripped.strip("[]").strip()
                        continue
                    if current_section == 'remote "origin"' and stripped.startswith("url"):
                        _, value = stripped.split("=", 1)
                        return value.strip()
        except Exception:
            return ""

        return ""

    def _read_head_branch(self, git_dir: str) -> str:
        """.git/HEAD에서 현재 브랜치 추출"""
        head_path = os.path.join(git_dir, "HEAD")
        if not os.path.isfile(head_path):
            return ""
        try:
            with open(head_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            if content.startswith("ref:"):
                ref = content.replace("ref:", "").strip()
                if ref:
                    return ref.split("/")[-1]
        except Exception:
            return ""
        return ""
    
    def validate_token(self) -> bool:
        """GitHub Token 유효성 검사"""
        if not self.github_token:
            print("[Token 검증] ⚠ Token이 설정되지 않았습니다.")
            return False
        
        try:
            import urllib.request
            import urllib.error
            import json
            
            # GitHub API의 authenticated user endpoint 호출
            url = "https://api.github.com/user"
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            request.add_header('Authorization', f'token {self.github_token}')
            
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                login = data.get('login', 'Unknown')
                print(f"[Token 검증] ✓ Token 유효함! (로그인: {login})")
                return True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(f"[Token 검증] Token 인증 실패 (401 Unauthorized)")
                print(f"[Token 검증] Token이 유효하지 않거나 만료되었을 수 있습니다.")
                print(f"[Token 검증] 확인: https://github.com/settings/tokens")
            else:
                print(f"[Token 검증] HTTP 오류: {e.code}")
            return False
        except Exception as e:
            print(f"[Token 검증] 오류: {str(e)}")
            return False
    
    def set_and_validate_token(self, token: str) -> bool:
        """Token 설정 및 유효성 검사"""
        if not token or not token.strip():
            print("[Token] ⚠ Token이 비어있습니다.")
            return False
        
        self.github_token = token.strip()
        print(f"[Token] Token 설정됨 (길이: {len(self.github_token)})")
        return self.validate_token()

    def set_branch(self, branch_name: str) -> bool:
        """브랜치 설정"""
        if branch_name and branch_name.strip():
            self.branch = branch_name.strip()
        return True
