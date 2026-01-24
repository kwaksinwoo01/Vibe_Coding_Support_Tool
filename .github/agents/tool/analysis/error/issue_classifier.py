"""
Issue Classifier - 이슈 분류 엔진

책임:
- 사용자 입력의 이슈를 분류
- IssueClassification 결과 생성
- keyword 기반 분류 + 신뢰도 계산
"""

from typing import List, Dict, Tuple
from ...models.core.reporting_models import IssueClassification


class IssueClassifier:
    """이슈 분류 엔진"""
    
    # 이슈 타입별 키워드 맵
    CLASSIFICATION_KEYWORDS = {
        "bug": {
            "keywords": ["error", "exception", "crash", "fail", "failed", "bug", "오류", "에러"],
            "confidence": 0.95,
            "categories": {
                "implementation_error": ["typeerror", "valueerror", "indexerror", "keyerror", "attributeerror"],
                "environment_error": ["environment", "config", "setup", "install", "dependency"],
                "data_error": ["data", "invalid", "corrupt", "missing", "null"],
            }
        },
        "design_flaw": {
            "keywords": ["design", "architecture", "structure", "refactor", "설계", "아키텍처"],
            "confidence": 0.85,
            "categories": {
                "architecture": ["architecture", "design pattern", "structure", "layering"],
                "algorithm": ["algorithm", "complexity", "performance", "inefficient"],
                "interface": ["interface", "api", "contract", "protocol"],
            }
        },
        "implementation": {
            "keywords": ["implement", "code", "function", "method", "구현", "코드"],
            "confidence": 0.80,
            "categories": {}
        },
        "documentation": {
            "keywords": ["doc", "comment", "readme", "guide", "문서", "주석"],
            "confidence": 0.90,
            "categories": {}
        }
    }
    
    def classify(self, issue_description: str) -> IssueClassification:
        """
        이슈 입력을 분류
        
        Args:
            issue_description: 사용자의 이슈 설명
            
        Returns:
            IssueClassification 객체
        """
        issue_lower = issue_description.lower()
        
        # Step 1: 이슈 타입 결정
        issue_type, confidence = self._determine_issue_type(issue_lower)
        
        # Step 2: 세부 카테고리 결정
        category = self._determine_category(issue_type, issue_lower)
        
        # Step 3: 심각도 결정
        severity = self._determine_severity(issue_lower, issue_type)
        
        # Step 4: 분류 키워드 추출
        keywords = self._extract_keywords(issue_lower)
        
        return IssueClassification(
            issue_type=issue_type,
            severity=severity,
            confidence_score=confidence,
            keywords=keywords,
            category=category
        )
    
    def _determine_issue_type(self, issue_lower: str) -> Tuple[str, float]:
        """이슈 타입 결정"""
        best_match = "unknown"
        best_score = 0.0
        
        for issue_type, config in self.CLASSIFICATION_KEYWORDS.items():
            match_count = sum(1 for kw in config["keywords"] if kw in issue_lower)
            if match_count > 0:
                score = min(match_count * config["confidence"], 1.0)
                if score > best_score:
                    best_score = score
                    best_match = issue_type
        
        return best_match, best_score
    
    def _determine_category(self, issue_type: str, issue_lower: str) -> str:
        """세부 카테고리 결정"""
        if issue_type not in self.CLASSIFICATION_KEYWORDS:
            return ""
        
        categories = self.CLASSIFICATION_KEYWORDS[issue_type].get("categories", {})
        
        for category, keywords in categories.items():
            if any(kw in issue_lower for kw in keywords):
                return category
        
        return ""
    
    def _determine_severity(self, issue_lower: str, issue_type: str) -> str:
        """심각도 결정"""
        critical_keywords = ["critical", "crash", "data loss", "security", "심각"]
        high_keywords = ["error", "fail", "exception", "broken", "실패"]
        medium_keywords = ["warning", "issue", "problem", "문제"]
        
        if any(kw in issue_lower for kw in critical_keywords):
            return "critical"
        elif any(kw in issue_lower for kw in high_keywords):
            return "high"
        elif any(kw in issue_lower for kw in medium_keywords):
            return "medium"
        else:
            return "low"
    
    def _extract_keywords(self, issue_lower: str) -> List[str]:
        """관련 키워드 추출"""
        all_keywords = []
        for config in self.CLASSIFICATION_KEYWORDS.values():
            all_keywords.extend(config["keywords"])
        
        return [kw for kw in all_keywords if kw in issue_lower]


__all__ = ["IssueClassifier"]
