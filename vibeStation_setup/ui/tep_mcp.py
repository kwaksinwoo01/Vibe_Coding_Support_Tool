"""
MCP Server Tab - MCP 서버 제어 GUI 탭
This module provides the MCP server control interface as a tab widget.
"""

import sys
import os
import socket
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
import logging

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTextEdit, QLabel, QLineEdit, QMessageBox, QFileDialog, QGroupBox, QMainWindow)
from PyQt6.QtCore import Qt, pyqtSignal

from .settings_dialog import SettingsDialog
from mcp_suver.core.server_thread import ServerThread
from settings.github_repository_config import GitHubRepositoryConfig
from settings.config_manager import load_config, save_config, load_env_vars


from settings.constants import (
    AGENT_PATH, FAVICON_PATH, GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH,
    DEFAULT_PORT, SERVER_HOST,
    LOG_DIR, LOG_FILE, CONFIG_DIR, CONFIG_FILE
)

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ============================================================================
# Helper Functions
# ============================================================================

def run_terminal_command(command: str) -> str:
    """터미널 명령 실행"""
    try:
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================================
# MCP Server Tab
# ============================================================================


class TepMCP(QWidget):
    """MCP 서버 제어 탭 (QWidget)
    
    이 클래스는 MainWindow의 탭으로 사용됩니다.
    MainWindow에서 menubar와 window-level 설정을 관리합니다.
    """
    
    # Signals for parent window communication
    server_started = pyqtSignal(int)  # port
    server_stopped = pyqtSignal()
    status_changed = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self, config_file=None, github_repo_config=None, env_vars=None, parent=None):
        super().__init__(parent)
        # Accept configuration from parent window
        self.config_file = config_file if config_file else CONFIG_FILE
        self.github_repo_config = github_repo_config if github_repo_config else GitHubRepositoryConfig()
        self.env_vars = env_vars if env_vars else load_env_vars(self.config_file)
        
        self.server_thread = None
        self.current_port = None

        self.initUI()
        self.check_prerequisites()

    def initUI(self):
        """UI 초기화 - 탭 전용 컨텐츠만 포함"""
        # NO window-level calls: setWindowTitle, setGeometry, menuBar, statusBar
        # Tab components should only create their content layout
        
        main_layout = QVBoxLayout(self)

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

        # === 상태 그룹 ===
        # Moved here since we removed the container widget pattern
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
        
        # Set the layout for this widget (not setCentralWidget - that's for QMainWindow)
        self.setLayout(main_layout)

    def show_settings_dialog(self):
        """설정 다이얼로그 표시 - 부모 윈도우를 통해 호출되어야 함"""
        # This method should ideally be removed and handled by MainWindow
        # Keeping it for now but it should use self.parent() if needed
        if self.parent():
            parent_window = self.parent()
            while parent_window and not isinstance(parent_window, QMainWindow):
                parent_window = parent_window.parent()
            if parent_window:
                dialog = SettingsDialog(parent_window, self.config_file, self.github_repo_config, self.env_vars)
                dialog.exec()
        else:
            dialog = SettingsDialog(self, self.config_file, self.github_repo_config, self.env_vars)
            dialog.exec()

    def check_prerequisites(self):
        """사전 요구사항 확인"""
        self.log("\n[체크] 사전 요구사항 확인 중...")

        self.log("✓ Agent 모듈(main_agent.py) 번들링됨 (경로 확인 불필요)")

    def start_server(self):
        """서버 시작"""
        self.log("\n" + "=" * 60)
        self.log("[시작] 서버 시작 중...")

        target_port = DEFAULT_PORT
        self.log(f" 고정 포트 {target_port} 사용")

        if not self._is_port_available(target_port):
            self.log(f" 포트 {target_port}가 사용 중입니다")
            QMessageBox.critical(self, "오류", f"포트 {target_port}가 이미 사용 중입니다.")
            return

        self.current_port = target_port
        self.server_thread = ServerThread(target_port)
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
        """Agent 작업 실행 (main_agent.py 모듈 직접 사용)"""
        user_input = self.agent_input.text().strip()
        if not user_input:
            self.log("Agent 작업을 입력하세요.")
            return
        self.log(f"[Agent] 실행: {user_input}")
        result = subprocess.run(
            [sys.executable, "-m", "vibeStation_setup.mcp_suver.main_agent", user_input],
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout if result.stdout else result.stderr
        self.log(f"[Agent 결과]\n{output}")

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

    # closeEvent removed - window lifecycle managed by MainWindow
    # Server cleanup should be done through parent window signals
