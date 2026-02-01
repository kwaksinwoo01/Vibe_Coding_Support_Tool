# settings/github_repository_config.py

"""
GitHub Repository Configuration
Configuration class for managing GitHub repository settings and API interactions.
"""

import os
import subprocess
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
