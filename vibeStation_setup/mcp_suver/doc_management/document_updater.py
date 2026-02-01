"""
Document Updater - WPD/PRD Document Updates

Handles:
- Checklist updates with status symbols
- Timestamp addition to completed tasks
- Implementation summary updates
- Progress tracking
- Batch updates across multiple documents

Status Symbols:
- ✅ complete/done
- ❌ failed
- ⏳ in_progress
- 📋 pending
- 🚫 blocked
"""

import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Literal


class DocumentUpdater:
    """
    Updates WPD and PRD documents with progress tracking
    
    Features:
    - Update checklist item status
    - Add timestamps to completed tasks
    - Update implementation summaries
    - Track progress systematically
    """
    
    STATUS_SYMBOLS = {
        'complete': '✅',
        'done': '✅',
        'failed': '❌',
        'in_progress': '⏳',
        'pending': '📋',
        'blocked': '🚫'
    }
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.changes: List[str] = []
    
    def update_checklist_item(
        self,
        doc_path: Path,
        item_text: str,
        status: Literal['complete', 'done', 'failed', 'in_progress', 'pending', 'blocked'],
        add_timestamp: bool = True
    ) -> Dict[str, any]:
        """
        Update checklist item status
        
        Args:
            doc_path: Document path
            item_text: Text of checklist item to update
            status: New status
            add_timestamp: Whether to add timestamp
            
        Returns:
            Result dict with success status
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        content = doc_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        status_symbol = self.STATUS_SYMBOLS.get(status, '📋')
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if add_timestamp else ""
        
        updated = False
        for i, line in enumerate(lines):
            # Match checklist items with item_text
            if item_text.lower() in line.lower() and re.match(r'^\s*[-*]\s+\[', line):
                # Update status
                if add_timestamp and status in ['complete', 'done']:
                    # Add timestamp for completed items
                    lines[i] = re.sub(
                        r'(\s*[-*]\s+)\[[ xX✅❌⏳📋🚫]\]\s*(.+)',
                        rf'\1[{status_symbol}] \2 (completed: {timestamp})',
                        line
                    )
                else:
                    # Just update status symbol
                    lines[i] = re.sub(
                        r'(\s*[-*]\s+)\[[ xX✅❌⏳📋🚫]\]\s*',
                        rf'\1[{status_symbol}] ',
                        line
                    )
                updated = True
                self.changes.append(f"Updated: {item_text} -> {status}")
                break
        
        if updated:
            content = '\n'.join(lines)
            doc_path.write_text(content, encoding='utf-8')
            
            return {
                "success": True,
                "item": item_text,
                "status": status,
                "timestamp": timestamp if add_timestamp else None
            }
        else:
            return {
                "success": False,
                "error": f"Checklist item not found: {item_text}"
            }
    
    def add_implementation_note(
        self,
        doc_path: Path,
        note_content: str,
        section: str = "Implementation Summary"
    ) -> Dict[str, any]:
        """
        Add implementation note to document
        
        Args:
            doc_path: Document path
            note_content: Note content to add
            section: Section name to add note to
            
        Returns:
            Result dict
        """
        if not doc_path.exists():
            return {"success": False, "error": "Document not found"}
        
        content = doc_path.read_text(encoding='utf-8')
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        note = f"\n**[{timestamp}]** {note_content}\n"
        
        # Find section and add note
        section_pattern = rf'(## {re.escape(section)}\s*\n)'
        if re.search(section_pattern, content):
            content = re.sub(section_pattern, rf'\1{note}', content)
        else:
            # Create section if not exists
            content += f"\n\n## {section}\n{note}"
        
        doc_path.write_text(content, encoding='utf-8')
        self.changes.append(f"Added note to {section}")
        
        return {
            "success": True,
            "section": section,
            "timestamp": timestamp
        }
    
    def batch_update_checklists(
        self,
        updates: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Batch update multiple checklist items
        
        Args:
            updates: List of update dicts with keys: doc_path, item_text, status
            
        Returns:
            Summary of batch operation
        """
        results = []
        for update in updates:
            result = self.update_checklist_item(
                Path(update['doc_path']),
                update['item_text'],
                update['status'],
                update.get('add_timestamp', True)
            )
            results.append(result)
        
        successful = sum(1 for r in results if r.get('success'))
        
        return {
            "success": True,
            "total": len(updates),
            "successful": successful,
            "failed": len(updates) - successful,
            "results": results
        }
    
    def find_checklist_items(
        self,
        doc_path: Path,
        section: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Find all checklist items in document
        
        Args:
            doc_path: Document path
            section: Optional section to limit search
            
        Returns:
            List of checklist items with status
        """
        if not doc_path.exists():
            return []
        
        content = doc_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        items = []
        in_target_section = section is None
        
        for i, line in enumerate(lines):
            # Check section boundaries
            if section and line.strip().startswith('#'):
                if section.lower() in line.lower():
                    in_target_section = True
                elif in_target_section and line.strip().startswith('##'):
                    in_target_section = False
            
            if not in_target_section:
                continue
            
            # Match checklist items
            match = re.match(r'^(\s*)[-*]\s+(\[[ xX✅❌⏳📋🚫]\]|[✅❌⏳📋🚫])?\s*(.+)$', line)
            if match:
                indent = len(match.group(1))
                status_part = match.group(2) or ''
                text = match.group(3).strip()
                
                # Determine status
                if '[x]' in status_part.lower() or '✅' in status_part:
                    status = 'complete'
                elif '❌' in status_part:
                    status = 'failed'
                elif '⏳' in status_part:
                    status = 'in_progress'
                elif '🚫' in status_part:
                    status = 'blocked'
                else:
                    status = 'pending'
                
                items.append({
                    "line_number": i + 1,
                    "indent": indent,
                    "status": status,
                    "text": text,
                    "raw_line": line
                })
        
        return items
    
    def get_changes(self) -> List[str]:
        """Get list of changes made"""
        return self.changes.copy()


__all__ = ["DocumentUpdater"]
