
"""
MCP Log Display Widget
Displays tier-based logs with filtering, status monitoring, and real-time updates.
Integrated with ServerThread for live log streaming.
Includes GitHub repository monitoring and work plan management.
"""
import sys
import json
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
                             QGroupBox, QStatusBar, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class MCPLogTab(QWidget):
    """Widget for displaying MCP tier logs with real-time updates and work plan management."""
    
    # Signals for status updates
    status_changed = pyqtSignal(str)
    
    def __init__(self, parent=None, github_repo_config=None):
        super().__init__(parent)
        self.github_repo_config = github_repo_config
        self.init_ui()
        self.all_logs = []
        self.current_status = "대기 중"
        self.plan_files = []  # 작업 계획 파일 목록 캐시
        
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # ============================================================================
        # GitHub Repository Info
        # ============================================================================
        repo_group = QGroupBox("GitHub 저장소 정보")
        repo_layout = QVBoxLayout()
        
        self.repo_info_label = QLabel("저장소: 설정되지 않음")
        self.repo_info_label.setStyleSheet("font-size: 10pt; color: #888;")
        repo_layout.addWidget(self.repo_info_label)
        repo_group.setLayout(repo_layout)
        layout.addWidget(repo_group)
        
        # ============================================================================
        # Status Display
        # ============================================================================
        status_group = QGroupBox("에이전트 상태")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("에이전트 상태: 대기 중")
        self.status_label.setStyleSheet(
            "color: white; background: #333333; padding: 10px; "
            "font-weight: bold; border-radius: 4px; font-size: 11pt;"
        )
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # ============================================================================
        # Work Plan Management
        # ============================================================================
        plan_group = QGroupBox("작업 계획 문서")
        plan_layout = QVBoxLayout()
        
        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(4)
        self.plan_table.setHorizontalHeaderLabels(["파일명", "경로", "브랜치", "상태"])
        self.plan_table.horizontalHeader().setStretchLastSection(True)
        self.plan_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        plan_layout.addWidget(self.plan_table)
        
        # 작업 계획 제어 버튼
        plan_btn_layout = QHBoxLayout()
        self.refresh_plan_btn = QPushButton("🔄 작업 계획 새로고침")
        self.refresh_plan_btn.clicked.connect(self.refresh_plan_list)
        plan_btn_layout.addWidget(self.refresh_plan_btn)
        
        self.open_github_btn = QPushButton("🌐 GitHub에서 열기")
        self.open_github_btn.clicked.connect(self.open_selected_in_github)
        plan_btn_layout.addWidget(self.open_github_btn)
        
        plan_btn_layout.addStretch()
        plan_layout.addLayout(plan_btn_layout)
        plan_group.setLayout(plan_layout)
        layout.addWidget(plan_group)
        
        # ============================================================================
        # Filter Controls
        # ============================================================================
        filter_group = QGroupBox("필터 및 제어")
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Tier별 필터:"))
        
        self.tier_filter = QComboBox()
        self.tier_filter.addItems(["전체", "A", "B", "C", "D", "E", "F"])
        self.tier_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.tier_filter)
        
        self.clear_btn = QPushButton("🗑️ 로그 지우기")
        self.clear_btn.clicked.connect(self.clear_logs)
        filter_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("💾 로그 내보내기")
        self.export_btn.clicked.connect(self.export_logs)
        filter_layout.addWidget(self.export_btn)
        
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # ============================================================================
        # Log Table
        # ============================================================================
        log_group = QGroupBox("실시간 로그")
        log_layout = QVBoxLayout()
        
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(4)
        self.log_table.setHorizontalHeaderLabels(["시간", "Tier", "메시지", "상태"])
        self.log_table.setColumnWidth(0, 150)
        self.log_table.setColumnWidth(1, 50)
        self.log_table.setColumnWidth(2, 450)
        self.log_table.setColumnWidth(3, 100)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setStyleSheet(
            "QTableWidget { "
            "  background-color: #f5f5f5; "
            "  gridline-color: #ddd; "
            "} "
            "QTableWidget::item { padding: 4px; } "
            "QHeaderView::section { background-color: #e8e8e8; padding: 4px; }"
        )
        log_layout.addWidget(self.log_table)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # ============================================================================
        # Statistics
        # ============================================================================
        stats_group = QGroupBox("통계")
        stats_layout = QHBoxLayout()
        
        self.total_logs_label = QLabel("총 로그: 0")
        stats_layout.addWidget(self.total_logs_label)
        
        stats_layout.addSpacing(20)
        
        self.tier_stats_labels = {}
        for tier in ["A", "B", "C", "D", "E", "F"]:
            tier_label = QLabel(f"Tier {tier}: 0")
            self.tier_stats_labels[tier] = tier_label
            stats_layout.addWidget(tier_label)
        
        stats_layout.addStretch()
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
    def add_log(self, tier: str, message: str, status: str = "완료", timestamp = None):
        """Add a log entry to the display."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Validate tier
        if tier not in ["A", "B", "C", "D", "E", "F"]:
            tier = "F"
        
        log_entry = {
            'tier': tier,
            'message': message,
            'status': status,
            'timestamp': timestamp
        }
        self.all_logs.append(log_entry)
        
        # Update status if A tier (highest priority)
        if tier == "A":
            self.update_agent_status(f"Tier {tier} - {message[:50]}")
        
        # Apply filter and refresh display
        self.refresh_display()
    
    def update_agent_status(self, status_text: str):
        """Update agent status display."""
        self.current_status = status_text
        self.status_label.setText(f"에이전트 상태: {status_text}")
        self.status_changed.emit(status_text)
    
    def refresh_display(self):
        """Refresh the log display with current filter."""
        filter_tier = self.tier_filter.currentText()
        
        # Filter logs
        if filter_tier == "전체":
            filtered_logs = self.all_logs
        else:
            filtered_logs = [log for log in self.all_logs if log['tier'] == filter_tier]
        
        # Update table
        self.log_table.setRowCount(len(filtered_logs))
        
        for i, log in enumerate(filtered_logs):
            # Timestamp
            time_item = QTableWidgetItem(log['timestamp'])
            self.log_table.setItem(i, 0, time_item)
            
            # Tier with color coding
            tier_item = QTableWidgetItem(log['tier'])
            tier_color = self._get_tier_color(log['tier'])
            tier_item.setBackground(tier_color)
            tier_item.setForeground(QColor(255, 255, 255))
            tier_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tier_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.log_table.setItem(i, 1, tier_item)
            
            # Message
            msg_item = QTableWidgetItem(log['message'])
            self.log_table.setItem(i, 2, msg_item)
            
            # Status
            status_item = QTableWidgetItem(log['status'])
            status_color = self._get_status_color(log['status'])
            status_item.setForeground(status_color)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.log_table.setItem(i, 3, status_item)
        
        # Update statistics
        self._update_statistics()
        
        # Scroll to bottom
        self.log_table.scrollToBottom()
    
    def _update_statistics(self):
        """Update log statistics display."""
        total = len(self.all_logs)
        self.total_logs_label.setText(f"총 로그: {total}")
        
        for tier in ["A", "B", "C", "D", "E", "F"]:
            count = len([log for log in self.all_logs if log['tier'] == tier])
            self.tier_stats_labels[tier].setText(f"Tier {tier}: {count}")
    
    def _get_tier_color(self, tier: str) -> QColor:
        """Get color for tier level."""
        colors = {
            'A': QColor(220, 53, 69),    # 빨강 - 기획
            'B': QColor(255, 193, 7),    # 노랑 - 수행
            'C': QColor(0, 123, 255),    # 파랑 - 수정
            'D': QColor(40, 167, 69),    # 초록 - 분석
            'E': QColor(108, 117, 125),  # 회색 - 관리
            'F': QColor(23, 162, 184)    # 시안 - 기타
        }
        return colors.get(tier, QColor(128, 128, 128))
    
    def _get_status_color(self, status: str) -> QColor:
        """Get color for status."""
        colors = {
            '완료': QColor(40, 167, 69),      # Green
            '진행중': QColor(255, 193, 7),    # Yellow
            '실패': QColor(220, 53, 69),      # Red
            '대기': QColor(108, 117, 125)     # Gray
        }
        return colors.get(status, QColor(0, 0, 0))
    
    def on_filter_changed(self):
        """Handle filter change."""
        self.refresh_display()
    
    def clear_logs(self):
        """Clear all logs."""
        self.all_logs.clear()
        self.log_table.setRowCount(0)
        self._update_statistics()
        self.update_agent_status("로그 초기화 완료")
    
    def export_logs(self):
        """Export logs to file."""
        try:
            from datetime import datetime
            filename = f"mcp_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"MCP Log Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                for log in self.all_logs:
                    f.write(f"[{log['timestamp']}] Tier {log['tier']} - {log['status']}\n")
                    f.write(f"  Message: {log['message']}\n\n")
            
            self.update_agent_status(f"로그 내보내기 완료: {filename}")
            
        except Exception as e:
            self.update_agent_status(f"로그 내보내기 실패: {str(e)}")
    
    def get_log_count(self) -> int:
        """Get total number of logs."""
        return len(self.all_logs)
    
    def get_tier_summary(self) -> dict:
        """Get summary of logs by tier."""
        summary = {tier: 0 for tier in ["A", "B", "C", "D", "E", "F"]}
        for log in self.all_logs:
            if log['tier'] in summary:
                summary[log['tier']] += 1
        return summary
    
    # ============================================================================
    # Work Plan Management Methods (from vibeStation_monitor\main_window.py)
    # ============================================================================
    
    def set_repository_config(self, github_repo_config):
        """저장소 설정 업데이트"""
        self.github_repo_config = github_repo_config
        self.update_repo_info_display()
    
    def update_repo_info_display(self):
        """GitHub 저장소 정보 표시 업데이트"""
        if self.github_repo_config and self.github_repo_config.is_valid:
            self.repo_info_label.setText(
                f"저장소: {self.github_repo_config.owner}/{self.github_repo_config.repo_name} "
                f"(브랜치: {self.github_repo_config.branch})"
            )
        else:
            self.repo_info_label.setText("저장소: 설정되지 않음")
    
    def refresh_plan_list(self):
        """작업 계획 목록 새로고침"""
        if not self.github_repo_config or not self.github_repo_config.is_valid:
            QMessageBox.warning(self, "경고", "GitHub 저장소를 먼저 설정하세요.")
            self.update_agent_status("GitHub 저장소 미설정")
            return
        
        self.update_agent_status("작업 계획 문서 검색 중...")
        
        try:
            api_url = f"https://api.github.com/repos/{self.github_repo_config.owner}/{self.github_repo_config.repo_name}/git/trees/{self.github_repo_config.branch}?recursive=1"
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            if hasattr(self.github_repo_config, 'github_token') and self.github_repo_config.github_token:
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
                
                self.plan_files = plan_files
                
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
                
                self.update_agent_status(f"✓ 작업 계획 문서 {len(plan_files)}개 발견")
                
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP 오류: {e.code}"
            self.update_agent_status(f"✗ 오류: {error_msg}")
            QMessageBox.critical(self, "오류", f"작업 계획 목록을 가져올 수 없습니다:\n{error_msg}")
        except Exception as e:
            error_msg = str(e)
            self.update_agent_status(f"✗ 오류: {error_msg}")
            QMessageBox.critical(self, "오류", f"작업 계획 목록을 가져올 수 없습니다:\n{error_msg}")
    
    def open_selected_in_github(self):
        """선택한 파일을 GitHub에서 열기"""
        selected_row = self.plan_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "경고", "파일을 먼저 선택하세요.")
            return
        
        if not self.github_repo_config or not self.github_repo_config.is_valid:
            QMessageBox.warning(self, "경고", "GitHub 저장소를 먼저 설정하세요.")
            return
        
        file_path = self.plan_table.item(selected_row, 1).text()
        
        # GitHub 웹 URL 생성
        try:
            web_url = f"https://github.com/{self.github_repo_config.owner}/{self.github_repo_config.repo_name}/blob/{self.github_repo_config.branch}/{file_path}"
            webbrowser.open(web_url)
            self.update_agent_status(f"GitHub에서 열기: {file_path}")
        except Exception as e:
            error_msg = f"URL 열기 실패: {str(e)}"
            self.update_agent_status(f"✗ {error_msg}")
            QMessageBox.warning(self, "경고", error_msg)
