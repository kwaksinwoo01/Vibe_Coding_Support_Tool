"""
MCP Server Core Engine
MCP 서버의 핵심 엔진을 제공합니다 (UI 의존성 제거).

이 모듈은 FastAPI 서버와 로그 수신 기능만 포함합니다.
UI 컴포넌트는 vibeStation_monitor 모듈에서 관리합니다.
"""
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from PyQt6.QtCore import QThread, pyqtSignal


# FastAPI 로그 수신 규격
app = FastAPI()


class LogData(BaseModel):
    """로그 데이터 모델"""
    tier: str
    msg: str
    status: str


# UI와 통신할 전역 시그널 관리
class CommSignal:
    """전역 시그널 관리 클래스"""
    log_signal = None


@app.post("/stream")
async def receive_log(data: LogData):
    """
    로그 수신 엔드포인트
    
    Args:
        data: 로그 데이터 (tier, msg, status)
    
    Returns:
        성공 상태
    """
    if CommSignal.log_signal:
        CommSignal.log_signal.emit(data.dict())
    return {"status": "success"}


class ServerThread(QThread):
    """
    FastAPI 서버를 백그라운드에서 실행할 스레드
    
    Signals:
        received: 로그 데이터 수신 시그널
    """
    received = pyqtSignal(dict)
    
    def run(self):
        """서버 실행"""
        CommSignal.log_signal = self.received
        uvicorn.run(app, host="127.0.0.1", port=18989, log_level="error")
