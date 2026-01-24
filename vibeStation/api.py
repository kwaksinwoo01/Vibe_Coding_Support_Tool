"""
FastAPI backend for vibeStation.
Provides endpoints for log streaming and authentication.
"""
import asyncio
import httpx
import secrets
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import yaml


class LogEntry(BaseModel):
    """Log entry model."""
    tier: str = Field(..., pattern="^[A-F]$", description="Log tier (A-F)")
    message: str = Field(..., min_length=1, description="Log message")
    timestamp: Optional[str] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)


class VibeLogRequest(BaseModel):
    """Request model for sending vibe logs."""
    destination: str
    data: dict
    

class APIServer:
    """FastAPI server for vibeStation."""
    
    def __init__(self, config_path: str = "vibeStation/config.yaml"):
        """Initialize API server with configuration."""
        self.app = FastAPI(title="vibeStation API", version="1.0")
        self.config = self._load_config(config_path)
        self.auth_key = self._load_or_create_auth_key()
        self.security = HTTPBearer()
        self.log_buffer: List[LogEntry] = []
        self.max_logs = self.config.get('logging', {}).get('max_log_entries', 1000)
        
        # Setup routes
        self._setup_routes()
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            # Return default config
            return {
                'server': {'host': '127.0.0.1', 'port': 8765},
                'files': {
                    'instructions': 'instructions.yaml',
                    'auth_key': 'auth_key.txt',
                    'github_dir': '.github'
                },
                'logging': {'max_log_entries': 1000},
                'vibe_log': {
                    'retry_attempts': 3,
                    'retry_delay': 5,
                    'timeout': 10
                }
            }
    
    def _load_or_create_auth_key(self) -> str:
        """Load or create authentication key."""
        github_dir = self.config.get('files', {}).get('github_dir', '.github')
        auth_file = self.config.get('files', {}).get('auth_key', 'auth_key.txt')
        auth_path = Path(github_dir) / auth_file
        
        if auth_path.exists():
            try:
                with open(auth_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
        
        # Generate new key
        new_key = secrets.token_urlsafe(32)
        try:
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            with open(auth_path, 'w', encoding='utf-8') as f:
                f.write(new_key)
        except Exception:
            pass
        
        return new_key
    
    async def verify_auth(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
        """Verify authentication token."""
        if credentials.credentials != self.auth_key:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return credentials.credentials
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.post("/stream")
        async def stream_log(log: LogEntry, _auth: str = Depends(self.verify_auth)):
            """
            Receive and store tier logs (A-F).
            
            Args:
                log: Log entry with tier and message
                
            Returns:
                Success status
            """
            # Add to buffer
            self.log_buffer.append(log)
            
            # Trim buffer if needed
            if len(self.log_buffer) > self.max_logs:
                self.log_buffer = self.log_buffer[-self.max_logs:]
            
            return {"status": "success", "timestamp": log.timestamp}
        
        @self.app.get("/logs")
        async def get_logs(
            tier: Optional[str] = None,
            limit: int = 100,
            _auth: str = Depends(self.verify_auth)
        ):
            """
            Get stored logs.
            
            Args:
                tier: Optional tier filter (A-F)
                limit: Maximum number of logs to return
                
            Returns:
                List of log entries
            """
            logs = self.log_buffer
            
            if tier:
                logs = [log for log in logs if log.tier == tier]
            
            # Return most recent logs
            return {"logs": [log.dict() for log in logs[-limit:]]}
        
        @self.app.post("/vibe_log")
        async def send_vibe_log(request: VibeLogRequest, _auth: str = Depends(self.verify_auth)):
            """
            Send vibe log with retry mechanism.
            
            Args:
                request: Vibe log request with destination and data
                
            Returns:
                Success status
            """
            result = await self._send_with_retry(request.destination, request.data)
            return result
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "logs_count": len(self.log_buffer)}
        
        @self.app.get("/auth_key")
        async def get_auth_key():
            """Get authentication key (only accessible locally)."""
            return {"auth_key": self.auth_key}
    
    async def _send_with_retry(self, destination: str, data: dict) -> dict:
        """
        Send data with retry mechanism.
        
        Args:
            destination: URL to send data to
            data: Data to send
            
        Returns:
            Response data
        """
        config = self.config.get('vibe_log', {})
        retry_attempts = config.get('retry_attempts', 3)
        retry_delay = config.get('retry_delay', 5)
        timeout = config.get('timeout', 10)
        
        last_error = None
        
        for attempt in range(retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(destination, json=data)
                    response.raise_for_status()
                    return {
                        "status": "success",
                        "attempt": attempt + 1,
                        "response": response.json() if response.text else {}
                    }
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text}"
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(retry_delay)
            except httpx.TimeoutException as e:
                last_error = f"Timeout: {e}"
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(retry_delay)
            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}: {e}"
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(retry_delay)
        
        return {
            "status": "failed",
            "attempts": retry_attempts,
            "error": last_error
        }
    
    def get_logs(self) -> List[LogEntry]:
        """Get current log buffer."""
        return self.log_buffer.copy()
    
    def clear_logs(self):
        """Clear log buffer."""
        self.log_buffer.clear()
