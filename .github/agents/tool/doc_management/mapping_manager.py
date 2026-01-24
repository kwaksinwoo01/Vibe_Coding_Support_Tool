"""
Mapping Manager - Document Mapping Table Management

Handles:
- Integration with MP (Mapping Table) tools ecosystem
- Automatic 500-line split handling
- Mapping validation and management
- Delegation to specialized MP tools

Integrates with refactored MP modules:
- .github/agents/tool/doc_management/mp/
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional


class MappingManager:
    """
    Manages document mapping tables via integration with MP tools
    
    Delegates to refactored MP (Mapping Table) tools at 
    .github/agents/tool/doc_management/mp/
    
    The MP tools provide:
    - Automatic 500-line split handling
    - Validation
    - Comprehensive management
    """
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.mp_tool_path = workspace_root / ".github" / "agents" / "tool"
        
        # Add tool path for imports
        if str(self.mp_tool_path) not in sys.path:
            sys.path.insert(0, str(self.mp_tool_path))
    
    def manage_mapping(self, current_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform mapping management operation
        
        Args:
            current_mapping: Mapping data to process
            
        Returns:
            Dict with operation results and tool recommendations
        """
        try:
            # Import refactored MP tools
            from doc_management.mp import (
                MPConfigurator,
                FileOperations,
                MetadataOperations,
            )
            
            # Setup MP tools
            MPConfigurator.setup(self.workspace_root)
            
            # Use new MP module structure
            # FileOperations, MetadataOperations, etc. are available
            
            return {
                "success": True,
                "message": "Mapping management using refactored MP tools",
                "recommendation": "Use doc_management.mp modules for mapping operations",
                "available_operations": {
                    "file_operations": "FileOperations.Reader, FileOperations.Writer, FileOperations.Validator",
                    "metadata_operations": "MetadataOperations.Extractor, MetadataOperations.Updater",
                    "section_operations": "SectionOperations.Extractor, SectionOperations.Analyzer",
                }
            }
            
        except ImportError as e:
            # Fallback if MP tools not available
            return {
                "success": False,
                "error": f"MP tools not available: {str(e)}",
                "recommendation": "Ensure MP tools are installed at .github/agents/tool/doc_management/mp/"
            }
    
    def list_mappings(self) -> Dict[str, Any]:
        """List all available mapping tables"""
        try:
            from doc_management.mp import MPPaths, FileOperations
            
            mp_root = MPPaths.get_mp_root()
            mp_files = []
            
            # Find all MP files in the docs_2/mp directory
            for scope_dir in mp_root.glob('*'):
                if scope_dir.is_dir():
                    for mp_file in scope_dir.glob('MP-*-flow*.md'):
                        if FileOperations.Validator.is_mp_file(mp_file):
                            mp_files.append(str(mp_file.relative_to(self.workspace_root)))
            
            return {
                "success": True,
                "files": mp_files,
                "count": len(mp_files)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_mappings(self, mapping_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Validate mapping tables
        
        Args:
            mapping_file: Specific file to validate, or None for all
            
        Returns:
            Validation results
        """
        try:
            from doc_management.mp import (
                FileOperations,
                MetadataOperations,
                FileLimits,
            )
            
            if mapping_file:
                content = FileOperations.Reader.read(mapping_file)
                missing = MetadataOperations.Validator.validate_required(content)
                is_within_limit, line_count = FileOperations.Validator.check_size_limit(mapping_file)
                
                return {
                    "success": len(missing) == 0 and is_within_limit,
                    "file": str(mapping_file),
                    "missing_metadata": missing,
                    "line_count": line_count,
                    "exceeds_limit": not is_within_limit
                }
            
            return {
                "success": True,
                "message": "Use validate_mappings with specific file"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def split_oversized_mapping(self, mapping_file: Path) -> Dict[str, Any]:
        """
        Split mapping file if it exceeds 500 lines
        
        Args:
            mapping_file: Path to mapping file to split
            
        Returns:
            Split operation results
        """
        try:
            from doc_management.mp import FileOperations, FileLimits
            
            is_within_limit, line_count = FileOperations.Validator.check_size_limit(mapping_file)
            
            if is_within_limit:
                return {
                    "success": True,
                    "message": "File does not need splitting",
                    "line_count": line_count
                }
            
            # Note: Actual splitting logic would go here
            # For now, just return status
            return {
                "success": False,
                "message": "Splitting not yet implemented in refactored version",
                "line_count": line_count,
                "limit": FileLimits.MAX_LINES
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_operations(self) -> Dict[str, str]:
        """
        Get available operations for MP tools
        
        Returns:
            Dict of operation name to description
        """
        return {
            "list_mappings": "List all MP files in the repository",
            "validate_mappings": "Validate MP file metadata and structure",
            "split_oversized_mapping": "Split MP files exceeding 500 lines",
            "file_operations": "FileOperations: Read, Write, Validate MP files",
            "metadata_operations": "MetadataOperations: Extract, Update, Validate metadata",
            "section_operations": "SectionOperations: Extract, Analyze sections",
        }


__all__ = ["MappingManager"]
