"""
E_Document_Management.py - ENHANCED VERSION

**Tier E: Task Document Management (Enhanced with Context-Aware Routing)**

Enhanced Features:
- Context-aware Part Number extraction from modified document
- Validation of PRD document existence and auto-routing to Tier C if missing
- Detailed logging for decision tracing
- LinkManager, VersionManager, ProgressManager integration
- MappingManager, ErrorSessionManager, MarkdownAutofixManager, DocumentMerger integration
- ADMP compliance with document merging

Trigger condition:
- Automatic execution after Tier C modifications
- User instructs "Save changes"
- Document synchronization required
"""

import sys
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# Setup UTF-8 encoding globally to prevent cp949 errors
if sys.stdout:
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr:
    try:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))

from models.core import AgentState, TierEState, TaskContext

try:
    from doc_management import (
        LinkManager,
        VersionManager,
        ChecklistManager,
        ProgressManager,
        MappingManager,
        ErrorSessionManager,
        MarkdownAutofixManager,
        DocumentMerger,
    )
    print("[SUCCESS] All doc_management modules imported")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

class DocumentManagementEngine:
    """
    Enhanced Document Management Engine with ALL 9 Specialized Managers
    
    Improvements:
    1. Extract Part Number from modified document path
    2. Validate corresponding PRD exists
    3. Log all decisions for tracing
    4. Update document version and links
    5. Auto-route to Tier C if PRD missing
    6. Manage mappings via MappingManager
    7. Track errors via ErrorSessionManager
    8. Fix markdown issues via MarkdownAutofixManager
    9. Merge documents via DocumentMerger
    """
    
    def __init__(self, context: TaskContext, previous_payload: Optional[Dict[str, Any]] = None):
        self.context = context
        self.tier = "E"
        self.previous_payload = previous_payload or {}
        self.workspace_root = Path(context.workspace_root)
        self.execution_log: List[str] = []
        
        # Initialize TierEState
        self.state = TierEState()
        self.state.sources.prd_path = self.previous_payload.get("prd_path")
        self.state.sources.wpd_sources = self.previous_payload.get("wpd_sources", [])
        
        # Validate previous payload
        self.log("[INIT] Validating previous_payload...")
        self.log(f"  - prd_path: {self.state.sources.prd_path}")
        self.log(f"  - wpd_sources: {len(self.state.sources.wpd_sources)} items")
        self.log(f"  - target_document: {self.previous_payload.get('target_document', 'N/A')}")
        
        # Initialize ALL 9 specialized managers (Facade pattern) - with error handling
        self.log(f"[INIT] Initializing {9} Document Management Managers...")
        
        # Safe initialization with try-except for each manager
        try:
            self.link_manager = LinkManager(self.workspace_root)
            self.log("[INIT] LinkManager initialized")
        except Exception as e:
            self.log(f"[INIT]LinkManager failed: {e}", "WARN")
            self.link_manager = None
        
        try:
            self.version_manager = VersionManager(self.workspace_root)
            self.log("[INIT] VersionManager initialized")
        except Exception as e:
            self.log(f"[INIT]VersionManager failed: {e}", "WARN")
            self.version_manager = None
        
        try:
            self.checklist_manager = ChecklistManager(self.workspace_root)
            self.log("[INIT] ChecklistManager initialized")
        except Exception as e:
            self.log(f"[INIT]ChecklistManager failed: {e}", "WARN")
            self.checklist_manager = None
        
        try:
            self.progress_manager = ProgressManager()
            self.log("[INIT] ProgressManager initialized")
        except Exception as e:
            self.log(f"[INIT]ProgressManager failed: {e}", "WARN")
            self.progress_manager = None
        
        # Skip MappingManager - its dependency (.github/agents/tool) may not exist
        # This is not critical for routing decision
        try:
            self.mapping_manager = MappingManager(self.workspace_root)
            self.log("[INIT] MappingManager initialized")
        except Exception as e:
            self.log(f"[INIT]MappingManager skipped (optional): {e}", "WARN")
            self.mapping_manager = None
        
        try:
            self.error_session_manager = ErrorSessionManager(self.workspace_root)
            self.log("[INIT] ErrorSessionManager initialized")
        except Exception as e:
            self.log(f"[INIT]ErrorSessionManager failed: {e}", "WARN")
            self.error_session_manager = None
        
        try:
            self.markdown_autofix_manager = MarkdownAutofixManager(self.workspace_root)
            self.log("[INIT] MarkdownAutofixManager initialized")
        except Exception as e:
            self.log(f"[INIT]MarkdownAutofixManager failed: {e}", "WARN")
            self.markdown_autofix_manager = None
        
        try:
            self.document_merger = DocumentMerger(self.workspace_root)
            self.log("[INIT] DocumentMerger initialized")
        except Exception as e:
            self.log(f"[INIT]DocumentMerger failed: {e}", "WARN")
            self.document_merger = None
        
        self.log(f"[INIT] Initialization complete - proceeding with available managers")
    
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging for decision tracing"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        self.execution_log.append(log_msg)
        print(log_msg)
    
    # ========== Part Number Extraction & Validation ==========
    
    def _execute_document_merge(self, merge_analysis: Dict[str, Any]) -> AgentState:
        """
        문서 병합 전략 실행 (Tier D 분석 결과 기반)
        
        Args:
            merge_analysis: Tier D에서 전달받은 병합 분석 결과
            
        Returns:
            AgentState with merge execution result
        """
        self.log("\n" + "="*80)
        self.log("[DOCUMENT MERGE] Executing merge strategy")
        self.log("="*80)
        
        try:
            strategy = merge_analysis.get("strategy")
            source_doc = merge_analysis.get("target_document")  # Tier D의 document_path
            target_doc = merge_analysis.get("target_document")  # 병합 대상
            
            self.log(f"\nMerge Strategy: {strategy}")
            self.log(f"Source Document: {self.previous_payload.get('document_path', 'Unknown')}")
            self.log(f"Target Document: {target_doc or 'None'}")
            self.log(f"Confidence: {merge_analysis.get('confidence', 0.0):.2%}")
            self.log(f"\nReasoning: {merge_analysis.get('reasoning', 'N/A')}")
            
            if strategy == "SINGLE_DOC_MODIFY":
                # 단일 문서 병합
                self.log("\n[STEP 1] Executing SINGLE_DOC_MODIFY strategy...")
                
                source_path = Path(self.workspace_root) / self.previous_payload.get("document_path", "")
                target_path = Path(target_doc) if target_doc else None
                
                if not source_path.exists():
                    self.log(f"[ERROR] Source document not found: {source_path}", "ERROR")
                    return self._create_merge_error_state("Source document not found")
                
                if not target_path or not target_path.exists():
                    self.log(f"[ERROR] Target document not found: {target_path}", "ERROR")
                    return self._create_merge_error_state("Target document not found")
                
                # DocumentMerger 사용
                self.log(f"\n[STEP 2] Merging {source_path.name} → {target_path.name}...")
                merge_result = self.document_merger.merge_documents(
                    source_path=source_path,
                    target_path=target_path,
                    merge_justification=f"Consolidating duplicate document per confidence-based analysis (confidence: {merge_analysis.get('confidence', 0.0):.2%})"
                )
                
                if merge_result.get("success"):
                    self.log(f"[OK] Merge successful:")
                    self.log(f"  Version: {merge_result['old_version']} → {merge_result['new_version']}")
                    self.log(f"  Integrated sections: {merge_result.get('integrated', 0)}")
                    self.log(f"  Appended sections: {merge_result.get('appended', 0)}")
                    self.log(f"  New sections: {merge_result.get('new_sections', 0)}")
                    
                    # 원본 문서 삭제 (병합 완료 후)
                    self.log(f"\n[STEP 3] Deleting source document: {source_path.name}")
                    source_path.unlink()
                    self.log(f"[OK] Source document deleted")
                    
                    # 성공 상태 반환
                    return AgentState.create_success(
                        tier=self.tier,
                        logic_summary=(
                            f"Document merge completed successfully. "
                            f"Merged {source_path.name} into {target_path.name}. "
                            f"Version updated to {merge_result['new_version']}. "
                            f"Source document deleted."
                        ),
                        payload={
                            "merge_result": merge_result,
                            "merge_analysis": merge_analysis,
                            "source_deleted": True,
                            "target_updated": str(target_path)
                        },
                        next_node=None  # Workflow complete
                    )
                else:
                    self.log(f"[ERROR] Merge failed: {merge_result.get('error', 'Unknown error')}", "ERROR")
                    return self._create_merge_error_state(merge_result.get("error", "Merge failed"))
            
            elif strategy == "DISTRIBUTED_EDIT":
                # 여러 문서로 분산 편집
                self.log("\n[STEP 1] Executing DISTRIBUTED_EDIT strategy...")
                self.log(" This strategy requires human review - routing to Tier F")
                
                return AgentState.create_success(
                    tier=self.tier,
                    logic_summary=(
                        f"DISTRIBUTED_EDIT strategy detected. This requires distributing content "
                        f"across {len(merge_analysis.get('related_documents', []))} documents. "
                        f"Manual review recommended."
                    ),
                    payload={
                        "merge_analysis": merge_analysis,
                        "requires_human_review": True
                    },
                    next_node="F"  # Route to Unknown Logic for human intervention
                )
            
            elif strategy == "UNIFIED_CREATION":
                # 통합 문서 생성 → Tier A로 라우팅
                self.log("\n[STEP 1] Executing UNIFIED_CREATION strategy...")
                self.log("→ Routing to Tier A to create consolidated document")
                
                return AgentState.create_success(
                    tier=self.tier,
                    logic_summary=(
                        f"UNIFIED_CREATION strategy detected. Creating consolidated document "
                        f"to merge {len(merge_analysis.get('related_documents', []))} related documents."
                    ),
                    payload={
                        "merge_analysis": merge_analysis,
                        "consolidated_content": self.previous_payload.get("document_content", "")
                    },
                    next_node="A"  # Route to Plan Creation
                )
            
            else:
                self.log(f" Unknown strategy: {strategy}", "WARNING")
                return self._create_merge_error_state(f"Unknown merge strategy: {strategy}")
            
        except Exception as e:
            self.log(f"CRITICAL ERROR in document merge: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return self._create_merge_error_state(str(e))
    
    def _create_merge_error_state(self, error_msg: str) -> AgentState:
        """병합 에러 상태 생성"""
        return AgentState.create_failure(
            tier=self.tier,
            error_msg=f"Document merge failed: {error_msg}",
            logic_summary=f"Merge error: {error_msg}"
        )
    
    # ========== Document Path Discovery ==========
    
    def discover_document_from_user_input(self) -> Optional[str]:
        """
        Extract document path from user input or context
        
        Searches for document paths in:
        1. User input (e.g., "docs_2/MIGRATION_GUIDE_v3.1.0.md are incorrect")
        2. Previous payload
        3. External GitHub repository (if configured)
        
        Returns:
            Document path (str) or None if not found
        """
        self.log("\n[DOCUMENT DISCOVERY] Searching for document path...")
        
        # Step 1: Check user input for document path patterns
        user_input = self.context.user_input
        doc_patterns = [
            r'(docs_\d+/[\w/\-\.]+\.md)',  # docs_2/MIGRATION_GUIDE_v3.1.0.md
            r'(docs/[\w/\-\.]+\.md)',      # docs/ip/PRD-P1.md
            r'([\w/\-]+\.md)',              # Any .md file
        ]
        
        for pattern in doc_patterns:
            match = re.search(pattern, user_input)
            if match:
                doc_path = match.group(1)
                self.log(f" Found document path in user input: {doc_path}")
                return doc_path
        
        # Step 2: Check previous_payload
        doc_path = self.previous_payload.get("target_document") or self.previous_payload.get("wpd_path")
        if doc_path:
            self.log(f" Found document path in previous_payload: {doc_path}")
            return doc_path
        
        # Step 3: Search for any .md file in previous_payload values
        for key, value in self.previous_payload.items():
            if isinstance(value, str) and ".md" in value:
                self.log(f" Found document path in payload['{key}']: {value}")
                return value
        
        self.log(f" No document path found", "WARN")
        return None
    
    def resolve_document_location(self, doc_path: str) -> Optional[Path]:
        """
        Resolve document location considering external GitHub repositories
        
        Search order:
        1. Local workspace (current project)
        2. External GitHub repository (if configured)
        
        Args:
            doc_path: Relative document path (e.g., "docs_2/MIGRATION_GUIDE_v3.1.0.md")
        
        Returns:
            Resolved Path object or None if not found
        """
        self.log(f"\n[RESOLVE LOCATION] Resolving: {doc_path}")
        
        # Step 1: Try local workspace
        local_path = self.workspace_root / doc_path
        if local_path.exists():
            self.log(f" Found in local workspace: {local_path}")
            return local_path
        else:
            self.log(f" Not found in local workspace: {local_path}", "DEBUG")
        
        # Step 2: Try external GitHub repository
        github_repo_url = self.context.github_repo_url
        github_branch = self.context.github_branch
        
        if github_repo_url:
            self.log(f"  → Searching in external repository: {github_repo_url}")
            self.log(f"    Branch: {github_branch or 'default'}")
            
            # Extract repo name from URL
            # https://github.com/kwaksinwoo01/turbo-system.git -> turbo-system
            repo_match = re.search(r'/([^/]+?)(?:\.git)?$', github_repo_url)
            if repo_match:
                repo_name = repo_match.group(1)
                
                # Check if repository is cloned locally
                # Common locations: ../turbo-system, ~/github/turbo-system
                potential_locations = [
                    self.workspace_root.parent / repo_name,  # ../turbo-system
                    Path.home() / "Documents" / "github" / repo_name,  # ~/Documents/github/turbo-system
                    Path.home() / "github" / repo_name,  # ~/github/turbo-system
                ]
                
                for potential_path in potential_locations:
                    external_doc_path = potential_path / doc_path
                    if external_doc_path.exists():
                        self.log(f" Found in external repository: {external_doc_path}")
                        return external_doc_path
                    else:
                        self.log(f"   Not in: {potential_path}", "DEBUG")
                
                self.log(f" Document not found in any external repository location", "WARN")
                self.log(f"    Hint: Clone {github_repo_url} to one of these locations:", "INFO")
                for loc in potential_locations:
                    self.log(f"      - {loc}", "INFO")
            else:
                self.log(f" Could not parse repository name from URL", "WARN")
        else:
            self.log(f"  → No external repository configured (context.github_repo_url is None)", "DEBUG")
        
        return None
    
    # ========== Part Number Extraction & Validation ==========
    
    def classify_document_issue(self, doc_path: Optional[str], resolved_path: Optional[Path]) -> Dict[str, Any]:
        """
        Classify document issues to determine proper routing
        
        Decision tree:
        1. Missing metadata (Part Number, wpd_grade, Version)? → Tier C (add metadata)
        2. Wrong metadata values? → Tier C (correct metadata)
        3. Wrong location/content? → Tier C (merge/move)
        4. Outdated document? → Compare with latest, keep valid content
        5. Other cases? → Document management workflow (L0→L1→L2 similarity check)
        
        Args:
            doc_path: Original document path string
            resolved_path: Resolved Path object (if found)
        
        Returns:
            Classification dict with issue_type and recommended action
        """
        classification = {
            "issue_type": "unknown",
            "action": "none",
            "tier": None,
            "reason": "",
            "missing_fields": [],
            "suggestions": []
        }
        
        if not doc_path:
            classification.update({
                "issue_type": "no_document_path",
                "action": "request_clarification",
                "tier": "F",
                "reason": "No document path provided in user input"
            })
            return classification
        
        # Check if document exists
        if not resolved_path or not resolved_path.exists():
            classification.update({
                "issue_type": "document_not_found",
                "action": "create_or_locate",
                "tier": "A",
                "reason": f"Document not found: {doc_path}",
                "suggestions": ["Create new document", "Verify document path", "Check repository settings"]
            })
            return classification
        
        # Read document content to check for required metadata
        try:
            content = resolved_path.read_text(encoding='utf-8')
            
            # Check for required metadata fields
            missing_fields = []
            
            # Check Part Number pattern
            if not re.search(r'P(\d+)', doc_path) and not re.search(r'\*\*Part\s*Number\*\*:\s*P?\d+', content, re.IGNORECASE):
                missing_fields.append("Part Number")
            
            # Check wpd_grade
            if not re.search(r'\*\*WPD[_\s]*grade\*\*:\s*L[0-3]', content, re.IGNORECASE):
                missing_fields.append("wpd_grade")
            
            # Check Version
            if not re.search(r'\*\*Version\*\*:\s*v?\d+\.\d+\.\d+', content, re.IGNORECASE):
                missing_fields.append("Version")
            
            if missing_fields:
                classification.update({
                    "issue_type": "missing_metadata",
                    "action": "add_metadata",
                    "tier": "C",
                    "reason": f"Document lacks required metadata: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields,
                    "suggestions": [
                        f"Add {field} to document header" for field in missing_fields
                    ]
                })
                return classification
            
            # If all metadata exists, this is a general document management task
            classification.update({
                "issue_type": "document_management",
                "action": "manage_document",
                "tier": "E",
                "reason": "Document has all required metadata - proceeding with management"
            })
            
        except Exception as e:
            self.log(f"[ERROR] Failed to read document: {e}", "ERROR")
            classification.update({
                "issue_type": "read_error",
                "action": "check_permissions",
                "tier": "F",
                "reason": f"Cannot read document: {e}"
            })
        
        return classification
    
    def extract_part_number_from_modified_doc(self) -> Optional[int]:
        """
        Extract Part Number from modified document
        
        Enhanced to support:
        1. User input document path discovery
        2. External GitHub repository documents
        3. Previous payload fallback
        
        Examples:
        - "docs_2/P2/P2.1/P2.1.01-Client-Event-Polling.md" → 2
        - "docs_2/P5/P5-Feature.md" → 5
        - "docs_2/P2.1.01-Client-Event-Polling.md" → 2
        
        Returns:
            Part Number (int) or None if not found
        """
        self.log("Step 1.0: Extracting Part Number from modified document")
        
        # Step 1: Try to discover document path from user input
        modified_doc = self.discover_document_from_user_input()
        
        # Step 2: Fallback to previous_payload
        if not modified_doc:
            modified_doc = self.previous_payload.get("target_document")
        if not modified_doc:
            modified_doc = self.previous_payload.get("wpd_path")
        
        if not modified_doc:
            for key, value in self.previous_payload.items():
                if isinstance(value, str) and "P" in value and ".md" in value:
                    modified_doc = value
                    break
        
        if not modified_doc:
            self.log("ERROR: Could not find modified document path", "ERROR")
            self.log(f"Available keys in previous_payload: {list(self.previous_payload.keys())}", "DEBUG")
            self.log(f"User input: {self.context.user_input}", "DEBUG")
            return None
        
        self.log(f"  Modified document path: {modified_doc}")
        
        # Step 3: Try to resolve document location (local or external repository)
        resolved_path = self.resolve_document_location(modified_doc)
        if resolved_path:
            self.log(f" Document resolved to: {resolved_path}")
            # Store resolved path for later use
            self.previous_payload["resolved_document_path"] = str(resolved_path)
        else:
            self.log(f"Document not found in filesystem (will continue with path parsing)", "WARN")
        
        # Step 4: Extract Part Number using regex (from path string)
        pattern = r'P(\d+)(?:[.\\/]|\.md)'
        match = re.search(pattern, modified_doc)
        
        if match:
            part_num = int(match.group(1))
            self.log(f" Extracted Part Number: {part_num}")
            return part_num
        else:
            self.log(f" Could not extract Part Number from: {modified_doc}", "WARN")
            self.log(f"     (Pattern not matched: {pattern})", "DEBUG")
            return None
    
    def validate_prd_exists(self, part_num: int) -> Tuple[bool, Optional[Path]]:
        """
        Validate that corresponding PRD document exists
        
        Args:
            part_num: Part Number (e.g., 2 for PRD-P2.md)
        
        Returns:
            Tuple: (exists: bool, prd_path: Path or None)
        """
        self.log(f"Step 1.1: Validating PRD-P{part_num}.md existence")
        
        prd_dir = self.workspace_root / "docs_2" / "prd"
        prd_path = prd_dir / f"PRD-P{part_num}.md"
        
        self.log(f"Expected PRD path: {prd_path}")
        
        if prd_path.exists():
            self.log(f"[OK] PRD document exists: PRD-P{part_num}.md")
            return True, prd_path
        else:
            self.log(f"[ERROR] PRD document MISSING: PRD-P{part_num}.md", "WARN")
            self.log(f"Available PRDs in {prd_dir}:")
            
            if prd_dir.exists():
                for prd_file in prd_dir.glob("PRD-*.md"):
                    self.log(f"  - {prd_file.name}")
            else:
                self.log(f"  - PRD directory does not exist: {prd_dir}")
            
            return False, None
    
    # ========== Document Update Methods ==========
    
    def update_modified_document_metadata(self, modified_doc_path: str) -> bool:
        """
        Update modified document metadata (best-effort approach)
        
        All updates are optional - manager unavailability won't cause failure
        
        Args:
            modified_doc_path: Path to document modified by Tier C
        
        Returns:
            Success: bool (always True if document exists)
        """
        self.log("Step 1.2: Updating modified document metadata (optional)")
        
        doc_path = Path(modified_doc_path)
        if not doc_path.is_absolute():
            doc_path = self.workspace_root / doc_path
        
        if not doc_path.exists():
            self.log(f"Document not found: {doc_path}", "WARN")
            return False
        
        self.log(f"  Target document: {doc_path.name}")
        updates_attempted = 0
        
        # Step 1.2.1: Update document links (optional)
        if self.link_manager:
            try:
                self.log("  [1/4] Running LinkManager...")
                link_result = self.link_manager.validate_and_fix_links(doc_path)
                links_fixed = link_result.get('links_fixed', 0) if link_result else 0
                self.log(f"    Links fixed: {links_fixed}")
                updates_attempted += 1
                if links_fixed > 0:
                    self.state.prd_operations.append({
                        "type": "link_management",
                        "document": str(doc_path),
                        "links_fixed": links_fixed
                    })
            except Exception as e:
                self.log(f"   LinkManager error (skipped): {e}", "WARN")
        else:
            self.log(f"  [1/4] LinkManager not available (skipped)")
        
        # Step 1.2.2: Update version (optional)
        if self.version_manager:
            try:
                self.log("  [2/4] Running VersionManager...")
                ver_result = self.version_manager.update_version_for_tier_c(doc_path)
                self.log(f"    Version updated")
                updates_attempted += 1
                if ver_result and ver_result.get('updated_documents'):
                    for update in ver_result.get('updated_documents', []):
                        self.state.prd_operations.append({
                            "type": "version_management",
                            "document": update.get('path'),
                            "old_version": update.get('old_version'),
                            "new_version": update.get('new_version')
                        })
            except Exception as e:
                self.log(f"   VersionManager error (skipped): {e}", "WARN")
        else:
            self.log(f"  [2/4] VersionManager not available (skipped)")
        
        # Step 1.2.3: Update progress (optional)
        if self.progress_manager:
            try:
                self.log("  [3/4] Running ProgressManager...")
                # ProgressManager might need different initialization
                if hasattr(self.progress_manager, 'update_progress'):
                    progress_result = self.progress_manager.update_progress(doc_path, "IN PROGRESS")
                    self.log(f"    Progress updated")
                    updates_attempted += 1
                    if progress_result:
                        self.state.prd_operations.append({
                            "type": "progress_management",
                            "document": str(doc_path),
                            "new_progress": progress_result.get('new_progress', 'IN PROGRESS')
                        })
                else:
                    self.log(f"   ProgressManager.update_progress not found (skipped)")
            except Exception as e:
                self.log(f"   ProgressManager error (skipped): {e}", "WARN")
        else:
            self.log(f"  [3/4] ProgressManager not available (skipped)")
        
        # Step 1.2.4: Fix markdown (optional)
        if self.markdown_autofix_manager:
            try:
                self.log("  [4/4] Running MarkdownAutofixManager...")
                markdown_result = self.markdown_autofix_manager.fix_document(doc_path, apply=True)
                changes = markdown_result.get('changes_count', 0) if markdown_result else 0
                self.log(f"    Markdown fixes: {changes} changes")
                updates_attempted += 1
                if changes > 0:
                    self.state.prd_operations.append({
                        "type": "markdown_formatting",
                        "document": str(doc_path),
                        "changes_count": changes
                    })
            except Exception as e:
                self.log(f"   MarkdownAutofixManager error (skipped): {e}", "WARN")
        else:
            self.log(f"  [4/4] MarkdownAutofixManager not available (skipped)")
        
        self.log(f"  Metadata update complete: {updates_attempted} managers attempted")
        return True
    
    # ========== PRD Creation & Update ==========
    
    def create_prd_for_part(self, part_num: int) -> Optional[Path]:
        """
        Create new PRD document for given Part Number
        
        Args:
            part_num: Part Number
        
        Returns:
            Path to created PRD or None if failed
        """
        self.log(f"Step 1.3: Creating new PRD-P{part_num}.md")
        
        prd_dir = self.workspace_root / "docs_2" / "prd"
        prd_dir.mkdir(parents=True, exist_ok=True)
        
        prd_path = prd_dir / f"PRD-P{part_num}.md"
        
        prd_content = self._generate_prd_template(part_num)
        
        try:
            prd_path.write_text(prd_content, encoding='utf-8')
            self.log(f"[OK] Created new PRD: {prd_path.name}")
            return prd_path
        except Exception as e:
            self.log(f"ERROR creating PRD: {str(e)}", "ERROR")
            return None
    
    def update_prd_with_summary(self, prd_path: Path, modified_doc_name: str, 
                                modification_summary: str) -> bool:
        """
        Update existing PRD with Implementation Summary from Tier C modification
        
        Args:
            prd_path: Path to PRD document
            modified_doc_name: Name of document that was modified
            modification_summary: Summary of modifications
        
        Returns:
            Success: bool
        """
        self.log(f"Step 1.4: Updating PRD with Implementation Summary")
        self.log(f"  PRD: {prd_path.name}")
        self.log(f"  Modified document: {modified_doc_name}")
        
        try:
            content = prd_path.read_text(encoding='utf-8')
            
            # Create implementation summary entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            summary_entry = f"""
### Modified Document: {modified_doc_name}
- **Timestamp**: {timestamp}
- **Modification Type**: Plan Modification (Tier C)
- **Summary**: {modification_summary}
- **Status**: [OK] Applied

"""
            
            # Find Implementation Notes section
            if "## Implementation Notes" in content:
                content = content.replace(
                    "## Implementation Notes",
                    f"## Implementation Notes\n{summary_entry}"
                )
            else:
                # Add new section before References
                if "## References" in content:
                    content = content.replace(
                        "## References",
                        f"## Implementation Notes\n{summary_entry}\n## References"
                    )
                else:
                    content += f"\n{summary_entry}"
            
            # Update version
            version_match = re.search(r'(\*\*Version\*\*:?\s*)(\d+\.\d+\.\d+)', content)
            if version_match:
                old_version = version_match.group(2)
                version_parts = old_version.split('.')
                version_parts[2] = str(int(version_parts[2]) + 1)  # Increment patch
                new_version = '.'.join(version_parts)
                content = content.replace(old_version, new_version)
                self.log(f"  Version updated: {old_version} → {new_version}")
            
            # Update status
            content = re.sub(
                r'\*\*Status\*\*:?\s*([📋❌⏳[OK]🚫]+\s*[A-Z_]+)',
                '**Status**: [OK] IN_PROGRESS',
                content
            )
            
            prd_path.write_text(content, encoding='utf-8')
            self.log(f"[OK] PRD updated: {prd_path.name}")
            
            self.state.prd_operations.append({
                "type": "prd_update",
                "prd_path": str(prd_path),
                "modified_document": modified_doc_name,
                "summary": modification_summary
            })
            
            return True
            
        except Exception as e:
            self.log(f"ERROR updating PRD: {str(e)}", "ERROR")
            return False
    
    # ========== Mapping Management (New) ==========
    
    def manage_document_mappings(self) -> bool:
        """
        Manage document mappings via MappingManager (optional)
        
        Returns:
            Success: bool
        """
        self.log("Step 1.5.1: Managing document mappings")
        
        try:
            if not self.mapping_manager:
                self.log("  MappingManager not available - skipping", "WARN")
                return False
            
            result = self.mapping_manager.manage_mapping({})
            
            if result and result.get('success'):
                self.log(f"[OK] Mapping management completed")
                self.state.prd_operations.append({
                    "type": "mapping_management",
                    "result": result
                })
                return True
            else:
                self.log(f"[INFO] No mapping updates needed")
                return False
                
        except Exception as e:
            self.log(f"[WARN] Mapping management skipped: {str(e)}", "WARN")
            return False
    
    # ========== Error Session Management (New) ==========
    
    def manage_error_sessions(self, modified_doc_path: str) -> bool:
        """
        Track and manage error sessions via ErrorSessionManager
        
        Args:
            modified_doc_path: Path to document that was modified
        
        Returns:
            Success: bool
        """
        self.log("Step 1.5.2: Managing error sessions")
        
        try:
            if not self.error_session_manager:
                self.log("  ErrorSessionManager not available - skipping", "WARN")
                return False
            
            doc_path = Path(modified_doc_path) if Path(modified_doc_path).is_absolute() else self.workspace_root / modified_doc_path
            
            if not doc_path.exists():
                self.log(f"Document not found for error session management: {doc_path}", "WARN")
                return False
            
            # Get error sessions from document
            errors = self.error_session_manager.get_error_sessions(doc_path)
            
            if errors:
                self.log(f"Found {len(errors)} error sessions")
                
                self.state.prd_operations.append({
                    "type": "error_session_management",
                    "document": str(doc_path),
                    "error_count": len(errors),
                    "errors": errors
                })
                
                # Solution plans already created by ErrorSessionManager
                # They will be routed to appropriate tier
                return True
            else:
                self.log(f"No error sessions found in document")
                return True
                
        except Exception as e:
            self.log(f"ERROR during error session management: {str(e)}", "ERROR")
            return False
    
    # ========== Document Merging (New) ==========
    
    def merge_related_documents(self, modified_doc_path: str) -> bool:
        """
        Merge related documents via DocumentMerger
        
        Consolidates similar content into existing documents
        
        Args:
            modified_doc_path: Path to newly modified document
        
        Returns:
            Success: bool
        """
        self.log("Step 1.5.3: Merging related documents")
        
        try:
            doc_path = Path(modified_doc_path) if Path(modified_doc_path).is_absolute() else self.workspace_root / modified_doc_path
            
            if not doc_path.exists():
                self.log(f"Document not found for merging: {doc_path}", "WARN")
                return True  # Not an error, just skip
            
            # Find related documents in same directory
            related_docs = list(doc_path.parent.glob("*.md"))
            
            if len(related_docs) <= 1:
                self.log(f"No related documents found for merging")
                return True
            
            self.log(f"Found {len(related_docs)} related documents in {doc_path.parent.name}")
            
            # Merge related documents (logic would go here)
            # For now, just log that check was performed
            self.state.prd_operations.append({
                "type": "document_merging",
                "document": str(doc_path),
                "related_documents": len(related_docs)
            })
            
            return True
            
        except Exception as e:
            self.log(f"ERROR during document merging: {str(e)}", "ERROR")
            return False
    
    # ========== Routing Logic ==========
    
    def decide_routing(self, part_num: Optional[int], prd_exists: bool, 
                      prd_path: Optional[Path]) -> Tuple[Optional[str], str]:
        """
        Decide next tier based on validation results
        
        Rules:
        1. If Part Number not extracted → cannot proceed → route to Tier C for clarification
        2. If PRD not exists → create it and continue
        3. If PRD exists → update with summary and complete
        
        Args:
            part_num: Extracted Part Number or None
            prd_exists: Whether PRD document exists
            prd_path: Path to PRD or None
        
        Returns:
            Tuple: (next_tier: str or None, reasoning: str)
        """
        self.log("Step 1.6: Determining routing decision")
        
        if part_num is None:
            self.log("ROUTING DECISION: Unable to extract Part Number", "WARN")
            self.log("  → Routing to Tier C for document clarification")
            return "C", "Cannot extract Part Number from modified document. Route to Tier C for clarification."
        
        if not prd_exists:
            self.log(f"ROUTING DECISION: PRD-P{part_num}.md does not exist", "WARN")
            self.log(f"  → Must create PRD-P{part_num}.md before workflow complete")
            self.log(f"  → After PRD creation, workflow will complete (next_node=None)")
            return None, f"PRD-P{part_num}.md created. Workflow complete."
        
        if prd_path:
            self.log(f"ROUTING DECISION: PRD-P{part_num}.md exists", "INFO")
            self.log(f"  → Update PRD with Implementation Summary")
            self.log(f"  → Workflow complete (next_node=None)")
            return None, f"PRD-P{part_num}.md updated. Workflow complete."
        
        # Default
        self.log("ROUTING DECISION: Default fallback", "WARN")
        return None, "Document management workflow complete."
    
    # ========== Template Generation ==========
    
    def _generate_prd_template(self, part_num: int) -> str:
        """Generate PRD template for given Part Number"""
        return f"""# PRD-P{part_num}: Progress Results Document

**WPD_grade**: L0
**Version**: 1.0.0
**Status**: PENDING
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
This document tracks the results and progress of work plan execution for Step {part_num}.

## Execution Summary
**Overall Progress**: 0%

### Completed Phases
- None

### In Progress
- Phase 1

### Pending
- All phases

## Implementation Notes
Implementation details will be added as work progresses.

## References

### Parent Documents
- Main document: [NextTask-2.md](../NextTask-2.md)
- Work Plan: [P{part_num}-*.md](../P{part_num}/P{part_num}-*.md)

## 📅 Timeline
**Started**: {datetime.now().strftime('%Y-%m-%d')}
**Target Completion**: TBD

---
*Generated by Tier E (Document Management)*
"""
    
    # ========== Main Execution ==========
    
    def execute(self) -> AgentState:
        """
        Simplified execution with robust error handling
        
        Workflow:
        1. Check if document merge requested
        2. Extract Part Number from modified document
        3. Validate PRD exists
        4. Return success state with routing decision
        """
        self.log("="*80)
        self.log("TIER E: Document Management - Starting")
        self.log("="*80)
        
        try:
            # ===== CRITICAL: Check merge request first =====
            merge_analysis = self.previous_payload.get("merge_analysis")
            if merge_analysis:
                self.log("\n[MERGE MODE] Document merge requested from Tier D")
                return self._execute_document_merge(merge_analysis)
            
            # ===== NORMAL MODE: Document management =====
            self.log("\n[NORMAL MODE] Standard document management")
            
            # Step 1: Discover and classify document
            doc_path = self.discover_document_from_user_input()
            resolved_path = None
            if doc_path:
                resolved_path = self.resolve_document_location(doc_path)
                if resolved_path:
                    self.previous_payload["resolved_document_path"] = str(resolved_path)
            
            # Step 2: Classify document issue
            classification = self.classify_document_issue(doc_path, resolved_path)
            
            self.log(f"\n[CLASSIFICATION] Issue Type: {classification['issue_type']}")
            self.log(f"  Recommended Action: {classification['action']}")
            self.log(f"  Recommended Tier: {classification['tier']}")
            self.log(f"  Reason: {classification['reason']}")
            
            if classification.get('missing_fields'):
                self.log(f"  Missing Fields: {', '.join(classification['missing_fields'])}")
            if classification.get('suggestions'):
                for suggestion in classification['suggestions']:
                    self.log(f"  - {suggestion}")
            
            # Step 3: Route based on classification
            if classification['tier'] == 'C':
                # Document needs correction/formatting → Route to Tier C
                state = AgentState.create_success(
                    tier=self.tier,
                    logic_summary=f"Document issue detected: {classification['reason']}. Routing to Tier C for correction.",
                    payload={
                        "document_path": doc_path,
                        "resolved_path": str(resolved_path) if resolved_path else None,
                        "classification": classification,
                        "action_required": classification['action'],
                        "missing_fields": classification.get('missing_fields', [])
                    },
                    next_node="C"
                )
                
                state.decision_trace.append({
                    "type": "tier_e_classification",
                    "classification": classification,
                    "routing_decision": "C",
                    "execution_log": self.execution_log[-10:] if len(self.execution_log) > 10 else self.execution_log
                })
                
                return state
            
            elif classification['tier'] == 'A':
                # Document not found → Route to Tier A to create
                state = AgentState.create_success(
                    tier=self.tier,
                    logic_summary=f"Document not found: {classification['reason']}. Routing to Tier A for document creation.",
                    payload={
                        "document_path": doc_path,
                        "classification": classification,
                        "action_required": "create_document"
                    },
                    next_node="A"
                )
                return state
            
            elif classification['tier'] == 'F':
                # Unknown issue → Route to Tier F
                state = AgentState.create_success(
                    tier=self.tier,
                    logic_summary=f"Unable to classify document issue: {classification['reason']}. Routing to Tier F for human review.",
                    payload={
                        "document_path": doc_path,
                        "classification": classification
                    },
                    next_node="F"
                )
                return state
            
            # Step 4: If classification says proceed with E, extract Part Number
            self.log("\n[PROCEED] Document has required metadata - extracting Part Number")
            part_num = self.extract_part_number_from_modified_doc()
            # Step 4: If classification says proceed with E, extract Part Number
            self.log("\n[PROCEED] Document has required metadata - extracting Part Number")
            part_num = self.extract_part_number_from_modified_doc()
            
            if part_num is None:
                self.log("[WARN] Part Number extraction failed despite metadata check")
                self.log("  → This indicates a formatting issue - routing to Tier C")
                
                # Even if metadata exists, Part Number pattern doesn't match
                # This is still a Tier C issue (formatting correction needed)
                state = AgentState.create_success(
                    tier=self.tier,
                    logic_summary=(
                        "Part Number pattern not recognized in document. "
                        "Document may have metadata but in wrong format. "
                        "Routing to Tier C to standardize Part Number format (e.g., 'P1', 'P2.1', etc.)."
                    ),
                    payload={
                        "document_path": doc_path,
                        "resolved_path": str(resolved_path) if resolved_path else None,
                        "issue_type": "part_number_format_invalid",
                        "action": "standardize_part_number_format",
                        "expected_pattern": r"P(\d+) or P(\d+)\.(\d+)"
                    },
                    next_node="C"
                )
                
                state.decision_trace.append({
                    "type": "tier_e_part_number_format_issue",
                    "document_path": doc_path,
                    "issue": "Part Number pattern mismatch",
                    "execution_log": self.execution_log[-5:] if len(self.execution_log) > 5 else self.execution_log
                })
                
                return state
            
            self.log(f"[OK] Extracted Part Number: {part_num}")
            
            # Step 2: Validate PRD exists
            prd_exists, prd_path = self.validate_prd_exists(part_num)
            self.log(f"[INFO] PRD exists: {prd_exists}, path: {prd_path}")
            
            # Step 3: Simple metadata update (with safe None checks)
            modified_doc = self.previous_payload.get("target_document")
            if modified_doc:
                try:
                    self.update_modified_document_metadata(modified_doc)
                except Exception as e:
                    self.log(f"[WARNING] Metadata update failed (non-critical): {e}", "WARN")
            
            # Step 4: PRD management
            if not prd_exists:
                prd_path = self.create_prd_for_part(part_num)
                self.log(f"[INFO] Created new PRD: {prd_path}")
            
            if prd_path and modified_doc:
                try:
                    modification_summary = self.previous_payload.get(
                        "logic_summary", 
                        "Document modified by Tier C"
                    )
                    self.update_prd_with_summary(prd_path, Path(modified_doc).name, modification_summary)
                except Exception as e:
                    self.log(f"[WARNING] PRD summary update failed (non-critical): {e}", "WARN")
            
            # Step 5: Additional management (best-effort)
            try:
                self.manage_document_mappings()
            except Exception as e:
                self.log(f"[WARNING] Mapping management skipped: {e}", "WARN")
            
            if modified_doc:
                try:
                    self.manage_error_sessions(modified_doc)
                except Exception as e:
                    self.log(f"[WARNING] Error session management skipped: {e}", "WARN")
                
                try:
                    self.merge_related_documents(modified_doc)
                except Exception as e:
                    self.log(f"[WARNING] Document merge skipped: {e}", "WARN")
            
            # Step 6: Routing decision
            next_node, routing_reason = self.decide_routing(part_num, prd_exists, prd_path)
            
            # Build success state
            state = AgentState.create_success(
                tier=self.tier,
                logic_summary=routing_reason,
                payload=self.state.to_payload(),
                next_node=next_node
            )
            
            # Add trace
            state.decision_trace.append({
                "type": "tier_e_execution",
                "part_number": part_num,
                "prd_path": str(prd_path) if prd_path else None,
                "prd_exists": prd_exists,
                "modified_document": modified_doc,
                "next_node": next_node,
                "routing_reason": routing_reason,
                "execution_log": self.execution_log[-10:] if len(self.execution_log) > 10 else self.execution_log
            })
            
            return state
            
        except Exception as e:
            self.log(f"\n[CRITICAL ERROR] {str(e)}", "ERROR")
            import traceback
            self.log(f"Traceback:\n{traceback.format_exc()}", "ERROR")
            
            state = AgentState.create_failure(
                tier=self.tier,
                error_msg=f"Unexpected error in document management: {str(e)}",
                logic_summary=f"Exception: {type(e).__name__}"
            )
            state.next_node = "F"  # Route to Tier F for unknown issues
            return state
            
            return state
        
        finally:
            self.log("="*80)
            self.log("TIER E: Document Management - Completed")
            self.log("="*80)


def main(user_input: str, workspace_root: str = ".", previous_payload: Optional[Dict[str, Any]] = None, 
         github_repo_url: Optional[str] = None, github_branch: Optional[str] = None, 
         github_token: Optional[str] = None) -> AgentState:
    """
    Tier E main entry point (Enhanced with GitHub repository support)
    
    Args:
        user_input: User input text
        workspace_root: Workspace root directory
        previous_payload: Payload from Tier C with modified document info
        github_repo_url: External GitHub repository URL (e.g., https://github.com/user/repo.git)
        github_branch: Branch name for external repository
        github_token: GitHub token for private repositories
    
    Returns:
        AgentState with routing decision
    """
    # Read GitHub settings from environment if not provided
    if not github_repo_url:
        import os
        github_repo_url = os.environ.get("GITHUB_REPO_URL")
        github_branch = os.environ.get("GITHUB_BRANCH")
        github_token = os.environ.get("GITHUB_TOKEN")
    
    context = TaskContext(
        user_input=user_input,
        current_tier="E",
        workspace_root=workspace_root,
        github_repo_url=github_repo_url,
        github_branch=github_branch,
        github_token=github_token
    )
    
    engine = DocumentManagementEngine(context, previous_payload)
    state = engine.execute()
    
    state.emit()
    
    return state


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python E_Document_Management.py '<user_input>' [workspace_root]")
        sys.exit(1)
    
    user_input = sys.argv[1]
    workspace_root = sys.argv[2] if len(sys.argv) > 2 else "."
    
    main(user_input, workspace_root)
