"""
Main application entry point for vibeStation Monitor.
Launches PyQt6 UI for monitoring coding agent logs.
"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QMessageBox

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import common components
from common.log_display import LogDisplayWidget
from common.server_thread import ServerThread

# 메인 UI 클래스 (한국어 지원)
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