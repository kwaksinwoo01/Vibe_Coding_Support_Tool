"""
Main Monitoring Window
실시간 로그 표시 및 상태 모니터링을 위한 메인 윈도우를 제공합니다.
"""
import sys
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QLabel, QTextEdit, QLineEdit, QPushButton, QWidget, QApplication
from mcp_suver.MCP_server import ServerThread
from common.config_manager import save_instruction


class VibeStation(QMainWindow):
    """
    메인 모니터링 UI 클래스
    
    AI 에이전트의 작업 상태를 실시간으로 모니터링하고 
    새로운 지침을 입력할 수 있는 인터페이스를 제공합니다.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vibe Station v1.0 - AI 코딩 에이전트 관제소")
        self.init_ui()
        self.start_server()

    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 티어 상태 인디케이터
        self.status_label = QLabel("에이전트 상태: 대기 중")
        self.status_label.setStyleSheet(
            "color: white; background: #333; padding: 10px; font-weight: bold;"
        )
        layout.addWidget(self.status_label)
        
        # 로그 출력창
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("background: #1e1e1e; color: #00ff00;")
        layout.addWidget(self.log_viewer)
        
        # 지침 추가 입력창
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("새로운 AI 지침을 한국어로 입력하세요...")
        
        self.send_btn = QPushButton("지침 업데이트")
        self.send_btn.clicked.connect(self.update_instruction)
        
        layout.addWidget(self.input_edit)
        layout.addWidget(self.send_btn)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def start_server(self):
        """FastAPI 서버 시작"""
        self.thread = ServerThread()
        self.thread.received.connect(self.display_log)
        self.thread.start()

    def display_log(self, data: dict):
        """
        로그 데이터를 화면에 표시
        
        Args:
            data: 로그 데이터 딕셔너리 (tier, msg, status)
        """
        tier_name = {
            "A": "기획",
            "B": "수행",
            "C": "수정",
            "D": "분석",
            "E": "관리",
            "F": "기타"
        }
        kor_tier = tier_name.get(data['tier'], data['tier'])
        
        self.status_label.setText(
            f"현재 단계: Tier {data['tier']} ({kor_tier}) - {data['status']}"
        )
        self.log_viewer.append(f"<b>[{kor_tier}]</b> {data['msg']}")

    def update_instruction(self):
        """AI 지침 업데이트"""
        instruction = self.input_edit.text()
        
        if save_instruction(instruction):
            self.log_viewer.append(
                "<font color='cyan'>시스템: 지침이 성공적으로 반영되었습니다.</font>"
            )
            self.input_edit.clear()
        else:
            self.log_viewer.append(
                "<font color='red'>오류: 지침 파일을 찾을 수 없습니다.</font>"
            )


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    window = VibeStation()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
