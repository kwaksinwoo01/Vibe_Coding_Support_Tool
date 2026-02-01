# ui/main_window.py

"""
main_window.py
↑
tep_dm.py, tep_mcp.py, tab_mcp_log.py 파일들을 통합하는 메인 윈도우 모듈
"""

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, QGroupBox, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

from .settings_dialog import SettingsDialog
from .tab_dm import TepDM
from .tep_mcp import TepMCP
from .tab_mcp_log import MCPLogTab
from mcp_suver.core.server_thread import ServerThread
from settings.config_manager import load_config, save_config, load_env_vars
from settings.github_repository_config import GitHubRepositoryConfig

class MainWindow(QMainWindow):
    """VibeStation UI 메인 윈도우"""
    
    def __init__(self, github_repo_config=None):
        super().__init__()
        
        # 저장소 설정 초기화
        self.github_repo_config = GitHubRepositoryConfig()
        
        # 설정 파일 경로
        config_dir = Path(__file__).parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        self.config_file = config_dir / "main_config.json"
        
        # 환경 변수 로드
        self.env_vars = load_env_vars(self.config_file)
        
        # 서버 스레드
        self.server_thread = None
        
        self.initUI()
        self.load_repository_config()
        self.setup_connections()
        self.start_server()
    
    def setup_connections(self):
        """탭 컴포넌트와 메인 윈도우 간 시그널/슬롯 연결"""
        # TepMCP 시그널 연결
        if hasattr(self, 'mcp_tab_ui'):
            self.mcp_tab_ui.server_started.connect(self.on_server_started)
            self.mcp_tab_ui.server_stopped.connect(self.on_server_stopped)
            self.mcp_tab_ui.status_changed.connect(self.on_tab_status_changed)
            self.mcp_tab_ui.log_message.connect(self.on_tab_log_message)
        
        # TepDM 시그널 연결
        if hasattr(self, 'dm_tab_ui'):
            self.dm_tab_ui.instructions_saved.connect(self.on_instructions_saved)
            self.dm_tab_ui.status_changed.connect(self.on_tab_status_changed)
    
    def on_server_started(self, port: int):
        """MCP 서버 시작됨 - TepMCP 탭에서 호출"""
        self.statusBar().showMessage(f"MCP 서버 시작됨 (포트: {port})")
    
    def on_server_stopped(self):
        """MCP 서버 중지됨 - TepMCP 탭에서 호출"""
        self.statusBar().showMessage("MCP 서버 중지됨")
    
    def on_tab_status_changed(self, status: str):
        """탭 상태 변경"""
        self.statusBar().showMessage(status)
    
    def on_tab_log_message(self, message: str):
        """탭에서 로그 메시지 수신"""
        # 로그 탭으로 메시지 전달
        if hasattr(self, 'mcp_log_ui'):
            self.mcp_log_ui.add_log('F', message, '완료')
    
    def on_instructions_saved(self, file_path: str):
        """Instructions 파일 저장됨"""
        self.statusBar().showMessage(f"Instructions 파일 저장됨: {file_path}")

    def initUI(self):
        """UI 초기화"""
        self.setWindowTitle("코딩에이전트 자동 문서관리 v1.0")
        self.setGeometry(100, 100, 1000, 700)

        # 메뉴바 - MainWindow에서만 생성 (SINGLE POINT OF MENUBAR CREATION)
        # 탭 컴포넌트에서는 menubar를 생성하지 않음
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("설정")
        settings_action = settings_menu.addAction("환경설정")
        settings_action.triggered.connect(self.show_settings_dialog)
        
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 탭 위젯
        self.tabs = QTabWidget()

        # 탭 1: MCP 로그 탭
        self.github_tab = QWidget()
        self.init_mcp_log_tab()
        self.tabs.addTab(self.github_tab, "로그 및 계획")

        # 탭 2: MCP 서버 탭
        self.server_tab = QWidget()
        self.init_mcp_tab()
        self.tabs.addTab(self.server_tab, "서버 설정")

        # 탭 3: 문서 관리 탭
        self.dm_tab = QWidget()
        self.init_dm_tab()
        self.tabs.addTab(self.dm_tab, "문서 관리")
        
        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def show_settings_dialog(self):
        """설정 다이얼로그 표시"""
        dialog = SettingsDialog(self, self.config_file, self.github_repo_config, self.env_vars)
        if dialog.exec():
            self.load_repository_config()

    def init_mcp_log_tab(self):
        """MCP 로그 탭 초기화"""
        layout = QVBoxLayout()
        self.mcp_log_ui = MCPLogTab(parent=self, github_repo_config=self.github_repo_config)
        layout.addWidget(self.mcp_log_ui)
        self.github_tab.setLayout(layout)

    def init_dm_tab(self):
        """문서 관리 탭 초기화"""
        layout = QVBoxLayout()
        self.dm_tab_ui = TepDM(self.config_file, self.github_repo_config, self.env_vars)
        layout.addWidget(self.dm_tab_ui)
        self.dm_tab.setLayout(layout)

    def init_mcp_tab(self):
        """MCP 서버 탭 초기화"""
        layout = QVBoxLayout()
        self.mcp_tab_ui = TepMCP(self.config_file, self.github_repo_config, self.env_vars)
        layout.addWidget(self.mcp_tab_ui)
        self.server_tab.setLayout(layout)

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
            
            # MCP 로그 탭에 저장소 설정 업데이트
            if hasattr(self, 'mcp_log_ui'):
                self.mcp_log_ui.set_repository_config(self.github_repo_config)

    def start_server(self):
        """MCP 서버 시작"""
        try:
            self.server_thread = ServerThread(port=18989)
            self.server_thread.received.connect(self.on_log_received)
            self.server_thread.log_signal.connect(self.on_server_log)
            self.server_thread.error_signal.connect(self.on_server_error)
            self.server_thread.status_signal.connect(self.on_server_status)
            self.server_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"서버 시작 실패: {str(e)}")
    
    def on_log_received(self, data: dict):
        """서버에서 로그 수신"""
        if hasattr(self, 'mcp_log_ui'):
            tier = data.get('tier', 'F')
            msg = data.get('msg', '')
            status = data.get('status', '완료')
            self.mcp_log_ui.add_log(tier, msg, status)
    
    def on_server_log(self, message: str):
        """서버 로그 수신"""
        if hasattr(self, 'mcp_log_ui'):
            # 로그 메시지에서 tier 자동 분류
            tier = 'F'
            if '[에러]' in message or 'ERROR' in message:
                tier = 'A'
            elif '[경고]' in message or 'WARNING' in message:
                tier = 'B'
            elif '[정보]' in message or 'INFO' in message:
                tier = 'C'
            
            self.mcp_log_ui.add_log(tier, message, '완료')
    
    def on_server_error(self, error: str):
        """서버 오류 수신"""
        if hasattr(self, 'mcp_log_ui'):
            self.mcp_log_ui.add_log('A', f"서버 오류: {error}", '실패')
    
    def on_server_status(self, status: str):
        """서버 상태 업데이트"""
        if hasattr(self, 'mcp_log_ui'):
            self.mcp_log_ui.update_agent_status(status)

    def log(self, message: str):
        """로그 메시지 처리 (SettingsDialog에서 호출됨)"""
        if hasattr(self, 'mcp_log_ui'):
            self.mcp_log_ui.add_log('F', message, '완료')

    def closeEvent(self, event):
        """윈도우 종료 이벤트 - 모든 서버 정리"""
        # MainWindow의 서버 스레드 정리
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()
            self.server_thread.wait()
        
        # TepMCP 탭의 서버 스레드도 정리
        if hasattr(self, 'mcp_tab_ui') and self.mcp_tab_ui.server_thread:
            if self.mcp_tab_ui.server_thread.isRunning():
                self.mcp_tab_ui.stop_server()
                self.mcp_tab_ui.server_thread.wait()
        
        event.accept()
