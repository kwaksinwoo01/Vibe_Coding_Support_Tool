"""
Core Indexer - Repository indexing logic

Handles:
- Commit threshold decision logic
- File collection and filtering
- SQLite database building
- Atomic write operations
"""

import os
import sqlite3
import hashlib
import subprocess
from pathlib import Path
from typing import Iterator, List, Optional, Dict, Any, Tuple
from datetime import datetime


class IndexBuildError(Exception):
    """Raised when index building fails"""
    pass


class CoreIndexer:
    """
    Core repository indexing logic
    
    Responsibilities:
    - Decide when to run indexing based on commit threshold
    - Collect relevant files from repository
    - Build SQLite index with file metadata and tokens
    - Atomic database writes
    """
    
    # File filtering configuration
    SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".agent_index"}
    VALID_EXTENSIONS = {".py", ".md", ".txt", ".log", ".json", ".yaml", ".yml", ".ini", ".toml"}
    
    def __init__(self, workspace_root: Path, db_path: Path, config: Optional[Dict[str, Any]] = None):
        self.workspace_root = workspace_root
        self.db_path = db_path
        self.config = config or {}
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def decide_should_run(self, commit_threshold: int = 6, force: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        Decide if indexing should run based on commit count
        
        Args:
            commit_threshold: Number of commits required to trigger indexing
            force: Force indexing regardless of threshold
            
        Returns:
            Tuple of (should_run: bool, details: dict)
        """
        if force:
            return True, {
                "reason": "forced_run",
                "commits_since_last": None,
                "threshold": commit_threshold
            }
        
        try:
            # Get the last index tag
            result = subprocess.run(
                ["git", "tag", "-l", "index-*", "--sort=-version:refname"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            tags = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            
            if not tags:
                # No previous index
                return True, {
                    "reason": "no_previous_index",
                    "commits_since_last": None,
                    "threshold": commit_threshold
                }
            
            last_tag = tags[0]
            
            # Count commits since last tag
            result = subprocess.run(
                ["git", "rev-list", f"{last_tag}..HEAD", "--count"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            commit_count = int(result.stdout.strip())
            
            if commit_count >= commit_threshold:
                return True, {
                    "reason": "commit_threshold_reached",
                    "commits_since_last": commit_count,
                    "threshold": commit_threshold
                }
            else:
                return False, {
                    "reason": "insufficient_commits",
                    "commits_since_last": commit_count,
                    "threshold": commit_threshold
                }
                
        except subprocess.CalledProcessError as e:
            # Git command failed - assume we should run
            return True, {
                "reason": "git_error",
                "error": str(e),
                "threshold": commit_threshold
            }
        except Exception as e:
            raise IndexBuildError(f"Failed to determine if should run: {e}")
    
    def _iter_files(self, root: Optional[Path] = None) -> Iterator[Path]:
        """Iterate over valid files in repository"""
        root = root or self.workspace_root
        
        for dirpath, dirnames, filenames in os.walk(root):
            # Filter out skip directories
            parts = set(Path(dirpath).parts)
            if parts & self.SKIP_DIRS:
                continue
            
            for filename in filenames:
                filepath = Path(dirpath) / filename
                if filepath.suffix.lower() in self.VALID_EXTENSIONS:
                    yield filepath
    
    def _file_sha256(self, path: Path) -> str:
        """Calculate SHA256 hash of file"""
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into searchable tokens"""
        return [t.lower() for t in text.split() if len(t) >= 3]
    
    def _ensure_schema(self, conn: sqlite3.Connection):
        """Create database schema if not exists"""
        cur = conn.cursor()
        
        # Files table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
          id INTEGER PRIMARY KEY,
          path TEXT UNIQUE,
          size INTEGER,
          mtime REAL,
          sha256 TEXT
        )
        """)
        
        # Tokens table for inverted index
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
          token TEXT,
          file_id INTEGER,
          count INTEGER,
          FOREIGN KEY(file_id) REFERENCES files(id)
        )
        """)
        
        cur.execute("CREATE INDEX IF NOT EXISTS idx_token ON tokens(token)")
        
        # Metadata table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
          key TEXT PRIMARY KEY,
          value TEXT
        )
        """)
        
        conn.commit()
    
    def _index_file(self, conn: sqlite3.Connection, path: Path) -> bool:
        """
        Index a single file
        
        Returns:
            True if file was updated, False if skipped (unchanged)
        """
        sha = self._file_sha256(path)
        stat = path.stat()
        cur = conn.cursor()
        
        # Check if file exists and hasn't changed
        cur.execute("SELECT id, sha256 FROM files WHERE path=?", (str(path),))
        row = cur.fetchone()
        
        if row and row[1] == sha:
            # File unchanged, skip
            return False
        
        if row:
            # File changed, delete old tokens
            file_id = row[0]
            cur.execute("DELETE FROM tokens WHERE file_id=?", (file_id,))
            cur.execute("UPDATE files SET size=?, mtime=?, sha256=? WHERE id=?",
                       (stat.st_size, stat.st_mtime, sha, file_id))
        else:
            # New file
            cur.execute("INSERT INTO files (path, size, mtime, sha256) VALUES (?, ?, ?, ?)",
                       (str(path), stat.st_size, stat.st_mtime, sha))
            file_id = cur.lastrowid
        
        # Index tokens
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            
            tokens = self._tokenize_text(text)
            token_counts = {}
            for token in tokens:
                token_counts[token] = token_counts.get(token, 0) + 1
            
            for token, count in token_counts.items():
                cur.execute("INSERT INTO tokens (token, file_id, count) VALUES (?, ?, ?)",
                           (token, file_id, count))
        except Exception:
            # Skip files that can't be read as text
            pass
        
        return True
    
    def build_index(
        self,
        paths: Optional[List[Path]] = None,
        allow_overwrite: bool = True
    ) -> Path:
        """
        Build SQLite index
        
        Args:
            paths: Optional list of specific paths to index (default: all files)
            allow_overwrite: Allow overwriting existing database
            
        Returns:
            Path to created database file
        """
        if self.db_path.exists() and not allow_overwrite:
            raise IndexBuildError(f"Database already exists: {self.db_path}")
        
        # Use temporary file for atomic write
        temp_db = self.db_path.parent / f"{self.db_path.name}.tmp"
        
        try:
            conn = sqlite3.connect(str(temp_db))
            self._ensure_schema(conn)
            
            # Add metadata
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                       ("created_at", datetime.now().isoformat()))
            cur.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                       ("workspace_root", str(self.workspace_root)))
            
            # Index files
            files_to_index = paths if paths else list(self._iter_files())
            indexed_count = 0
            updated_count = 0
            
            for filepath in files_to_index:
                try:
                    if self._index_file(conn, filepath):
                        updated_count += 1
                    indexed_count += 1
                except Exception as e:
                    # Log error but continue indexing
                    print(f"Warning: Failed to index {filepath}: {e}")
            
            # Add stats
            cur.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                       ("total_files", str(indexed_count)))
            cur.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                       ("updated_files", str(updated_count)))
            
            conn.commit()
            conn.close()
            
            # Atomic rename
            if self.db_path.exists():
                self.db_path.unlink()
            temp_db.rename(self.db_path)
            
            return self.db_path
            
        except Exception as e:
            # Cleanup temp file on error
            if temp_db.exists():
                temp_db.unlink()
            raise IndexBuildError(f"Failed to build index: {e}")


__all__ = ["CoreIndexer", "IndexBuildError"]
