"""
Configuration management utilities for vibeStation.
Handles loading and saving configuration from .env and JSON files.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv


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


def load_env_vars(config_file: Path = None) -> dict:
    """
    환경 변수 통합 로드
    JSON 설정 파일과 환경 변수를 결합하여 반환
    
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
        "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "REDIS_HOST": os.getenv("REDIS_HOST", "localhost"),
        "REDIS_PORT": int(os.getenv("REDIS_PORT", 6379)),
        "REDIS_DB": int(os.getenv("REDIS_DB", 0)),
        "AGENT_PATH": os.getenv("AGENT_PATH", ""),
        "REPO_PATH": os.getenv("REPO_PATH", ""),
        "MAIN_DOC": os.getenv("MAIN_DOC", ""),
        "BRANCH": os.getenv("BRANCH", "main")
    }
    
    # JSON 설정 파일이 있으면 값 덮어쓰기
    if config_file and config_file.exists():
        saved_config = load_config(config_file)
        if "github_token" in saved_config:
            env_vars["GITHUB_TOKEN"] = saved_config["github_token"]
        if "workflow_secret" in saved_config:
            env_vars["WORKFLOW_SHARED_SECRET"] = saved_config["workflow_secret"]
        if "redis_url" in saved_config:
            env_vars["REDIS_URL"] = saved_config["redis_url"]
        if "repo_path" in saved_config:
            env_vars["REPO_PATH"] = saved_config["repo_path"]
        if "branch" in saved_config:
            env_vars["BRANCH"] = saved_config["branch"]
        if "agent_path" in saved_config:
            env_vars["AGENT_PATH"] = saved_config["agent_path"]
    
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
    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"설정 로드 실패: {e}")
    return {}
