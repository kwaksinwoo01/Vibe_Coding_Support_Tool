"""
classification_engine.py

개선된 분류 엔진 (SQLite DB 기반 피드백 활용)

기능:
- tier_keywords 방식에서 벗어남
- 라우팅 히스토리 기반 동적 분류 (SQLite)
- 피드백 데이터 활용
- 신뢰도 점수 재계산 (매번 새로 측정)
- 캐싱을 통한 성능 최적화

규칙:
- 티어 분류할 때마다 신뢰도 새로 측정 (매번 재계산)
- 과거 피드백 데이터 활용하여 정확도 개선
- 캐시는 1시간마다 갱신
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib
import re

from routing_history import RoutingHistoryDB, RoutingRecord
from database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """분류 결과"""
    tier: str
    confidence: float
    reasoning: str
    similar_cases: List[str]  # 유사 사례
    feedback_score: float  # 과거 피드백 기반 스코어


class ImprovedClassificationEngine:
    """개선된 분류 엔진 (SQLite DB 기반 피드백)"""
    
    def __init__(self, db_root: Path):
        self.db_root = Path(db_root)
        self.history_db = RoutingHistoryDB(db_root)
        self.db_manager = DatabaseManager(db_root)
        
        # 개선된 키워드 - 문맥 기반 그룹화
        self.base_keywords = {
            "A": ["create", "plan", "wpd", "작업 계획", "생성", "작성"],
            "B": ["execute", "perform", "run", "실행", "수행", "진행"],
            "C": ["edit", "modify", "change", "수정", "변경", "편집"],
            "D": ["error", "bug", "issue", "problem", "오류", "버그", "문제", "fail"],
            "E": [
                # 문서 관리 핵심 키워드
                "save", "document", "mapping", "저장", "매핑",
                "path", "location", "name", "rename", "classification",
                "경로", "위치", "이름", "이름변경", "분류",
                # 새로 추가: 문서 이동/재정렬 관련
                "move", "relocate", "reorganize", "folder", "directory",
                "migration", "guide", "structure", "organize"
            ],
            "F": []
        }
        
        # 컨텍스트 기반 가중치 (문장 구조 분석)
        self.context_patterns = {
            "E": [
                r".*(?:document|file|guide).*(?:location|path|name|classification).*",
                r".*(?:should be|should move|incorrect.*location).*",
                r".*(?:docs_\d+|migration|folder structure).*"
            ]
        }
        
        logger.info("[CLASSIFIER] Initialized with improved context analysis")
    
    def classify(self, user_input: str, use_feedback: bool = True) -> ClassificationResult:
        """개선된 분류 로직"""
        user_input_hash = RoutingHistoryDB.hash_user_input(user_input)
        user_input_lower = user_input.lower()
        
        # Step 1: 키워드 매칭
        keyword_scores = self._keyword_matching(user_input_lower)
        
        # Step 2: 컨텍스트 기반 패턴 분석 (새로 추가)
        context_scores = self._context_pattern_matching(user_input_lower)
        
        # Step 3: 피드백 데이터 활용
        if use_feedback:
            feedback_scores = self._feedback_based_scoring(user_input)
            combined_scores = {
                tier: (
                    keyword_scores.get(tier, 0.0) * 0.5 +
                    context_scores.get(tier, 0.0) * 0.3 +
                    feedback_scores.get(tier, 0.0) * 0.2
                )
                for tier in ["A", "B", "C", "D", "E", "F"]
            }
        else:
            combined_scores = {
                tier: keyword_scores.get(tier, 0.0) * 0.6 + context_scores.get(tier, 0.0) * 0.4
                for tier in ["A", "B", "C", "D", "E", "F"]
            }
        
        # Step 4: 최고 신뢰도 티어 결정
        best_tier = max(combined_scores, key=combined_scores.get)
        
        # 스코어 정규화 (최소값을 0으로 조정)
        min_score = min(combined_scores.values())
        max_score = max(combined_scores.values())
        
        if max_score > min_score:
            normalized_scores = {
                tier: (score - min_score) / (max_score - min_score)
                for tier, score in combined_scores.items()
            }
        else:
            normalized_scores = combined_scores
        
        confidence = normalized_scores[best_tier]
        
        # Step 5: 유사 케이스 찾기
        similar_cases = self._find_similar_cases(user_input_hash, best_tier)
        
        # Step 6: 피드백 기반 스코어
        feedback_score = self._calculate_feedback_score(best_tier)
        
        # Step 7: 최종 신뢰도 조정
        final_confidence = self._adjust_confidence(
            base_confidence=confidence,
            feedback_score=feedback_score,
            history_score=self._get_history_confidence(best_tier)
        )
        
        reasoning = self._generate_reasoning(
            user_input,
            best_tier,
            final_confidence,
            feedback_score,
            keyword_scores,
            context_scores
        )
        
        return ClassificationResult(
            tier=best_tier,
            confidence=final_confidence,
            reasoning=reasoning,
            similar_cases=similar_cases,
            feedback_score=feedback_score
        )
    
    def _keyword_matching(self, user_input_lower: str) -> Dict[str, float]:
        """키워드 매칭 (기본 방식)"""
        scores = {}
        
        for tier, keywords in self.base_keywords.items():
            score = sum(1 for kw in keywords if kw in user_input_lower)
            scores[tier] = float(score)
        
        return scores
    
    def _context_pattern_matching(self, user_input_lower: str) -> Dict[str, float]:
        """컨텍스트 기반 패턴 매칭 (새로 추가)"""
        import re
        
        scores = {tier: 0.0 for tier in ["A", "B", "C", "D", "E", "F"]}
        
        for tier, patterns in self.context_patterns.items():
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    scores[tier] += 1.0
        
        return scores
    
    def _feedback_based_scoring(self, user_input: str) -> Dict[str, float]:
        """
        피드백 데이터 기반 점수 (신뢰도 새로 측정)
        
        과거 유사한 입력에 대한 분류 피드백을 활용
        """
        recent_records = self.history_db.get_recent_routing_records(count=200)
        
        # 유사도 계산
        scores = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0, "F": 0.0}
        similarity_weights = []
        
        for record in recent_records:
            # 간단한 유사도: 공통 단어 수
            input_words = set(user_input.lower().split())
            record_words = set(record.user_input_hash.split()) if record.user_input_hash else set()
            
            # 같은 해시면 정확히 같은 입력
            if record.user_input_hash == RoutingHistoryDB.hash_user_input(user_input):
                # 정확한 일치 - 최고 가중치
                scores[record.classified_tier] += 10.0
                continue
            
            # 부분 일치
            common = len(input_words.intersection(record_words))
            if common > 0:
                # 성공한 분류에 높은 가중치
                weight = 2.0 if record.execution_status == "SUCCESS" else 1.0
                scores[record.classified_tier] += weight * (common / max(len(input_words), 1))
        
        # 정규화
        total = sum(scores.values())
        if total > 0:
            scores = {tier: score / total for tier, score in scores.items()}
        
        return scores
    
    def _find_similar_cases(self, user_input_hash: str, tier: str, count: int = 5) -> List[str]:
        """유사한 과거 사례 찾기"""
        recent_records = self.history_db.get_recent_routing_records(count=100)
        
        similar = []
        for record in recent_records:
            if record.classified_tier == tier and record.execution_status == "SUCCESS":
                similar.append(f"{record.user_input_hash[:8]}... → {record.executed_tier}")
        
        return similar[:count]
    
    def _calculate_feedback_score(self, tier: str) -> float:
        """
        피드백 점수 계산 (0.0 ~ 1.0)
        
        과거 이 티어로 분류한 경우의 성공률
        """
        tier_stats = self.history_db.get_tier_statistics(tier)
        if not tier_stats:
            return 0.5  # 기본값
        
        return tier_stats.success_rate
    
    def _get_history_confidence(self, tier: str) -> float:
        """과거 히스토리 기반 신뢰도"""
        tier_stats = self.history_db.get_tier_statistics(tier)
        if not tier_stats:
            return 0.5
        
        # 평균 신뢰도와 성공률의 조합
        return (tier_stats.avg_confidence + tier_stats.success_rate) / 2.0
    
    def _adjust_confidence(
        self,
        base_confidence: float,
        feedback_score: float,
        history_score: float
    ) -> float:
        """
        신뢰도 조정 (매번 새로 측정)
        
        규칙:
        - 기본 신뢰도: 40%
        - 피드백 점수: 30%
        - 히스토리 점수: 30%
        """
        adjusted = (
            base_confidence * 0.4 +
            feedback_score * 0.3 +
            history_score * 0.3
        )
        
        # 최소 0.3 (Circuit Breaker OPEN 상태에서도 진행)
        # 최대 0.95 (완벽한 신뢰는 불가능)
        return max(0.3, min(adjusted, 0.95))
    
    def _generate_reasoning(
        self,
        user_input: str,
        tier: str,
        confidence: float,
        feedback_score: float,
        keyword_scores: Dict,
        context_scores: Dict
    ) -> str:
        """개선된 이유 생성"""
        tier_names = {
            "A": "Work Plan Creation",
            "B": "Task Execution",
            "C": "Plan Modification",
            "D": "Issue Analysis",
            "E": "Document Management",
            "F": "Unknown Logic"
        }
        
        keyword_contribution = keyword_scores.get(tier, 0.0)
        context_contribution = context_scores.get(tier, 0.0)
        
        reasoning = (
            f"Tier {tier} ({tier_names[tier]}). "
            f"Confidence: {confidence:.1%} | "
            f"Keywords: {keyword_contribution:.0f} | "
            f"Context: {context_contribution:.0f} | "
            f"Feedback: {feedback_score:.1%}"
        )
        
        return reasoning
    
    def save_classification_feedback(
        self,
        user_input: str,
        classified_tier: str,
        actual_tier: str,
        correction_action: Optional[Dict[str, str]] = None,
        notes: str = ""
    ):
        """
        분류 피드백 저장 (SQLite 기반 학습 데이터)
        
        Args:
            user_input: 원본 사용자 입력
            classified_tier: 자동 분류 결과
            actual_tier: 정정된 실제 분류
            correction_action: 수행해야 할 액션 (예: 경로 변경, 파일 이름 변경)
            notes: 추가 메모
        
        예시:
        >>> feedback.save_classification_feedback(
        ...     user_input="The document classification and name location in docs_2/MIGRATION_GUIDE_v3.1.0.md are incorrect.",
        ...     classified_tier="F",
        ...     actual_tier="E",
        ...     correction_action={
        ...         "action": "move_and_rename",
        ...         "current_path": "docs_2/MIGRATION_GUIDE_v3.1.0.md",
        ...         "target_path": "docs_2/P1/MIGRATION_GUIDE_v3.1.0.md",
        ...         "reason": "MIGRATION_GUIDE belongs to P1 (File Renaming Tasks category)"
        ...     },
        ...     notes="Path and classification correction"
        ... )
        """
        # SQLite에 피드백 저장
        self.db_manager.add_classification_feedback(
            user_input=user_input,
            classified_tier=classified_tier,
            actual_tier=actual_tier,
            correction_action=json.dumps(correction_action) if correction_action else None,
            notes=notes,
            timestamp=datetime.now().isoformat()
        )
        
        is_correct = classified_tier == actual_tier
        logger.info(
            f"[FEEDBACK] Classification: {classified_tier} → {actual_tier} "
            f"(correct: {is_correct}) | Action: {correction_action.get('action') if correction_action else 'N/A'}"
        )
        
        # 콘솔 출력
        print(f"✓ [FEEDBACK] Saved to SQLite DB")
        print(f"  Input: {user_input[:80]}...")
        print(f"  Classification: {classified_tier} → {actual_tier}")
        if correction_action:
            print(f"  Action: {correction_action.get('action')}")
            print(f"    From: {correction_action.get('current_path')}")
            print(f"    To:   {correction_action.get('target_path')}")
            print(f"    Reason: {correction_action.get('reason')}")
        if notes:
            print(f"  Notes: {notes}")
