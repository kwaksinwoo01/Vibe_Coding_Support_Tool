"""
E_Document_Management.py

**Tier E: Task Document Management (Refactored with Facade Pattern)**

Role: Manages the creation, modification, storage and synchronization of work documents (WPD, PRD, MP, etc.).
Refactored Architecture:
- Uses Facade pattern to delegate to specialized managers
- Each manager handles one aspect of document management
- Managers are located in doc_management/ directory
- Integrates with ADMP and MP tools without duplication

Management Modules:
1. LinkManager - Document link management
2. VersionManager - Version tracking (N1.N2.N3)
3. ChecklistManager - Checklist add/delete/modify
4. ProgressManager - Progress state tracking
5. MappingManager - Mapping table with 500-line split (integrates MP tools)
6. ErrorSessionManager - Error tracking and resolution

Trigger condition:
-Automatic execution after creating Results Report in Tier B
-User instructs “Save changes”
-User instructs “Update mapping table”
-User instructs “Modify data class”
-When automatic document synchronization is required

Specification: docs_2/Untitled-1.md (Lines 342-472)
"""

import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent))

from models.core import AgentState, TierEState, TaskContext
from models.builders import create_tier_e_state
from models.core import AgentState, TierEState

# Import document management modules (Facade pattern)
from doc_management import (
    LinkManager,
    VersionManager,
    ChecklistManager,
    ProgressManager,
    MappingManager,
    ErrorSessionManager,
    MarkdownAutofixManager,
    DocumentMerger,
    SemanticAnalyzer,
)

# Import indexer module
from indexer import IndexFacade


class DocumentManagementEngine:
    """
    Document Management Facade
    
    Provides unified interface to 8 specialized managers:
    1. link_manager - Document link validation and fixing
    2. version_manager - Version tracking (N1.N2.N3)
    3. checklist_manager - Checklist add/delete/modify
    4. progress_manager - Progress state tracking
    5. mapping_manager - Mapping table management (integrates MP tools)
    6. error_session_manager - Error tracking and resolution
    7. markdown_autofix_manager - Automatic markdown linting fixes
    8. document_merger - Semantic document merging with ADMP compliance
    
    Architecture: Facade Pattern
    - Delegates operations to specialized managers
    - Each manager is responsible for one aspect
    - No duplication with ADMP/MP tools
    """
    
    def __init__(self, context: TaskContext, previous_payload: Optional[Dict[str, Any]] = None):
        self.context = context
        self.tier = "E"
        self.previous_payload = previous_payload or {}
        self.workspace_root = Path(context.workspace_root)
        
        # Initialize TierEState
        self.state = TierEState()
        self.state.sources.prd_path = self.previous_payload.get("prd_path")
        self.state.sources.wpd_sources = self.previous_payload.get("wpd_sources", [])
        
        # Initialize specialized managers (Facade pattern)
        self.link_manager = LinkManager(self.workspace_root)
        self.version_manager = VersionManager(self.workspace_root)
        self.checklist_manager = ChecklistManager(self.workspace_root)
        self.progress_manager = ProgressManager(self.workspace_root)
        self.mapping_manager = MappingManager(self.workspace_root)
        self.error_session_manager = ErrorSessionManager(self.workspace_root)
        self.markdown_autofix_manager = MarkdownAutofixManager(self.workspace_root)
        self.document_merger = DocumentMerger(self.workspace_root)
    
    def validate_user_input(self) -> bool:
        """Check if user input is a document management instruction"""
        keywords = [
            "save changes",
            "save",
            "update mapping",
            "modify data class",
            "data class field",
            "동기화",
            "문서 저장",
            "매핑 테이블",
            "데이터 클래스",
            "필드 수정",
            "document management",
            "link validation",
            "fix markdown",
            "autofix",
            "markdown lint",
            "fix md",
            "merge",
            "merge documents",
            "consolidate",
            "integrate documents",
            "병합",
            "문서 병합",
        ]
        
        user_input_lower = self.context.user_input.lower()
        return any(keyword in user_input_lower for keyword in keywords)
    
    # ========== Facade Methods - Delegate to Managers ==========
    
    def manage_links(self, doc_path: Path) -> Dict[str, Any]:
        """Delegate link management to LinkManager"""
        result = self.link_manager.validate_and_fix_links(doc_path)
        
        # Update state with results
        self.state.prd_operations.append({
            "type": "link_management",
            "document": str(doc_path),
            "links_inspected": result.get("links_inspected", 0),
            "links_fixed": result.get("links_fixed", 0)
        })
        
        return result
    
    def manage_version(self, doc_path: Path, tier_context: str = "B") -> Dict[str, Any]:
        """
        Delegate version management to VersionManager
        
        Args:
            doc_path: Document to update
            tier_context: Context tier ("B" for execution, "C" for modification)
        """
        if tier_context == "B":
            result = self.version_manager.update_version_for_tier_b(doc_path)
        elif tier_context == "C":
            result = self.version_manager.update_version_for_tier_c(doc_path)
        else:
            result = self.version_manager.update_version_for_tier_b(doc_path)
        
        # Update state with results
        self.state.prd_operations.append({
            "type": "version_management",
            "document": str(doc_path),
            "old_version": result.get("old_version"),
            "new_version": result.get("new_version")
        })
        
        return result
    
    def manage_checklist(self, doc_path: Path, operation: str, item_desc: str) -> Dict[str, Any]:
        """Delegate checklist management to ChecklistManager"""
        result = self.checklist_manager.manage_item(doc_path, operation, item_desc)
        
        # Update state with results
        self.state.prd_operations.append({
            "type": "checklist_management",
            "document": str(doc_path),
            "operation": operation,
            "item": item_desc
        })
        
        return result
    
    def manage_progress(self, doc_path: Path, progress_state: str) -> Dict[str, Any]:
        """Delegate progress management to ProgressManager"""
        result = self.progress_manager.update_progress(doc_path, progress_state)
        
        # Update state with results
        self.state.prd_operations.append({
            "type": "progress_management",
            "document": str(doc_path),
            "new_progress": progress_state
        })
        
        return result
    
    def manage_mapping(self, mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate mapping management to MappingManager (integrates MP tools)"""
        result = self.mapping_manager.manage_mapping(mapping_data)
        
        # Update state with results
        self.state.prd_operations.append({
            "type": "mapping_management",
            "success": result.get("success", False),
            "message": result.get("message", "")
        })
        
        return result
    
    def manage_error_sessions(self, doc_path: Path, error_list: List[str]) -> Dict[str, Any]:
        """Delegate error session management to ErrorSessionManager"""
        result = self.error_session_manager.add_error_sessions(doc_path, error_list)
        
        # Update state with results
        self.state.prd_operations.append({
            "type": "error_session_management",
            "document": str(doc_path),
            "errors_added": len(error_list)
        })
        
        return result
    
    def manage_markdown_autofix(self, target: Path, apply: bool = False) -> Dict[str, Any]:
        """
        Delegate markdown autofix to MarkdownAutofixManager
        
        Args:
            target: File or directory to fix
            apply: If True, write fixes; if False, dry-run
            
        Returns:
            Dict with fix results
        """
        if target.is_file():
            result = self.markdown_autofix_manager.fix_document(target, apply=apply)
        else:
            result = self.markdown_autofix_manager.fix_directory(target, apply=apply)
        
        # Update state with results
        self.state.prd_operations.append({
            "type": "markdown_autofix",
            "target": str(target),
            "applied": apply,
            "changes": result.get("changes_count", 0) if target.is_file() else result.get("total_changes", 0)
        })
        
        return result
    
    def manage_document_merge(
        self, 
        source_path: Path, 
        target_path: Path, 
        justification: str = "Semantic document merge per ADMP policy"
    ) -> Dict[str, Any]:
        """
        Delegate document merging to DocumentMerger
        
        Implements ADMP Scenario D: Consolidation instead of creating separate documents
        
        Args:
            source_path: Source document to merge from
            target_path: Target document to merge into (existing Implementation Report)
            justification: Justification for merge (ADMP requirement)
            
        Returns:
            Dict with merge results
        """
        result = self.document_merger.merge_documents(source_path, target_path, justification)
        
        # Update state with results
        self.state.prd_operations.append({
            "type": "document_merge",
            "source": str(source_path),
            "target": str(target_path),
            "success": result.get("success", False),
            "old_version": result.get("old_version"),
            "new_version": result.get("new_version"),
            "merge_decisions": result.get("merge_decisions", 0),
            "integrated": result.get("integrated", 0),
            "appended": result.get("appended", 0),
            "new_sections": result.get("new_sections", 0)
        })
        
        return result
    
    # ========== Helper Methods ==========
    
    def get_parent_documents(self, doc_path: Path) -> List[Path]:
        """Get parent documents using VersionManager"""
        return self.version_manager.get_parent_documents(doc_path)
    
    def get_child_documents(self, doc_path: Path) -> List[Path]:
        """Get child documents using VersionManager"""
        return self.version_manager.get_child_documents(doc_path)
    
    def read_file_content(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        """
        Read file content with optional line range
        
        Args:
            file_path: Path to the file to read
            start_line: Starting line number (1-based, optional)
            end_line: Ending line number (1-based, optional)
        
        Returns:
            Dict with file content and metadata
        """
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.workspace_root / path
            
            if not path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "content": ""
                }
            
            # Check file size for large files
            file_size = path.stat().st_size
            if file_size > 50 * 1024 * 1024:  # 50MB threshold
                return {
                    "success": False,
                    "error": f"File too large to read ({file_size / (1024*1024):.1f} MB). Use grep_search or semantic_search for specific content.",
                    "content": "",
                    "file_size_mb": file_size / (1024*1024)
                }
            
            with open(path, 'r', encoding='utf-8') as f:
                if start_line is None and end_line is None:
                    # For large files, suggest using line ranges
                    if file_size > 1024 * 1024:  # 1MB
                        return {
                            "success": False,
                            "error": f"File is large ({file_size / (1024*1024):.1f} MB). Please specify line range (e.g., 'read file {file_path} lines 1-100').",
                            "content": "",
                            "file_size_mb": file_size / (1024*1024),
                            "suggest_range": True
                        }
                    content = f.read()
                    lines = content.splitlines()
                else:
                    lines = f.readlines()
                    start_idx = (start_line - 1) if start_line else 0
                    end_idx = end_line if end_line else len(lines)
                    lines = lines[start_idx:end_idx]
                    content = ''.join(lines)
            
            return {
                "success": True,
                "file_path": str(path),
                "content": content,
                "line_count": len(lines),
                "total_lines": len(content.splitlines()) if start_line or end_line else len(lines)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading file: {str(e)}",
                "content": ""
            }
    
    def _is_file_read_request(self) -> bool:
        """Check if user input is a file read request"""
        user_input_lower = self.context.user_input.lower()
        return ("read file" in user_input_lower or 
                user_input_lower.startswith("read ") or
                "파일 읽기" in user_input_lower)
    
    def _execute_file_read(self) -> AgentState:
        """Execute file read operation"""
        try:
            file_path, start_line, end_line = self._parse_file_read_input()
            
            if not file_path:
                return AgentState.create_failure(
                    tier=self.tier,
                    error_msg="Could not parse file path from input",
                    logic_summary="File read failed: invalid input format"
                )
            
            result = self.read_file_content(file_path, start_line, end_line)
            
            if result["success"]:
                # Truncate content if too long for display
                content = result["content"]
                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated)"
                
                logic_summary = f"Read file: {result['file_path']}"
                if start_line or end_line:
                    logic_summary += f" (lines {start_line or 1}-{end_line or 'end'})"
                logic_summary += f" - {result['line_count']} lines"
                
                state = AgentState.create_success(
                    tier=self.tier,
                    logic_summary=logic_summary,
                    payload={
                        "file_read_result": result,
                        "content": content
                    },
                    next_node=None
                )
                
                state.decision_trace.append({
                    "operation": "file_read",
                    "file_path": result["file_path"],
                    "line_count": result["line_count"],
                    "success": True
                })
                
                return state
            else:
                return AgentState.create_failure(
                    tier=self.tier,
                    error_msg=result["error"],
                    logic_summary=f"File read failed: {result['error']}"
                )
        
        except Exception as e:
            return AgentState.create_failure(
                tier=self.tier,
                error_msg=f"Exception during file read: {str(e)}",
                logic_summary=f"Error: {str(e)}"
            )
    
    def _parse_file_read_input(self) -> tuple[str, Optional[int], Optional[int]]:
        """
        Parse file path and optional line range from user input
        
        Examples:
        - "read file docs_2/NextTask-2.md"
        - "read docs_2/NextTask-2.md lines 10-20"
        - "파일 읽기 client/app.py"
        
        Returns:
            tuple: (file_path, start_line, end_line)
        """
        
        user_input = self.context.user_input.strip()
        
        # Remove common prefixes
        prefixes = ["read file", "read", "파일 읽기"]
        for prefix in prefixes:
            if user_input.lower().startswith(prefix):
                user_input = user_input[len(prefix):].strip()
                break
        
        # Check for line range (e.g., "lines 10-20" or "10-20")
        line_match = re.search(r'(?:lines?\s*)?(\d+)(?:\s*-\s*(\d+))?$', user_input)
        start_line = None
        end_line = None
        
        if line_match:
            start_line = int(line_match.group(1))
            if line_match.group(2):
                end_line = int(line_match.group(2))
            # Remove line specification from file path
            user_input = re.sub(r'(?:lines?\s*)?\d+(?:\s*-\s*\d+)?$', '', user_input).strip()
        
        # Clean up file path
        file_path = user_input.strip()
        
        return file_path, start_line, end_line
    
    def _get_reference_documents(self, doc_path: Path) -> List[Path]:
        """Extract reference document paths from document"""
        if not doc_path.exists():
            return []
        
        content = doc_path.read_text(encoding='utf-8')
        ref_pattern = r'\*\*References?\*\*:.*?`([^`]+)`'
        matches = re.findall(ref_pattern, content)
        
        ref_paths = []
        for match in matches:
            ref_path = self.workspace_root / match
            if ref_path.exists():
                ref_paths.append(ref_path)
        
        return ref_paths
    
    def _add_prd_link_to_document(self, target_doc: Path, prd_path: Path):
        """Add PRD link to target document"""
        if not target_doc.exists():
            return
        
        content = target_doc.read_text(encoding='utf-8')
        
        # Add PRD link in Results Report section
        prd_link = f"- **Results Report**: [{prd_path.name}]({prd_path.relative_to(target_doc.parent)})\n"
        
        # Find or create Results Report section
        if "## Results Report" in content or "## 📊 Results" in content:
            # Append to existing section
            content = content.replace("## Results Report\n", f"## Results Report\n{prd_link}")
            content = content.replace("## 📊 Results\n", f"## 📊 Results\n{prd_link}")
        else:
            # Add new section before References
            if "## References" in content or "## 🔗 References" in content:
                content = content.replace("## References", f"## Results Report\n{prd_link}\n## References")
                content = content.replace("## 🔗 References", f"## 📊 Results Report\n{prd_link}\n## 🔗 References")
            else:
                # Add at end
                content += f"\n\n## 📊 Results Report\n{prd_link}"
        
        target_doc.write_text(content, encoding='utf-8')
    
    def _extract_Part_Number_from_context(self) -> int:
        """Extract step number from context or previous payload"""
        # Try to extract from wpd_sources
        wpd_sources = self.previous_payload.get("wpd_sources", [])
        if wpd_sources:
            wpd_path = wpd_sources[0]
            match = re.search(r'P(\d+)', wpd_path)
            if match:
                return int(match.group(1))
        
        # Default
        return 1
    
    def run_repository_index(
        self,
        root: Path,
        db_path: Path,
        commit_threshold: int = 6,
        upload_release: bool = False,
        gh_token: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Run repository indexing operation
        
        Delegates to IndexFacade for core indexing logic.
        
        Args:
            root: Repository root path
            db_path: Database file path
            commit_threshold: Minimum commits to trigger indexing
            upload_release: Whether to upload as GitHub release
            gh_token: GitHub token for release operations
            force: Force indexing regardless of threshold
            
        Returns:
            Dict with indexing results
        """
        indexer = IndexFacade(root, db_path)
        
        result = indexer.run_index_cycle(
            commit_threshold=commit_threshold,
            upload_release=upload_release,
            gh_token=gh_token,
            force=force
        )
        
        return result
    
    def _generate_prd_template(self, Part_N: int) -> str:
        """Generate PRD template content"""
        return f"""# PRD-P{Part_N}: Progress Results Document

            **WPD_grade**: L0
            **Version**: 1.0.0
            **Status**: 📋 PENDING
            **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            ## 📋 Overview
            This document tracks the results and progress of work plan execution for Step {Part_N}.

            ## 📊 Execution Summary
            **Overall Progress**: 0%

            ### Completed Phases
            - None

            ### In Progress
            - Phase 1

            ### Pending
            - All phases

            ## 📝 Implementation Notes
            Implementation details will be added as work progresses.

            ## 🔗 References

            ### Parents Documents
            - Main document: [NextTask-2.md](../NextTask-2.md)

            ### Related WPD Documents
            - Work Plan: [P{Part_N}-*.md](../P{Part_N}/P{Part_N}-*.md)

            ## 📅 Timeline
            **Started**: {datetime.now().strftime('%Y-%m-%d')}
            **Target Completion**: TBD

            ---
            *Generated by Tier E (Document Management)*
            """
    
    # ========== Main Execution Methods ==========
    
    def execute(self) -> AgentState:
        """
        Execute complete document management workflow
        Implements Untitled-1.md Steps 1.0-2.5
        
        Note: validate_user_input() check removed for automatic chain execution.
        Tier E is automatically triggered after Tier B success, so validation is unnecessary.
        """
        try:
            # Check if called from Tier B with Results Report
            prd_path_str = self.state.sources.prd_path
            
            if prd_path_str:
                # Step 1.0: Results Report exists from Tier B
                return self._execute_with_results_report(Path(prd_path_str))
            else:
                # Step 2.0: Results Report does not exist
                return self._execute_without_results_report()
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return AgentState.create_failure(
                tier=self.tier,
                error_msg=f"Exception during document management: {str(e)}",
                logic_summary=f"Error: {str(e)}"
            )
    
    def _execute_with_results_report(self, prd_path: Path) -> AgentState:
        """Step 1.0: When Results Report exists from Tier B"""
        if not prd_path.exists():
            return self._execute_without_results_report()
        
        self.state.sources.prd_path = str(prd_path)
        operations_performed = []
        
        # Step 1.1.0: Query parent documents and add PRD link
        parents = self.get_parent_documents(prd_path)
        for parent_path in parents:
            self._add_prd_link_to_document(parent_path, prd_path)
            operations_performed.append(f"Added PRD link to parent: {parent_path.name}")
        
        # Step 1.1.1: Query child documents and add PRD link
        children = self.get_child_documents(prd_path)
        for child_path in children:
            self._add_prd_link_to_document(child_path, prd_path)
            operations_performed.append(f"Added PRD link to child: {child_path.name}")
        
        # Step 1.1.2: Query references and add PRD link
        references = self._get_reference_documents(prd_path)
        for ref_path in references:
            self._add_prd_link_to_document(ref_path, prd_path)
            operations_performed.append(f"Added PRD link to reference: {ref_path.name}")
        
        # Perform all 6 management operations using specialized managers
        managed_docs = [prd_path] + parents + children + references
        for doc_path in managed_docs:
            # Link management
            link_result = self.manage_links(doc_path)
            if link_result.get("links_fixed", 0) > 0:
                operations_performed.append(f"Fixed {link_result['links_fixed']} links in {doc_path.name}")
            
            # Version management (Tier B trigger - increment N3)
            ver_result = self.manage_version(doc_path, tier_context="B")
            operations_performed.append(f"Updated {doc_path.name} version: {ver_result['old_version']} → {ver_result['new_version']}")
        
        # Step 1.2: Terminate process
        state = AgentState.create_success(
            tier=self.tier,
            logic_summary=f"Document management complete. PRD: {prd_path.name}. "
                         f"Updated {len(parents)} parents, {len(children)} children, {len(references)} references. "
                         f"Operations: {len(operations_performed)}",
            payload=self.state.to_payload(),
            next_node=None  # Process complete
        )
        
        state.decision_trace.append({
            "prd_path": str(prd_path),
            "operations_performed": operations_performed,
            "parents_updated": len(parents),
            "children_updated": len(children),
            "references_updated": len(references),
            "workflow_complete": True
        })
        
        return state
    
    def _execute_without_results_report(self) -> AgentState:
        """Step 2.0: When Results Report does not exist"""
        
        # Check if this is a file read request
        if self._is_file_read_request():
            return self._execute_file_read()
        
        # Step 2.1: Query PRD documents
        prd_dir = self.workspace_root / "docs_2" / "prd"
        prd_dir.mkdir(parents=True, exist_ok=True)
        
        # Find latest PRD or create new one
        prd_pattern = r'PRD-P(\d+)\.md'
        Part_N = self._extract_Part_Number_from_context()
        
        prd_path = prd_dir / f"PRD-P{Part_N}.md"
        
        # Step 2.3: Create new PRD if not exists
        if not prd_path.exists():
            prd_content = self._generate_prd_template(Part_N)
            prd_path.write_text(prd_content, encoding='utf-8')
            self.state.sources.prd_path = str(prd_path)
            
            state = AgentState.create_success(
                tier=self.tier,
                logic_summary=f"Created new PRD document: {prd_path.name}",
                payload=self.state.to_payload(),
                next_node=None
            )
            
            state.decision_trace.append({
                "prd_created": str(prd_path),
                "workflow_complete": True
            })
            
            return state
        else:
            # PRD exists, update it
            self.state.sources.prd_path = str(prd_path)
            
            state = AgentState.create_success(
                tier=self.tier,
                logic_summary=f"PRD document already exists: {prd_path.name}",
                payload=self.state.to_payload(),
                next_node=None
            )
            
            return state


def main(user_input: str, workspace_root: str = ".", previous_payload: Optional[Dict[str, Any]] = None) -> AgentState:
    """
    Tier E main entry point
    
    Args:
        user_input: User input text
        workspace_root: Workspace root directory
        previous_payload: Payload passed from the previous Tier (Tier B)
    
    Returns:
        AgentState: Execution result and next step information
    """
    context = TaskContext(
        user_input=user_input,
        current_tier="E",
        workspace_root=workspace_root
    )
    
    engine = DocumentManagementEngine(context, previous_payload)
    state = engine.execute()
    
    state.emit()
    
    return state


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Tier E - Document Management")
    parser.add_argument("command", nargs="?", default="execute", 
                       help="Command to execute: execute, reindex")
    parser.add_argument("--root", type=str, default=".", 
                       help="Workspace root directory")
    parser.add_argument("--db", type=str, default=".agent_index/ci_db.sqlite",
                       help="Database path for indexing")
    parser.add_argument("--commit-threshold", type=int, default=6,
                       help="Commit threshold for indexing")
    parser.add_argument("--upload-release", action="store_true",
                       help="Upload index as GitHub release")
    parser.add_argument("--gh-token", type=str, default=None,
                       help="GitHub token for release operations")
    parser.add_argument("--force", action="store_true",
                       help="Force indexing regardless of threshold")
    
    args = parser.parse_args()
    
    if args.command == "reindex":
        # Run repository indexing
        context = TaskContext(
            user_input="reindex",
            current_tier="E",
            workspace_root=args.root
        )
        
        engine = DocumentManagementEngine(context, None)
        
        result = engine.run_repository_index(
            root=Path(args.root),
            db_path=Path(args.db),
            commit_threshold=args.commit_threshold,
            upload_release=args.upload_release,
            gh_token=args.gh_token,
            force=args.force
        )
        
        # Convert to AgentState and emit
        if result["status"] == "SUCCESS":
            state = AgentState.create_success(
                tier="E",
                logic_summary=f"Index built: {result['reason']}. Runtime: {result['runtime_seconds']:.2f}s",
                payload=result,
                next_node=None
            )
        elif result["status"] == "SKIPPED":
            state = AgentState(
                tier="E",
                status="SKIPPED",
                logic_summary=f"Indexing skipped: {result['reason']}. Commits: {result.get('commits_since_last', 'N/A')}/{result.get('threshold', 6)}",
                payload=result,
                next_node=None,
                decision_trace={}
            )
        else:
            state = AgentState.create_failure(
                tier="E",
                error_msg=", ".join(result.get("errors", ["Unknown error"])),
                logic_summary=f"Indexing failed: {result['reason']}"
            )
            state.payload = result
        
        state.emit()
        
        # Exit with appropriate code
        import sys
        if result["status"] == "FAILED":
            sys.exit(1)
        elif result["status"] == "SKIPPED":
            sys.exit(0)
        else:
            sys.exit(0)
    
    else:
        # Default: document management execution
        test_payload = {
            "prd_path": "docs_2/prd/PRD-P1.md",
            "wpd_sources": ["docs_2/P1/P1-Test.md"]
        }
        
        main("Document management after execution", 
             workspace_root=args.root,
             previous_payload=test_payload)
