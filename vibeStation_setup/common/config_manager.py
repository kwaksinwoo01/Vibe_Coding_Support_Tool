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
