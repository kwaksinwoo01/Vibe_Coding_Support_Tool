"""
caching_manager.py

MCP 서버 부팅 시간 단축을 위한 캐싱 시스템

기능:
- 분류 결과 캐싱
- 라우팅 결정 캐싱
- 티어별 통계 캐싱
- 캐시 만료 관리 (TTL 기반)
- 캐시 히트율 모니터링

캐시 계층:
1. In-Memory: 빠른 조회 (메인 캐시)
2. Disk: 장기 저장 (재부팅 후 복구)
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from threading import Lock


class CacheEntry:
    """캐시 항목"""
    
    def __init__(self, value: Any, ttl_seconds: int = 3600):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.hit_count = 0
    
    def is_expired(self) -> bool:
        """캐시 만료 확인"""
        return (time.time() - self.created_at) > self.ttl_seconds
    
    def hit(self) -> Any:
        """캐시 히트"""
        self.hit_count += 1
        return self.value


class CachingManager:
    """MCP 서버용 캐싱 시스템"""
    
    def __init__(self, cache_root: Path):
        self.cache_root = Path(cache_root) / "cache"
        self.cache_root.mkdir(parents=True, exist_ok=True)
        
        # In-Memory 캐시
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.memory_lock = Lock()
        
        # 캐시 통계
        self.hit_count = 0
        self.miss_count = 0
        
        # 캐시 설정
        self.default_ttl = 3600  # 1시간
        self.classification_ttl = 1800  # 30분 (빈번히 변함)
        self.stats_ttl = 3600  # 1시간
        
        # 디스크 캐시 로드
        self._load_disk_cache()
    
    def _load_disk_cache(self):
        """디스크에서 캐시 로드 (부팅 시간 단축)"""
        cache_file = self.cache_root / "memory_cache.json"
        
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding='utf-8'))
                
                # 유효한 캐시만 로드
                for key, entry_data in data.items():
                    created_at = entry_data.get("created_at", 0)
                    ttl = entry_data.get("ttl_seconds", self.default_ttl)
                    
                    # 만료 확인
                    if (time.time() - created_at) < ttl:
                        entry = CacheEntry(entry_data["value"], ttl)
                        entry.created_at = created_at
                        entry.hit_count = entry_data.get("hit_count", 0)
                        self.memory_cache[key] = entry
                
                print(f"[CACHE] [OK] Loaded {len(self.memory_cache)} entries from disk")
            except Exception as e:
                print(f"[CACHE] [ERROR] Failed to load disk cache: {e}")
    
    def _save_disk_cache(self):
        """캐시를 디스크에 저장"""
        cache_file = self.cache_root / "memory_cache.json"
        
        try:
            data = {}
            for key, entry in self.memory_cache.items():
                if not entry.is_expired():
                    data[key] = {
                        "value": entry.value,
                        "created_at": entry.created_at,
                        "ttl_seconds": entry.ttl_seconds,
                        "hit_count": entry.hit_count
                    }
            
            cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            print(f"[CACHE] [ERROR] Failed to save disk cache: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 조회"""
        with self.memory_lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                if not entry.is_expired():
                    self.hit_count += 1
                    return entry.hit()
                else:
                    # 만료된 캐시 제거
                    del self.memory_cache[key]
            
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """캐시에 저장"""
        ttl = ttl_seconds or self.default_ttl
        
        with self.memory_lock:
            self.memory_cache[key] = CacheEntry(value, ttl)
        
        # 주기적으로 디스크 캐시 갱신
        if self.hit_count + self.miss_count > 100:
            self._save_disk_cache()
            self.hit_count = 0
            self.miss_count = 0
    
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
        self.set(key, decision, 1800)  # 30분
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        
        return {
            "total_requests": total,
            "cache_hits": self.hit_count,
            "cache_misses": self.miss_count,
            "hit_rate": f"{hit_rate:.1f}%",
            "cached_items": len(self.memory_cache),
            "cache_size_kb": self._get_cache_size()
        }
    
    def _get_cache_size(self) -> float:
        """캐시 크기 (KB)"""
        import sys
        size = 0
        for entry in self.memory_cache.values():
            size += sys.getsizeof(entry.value)
        return size / 1024.0
    
    def clear(self):
        """캐시 전체 삭제"""
        with self.memory_lock:
            self.memory_cache.clear()
        
        cache_file = self.cache_root / "memory_cache.json"
        if cache_file.exists():
            cache_file.unlink()
        
        print("[CACHE] [OK] Cache cleared")
    
    def cleanup_expired(self):
        """만료된 캐시 정리"""
        with self.memory_lock:
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
        
        if expired_keys:
            print(f"[CACHE] Cleaned up {len(expired_keys)} expired entries")
