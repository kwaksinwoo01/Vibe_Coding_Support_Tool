
import os
import sys
import json
import asyncio
import traceback
import subprocess
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel
from PyQt6.QtCore import QThread, pyqtSignal
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# 로거 설정
logger = logging.getLogger(__name__)

# ============================================
# Project Root Configuration for subprocess execution
# ============================================
# Calculate project root (repository root where vibeStation_setup is a subdirectory)
# server_thread.py is at: Vibe_Coding_Support_Tool/vibeStation_setup/mcp_suver/core/server_thread.py
# Project root is: Vibe_Coding_Support_Tool (4 levels up)
# This allows importing as: vibeStation_setup.mcp_suver.main_agent
_CALLING_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _CALLING_FILE.parent.parent.parent.parent  # Go up to repository root

# Ensure project root is in sys.path for module imports
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger.info(f"Project root for subprocess: {_PROJECT_ROOT}")


# ============================================
# Pydantic 모델 (common/server_thread.py에서)
# ============================================
class LogData(BaseModel):
    """FastAPI 로그 데이터 모델"""
    tier: str
    msg: str
    status: str


# ============================================
# 전역 시그널 관리 (common/server_thread.py에서)
# ============================================
class CommSignal:
    """UI와 통신할 전역 시그널 관리"""
    log_signal: Optional[Any] = None


class ServerThread(QThread):
    """FastAPI + SSE 서버 실행 스레드
    
    기능:
    - MCP 프로토콜 기반 SSE 통신
    - 로그 데이터 수신 (/stream 엔드포인트)
    - SQLite 기반 데이터 저장 (Redis 제거됨)
    - 에이전트 작업 실행
    - 상태 모니터링
    """
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    received = pyqtSignal(dict)  # common/server_thread.py에서

    def __init__(self, port: int = 18989):
        super().__init__()
        self.port = port
        self.app = None
        self.checkpointer = None
        self._running = True
        self.server = None  # Uvicorn 서버 인스턴스 저장
        
        # 전역 시그널 설정 (타입 체크 무시)
        CommSignal.log_signal = self.received  # type: ignore

    def run(self):
        """서버 실행"""
        try:
            self.log_signal.emit(f"[서버] 포트 {self.port}에서 시작 중...")
            self.status_signal.emit(f"초기화 중... (Port: {self.port})")
            
            # FastAPI 앱 생성
            self.app = FastAPI(title="MCP Server", version="1.0.0")
            self._setup_routes()
            
            # Uvicorn 서버 실행
            self.status_signal.emit(f"실행 중 (Port: {self.port})")
            self.log_signal.emit(f"[서버] http://127.0.0.1:{self.port} 리스닝 시작")
            
            import uvicorn
            config = uvicorn.Config(
                self.app, 
                host="127.0.0.1", 
                port=self.port, 
                log_level="error"
            )
            self.server = uvicorn.Server(config)
            asyncio.run(self.server.serve())
            
        except Exception as e:
            error_msg = f"서버 실행 오류: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.error_signal.emit(error_msg)
            self.status_signal.emit("오류 발생")
    
    def _setup_routes(self):
        """FastAPI 라우트 설정"""
        
        @self.app.get("/")
        async def root():
            return {
                "status": "MCP Server Running",
                "port": self.port,
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.post("/stream")
        async def receive_log(data: LogData):
            """로그 데이터 수신 엔드포인트 (common/server_thread.py에서)"""
            if CommSignal.log_signal:
                CommSignal.log_signal.emit(data.dict())
            self.log_signal.emit(f"[LOG] [{data.tier}] {data.msg} ({data.status})")
            return {"status": "success"}
        
        @self.app.get("/sse")
        async def sse_endpoint(request: Request):
            """SSE 엔드포인트 (MCP 프로토콜)"""
            async def event_generator():
                try:
                    self.log_signal.emit("[SSE] 클라이언트 연결됨")
                    yield f"event: connected\ndata: {json.dumps({'status': 'ok'})}\n\n"
                    
                    counter = 0
                    while self._running:
                        if await request.is_disconnected():
                            self.log_signal.emit("[SSE] 클라이언트 연결 끊김")
                            break
                        
                        # 하트비트 전송
                        counter += 1
                        yield f"event: heartbeat\ndata: {json.dumps({'count': counter, 'time': datetime.now().isoformat()})}\n\n"
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    error_msg = f"SSE 오류: {e}"
                    logger.error(error_msg)
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        
        @self.app.post("/execute")
        async def execute_task(request: Request):
            """에이전트 작업 실행 (main_agent.py 모듈 직접 사용)
            
            Fix for diagnoseModulePathError:
            - Sets explicit working directory (cwd) to project root
            - Ensures module can be found via -m flag
            - Inherits parent environment variables
            """
            try:
                data = await request.json()
                user_input = data.get("user_input", "")
                
                self.log_signal.emit(f"[실행] 요청: {user_input[:100]}")
                
                # main_agent.py 모듈을 subprocess로 실행
                # Fix: Added cwd and env parameters for reliable module execution
                result = subprocess.run(
                    [sys.executable, "-m", "vibeStation_setup.mcp_suver.main_agent", user_input],
                    cwd=str(_PROJECT_ROOT),  # Set working directory to project root
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=os.environ.copy()  # Inherit parent environment
                )
                
                self.log_signal.emit(f"[실행] 완료 (코드: {result.returncode})")
                
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
                
            except Exception as e:
                error_msg = f"실행 오류: {e}"
                logger.error(error_msg)
                self.log_signal.emit(f"[오류] {error_msg}")
                return {"status": "error", "message": str(e)}
    
    def stop(self):
        """서버 중지 - Uvicorn 서버를 안전하게 종료"""
        self._running = False
        self.log_signal.emit("[서버] 중지 요청됨")
        
        # Uvicorn 서버 종료
        if self.server:
            try:
                self.server.should_exit = True  # Uvicorn에 종료 신호 전송
                self.log_signal.emit("[서버] Uvicorn 서버 종료 신호 전송")
            except Exception as e:
                logger.warning(f"Uvicorn 서버 종료 오류: {e}")
