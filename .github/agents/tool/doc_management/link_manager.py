"""
Link Manager - Document Link Management

Handles:
- Document link inspection
- Broken link detection
- Link fixing and validation
- Cross-reference tracking
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional


class LinkManager:
    """Manages document links and cross-references"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.broken_links: List[str] = []
        self.cross_references_added: List[Dict[str, Any]] = []
    
    def inspect_document_links(self, doc_path: Path) -> List[Dict[str, Any]]:
        """
        Inspect links in document
        
        Args:
            doc_path: Path to document to inspect
            
        Returns:
            List of {link_module, link_url, valid} dicts
        """
        if not doc_path.exists():
            return []
        
        link_list = []
        content = doc_path.read_text(encoding='utf-8')
        
        # Markdown link pattern: [link_module](link_url)
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        matches = re.findall(link_pattern, content)
        
        for link_module, link_url in matches:
            # Check if link is valid
            valid = False
            if link_url.startswith('http'):
                valid = True  # External link (assumed valid)
            else:
                # Local file link - check if exists
                link_path = doc_path.parent / link_url
                valid = link_path.exists()
            
            link_list.append({
                "link_module": link_module,
                "link_url": link_url,
                "valid": valid
            })
        
        return link_list
    
    def fix_broken_links(self, doc_path: Path, link_list: List[Dict[str, Any]]) -> int:
        """
        Fix broken links in document
        
        Args:
            doc_path: Path to document
            link_list: List of link information dicts
            
        Returns:
            Number of links fixed
        """
        if not doc_path.exists():
            return 0
        
        content = doc_path.read_text(encoding='utf-8')
        fixed_count = 0
        
        for link_info in link_list:
            if link_info["valid"]:
                continue
            
            link_module = link_info["link_module"]
            link_url = link_info["link_url"]
            
            # Try to find correct path
            corrected_url = self._find_correct_link_url(link_module, doc_path)
            
            if corrected_url:
                # Replace broken link
                old_link = f"[{link_module}]({link_url})"
                new_link = f"[{link_module}]({corrected_url})"
                content = content.replace(old_link, new_link)
                fixed_count += 1
                
                self.cross_references_added.append({
                    "from": str(doc_path),
                    "to": corrected_url,
                    "type": "link_fix"
                })
            else:
                self.broken_links.append(f"{doc_path}: {link_module} -> {link_url}")
        
        if fixed_count > 0:
            doc_path.write_text(content, encoding='utf-8')
        
        return fixed_count
    
    def _find_correct_link_url(self, link_module: str, current_doc: Path) -> Optional[str]:
        """Find correct URL for link module name"""
        # Search in common document directories
        search_dirs = [
            self.workspace_root / "docs_2",
            self.workspace_root / "docs_2" / "prd",
            self.workspace_root / ".github" / "agents" / "tool"
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            # Search for files matching link_module
            for file_path in search_dir.rglob("*.md"):
                if link_module.lower() in file_path.stem.lower():
                    # Return relative path from current document
                    try:
                        rel_path = file_path.relative_to(current_doc.parent)
                        return str(rel_path)
                    except ValueError:
                        # If can't make relative, use absolute
                        return str(file_path)
        
        return None
    
    def validate_and_fix_links(self, doc_path: Path) -> Dict[str, Any]:
        """
        Complete link validation and fixing operation
        
        Args:
            doc_path: Document path to process
            
        Returns:
            Result dict with success status and statistics
        """
        result = {
            "success": False,
            "links_inspected": 0,
            "links_fixed": 0,
            "broken_links": []
        }
        
        # Inspect links
        link_list = self.inspect_document_links(doc_path)
        result["links_inspected"] = len(link_list)
        
        # Fix broken links
        fixed_count = self.fix_broken_links(doc_path, link_list)
        result["links_fixed"] = fixed_count
        result["broken_links"] = self.broken_links.copy()
        result["success"] = True
        
        return result


__all__ = ["LinkManager"]
