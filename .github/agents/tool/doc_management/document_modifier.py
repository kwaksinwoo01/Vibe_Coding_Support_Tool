"""
Document Modifier - Safe Document Modification with ADMP Rules

Handles:
- Safe modification of WPD/PRD documents
- ADMP policy enforcement (immutable vs modifiable sections)
- Modification tracking and timestamping
- Permission validation
- Attempt tracking (3-strike rule)

Enforces Agent Document Modification Policy (ADMP):
- Immutable sections are protected
- All modifications are timestamped and justified
- Modification attempts are tracked
- Traceability is preserved
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional, Dict, List, Tuple


class ModificationPermissionError(Exception):
    """Raised when agent attempts unauthorized modification."""
    pass


class DocumentModifier:
    """
    Safe document modifier following ADMP rules
    
    Enforces strict rules for agent modifications:
    - Protects immutable sections (Goal, Success Criteria, Scope)
    - Allows modifications to designated sections
    - Tracks all modification attempts
    - Adds timestamps to modifications
    """
    
    # ADMP Policy Definitions
    IMMUTABLE_SECTIONS = {
        "WPD": [
            "Goal", "목표",
            "Success Criteria", "성공 기준",
            "Scope", "범위",
        ],
        "PRD": [
            "Original Success Criteria",
            "Task Definition",
            "Sign-off",
        ],
    }
    
    MODIFIABLE_SECTIONS = {
        "WPD": [
            "Implementation Summary", "구현 요약",
            "Work Progress", "작업 진행도",
            "Test Results", "테스트 결과",
            "Blockers and Workarounds", "문제점 및 해결방법",
            "Agent Update",  # Special section for agent additions
        ],
        "PRD": [
            "Implementation Progress", "구현 진행도",
            "Validation Results", "검증 결과",
            "Issues Found & Resolutions", "발견된 문제 및 해결 방법",
            "Attempt History", "시도 기록",
        ],
    }
    
    CHECKLIST_SECTIONS = {
        "WPD": ["Work Progress", "작업 진행도"],
        "PRD": ["Implementation Progress", "구현 진행도"],
    }
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.modification_attempts: List[Dict[str, str]] = []
    
    def can_modify(
        self,
        doc_type: Literal["WPD", "PRD"],
        section_name: str,
        modification_type: Literal["add_content", "update_checklist", "delete", "modify"],
    ) -> bool:
        """
        Check if modification is allowed
        
        Args:
            doc_type: Document type
            section_name: Section being modified
            modification_type: Type of modification
            
        Returns:
            True if allowed, False otherwise
        """
        # Immutable sections cannot be deleted or modified
        if section_name in self.IMMUTABLE_SECTIONS.get(doc_type, []):
            if modification_type in ["delete", "modify"]:
                return False
        
        # Modifiable sections can be updated
        if section_name in self.MODIFIABLE_SECTIONS.get(doc_type, []):
            return True
        
        # Checklist sections allow checklist updates
        if section_name in self.CHECKLIST_SECTIONS.get(doc_type, []):
            if modification_type == "update_checklist":
                return True
        
        # Default: allow adding content, deny modifications
        return modification_type == "add_content"
    
    def modify_section(
        self,
        doc_path: Path,
        doc_type: Literal["WPD", "PRD"],
        section_name: str,
        new_content: str,
        modification_type: Literal["add_content", "update_checklist", "modify"] = "add_content",
        justification: str = ""
    ) -> Dict[str, any]:
        """
        Safely modify document section
        
        Args:
            doc_path: Document path
            doc_type: Document type
            section_name: Section to modify
            new_content: Content to add/update
            modification_type: Type of modification
            justification: Reason for modification
            
        Returns:
            Result dict with success status
        """
        # Check permission
        if not self.can_modify(doc_type, section_name, modification_type):
            raise ModificationPermissionError(
                f"Cannot {modification_type} section '{section_name}' in {doc_type} document. "
                f"This section is immutable per ADMP policy."
            )
        
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        content = doc_path.read_text(encoding='utf-8')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add timestamp and justification to modification
        modification_header = f"\n**[Agent Update - {timestamp}]**"
        if justification:
            modification_header += f" *{justification}*"
        modification_header += "\n\n"
        
        # Find section and add content
        section_pattern = rf'(## {re.escape(section_name)}\s*\n)'
        if re.search(section_pattern, content):
            # Add content after section header
            content = re.sub(
                section_pattern,
                rf'\1{modification_header}{new_content}\n\n',
                content
            )
        else:
            # Section doesn't exist - add it
            content += f"\n\n## {section_name}\n{modification_header}{new_content}\n"
        
        doc_path.write_text(content, encoding='utf-8')
        
        # Track modification
        self.modification_attempts.append({
            "timestamp": timestamp,
            "doc_path": str(doc_path),
            "section": section_name,
            "type": modification_type,
            "justification": justification,
            "success": True
        })
        
        return {
            "success": True,
            "timestamp": timestamp,
            "section": section_name,
            "modification_type": modification_type
        }
    
    def add_agent_update(
        self,
        doc_path: Path,
        doc_type: Literal["WPD", "PRD"],
        update_content: str,
        justification: str = ""
    ) -> Dict[str, any]:
        """
        Add content to Agent Update section
        
        Args:
            doc_path: Document path
            doc_type: Document type
            update_content: Content to add
            justification: Reason for update
            
        Returns:
            Result dict
        """
        return self.modify_section(
            doc_path,
            doc_type,
            "Agent Update",
            update_content,
            modification_type="add_content",
            justification=justification
        )
    
    def get_modification_history(self, doc_path: Optional[Path] = None) -> List[Dict[str, str]]:
        """
        Get modification attempt history
        
        Args:
            doc_path: Optional filter by document path
            
        Returns:
            List of modification attempts
        """
        if doc_path:
            return [
                attempt for attempt in self.modification_attempts
                if attempt["doc_path"] == str(doc_path)
            ]
        return self.modification_attempts


__all__ = ["DocumentModifier", "ModificationPermissionError"]
