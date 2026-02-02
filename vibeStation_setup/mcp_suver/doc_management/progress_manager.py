"""
Progress Manager - Document Progress State Management

Handles:
- Progress state updates (Not Started, In Progress, Completed)
- Status field validation and updates
- Progress tracking across document hierarchy
"""

import re
from pathlib import Path
from typing import Dict, Any, List


class ProgressManager:
    """Manages document progress states"""
    
    VALID_STATES = ["Not Started", "In Progress", "Completed", "PENDING", "IN PROGRESS", "COMPLETE"]
    
    def update_progress(self, doc_path: Path, progress_state: str) -> Dict[str, Any]:
        """
        Update document progress state
        
        Args:
            doc_path: Document path
            progress_state: New progress state
            
        Returns:
            Result dict with success status and new progress
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        if progress_state not in self.VALID_STATES:
            return {
                "success": False,
                "error": f"Invalid progress state: {progress_state}. Valid states: {', '.join(self.VALID_STATES)}"
            }
        
        content = doc_path.read_text(encoding='utf-8')
        
        # Update Status field
        status_pattern = r'(\*\*Status\*\*:\s*)[^\n]*'
        if re.search(status_pattern, content):
            content = re.sub(status_pattern, rf'\1{progress_state}', content)
        else:
            # Add status if not exists (after WPD_grade or Version line)
            insertion_patterns = [
                r'(\*\*Version\*\*:.*\n)',
                r'(\*\*WPD_grade\*\*:.*\n)'
            ]
            
            inserted = False
            for pattern in insertion_patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, rf'\g<1>**Status**: {progress_state}\n', content)
                    inserted = True
                    break
            
            if not inserted:
                # Add at beginning of document
                content = f"**Status**: {progress_state}\n\n{content}"
        
        doc_path.write_text(content, encoding='utf-8')
        
        return {
            "success": True,
            "new_progress": progress_state,
            "document": str(doc_path)
        }
    
    def get_progress(self, doc_path: Path) -> str:
        """
        Get current progress state from document
        
        Args:
            doc_path: Document path
            
        Returns:
            Current progress state or "Not Started" as default
        """
        if not doc_path.exists():
            return "Not Started"
        
        content = doc_path.read_text(encoding='utf-8')
        status_pattern = r'\*\*Status\*\*:\s*([^\n]+)'
        match = re.search(status_pattern, content)
        
        if match:
            return match.group(1).strip()
        
        return "Not Started"
    
    def mark_as_started(self, doc_path: Path) -> Dict[str, Any]:
        """Mark document as In Progress"""
        return self.update_progress(doc_path, "IN PROGRESS")

    def mark_as_completed(self, doc_path: Path) -> Dict[str, Any]:
        """Mark document as Completed"""
        return self.update_progress(doc_path, "COMPLETE")

    def mark_as_pending(self, doc_path: Path) -> Dict[str, Any]:
        """Mark document as Pending"""
        return self.update_progress(doc_path, "PENDING")
        """
        Get progress summary for multiple documents
        
        Args:
            doc_paths: List of document paths to check
            
        Returns:
            Summary dict with counts and progress list
        """
        summary = {
            "total": len(doc_paths),
            "not_started": 0,
            "in_progress": 0,
            "completed": 0,
            "documents": []
        }
        
        for doc_path in doc_paths:
            progress = self.get_progress(doc_path)
            
            # Categorize
            if "COMPLETE" in progress or "Completed" in progress:
                summary["completed"] += 1
            elif "PROGRESS" in progress or "In Progress" in progress:
                summary["in_progress"] += 1
            else:
                summary["not_started"] += 1
            
            summary["documents"].append({
                "path": str(doc_path),
                "progress": progress
            })
        
        # Calculate completion percentage
        if summary["total"] > 0:
            summary["completion_percentage"] = (summary["completed"] / summary["total"]) * 100
        else:
            summary["completion_percentage"] = 0.0
        
        return summary


__all__ = ["ProgressManager"]
