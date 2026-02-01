"""
Version Manager - Document Version Management

Handles:
- Version parsing and formatting (N1.N2.N3)
- Version incrementing
- Document version extraction and updates
- Parent/child document tracking
- Version notes
"""

import re
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional


class VersionManager:
    """Manages document versions following N1.N2.N3 format"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
    
    def parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """Parse version string (N1.N2.N3) to tuple"""
        try:
            parts = version_str.split('.')
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except:
            return (1, 0, 0)
    
    def increment_version(self, old_version: str, level: str) -> str:
        """
        Increment version based on level
        
        Args:
            old_version: Current version string
            level: 'N1', 'N2', or 'N3'
            
        Returns:
            New version string
        """
        n1, n2, n3 = self.parse_version(old_version)
        
        if level == 'N1':
            return f"{n1 + 1}.0.0"
        elif level == 'N2':
            return f"{n1}.{n2 + 1}.0"
        elif level == 'N3':
            return f"{n1}.{n2}.{n3 + 1}"
        else:
            return old_version
    
    def get_document_version(self, doc_path: Path) -> str:
        """Extract version from document"""
        if not doc_path.exists():
            return "1.0.0"
        
        content = doc_path.read_text(encoding='utf-8')
        version_pattern = r'\*\*Version\*\*:\s*(\d+\.\d+\.\d+)'
        match = re.search(version_pattern, content)
        
        if match:
            return match.group(1)
        return "1.0.0"
    
    def set_document_version(self, doc_path: Path, new_version: str) -> bool:
        """Update version in document"""
        if not doc_path.exists():
            return False
        
        content = doc_path.read_text(encoding='utf-8')
        version_pattern = r'(\*\*Version\*\*:\s*)(\d+\.\d+\.\d+)'
        
        if re.search(version_pattern, content):
            # Update existing version
            content = re.sub(version_pattern, rf'\g<1>{new_version}', content)
        else:
            # Add version if not exists (after WPD_grade line)
            grade_pattern = r'(\*\*WPD_grade\*\*:.*\n)'
            if re.search(grade_pattern, content):
                content = re.sub(grade_pattern, rf'\g<1>**Version**: {new_version}\n', content)
        
        doc_path.write_text(content, encoding='utf-8')
        return True
    
    def get_wpd_grade(self, doc_path: Path) -> str:
        """Extract WPD_grade from document"""
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
    
    def get_parent_documents(self, doc_path: Path) -> List[Path]:
        """Extract parent document paths from document"""
        if not doc_path.exists():
            return []
        
        content = doc_path.read_text(encoding='utf-8')
        parent_pattern = r'\*\*Parent\s+Documents?\*\*:\s*`([^`]+)`'
        matches = re.findall(parent_pattern, content)
        
        parent_paths = []
        for match in matches:
            parent_path = self.workspace_root / match
            if parent_path.exists():
                parent_paths.append(parent_path)
        
        return parent_paths
    
    def get_child_documents(self, doc_path: Path) -> List[Path]:
        """Extract child document paths from document"""
        if not doc_path.exists():
            return []
        
        content = doc_path.read_text(encoding='utf-8')
        child_pattern = r'\*\*Child\s+Documents?\*\*:\s*`([^`]+)`'
        matches = re.findall(child_pattern, content)
        
        child_paths = []
        for match in matches:
            child_path = self.workspace_root / match
            if child_path.exists():
                child_paths.append(child_path)
        
        return child_paths
    
    def update_version_for_tier_b(self, managed_doc_path: Path) -> Dict[str, Any]:
        """
        Version management for Tier B execution results
        
        Args:
            managed_doc_path: Document to update
            
        Returns:
            Result dict with old/new versions
        """
        result = {
            "success": False,
            "old_version": "1.0.0",
            "new_version": "1.0.0"
        }
        
        old_version = self.get_document_version(managed_doc_path)
        new_version = self.increment_version(old_version, 'N3')
        
        self.set_document_version(managed_doc_path, new_version)
        
        result["old_version"] = old_version
        result["new_version"] = new_version
        result["success"] = True
        
        return result
    
    def update_version_for_tier_c(self, point_doc_path: Path) -> Dict[str, Any]:
        """
        Version management for Tier C modifications
        
        Args:
            point_doc_path: Document being modified
            
        Returns:
            Result dict with version updates
        """
        result = {
            "success": False,
            "updated_documents": []
        }
        
        wpd_grade = self.get_wpd_grade(point_doc_path)
        
        if wpd_grade == "L3":
            # L3: Update self (N3+1) and parent L2 (N2+1)
            old_version_l3 = self.get_document_version(point_doc_path)
            new_version_l3 = self.increment_version(old_version_l3, 'N3')
            self.set_document_version(point_doc_path, new_version_l3)
            
            result["updated_documents"].append({
                "path": str(point_doc_path),
                "old_version": old_version_l3,
                "new_version": new_version_l3,
                "level": "L3"
            })
            
            # Update parent L2
            parents = self.get_parent_documents(point_doc_path)
            for parent_path in parents:
                if self.get_wpd_grade(parent_path) == "L2":
                    old_version_l2 = self.get_document_version(parent_path)
                    new_version_l2 = self.increment_version(old_version_l2, 'N2')
                    self.set_document_version(parent_path, new_version_l2)
                    self.add_version_note_to_parent(parent_path, point_doc_path, new_version_l3)
                    
                    result["updated_documents"].append({
                        "path": str(parent_path),
                        "old_version": old_version_l2,
                        "new_version": new_version_l2,
                        "level": "L2"
                    })
        
        elif wpd_grade == "L2":
            # L2: Update self (N2+1) and parent L1 (N1+1)
            old_version_l2 = self.get_document_version(point_doc_path)
            new_version_l2 = self.increment_version(old_version_l2, 'N2')
            self.set_document_version(point_doc_path, new_version_l2)
            
            result["updated_documents"].append({
                "path": str(point_doc_path),
                "old_version": old_version_l2,
                "new_version": new_version_l2,
                "level": "L2"
            })
            
            # Update parent L1
            parents = self.get_parent_documents(point_doc_path)
            for parent_path in parents:
                if self.get_wpd_grade(parent_path) == "L1":
                    old_version_l1 = self.get_document_version(parent_path)
                    new_version_l1 = self.increment_version(old_version_l1, 'N1')
                    self.set_document_version(parent_path, new_version_l1)
                    self.add_version_note_to_parent(parent_path, point_doc_path, new_version_l2)
                    
                    result["updated_documents"].append({
                        "path": str(parent_path),
                        "old_version": old_version_l1,
                        "new_version": new_version_l1,
                        "level": "L1"
                    })
        
        elif wpd_grade == "L1":
            # L1: Update self only (N1+1)
            old_version_l1 = self.get_document_version(point_doc_path)
            new_version_l1 = self.increment_version(old_version_l1, 'N1')
            self.set_document_version(point_doc_path, new_version_l1)
            
            result["updated_documents"].append({
                "path": str(point_doc_path),
                "old_version": old_version_l1,
                "new_version": new_version_l1,
                "level": "L1"
            })
        
        result["success"] = True
        return result
    
    def add_version_note_to_parent(self, parent_path: Path, child_path: Path, child_version: str):
        """Add version change note to parent document"""
        if not parent_path.exists():
            return
        
        content = parent_path.read_text(encoding='utf-8')
        
        # Add version note in a Version History section
        version_note = f"- Child document `{child_path.name}` updated to version {child_version}\n"
        
        # Find or create Version History section
        if "## Version History" in content:
            # Append to existing section
            content = content.replace("## Version History\n", f"## Version History\n{version_note}")
        else:
            # Add new section at end
            content += f"\n\n## Version History\n{version_note}"
        
        parent_path.write_text(content, encoding='utf-8')


__all__ = ["VersionManager"]
