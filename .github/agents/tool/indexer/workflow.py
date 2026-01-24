"""
Workflow Generator - GitHub Actions workflow generation

Handles:
- Generate minimal CI workflow YAML
- Template generation for manual review
"""

from pathlib import Path
from typing import Dict, Any, Optional


class WorkflowGenerator:
    """
    Workflow template generator
    
    Responsibilities:
    - Generate minimal GitHub Actions workflow YAML
    - Produce workflow templates for operator review
    """
    
    def __init__(self, workspace_root: Path, db_path: Path, config: Optional[Dict[str, Any]] = None):
        self.workspace_root = workspace_root
        self.db_path = db_path
        self.config = config or {}
    
    def generate_workflow_template(
        self,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate minimal GitHub Actions workflow template
        
        Args:
            config: Optional configuration overrides
            
        Returns:
            YAML workflow content as string
        """
        config = config or self.config
        
        commit_threshold = config.get("commit_threshold", 6)
        db_path = config.get("db_path", ".agent_index/ci_db.sqlite")
        
        template = f"""name: Agent Indexer (6-Tier Integration)

permissions:
  contents: write

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-index:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for commit counting

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run indexer via Tier E
        run: |
          python .github/agents/tool/E_Document_Management.py reindex \\
            --root . \\
            --db {db_path} \\
            --commit-threshold {commit_threshold} \\
            --upload-release \\
            --gh-token ${{{{ secrets.GITHUB_TOKEN }}}}
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
"""
        return template


__all__ = ["WorkflowGenerator"]
