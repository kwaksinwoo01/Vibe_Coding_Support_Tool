"""
Main application entry point for vibeStation Monitor.
Launches PyQt6 UI for monitoring coding agent logs.
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QLabel, QPushButton, QMessageBox, QComboBox, QTableWidget, QTableWidgetItem, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLineEdit
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime

# 1. FastAPI 로그 수신 규격
app = FastAPI()
class LogData(BaseModel):
    tier: str
    msg: str
    status: str

# 2. UI와 통신할 전역 시그널 관리
class CommSignal:
    log_signal = None

@app.post("/stream")
async def receive_log(data: LogData):
    if CommSignal.log_signal:
        CommSignal.log_signal.emit(data.dict())
    return {"status": "success"}

# 3. FastAPI 서버를 백그라운드에서 실행할 스레드
class ServerThread(QThread):
    received = pyqtSignal(dict)
    def run(self):
        CommSignal.log_signal = self.received
        uvicorn.run(app, host="127.0.0.1", port=18989, log_level="error")

# 4. 로그 표시 위젯
class LogDisplayWidget(QWidget):
    """Widget for displaying tier logs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Tier:"))
        
        self.tier_filter = QComboBox()
        self.tier_filter.addItems(["All", "A", "B", "C", "D", "E", "F"])
        self.tier_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.tier_filter)
        
        self.clear_btn = QPushButton("Clear Logs")
        self.clear_btn.clicked.connect(self.clear_logs)
        filter_layout.addWidget(self.clear_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Log table
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(["Time", "Tier", "Message"])
        self.log_table.setColumnWidth(0, 150)
        self.log_table.setColumnWidth(1, 50)
        self.log_table.setColumnWidth(2, 600)
        layout.addWidget(self.log_table)
        
        self.all_logs = []
        
    def add_log(self, tier: str, message: str, timestamp: str = None):
        """Add a log entry to the display."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            'tier': tier,
            'message': message,
            'timestamp': timestamp
        }
        self.all_logs.append(log_entry)
        
        # Apply filter
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the log display with current filter."""
        filter_tier = self.tier_filter.currentText()
        
        # Filter logs
        if filter_tier == "All":
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
            self.log_table.setItem(i, 1, tier_item)
            
            # Message
            msg_item = QTableWidgetItem(log['message'])
            self.log_table.setItem(i, 2, msg_item)
        
        # Scroll to bottom
        self.log_table.scrollToBottom()
    
    def _get_tier_color(self, tier: str) -> QColor:
        """Get color for tier level."""
        colors = {
            'A': QColor(220, 53, 69),    # Red
            'B': QColor(255, 193, 7),    # Yellow
            'C': QColor(0, 123, 255),    # Blue
            'D': QColor(40, 167, 69),    # Green
            'E': QColor(108, 117, 125),  # Gray
            'F': QColor(23, 162, 184)    # Cyan
        }
        return colors.get(tier, QColor(128, 128, 128))
    
    def on_filter_changed(self):
        """Handle filter change."""
        self.refresh_display()
    
    def clear_logs(self):
        """Clear all logs."""
        self.all_logs.clear()
        self.log_table.setRowCount(0)

# 5. 메인 UI 클래스 (한국어 지원)
class VibeStationMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("vibeStation Monitor v1.0 - AI 코딩 에이전트 관제소")
        self.init_ui()
        self.start_server()

    def init_ui(self):
        layout = QVBoxLayout()
        # 티어 상태 인디케이터
        self.status_label = QLabel("에이전트 상태: 대기 중")
        self.status_label.setStyleSheet("color: white; background: #333; padding: 10px; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # 로그 표시 위젯
        self.log_display = LogDisplayWidget()
        layout.addWidget(self.log_display)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def start_server(self):
        self.thread = ServerThread()
        self.thread.received.connect(self.display_log)
        self.thread.start()

    def display_log(self, data):
        tier_name = {"A": "기획", "B": "수행", "C": "수정", "D": "분석", "E": "관리", "F": "기타"}
        kor_tier = tier_name.get(data['tier'], data['tier'])
        self.status_label.setText(f"현재 단계: Tier {data['tier']} ({kor_tier}) - {data['status']}")
        self.log_display.add_log(data['tier'], data['msg'])

    def closeEvent(self, event):
        """Handle window close event."""
        reply = QMessageBox.question(
            self,
            'Exit',
            'Are you sure you want to exit vibeStation Monitor?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    """Main entry point."""
    q_app = QApplication(sys.argv)
    window = VibeStationMonitor()
    window.show()
    sys.exit(q_app.exec())


if __name__ == "__main__":
    main()