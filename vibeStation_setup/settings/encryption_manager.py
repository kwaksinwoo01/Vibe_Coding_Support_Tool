"""
암호화된 설정 관리자
Encrypted configuration manager using Jasypt-like approach

사용 방식:
1. Fernet 기반 대칭 암호화 (Python native)
2. 마스터 키는 환경 변수로 관리
3. 암호화된 데이터를 JSON으로 저장

설치 필요:
pip install cryptography python-dotenv
"""

import os
import json
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """설정값을 암호화하여 관리하는 클래스"""
    
    def __init__(self, config_dir: Optional[Path] = None, master_key_env: str = "APP_MASTER_KEY"):
        """
        초기화
        
        Args:
            config_dir: 설정 파일 디렉토리
            master_key_env: 마스터 키가 저장된 환경 변수명
        """
        # 올바른 경로: settings/config (settings 폴더 내의 config)
        self.config_dir = (config_dir or Path(__file__).parent / "config").resolve()
        self.config_dir.mkdir(exist_ok=True)
        
        self.master_key_env = master_key_env
        self.encrypted_config_file = self.config_dir / "encrypted_config.enc"
        self.key_file = self.config_dir / ".key"
        self.cipher_suite = None
        
        self._initialize_cipher()
    
    def _initialize_cipher(self):
        """암호화 스위트 초기화"""
        master_key = self._get_or_create_master_key()
        if master_key:
            try:
                self.cipher_suite = Fernet(master_key)
                logger.info("암호화 매니저 초기화됨")
            except Exception as e:
                logger.error(f"암호화 스위트 초기화 실패: {e}")
    
    def _get_or_create_master_key(self) -> Optional[bytes]:
        """
        마스터 키 획득 또는 생성
        
        우선순위:
        1. 환경 변수 (APP_MASTER_KEY)
        2. .key 파일
        3. 새로 생성
        """
        # 1. 환경 변수에서 확인
        env_key = os.getenv(self.master_key_env)
        if env_key:
            try:
                key_bytes = env_key.encode() if isinstance(env_key, str) else env_key
                logger.info(f"환경 변수에서 마스터 키 로드됨 (길이: {len(key_bytes)})")
                
                # 이미 .key 파일이 있으면 일치성 확인
                if self.key_file.exists():
                    try:
                        with open(self.key_file, 'rb') as f:
                            file_key = f.read()
                        if key_bytes != file_key:
                            logger.warning("⚠️ 환경 변수와 .key 파일의 마스터 키가 다릅니다!")
                            logger.warning("  이 경우 기존 저장된 데이터를 복호화할 수 없습니다.")
                            logger.info("  해결: .key 파일을 삭제하고 다시 시작하거나, 환경 변수를 수정하세요.")
                    except Exception as e:
                        logger.error(f"마스터 키 일치성 확인 실패: {e}")
                
                return key_bytes
            except Exception as e:
                logger.error(f"환경 변수 마스터 키 로드 실패: {e}")
        
        # 2. .key 파일에서 확인
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                logger.info(f".key 파일에서 마스터 키 로드됨 (길이: {len(key)})")
                return key
            except Exception as e:
                logger.error(f".key 파일 로드 실패: {e}")
        
        # 3. 새로 생성
        logger.warning("마스터 키를 생성합니다.")
        try:
            new_key = Fernet.generate_key()
            
            # .key 파일로 저장 (권한 600)
            with open(self.key_file, 'wb') as f:
                f.write(new_key)
            os.chmod(self.key_file, 0o600)  # Unix: rw------- 권한
            
            logger.info(f"새 마스터 키 생성됨: {self.key_file}")
            logger.warning(f"  환경 변수에도 저장하세요: {self.master_key_env}={new_key.decode()}")
            
            return new_key
        except Exception as e:
            logger.error(f"마스터 키 생성 실패: {e}")
            return None
    
    def encrypt_value(self, value: str) -> str:
        """
        문자열을 암호화
        
        Args:
            value: 암호화할 문자열
            
        Returns:
            base64 인코딩된 암호화된 문자열
        """
        if not self.cipher_suite:
            raise RuntimeError("암호화 매니저가 초기화되지 않았습니다")
        
        try:
            encrypted = self.cipher_suite.encrypt(value.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"암호화 실패: {e}")
            raise
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """
        문자열을 복호화
        
        Args:
            encrypted_value: base64 인코딩된 암호화된 문자열
            
        Returns:
            복호화된 문자열
        """
        if not self.cipher_suite:
            raise RuntimeError("암호화 매니저가 초기화되지 않았습니다")
        
        try:
            encrypted = base64.b64decode(encrypted_value.encode())
            decrypted = self.cipher_suite.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"복호화 실패: {e}")
            raise
    
    def save_config(self, config: Dict[str, Any], sensitive_keys: Optional[list] = None):
        """
        설정을 암호화하여 저장 (.enc 바이너리 파일만 생성)
        메모리에서 JSON 처리 후 바로 Fernet 암호화 → 파일 시스템에 평문 저장 없음
        
        Args:
            config: 저장할 설정 딕셔너리
            sensitive_keys: 사용하지 않음 (하위 호환성 유지)
        """
        if not self.cipher_suite:
            raise RuntimeError("암호화 매니저가 초기화되지 않았습니다")
        
        try:
            # 1️⃣ 메모리에서만 JSON 생성 (파일 시스템에 쓰지 않음)
            payload = json.dumps(config, ensure_ascii=False).encode("utf-8")
            logger.debug(f"메모리에서 JSON 생성: {len(payload)} bytes")
            
            # 2️⃣ 전체 페이로드를 Fernet 암호화
            encrypted_payload = self.cipher_suite.encrypt(payload)
            logger.debug(f"Fernet 암호화 완료: {len(encrypted_payload)} bytes")
            
            # 3️⃣ 임시 파일에 먼저 쓰고 안전하게 교체 (원자성 보장)
            tmp_path = self.encrypted_config_file.with_suffix(self.encrypted_config_file.suffix + ".tmp")
            with open(tmp_path, "wb") as f:
                f.write(encrypted_payload)
                f.flush()
                os.fsync(f.fileno())
            
            os.replace(tmp_path, self.encrypted_config_file)
            logger.info(f"암호화된 설정 저장됨: {self.encrypted_config_file}")
            logger.info(f"  파일 크기: {self.encrypted_config_file.stat().st_size} bytes")
            
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            raise
    def load_config(self) -> Dict[str, Any]:
        """
        암호화된 설정을 로드하여 복호화 (.enc 바이너리 파일)
        전체 JSON을 Fernet 복호화 (개별 값 복호화 없음)
        
        Returns:
            복호화된 설정 딕셔너리
        """
        if not self.cipher_suite:
            raise RuntimeError("암호화 매니저가 초기화되지 않았습니다")
        
        if not self.encrypted_config_file.exists():
            logger.warning(f"설정 파일을 찾을 수 없습니다: {self.encrypted_config_file}")
            return {}
        
        try:
            # .enc 바이너리 파일 읽기
            with open(self.encrypted_config_file, "rb") as f:
                encrypted_payload = f.read()

            # 전체 페이로드 복호화
            decrypted_payload = self.cipher_suite.decrypt(encrypted_payload)
            
            # JSON 파싱하여 평문 딕셔너리 반환
            config = json.loads(decrypted_payload.decode("utf-8"))
            
            logger.info(f"암호화된 설정 로드됨: {self.encrypted_config_file}")
            return config
        
        except json.JSONDecodeError as e:
            logger.error(f"설정 파일 파싱 실패: {e}")
            return {}
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            logger.error(f"마스터 키가 변경되었거나 파일이 손상되었을 수 있습니다.")
            return {}

    def get_value(self, key: str, default: Any = "") -> Any:
        """
        특정 키의 값을 복호화하여 반환
        
        Args:
            key: 가져올 설정 키
            default: 키가 없을 때 반환할 기본값
        
        Returns:
            복호화된 값 또는 기본값
        """
        config = self.load_config()
        return config.get(key, default)
    
    def set_value(self, key: str, value: Any, is_sensitive: bool = True) -> bool:
        """
        특정 키의 값을 설정하고 암호화하여 저장
        
        Args:
            key: 설정할 키
            value: 설정할 값
            is_sensitive: 민감한 정보인지 여부 (True면 암호화)
        
        Returns:
            저장 성공 여부
        """
        try:
            config = self.load_config()
            config[key] = value
            sensitive_keys = [key] if is_sensitive else []
            self.save_config(config, sensitive_keys=sensitive_keys)
            logger.info(f"설정값 저장됨: {key}")
            return True
        except Exception as e:
            logger.error(f"설정값 저장 실패 ({key}): {e}")
            return False
    
    def update_values(self, updates: Dict[str, Any], sensitive_keys: Optional[list] = None) -> bool:
        """
        여러 설정값을 한 번에 업데이트
        
        Args:
            updates: 업데이트할 키-값 딕셔너리
            sensitive_keys: 암호화할 키 목록 (기본값: github_token, workflow_secret)
        
        Returns:
            저장 성공 여부
        """
        try:
            if sensitive_keys is None:
                sensitive_keys = [
                    "github_token",
                    "workflow_secret",
                    "database_password",
                    "api_key"
                ]
            
            # 기존 설정 로드
            try:
                existing_config = self.load_config()
            except Exception as e:
                logger.warning(f"기존 설정 로드 실패: {e}, 빈 설정으로 시작합니다.")
                existing_config = {}
            
            # 들어오는 값이 이미 암호화된 상태인지 확인 (버그 방지)
            for key, value in updates.items():
                if isinstance(value, str) and value.startswith('gAAAAAB'):
                    logger.warning(f"⚠️ {key}: 이미 암호화된 값이 업데이트 요청에 포함되었습니다.")
                    logger.warning(f"   평문 값을 보내주세요. 암호화된 값은 저장에서 제외합니다.")
                    # 암호화된 값은 기존값으로 유지
                    if key in existing_config and existing_config[key].startswith('gAAAAAB'):
                        updates[key] = existing_config[key]
            
            config = existing_config.copy()
            config.update(updates)
            
            self.save_config(config, sensitive_keys=sensitive_keys)
            logger.info(f"{len(updates)}개 설정값 업데이트됨")
            return True
        except Exception as e:
            logger.error(f"설정값 업데이트 실패: {e}")
            return False
    
    def get_github_token(self) -> str:
        """
        GitHub 토큰을 복호화하여 반환 (전용 메서드)
        
        Returns:
            복호화된 GitHub 토큰 또는 빈 문자열
        """
        return self.get_value("github_token", "")
    
    def set_github_token(self, token: str) -> bool:
        """
        GitHub 토큰을 암호화하여 저장 (전용 메서드)
        
        Args:
            token: 저장할 GitHub 토큰
        
        Returns:
            저장 성공 여부
        """
        return self.set_value("github_token", token, is_sensitive=True)

    def _load_legacy_json(self, legacy_file: Path) -> Dict[str, Any]:
        """레거시 JSON 암호화 설정 파일 로드"""
        try:
            with open(legacy_file, "r", encoding="utf-8") as f:
                encrypted_config = json.load(f)

            decrypted_config = {}
            for key, value in encrypted_config.items():
                if isinstance(value, str) and value.startswith("gAAAAAB"):
                    try:
                        decrypted_config[key] = self.decrypt_value(value)
                        logger.debug(f"복호화됨: {key}")
                    except Exception as e:
                        logger.warning(f"{key} 복호화 실패: {e}, 원본 사용")
                        decrypted_config[key] = value
                else:
                    decrypted_config[key] = value

            logger.info(f"레거시 암호화 설정 로드됨: {legacy_file}")
            return decrypted_config
        except Exception as e:
            logger.error(f"레거시 설정 로드 실패: {e}")
            return {}


# 글로벌 인스턴스
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager(config_dir: Optional[Path] = None) -> EncryptionManager:
    """암호화 매니저 인스턴스 획득"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager(config_dir)
        return _encryption_manager

    if config_dir is not None:
        try:
            resolved = Path(config_dir).resolve()
            if _encryption_manager.config_dir.resolve() != resolved:
                _encryption_manager = EncryptionManager(config_dir)
        except Exception:
            _encryption_manager = EncryptionManager(config_dir)

    return _encryption_manager


def save_encrypted_config(config: Dict[str, Any], sensitive_keys: Optional[list] = None):
    """설정을 암호화하여 저장 (편의 함수)
    
    Args:
        config: 저장할 설정 딕셔너리
        sensitive_keys: 암호화할 키 목록
    """
    manager = get_encryption_manager()
    manager.update_values(config, sensitive_keys)


def load_encrypted_config() -> Dict[str, Any]:
    """암호화된 설정을 로드 (편의 함수)"""
    manager = get_encryption_manager()
    return manager.load_config()


def get_github_token() -> str:
    """GitHub 토큰을 복호화하여 반환 (편의 함수)"""
    manager = get_encryption_manager()
    return manager.get_github_token()


def set_github_token(token: str) -> bool:
    """GitHub 토큰을 암호화하여 저장 (편의 함수)"""
    manager = get_encryption_manager()
    return manager.set_github_token(token)


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 암호화 매니저 초기화
    manager = EncryptionManager()
    
    # 테스트 설정
    test_config = {
        "github_token": "ghp_test1234567890",
        "workflow_secret": "secret_key_123",
        "repo_path": "https://github.com/owner/repo.git",
        "main_doc": "docs/config.md",
        "branch": "main"
    }
    
    print("\n=== 설정 저장 ===")
    manager.save_config(test_config)
    
    print("\n=== 설정 로드 ===")
    loaded = manager.load_config()
    for key, value in loaded.items():
        if key in ["github_token", "workflow_secret"]:
            print(f"{key}: {value[:10]}..." if len(str(value)) > 10 else f"{key}: {value}")
        else:
            print(f"{key}: {value}")
