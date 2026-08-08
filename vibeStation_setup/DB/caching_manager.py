"""
caching_manager.py

SQLite 기반 캐싱 시스템 (MCP 서버 부팅 시간 단축)

기능:
- 분류 결과 캐싱 (SQLite)
- 라우팅 결정 캐싱 (SQLite)
- 티어별 통계 캐싱 (SQLite)
- 캐시 만료 관리 (TTL 기반)
- 캐시 히트율 모니터링

캐시 전략:
1. 분류 결과: 30분 TTL (빈번히 변함)
2. 티어 통계: 1시간 TTL (변동성 적음)
3. 라우팅 결정: 30분 TTL
4. 자동 정리: 매 100회 요청마다 만료된 캐시 정리
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from threading import Lock

from database import DatabaseManager

logger = logging.getLogger(__name__)


class CachingManager:
    """SQLite 기반 캐싱 시스템"""
    
    def __init__(self, cache_root: Path):
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        
        # SQLite 데이터베이스 관리자
        self.db_manager = DatabaseManager(self.cache_root)
        
        # 캐시 통계 (메모리)
        self.hit_count = 0
        self.miss_count = 0
        self.stats_lock = Lock()
        
        # 캐시 설정
        self.default_ttl = 3600  # 1시간
        self.classification_ttl = 1800  # 30분
        self.stats_ttl = 3600  # 1시간
        self.routing_ttl = 1800  # 30분
        
        logger.info("[CACHE] CachingManager initialized with SQLite backend")
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 조회"""
        try:
            value = self.db_manager.cache_get(key)
            
            with self.stats_lock:
                if value is not None:
                    self.hit_count += 1
                    # 주기적으로 정리
                    if (self.hit_count + self.miss_count) % 100 == 0:
                        self._cleanup_periodically()
                else:
                    self.miss_count += 1
            
            return value
        except Exception as e:
            logger.error(f"[CACHE] Error retrieving cache key {key}: {e}")
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """캐시에 저장"""
        try:
            ttl = ttl_seconds or self.default_ttl
            self.db_manager.cache_set(key, value, ttl)
        except Exception as e:
            logger.error(f"[CACHE] Error setting cache key {key}: {e}")
    
    def cache_classification(self, user_input_hash: str, result: Dict[str, Any]):
        """분류 결과 캐싱"""
        key = f"classification:{user_input_hash}"
        self.set(key, result, self.classification_ttl)
    
    def get_cached_classification(self, user_input_hash: str) -> Optional[Dict[str, Any]]:
        """캐시된 분류 결과 조회"""
        key = f"classification:{user_input_hash}"
        return self.get(key)
    
    def cache_tier_stats(self, tier: str, stats: Dict[str, Any]):
        """티어 통계 캐싱"""
        key = f"tier_stats:{tier}"
        self.set(key, stats, self.stats_ttl)
    
    def get_cached_tier_stats(self, tier: str) -> Optional[Dict[str, Any]]:
        """캐시된 티어 통계 조회"""
        key = f"tier_stats:{tier}"
        return self.get(key)
    
    def cache_routing_decision(self, tier: str, decision: Dict[str, Any]):
        """라우팅 결정 캐싱"""
        key = f"routing:{tier}"
        self.set(key, decision, self.routing_ttl)
    
    def get_cached_routing_decision(self, tier: str) -> Optional[Dict[str, Any]]:
        """캐시된 라우팅 결정 조회"""
        key = f"routing:{tier}"
        return self.get(key)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        with self.stats_lock:
            total = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total * 100) if total > 0 else 0
            
            db_stats = self.db_manager.cache_stats()
            
            return {
                "total_requests": total,
                "cache_hits": self.hit_count,
                "cache_misses": self.miss_count,
                "hit_rate": f"{hit_rate:.1f}%",
                "cached_items": db_stats['cached_items'],
                "cache_size_kb": db_stats['size_kb']
            }
    
    def clear(self):
        """캐시 전체 삭제"""
        try:
            self.db_manager.cache_clear()
            
            with self.stats_lock:
                self.hit_count = 0
                self.miss_count = 0
            
            logger.info("[CACHE] Cache cleared successfully")
        except Exception as e:
            logger.error(f"[CACHE] Error clearing cache: {e}")
    
    def cleanup_expired(self) -> int:
        """만료된 캐시 정리"""
        try:
            count = self.db_manager.cache_delete_expired()
            if count > 0:
                logger.info(f"[CACHE] Cleaned up {count} expired cache entries")
            return count
        except Exception as e:
            logger.error(f"[CACHE] Error cleaning up expired cache: {e}")
            return 0
    
    def _cleanup_periodically(self):
        """주기적인 캐시 정리 (백그라운드)"""
        try:
            expired_count = self.db_manager.cache_delete_expired()
            if expired_count > 0:
                logger.debug(f"[CACHE] Periodic cleanup: removed {expired_count} expired entries")
        except Exception as e:
            logger.error(f"[CACHE] Periodic cleanup error: {e}")
    
    def prefill_tier_stats(self, tier_stats: Dict[str, Dict[str, Any]]):
        """티어 통계 프리필
        
        부팅 시에 기존 데이터를 캐시에 미리 로드
        """
        try:
            for tier, stats in tier_stats.items():
                self.cache_tier_stats(tier, stats)
            logger.info(f"[CACHE] Prefilled {len(tier_stats)} tier statistics")
        except Exception as e:
            logger.error(f"[CACHE] Error prefilling tier stats: {e}")

