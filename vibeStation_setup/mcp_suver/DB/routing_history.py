"""
routing_history.py

라우팅 히스토리 및 피드백 데이터베이스 관리

기능:
- 라우팅 결정 기록 저장
- 신뢰도 측정 히스토리 추적
- 피드백 데이터 수집 및 저장
- 라우팅 성공/실패율 계산
- 신뢰도 점수 최적화를 위한 학습 데이터

구조:
  DB/
  ├── routing_history.jsonl (각 라우팅 기록)
  ├── feedback_data.json (사용자 피드백)
  ├── tier_confidence.json (티어별 신뢰도 통계)
  └── classification_feedback.json (분류 피드백)
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
import hashlib


@dataclass
class RoutingRecord:
    """단일 라우팅 기록"""
    timestamp: str
    user_input: str  # 해시된 입력
    user_input_hash: str
    classified_tier: str
    classification_confidence: float
    executed_tier: str
    execution_status: str  # SUCCESS, FAILED, PARTIAL
    execution_confidence: float
    next_node: Optional[str]
    routing_confidence: float
    duration_ms: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    feedback: Optional[str] = None  # 사용자 피드백
    feedback_tier: Optional[str] = None  # 피드백 정정 티어


@dataclass
class RoutingStatistics:
    """라우팅 통계"""
    tier: str
    total_routes: int
    successful_routes: int
    failed_routes: int
    partial_routes: int
    avg_confidence: float
    success_rate: float
    avg_execution_time_ms: float


class RoutingHistoryDB:
    """라우팅 히스토리 데이터베이스"""
    
    def __init__(self, db_root: Path):
        self.db_root = Path(db_root)
        self.db_root.mkdir(parents=True, exist_ok=True)
        
        self.history_file = self.db_root / "routing_history.jsonl"
        self.feedback_file = self.db_root / "feedback_data.json"
        self.tier_stats_file = self.db_root / "tier_confidence.json"
        self.classification_feedback_file = self.db_root / "classification_feedback.json"
        
        # 초기화
        self._init_files()
    
    def _init_files(self):
        """필요한 파일 초기화"""
        if not self.feedback_file.exists():
            self.feedback_file.write_text(json.dumps({"feedbacks": []}, indent=2))
        
        if not self.tier_stats_file.exists():
            stats = {tier: asdict(RoutingStatistics(tier, 0, 0, 0, 0, 0.0, 0.0, 0.0)) for tier in ["A", "B", "C", "D", "E", "F"]}
            self.tier_stats_file.write_text(json.dumps(stats, indent=2))
        
        if not self.classification_feedback_file.exists():
            self.classification_feedback_file.write_text(json.dumps({"feedbacks": []}, indent=2))
    
    def record_routing(self, record: RoutingRecord):
        """라우팅 기록 저장"""
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(record)) + '\n')
    
    def add_feedback(self, user_input_hash: str, feedback: str, corrected_tier: Optional[str] = None):
        """피드백 추가"""
        feedbacks = json.loads(self.feedback_file.read_text(encoding='utf-8'))
        
        feedbacks["feedbacks"].append({
            "timestamp": datetime.now().isoformat(),
            "user_input_hash": user_input_hash,
            "feedback": feedback,
            "corrected_tier": corrected_tier
        })
        
        self.feedback_file.write_text(json.dumps(feedbacks, indent=2, ensure_ascii=False), encoding='utf-8')
    
    def add_classification_feedback(self, user_input: str, classified_tier: str, actual_tier: str, notes: str = ""):
        """분류 피드백 추가"""
        feedbacks = json.loads(self.classification_feedback_file.read_text(encoding='utf-8'))
        
        feedbacks["feedbacks"].append({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input[:100],  # 처음 100자만
            "classified_tier": classified_tier,
            "actual_tier": actual_tier,
            "correct": classified_tier == actual_tier,
            "notes": notes
        })
        
        self.classification_feedback_file.write_text(
            json.dumps(feedbacks, indent=2, ensure_ascii=False), 
            encoding='utf-8'
        )
    
    def get_tier_statistics(self, tier: str) -> Optional[RoutingStatistics]:
        """티어별 통계 조회"""
        stats = json.loads(self.tier_stats_file.read_text(encoding='utf-8'))
        if tier in stats:
            return RoutingStatistics(**stats[tier])
        return None
    
    def update_tier_statistics(self, record: RoutingRecord):
        """티어별 통계 업데이트"""
        stats = json.loads(self.tier_stats_file.read_text(encoding='utf-8'))
        
        tier = record.executed_tier
        if tier not in stats:
            stats[tier] = asdict(RoutingStatistics(tier, 0, 0, 0, 0, 0.0, 0.0, 0.0))
        
        tier_stat = stats[tier]
        tier_stat["total_routes"] += 1
        
        if record.execution_status == "SUCCESS":
            tier_stat["successful_routes"] += 1
        elif record.execution_status == "FAILED":
            tier_stat["failed_routes"] += 1
        else:
            tier_stat["partial_routes"] += 1
        
        # 평균 신뢰도 업데이트 (가중 평균)
        total = tier_stat["total_routes"]
        old_avg = tier_stat["avg_confidence"]
        tier_stat["avg_confidence"] = (old_avg * (total - 1) + record.execution_confidence) / total
        
        # 성공률 계산
        tier_stat["success_rate"] = tier_stat["successful_routes"] / total if total > 0 else 0.0
        
        # 평균 실행 시간 업데이트
        old_time_avg = tier_stat["avg_execution_time_ms"]
        tier_stat["avg_execution_time_ms"] = (old_time_avg * (total - 1) + record.duration_ms) / total
        
        self.tier_stats_file.write_text(json.dumps(stats, indent=2))
    
    def get_recent_routing_records(self, count: int = 100) -> List[RoutingRecord]:
        """최근 라우팅 기록 조회"""
        if not self.history_file.exists():
            return []
        
        records = []
        with open(self.history_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-count:]:
                try:
                    data = json.loads(line)
                    records.append(RoutingRecord(**data))
                except json.JSONDecodeError:
                    pass
        
        return records
    
    def get_classification_accuracy(self, window: int = 100) -> Dict[str, float]:
        """분류 정확도 조회"""
        feedbacks_data = json.loads(self.classification_feedback_file.read_text(encoding='utf-8'))
        feedbacks = feedbacks_data.get("feedbacks", [])[-window:]
        
        tier_accuracy = {}
        for feedback in feedbacks:
            tier = feedback["classified_tier"]
            if tier not in tier_accuracy:
                tier_accuracy[tier] = {"correct": 0, "total": 0}
            
            tier_accuracy[tier]["total"] += 1
            if feedback["correct"]:
                tier_accuracy[tier]["correct"] += 1
        
        # 백분율로 변환
        return {
            tier: (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0.0
            for tier, data in tier_accuracy.items()
        }
    
    @staticmethod
    def hash_user_input(user_input: str) -> str:
        """사용자 입력 해시"""
        return hashlib.sha256(user_input.encode()).hexdigest()[:16]
