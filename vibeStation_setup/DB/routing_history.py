"""
routing_history.py

SQLite 기반 라우팅 히스토리 및 피드백 데이터베이스 관리

기능:
- 라우팅 결정 기록 저장 (SQLite)
- 신뢰도 측정 히스토리 추적
- 피드백 데이터 수집 및 저장
- 라우팅 성공/실패율 계산
- 신뢰도 점수 최적화를 위한 학습 데이터
- JSON 파일에서 SQLite로 마이그레이션

구조:
  DB/
  ├── vibestation.db (SQLite 데이터베이스)
  ├── database.py (DB 관리 모듈)
  └── routing_history.py (이 파일)
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
import hashlib

from database import DatabaseManager

logger = logging.getLogger(__name__)


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
    """SQLite 기반 라우팅 히스토리 데이터베이스"""
    
    def __init__(self, db_root: Path):
        self.db_root = Path(db_root)
        self.db_root.mkdir(parents=True, exist_ok=True)
        
        # SQLite 데이터베이스 관리자
        self.db_manager = DatabaseManager(self.db_root)
        
        # 레거시 파일 경로 (마이그레이션용)
        self.history_file = self.db_root / "routing_history.jsonl"
        self.feedback_file = self.db_root / "feedback_data.json"
        self.tier_stats_file = self.db_root / "tier_confidence.json"
        self.classification_feedback_file = self.db_root / "classification_feedback.json"
    
    def record_routing(self, record: RoutingRecord):
        """라우팅 기록 저장"""
        self.db_manager.insert_routing_record(asdict(record))
        
        # 티어 통계 업데이트
        self.update_tier_statistics(record)
        
        logger.info(f"[ROUTING] Recorded: {record.executed_tier} (confidence: {record.execution_confidence:.2f})")
    
    def add_feedback(self, user_input_hash: str, feedback: str, corrected_tier: Optional[str] = None):
        """피드백 추가"""
        feedback_id = self.db_manager.add_feedback(user_input_hash, feedback, corrected_tier)
        logger.info(f"[FEEDBACK] Added feedback #{feedback_id}")
    
    def add_classification_feedback(self, user_input: str, classified_tier: str, actual_tier: str, notes: str = ""):
        """분류 피드백 추가"""
        feedback_id = self.db_manager.add_classification_feedback(
            user_input, classified_tier, actual_tier, notes
        )
        is_correct = classified_tier == actual_tier
        logger.info(f"[CLASSIFICATION] Feedback #{feedback_id}: {classified_tier} → {actual_tier} (correct: {is_correct})")
    
    def get_tier_statistics(self, tier: str) -> Optional[RoutingStatistics]:
        """티어별 통계 조회"""
        stats = self.db_manager.get_tier_statistics(tier)
        if stats:
            return RoutingStatistics(**stats)
        return None
    
    def update_tier_statistics(self, record: RoutingRecord):
        """티어별 통계 업데이트"""
        tier = record.executed_tier
        
        # 현재 통계 조회
        current_stats = self.db_manager.get_tier_statistics(tier)
        
        if current_stats:
            # 업데이트할 값 계산
            total = current_stats['total_routes'] + 1
            
            # 상태별 카운트 업데이트
            successful = current_stats['successful_routes']
            failed = current_stats['failed_routes']
            partial = current_stats['partial_routes']
            
            if record.execution_status == "SUCCESS":
                successful += 1
            elif record.execution_status == "FAILED":
                failed += 1
            else:
                partial += 1
            
            # 평균 신뢰도 (가중 평균)
            old_avg_confidence = current_stats['avg_confidence']
            new_avg_confidence = (old_avg_confidence * (total - 1) + record.execution_confidence) / total
            
            # 성공률
            success_rate = successful / total if total > 0 else 0.0
            
            # 평균 실행 시간
            old_avg_time = current_stats['avg_execution_time_ms']
            new_avg_time = (old_avg_time * (total - 1) + record.duration_ms) / total
            
            # DB 업데이트
            self.db_manager.update_tier_statistics(tier, {
                'total_routes': total,
                'successful_routes': successful,
                'failed_routes': failed,
                'partial_routes': partial,
                'avg_confidence': new_avg_confidence,
                'success_rate': success_rate,
                'avg_execution_time_ms': new_avg_time
            })
    
    def get_recent_routing_records(self, count: int = 100) -> List[RoutingRecord]:
        """최근 라우팅 기록 조회"""
        records_dict = self.db_manager.get_recent_routing_records(count)
        return [RoutingRecord(**record) for record in records_dict]
    
    def get_routing_records_by_tier(self, tier: str, count: int = 100) -> List[RoutingRecord]:
        """티어별 라우팅 기록 조회"""
        records_dict = self.db_manager.get_routing_records_by_tier(tier, count)
        return [RoutingRecord(**record) for record in records_dict]
    
    def get_classification_accuracy(self, tier: Optional[str] = None, window: int = 100) -> Dict[str, float]:
        """분류 정확도 조회"""
        return self.db_manager.get_classification_accuracy(tier, window)
    
    # =========================================================================
    # 마이그레이션 함수 (JSON → SQLite)
    # =========================================================================
    
    def migrate_from_json(self) -> Dict[str, int]:
        """JSON 파일에서 SQLite로 데이터 마이그레이션"""
        import shutil
        
        migration_stats = {
            'routing_records': 0,
            'feedbacks': 0,
            'classification_feedbacks': 0
        }
        
        logger.info("[MIGRATION] Starting JSON to SQLite migration...")
        
        # 1. 라우팅 히스토리 마이그레이션
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            self.db_manager.insert_routing_record(data)
                            migration_stats['routing_records'] += 1
                        except json.JSONDecodeError:
                            pass
                logger.info(f"[MIGRATION] ✓ Migrated {migration_stats['routing_records']} routing records")
            except Exception as e:
                logger.error(f"[MIGRATION] ✗ Error migrating routing records: {e}")
        
        # 2. 피드백 마이그레이션
        if self.feedback_file.exists():
            try:
                feedbacks_data = json.loads(self.feedback_file.read_text(encoding='utf-8'))
                for feedback in feedbacks_data.get('feedbacks', []):
                    self.db_manager.add_feedback(
                        feedback.get('user_input_hash'),
                        feedback.get('feedback', ''),
                        feedback.get('corrected_tier')
                    )
                    migration_stats['feedbacks'] += 1
                logger.info(f"[MIGRATION] ✓ Migrated {migration_stats['feedbacks']} feedbacks")
            except Exception as e:
                logger.error(f"[MIGRATION] ✗ Error migrating feedbacks: {e}")
        
        # 3. 분류 피드백 마이그레이션
        if self.classification_feedback_file.exists():
            try:
                feedbacks_data = json.loads(self.classification_feedback_file.read_text(encoding='utf-8'))
                for feedback in feedbacks_data.get('feedbacks', []):
                    self.db_manager.add_classification_feedback(
                        feedback.get('user_input', ''),
                        feedback.get('classified_tier', ''),
                        feedback.get('actual_tier', ''),
                        feedback.get('notes', '')
                    )
                    migration_stats['classification_feedbacks'] += 1
                logger.info(f"[MIGRATION] ✓ Migrated {migration_stats['classification_feedbacks']} classification feedbacks")
            except Exception as e:
                logger.error(f"[MIGRATION] ✗ Error migrating classification feedbacks: {e}")
        
        # 4. 티어 통계 마이그레이션
        if self.tier_stats_file.exists():
            try:
                stats_data = json.loads(self.tier_stats_file.read_text(encoding='utf-8'))
                for tier, stats in stats_data.items():
                    if tier in ['A', 'B', 'C', 'D', 'E', 'F']:
                        self.db_manager.update_tier_statistics(tier, stats)
                logger.info("[MIGRATION] ✓ Migrated tier statistics")
            except Exception as e:
                logger.error(f"[MIGRATION] ✗ Error migrating tier statistics: {e}")
        
        logger.info("[MIGRATION] Migration completed successfully!")
        return migration_stats
    
    def backup_json_files(self) -> Path:
        """JSON 파일 백업"""
        import shutil
        
        backup_dir = self.db_root / f"json_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        json_files = [self.history_file, self.feedback_file, 
                     self.tier_stats_file, self.classification_feedback_file]
        
        for file in json_files:
            if file.exists():
                shutil.copy2(file, backup_dir / file.name)
        
        logger.info(f"[BACKUP] JSON files backed up to {backup_dir}")
        return backup_dir
    
    def get_db_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계"""
        return self.db_manager.get_db_info()
    
    @staticmethod
    def hash_user_input(user_input: str) -> str:
        """사용자 입력 해시"""
        return hashlib.sha256(user_input.encode()).hexdigest()[:16]
