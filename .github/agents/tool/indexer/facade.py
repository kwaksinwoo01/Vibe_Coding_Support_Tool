"""
Index Facade - Main entry point for indexing operations

Provides unified interface to indexing subsystem:
- Orchestrates core indexing, release, and workflow generation
- Single point of entry for Tier E integration
"""

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import time

from .core import CoreIndexer, IndexBuildError
from .releaser import Releaser, ReleaseError
from .workflow import WorkflowGenerator


class IndexFacade:
    """
    Index Facade - Main entry point
    
    Orchestrates indexing operations through nested components:
    - core: CoreIndexer (decision logic, DB building)
    - releaser: Releaser (GitHub release management)
    - workflow: WorkflowGenerator (CI workflow templates)
    """
    
    def __init__(
        self,
        workspace_root: Path,
        db_path: Path,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize index facade
        
        Args:
            workspace_root: Repository root path
            db_path: Database file path
            config: Optional configuration dict
        """
        self.workspace_root = workspace_root
        self.db_path = db_path
        self.config = config or {}
        
        # Initialize nested components
        self.core = CoreIndexer(workspace_root, db_path, config)
        self.releaser = Releaser(workspace_root, db_path, config)
        self.workflow = WorkflowGenerator(workspace_root, db_path, config)
    
    def run_index_cycle(
        self,
        commit_threshold: int = 6,
        upload_release: bool = False,
        gh_token: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete index cycle
        
        High-level orchestration:
        1. Decide if should run (commit threshold check)
        2. Build index if needed
        3. Upload release if requested
        4. Return structured results
        
        Args:
            commit_threshold: Minimum commits to trigger indexing
            upload_release: Whether to upload as GitHub release
            gh_token: GitHub token for release operations
            force: Force indexing regardless of threshold
            
        Returns:
            Dict with structured results:
            {
                "status": "SUCCESS" | "SKIPPED" | "FAILED",
                "db_path": str,
                "reason": str,
                "runtime_seconds": float,
                "release": dict (if uploaded),
                "errors": list
            }
        """
        start_time = time.time()
        result = {
            "status": "SKIPPED",
            "db_path": str(self.db_path),
            "reason": "",
            "runtime_seconds": 0.0,
            "release": None,
            "errors": []
        }
        
        try:
            # Step 1: Decide if should run
            should_run, details = self.core.decide_should_run(commit_threshold, force)
            
            if not should_run:
                result["status"] = "SKIPPED"
                result["reason"] = details.get("reason", "insufficient_commits")
                result["commits_since_last"] = details.get("commits_since_last")
                result["threshold"] = details.get("threshold")
                return result
            
            # Step 2: Build index
            try:
                db_path = self.core.build_index(allow_overwrite=True)
                result["status"] = "SUCCESS"
                result["reason"] = details.get("reason", "index_built")
                result["db_path"] = str(db_path)
                result["commits_since_last"] = details.get("commits_since_last")
                result["threshold"] = details.get("threshold")
            except IndexBuildError as e:
                result["status"] = "FAILED"
                result["reason"] = "index_build_failed"
                result["errors"].append(str(e))
                return result
            
            # Step 3: Upload release if requested
            if upload_release:
                if not gh_token:
                    result["errors"].append("GitHub token required for release upload")
                else:
                    try:
                        release_result = self.releaser.upload_release(gh_token=gh_token)
                        result["release"] = release_result
                    except ReleaseError as e:
                        result["errors"].append(f"Release upload failed: {e}")
            
            return result
            
        except Exception as e:
            result["status"] = "FAILED"
            result["reason"] = "unexpected_error"
            result["errors"].append(str(e))
            return result
        
        finally:
            result["runtime_seconds"] = time.time() - start_time


__all__ = ["IndexFacade"]
