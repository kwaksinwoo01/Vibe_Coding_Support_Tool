"""
Configuration Manager
설정 로드/저장을 위한 공통 함수를 제공합니다.
"""
from pathlib import Path
from typing import Optional


def get_config_path(filename: str) -> Path:
    """
    설정 파일 경로를 반환합니다.
    
    Args:
        filename: 설정 파일명
    
    Returns:
        설정 파일의 Path 객체
    """
    return Path(filename)


def save_instruction(instruction: str, target_file: Optional[str] = None) -> bool:
    """
    AI 지침을 파일에 저장합니다.
    
    Args:
        instruction: 저장할 지침 내용
        target_file: 대상 파일 경로 (기본값: .github/copilot-instructions.md)
    
    Returns:
        저장 성공 여부
    """
    if target_file is None:
        target_file = ".github/copilot-instructions.md"
    
    target = Path(target_file)
    
    try:
        if target.exists():
            with open(target, "a", encoding="utf-8") as f:
                f.write(f"\n- [사용자 요청]: {instruction}")
            return True
        return False
    except Exception as e:
        print(f"설정 저장 오류: {e}")
        return False


def load_config(config_file: str) -> Optional[dict]:
    """
    설정 파일을 로드합니다.
    
    Args:
        config_file: 설정 파일 경로
    
    Returns:
        설정 딕셔너리 또는 None
    """
    config_path = Path(config_file)
    
    if not config_path.exists():
        return None
    
    try:
        # 여기에 설정 로드 로직 추가 가능
        # 현재는 기본 구조만 제공
        return {}
    except Exception as e:
        print(f"설정 로드 오류: {e}")
        return None
