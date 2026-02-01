# UI Module Reorganization

## 개요
이 문서는 Vibe Station의 UI 모듈 재조직 결과를 설명합니다.

## 새로운 구조

### 모듈 구성

```
Vibe_Coding_Support_Tool/
├── vibeStation_setup/          # 설치 모듈
│   ├── __init__.py
│   └── installer/
│       ├── __init__.py
│       └── main_window.py      # SetupWizardWidget (초기 설정 마법사)
│
├── vibeStation_monitor/         # 모니터링 모듈
│   ├── __init__.py
│   └── main_window.py          # VibeStation (메인 모니터링 UI)
│
├── mcp_suver/                   # MCP 서버 핵심 엔진
│   ├── __init__.py
│   └── MCP_server.py           # ServerThread, FastAPI 앱 (UI 제거)
│
├── common/                      # 공유 유틸리티
│   ├── __init__.py
│   ├── config_manager.py       # 설정 로드/저장 함수
│   └── dialogs.py              # GitHubTokenHelpDialog, SettingsDialog
│
└── Monitoring.py                # 레거시 진입점 (하위 호환성)
```

## 모듈별 책임

### 1. vibeStation_setup (설치 모듈)
**역할**: 초기 설정 및 마법사 UI
- `installer/main_window.py`: 설치 마법사 위젯 (`SetupWizardWidget`)
- 처음 사용자가 필요한 설정을 단계별로 안내

### 2. vibeStation_monitor (모니터링 모듈)
**역할**: 실시간 로그 표시 및 상태 모니터링
- `main_window.py`: 메인 모니터링 윈도우 (`VibeStation`)
- AI 에이전트의 작업 상태를 실시간으로 표시
- 새로운 지침 입력 및 관리

### 3. mcp_suver (서버 제어 모듈)
**역할**: MCP 서버 핵심 엔진 (UI 의존성 제거)
- `MCP_server.py`: FastAPI 서버와 ServerThread
- 로그 수신 및 전달 (UI 제외)
- 순수 백엔드 로직만 포함

### 4. common (공통 모듈)
**역할**: 공유 유틸리티 및 다이얼로그
- `config_manager.py`: 설정 파일 로드/저장
- `dialogs.py`: 공통 다이얼로그 컴포넌트
  - `GitHubTokenHelpDialog`: GitHub 토큰 생성 도움말
  - `SettingsDialog`: 설정 다이얼로그

## 사용 방법

### 메인 모니터링 UI 실행
```bash
python vibeStation_monitor/main_window.py
```

### 레거시 방식 (하위 호환성)
```bash
python Monitoring.py
```

### 설치 마법사 실행
```bash
python vibeStation_setup/installer/main_window.py
```

## 설계 원칙

### 1. 관심사의 분리 (Separation of Concerns)
- 각 모듈은 명확한 단일 책임을 가짐
- UI 로직과 비즈니스 로직의 분리

### 2. 의존성 관리
- UI 컴포넌트는 서버 엔진을 import
- 서버 엔진은 UI에 대한 의존성 없음
- 공통 유틸리티는 독립적으로 사용 가능

### 3. 확장성
- 새로운 UI 컴포넌트 추가 용이
- 모듈별 독립적 개발 및 테스트 가능

## 마이그레이션 가이드

### 기존 코드에서 변경사항

**Before (Monitoring.py):**
```python
from PyQt6.QtWidgets import *
# 모든 코드가 한 파일에 존재
```

**After (새로운 구조):**
```python
from vibeStation_monitor.main_window import VibeStation
from mcp_suver.MCP_server import ServerThread
from common.config_manager import save_instruction
```

### Import 경로 변경

| 이전 위치 | 새로운 위치 |
|----------|------------|
| `Monitoring.VibeStation` | `vibeStation_monitor.main_window.VibeStation` |
| `Monitoring.ServerThread` | `mcp_suver.MCP_server.ServerThread` |
| - | `common.dialogs.SettingsDialog` |
| - | `common.config_manager.save_instruction` |

## 향후 개선 사항

1. **로그 표시 분리**: `vibeStation_monitor/log_display.py` 생성 고려
2. **설정 파일 형식**: JSON/YAML 기반 설정 관리 추가
3. **테스트 코드**: 각 모듈별 단위 테스트 추가
4. **문서화**: API 문서 및 사용 예제 추가

## 검증 완료 항목

- [x] 모듈 구조 생성
- [x] ServerThread를 mcp_suver로 이동
- [x] VibeStation을 vibeStation_monitor로 이동
- [x] 공통 유틸리티 분리 (config_manager)
- [x] 공통 다이얼로그 생성 (dialogs)
- [x] 하위 호환성 유지 (Monitoring.py)
- [x] Import 경로 업데이트
- [ ] 순환 import 확인 필요
- [ ] 독립 실행 테스트 필요
