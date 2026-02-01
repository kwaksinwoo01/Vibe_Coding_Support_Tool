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

# Import UI components from mcp_suver and ui modules
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_suver"))
sys.path.insert(0, str(Path(__file__).parent.parent / "ui"))

from ui.settings_dialog import SettingsDialog
from settings_github_repository import GitHubRepositoryConfig

# ============================================================================
# Constants
# ============================================================================

AGENT_PATH = os.getenv("AGENT_PATH", r"C:\Users\user\Documents\github\turbo-system\.github\agents\tool\main_agent.py")

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
