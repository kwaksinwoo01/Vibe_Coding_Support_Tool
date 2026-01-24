# Vibe_Coding_Support_Tool

이 프로그램은 AI 코딩 에이전트로 대규모 코딩프로그램을 만들 때 바이브 코딩으로 개발하는 고질적인 문제를 최소화하고 작업을 효율적으로 수행하기 위한 기능을 최대한 지원하기 위해 만들었습니다.

## vibeStation - GitHub Instructions Monitor & Editor

vibeStation은 PyQt6와 FastAPI를 결합한 데스크톱 애플리케이션으로, .github 디렉토리의 지시사항 파일을 편집하고 실시간 로그를 모니터링할 수 있습니다.

### 주요 기능

- **실시간 로그 모니터링**: Tier A-F 로그를 실시간으로 수신하고 표시
- **YAML 편집기**: .github/instructions.yaml 파일을 안전하게 편집 (자동 백업, 원자적 교체, 검증 포함)
- **FastAPI 서버**: 127.0.0.1에서 실행되는 내장 API 서버
- **인증**: 로컬 인증 키를 사용한 보안 API 접근
- **비동기 로그 전송**: 재시도 메커니즘을 포함한 send_vibe_log
- **Windows EXE 빌드**: PyInstaller를 사용한 독립 실행 파일 생성

### 설치 방법

1. 저장소 클론:
```bash
git clone https://github.com/kwaksinwoo01/Vibe_Coding_Support_Tool.git
cd Vibe_Coding_Support_Tool
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

### 실행 방법

```bash
python run_vibestation.py
```

또는:
```bash
python -m vibeStation.app
```

### Windows EXE 빌드

```bash
pyinstaller vibestation.spec
```

빌드된 실행 파일은 `dist/vibeStation.exe`에 생성됩니다.

### 사용 방법

#### 1. 애플리케이션 시작

애플리케이션을 시작하면:
- FastAPI 서버가 자동으로 시작됩니다 (기본 포트: 8765)
- PyQt6 GUI 창이 열립니다
- 인증 키가 자동으로 생성됩니다 (.github/auth_key.txt)

#### 2. Tier 로그 모니터링

"📊 Tier Logs" 탭에서:
- POST /stream으로 수신된 로그를 실시간으로 확인
- Tier (A-F)별로 필터링 가능
- 색상 코딩으로 로그 레벨 구분

#### 3. Instructions 편집

"📝 Instructions Editor" 탭에서:
- .github/instructions.yaml 파일 편집
- YAML 문법 검증
- 저장 시 자동 백업 생성
- 백업 파일 목록 확인 및 복원

### API 엔드포인트

모든 API 요청에는 Bearer 토큰 인증이 필요합니다 (GET /health 및 GET /auth_key 제외).

#### POST /stream
Tier 로그 전송
```bash
curl -X POST http://127.0.0.1:8765/stream \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tier": "A", "message": "High priority log"}'
```

#### GET /logs
저장된 로그 조회
```bash
curl -X GET "http://127.0.0.1:8765/logs?tier=A&limit=10" \
  -H "Authorization: Bearer YOUR_AUTH_KEY"
```

#### POST /vibe_log
재시도 메커니즘이 포함된 로그 전송
```bash
curl -X POST http://127.0.0.1:8765/vibe_log \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "http://example.com/api/log",
    "data": {"message": "test"}
  }'
```

#### GET /health
헬스 체크 (인증 불필요)
```bash
curl http://127.0.0.1:8765/health
```

#### GET /auth_key
인증 키 조회 (인증 불필요, 로컬에서만 접근)
```bash
curl http://127.0.0.1:8765/auth_key
```

### 설정

`vibeStation/config.yaml`에서 설정 변경 가능:

```yaml
server:
  host: "127.0.0.1"
  port: 8765

files:
  instructions: "instructions.yaml"
  auth_key: "auth_key.txt"
  github_dir: ".github"

logging:
  tiers: ["A", "B", "C", "D", "E", "F"]
  max_log_entries: 1000

vibe_log:
  retry_attempts: 3
  retry_delay: 5
  timeout: 10
```

### 보안

- 인증 키는 `.github/auth_key.txt`에 자동 생성됩니다
- 이 키를 공유하지 마세요
- API 서버는 기본적으로 127.0.0.1에서만 접근 가능합니다
- YAML 파일 저장 시 자동 백업이 생성됩니다

### 파일 구조

```
Vibe_Coding_Support_Tool/
├── .github/
│   ├── instructions.yaml          # AI 에이전트 지시사항
│   └── auth_key.txt               # API 인증 키 (자동 생성)
├── vibeStation/
│   ├── __init__.py
│   ├── app.py                     # 메인 애플리케이션
│   ├── api.py                     # FastAPI 서버
│   ├── main_window.py             # PyQt6 GUI
│   ├── yaml_handler.py            # YAML 파일 핸들러
│   └── config.yaml                # 설정 파일
├── run_vibestation.py             # 실행 스크립트
├── requirements.txt               # Python 의존성
├── vibestation.spec               # PyInstaller 스펙
├── test_vibestation.py            # 테스트 스크립트
├── example_client.py              # API 클라이언트 예제
├── USAGE.md                       # 사용 설명서
├── SCREENSHOTS.md                 # UI 스크린샷
├── Monitoring.py                  # (레거시) 이전 모니터링 구현
└── README.md
```

**참고**: `Monitoring.py`는 이전 버전의 모니터링 도구입니다. 새로운 `vibeStation` 구현을 사용하는 것을 권장합니다.

### 라이선스

MIT License - 자세한 내용은 LICENSE 파일을 참조하세요.

### 기여

이슈 및 풀 리퀘스트는 언제나 환영합니다!
