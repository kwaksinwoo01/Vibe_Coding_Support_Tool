"""
Monitoring.py - Legacy Entry Point
기존 호환성을 위한 레거시 진입점입니다.
새로운 모듈 구조로 재조직되었습니다:
- vibeStation_monitor/ - 모니터링 UI
- mcp_suver/ - MCP 서버 엔진
- common/ - 공통 유틸리티
- vibeStation_setup/ - 설치 마법사

이 파일은 하위 호환성을 위해 유지되며, 
실제 구현은 vibeStation_monitor.main_window를 사용합니다.
"""
import sys
from vibeStation_monitor.main_window import main

if __name__ == "__main__":
    # 새로운 모듈 구조의 main 함수 호출
    main()