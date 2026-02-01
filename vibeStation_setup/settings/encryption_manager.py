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
        self.config_dir = config_dir or Path(__file__).parent / "../config"
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
                logger.info("✓ 암호화 매니저 초기화됨")
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
                return env_key.encode()
            except Exception as e:
                logger.error(f"환경 변수 마스터 키 로드 실패: {e}")
        
        # 2. .key 파일에서 확인
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                logger.info("✓ .key 파일에서 마스터 키 로드됨")
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
            
            logger.info(f"✓ 새 마스터 키 생성됨: {self.key_file}")
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
    
    def save_config(self, config: Dict[str, Any], sensitive_keys: list = None):
        """
        설정을 암호화하여 저장
        
        Args:
            config: 저장할 설정 딕셔너리
            sensitive_keys: 암호화할 키 목록 (기본값: github_token, workflow_secret, redis_url 등)
        """
        if not self.cipher_suite:
            raise RuntimeError("암호화 매니저가 초기화되지 않았습니다")
        
        if sensitive_keys is None:
            sensitive_keys = [
                "github_token",
                "workflow_secret",
                "redis_url",
                "database_password",
                "api_key"
            ]
        
        encrypted_config = {}
        
        for key, value in config.items():
            if key in sensitive_keys and value:
                # 민감한 정보는 암호화
                try:
                    encrypted_config[key] = self.encrypt_value(str(value))
                    logger.debug(f"암호화됨: {key}")
                except Exception as e:
                    logger.error(f"{key} 암호화 실패: {e}")
                    encrypted_config[key] = value
            else:
                # 일반 정보는 그대로 저장
                encrypted_config[key] = value
        
        try:
            payload = json.dumps(encrypted_config, ensure_ascii=False).encode("utf-8")
            encrypted_payload = self.cipher_suite.encrypt(payload)
            with open(self.encrypted_config_file, "wb") as f:
                f.write(encrypted_payload)
            logger.info(f"✓ 암호화된 설정 저장됨: {self.encrypted_config_file}")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            raise
    
    def load_config(self) -> Dict[str, Any]:
        """
        암호화된 설정을 로드하여 복호화
        
        Returns:
            복호화된 설정 딕셔너리
        """
        if not self.cipher_suite:
            raise RuntimeError("암호화 매니저가 초기화되지 않았습니다")
        
        if not self.encrypted_config_file.exists():
            legacy_file = self.config_dir / "encrypted_config.json"
            if legacy_file.exists():
                return self._load_legacy_json(legacy_file)
            logger.warning(f"설정 파일을 찾을 수 없습니다: {self.encrypted_config_file}")
            return {}
        
        try:
            with open(self.encrypted_config_file, "rb") as f:
                encrypted_payload = f.read()

            decrypted_payload = self.cipher_suite.decrypt(encrypted_payload)
            encrypted_config = json.loads(decrypted_payload.decode("utf-8"))
            
            decrypted_config = {}
            
            for key, value in encrypted_config.items():
                if isinstance(value, str) and value.startswith('gAAAAAB'):
                    # 암호화된 값으로 추정
                    try:
                        decrypted_config[key] = self.decrypt_value(value)
                        logger.debug(f"복호화됨: {key}")
                    except Exception as e:
                        logger.warning(f"{key} 복호화 실패: {e}, 원본 사용")
                        decrypted_config[key] = value
                else:
                    decrypted_config[key] = value
            
            logger.info(f"✓ 암호화된 설정 로드됨: {self.encrypted_config_file}")
            return decrypted_config
        
        except json.JSONDecodeError as e:
            logger.error(f"설정 파일 파싱 실패: {e}")
            return {}
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return {}

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

            logger.info(f"✓ 레거시 암호화 설정 로드됨: {legacy_file}")
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


def save_encrypted_config(config: Dict[str, Any], sensitive_keys: list = None):
    """설정을 암호화하여 저장 (편의 함수)"""
    manager = get_encryption_manager()
    manager.save_config(config, sensitive_keys)


def load_encrypted_config() -> Dict[str, Any]:
    """암호화된 설정을 로드 (편의 함수)"""
    manager = get_encryption_manager()
    return manager.load_config()


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
