import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import QThread, pyqtSignal
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path

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

# 4. 메인 UI 클래스 (한국어 지원)
class VibeStation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vibe Station v1.0 - AI 코딩 에이전트 관제소")
        self.init_ui()
        self.start_server()

    def init_ui(self):
        layout = QVBoxLayout()
        # 티어 상태 인디케이터
        self.status_label = QLabel("에이전트 상태: 대기 중")
        self.status_label.setStyleSheet("color: white; background: #333; padding: 10px; font-weight: bold;")
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
        self.thread = ServerThread()
        self.thread.received.connect(self.display_log)
        self.thread.start()

    def display_log(self, data):
        tier_name = {"A": "기획", "B": "수행", "C": "수정", "D": "분석", "E": "관리", "F": "기타"}
        kor_tier = tier_name.get(data['tier'], data['tier'])
        self.status_label.setText(f"현재 단계: Tier {data['tier']} ({kor_tier}) - {data['status']}")
        self.log_viewer.append(f"<b>[{kor_tier}]</b> {data['msg']}")

    def update_instruction(self):
        # .github/copilot-instructions.md 자동 탐색 및 저장 로직
        target = Path(".github/copilot-instructions.md")
        if target.exists():
            with open(target, "a", encoding="utf-8") as f:
                f.write(f"\n- [사용자 요청]: {self.input_edit.text()}")
            self.log_viewer.append("<font color='cyan'>시스템: 지침이 성공적으로 반영되었습니다.</font>")
            self.input_edit.clear()

if __name__ == "__main__":
    q_app = QApplication(sys.argv)
    window = VibeStation()
    window.show()
    sys.exit(q_app.exec())