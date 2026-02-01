# GitHub Copilot MCP Configuration Guide

## GitHub Copilot 설정 페이지에서 MCP 추가하기

GitHub Copilot의 Coding Agent 설정 페이지에서 다음과 같이 설정합니다:

### 1. 설정 페이지 접속
- URL: `https://github.com/kwaksinwoo01/turbo-system/settings/copilot/coding_agent`

### 2. MCP 추가
**"Add MCP Server" 또는 "Add Custom Tools" 버튼을 클릭**하면 아래 JSON을 입력합니다:

```json
{
  "mcpServers": {
    "turbo-system": {
      "command": "python",
      "args": [
        ".github/MCP/mcp_server.py",
        "--host",
        "127.0.0.1",
        "--port",
        "3846",
        "--redis-host",
        "localhost",
        "--redis-port",
        "6379"
      ],
      "env": {
        "PYTHONPATH": ".",
        "WORKSPACE_ROOT": "."
      }
    }
  }
}
```

---

## 각 행의 의미

| 설정 항목 | 설명 |
|---------|------|
| **command** | MCP 서버를 실행할 프로그램 (`python`) |
| **args** | Python 스크립트 경로 및 실행 인자 |
| **--host** | MCP 서버가 바인딩될 IP 주소 |
| **--port** | MCP 서버 포트 번호 (3846) |
| **--redis-host** | Redis 캐시 서버 주소 |
| **--redis-port** | Redis 포트 |
| **env.PYTHONPATH** | Python 모듈 검색 경로 |
| **env.WORKSPACE_ROOT** | 작업 디렉토리 (프로젝트 루트) |

---

## 🚀 빠른 설정 (권장)

GitHub Copilot 웹 설정 페이지의 **"Custom MCP" 탭**에서:

```
Server Name: turbo-system
Command: python .github/MCP/mcp_server.py --host 127.0.0.1 --port 3846 --redis-host localhost --redis-port 6379
```

---

## ✅ 설정 후 확인

1. **저장** 버튼 클릭
2. **Test Connection** 또는 **Verify** 버튼으로 연결 확인
3. MCP 서버가 정상 작동하면 Copilot Coding Agent에서 사용 가능

---

## 🔧 로컬 개발 환경에서 MCP 서버 수동 실행

```bash
# 1. 필수 패키지 설치
pip install -r requirements.txt

# 2. Redis 서버 실행 (선택)
redis-server

# 3. MCP 서버 시작
python .github/MCP/mcp_server.py --host 127.0.0.1 --port 3846

# 또는 래퍼 스크립트 사용
python .github/MCP/run_server.py --host 127.0.0.1 --port 3846
```

---

## 📌 주요 MCP 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|-------|------|
| `/health` | GET | 서버 상태 확인 |
| `/.well-known/mcp` | GET | MCP 매니페스트 (자동 검색) |
| `/execute` | POST | 6-Tier 오케스트레이션 워크플로우 실행 |
| `/classify` | POST | 사용자 입력 분류 |
| `/execute-tier/{tier}` | POST | 특정 Tier 직접 실행 |
| `/route` | POST | 라우팅 결정 평가 |
| `/resources/metrics` | GET | 성능 메트릭 조회 |

---

## 🐛 트러블슈팅

### 연결 실패 (Connection Refused)
- Redis 서버 확인: `redis-cli ping`
- MCP 서버 포트 확인: `netstat -an | findstr :3846` (Windows)
- 방화벽 설정 확인

### ImportError: No module named 'main_agent'
- PYTHONPATH 확인: `.github/MCP` 또는 프로젝트 루트 설정
- 필수 패키지 설치 확인: `pip install -r requirements.txt`

### Redis 연결 오류
- Redis 없이도 실행 가능 (기본값)
- 선택사항: `--redis-host localhost --redis-port 6379` 제거 가능

---

## 📚 참고 자료
- [GitHub Copilot MCP 문서](https://docs.github.com/en/copilot/customizing-copilot/adding-custom-tools-to-github-copilot)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- 프로젝트 가이드: `docs_2/copilot-instructions.md`
