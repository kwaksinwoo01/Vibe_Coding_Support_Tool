"""
A_Working_Document_Progress.py

Tier A: Work Plan Creation Module

Implements the complete WPD (Work Plan Document) creation workflow with hierarchical
document structure (L0 → L1 → L2 → L3) based on natural language user input.

Triggers:
- "Create a work plan"
- "Create WPD"
- "작업 계획 생성"


Workflow:
1. Validate NEXT_TASK document existence and WPD_grade
2. Determine if user specified a plan document or use default
3. Create hierarchical WPD documents based on grade level (L1→L2→L3)
4. Validate created documents
5. Auto-route to Tier B for execution

Output: AgentState with created WPD documents and next_node="B"
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import re
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models.core import AgentState, TierAState, WPDDocument, DocumentMetadata, DocumentHierarchy
from models.document_format import render_wpd_template, validate_template_structure

# WORKSPACE_ROOT is now passed via constructor parameter to avoid module-level constants


@dataclass(frozen=True)
class GradeInfo:
    """
    Immutable dataclass for WPD grade validation information.
    
    Follows SRP: Represents only grade validation data.
    
    Attributes:
        grade: WPD grade level (L0, L1, L2, L3)
        path: Path to the document
        exists: Whether the document exists
        has_grade_field: Whether WPD_grade field is present in document
    """
    grade: str = "L0"
    path: str = ""
    exists: bool = False
    has_grade_field: bool = False


@dataclass(frozen=True)
class ConflictResolution:
    """
    Immutable dataclass for document conflict resolution.
    
    Follows SRP: Represents only conflict detection and resolution data.
    
    Attributes:
        has_conflict: Whether a conflict was detected
        target_document: Path to the document to merge into (if conflict exists)
        merge_strategy: Strategy for merging content ("append", "insert", "replace")
    """
    has_conflict: bool = False
    target_document: Optional[Path] = None
    merge_strategy: str = "append"


def detect_grade_from_path(path: str) -> str:
    """Detect WPD grade from file path pattern
    
    Args:
        path: File path to analyze
        
    Returns:
        WPD grade: "L0", "L1", "L2", or "L3"
    """
    if re.search(r'NextTask.*\.md$', path):
        return "L0"
    elif re.search(r'P\d+/P\d+-[^/]+\.md$', path):
        return "L1"
    elif re.search(r'P\d+/P\d+\.\d+-[^/]+\.md$', path):
        return "L2"
    elif re.search(r'P\d+/P\d+\.\d+\.\d+-[^/]+\.md$', path):
        return "L3"
    return "L0"  # Default


class WorkPlanCreationEngine:
    """
    Main engine for creating hierarchical work plan documents.
    
    Architecture follows SRP with nested classes:
    - Validator: Document and field validation
    - Creator: WPD document creation (with L1/L2/L3 sub-creators)
    - Verifier: Template structure verification with retry logic
    """
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.state = AgentState(tier="A", status="PENDING")  # Parent state
        self.tier_state = TierAState()  # Tier-specific state
        self.tier = "A"
        self.execution_log: List[str] = []  # Local log for building
        self.created_documents: List[str] = []  # Track created docs

    def log(self, message: str):
        """Add message to execution log in state"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.execution_log.append(log_msg)
        print(log_msg)
        self.state.execution_log.append(log_msg)
        print(log_msg)
    
    # ========================================================================
    # Nested Classes for Single Responsibility Principle
    # ========================================================================
    
    class Validator:
        """Single Responsibility: Document and field validation"""
        
        @staticmethod
        def read_wpd_grade(file_path: Path) -> Optional[str]:
            """Read WPD_grade field from document"""
            try:
                if not file_path.exists():
                    return None
                
                content = file_path.read_text(encoding='utf-8')
                
                # Look for **WPD_grade**: L[0-3] pattern
                match = re.search(r'\*\*WPD_grade\*\*:\s*(L[0-3])', content)
                if match:
                    return match.group(1)
                
                return None
            except Exception as e:
                print(f"Error reading WPD_grade from {file_path}: {e}")
                return None
        
        @staticmethod
        def validate_main_document(state: TierAState, workspace_root: Path) -> Tuple[bool, GradeInfo]:
            """
            Step 1.0: Validate main progress document (main_document_path)
            
            Args:
                state: TierAState with main_document_path to validate
                workspace_root: Workspace root path
            
            Returns:
                Tuple of (is_valid, GradeInfo with validation results)
            """
            print(f"Step 1.0: Validating main document: {state.main_document_path}")
            
            main_doc_path = workspace_root / state.main_document_path
            
            if not main_doc_path.exists():
                print(f"ERROR: Main document {state.main_document_path} does not exist")
                # Try default only if not already using default
                if state.main_document_path != "docs_2/NextTask-2.md":
                    print(f"Setting default to: docs_2/NextTask-2.md")
                    state.main_document_path = "docs_2/NextTask-2.md"
                    return WorkPlanCreationEngine.Validator.validate_main_document(state, workspace_root)
                else:
                    # Default also doesn't exist - just return False
                    print(f"WARNING: Default main document also does not exist")
                    grade_info = GradeInfo(
                        grade="L0",
                        path=str(main_doc_path),
                        exists=False,
                        has_grade_field=False
                    )
                    return False, grade_info
            
            # Read WPD_grade
            wpd_grade = WorkPlanCreationEngine.Validator.read_wpd_grade(main_doc_path)
            
            # Create GradeInfo with final values (immutable)
            if wpd_grade:
                grade_info = GradeInfo(
                    grade=wpd_grade,
                    path=str(main_doc_path),
                    exists=True,
                    has_grade_field=True
                )
                print(f"Main document has WPD_grade: {wpd_grade}")
            else:
                grade_info = GradeInfo(
                    grade="L0",
                    path=str(main_doc_path),
                    exists=True,
                    has_grade_field=False
                )
                print(f"Main document lacks WPD_grade field, assuming L0")
            
            return True, grade_info
        
        @staticmethod
        def check_three_tier_documentation(doc_path: Path, Part_N: str) -> Tuple[bool, Optional[Dict[str, str]]]:
            """
            Step 1.3.0: Check if Three-Tier Documentation section exists
            Returns: (exists, doc_paths)
            """
            try:
                content = doc_path.read_text(encoding='utf-8')
                
                # Look for Three-Tier Documentation section
                three_tier_match = re.search(
                    r'### Three-Tier Documentation\s+'
                    r'1\.\s+\*\*WPD\*\*\s+\(`([^`]+)`\)',
                    content
                )
                
                if three_tier_match:
                    wpd_path = three_tier_match.group(1)
                    print(f"Found Three-Tier Documentation: WPD={wpd_path}")
                    return True, {"wpd": wpd_path}
                
                return False, None
                
            except Exception as e:
                print(f"Error checking Three-Tier Documentation: {e}")
                return False, None
        
        @staticmethod
        def extract_step_info_from_main_doc(main_doc_path: Path) -> Tuple[Optional[str], Optional[str]]:
            """Extract step number and task title from main document"""
            try:
                content = main_doc_path.read_text(encoding='utf-8')
                
                # Look for pattern: ## 🟢 step [Part_N]: [Task Title]
                match = re.search(r'##\s+🟢\s+step\s+(\d+):\s+([^\n]+)', content)
                if match:
                    Part_N = match.group(1)
                    task_title = match.group(2).strip()
                    print(f"Extracted from main doc: step {Part_N}, title '{task_title}'")
                    return Part_N, task_title
                
                return None, None
            except Exception as e:
                print(f"Error extracting step info: {e}")
                return None, None
    
    class Verifier:
        """Single Responsibility: Template structure verification with retry"""
        
        @staticmethod
        def validate_template(content: str, grade: str) -> List[str]:
            """
            Validate template structure using template_validators module
            Returns list of errors (empty if valid)
            """
            return validate_template_structure(content, grade)
        
        @staticmethod
        def verify_with_retry(file_path: Path, grade: str, max_retries: int = 3) -> Tuple[bool, List[str]]:
            """
            Steps 3.2.3, 3.4.3, 3.6.3: Validate wpd_template with retry
            Steps 3.2.4, 3.4.4, 3.6.4: Automatic retry on validation failure
            
            Returns: (is_valid, error_list)
            """
            if not file_path.exists():
                return False, [f"File does not exist: {file_path}"]
            
            content = file_path.read_text(encoding='utf-8')
            
            for attempt in range(1, max_retries + 1):
                errors = WorkPlanCreationEngine.Verifier.validate_template(content, grade)
                
                if not errors:
                    print(f"✅ Template validation passed for {grade}: {file_path.name}")
                    return True, []
                
                print(f"❌ Template validation failed (attempt {attempt}/{max_retries})")
                for error in errors:
                    print(f"  - {error}")
                
                if attempt < max_retries:
                    print(f"🔄 Retrying validation...")
                    # In real implementation, could attempt to fix issues here
                    # For now, just retry with same content
            
            return False, errors
    
    class PhaseExtractor:
        """Single Responsibility: Extract phases and subphases from WPD documents"""
        
        @staticmethod
        def extract_phases_from_l1(l1_doc_path: Path) -> List[Dict[str, str]]:
            """
            Extract Phase sections from L1 document (Step 3.3.0, 3.3.1)
            
            Pattern: ### Phase [Part_N].[Phase_N]: [Phase Title]
            
            Returns:
                List of dicts with 'phase_n', 'phase_title', 'content'
            """
            if not l1_doc_path.exists():
                return []
            
            content = l1_doc_path.read_text(encoding='utf-8')
            phases = []
            
            # Find all phase sections
            # Pattern: ### Phase [Part_N].[Phase_N]: [Phase Title]
            phase_pattern = r'###\s+Phase\s+\d+\.(\d+):\s+([^\n]+)'
            matches = re.finditer(phase_pattern, content)
            
            for match in matches:
                phase_n = match.group(1)
                phase_title = match.group(2).strip()
                
                # Extract content between this phase and next phase (or end)
                start_pos = match.end()
                next_match = re.search(r'###\s+Phase\s+\d+\.\d+:', content[start_pos:])
                if next_match:
                    end_pos = start_pos + next_match.start()
                else:
                    # Last phase, go until next major section or end
                    next_section = re.search(r'\n##\s+', content[start_pos:])
                    end_pos = start_pos + next_section.start() if next_section else len(content)
                
                phase_content = content[start_pos:end_pos].strip()
                
                phases.append({
                    'phase_n': phase_n,
                    'phase_title': phase_title,
                    'content': phase_content
                })
            
            print(f"Extracted {len(phases)} phases from L1: {l1_doc_path.name}")
            return phases
        
        @staticmethod
        def extract_subphases_from_l2(l2_doc_path: Path) -> List[Dict[str, Any]]:
            """
            Extract Subphase sections from L2 document (Step 3.5)
            
            Pattern: ### Subphase [Part_N].[Phase_N].[Subphase_N]: [Subphase Title]
            
            Returns:
                List of dicts with 'subphase_n', 'subphase_title', 'content', 'line_count'
            """
            if not l2_doc_path.exists():
                return []
            
            content = l2_doc_path.read_text(encoding='utf-8')
            subphases = []
            
            # Pattern: ### Subphase [Part_N].[Phase_N].[Subphase_N]: [Subphase Title]
            subphase_pattern = r'###\s+Subphase\s+\d+\.\d+\.(\d+):\s+([^\n]+)'
            matches = re.finditer(subphase_pattern, content)
            
            for match in matches:
                subphase_n = match.group(1)
                subphase_title = match.group(2).strip()
                
                # Extract content between this subphase and next subphase (or end)
                start_pos = match.end()
                next_match = re.search(r'###\s+Subphase\s+\d+\.\d+\.\d+:', content[start_pos:])
                if next_match:
                    end_pos = start_pos + next_match.start()
                else:
                    # Last subphase, go until next major section or end
                    next_section = re.search(r'\n##\s+', content[start_pos:])
                    end_pos = start_pos + next_section.start() if next_section else len(content)
                
                subphase_content = content[start_pos:end_pos].strip()
                line_count = len(subphase_content.split('\n'))
                
                subphases.append({
                    'subphase_n': subphase_n,
                    'subphase_title': subphase_title,
                    'content': subphase_content,
                    'line_count': line_count
                })
            
            print(f"Extracted {len(subphases)} subphases from L2: {l2_doc_path.name}")
            return subphases
        
        @staticmethod
        def check_300_line_threshold(subphases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """
            Check if any subphases exceed 300 lines (Step 3.5.1)
            
            Returns:
                List of subphases that exceed 300 lines
            """
            exceeding = [sp for sp in subphases if sp['line_count'] > 300]
            
            if exceeding:
                print(f"Found {len(exceeding)} subphases exceeding 300 lines:")
                for sp in exceeding:
                    print(f"  - Subphase {sp['subphase_n']}: {sp['line_count']} lines")
            
            return exceeding
    
    class AutoRoutingEngine:
        """Single Responsibility: Automatic routing and conflict resolution for document creation"""
        
        def __init__(self, workspace_root: Path):
            self.workspace_root = workspace_root
        
        def scan_existing_documents(self, keywords: List[str]) -> List[Path]:
            """Scan docs_2/ directory for documents containing specified keywords"""
            docs_dir = self.workspace_root / "docs_2"
            matching_docs = []
            
            if not docs_dir.exists():
                return matching_docs
            
            for md_file in docs_dir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding='utf-8')
                    if any(keyword.lower() in content.lower() for keyword in keywords):
                        matching_docs.append(md_file)
                except Exception:
                    continue
            
            return matching_docs
        
        def detect_conflicts(self, user_input: str) -> ConflictResolution:
            """Analyze user input and detect potential document conflicts"""
            # Extract keywords from user input
            keywords = self._extract_keywords(user_input)
            
            # Scan for existing documents
            existing_docs = self.scan_existing_documents(keywords)
            
            if not existing_docs:
                return ConflictResolution()
            
            # Find the most relevant document (prioritize P2 documents)
            target_doc = self._select_target_document(existing_docs, user_input)
            
            if target_doc:
                return ConflictResolution(
                    has_conflict=True,
                    target_document=target_doc,
                    merge_strategy=self._determine_merge_strategy(user_input)
                )
            
            return ConflictResolution()
        
        def merge_content(self, target_doc: Path, new_content: str) -> bool:
            """Merge new content into existing document"""
            try:
                current_content = target_doc.read_text(encoding='utf-8')
                merged_content = self._perform_merge(current_content, new_content)
                target_doc.write_text(merged_content, encoding='utf-8')
                return True
            except Exception as e:
                print(f"Error merging content into {target_doc}: {e}")
                return False
        
        def _extract_keywords(self, user_input: str) -> List[str]:
            """
            Extract relevant keywords from user input for document matching.
            
            Uses a combination of:
            1. Predefined key phrases (high-priority matches)
            2. N-gram extraction (2-4 word phrases from input)
            3. Part number patterns (P2.1, P2.1.01, etc.)
            
            Returns:
                List of extracted keywords/phrases for matching
            """
            keywords = []
            user_lower = user_input.lower()
            
            # 1. Predefined high-priority phrases
            key_phrases = [
                "Client Dropbox Event Polling",
                "event polling",
                "dropbox polling",
                "client event",
                "SRP refactoring",
                "event transformer",
                "sync reconciler",
            ]
            
            # Add matching predefined phrases
            for phrase in key_phrases:
                if phrase.lower() in user_lower:
                    keywords.append(phrase)
            
            # 2. Extract Part number patterns (e.g., P2.1, P2.1.01, P5, etc.)
            import re
            part_patterns = re.findall(r'P\d+(?:\.\d+)*', user_input, re.IGNORECASE)
            keywords.extend(part_patterns)
            
            # 3. Extract significant word sequences (2-4 word n-grams)
            # Skip common words
            stop_words = {'a', 'an', 'the', 'for', 'to', 'of', 'in', 'on', 'at', 'by', 'with', 'from', 'and', 'or', 'but'}
            words = user_input.lower().split()
            
            # Filter out stop words and very short words
            meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
            
            # Generate 2-grams and 3-grams
            for i in range(len(meaningful_words) - 1):
                bigram = ' '.join(meaningful_words[i:i+2])
                if len(bigram) > 5:  # Avoid very short n-grams
                    keywords.append(bigram)
                
                if i < len(meaningful_words) - 2:
                    trigram = ' '.join(meaningful_words[i:i+3])
                    if len(trigram) > 8:  # Avoid very short n-grams
                        keywords.append(trigram)
            
            # 4. Add individual meaningful words (fallback)
            keywords.extend(meaningful_words)
            
            # Deduplicate while preserving order
            seen = set()
            unique_keywords = []
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower not in seen:
                    seen.add(kw_lower)
                    unique_keywords.append(kw)
            
            return unique_keywords
        
        def _select_target_document(self, docs: List[Path], user_input: str) -> Optional[Path]:
            """
            Select the most appropriate document for merging using scoring system.
            
            Scoring criteria:
            1. Priority by document level: P2.1.01 > P2.1 > P2
            2. Exact filename match with keywords
            3. Content relevance to user input
            
            **Minimum Score Threshold**: 150 points required to trigger merge
            (Prevents over-aggressive merging)
            
            Returns:
                Path to the best matching document, or None if no good match
            """
            if not docs:
                return None
            
            # Extract keywords for relevance scoring
            keywords = self._extract_keywords(user_input)
            user_lower = user_input.lower()
            
            # Score each document
            doc_scores = []
            for doc in docs:
                score = 0
                doc_name = doc.name.lower()
                
                # 1. Priority scoring based on document level
                if "P2.1.01" in doc.name or "P2.1.1" in doc.name:
                    score += 100  # Highest priority for L3 documents
                elif re.search(r'P\d+\.\d+', doc.name):
                    score += 50   # Medium priority for L2 documents
                elif re.search(r'P\d+', doc.name):
                    score += 25   # Lower priority for L1 documents
                
                # 2. Filename keyword matching
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in doc_name:
                        # Longer keywords get higher scores
                        score += len(keyword) * 2
                
                # 3. Specific pattern matching (high value)
                if "client-event-polling" in doc_name:
                    score += 200
                if "event-polling" in doc_name:
                    score += 100
                if "polling" in doc_name and "event" in user_lower:
                    score += 50
                
                # 4. P2 documents get bonus (from requirements)
                if doc.name.startswith("P2"):
                    score += 30
                
                doc_scores.append((score, doc))
            
            # Sort by score (highest first)
            doc_scores.sort(reverse=True, key=lambda x: x[0])
            
            # **Minimum score threshold**: Require at least 150 points
            # This prevents over-aggressive merging for weak matches
            MIN_SCORE_THRESHOLD = 150
            
            # Return highest scoring document if score > threshold
            if doc_scores and doc_scores[0][0] >= MIN_SCORE_THRESHOLD:
                return doc_scores[0][1]
            
            return None
        
        def _determine_merge_strategy(self, user_input: str) -> str:
            """Determine the appropriate merge strategy based on user input"""
            if "add" in user_input.lower() or "append" in user_input.lower():
                return "append"
            elif "insert" in user_input.lower():
                return "insert"
            else:
                return "append"
        
        def _perform_merge(self, current_content: str, new_content: str) -> str:
            """Perform the actual content merging"""
            # Simple append strategy - add new content at the end
            return current_content + "\n\n" + new_content
    
    class Creator:
        """Single Responsibility: WPD document creation with nested grade-specific creators"""
        
        class L1Creator:
            """Single Responsibility: L1 WPD creation"""
            
            @staticmethod
            def create(state: AgentState, tier_state: TierAState, workspace_root: Path, Part_N: str, task_title: str, 
                      parent_doc: Path, description: str = "") -> Optional[Path]:
                """
                Step 3.2: Create L1 WPD document using wpd_1_template
                
                Args:
                    state: AgentState containing common fields (wpd_grade, execution_log, etc.)
                    tier_state: TierAState containing tier-specific metadata and hierarchy
                    workspace_root: Workspace root path
                    Part_N: Step number (e.g., "5")
                    task_title: Task title
                    parent_doc: Parent document path
                    description: Optional description
                
                Returns:
                    Path to created WPD document or None on failure
                """
                print(f"Step 3.2: Creating L1 WPD document for step {Part_N}: {task_title}")
                
                # Generate path: docs_2/P[Part_N]/P[Part_N]-[Task Title].md
                wpd_dir = workspace_root / "docs_2" / f"P{Part_N}"
                wpd_dir.mkdir(parents=True, exist_ok=True)
                
                wpd_filename = f"P{Part_N}-{task_title}.md"
                wpd_path = wpd_dir / wpd_filename
                
                # Update state metadata for template rendering
                state.wpd_grade = "L1"
                tier_state.metadata.Part_N = Part_N
                tier_state.metadata.document_title = task_title
                tier_state.metadata.document_type = "WPD"
                tier_state.hierarchy.parent_document = str(parent_doc.relative_to(workspace_root))
                
                # Use wpd_1_template for content generation (pass tier_state, not state)
                template_content = render_wpd_template("L1", tier_state)
                
                # Add description to content if provided
                if description:
                    template_content += f"\n## Description\n\n{description}\n"
                
                # Write to file
                wpd_path.write_text(template_content, encoding='utf-8')
                print(f"✅ Created L1 WPD: {wpd_path.relative_to(workspace_root)}")
                
                # Step 3.2.3: Validate template
                is_valid, errors = WorkPlanCreationEngine.Verifier.verify_with_retry(wpd_path, "L1")
                tier_state.validation_results[str(wpd_path)] = is_valid
                
                if is_valid:
                    tier_state.created_documents.append(str(wpd_path.relative_to(workspace_root)))
                    return wpd_path
                else:
                    print(f"⚠️ Validation failed but document created: {wpd_path.name}")
                    tier_state.created_documents.append(str(wpd_path.relative_to(workspace_root)))
                    return wpd_path
        
        class L2Creator:
            """Single Responsibility: L2 WPD creation"""
            
            @staticmethod
            def create(state: AgentState, tier_state: TierAState, workspace_root: Path, parent_wpd_path: Path) -> Optional[Path]:
                """
                Step 3.4: Create L2 WPD document using wpd_2_template
                
                Args:
                    state: AgentState containing common fields (wpd_grade, execution_log, etc.)
                    tier_state: TierAState containing tier-specific metadata and hierarchy
                    workspace_root: Workspace root path
                    parent_wpd_path: Parent L1 WPD document path
                
                Returns:
                    Path to created L2 WPD document or None on failure
                """
                print(f"Step 3.4: Creating L2 WPD document from parent: {parent_wpd_path.name}")
                
                # Extract metadata from parent L1 document
                parent_content = parent_wpd_path.read_text(encoding='utf-8')
                
                # Extract Part_N and phase info
                # Pattern: docs_2/P[Part_N]/P[Part_N]-[Task Title].md
                step_match = re.search(r'P(\d+)-([^.]+)\.md$', parent_wpd_path.name)
                if not step_match:
                    print(f"ERROR: Cannot extract step info from {parent_wpd_path.name}")
                    return None
                
                Part_N = step_match.group(1)
                task_title = step_match.group(2)
                
                # Generate L2 path: docs_2/P[Part_N]/P[Part_N].[Phase_N]-[Phase Title].md
                # For now, use Phase_N=1
                phase_n = "1"
                phase_title = f"{task_title}-Phase{phase_n}"
                
                wpd_filename = f"P{Part_N}.{phase_n}-{phase_title}.md"
                wpd_path = parent_wpd_path.parent / wpd_filename
                
                # Update state metadata (use tier_state, not separate objects)
                state.wpd_grade = "L2"
                tier_state.metadata.Part_N = Part_N
                tier_state.metadata.document_title = phase_title
                tier_state.metadata.document_type = "WPD"
                tier_state.hierarchy.parent_document = str(parent_wpd_path.relative_to(workspace_root))
                
                # Use wpd_2_template for content generation (pass tier_state, not state)
                template_content = render_wpd_template("L2", tier_state)
                
                # Write to file
                wpd_path.write_text(template_content, encoding='utf-8')
                print(f"✅ Created L2 WPD: {wpd_path.relative_to(workspace_root)}")
                
                # Step 3.4.3: Validate template
                is_valid, errors = WorkPlanCreationEngine.Verifier.verify_with_retry(wpd_path, "L2")
                tier_state.validation_results[str(wpd_path)] = is_valid
                
                if is_valid:
                    tier_state.created_documents.append(str(wpd_path.relative_to(workspace_root)))
                    return wpd_path
                else:
                    print(f"⚠️ Validation failed but document created: {wpd_path.name}")
                    tier_state.created_documents.append(str(wpd_path.relative_to(workspace_root)))
                    return wpd_path
            
            @staticmethod
            def create_from_phase(state: AgentState, tier_state: TierAState, workspace_root: Path, 
                                 parent_wpd_path: Path, phase_info: Dict[str, str]) -> Optional[Path]:
                """
                Step 3.4: Create L2 WPD document for a specific phase from L1
                
                Args:
                    state: AgentState
                    tier_state: TierAState
                    workspace_root: Workspace root path
                    parent_wpd_path: Parent L1 WPD document path
                    phase_info: Dict with 'phase_n', 'phase_title', 'content'
                
                Returns:
                    Path to created L2 WPD document or None on failure
                """
                print(f"Step 3.4: Creating L2 for Phase {phase_info['phase_n']}: {phase_info['phase_title']}")
                
                # Extract Part_N from parent path
                step_match = re.search(r'P(\d+)-', parent_wpd_path.name)
                if not step_match:
                    print(f"ERROR: Cannot extract step from {parent_wpd_path.name}")
                    return None
                
                Part_N = step_match.group(1)
                phase_n = phase_info['phase_n']
                phase_title = phase_info['phase_title']
                
                # Generate L2 path: docs_2/P[Part_N]/P[Part_N].[Phase_N]-[Phase Title].md
                wpd_filename = f"P{Part_N}.{phase_n}-{phase_title}.md"
                wpd_path = parent_wpd_path.parent / wpd_filename
                
                # Update state metadata
                state.wpd_grade = "L2"
                tier_state.metadata.Part_N = Part_N
                tier_state.metadata.document_title = phase_title
                tier_state.metadata.document_type = "WPD"
                tier_state.hierarchy.parent_document = str(parent_wpd_path.relative_to(workspace_root))
                
                # Use wpd_2_template for content generation
                template_content = render_wpd_template("L2", tier_state)
                
                # Inject phase content into template
                phase_content_section = f"\n### Phase {Part_N}.{phase_n}: {phase_title}\n\n{phase_info['content']}\n"
                template_content += phase_content_section
                
                # Write to file
                wpd_path.write_text(template_content, encoding='utf-8')
                print(f"✅ Created L2 WPD: {wpd_path.relative_to(workspace_root)}")
                
                # Step 3.4.3: Validate template
                is_valid, errors = WorkPlanCreationEngine.Verifier.verify_with_retry(wpd_path, "L2")
                tier_state.validation_results[str(wpd_path)] = is_valid
                
                if is_valid:
                    tier_state.created_documents.append(str(wpd_path.relative_to(workspace_root)))
                    return wpd_path
                else:
                    print(f"⚠️ Validation failed but document created: {wpd_path.name}")
                    tier_state.created_documents.append(str(wpd_path.relative_to(workspace_root)))
                    return wpd_path

        
        class L3Creator:
            """Single Responsibility: L3 WPD creation"""
            
            @staticmethod
            def create(state: AgentState, tier_state: TierAState, workspace_root: Path, parent_wpd_path: Path) -> Optional[Path]:
                """
                Step 3.6: Create L3 WPD document using wpd_3_template
                
                Args:
                    state: AgentState containing common fields (wpd_grade, execution_log, etc.)
                    tier_state: TierAState containing tier-specific metadata and hierarchy
                    workspace_root: Workspace root path
                    parent_wpd_path: Parent L2 WPD document path
                
                Returns:
                    Path to created L3 WPD document or None on failure
                """
                print(f"Step 3.6: Creating L3 WPD document from parent: {parent_wpd_path.name}")
                
                # Extract metadata from parent L2 document
                # Pattern: docs_2/P[Part_N]/P[Part_N].[Phase_N]-[Phase Title].md
                step_phase_match = re.search(r'P(\d+)\.(\d+)-([^.]+)\.md$', parent_wpd_path.name)
                if not step_phase_match:
                    print(f"ERROR: Cannot extract step/phase info from {parent_wpd_path.name}")
                    return None
                
                Part_N = step_phase_match.group(1)
                phase_n = step_phase_match.group(2)
                phase_title = step_phase_match.group(3)
                
                # Generate L3 path: docs_2/P[Part_N]/P[Part_N].[Phase_N].[Subphase_N]-[Subphase Title].md
                subphase_n = "1"
                subphase_title = f"{phase_title}-Sub{subphase_n}"
                
                wpd_filename = f"P{Part_N}.{phase_n}.{subphase_n}-{subphase_title}.md"
                wpd_path = parent_wpd_path.parent / wpd_filename
                
                # Update state metadata
                state.wpd_grade = "L3"
                tier_state.metadata.Part_N = Part_N
                tier_state.metadata.document_title = subphase_title
                tier_state.metadata.document_type = "WPD"
                tier_state.hierarchy.parent_document = str(parent_wpd_path.relative_to(workspace_root))
                
                # Use wpd_3_template for content generation (pass tier_state, not state)
                template_content = render_wpd_template("L3", tier_state)
                
                # Write to file
                wpd_path.write_text(template_content, encoding='utf-8')
                print(f"✅ Created L3 WPD: {wpd_path.relative_to(workspace_root)}")
                
                # Step 3.6.3: Validate template
                is_valid, errors = WorkPlanCreationEngine.Verifier.verify_with_retry(wpd_path, "L3")
                tier_state.validation_results[str(wpd_path)] = is_valid
                
                if is_valid:
                    tier_state.created_documents.append(str(wpd_path.relative_to(workspace_root)))
                    return wpd_path
                else:
                    print(f"⚠️ Validation failed but document created: {wpd_path.name}")
                    tier_state.created_documents.append(str(wpd_path.relative_to(workspace_root)))
                    return wpd_path
    
    # ========================================================================
    # Main Engine Methods (Orchestration Only)
    # ========================================================================
    
    def read_wpd_grade(self, file_path: Path) -> Optional[str]:
        """Delegate to Validator.read_wpd_grade"""
        return self.Validator.read_wpd_grade(file_path)
    
    def validate_main_document(self) -> Tuple[bool, GradeInfo]:
        """
        Delegate to Validator.validate_main_document
        
        Returns:
            Tuple of (is_valid, GradeInfo with validation results)
        """
        return self.Validator.validate_main_document(self.tier_state, self.workspace_root)
    
    def check_three_tier_documentation(self, doc_path: Path, Part_N: str) -> Tuple[bool, Optional[Dict[str, str]]]:
        """Delegate to Validator.check_three_tier_documentation"""
        return self.Validator.check_three_tier_documentation(doc_path, Part_N)
    
    def extract_step_info_from_main_doc(self, main_doc_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """Delegate to Validator.extract_step_info_from_main_doc"""
        return self.Validator.extract_step_info_from_main_doc(main_doc_path)
    
    def create_wpd_l1_document(self, Part_N: str, task_title: str, parent_doc: Path, description: str = "") -> Optional[Path]:
        """
        Delegate to Creator.L1Creator.create
        
        Args:
            Part_N: Step number
            task_title: Task title
            parent_doc: Parent document path
            description: Optional description
        
        Returns:
            Path to created L1 WPD document or None
        """
        return self.Creator.L1Creator.create(
            self.state, 
            self.tier_state, 
            self.workspace_root, 
            Part_N, 
            task_title, 
            parent_doc, 
            description
        )
    
    def create_wpd_l2_document(self, parent_wpd_path: Path) -> Optional[Path]:
        """
        Delegate to Creator.L2Creator.create
        
        Args:
            parent_wpd_path: Parent L1 WPD document path
        
        Returns:
            Path to created L2 WPD document or None
        """
        return self.Creator.L2Creator.create(
            self.state, 
            self.tier_state, 
            self.workspace_root, 
            parent_wpd_path
        )
    
    def create_wpd_l3_document(self, parent_wpd_path: Path) -> Optional[Path]:
        """
        Delegate to Creator.L3Creator.create
        
        Args:
            parent_wpd_path: Parent L2 WPD document path
        
        Returns:
            Path to created L3 WPD document or None
        """
        return self.Creator.L3Creator.create(
            self.state, 
            self.tier_state, 
            self.workspace_root, 
            parent_wpd_path
        )
    
    def execute(self, user_input: str) -> AgentState:
        """
        Main execution entry point for Tier A
        
        Implements the complete workflow from Untitled-1.md lines 14-193
        """
        self.log("=" * 80)
        self.log("TIER A: Work Plan Creation - Starting")
        self.log("=" * 80)
        
        try:
            # Step 0: Auto-routing conflict detection
            routing_engine = self.AutoRoutingEngine(self.workspace_root)
            conflict_resolution = routing_engine.detect_conflicts(user_input)
            
            if conflict_resolution.has_conflict and conflict_resolution.target_document:
                self.log(f"Conflict detected: Merging into existing document {conflict_resolution.target_document.name}")
                # Generate content to merge (simplified for now)
                merge_content = f"## Auto-Merged Content\n\n{user_input}\n\n*Generated via auto-routing on {datetime.now().strftime('%Y-%m-%d')}*"
                
                if routing_engine.merge_content(conflict_resolution.target_document, merge_content):
                    self.log("✅ Content merged successfully")
                    # Chain to Tier E for document management
                    self.state.next_node = "E"
                    self.state.status = "SUCCESS"
                    self.state.logic_summary = f"Auto-routed content merged into {conflict_resolution.target_document.name}"
                    return self.state
                else:
                    self.log("❌ Content merge failed, proceeding with normal creation")
            
            # Step 1.0: Validate main document
            is_valid, main_grade_info = self.validate_main_document()
            
            if not is_valid:
                return AgentState.create_failure(
                    tier="A",
                    error_msg=f"Main document validation failed: {self.tier_state.main_document_path}",
                    logic_summary="Cannot proceed without valid main progress document"
                )
            
            # Extract step number and task title from main document
            main_doc_path = self.workspace_root / self.tier_state.main_document_path
            Part_N, task_title = self.extract_step_info_from_main_doc(main_doc_path)
            
            if not Part_N or not task_title:
                # Use default values if not found
                Part_N = "99"
                task_title = "New-Task"
                self.log(f"Using default Part_N={Part_N}, task_title={task_title}")
            
            # Check if user specified a document path (Step 2.0)
            user_specified_doc = self._extract_document_path_from_input(user_input)
            
            if user_specified_doc:
                # Step 2.0: User specified document path
                self.log(f"Step 2.0: User specified document: {user_specified_doc}")
                specified_path = self.workspace_root / user_specified_doc
                
                if not specified_path.exists():
                    return AgentState.create_failure(
                        tier="A",
                        error_msg=f"Specified document does not exist: {user_specified_doc}",
                        logic_summary="User-specified document not found"
                    )
                
                # Read or detect WPD_grade (Step 2.4)
                grade = self.read_wpd_grade(specified_path)
                if not grade:
                    grade = detect_grade_from_path(user_specified_doc)
                    self.log(f"Auto-detected WPD_grade from path: {grade}")
                else:
                    self.log(f"Read WPD_grade from document: {grade}")
                
                # Handle based on grade level
                if grade == "L1":
                    # Step 2.1 & 3.3: L1 → L2 progression - Extract phases and create L2 per phase
                    self.log("Step 2.1 & 3.3: Creating L2 documents from L1 phases")
                    
                    # Step 3.3.0-3.3.1: Extract phases from L1
                    phases = self.PhaseExtractor.extract_phases_from_l1(specified_path)
                    
                    if not phases:
                        # No phases found, create a default L2
                        self.log("No phases found in L1, creating default L2")
                        l2_path = self.create_wpd_l2_document(specified_path)
                        if not l2_path:
                            self.log(f"WARNING: Failed to create L2 from L1: {specified_path.name}")
                    else:
                        # Step 3.4: Create L2 for each phase
                        for phase in phases:
                            l2_path = self.Creator.L2Creator.create_from_phase(
                                self.state,
                                self.tier_state,
                                self.workspace_root,
                                specified_path,
                                phase
                            )
                            if l2_path:
                                self.created_documents.append(str(l2_path.relative_to(self.workspace_root)))
                                self.log(f"Created L2 for phase {phase['phase_n']}: {l2_path.name}")
                                
                                # Step 3.5: Check if any subphases exceed 300 lines for L3 creation
                                subphases = self.PhaseExtractor.extract_subphases_from_l2(l2_path)
                                exceeding = self.PhaseExtractor.check_300_line_threshold(subphases)
                                
                                if exceeding:
                                    self.log(f"Step 3.5.1: {len(exceeding)} subphases exceed 300 lines, creating L3 documents")
                                    # Create L3 for subphases that exceed threshold
                                    for subphase in exceeding:
                                        l3_path = self.create_wpd_l3_document(l2_path)
                                        if l3_path:
                                            self.created_documents.append(str(l3_path.relative_to(self.workspace_root)))
                                            self.log(f"Created L3 for subphase {subphase['subphase_n']}")
                                else:
                                    self.log("Step 3.5.0: No subphases exceed 300 lines, stopping at L2")
                    
                elif grade == "L2":
                    # Step 2.2 & 3.5: L2 → L3 progression with 300-line threshold check
                    self.log("Step 2.2 & 3.5: Creating L3 documents from L2 subphases")
                    
                    # Step 3.5: Extract subphases and check 300-line threshold
                    subphases = self.PhaseExtractor.extract_subphases_from_l2(specified_path)
                    exceeding = self.PhaseExtractor.check_300_line_threshold(subphases)
                    
                    if exceeding:
                        self.log(f"Step 3.5.1: {len(exceeding)} subphases exceed 300 lines")
                        # Create L3 for each subphase that exceeds threshold
                        for subphase in exceeding:
                            l3_path = self.create_wpd_l3_document(specified_path)
                            if l3_path:
                                self.created_documents.append(str(l3_path.relative_to(self.workspace_root)))
                                self.log(f"Created L3 for subphase {subphase['subphase_n']}")
                            else:
                                self.log(f"WARNING: Failed to create L3 for subphase {subphase['subphase_n']}")
                    else:
                        self.log("Step 3.5.0: No subphases exceed 300 lines, stopping at L2")
                
                elif grade == "L3":
                    # Step 2.3: L3 creation in same path
                    self.log("Step 2.3: Creating additional L3 document")
                    # For L3, we would need to create a sibling L3
                    # This requires the parent L2 path
                    # Extract parent L2 path from L3 path
                    # Pattern: docs_2/P[Part_N]/P[Part_N].[Phase_N].[Subphase_N]-title.md
                    # Parent:  docs_2/P[Part_N]/P[Part_N].[Phase_N]-title.md
                    match = re.search(r'(P\d+\.\d+)-', specified_path.name)
                    if match:
                        parent_l2_name = match.group(1)
                        parent_l2_files = list(specified_path.parent.glob(f"{parent_l2_name}-*.md"))
                        # Filter to only L2 files (not L3)
                        parent_l2_files = [f for f in parent_l2_files if re.search(r'P\d+\.\d+-[^.]+\.md$', f.name)]
                        if parent_l2_files:
                            l3_path = self.create_wpd_l3_document(parent_l2_files[0])
                        else:
                            self.log(f"WARNING: Could not find parent L2 for L3: {specified_path.name}")
                    else:
                        self.log(f"WARNING: Could not extract parent info from L3: {specified_path.name}")
                
            else:
                # Step 1.2-1.3: Work with main document (no user-specified doc)
                # Check for Three-Tier Documentation
                has_three_tier, doc_paths = self.check_three_tier_documentation(main_doc_path, Part_N)
                
                if not has_three_tier:
                    # Step 1.3.0: Create Three-Tier Documentation
                    self.log("Step 1.3.0: Creating Three-Tier Documentation section")
                    
                    # Create new WPD L1 document
                    wpd_path = self.create_wpd_l1_document(Part_N, task_title, main_doc_path)
                    
                    if not wpd_path:
                        return AgentState.create_failure(
                            tier="A",
                            error_msg="Failed to create L1 WPD document",
                            logic_summary="L1 WPD creation failed validation"
                        )
                    
                    # Add Three-Tier Documentation section to main document
                    self._add_three_tier_section_to_main_doc(main_doc_path, Part_N, task_title)
                    
                else:
                    # Step 1.3.1: Three-Tier Documentation exists
                    self.log("Step 1.3.1: Three-Tier Documentation exists, reading existing WPD")
                    
                    # Read existing L1 WPD
                    wpd_path_str = doc_paths.get("wpd", "")
                    wpd_path = self.workspace_root / wpd_path_str if wpd_path_str else None
                    
                    if wpd_path and wpd_path.exists():
                        # Step 3.3: Extract phases from L1 and create L2 for each phase
                        phases = self.PhaseExtractor.extract_phases_from_l1(wpd_path)
                        
                        if not phases:
                            # No phases found, create a default L2
                            self.log("No phases found in L1, creating default L2")
                            l2_path = self.create_wpd_l2_document(wpd_path)
                            if l2_path:
                                self.created_documents.append(str(l2_path.relative_to(self.workspace_root)))
                        else:
                            # Step 3.4: Create L2 for each phase
                            for phase in phases:
                                l2_path = self.Creator.L2Creator.create_from_phase(
                                    self.state,
                                    self.tier_state,
                                    self.workspace_root,
                                    wpd_path,
                                    phase
                                )
                                if l2_path:
                                    self.created_documents.append(str(l2_path.relative_to(self.workspace_root)))
                                    self.log(f"Created L2 for phase {phase['phase_n']}: {l2_path.name}")
                                    
                                    # Step 3.5: Check if any subphases exceed 300 lines for L3 creation
                                    subphases = self.PhaseExtractor.extract_subphases_from_l2(l2_path)
                                    exceeding = self.PhaseExtractor.check_300_line_threshold(subphases)
                                    
                                    if exceeding:
                                        self.log(f"Step 3.5.1: {len(exceeding)} subphases exceed 300 lines, creating L3 documents")
                                        # Create L3 for subphases that exceed threshold
                                        for subphase in exceeding:
                                            l3_path = self.create_wpd_l3_document(l2_path)
                                            if l3_path:
                                                self.created_documents.append(str(l3_path.relative_to(self.workspace_root)))
                                                self.log(f"Created L3 for subphase {subphase['subphase_n']}")
                                    else:
                                        self.log("Step 3.5.0: No subphases exceed 300 lines, stopping at L2")
            # Create success state and route to Tier B
            # Update tier state with results
            self.tier_state.created_documents = self.created_documents
            self.tier_state.metadata = DocumentMetadata(Part_N=Part_N, document_type="WPD")
            
            # Determine highest grade created
            wpd_grade = "L1"
            for doc in self.created_documents:
                if "P" in doc and "." in doc:
                    parts = doc.split(".")
                    if len(parts) >= 3:  # L3
                        wpd_grade = "L3"
                    elif len(parts) >= 2 and wpd_grade != "L3":  # L2
                        wpd_grade = "L2"
            
            # Build final AgentState with both payloads
            self.state.tier = "A"
            self.state.status = "SUCCESS"
            self.state.logic_summary = f"Work plan creation completed. Created {len(self.created_documents)} documents."
            self.state.next_node = "B"  # Auto-route to Tier B
            self.state.payload = self.tier_state.to_payload()  # Tier-specific data
            
            # Set common fields in AgentState
            self.state.execution_log = self.execution_log
            self.state.wpd_grade = wpd_grade
            self.tier_state.metadata.to_dict()
            self.tier_state.hierarchy.to_dict()
            self.state.execution_time_ms = 0  # TODO: Track actual time
            
            self.log("=" * 80)
            self.log("TIER A: Work Plan Creation - Completed")
            self.log(f"Next Node: {self.state.next_node}")
            self.log("=" * 80)
            
            return self.state
            
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            
            return AgentState.create_failure(
                tier="A",
                error_msg=f"Work plan creation failed: {str(e)}",
                logic_summary=f"Exception during execution: {type(e).__name__}"
            )
    
    def _add_three_tier_section_to_main_doc(self, main_doc_path: Path, Part_N: str, task_title: str):
        """Add Three-Tier Documentation section to main document (Step 1.3.0)"""
        try:
            content = main_doc_path.read_text(encoding='utf-8')
            
            # Create Three-Tier Documentation section
            three_tier_section = f"""
            ### Three-Tier Documentation
            1. **WPD** (`docs_2/P{Part_N}/P{Part_N}-{task_title}.md`) - Implementation plans
            2. **PRD** (`docs_2/prd/PRD-P{Part_N}.md`) - Progress tracking
            """
            
            # Find the step section and add after it
            step_pattern = rf'(##\s+🟢\s+step\s+{Part_N}:[^\n]+\n.*?)(##\s+|$)'
            
            if re.search(step_pattern, content, re.DOTALL):
                # Insert Three-Tier Documentation after step header
                content = re.sub(
                    rf'(##\s+🟢\s+step\s+{Part_N}:[^\n]+\n)',
                    rf'\1{three_tier_section}\n',
                    content
                )
                
                main_doc_path.write_text(content, encoding='utf-8')
                self.log(f"Added Three-Tier Documentation section to {main_doc_path}")
            else:
                self.log(f"Could not find step {Part_N} section in main document")
                
        except Exception as e:
            self.log(f"Error adding Three-Tier section: {e}")
    
    def _extract_document_path_from_input(self, user_input: str) -> Optional[str]:
        """Extract document path from user input if specified"""
        # Look for file paths in user input
        path_patterns = [
            r'docs_2/[^\s]+\.md',
            r'P\d+/[^\s]+\.md',
        ]
        
        for pattern in path_patterns:
            match = re.search(pattern, user_input)
            if match:
                return match.group(0)
        
        return None


def main(user_input: str, workspace_root: str = ".") -> AgentState:
    """
    Entry point for Tier A module
    
    Args:
        user_input: User's natural language request
        workspace_root: Root directory of the workspace
    
    Returns:
        AgentState with execution results
    """
    engine = WorkPlanCreationEngine(workspace_root)
    state = engine.execute(user_input)
    
    # Emit AgentState to stdout for orchestrator to capture
    state.emit()
    
    return state


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python A_Working_Document_Progress.py '<user_input>' [workspace_root]")
        print("Example: python A_Working_Document_Progress.py 'Create a work plan for step 5' .")
        sys.exit(1)
    
    user_input = sys.argv[1]
    workspace_root = sys.argv[2] if len(sys.argv) > 2 else "."
    
    main(user_input, workspace_root)
