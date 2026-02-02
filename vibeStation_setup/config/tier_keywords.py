"""
tier_keywords.py - Centralized Tier Classification Keywords

Single source of truth for tier keyword configuration with complex scoring system.
All modules import from this file to ensure consistency and simplicity of maintenance.

Features:
- Centralized keyword management for all 6 tiers (A-F)
- Complex scoring system with base scores and context bonuses
- Easy keyword updates via tier_keywords_manager.py
- Support for multiple languages (English, Korean)

Usage:
    from config.tier_keywords import get_tier_keywords, add_keyword
    
    keywords = get_tier_keywords()
    add_keyword("C", "새 키워드", bonus_points=3.0)
"""

from typing import Dict, List, Tuple

# ============================================================================
# Tier A: Work Plan Creation
# ============================================================================
TIER_A_KEYWORDS: Dict[str, any] = {
    "max_score": 10.0,
    "keywords": [
        "create", "plan", "new plan", "work plan", "make plan", "generate plan",
        "start plan", "set up plan", "establish plan", "wpd creation",
        "작업 계획", "계획 생성", "작업 계획 생성", "새로운 작업", "첫번째 작업",
        "build", "design", "structure", "organize", "setup", "initialize",
    ]
}

# ============================================================================
# Tier B: Execute Work Plan
# ============================================================================
TIER_B_KEYWORDS: Dict[str, any] = {
    "max_score": 10.0,
    "keywords": [
        "perform", "execute", "run", "do", "implement", "carry out",
        "proceed", "move forward", "progress",
        "진행", "실행", "작업 계획 실행", "작업 실행", "진행하기", "다음 단계",
        "complete", "finish", "accomplish", "conduct", "fulfill", "deliver",
    ]
}

# ============================================================================
# Tier C: Edit/Modify Work Plan
# ============================================================================
TIER_C_KEYWORDS: Dict[str, any] = {
    "max_score": 12.0,
    "keywords": [
        "change", "modify", "edit", "update", "revise", "alter",
        "incorrectly", "wrong", "incorrect", "mistake", "error",
        "merge", "combine", "consolidate", "move", "relocate",
        "document", "file", "created", "generated",
        "수정", "변경", "편집", "업데이트", "개정", "변경하기",
        "잘못", "오류", "틀린", "부정확한", "이상한",
        "병합", "통합", "이동", "옮기기", "결합",
        "문서", "파일", "생성", "생성된", "만들어진",
        "incorrectly created", "wrongly generated", "should be merged",
        "incorrect location", "wrong path", "wrong directory",
        "문서 병합", "문서 수정", "문서 이동", "문서 생성",
    ]
}

# ============================================================================
# Tier D: Issue Analysis & Debugging
# ============================================================================
TIER_D_KEYWORDS: Dict[str, any] = {
    "max_score": 10.0,
    "keywords": [
        "error", "issue", "fails", "failure", "problem", "bug",
        "broken", "not working", "malfunction", "crash", "exception",
        "analyze", "debug", "check", "validate", "diagnose",
        "investigate", "fix", "resolve", "troubleshoot",
        "오류", "문제", "실패", "작동 안함", "버그", "오작동",
        "분석", "검토", "확인", "진단", "점검",
        "수정", "해결", "문제 해결", "디버깅",
        "why doesn't", "not working", "causing error", "throwing exception",
        "왜 안되", "왜 실패", "오류 발생", "예외 발생",
    ]
}

# ============================================================================
# Tier E: Document Management
# ============================================================================
TIER_E_KEYWORDS: Dict[str, any] = {
    "max_score": 10.0,
    "keywords": [
        "save", "mapping", "synchronize", "sync", "document",
        "metadata", "version", "field", "property", "attribute",
        "update mapping", "reflect changes", "manage document",
        "classification", "categorization", "organization",
        "저장", "매핑", "동기화", "문서", "메타데이터",
        "버전", "필드", "속성", "특성", "반영",
        "문서 관리", "분류", "카테고리", "구성",
        "save changes", "update metadata", "manage version",
        "저장하기", "메타데이터 업데이트", "버전 관리",
    ]
}

# ============================================================================
# Tier F: Unknown Logic / Clarification
# ============================================================================
TIER_F_KEYWORDS: Dict[str, any] = {
    "max_score": 5.0,
    "keywords": [
        "unclear", "ambiguous", "confused", "help", "what",
        "explain", "how", "why", "tell me", "clarify",
        "명확하지", "불명확", "혼동", "도움", "뭐",
        "설명", "어떻게", "왜", "알려줘", "명확히",
    ]
}

# ============================================================================
# Context Bonus System
# ============================================================================
CONTEXT_BONUSES: Dict[str, Dict[Tuple[str, ...], float]] = {
    "C": {
        ("incorrectly", "document"): 4.0,
        ("incorrectly", "created"): 4.0,
        ("incorrectly", "generated"): 4.0,
        ("wrong", "document"): 3.5,
        ("wrong", "created"): 3.5,
        ("merge", "document"): 3.0,
        ("combine", "document"): 3.0,
        ("move", "document"): 3.0,
        ("wrong", "directory"): 3.0,
        ("wrong", "path"): 3.0,
        ("change", "location"): 2.5,
        ("relocate", "file"): 2.5,
        ("잘못", "문서"): 4.0,
        ("잘못", "생성"): 4.0,
        ("문서", "병합"): 3.0,
        ("문서", "이동"): 3.0,
        ("잘못된", "위치"): 3.0,
    },
    "D": {
        ("error", "why"): 3.0,
        ("error", "fix"): 3.5,
        ("not", "working"): 3.0,
        ("bug", "analyze"): 3.0,
        ("debug", "issue"): 3.0,
        ("failure", "reason"): 2.5,
        ("오류", "원인"): 3.0,
        ("작동", "안함"): 3.0,
        ("문제", "해결"): 3.0,
    }
}


def get_tier_keywords() -> Dict[str, Dict]:
    """Get all tier keywords in a single dictionary"""
    return {
        "A": TIER_A_KEYWORDS,
        "B": TIER_B_KEYWORDS,
        "C": TIER_C_KEYWORDS,
        "D": TIER_D_KEYWORDS,
        "E": TIER_E_KEYWORDS,
        "F": TIER_F_KEYWORDS,
    }


def get_context_bonuses() -> Dict[str, Dict[Tuple, float]]:
    """Get context bonus configuration"""
    return CONTEXT_BONUSES


def get_tier_max_score(tier: str) -> float:
    """Get maximum score for a specific tier"""
    tier_keywords = {
        "A": TIER_A_KEYWORDS,
        "B": TIER_B_KEYWORDS,
        "C": TIER_C_KEYWORDS,
        "D": TIER_D_KEYWORDS,
        "E": TIER_E_KEYWORDS,
        "F": TIER_F_KEYWORDS,
    }
    return tier_keywords.get(tier, {}).get("max_score", 10.0)


def get_tier_keywords_list(tier: str) -> List[str]:
    """Get keyword list for a specific tier"""
    tier_keywords = {
        "A": TIER_A_KEYWORDS,
        "B": TIER_B_KEYWORDS,
        "C": TIER_C_KEYWORDS,
        "D": TIER_D_KEYWORDS,
        "E": TIER_E_KEYWORDS,
        "F": TIER_F_KEYWORDS,
    }
    return tier_keywords.get(tier, {}).get("keywords", [])


__all__ = [
    "TIER_A_KEYWORDS",
    "TIER_B_KEYWORDS",
    "TIER_C_KEYWORDS",
    "TIER_D_KEYWORDS",
    "TIER_E_KEYWORDS",
    "TIER_F_KEYWORDS",
    "CONTEXT_BONUSES",
    "get_tier_keywords",
    "get_context_bonuses",
    "get_tier_max_score",
    "get_tier_keywords_list",
]
