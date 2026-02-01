"""
database.py

SQLite 기반 데이터베이스 관리 모듈

기능:
- SQLite 데이터베이스 연결 관리
- 테이블 스키마 생성 및 마이그레이션
- 기본 CRUD 작업
- 트랜잭션 관리
- 데이터베이스 초기화 및 백업

테이블 구조:
- routing_history: 라우팅 기록
- tier_statistics: 티어별 통계
- feedback: 사용자 피드백
- classification_feedback: 분류 피드백
- cache: 캐시 데이터
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite 데이터베이스 관리자"""
    
    def __init__(self, db_path: Path):
        """
        데이터베이스 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 데이터베이스 파일 경로
        self.db_file = self.db_path / "vibestation.db"
        
        # 초기화
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(str(self.db_file))
        conn.row_factory = sqlite3.Row  # 딕셔너리 형식으로 결과 반환
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """데이터베이스 테이블 초기화"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 라우팅 히스토리 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input_hash TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    classified_tier TEXT NOT NULL,
                    classification_confidence REAL NOT NULL,
                    executed_tier TEXT NOT NULL,
                    execution_status TEXT NOT NULL,
                    execution_confidence REAL NOT NULL,
                    next_node TEXT,
                    routing_confidence REAL NOT NULL,
                    duration_ms REAL NOT NULL,
                    errors TEXT,  -- JSON 배열
                    warnings TEXT,  -- JSON 배열
                    feedback TEXT,
                    feedback_tier TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, user_input_hash)
                )
            """)
            
            # 2. 티어별 통계 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tier_statistics (
                    tier TEXT PRIMARY KEY,
                    total_routes INTEGER DEFAULT 0,
                    successful_routes INTEGER DEFAULT 0,
                    failed_routes INTEGER DEFAULT 0,
                    partial_routes INTEGER DEFAULT 0,
                    avg_confidence REAL DEFAULT 0.0,
                    success_rate REAL DEFAULT 0.0,
                    avg_execution_time_ms REAL DEFAULT 0.0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 기본 티어 초기화 (A~F)
            for tier in ['A', 'B', 'C', 'D', 'E', 'F']:
                cursor.execute("""
                    INSERT OR IGNORE INTO tier_statistics (tier)
                    VALUES (?)
                """, (tier,))
            
            # 3. 피드백 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input_hash TEXT NOT NULL,
                    feedback_text TEXT NOT NULL,
                    corrected_tier TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. 분류 피드백 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classification_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    classified_tier TEXT NOT NULL,
                    actual_tier TEXT NOT NULL,
                    is_correct BOOLEAN NOT NULL,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 5. 캐시 테이블 (TTL 기반)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    cache_value TEXT NOT NULL,  -- JSON
                    ttl_seconds INTEGER DEFAULT 3600,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL
                )
            """)
            
            # 6. 인덱스 생성 (성능 최적화)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_routing_history_timestamp
                ON routing_history(timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_routing_history_tier
                ON routing_history(executed_tier)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_expires
                ON cache(expires_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_classification_feedback_tier
                ON classification_feedback(classified_tier)
            """)
            
            logger.info("[DB] Database initialized successfully")
    
    # =========================================================================
    # Routing History 작업
    # =========================================================================
    
    def insert_routing_record(self, record_data: Dict[str, Any]) -> int:
        """라우팅 기록 저장"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO routing_history (
                    timestamp, user_input_hash, user_input,
                    classified_tier, classification_confidence,
                    executed_tier, execution_status, execution_confidence,
                    next_node, routing_confidence, duration_ms,
                    errors, warnings, feedback, feedback_tier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_data.get('timestamp'),
                record_data.get('user_input_hash'),
                record_data.get('user_input', ''),
                record_data.get('classified_tier'),
                record_data.get('classification_confidence', 0.0),
                record_data.get('executed_tier'),
                record_data.get('execution_status'),
                record_data.get('execution_confidence', 0.0),
                record_data.get('next_node'),
                record_data.get('routing_confidence', 0.0),
                record_data.get('duration_ms', 0.0),
                json.dumps(record_data.get('errors', [])),
                json.dumps(record_data.get('warnings', [])),
                record_data.get('feedback'),
                record_data.get('feedback_tier')
            ))
            
            return cursor.lastrowid
    
    def get_recent_routing_records(self, count: int = 100) -> List[Dict[str, Any]]:
        """최근 라우팅 기록 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM routing_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (count,))
            
            records = []
            for row in cursor.fetchall():
                record = dict(row)
                record['errors'] = json.loads(record['errors'] or '[]')
                record['warnings'] = json.loads(record['warnings'] or '[]')
                records.append(record)
            
            return records
    
    def get_routing_records_by_tier(self, tier: str, count: int = 100) -> List[Dict[str, Any]]:
        """티어별 라우팅 기록 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM routing_history
                WHERE executed_tier = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (tier, count))
            
            records = []
            for row in cursor.fetchall():
                record = dict(row)
                record['errors'] = json.loads(record['errors'] or '[]')
                record['warnings'] = json.loads(record['warnings'] or '[]')
                records.append(record)
            
            return records
    
    # =========================================================================
    # 티어 통계 작업
    # =========================================================================
    
    def update_tier_statistics(self, tier: str, update_data: Dict[str, Any]):
        """티어별 통계 업데이트"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 현재 통계 조회
            cursor.execute("""
                SELECT * FROM tier_statistics WHERE tier = ?
            """, (tier,))
            
            row = cursor.fetchone()
            if not row:
                # 새로 생성
                cursor.execute("""
                    INSERT INTO tier_statistics (tier) VALUES (?)
                """, (tier,))
            
            # 업데이트
            updates = []
            values = []
            
            for key, value in update_data.items():
                if key != 'tier':
                    updates.append(f"{key} = ?")
                    values.append(value)
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(tier)
            
            if updates:
                query = f"UPDATE tier_statistics SET {', '.join(updates)} WHERE tier = ?"
                cursor.execute(query, values)
    
    def get_tier_statistics(self, tier: str) -> Optional[Dict[str, Any]]:
        """티어별 통계 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM tier_statistics WHERE tier = ?
            """, (tier,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_tier_statistics(self) -> Dict[str, Any]:
        """모든 티어 통계 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM tier_statistics ORDER BY tier
            """)
            
            stats = {}
            for row in cursor.fetchall():
                row_dict = dict(row)
                tier = row_dict.pop('tier')
                stats[tier] = row_dict
            
            return stats
    
    # =========================================================================
    # 피드백 작업
    # =========================================================================
    
    def add_feedback(self, user_input_hash: str, feedback_text: str, 
                     corrected_tier: Optional[str] = None) -> int:
        """피드백 추가"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO feedback (timestamp, user_input_hash, feedback_text, corrected_tier)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                user_input_hash,
                feedback_text,
                corrected_tier
            ))
            
            return cursor.lastrowid
    
    def add_classification_feedback(self, user_input: str, classified_tier: str,
                                   actual_tier: str, notes: str = "") -> int:
        """분류 피드백 추가"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            is_correct = classified_tier == actual_tier
            
            cursor.execute("""
                INSERT INTO classification_feedback 
                (timestamp, user_input, classified_tier, actual_tier, is_correct, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                user_input[:100],  # 처음 100자
                classified_tier,
                actual_tier,
                is_correct,
                notes
            ))
            
            return cursor.lastrowid
    
    def get_classification_accuracy(self, tier: Optional[str] = None, window: int = 100) -> Dict[str, float]:
        """분류 정확도 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if tier:
                cursor.execute("""
                    SELECT classified_tier, COUNT(*) as total, 
                           SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                    FROM classification_feedback
                    WHERE classified_tier = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    GROUP BY classified_tier
                """, (tier, window))
            else:
                cursor.execute("""
                    SELECT classified_tier, COUNT(*) as total,
                           SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                    FROM classification_feedback
                    ORDER BY timestamp DESC
                    LIMIT ?
                    GROUP BY classified_tier
                """, (window,))
            
            accuracy = {}
            for row in cursor.fetchall():
                row_dict = dict(row)
                tier_name = row_dict['classified_tier']
                total = row_dict['total']
                correct = row_dict['correct'] or 0
                accuracy[tier_name] = (correct / total * 100) if total > 0 else 0.0
            
            return accuracy
    
    # =========================================================================
    # 캐시 작업
    # =========================================================================
    
    def cache_set(self, cache_key: str, cache_value: Any, ttl_seconds: int = 3600):
        """캐시 저장"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            expires_at = datetime.fromtimestamp(
                datetime.now().timestamp() + ttl_seconds
            ).isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO cache 
                (cache_key, cache_value, ttl_seconds, expires_at)
                VALUES (?, ?, ?, ?)
            """, (
                cache_key,
                json.dumps(cache_value) if not isinstance(cache_value, str) else cache_value,
                ttl_seconds,
                expires_at
            ))
    
    def cache_get(self, cache_key: str) -> Optional[Any]:
        """캐시 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cache_value FROM cache
                WHERE cache_key = ? AND expires_at > datetime('now')
            """, (cache_key,))
            
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['cache_value'])
                except (json.JSONDecodeError, TypeError):
                    return row['cache_value']
            
            return None
    
    def cache_delete_expired(self) -> int:
        """만료된 캐시 삭제"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM cache
                WHERE expires_at <= datetime('now')
            """)
            
            return cursor.rowcount
    
    def cache_clear(self):
        """캐시 전체 삭제"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache")
    
    def cache_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(length(cache_value)) as size_bytes
                FROM cache
                WHERE expires_at > datetime('now')
            """)
            
            row = cursor.fetchone()
            return {
                'cached_items': row['total'] or 0,
                'size_bytes': row['size_bytes'] or 0,
                'size_kb': (row['size_bytes'] or 0) / 1024.0
            }
    
    # =========================================================================
    # 데이터베이스 관리
    # =========================================================================
    
    def backup(self, backup_path: Optional[Path] = None) -> Path:
        """데이터베이스 백업"""
        if backup_path is None:
            backup_path = self.db_path / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as conn:
            backup_conn = sqlite3.connect(str(backup_path))
            conn.backup(backup_conn)
            backup_conn.close()
        
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
    
    def vacuum(self):
        """데이터베이스 최적화"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("VACUUM")
        logger.info("Database vacuumed")
    
    def get_db_info(self) -> Dict[str, Any]:
        """데이터베이스 정보"""
        db_size = self.db_file.stat().st_size if self.db_file.exists() else 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 테이블 정보
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            
            tables = {}
            for row in cursor.fetchall():
                table_name = row[0]
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()['count']
                tables[table_name] = count
            
            return {
                'db_file': str(self.db_file),
                'size_bytes': db_size,
                'size_mb': db_size / (1024 * 1024),
                'tables': tables
            }
    
    def cleanup(self):
        """정기적인 정리 작업"""
        # 만료된 캐시 삭제
        expired_count = self.cache_delete_expired()
        
        # 데이터베이스 최적화
        self.vacuum()
        
        logger.info(f"Cleanup completed: {expired_count} expired cache entries deleted")
