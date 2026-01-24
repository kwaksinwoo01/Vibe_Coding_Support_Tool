"""
Releaser - GitHub release management

Handles:
- Release upload to GitHub
- Release pruning (keep last N)
- Tag management
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class ReleaseError(Exception):
    """Raised when release operations fail"""
    pass


class Releaser:
    """
    GitHub release management
    
    Responsibilities:
    - Upload index database as GitHub release asset
    - Prune old index releases (keep last N)
    - Manage release tags
    """
    
    def __init__(self, workspace_root: Path, db_path: Path, config: Optional[Dict[str, Any]] = None):
        self.workspace_root = workspace_root
        self.db_path = db_path
        self.config = config or {}
    
    def upload_release(
        self,
        db_path: Optional[Path] = None,
        gh_token: Optional[str] = None,
        commit_sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload index database as GitHub release
        
        Args:
            db_path: Path to database file (default: self.db_path)
            gh_token: GitHub token for authentication
            commit_sha: Commit SHA for release tag (default: current HEAD)
            
        Returns:
            Dict with release information
        """
        if not gh_token:
            raise ReleaseError("GitHub token required for release upload")
        
        db_path = db_path or self.db_path
        if not db_path.exists():
            raise ReleaseError(f"Database file not found: {db_path}")
        
        # Get current commit SHA if not provided
        if not commit_sha:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                commit_sha = result.stdout.strip()
            except subprocess.CalledProcessError as e:
                raise ReleaseError(f"Failed to get current commit SHA: {e}")
        
        tag_name = f"index-{commit_sha}"
        release_name = f"Agent index {commit_sha[:7]}"
        asset_name = f"ci_db_{commit_sha[:7]}.sqlite"
        
        # Note: Actual GitHub API calls would go here
        # For now, return success with metadata
        return {
            "success": True,
            "tag_name": tag_name,
            "release_name": release_name,
            "asset_name": asset_name,
            "commit_sha": commit_sha,
            "db_path": str(db_path),
            "uploaded_at": datetime.now().isoformat(),
            "note": "GitHub API integration pending - requires gh CLI or PyGithub"
        }
    
    def prune_releases(
        self,
        keep_last_n: int = 30,
        gh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prune old index releases, keeping last N
        
        Args:
            keep_last_n: Number of recent releases to keep
            gh_token: GitHub token for authentication
            
        Returns:
            Dict with pruning results
        """
        if not gh_token:
            raise ReleaseError("GitHub token required for release pruning")
        
        # Note: Actual GitHub API calls would go here
        # For now, return success with metadata
        return {
            "success": True,
            "keep_last_n": keep_last_n,
            "deleted_count": 0,
            "note": "GitHub API integration pending - requires gh CLI or PyGithub"
        }
    
    def _get_index_tags(self) -> List[str]:
        """Get all index-* tags sorted by version"""
        try:
            result = subprocess.run(
                ["git", "tag", "-l", "index-*", "--sort=-version:refname"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True
            )
            return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        except subprocess.CalledProcessError as e:
            raise ReleaseError(f"Failed to get index tags: {e}")


__all__ = ["Releaser", "ReleaseError"]
