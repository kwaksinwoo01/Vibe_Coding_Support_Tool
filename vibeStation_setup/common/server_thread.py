"""
Server thread for vibeStation monitoring.
Runs FastAPI server to receive log data via HTTP POST.
"""
from PyQt6.QtCore import QThread, pyqtSignal
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel


# FastAPI 로그 수신 규격
app = FastAPI()


class LogData(BaseModel):
    tier: str
    msg: str
    status: str


# UI와 통신할 전역 시그널 관리
class CommSignal:
    log_signal = None


@app.post("/stream")
async def receive_log(data: LogData):
    if CommSignal.log_signal:
        CommSignal.log_signal.emit(data.dict())
    return {"status": "success"}


# FastAPI 서버를 백그라운드에서 실행할 스레드
class ServerThread(QThread):
    received = pyqtSignal(dict)
    
    def run(self):
        CommSignal.log_signal = self.received
        uvicorn.run(app, host="127.0.0.1", port=18989, log_level="error")
