"""
Configuration management utilities for vibeStation.
Handles loading and saving configuration with encryption support.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# 암호화 기능 (선택사항)
try:
    from .encryption_manager import get_encryption_manager
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


def load_env_config() -> dict:
    """Load configuration from environment variables."""
    load_dotenv()
    return {
        "github_token": os.getenv("GITHUB_TOKEN", ""),
        "workflow_secret": os.getenv("WORKFLOW_SECRET", ""),
        "repo_path": os.getenv("REPO_PATH", ""),
        "main_doc": os.getenv("MAIN_DOC", ""),
        "branch": os.getenv("BRANCH", "")
    }


def load_env_vars(config_file: Optional[Path] = None) -> dict:
    """
    환경 변수 통합 로드
    JSON 설정 파일과 환경 변수를 결합하여 반환
    
    Note: Redis support removed - now using SQLite for all persistence
    
    Args:
        config_file: JSON 설정 파일 경로 (선택사항)
    
    Returns:
        통합된 환경 변수 딕셔너리
    """
    # 환경 변수 먼저 로드
    load_dotenv()
    
    env_vars = {
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
        "WORKFLOW_SHARED_SECRET": os.getenv("WORKFLOW_SHARED_SECRET", ""),
        "REPO_PATH": os.getenv("REPO_PATH", ""),
        "MAIN_DOC": os.getenv("MAIN_DOC", ""),
        "BRANCH": os.getenv("BRANCH", "main")
    }
    
    # 암호화된 설정만 사용 (encrypted_config.enc)
    if config_file and config_file.exists():
        if ENCRYPTION_AVAILABLE:
            try:
                saved_config = load_encrypted_config(config_file.parent)
            except Exception:
                saved_config = {}
        else:
            # 암호화 미지원 환경이면 기존 환경변수만 사용
            saved_config = {}

        if "github_token" in saved_config:
            env_vars["GITHUB_TOKEN"] = saved_config["github_token"]
        if "workflow_secret" in saved_config:
            env_vars["WORKFLOW_SHARED_SECRET"] = saved_config["workflow_secret"]
        if "repo_path" in saved_config:
            env_vars["REPO_PATH"] = saved_config["repo_path"]
        if "branch" in saved_config:
            env_vars["BRANCH"] = saved_config["branch"]
    
    return env_vars


def save_env_config(config: dict):
    """Save configuration to .env file."""
    # .env 파일에 쓰기 (단순 예시, 실제로는 파일 업데이트 로직 필요)
    with open(".env", "w") as f:
        for key, value in config.items():
            f.write(f"{key.upper()}={value}\n")


def save_config(config: dict, config_file: Path):
    """설정을 JSON 파일에 저장"""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"설정 저장 실패: {e}")
        return False


def load_config(config_file: Path) -> dict:
    """설정을 JSON 파일에서 로드"""
    config: Dict[str, Any] = {}
    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
    except Exception as e:
        print(f"설정 로드 실패: {e}")

    if ENCRYPTION_AVAILABLE:
        try:
            encrypted_config = load_encrypted_config(config_file.parent)
            if encrypted_config:
                config.update(encrypted_config)
        except Exception as e:
            print(f"암호화된 설정 로드 실패: {e}")

    return config


# ============================================================================
# 암호화된 설정 관리 함수
# ============================================================================

def save_encrypted_config(config: Dict[str, Any], config_dir: Optional[Path] = None, 
                         sensitive_keys: Optional[list] = None) -> bool:
    """
    설정을 암호화하여 저장 (jasypt 스타일)
    EncryptionManager를 통해서만 저장을 수행합니다.
    
    Args:
        config: 저장할 설정 딕셔너리
        config_dir: 설정 디렉토리 (기본값: vibeStation_setup/config)
        sensitive_keys: 암호화할 키 목록
    
    Returns:
        저장 성공 여부
    
    Example:
        >>> config = {
        ...     "github_token": "ghp_xxxxx",
        ...     "repo_path": "https://github.com/owner/repo.git"
        ... }
        >>> save_encrypted_config(config)
    """
    if not ENCRYPTION_AVAILABLE:
        print("⚠ 암호화 라이브러리가 필요합니다. 설치: pip install cryptography")
        return False
    
    try:
        manager = get_encryption_manager(config_dir)
        # EncryptionManager의 update_values 메서드 사용 (이중 암호화 방지)
        return manager.update_values(config, sensitive_keys)
    except Exception as e:
        print(f"암호화된 설정 저장 실패: {e}")
        return False


def load_encrypted_config(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    암호화된 설정을 로드하여 복호화
    
    Args:
        config_dir: 설정 디렉토리
    
    Returns:
        복호화된 설정 딕셔너리
    
    Example:
        >>> config = load_encrypted_config()
        >>> token = config.get("github_token")
    """
    if not ENCRYPTION_AVAILABLE:
        print("⚠ 암호화 라이브러리를 사용할 수 없습니다.")
        return {}
    
    try:
        manager = get_encryption_manager(config_dir)
        return manager.load_config()
    except Exception as e:
        print(f"암호화된 설정 로드 실패: {e}")
        return {}


def setup_encryption(config_dir: Optional[Path] = None) -> bool:
    """
    암호화 설정 초기화 (마스터 키 생성)
    
    Args:
        config_dir: 설정 디렉토리
    
    Returns:
        초기화 성공 여부
    """
    if not ENCRYPTION_AVAILABLE:
        print("⚠ cryptography 라이브러리가 필요합니다.")
        print("  설치: pip install cryptography")
        return False
    
    try:
        manager = get_encryption_manager(config_dir)
        print("✓ 암호화 설정이 초기화되었습니다.")
        print(f"  설정 파일: {manager.encrypted_config_file}")
        print(f"  마스터 키: {manager.key_file}")
        return True
    except Exception as e:
        print(f"암호화 설정 초기화 실패: {e}")
        return False
