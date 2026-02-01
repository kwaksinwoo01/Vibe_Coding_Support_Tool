"""
Checklist Manager - Document Checklist Management

Handles:
- Adding checklist items
- Deleting checklist items
- Modifying checklist items (mark as complete/incomplete)
- Checklist validation
"""

import re
from pathlib import Path
from typing import Dict, Any


class ChecklistManager:
    """Manages document checklists"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
    
    def add_item(self, doc_path: Path, item_description: str) -> Dict[str, Any]:
        """
        Add new checklist item to document
        
        Args:
            doc_path: Document path
            item_description: Item description text
            
        Returns:
            Result dict with success status
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        content = doc_path.read_text(encoding='utf-8')
        
        # Add new checklist item
        checklist_pattern = r'(\*\*Checklist\*\*:.*\n)'
        if re.search(checklist_pattern, content):
            content = re.sub(checklist_pattern, rf'\g<1>- [ ] {item_description}\n', content)
        else:
            # Create Checklist section if not exists
            content += f"\n\n**Checklist**:\n- [ ] {item_description}\n"
        
        doc_path.write_text(content, encoding='utf-8')
        
        return {
            "success": True,
            "action": "add",
            "item": item_description
        }
    
    def delete_item(self, doc_path: Path, item_description: str) -> Dict[str, Any]:
        """
        Delete checklist item from document
        
        Args:
            doc_path: Document path
            item_description: Item description to delete
            
        Returns:
            Result dict with success status
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        content = doc_path.read_text(encoding='utf-8')
        
        # Remove checklist item
        item_pattern = rf'- \[[ x]\] {re.escape(item_description)}\n'
        content = re.sub(item_pattern, '', content)
        
        doc_path.write_text(content, encoding='utf-8')
        
        return {
            "success": True,
            "action": "delete",
            "item": item_description
        }
    
    def mark_complete(self, doc_path: Path, item_description: str) -> Dict[str, Any]:
        """
        Mark checklist item as complete
        
        Args:
            doc_path: Document path
            item_description: Item description to mark
            
        Returns:
            Result dict with success status
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}

        content = doc_path.read_text(encoding='utf-8')

        # Replace unchecked item with checked one
        pattern = rf'- \[ \] {re.escape(item_description)}'
        if re.search(pattern, content):
            content = re.sub(pattern, f'- [x] {item_description}', content)
        else:
            # If an unchecked item pattern wasn't found, try a more permissive replace
            content = re.sub(rf'- \[[ xX]\] {re.escape(item_description)}', f'- [x] {item_description}', content)

        doc_path.write_text(content, encoding='utf-8')

        return {
            "success": True,
            "action": "mark_complete",
            "item": item_description
        }
    
    def mark_incomplete(self, doc_path: Path, item_description: str) -> Dict[str, Any]:
        """
        Mark checklist item as incomplete
        
        Args:
            doc_path: Document path
            item_description: Item description to unmark
            
        Returns:
            Result dict with success status
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}

        content = doc_path.read_text(encoding='utf-8')

        # Replace checked item with unchecked one
        pattern = rf'- \[[xX]\] {re.escape(item_description)}'
        if re.search(pattern, content):
            content = re.sub(pattern, f'- [ ] {item_description}', content)
        else:
            # If exact pattern not found, perform a permissive replace
            content = re.sub(rf'- \[[ xX]\] {re.escape(item_description)}', f'- [ ] {item_description}', content)

        doc_path.write_text(content, encoding='utf-8')

        return {
            "success": True,
            "action": "mark_incomplete",
            "item": item_description
        }
    
    def manage_item(self, doc_path: Path, item_status: str, item_description: str) -> Dict[str, Any]:
        """
        Unified checklist management interface
        
        Args:
            doc_path: Document path
            item_status: Operation type: 'add', 'delete', 'modify' (mark complete)
            item_description: Item description
            
        Returns:
            Result dict with success status
        """
        if item_status == "add":
            return self.add_item(doc_path, item_description)
        elif item_status == "delete":
            return self.delete_item(doc_path, item_description)
        elif item_status == "modify":
            return self.mark_complete(doc_path, item_description)
        else:
            return {"success": False, "error": f"Invalid operation: {item_status}"}


__all__ = ["ChecklistManager"]
