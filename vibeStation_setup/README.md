# vibeStation Setup

GitHub Copilot Instructions 파일 생성 및 편집 도구

## 기능

- **새로운 Instructions 파일 생성**: 설정 마법사를 통해 새로운 copilot-instructions.md 파일 생성
- **기존 파일 서식 변경**: 기존 파일을 표준 템플릿에 맞게 자동 변환
- **수동 편집**: 생성된 파일을 직접 편집하고 검토
- **유효성 검증**: Instructions 파일의 형식을 검증
- **문서 포맷팅**: 일관된 서식으로 문서 정리

## 사용법

### 실행
```bash
python run_vibestation_setup.bat
# 또는
python vibeStation_setup/app.py
```

### 워크플로우

1. **앱 실행**: vibeStation Setup을 실행합니다
2. **파일 확인**: 기존 copilot-instructions.md 파일이 있는지 자동으로 확인합니다
3. **옵션 선택**:
   - 파일이 없는 경우: "Setup Wizard" 탭에서 새 파일 생성
   - 파일이 있는 경우: 서식 변경 옵션 선택
4. **서식 변경**: 기존 파일을 템플릿에 맞게 변환 (백업 자동 생성)
5. **수동 편집**: "Instructions Editor" 탭에서 내용 검토 및 수정
6. **저장**: 변경사항을 파일에 저장

## 탭 설명

### 📝 Instructions Editor
- copilot-instructions.md 파일 직접 편집
- 저장, 다시 로드, 유효성 검증, 포맷팅 기능 제공

### 🛠️ Setup Wizard
- 새로운 Instructions 파일 생성을 위한 설정 마법사
- 프로젝트 정보, 코딩 설정, 문서 설정 입력

### ℹ️ Info
- 사용법 및 도움말 정보

## 특징

- **자동 백업**: 서식 변경 시 원본 파일을 .backup 파일로 보존
- **템플릿 기반**: 표준화된 Instructions 템플릿 사용
- **실시간 검증**: 파일 형식의 유효성을 즉시 확인
- **사용자 친화적**: 직관적인 GUI 인터페이스