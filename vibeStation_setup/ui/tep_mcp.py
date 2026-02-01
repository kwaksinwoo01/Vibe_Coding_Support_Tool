"""
MCP Server Window - MCP 서버 제어 GUI 메인 윈도우
"""

import sys
import os
import socket
import traceback
from datetime import datetime
from pathlib import Path
import logging

from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTextEdit, QLabel, QLineEdit, QMessageBox, QFileDialog, QGroupBox)
from PyQt6.QtCore import Qt

from .settings_dialog import SettingsDialog
from mcp_suver.core.server_thread import ServerThread
from settings.github_repository_config import GitHubRepositoryConfig
from settings.config_manager import load_config, save_config, load_env_vars


from settings.constants import (
    AGENT_PATH, FAVICON_PATH, GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH,
    REDIS_HOST, REDIS_PORT, REDIS_DB, DEFAULT_PORT, SERVER_HOST,
    LOG_DIR, LOG_FILE, CONFIG_DIR, CONFIG_FILE
)

# ============================================================================
# MCP Server Window
# ============================================================================


class TepMCP(QMainWindow):
    """MCP 서버 제어 GUI 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.server_thread = None
        self.current_port = None
        self.agent_path = AGENT_PATH
        self.github_repo_config = GitHubRepositoryConfig()
        self.config_file = CONFIG_FILE

        # 환경 변수 로드
        self.env_vars = load_env_vars(self.config_file)

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
