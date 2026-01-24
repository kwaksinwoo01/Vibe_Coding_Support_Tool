"""
B_Performing_Tasks.py

**Tier B: Execute Work Plan Instructions**

역할: 생성된 작업 계획(Work Plan)의 지시사항을 실행합니다.
- 작업 계획의 단계별 실행
- 각 Phase/Milestone 진행 추적
- 중간 결과물(output) 생성 및 저장
- 실행 진행률 업데이트
- 실행 결과를 stdout으로 출력

트리거 조건:
- 사용자가 "Perform work plan" 지시
- 사용자가 "Execute plan" 지시
- Tier A에서 next_node가 "B"로 설정
- 사용자가 "작업 계획 실행" 지시

**Refactored**: Uses new dataclass hierarchy (AgentState, TierBState, DocumentSources, TaskContext)
- Removed duplicate fields (start_time, end_time now local variables)
- Execution tracking moved to DocumentSources
- Simplified function parameters using TaskContext
- Uses TierBState.to_payload() for serialization
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent))

from models.core import AgentState, TierBState, DocumentSources, TaskContext


class TaskExecutionEngine:
    """
    작업 계획 실행 엔진
    
    Refactored to use new dataclass hierarchy:
    - Uses TaskContext for context management
    - Uses TierBState with nested DocumentSources
    - Removes redundant fields and parameters
    """
    
    def __init__(self, context: TaskContext):
        """
        Initialize TaskExecutionEngine with context.
        
        Args:
            context: TaskContext containing user input, workspace, and previous state
        """
        self.context = context
        self.tier = "B"
        
        # Initialize AgentState and TierBState
        self.state = AgentState(tier="B", status="PENDING")
        self.tier_state = TierBState()
        
        # Extract WPD source from previous state (Tier A) if available
        if context.previous_state and context.previous_state.tier == 'A':
            prev_payload = context.previous_state.payload
            created_docs = prev_payload.get('created_documents', [])
            if created_docs:
                self.state.wpd_source_path = created_docs[0]
                self.tier_state.sources.wpd_sources = created_docs
            # Copy wpd_grade from previous state
            self.state.wpd_grade = context.previous_state.wpd_grade or 'L1'
    
    def validate_user_input(self) -> bool:
        """
        사용자 입력이 작업 계획 실행 지시인지 확인 (또는 Tier A로부터 체인됨)
        
        Returns:
            bool: True if input is valid for Tier B execution
        """
        # Check if chained from Tier A via previous_state in context
        if self.context.previous_state and self.context.previous_state.tier == 'A':
            return True
        
        # Check if user input contains Tier B keywords
        keywords = [
            "perform work plan",
            "perform plan",
            "execute plan",
            "start plan",
            "run plan",
            "작업 계획 실행",
            "계획 실행",
            "실행",
            "진행",
            "continue from tier a",
            "continue from tier"
        ]
        
        user_input_lower = self.context.user_input.lower()
        return any(keyword in user_input_lower for keyword in keywords)
    
    def load_work_plan(self) -> Optional[str]:
        """
        Load work plan document with WPD-grade-based priority (L3 → L2 → L1).
        
        When chained from Tier A, selects the highest grade WPD from created documents.
        Priority order: L3 > L2 > L1 > L0
        
        Returns:
            str: Work plan content, or None if not found
        """
        # Check if chained from Tier A and has created documents (from previous_state)
        if self.context.previous_state and self.context.previous_state.tier == 'A':
            created_docs = self.context.previous_state.payload.get('created_documents', [])
            if created_docs:
                # Select WPD by grade priority: L3 > L2 > L1 > L0
                selected_wpd = self._select_wpd_by_grade_priority(created_docs)
                
                if selected_wpd:
                    wpd_path = Path(self.context.workspace_root) / selected_wpd
                    if wpd_path.exists():
                        try:
                            content = wpd_path.read_text(encoding='utf-8')
                            # Extract WPD_grade from document
                            grade_match = re.search(r'\*\*WPD_grade\*\*:\s*(\w+)', content)
                            if grade_match:
                                self.state.wpd_grade = grade_match.group(1)
                            print(f"[Tier B] Selected WPD: {selected_wpd} (Grade: {self.state.wpd_grade})")
                            return content
                        except Exception as e:
                            self.state.add_error(f"Error reading WPD from Tier A: {e}")
        
        # Fallback: use context document_path if provided
        if self.context.document_path:
            try:
                with open(self.context.document_path, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                return None
        
        # 최신 작업 계획 찾기
        docs_path = Path(self.context.workspace_root) / "docs_2" / "working_plans"
        if docs_path.exists():
            plans = sorted(docs_path.glob("WP_*.md"), reverse=True)
            if plans:
                with open(plans[0], "r", encoding="utf-8") as f:
                    return f.read()
        
        return None
    
    def _select_wpd_by_grade_priority(self, created_docs: List[str]) -> Optional[str]:
        """
        Select WPD document by grade priority (L3 > L2 > L1 > L0).
        
        Args:
            created_docs: List of created document paths from Tier A
            
        Returns:
            Selected WPD document path, or None if no valid WPD found
        """
        grade_priority = ["L3", "L2", "L1", "L0"]
        wpd_by_grade = {grade: [] for grade in grade_priority}
        
        # Read each document and extract WPD_grade
        for doc_path_str in created_docs:
            doc_path = Path(self.context.workspace_root) / doc_path_str
            if doc_path.exists() and doc_path.suffix == '.md':
                try:
                    content = doc_path.read_text(encoding='utf-8')
                    # Look for WPD_grade field
                    grade_match = re.search(r'\*\*WPD_grade\*\*:\s*(\w+)', content)
                    if grade_match:
                        grade = grade_match.group(1)
                        if grade in grade_priority:
                            wpd_by_grade[grade].append(doc_path_str)
                    else:
                        # Fallback: detect grade from filename pattern
                        from A_Working_Document_Progress import detect_grade_from_path
                        grade = detect_grade_from_path(doc_path_str)
                        if grade in grade_priority:
                            wpd_by_grade[grade].append(doc_path_str)
                except Exception as e:
                    print(f"[Tier B] Error reading {doc_path_str}: {e}")
        
        # Select highest priority grade with documents
        for grade in grade_priority:
            if wpd_by_grade[grade]:
                # Return first document of highest priority grade
                return wpd_by_grade[grade][0]
        
        # Fallback: return first document
        return created_docs[0] if created_docs else None
    
    def parse_phases(self, plan_content: str, wpd_grade: str = "L1") -> List[Dict[str, Any]]:
        """
        Parse phases from WPD Execution Plan section with hierarchical support.
        
        Handles both old Milestone format and new Phase format:
        - Old: ## 🎯 Milestones
        - New: ## 🔧 Execution Plan with ### Phase sections
        
        Supports hierarchical phases for L2/L3 documents:
        - L1: ### Phase [N]: [Title]
        - L2: ### Phase [N].[M]: [Title] (nested under Phase [N])
        - L3: ### Phase [N].[M].[K]: [Title] (nested under Phase [N].[M])
        
        Args:
            plan_content: WPD document content
            wpd_grade: WPD grade level (L0, L1, L2, L3)
            
        Returns:
            List of phase dictionaries with nested subphases for L2/L3
        """
        phases = []
        lines = plan_content.split("\n")
        
        # Try to find Execution Plan section first (new format)
        in_execution_plan = False
        current_phase = None
        phase_hierarchy = {}  # Track phases by number for nesting
        phase_saved = False
        
        for i, line in enumerate(lines):
            # Check for Execution Plan section
            if "## 🔧 Execution Plan" in line:
                in_execution_plan = True
                continue
            
            # Stop at next major section
            if in_execution_plan and line.startswith("## ") and "🔧 Execution Plan" not in line:
                # Save last phase if exists and not already saved
                if current_phase and not phase_saved:
                    self._add_phase_to_hierarchy(current_phase, phases, phase_hierarchy, wpd_grade)
                    phase_saved = True
                break
            
            # Parse Phase headers: ### Phase [Part_N].[Phase_N]: [Phase Title]
            # Supports: Phase 5.1, Phase 5.1.2, Phase 5.1.2.3 etc.
            if in_execution_plan and line.strip().startswith("### Phase "):
                # Save previous phase if exists
                if current_phase:
                    self._add_phase_to_hierarchy(current_phase, phases, phase_hierarchy, wpd_grade)
                
                # Extract phase info
                phase_match = re.search(r'### Phase\s+([\d.]+):\s+(.+)', line)
                if phase_match:
                    phase_number = phase_match.group(1)
                    phase_title = phase_match.group(2).strip()
                    
                    current_phase = {
                        "title": f"Phase {phase_number}: {phase_title}",
                        "phase_number": phase_number,
                        "phase_title": phase_title,
                        "completed": False,
                        "order": len(phases) + 1,
                        "action": "",
                        "files_to_update": [],
                        "checklist": [],
                        "subphases": [],  # For nested phases in L2/L3
                        "level": len(phase_number.split('.'))  # Depth level (1, 2, 3, etc.)
                    }
                    phase_saved = False
            
            # Extract checklist items within a phase
            elif current_phase and (line.strip().startswith("- [ ]") or line.strip().startswith("- [x]") or line.strip().startswith("- ✅")):
                is_done = "[x]" in line or "✅" in line
                checklist_text = line.replace("- [ ]", "").replace("- [x]", "").replace("- ✅", "").strip()
                current_phase["checklist"].append({
                    "text": checklist_text,
                    "completed": is_done
                })
                # Mark phase as completed if all checklist items are done
                if current_phase["checklist"]:
                    all_done = all(item.get("completed", False) for item in current_phase["checklist"])
                    current_phase["completed"] = all_done
        
        # Save last phase if not already saved
        if current_phase and not phase_saved:
            self._add_phase_to_hierarchy(current_phase, phases, phase_hierarchy, wpd_grade)
        
        # Fallback: Try old Milestone format if no phases found
        if not phases:
            phases = self._parse_legacy_milestones(plan_content)
        
        return phases
    
    def _add_phase_to_hierarchy(self, phase: Dict[str, Any], phases: List[Dict[str, Any]], 
                                 hierarchy: Dict[str, Dict[str, Any]], wpd_grade: str):
        """
        Add phase to appropriate hierarchy level (flat for L1, nested for L2/L3).
        
        Args:
            phase: Phase dictionary to add
            phases: Top-level phases list
            hierarchy: Hierarchy tracking dictionary
            wpd_grade: WPD grade level
        """
        phase_number = phase["phase_number"]
        parts = phase_number.split('.')
        
        # Store in hierarchy tracker
        hierarchy[phase_number] = phase
        
        if len(parts) == 1:
            # Top-level phase (e.g., "5" or "1") - always add to phases
            phases.append(phase)
        elif len(parts) == 2:
            # Second-level phase (e.g., "5.1") - nest under parent if L2/L3
            parent_number = parts[0]
            if parent_number in hierarchy:
                # Add as subphase to parent
                hierarchy[parent_number]["subphases"].append(phase)
            else:
                # Parent not found, add as top-level (fallback)
                phases.append(phase)
        elif len(parts) >= 3:
            # Third-level or deeper (e.g., "5.1.2") - nest under parent if L3
            parent_number = '.'.join(parts[:-1])  # e.g., "5.1" from "5.1.2"
            if parent_number in hierarchy:
                # Add as subphase to parent
                hierarchy[parent_number]["subphases"].append(phase)
            else:
                # Parent not found, add as top-level (fallback)
                phases.append(phase)
    
    def _parse_legacy_milestones(self, plan_content: str) -> List[Dict[str, Any]]:
        """Parse legacy milestone format for backward compatibility"""
        milestones = []
        lines = plan_content.split("\n")
        
        in_milestones_section = False
        for i, line in enumerate(lines):
            if "## 🎯 Milestones" in line:
                in_milestones_section = True
                continue
            
            if in_milestones_section:
                if line.startswith("## "):
                    break
                
                if line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
                    is_done = "[x]" in line
                    milestone_text = line.replace("- [ ]", "").replace("- [x]", "").strip()
                    milestones.append({
                        "title": milestone_text,
                        "completed": is_done,
                        "order": len(milestones) + 1,
                        "checklist": [{"text": milestone_text, "completed": is_done}]
                    })
        
        return milestones
    
    def execute_phase(self, phase: Dict[str, Any], parent_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute individual phase from WPD with support for nested subphases.
        
        Args:
            phase: Phase dictionary containing title, checklist, subphases, etc.
            parent_result: Parent phase result for nested execution tracking
            
        Returns:
            Dict containing execution results for the phase and all subphases
        """
        result = {
            "phase": phase["title"],
            "phase_number": phase.get("phase_number", ""),
            "order": phase["order"],
            "status": "IN_PROGRESS",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "output": "",
            "errors": [],
            "checklist_results": [],
            "subphase_results": []  # For nested phases in L2/L3
        }
        
        try:
            # Execute based on checklist items
            checklist = phase.get("checklist", [])
            if checklist:
                for item in checklist:
                    if not item.get("completed", False):
                        # Execute actual task (currently simulated)
                        # TODO: Replace with actual task execution logic
                        item_result = {
                            "text": item["text"],
                            "status": "COMPLETED",
                            "output": f"Executed: {item['text']}"
                        }
                        result["checklist_results"].append(item_result)
                
                result["output"] = f"Completed {len(checklist)} checklist items"
                result["status"] = "COMPLETED"
            else:
                # No checklist - mark as completed with generic message
                result["output"] = f"Phase '{phase['title']}' executed"
                result["status"] = "COMPLETED"
            
            # Execute nested subphases recursively (for L2/L3 documents)
            subphases = phase.get("subphases", [])
            if subphases:
                print(f"[Tier B] Executing {len(subphases)} subphases for {phase['title']}")
                for subphase in subphases:
                    subphase_result = self.execute_phase(subphase, result)
                    result["subphase_results"].append(subphase_result)
                    
                    # Update parent status based on subphase results
                    if subphase_result["status"] == "FAILED":
                        result["status"] = "PARTIALLY_COMPLETED"
                
                # Aggregate subphase statistics
                total_subphases = len(subphases)
                completed_subphases = sum(1 for sr in result["subphase_results"] 
                                        if sr["status"] in ["COMPLETED", "PARTIALLY_COMPLETED"])
                result["output"] += f"\nCompleted {completed_subphases}/{total_subphases} subphases"
            
            result["end_time"] = datetime.now(timezone.utc).isoformat()
        
        except Exception as e:
            result["status"] = "FAILED"
            result["errors"].append(str(e))
            result["end_time"] = datetime.now(timezone.utc).isoformat()
        
        return result
    
    def generate_prd_report(self, phases: List[Dict[str, Any]], 
                            results: List[Dict[str, Any]], 
                            wpd_source_path: str,
                            Part_N: str = "") -> str:
        """
        Generate PRD (Product Requirements Document) report using template format.
        
        Replaces basic generate_execution_report() with structured PRD generation.
        
        Args:
            phases: List of phase definitions
            results: List of execution results
            wpd_source_path: Source WPD document path
            Part_N: Step number (extracted from WPD filename if empty)
            
        Returns:
            str: Formatted PRD markdown content
        """
        # Extract step number from WPD filename if not provided
        if not Part_N:
            step_match = re.search(r'P(\d+)', wpd_source_path)
            if step_match:
                Part_N = step_match.group(1)
            else:
                Part_N = "XX"  # Fallback
        
        # Calculate statistics
        total_phases = len(phases)
        completed = sum(1 for r in results if r['status'] in ['COMPLETED', 'PARTIALLY_COMPLETED'])
        failed = sum(1 for r in results if r['status'] == 'FAILED')
        in_progress = sum(1 for r in results if r['status'] == 'IN_PROGRESS')
        success_rate = (completed / total_phases * 100) if total_phases > 0 else 0
        
        # Calculate total execution time
        start_times = [r.get('start_time') for r in results if r.get('start_time')]
        end_times = [r.get('end_time') for r in results if r.get('end_time')]
        
        total_duration = "N/A"
        if start_times and end_times:
            try:
                start = datetime.fromisoformat(min(start_times))
                end = datetime.fromisoformat(max(end_times))
                duration_sec = (end - start).total_seconds()
                total_duration = f"{duration_sec:.2f}s"
            except:
                pass
        
        # Generate PRD content
        prd_content = f"""# PRD-P{Part_N}: Execution Results Report

**Document Type**: PRD (Product Requirements Document)  
**Generated**: {datetime.now(timezone.utc).isoformat()}  
**Status**: {"✅ COMPLETED" if failed == 0 else "⚠️ PARTIALLY COMPLETED" if completed > 0 else "❌ FAILED"}  
**WPD Source**: `{wpd_source_path}`

---

## 📊 Executive Summary

This document reports the execution results of work plan P{Part_N}. The plan consisted of {total_phases} phase(s), with {completed} successfully completed, {failed} failed, and {in_progress} still in progress.

### Key Metrics

| Metric | Value |
|--------|-------|
| **Total Phases** | {total_phases} |
| **Completed** | {completed} ({success_rate:.1f}%) |
| **Failed** | {failed} |
| **In Progress** | {in_progress} |
| **Total Execution Time** | {total_duration} |
| **Success Rate** | {success_rate:.1f}% |

---

## 🎯 Phase Execution Results

"""
        # Add detailed phase results
        for i, result in enumerate(results, 1):
            status_emoji = {
                "COMPLETED": "✅",
                "PARTIALLY_COMPLETED": "⚠️",
                "FAILED": "❌",
                "IN_PROGRESS": "⏳"
            }.get(result["status"], "❓")
            
            prd_content += f"### {status_emoji} Phase {i}: {result['phase']}\n\n"
            prd_content += f"- **Status**: {result['status']}\n"
            prd_content += f"- **Phase Number**: {result.get('phase_number', 'N/A')}\n"
            prd_content += f"- **Start Time**: {result['start_time']}\n"
            
            if "end_time" in result:
                prd_content += f"- **End Time**: {result['end_time']}\n"
                # Calculate phase duration
                try:
                    start = datetime.fromisoformat(result['start_time'])
                    end = datetime.fromisoformat(result['end_time'])
                    duration = (end - start).total_seconds()
                    prd_content += f"- **Duration**: {duration:.2f}s\n"
                except:
                    pass
            
            if result['output']:
                prd_content += f"\n**Output**:\n```\n{result['output']}\n```\n"
            
            # Checklist results
            if result.get('checklist_results'):
                prd_content += f"\n**Checklist Items** ({len(result['checklist_results'])} items):\n"
                for item in result['checklist_results']:
                    status_icon = "✓" if item.get('status') == 'COMPLETED' else "✗"
                    prd_content += f"- {status_icon} {item['text']}\n"
            
            # Subphase results (for L2/L3 hierarchical execution)
            if result.get('subphase_results'):
                prd_content += f"\n**Subphases** ({len(result['subphase_results'])} subphases):\n"
                for subresult in result['subphase_results']:
                    sub_status_emoji = {
                        "COMPLETED": "✅",
                        "FAILED": "❌",
                        "IN_PROGRESS": "⏳"
                    }.get(subresult["status"], "❓")
                    prd_content += f"- {sub_status_emoji} {subresult['phase']}: {subresult['status']}\n"
            
            # Errors
            if result['errors']:
                prd_content += f"\n**Errors**:\n"
                for error in result['errors']:
                    prd_content += f"- ❌ {error}\n"
            
            prd_content += "\n---\n\n"
        
        # Add artifacts and references section
        prd_content += f"""## 📦 Generated Artifacts

- Execution Report: This document
- Source WPD: `{wpd_source_path}`
- Execution Timestamp: {datetime.now(timezone.utc).isoformat()}

---

## 📚 References

- **Parent WPD**: `{wpd_source_path}`
- **Execution Engine**: Tier B (B_Performing_Tasks.py)
- **Report Format**: PRD Template v1.0

---

## ✅ Completion Status

**Overall Status**: {"✅ All phases completed successfully" if failed == 0 and in_progress == 0 else "⚠️ Some phases incomplete or failed" if completed > 0 else "❌ Execution failed"}

**Next Steps**:
- Review failed phases (if any) and retry or modify plan
- Update parent WPD document with execution results
- Proceed to Tier E for document management and synchronization

---

*Generated by Tier B Task Execution Engine*  
*Timestamp: {datetime.now(timezone.utc).isoformat()}*
"""
        
        return prd_content
    
    def save_prd_report(self, prd_content: str, Part_N: str = "") -> str:
        """
        Save PRD report in standardized location: docs_2/prd/PRD-P[Part_N].md
        
        Args:
            prd_content: PRD markdown content
            Part_N: Step number for filename
            
        Returns:
            str: Path to saved PRD file
        """
        # Create prd directory if it doesn't exist
        prd_dir = Path(self.context.workspace_root) / "docs_2" / "prd"
        prd_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        if not Part_N:
            # Try to extract from wpd_source_path
            if self.state.wpd_source_path:
                step_match = re.search(r'P(\d+)', self.state.wpd_source_path)
                if step_match:
                    Part_N = step_match.group(1)
        
        if not Part_N:
            # Fallback to timestamp
            Part_N = f"EXEC_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        filename = f"PRD-P{Part_N}.md"
        filepath = prd_dir / filename
        
        # Write PRD content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(prd_content)
        
        print(f"[Tier B] PRD report saved: {filepath}")
        return str(filepath.relative_to(self.context.workspace_root))
    
    def generate_execution_report(self, phases: List[Dict[str, Any]], 
                                  results: List[Dict[str, Any]]) -> str:
        """
        Generate execution result report (legacy method for backward compatibility).
        
        Now delegates to generate_prd_report() for PRD template-based generation.
        
        Args:
            phases: List of phase definitions
            results: List of execution results
            
        Returns:
            str: Formatted markdown report
        """
        # Delegate to PRD generation
        wpd_source = self.state.wpd_source_path or "Unknown WPD"
        return self.generate_prd_report(phases, results, wpd_source)
    
    def save_execution_report(self, report: str) -> str:
        """
        실행 보고서 저장
        
        Args:
            report: Report content to save
            
        Returns:
            str: Path to saved report file
        """
        docs_path = Path(self.context.workspace_root) / "docs_2" / "execution_reports"
        docs_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"ER_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
        filepath = docs_path / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)
        
        return str(filepath)
    
    def execute(self) -> AgentState:
        """
        작업 계획 실행
        
        Refactored to use new dataclass hierarchy:
        - Uses local variables for timing instead of storing in tier state
        - Uses DocumentSources for execution tracking
        - Uses TierBState.to_payload() for serialization
        
        Returns:
            AgentState: Execution state with results in payload
        """
        # Local timing variables (not stored in tier state)
        start_time = datetime.now(timezone.utc)
        
        try:
            # 입력 검증
            if not self.validate_user_input():
                return AgentState.create_failure(
                    tier=self.tier,
                    error_msg="User input does not match Tier B (Perform Work Plan) keywords",
                    logic_summary="Input validation failed"
                )
            
            # 작업 계획 로드
            plan_content = self.load_work_plan()
            if not plan_content:
                # Preserve wpd metadata when failing
                failure_state = AgentState.create_failure(
                    tier=self.tier,
                    error_msg="No work plan found. Please create a work plan first using Tier A.",
                    logic_summary="Work plan not found"
                )
                failure_state.wpd_source_path = self.state.wpd_source_path
                failure_state.wpd_grade = self.state.wpd_grade
                return failure_state
            
            # Parse phases from WPD with grade-aware hierarchical parsing
            phases = self.parse_phases(plan_content, self.state.wpd_grade)
            if not phases:
                return AgentState.create_failure(
                    tier=self.tier,
                    error_msg="No phases found in work plan. Expected '## 🔧 Execution Plan' section.",
                    logic_summary="Invalid plan structure"
                )
            
            # Update execution tracking in DocumentSources
            self.tier_state.sources.total_phases = len(phases)
            self.tier_state.current_phase = ""
            
            # Execute each phase
            results = []
            for phase in phases:
                if not phase["completed"]:
                    self.tier_state.current_phase = phase["title"]
                    result = self.execute_phase(phase)
                    results.append(result)
                    
                    # Update counts in DocumentSources
                    if result["status"] == "COMPLETED":
                        self.tier_state.sources.completed_phases += 1
                    elif result["status"] == "FAILED":
                        self.tier_state.sources.failed_phases += 1
            
            # Store phase results in DocumentSources
            self.tier_state.sources.phase_results = results
            
            # Generate PRD report using template and save in standardized location
            prd_content = self.generate_prd_report(phases, results, self.state.wpd_source_path or "")
            
            # Extract Part_N for PRD filename
            Part_N = ""
            if self.state.wpd_source_path:
                step_match = re.search(r'P(\d+)', self.state.wpd_source_path)
                if step_match:
                    Part_N = step_match.group(1)
            
            prd_path = self.save_prd_report(prd_content, Part_N)
            self.tier_state.sources.prd_path = prd_path
            
            # Also save in execution_reports for backward compatibility
            report_path = self.save_execution_report(prd_content)
            self.tier_state.sources.execution_report_path = report_path
            
            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Store timing in tier state for backward compatibility
            self.tier_state.start_time = start_time.isoformat()
            self.tier_state.end_time = end_time.isoformat()
            self.tier_state.total_duration_ms = duration_ms
            
            # Success state return
            completed_count = self.tier_state.sources.completed_phases
            total_count = self.tier_state.sources.total_phases
            prd_filename = Path(prd_path).name if prd_path else "PRD report"
            
            state = AgentState.create_success(
                tier=self.tier,
                logic_summary=f"Successfully executed {completed_count}/{total_count} phases. "
                             f"PRD report saved at {prd_filename}",
                payload=self.tier_state.to_payload(),  # Use tier state serialization
                next_node="E"  # Next: E (Document Management) for PRD synchronization
            )
            
            # Set execution time and wpd metadata from current state
            state.execution_time_ms = duration_ms
            state.wpd_source_path = self.state.wpd_source_path
            state.wpd_grade = self.state.wpd_grade
            
            # Add decision trace
            state.decision_trace.append({
                "plan_loaded": True,
                "phases_count": len(phases),
                "auto_proceed": True,
                "reason": "All phases executed. Ready for documentation or plan modification."
            })
            
            return state
        
        except Exception as e:
            return AgentState.create_failure(
                tier=self.tier,
                error_msg=f"Exception during plan execution: {str(e)}",
                logic_summary=f"Error: {str(e)}"
            )


def main(user_input: str, workspace_root: str = ".", previous_payload: Optional[Dict[str, Any]] = None) -> AgentState:
    """
    Tier B 메인 진입점
    
    Refactored to use new dataclass hierarchy:
    - Uses TaskContext instead of passing individual parameters
    - Converts previous_payload to AgentState for context.previous_state
    - Simplified parameter handling
    
    Args:
        user_input: 사용자 입력 텍스트
        workspace_root: 작업 공간 루트 경로
        previous_payload: 이전 tier의 payload (chaining용, backward compatibility)
    
    Returns:
        AgentState: 실행 결과 및 다음 단계 정보
    """
    # Convert previous_payload to AgentState if provided
    prev_state_obj = None
    if previous_payload:
        prev_state_obj = AgentState(
            tier=previous_payload.get('tier', ''),
            status=previous_payload.get('status', 'FAILED'),
            logic_summary=previous_payload.get('logic_summary', ''),
            next_node=previous_payload.get('next_node'),
            payload=previous_payload.get('payload', {}),
            execution_time_ms=previous_payload.get('execution_time_ms', 0),
            errors=previous_payload.get('errors', []),
            warnings=previous_payload.get('warnings', []),
            timestamp=previous_payload.get('timestamp', ''),
            decision_trace=previous_payload.get('decision_trace', []),
            wpd_grade=previous_payload.get('wpd_grade', 'L1'),
            wpd_source_path=previous_payload.get('wpd_source_path', '')
        )

    # Create TaskContext
    context = TaskContext(
        user_input=user_input,
        current_tier="B",
        workspace_root=workspace_root,
        previous_state=prev_state_obj
    )
    
    # Execute tier
    engine = TaskExecutionEngine(context)
    state = engine.execute()
    
    # Emit result to stdout
    state.emit()
    
    return state


if __name__ == "__main__":
    # 테스트 코드
    test_input = "Perform work plan"
    
    main(test_input, workspace_root="c:\\Users\\rhkrt\\Documents\\GitHub\\turbo-system")
