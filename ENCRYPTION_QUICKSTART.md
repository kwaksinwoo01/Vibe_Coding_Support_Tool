# 암호화된 설정 관리 - 빠른 시작

## 📋 개요

vibeStation은 민감한 정보(GitHub Token, API Key 등)를 **자동으로 암호화**하여 저장합니다.

- **암호화 방식**: Fernet (AES-128)
- **마스터 키**: 환경 변수 또는 파일로 자동 관리
- **저장 형식**: JSON (암호화된 값은 Base64 인코딩)

---

## 빠른 설정 (3단계)

### 1️⃣ 필수 패키지 설치

```bash
pip install cryptography python-dotenv
```

### 2️⃣ 암호화 초기화

```python
from settings.config_manager import setup_encryption

# 마스터 키 자동 생성
setup_encryption()
```

또는 CLI에서:

```bash
python -c "from settings.config_manager import setup_encryption; setup_encryption()"
```

**결과**:
- `vibeStation_setup/config/.key` 생성 (마스터 키)
- `vibeStation_setup/config/encrypted_config.json` 준비

### 3️⃣ 설정 저장 및 로드

**저장**:
```python
from settings.config_manager import save_encrypted_config

config = {
    "github_token": "ghp_your_token_here",
    "workflow_secret": "your_secret_here",
    "repo_path": "https://github.com/owner/repo"
}

save_encrypted_config(config)
```

**로드**:
```python
from settings.config_manager import load_encrypted_config

config = load_encrypted_config()
token = config["github_token"]
```

---

## 🔑 마스터 키 관리

### 자동 생성 (권장)

처음 실행 시 `.key` 파일이 자동으로 생성됩니다.

```
vibeStation_setup/config/
  ├── .key                      # 마스터 키 (자동 생성)
  └── encrypted_config.json     # 암호화된 설정
```

### 환경 변수로 관리 (보안 강화)

`.key` 파일 대신 환경 변수 사용:

**Windows (PowerShell)**:
```powershell
$env:APP_MASTER_KEY="your_key_value_here"
```

**Linux/Mac**:
```bash
export APP_MASTER_KEY="your_key_value_here"
```

**시스템 환경 변수 등록** (영구 설정):
- Windows: 시스템 속성 > 고급 > 환경 변수
- Linux/Mac: `.bashrc` 또는 `.zshrc`에 추가

---

## 📁 파일 구조

```
vibeStation_setup/
├── settings/
│   ├── encryption_manager.py      # 암호화 로직
│   ├── config_manager.py          # 설정 관리 (암호화 지원)
│   ├── ENCRYPTION_GUIDE.md        # 상세 가이드
│   └── ENCRYPTION_INTEGRATION.md  # UI 통합 방법
├── config/
│   ├── .key                       # 마스터 키 (Git 제외)
│   └── encrypted_config.json      # 암호화된 설정 (Git 포함 가능)
└── logs/
```

---

## 🔒 보안 체크리스트

```
✅ .gitignore에 다음 항목 추가:
   - vibeStation_setup/config/.key
   - vibeStation_setup/config/.env
   - *.key
   - *secret*

✅ Git에서 .key 파일 제외 (이미 .gitignore에 있음)

✅ 환경 변수 APP_MASTER_KEY 안전 보관

✅ 로그에 민감정보 출력 금지

✅ CI/CD에서 마스터 키를 시크릿으로 관리
```

---

## 🧪 테스트

암호화 기능 테스트:

```bash
python test_encryption.py
```

예상 출력:
```
[INFO] ✓ 암호화 초기화 완료
[INFO] ✓ 설정 저장 완료
[INFO] ✓ 설정 로드 완료
[INFO] ✓ 모든 테스트 통과!
```

---

## 사용 예시

### 예시 1: 설정 저장

```python
from settings.config_manager import save_encrypted_config

# GitHub 토큰 저장 (자동 암호화)
config = {
    "github_token": "ghp_abc123def456",
    "workflow_secret": "my_secret_key",
    "repo_path": "https://github.com/owner/repo",
    "branch": "main"
}

save_encrypted_config(config)
# → encrypted_config.json에 저장됨
```

### 예시 2: 설정 로드

```python
from settings.config_manager import load_encrypted_config

config = load_encrypted_config()

# 자동으로 복호화됨
print(config["github_token"])  # "ghp_abc123def456"
```

### 예시 3: UI에서 사용

```python
from settings.config_manager import load_encrypted_config, save_encrypted_config

class SettingsDialog:
    def load_settings(self):
        config = load_encrypted_config()
        self.token_input.setText(config.get("github_token", ""))
    
    def save_settings(self):
        config = {
            "github_token": self.token_input.text(),
            "repo_path": self.repo_input.text()
        }
        save_encrypted_config(config)
```

---

## 고급 설정

### 특정 키만 암호화

```python
from settings.config_manager import save_encrypted_config

config = {
    "github_token": "ghp_xxx",
    "repo_path": "https://github.com/owner/repo",
    "public_info": "some_value"
}

# github_token만 암호화
save_encrypted_config(
    config,
    sensitive_keys=["github_token"]
)
```

### Jasypt 호환성 (Java 연동)

Java와의 연동이 필요한 경우:

```python
from settings.encryption_manager import get_encryption_manager

manager = get_encryption_manager()

# 값 암호화
encrypted = manager.encrypt_value("sensitive_data")

# 값 복호화
decrypted = manager.decrypt_value(encrypted)
```

---

## 문제 해결

### Q: "암호화 라이브러리를 사용할 수 없습니다" 오류

```bash
pip install cryptography
```

### Q: ".key 파일을 찾을 수 없음" 오류

```python
from settings.config_manager import setup_encryption

# 마스터 키 재생성
setup_encryption()
```

### Q: 마스터 키 변경 방법

```python
from settings.encryption_manager import EncryptionManager
from pathlib import Path

manager = EncryptionManager()

# 기존 .key 파일 삭제
Path(manager.key_file).unlink()

# 새 마스터 키 생성
from settings.config_manager import setup_encryption
setup_encryption()
```

---

## 상세 문서

- [ENCRYPTION_GUIDE.md](ENCRYPTION_GUIDE.md) - 완전한 가이드
- [ENCRYPTION_INTEGRATION.md](ENCRYPTION_INTEGRATION.md) - UI 통합 방법

---

## 다음 단계

1. **패키지 설치**: `pip install cryptography`
2. **암호화 초기화**: `python -c "from settings.config_manager import setup_encryption; setup_encryption()"`
3. **설정 저장**: `save_encrypted_config(config)`
4. **설정 로드**: `load_encrypted_config()`

---

**문제가 있으신가요?** [Issue 등록](https://github.com/kwaksinwoo01/Vibe_Coding_Support_Tool/issues)
