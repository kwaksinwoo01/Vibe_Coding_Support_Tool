"""
Error Session Manager - Document Error Tracking and Resolution

Handles:
- Adding error sessions to documents
- Creating solution plans
- Routing errors to appropriate tiers
- Error tracking and resolution workflow
"""

import re
from pathlib import Path
from typing import Dict, Any, List


class ErrorSessionManager:
    """Manages error sessions and solution routing"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
    
    def add_error_sessions(self, doc_path: Path, error_list: List[str]) -> Dict[str, Any]:
        """
        Add error sessions to document
        
        Args:
            doc_path: Document path
            error_list: List of error descriptions
            
        Returns:
            Result dict with success status and solution plans
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        content = doc_path.read_text(encoding='utf-8')
        
        # Add "## Issues" section if not exists
        if "## Issues" not in content:
            # Insert above Overview/Implementation Note/Executive Summary
            insert_patterns = [
                r'(## 📋 Overview)',
                r'(## 📋 Implementation Note)',
                r'(## 📋 Executive Summary)',
                r'(## Overview)',
                r'(## Implementation)'
            ]
            
            inserted = False
            for pattern in insert_patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, r'## Issues\n\n\1', content)
                    inserted = True
                    break
            
            if not inserted:
                # Add Issues section at end
                content += "\n\n## Issues\n\n"
        
        # Add error entries
        issues_section_pattern = r'(## Issues\n+)'
        error_entries = "\n".join([f"- {error_desc}" for error_desc in error_list])
        content = re.sub(issues_section_pattern, rf'\1{error_entries}\n\n', content)
        
        doc_path.write_text(content, encoding='utf-8')
        
        # Create solution plans for Tier C
        solution_plans = []
        for error_desc in error_list:
            solution_plan = {
                "error": error_desc,
                "target_doc": str(doc_path),
                "wpd_grade": self._get_wpd_grade(doc_path),
                "route_to": "Tier C"
            }
            solution_plans.append(solution_plan)
        
        return {
            "success": True,
            "errors_added": len(error_list),
            "solution_plans": solution_plans,
            "next_node": "C"  # Route to Tier C for implementation
        }
    
    def get_error_sessions(self, doc_path: Path) -> List[str]:
        """
        Extract error sessions from document
        
        Args:
            doc_path: Document path
            
        Returns:
            List of error descriptions
        """
        if not doc_path.exists():
            return []
        
        content = doc_path.read_text(encoding='utf-8')
        
        # Find Issues section
        issues_pattern = r'## Issues\n+((?:- .+\n?)+)'
        match = re.search(issues_pattern, content)
        
        if not match:
            return []
        
        # Extract error items
        issues_text = match.group(1)
        errors = re.findall(r'- (.+)', issues_text)
        
        return errors
    
    def resolve_error_session(self, doc_path: Path, error_description: str) -> Dict[str, Any]:
        """
        Mark error session as resolved
        
        Args:
            doc_path: Document path
            error_description: Error description to resolve
            
        Returns:
            Result dict with success status
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        content = doc_path.read_text(encoding='utf-8')
        
        # Mark error as resolved (strikethrough)
        error_pattern = rf'(- ){re.escape(error_description)}'
        resolved_pattern = rf'\1~~{error_description}~~ ✅ RESOLVED'
        content = re.sub(error_pattern, resolved_pattern, content)
        
        doc_path.write_text(content, encoding='utf-8')
        
        return {
            "success": True,
            "resolved_error": error_description
        }
    
    def remove_error_session(self, doc_path: Path, error_description: str) -> Dict[str, Any]:
        """
        Remove error session from document
        
        Args:
            doc_path: Document path
            error_description: Error description to remove
            
        Returns:
            Result dict with success status
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        content = doc_path.read_text(encoding='utf-8')
        
        # Remove error line
        error_pattern = rf'- {re.escape(error_description)}\n?'
        content = re.sub(error_pattern, '', content)
        
        doc_path.write_text(content, encoding='utf-8')
        
        return {
            "success": True,
            "removed_error": error_description
        }
    
    def create_solution_plan(self, error_description: str, target_doc: Path, 
                           route_to_tier: str = "C") -> Dict[str, Any]:
        """
        Create a solution plan for an error
        
        Args:
            error_description: Error description
            target_doc: Document with the error
            route_to_tier: Tier to route to (default: C)
            
        Returns:
            Solution plan dict
        """
        return {
            "error": error_description,
            "target_doc": str(target_doc),
            "wpd_grade": self._get_wpd_grade(target_doc),
            "route_to": f"Tier {route_to_tier}",
            "status": "pending"
        }
    
    def _get_wpd_grade(self, doc_path: Path) -> str:
        """Extract WPD grade from document"""
        if not doc_path.exists():
            return "L0"
        
        content = doc_path.read_text(encoding='utf-8')
        grade_pattern = r'\*\*WPD_grade\*\*:\s*(L\d+)'
        match = re.search(grade_pattern, content)
        
        if match:
            return match.group(1)
        
        # Infer from filename
        filename = doc_path.stem
        if re.match(r'P\d+\.\d+\.\d+-', filename):
            return "L3"
        elif re.match(r'P\d+\.\d+-', filename):
            return "L2"
        elif re.match(r'P\d+-', filename):
            return "L1"
        
        return "L0"


__all__ = ["ErrorSessionManager"]
