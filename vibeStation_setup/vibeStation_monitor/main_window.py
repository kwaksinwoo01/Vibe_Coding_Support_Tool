"""
Monitor Module - Main Window
Consolidated UI components for the vibeStation monitor application.
This module contains the main application window and settings dialog for managing
GitHub repository connections, server configuration, and work plan monitoring.
"""
import sys
import os
import socket
import subprocess
import shutil
import json
import traceback
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QScrollArea,
                             QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLabel,
                             QLineEdit, QFileDialog, QGroupBox, QMessageBox, QComboBox, QDialog,
                             QTabWidget, QToolButton, QListWidget, QCheckBox, QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import QThread, pyqtSignal, QProcess, Qt
from PyQt6.QtGui import QFont, QIcon, QColor

# Import common components from the parent common module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.dialogs import GitHubTokenHelpDialog
from common.config_manager import load_config, save_config
from common.log_display import LogDisplayWidget
from common.server_thread import ServerThread as MonitorServerThread

# ============================================================================
# Constants
# ============================================================================

# Agent path - should be configured via environment variable or settings dialog
AGENT_PATH = os.getenv("AGENT_PATH", "")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

DEFAULT_PORT = 8001
SERVER_HOST = "127.0.0.1"

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

CONFIG_DIR = Path(__file__).parent / "config"
CONFIG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "monitor_config.json"

# ============================================================================
# GitHub Repository Configuration
# ============================================================================

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
        self.github_token = github_token
    
    def detect_repo_type(self, repo_path: str) -> str:
        """저장소 경로 타입 감지"""
        if not repo_path:
            return "unknown"
        
        repo_path = repo_path.strip()
        
        if repo_path.startswith(("https://github.com/", "http://github.com/")):
            return "https"
        
        if repo_path.startswith("git@github.com:"):
            return "ssh"
        
        parts = repo_path.split()
        clean_path = parts[-1] if parts else ""
        if "/" in clean_path and not clean_path.startswith(("http://", "https://", "git@")):
            return "cli"
        
        if os.path.isdir(repo_path):
            return "local"
        
        return "unknown"
    
    def parse_repository(self, repo_path: str) -> bool:
        """저장소 경로 파싱"""
        self.repo_path = repo_path.strip()
        self.repo_type = self.detect_repo_type(self.repo_path)
        
        try:
            if self.repo_type == "https":
                parts = self.repo_path.replace("https://", "").replace("http://", "")
                parts = parts.replace("github.com/", "").replace(".git", "")
                owner_repo = parts.split("/")
                if len(owner_repo) >= 2:
                    self.owner = owner_repo[0]
                    self.repo_name = owner_repo[1]
                    self.is_valid = True
                    return True
            
            elif self.repo_type == "ssh":
                parts = self.repo_path.replace("git@github.com:", "").replace(".git", "")
                owner_repo = parts.split("/")
                if len(owner_repo) == 2:
                    self.owner = owner_repo[0]
                    self.repo_name = owner_repo[1]
                    self.is_valid = True
                    return True
            
            elif self.repo_type == "cli":
                parts = self.repo_path.split()
                clean_path = parts[-1] if parts else ""
                owner_repo = clean_path.split("/")
                if len(owner_repo) >= 2:
                    self.owner = owner_repo[0]
                    self.repo_name = owner_repo[1]
                    self.is_valid = True
                    return True
            
            elif self.repo_type == "local":
                git_dir = os.path.join(self.repo_path, ".git")
                if os.path.isdir(git_dir):
                    result = subprocess.run(
                        ["git", "-C", self.repo_path, "remote", "-v"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split("\n"):
                            if "origin" in line:
                                parts = line.split()
                                if len(parts) >= 2:
                                    url = parts[1]
                                    # Only process GitHub URLs
                                    if url.startswith(("https://github.com/", "http://github.com/", "git@github.com:")):
                                        config = GitHubRepositoryConfig()
                                        if config.parse_repository(url):
                                            self.owner = config.owner
                                            self.repo_name = config.repo_name
                                            self.branch = config.branch
                                            self.is_valid = True
                                            return True
                    
                    result = subprocess.run(
                        ["git", "-C", self.repo_path, "symbolic-ref", "refs/remotes/origin/HEAD"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        branch_ref = result.stdout.strip()
                        if "/" in branch_ref:
                            self.branch = branch_ref.split("/")[-1]
        
        except Exception as e:
            self.is_valid = False
            return False
        
        self.is_valid = False
        return False
    
    def get_raw_content_url(self, file_path: str, branch: str = "") -> str:
        """GitHub Raw Content URL 생성"""
        if not self.is_valid:
            return ""
        
        branch = branch or self.branch
        file_path = file_path.replace("\\", "/").strip()
        
        return f"https://raw.githubusercontent.com/{self.owner}/{self.repo_name}/{branch}/{file_path}"

    def get_web_url(self, file_path: str, branch: str = "") -> str:
        """GitHub Web URL 생성"""
        if not self.is_valid:
            return ""
        
        if not branch:
            branch = self.branch
        
        file_path = file_path.replace("\\", "/").strip()
        
        return f"https://github.com/{self.owner}/{self.repo_name}/blob/{branch}/{file_path}"
    
    def detect_default_branch(self) -> str:
        """GitHub API로 기본 브랜치 감지"""
        if not self.is_valid:
            return "main"
        
        try:
            url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(request, timeout=5) as response:
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
        
        if use_git or self.repo_type == "local":
            return self._fetch_branches_via_git()
        
        branches = self._fetch_branches_via_api()
        if not branches:
            branches = self._fetch_branches_via_git()
        
        return branches
    
    def _fetch_branches_via_api(self) -> list:
        """GitHub API를 통한 브랜치 조회"""
        try:
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/branches?per_page=100"
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            if self.github_token:
                request.add_header('Authorization', f'token {self.github_token}')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                branches_data = json.loads(response.read().decode('utf-8'))
                
                branches_with_date = []
                for branch in branches_data:
                    if isinstance(branch, dict) and 'name' in branch:
                        try:
                            commit_date = branch.get('commit', {}).get('commit', {}).get('committer', {}).get('date', '')
                            branches_with_date.append({
                                'name': branch['name'],
                                'date': commit_date
                            })
                        except Exception:
                            branches_with_date.append({
                                'name': branch['name'],
                                'date': '0000-00-00T00:00:00Z'
                            })
                
                branches_with_date.sort(key=lambda x: x['date'], reverse=True)
                
                active_branches = [b['name'] for b in branches_with_date]
                
                if self.branch in active_branches:
                    active_branches.remove(self.branch)
                    active_branches.insert(0, self.branch)
                
                self.available_branches = sorted(active_branches)
                return self.available_branches
                
        except urllib.error.HTTPError as e:
            return []
        except Exception as e:
            return []

    def _fetch_branches_via_git(self) -> list:
        """git 명령어를 통한 브랜치 조회"""
        try:
            branches_with_date = []
            
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
                    
                    seen = set()
                    unique_branches = []
                    for b in branches_with_date:
                        if b['name'] not in seen:
                            seen.add(b['name'])
                            unique_branches.append(b)
                    
                    branches = [b['name'] for b in unique_branches]
                    self.available_branches = sorted(list(set(branches)))
                    return self.available_branches
            
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
                            parts = line.split("/")
                            if len(parts) >= 3:
                                branch = parts[-1]
                                branches.append(branch)
                    
                    self.available_branches = sorted(list(set(branches)))
                    return self.available_branches
        
        except Exception as e:
            return []
        
        return []
    
    def set_branch(self, branch_name: str):
        """브랜치 설정"""
        if branch_name:
            self.branch = branch_name
        return True


# ============================================================================
# Settings Dialog
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
        
        main_layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        self.github_tab = QWidget()
        self.init_github_tab()
        self.tabs.addTab(self.github_tab, "GitHub 저장소 연결")
        
        self.server_tab = QWidget()
        self.init_server_tab()
        self.tabs.addTab(self.server_tab, "서버 설정")
        
        main_layout.addWidget(self.tabs)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
        
        self.load_saved_settings()
    
    def load_saved_settings(self):
        """저장된 설정 로드"""
        saved_config = load_config(self.config_file)
        
        if "github_token" in saved_config:
            self.github_token_input.setText(saved_config["github_token"])
        
        if "workflow_secret" in saved_config:
            self.workflow_secret_input.setText(saved_config["workflow_secret"])
        
        if "repo_path" in saved_config:
            self.repo_input.setText(saved_config["repo_path"])
        
        if "main_doc" in saved_config:
            self.main_doc_input.setText(saved_config["main_doc"])
        
        if "branch" in saved_config:
            self.branch_combo.setCurrentText(saved_config["branch"])

        if "redis_url" in saved_config:
            self.redis_url_input.setText(saved_config["redis_url"])

        if "agent_path" in saved_config:
            self.agent_path_input.setText(saved_config["agent_path"])

        if "docs2_filter" in saved_config:
            self.docs2_filter_checkbox.setChecked(bool(saved_config["docs2_filter"]))
        if "docs_filter" in saved_config:
            self.docs_filter_checkbox.setChecked(bool(saved_config["docs_filter"]))
        if "keyword_filter" in saved_config:
            self.keyword_filter_checkbox.setChecked(bool(saved_config["keyword_filter"]))
    
    def init_github_tab(self):
        """GitHub 저장소 연결 탭 초기화"""
        layout = QVBoxLayout()
        
        github_group = QGroupBox("GitHub 저장소 설정")
        github_layout = QVBoxLayout()
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("저장소 경로:"))
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("https://github.com/owner/repo.git")
        row1.addWidget(self.repo_input)
        detect_repo_btn = QPushButton("연결")
        detect_repo_btn.clicked.connect(self.connect_github_repo)
        row1.addWidget(detect_repo_btn)
        github_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("GitHub Token:"))
        self.github_token_input = QLineEdit()
        self.github_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.github_token_input.setPlaceholderText("ghp_...")
        self.github_token_input.textChanged.connect(self.on_token_changed)
        row2.addWidget(self.github_token_input)
        
        help_btn = QToolButton()
        help_btn.setText("?")
        help_btn.clicked.connect(self.show_token_help)
        row2.addWidget(help_btn)
        github_layout.addLayout(row2)
        
        self.repo_info_label = QLabel("저장소: 연결 안됨")
        self.repo_info_label.setStyleSheet("color: #888; font-size: 9pt;")
        github_layout.addWidget(self.repo_info_label)
        
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Workflow Secret:"))
        self.workflow_secret_input = QLineEdit()
        self.workflow_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        row3.addWidget(self.workflow_secret_input)
        github_layout.addLayout(row3)
        
        row4 = QVBoxLayout()
        branch_label = QLabel("브랜치:")
        branch_label_desc = QLabel("(최근 커밋순 | GitHub Token 필요)")
        branch_label_desc.setStyleSheet("color: #888; font-size: 8pt;")
        row4.addWidget(branch_label)
        row4.addWidget(branch_label_desc)
        
        self.branch_combo = QComboBox()
        self.branch_combo.setEnabled(False)
        self.branch_combo.setEditable(True)
        
        self.branch_combo.currentTextChanged.connect(self.on_branch_selected)
        
        row4.addWidget(self.branch_combo)
        github_layout.addLayout(row4)

        
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
        
        save_config_btn = QPushButton("GitHub 설정 저장")
        save_config_btn.clicked.connect(self.save_github_config)
        github_layout.addWidget(save_config_btn)
        
        github_group.setLayout(github_layout)
        layout.addWidget(github_group)
        
        config_group = QGroupBox("Agent 설정")
        config_layout = QVBoxLayout()
        
        agent_layout = QHBoxLayout()
        agent_layout.addWidget(QLabel("Agent 경로:"))
        self.agent_path_input = QLineEdit(AGENT_PATH)
        self.agent_path_input.setReadOnly(True)
        agent_layout.addWidget(self.agent_path_input)
        browse_agent_btn = QPushButton("변경")
        browse_agent_btn.clicked.connect(self.browse_agent_path)
        agent_layout.addWidget(browse_agent_btn)
        config_layout.addLayout(agent_layout)
        
        redis_url_layout = QHBoxLayout()
        redis_url_layout.addWidget(QLabel("Redis URL:"))
        self.redis_url_input = QLineEdit(self.env_vars.get("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"))
        redis_url_layout.addWidget(self.redis_url_input)
        config_layout.addLayout(redis_url_layout)
        
        apply_env_btn = QPushButton("환경 변수 적용")
        apply_env_btn.clicked.connect(self.apply_env_vars)
        config_layout.addWidget(apply_env_btn)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

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
            
            token = self.github_token_input.text().strip()
            if token:
                self.github_repo_config.github_token = token
                self.log("[GitHub] Token 지원 API 호출 (제한: 60 -> 5000)")
            
            self.log("[GitHub] 활성 브랜치 조회 중...")
            self.log("  방법 1: GitHub API 시도...")
            branches = self.github_repo_config.fetch_available_branches(use_git=False)
            
            if not branches:
                self.log("  GitHub API 실패 - 대체 방법 시도")
                self.log("  방법 2: git ls-remote 명령어 시도...")
                branches = self.github_repo_config.fetch_available_branches(use_git=True)
            
            if branches:
                top_branches = branches[:5]
                
                self.log(f"✓ 활성 브랜치 총 {len(branches)}개 발견 (최근 5개 표시):")
                for i, branch in enumerate(top_branches, 1):
                    self.log(f"  {i}. {branch}")
                
                if len(branches) > 5:
                    self.log(f"  ... 외 {len(branches) - 5}개 (직접 입력 가능)")
                
                self.branch_combo.blockSignals(True)
                self.branch_combo.clear()
                self.branch_combo.addItems(top_branches)
                self.branch_combo.setEnabled(True)
                
                if self.github_repo_config.branch in top_branches:
                    self.branch_combo.setCurrentText(self.github_repo_config.branch)
                else:
                    self.branch_combo.setCurrentText(top_branches[0])
                
                self.branch_combo.blockSignals(False)
                
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
        
        if self.github_repo_config.is_valid:
            self.github_repo_config.set_branch(branch_name)
            self.log(f"============================================================")
            self.log(f"[브랜치 선택] {branch_name}")
            self.log(f"============================================================")
            
            os.environ["GITHUB_BRANCH"] = branch_name
            
            main_doc = self.main_doc_input.text().strip()
            if main_doc:
                self.log(f"✓ 메인 문서 자동 검증 시작: {main_doc}")
                self.validate_main_document()
        else:
            self.log(f"⚠ 브랜치 선택됨: {branch_name} (저장소 먼저 연결하세요)")


    def validate_main_document(self):
        """메인 문서 경로 검증"""
        main_doc = self.main_doc_input.text().strip()
        
        if not main_doc:
            self.log("메인 문서 경로를 입력하세요.")
            return False
        
        if not self.github_repo_config.is_valid:
            self.log("GitHub 저장소를 먼저 연결하세요.")
            return False
        
        current_branch = self.branch_combo.currentText().strip()
        if not current_branch:
            current_branch = self.github_repo_config.branch
        
        self.log("=" * 60)
        self.log(f"[검증 시작] 문서: {main_doc}")
        self.log(f"[검증] 선택된 브랜치: {current_branch}")
        
        branches_to_try = [current_branch]
        if "main" not in branches_to_try:
            branches_to_try.append("main")
        if self.github_repo_config.branch not in branches_to_try:
            branches_to_try.append(self.github_repo_config.branch)
        
        self.log(f"[검증] 브랜치별 순차 검색 시작...")
        
        for branch in branches_to_try:
            raw_url = self.github_repo_config.get_raw_content_url(main_doc, branch)
            
            if not raw_url:
                self.log(f"  ✗ {branch}: URL 생성 실패")
                continue
            
            self.log(f"  시도 중: {branch}")
            
            try:
                request = urllib.request.Request(raw_url)
                request.add_header('User-Agent', 'Mozilla/5.0')
                
                if self.github_repo_config.github_token:
                    request.add_header('Authorization', f'token {self.github_repo_config.github_token}')
                
                with urllib.request.urlopen(request, timeout=5) as response:
                    if response.status == 200:
                        content = response.read().decode('utf-8')
                        self.log(f"  ✓ 파일 발견! (브랜치: {branch}, 크기: {len(content)} bytes)")
                        
                        if branch != current_branch:
                            self.branch_combo.setCurrentText(branch)
                            self.github_repo_config.set_branch(branch)
                            self.log(f"  ✓ 브랜치 자동 변경: {current_branch} → {branch}")
                        
                        self.log("=" * 60)
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
        
        self.log("=" * 60)
        self.log(f"✗✗✗ 검증 실패 ✗✗✗")
        self.log(f"  시도한 브랜치: {', '.join(branches_to_try)}")
        self.log(f"  파일 경로: {main_doc}")
        self.log("=" * 60)
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
            api_url = f"https://api.github.com/repos/{self.github_repo_config.owner}/{self.github_repo_config.repo_name}/git/trees/{current_branch}?recursive=1"
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            if self.github_repo_config.github_token:
                request.add_header('Authorization', f'token {self.github_repo_config.github_token}')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                tree_data = json.loads(response.read().decode('utf-8'))
                
                markdown_files = [
                    item['path']
                    for item in tree_data.get('tree', [])
                    if item.get('type') == 'blob' and item.get('path', '').endswith('.md')
                ]

                if self.keyword_filter_checkbox.isChecked():
                    keywords = ['nexttask', 'wpd', 'prd', 'task']
                    markdown_files = [
                        path for path in markdown_files
                        if any(keyword in path.lower() for keyword in keywords)
                    ]

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
                
                self.doc_results_list.clear()

                if markdown_files:
                    for file_path in markdown_files:
                        self.doc_results_list.addItem(file_path)

                    self.log(f"\n✓ 발견된 문서 파일 ({len(markdown_files)}개)")

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
        self.save_github_config()
    
    def save_github_config(self):
        """GitHub 설정 저장"""
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
        
        selected_branch = self.branch_combo.currentText().strip()
        if selected_branch:
            if self.github_repo_config.is_valid:
                self.github_repo_config.set_branch(selected_branch)
            self.log(f"  저장할 브랜치: {selected_branch}")
        else:
            self.log(f"  경고: 브랜치가 선택되지 않음")
        
        raw_url = ""
        if self.github_repo_config.is_valid and main_doc:
            raw_url = self.github_repo_config.get_raw_content_url(main_doc)
            if not raw_url:
                self.log("Raw URL을 생성할 수 없습니다. 저장소 설정을 확인하세요.")
        
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
        self.env_vars["GITHUB_TOKEN"] = self.github_token_input.text().strip()
        self.env_vars["WORKFLOW_SHARED_SECRET"] = self.workflow_secret_input.text().strip()
        self.env_vars["REDIS_URL"] = self.redis_url_input.text().strip()
        
        os.environ["GITHUB_TOKEN"] = self.env_vars["GITHUB_TOKEN"]
        os.environ["WORKFLOW_SHARED_SECRET"] = self.env_vars["WORKFLOW_SHARED_SECRET"]
        os.environ["REDIS_URL"] = self.env_vars["REDIS_URL"]
        
        config = load_config(self.config_file)
        config["github_token"] = self.env_vars["GITHUB_TOKEN"]
        config["workflow_secret"] = self.env_vars["WORKFLOW_SHARED_SECRET"]
        save_config(config, self.config_file)
        
        self.log("✓ 환경 변수 적용 및 저장됨")
        self.log(f"  저장 위치: {self.config_file}")
        
        if self.env_vars["GITHUB_TOKEN"]:
            self.github_repo_config.github_token = self.env_vars["GITHUB_TOKEN"]
            self.log("✓ GitHubReporter 활성화됨")
        else:
            self.log("⚠ GitHubReporter 비활성화됨 (토큰 없음)")
    
    def log(self, message: str):
        """로그 출력"""
        if hasattr(self, "settings_log_viewer") and self.settings_log_viewer is not None:
            self.settings_log_viewer.append(message)
        self.parent_app.log(message)


# ============================================================================
# VibeStation Monitor Main Window
# ============================================================================

class VibeStationMonitor(QMainWindow):
    """VibeStation 모니터 GUI (작업 계획 모니터링 전용)"""
    
    def __init__(self):
        super().__init__()
        self.github_repo_config = GitHubRepositoryConfig()
        self.config_file = CONFIG_FILE
        
        saved_config = load_config(self.config_file)
        self.env_vars = {
            "GITHUB_TOKEN": saved_config.get("github_token", os.getenv("GITHUB_TOKEN", "")),
            "WORKFLOW_SHARED_SECRET": saved_config.get("workflow_secret", os.getenv("WORKFLOW_SHARED_SECRET", "")),
            "REDIS_URL": os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
        }
        
        self.initUI()
        self.load_repository_config()
    
    def initUI(self):
        """UI 초기화"""
        self.setWindowTitle("VibeStation Monitor v1.0")
        self.setGeometry(100, 100, 1000, 700)
        
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("설정")
        settings_action = settings_menu.addAction("환경설정")
        settings_action.triggered.connect(self.show_settings_dialog)
        
        main_layout = QVBoxLayout()
        
        # 저장소 정보 표시
        repo_group = QGroupBox("GitHub 저장소 정보")
        repo_layout = QVBoxLayout()
        self.repo_info_label = QLabel("저장소: 설정되지 않음")
        self.repo_info_label.setStyleSheet("font-size: 10pt; color: #888;")
        repo_layout.addWidget(self.repo_info_label)
        repo_group.setLayout(repo_layout)
        main_layout.addWidget(repo_group)
        
        # 탭 위젯
        self.tabs = QTabWidget()
        
        # 탭 1: 작업 계획 목록
        self.plan_tab = QWidget()
        self.init_plan_tab()
        self.tabs.addTab(self.plan_tab, "작업 계획 목록")
        
        # 탭 2: 로그 뷰어
        self.log_tab = QWidget()
        self.init_log_tab()
        self.tabs.addTab(self.log_tab, "로그")
        
        main_layout.addWidget(self.tabs)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        self.statusBar().showMessage("준비됨")
    
    def init_plan_tab(self):
        """작업 계획 탭 초기화"""
        layout = QVBoxLayout()
        
        # 작업 계획 테이블
        plan_group = QGroupBox("작업 계획 문서")
        plan_layout = QVBoxLayout()
        
        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(4)
        self.plan_table.setHorizontalHeaderLabels(["파일명", "경로", "브랜치", "상태"])
        self.plan_table.horizontalHeader().setStretchLastSection(True)
        self.plan_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        plan_layout.addWidget(self.plan_table)
        
        # 버튼
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.refresh_plan_list)
        btn_layout.addWidget(refresh_btn)
        
        open_btn = QPushButton("GitHub에서 열기")
        open_btn.clicked.connect(self.open_selected_in_github)
        btn_layout.addWidget(open_btn)
        
        btn_layout.addStretch()
        plan_layout.addLayout(btn_layout)
        
        plan_group.setLayout(plan_layout)
        layout.addWidget(plan_group)
        
        self.plan_tab.setLayout(layout)
    
    def init_log_tab(self):
        """로그 탭 초기화"""
        layout = QVBoxLayout()
        
        log_group = QGroupBox("시스템 로그")
        log_layout = QVBoxLayout()
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet(
            "background-color: #1e1e1e; color: #dcdcdc; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 10pt; padding: 5px;"
        )
        log_layout.addWidget(self.log_viewer)
        
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("로그 지우기")
        clear_btn.clicked.connect(self.log_viewer.clear)
        btn_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("로그 저장")
        save_btn.clicked.connect(self.save_log)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        log_layout.addLayout(btn_layout)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.log_tab.setLayout(layout)
    
    def show_settings_dialog(self):
        """설정 다이얼로그 표시"""
        dialog = SettingsDialog(self, self.config_file, self.github_repo_config, self.env_vars)
        if dialog.exec():
            self.load_repository_config()
    
    def load_repository_config(self):
        """저장된 저장소 설정 로드"""
        saved_config = load_config(self.config_file)
        
        repo_path = saved_config.get("repo_path", "")
        if repo_path and self.github_repo_config.parse_repository(repo_path):
            branch = saved_config.get("branch", "main")
            self.github_repo_config.set_branch(branch)
            
            token = saved_config.get("github_token", "")
            if token:
                self.github_repo_config.github_token = token
            
            self.repo_info_label.setText(
                f"저장소: {self.github_repo_config.owner}/{self.github_repo_config.repo_name} "
                f"(브랜치: {self.github_repo_config.branch})"
            )
            self.log(f"저장소 설정 로드됨: {self.github_repo_config.owner}/{self.github_repo_config.repo_name}")
            
            # 작업 계획 목록 자동 로드
            self.refresh_plan_list()
        else:
            self.repo_info_label.setText("저장소: 설정되지 않음 (환경설정에서 연결하세요)")
            self.log("저장소가 설정되지 않았습니다.")
    
    def refresh_plan_list(self):
        """작업 계획 목록 새로고침"""
        if not self.github_repo_config.is_valid:
            self.log("GitHub 저장소를 먼저 설정하세요.")
            QMessageBox.warning(self, "경고", "GitHub 저장소를 먼저 설정하세요.")
            return
        
        self.log("작업 계획 문서 검색 중...")
        
        try:
            api_url = f"https://api.github.com/repos/{self.github_repo_config.owner}/{self.github_repo_config.repo_name}/git/trees/{self.github_repo_config.branch}?recursive=1"
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            if self.github_repo_config.github_token:
                request.add_header('Authorization', f'token {self.github_repo_config.github_token}')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                tree_data = json.loads(response.read().decode('utf-8'))
                
                # docs/wp 폴더의 마크다운 파일만 필터링
                plan_files = [
                    item['path']
                    for item in tree_data.get('tree', [])
                    if item.get('type') == 'blob' and 
                       item.get('path', '').endswith('.md') and
                       'docs/wp' in item.get('path', '')
                ]
                
                # 테이블 업데이트
                self.plan_table.setRowCount(0)
                for file_path in plan_files:
                    row = self.plan_table.rowCount()
                    self.plan_table.insertRow(row)
                    
                    file_name = file_path.split('/')[-1]
                    self.plan_table.setItem(row, 0, QTableWidgetItem(file_name))
                    self.plan_table.setItem(row, 1, QTableWidgetItem(file_path))
                    self.plan_table.setItem(row, 2, QTableWidgetItem(self.github_repo_config.branch))
                    self.plan_table.setItem(row, 3, QTableWidgetItem("활성"))
                
                self.log(f"✓ 작업 계획 문서 {len(plan_files)}개 발견")
                
        except Exception as e:
            self.log(f"✗ 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"작업 계획 목록을 가져올 수 없습니다:\n{str(e)}")
    
    def open_selected_in_github(self):
        """선택한 파일을 GitHub에서 열기"""
        selected_row = self.plan_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "경고", "파일을 먼저 선택하세요.")
            return
        
        file_path = self.plan_table.item(selected_row, 1).text()
        web_url = self.github_repo_config.get_web_url(file_path)
        
        if web_url:
            import webbrowser
            webbrowser.open(web_url)
            self.log(f"GitHub에서 열기: {file_path}")
        else:
            QMessageBox.warning(self, "경고", "URL을 생성할 수 없습니다.")
    
    def save_log(self):
        """로그 저장"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "로그 저장",
            str(LOG_DIR / f"monitor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
            "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_viewer.toPlainText())
                self.log(f"✓ 로그 저장됨: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"로그 저장 실패:\n{str(e)}")
    
    def log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_viewer.append(f"[{timestamp}] {message}")


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("VibeStation Monitor")
        app.setOrganizationName("VibeStation")
        
        window = VibeStationMonitor()
        window.show()
        
        exit_code = app.exec()
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
