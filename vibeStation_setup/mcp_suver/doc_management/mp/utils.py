"""
MP Utilities Module - Refactored with Nested Classes

Common utilities for MP (Mapping Table) operations.
Clean architecture with nested classes for related functionality.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .constants import (
    FileLimits,
    MPPatterns,
    MPScope,
    MPMetadataFields,
    MPConfig,
)


class FileOperations:
    """File I/O operations for MP files"""
    
    class Reader:
        """Read operations"""
        
        @staticmethod
        def read(file_path: Path) -> str:
            """Read file content"""
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            return file_path.read_text(encoding=MPConfig.FILE_ENCODING)
        
        @staticmethod
        def count_lines(file_path: Path) -> int:
            """Count lines in file"""
            if not file_path.exists():
                return 0
            return len(file_path.read_text(encoding=MPConfig.FILE_ENCODING).split('\n'))
        
        @staticmethod
        def extract_lines(content: str, start_line: int, end_line: int) -> str:
            """
            Extract lines from content.
            
            Args:
                content: File content
                start_line: Starting line (1-indexed)
                end_line: Ending line (1-indexed)
            """
            lines = content.split('\n')
            return '\n'.join(lines[start_line-1:end_line])
    
    class Writer:
        """Write operations"""
        
        @staticmethod
        def write(file_path: Path, content: str, create_backup: bool = True) -> None:
            """
            Write content to file with optional backup.
            
            Args:
                file_path: Target file path
                content: Content to write
                create_backup: Create timestamped backup
            """
            if create_backup and file_path.exists():
                backup_path = file_path.with_suffix(
                    f'.bak.{datetime.now().strftime("%Y%m%d%H%M%S")}'
                )
                backup_path.write_text(
                    file_path.read_text(encoding=MPConfig.FILE_ENCODING),
                    encoding=MPConfig.FILE_ENCODING
                )
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding=MPConfig.FILE_ENCODING)
    
    class Validator:
        """File validation"""
        
        @staticmethod
        def is_mp_file(file_path: Path) -> bool:
            """Check if file is MP file by pattern"""
            return bool(MPPatterns.FILE.search(str(file_path.name)))
        
        @staticmethod
        def is_extension_file(file_path: Path) -> bool:
            """Check if file is extension file"""
            return bool(MPPatterns.EXTENSION.search(str(file_path.name)))
        
        @staticmethod
        def check_size_limit(file_path: Path) -> Tuple[bool, int]:
            """
            Check if file exceeds line limit.
            
            Returns:
                (is_within_limit, line_count)
            """
            line_count = FileOperations.Reader.count_lines(file_path)
            return line_count <= FileLimits.MAX_LINES, line_count


class MetadataOperations:
    """Metadata extraction and manipulation"""
    
    class Extractor:
        """Extract metadata from content"""
        
        @staticmethod
        def extract_all(content: str) -> Dict[str, str]:
            """Extract all metadata fields"""
            metadata = {}
            lines = content.split('\n')
            
            # Look in first 50 lines for metadata
            for line in lines[:50]:
                match = re.match(r'\*\*([^*]+)\*\*:\s*(.+)', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    metadata[key] = value
            
            return metadata
        
        @staticmethod
        def extract_current_line(content: str) -> Optional[int]:
            """Extract Current line value"""
            match = MPPatterns.LINE_COUNT.search(content)
            if match:
                return int(match.group(1))
            return None
        
        @staticmethod
        def extract_purpose(content: str) -> Optional[str]:
            """Extract Purpose value"""
            match = MPPatterns.PURPOSE.search(content)
            if match:
                return match.group(1).strip()
            return None
        
        @staticmethod
        def extract_scope(content: str) -> Optional[str]:
            """Extract Scope value"""
            metadata = MetadataOperations.Extractor.extract_all(content)
            return metadata.get('Scope')
        
        @staticmethod
        def extract_type(content: str) -> Optional[str]:
            """Extract Type value"""
            match = MPPatterns.TYPE.search(content)
            if match:
                return match.group(1).strip()
            return None
    
    class Updater:
        """Update metadata in content"""
        
        @staticmethod
        def update_current_line(content: str, line_count: int) -> str:
            """Update Current line metadata"""
            replacement = f'**Current line**: {line_count}'
            
            if MPPatterns.LINE_COUNT.search(content):
                return MPPatterns.LINE_COUNT.sub(replacement, content)
            else:
                # Add after Purpose if not found
                if MPPatterns.PURPOSE.search(content):
                    return MPPatterns.PURPOSE.sub(
                        rf'\g<0>\n{replacement}',
                        content,
                        count=1
                    )
                # Add at beginning
                return f"{replacement}\n{content}"
    
    class Validator:
        """Validate metadata"""
        
        @staticmethod
        def validate_required(content: str) -> List[str]:
            """
            Check for required metadata fields.
            
            Returns:
                List of missing field names
            """
            metadata = MetadataOperations.Extractor.extract_all(content)
            missing = []
            
            for field in MPMetadataFields.REQUIRED:
                if field.name not in metadata:
                    missing.append(field.name)
            
            return missing
        
        @staticmethod
        def validate_scope(scope: str) -> bool:
            """Validate scope value"""
            return MPScope.is_valid(scope)


class SectionOperations:
    """Section extraction and manipulation"""
    
    class Extractor:
        """Extract sections from content"""
        
        @staticmethod
        def extract_all(content: str) -> List[Dict[str, any]]:
            """
            Extract all sections from content.
            
            Returns:
                List of section dictionaries with:
                - name: Section title
                - content: Section content
                - level: Heading level
                - line_start: Start line number
                - line_end: End line number
            """
            sections = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                match = MPPatterns.SECTION_MARKER.match(line)
                if match:
                    section_title = match.group(1).strip()
                    level_match = re.match(r'^(#+)', line)
                    level = len(level_match.group(1)) if level_match else 1
                    
                    start_line = i + 1  # 1-indexed
                    
                    # Find next section or end
                    end_line = len(lines)
                    for j in range(i + 1, len(lines)):
                        if MPPatterns.SECTION_MARKER.match(lines[j]):
                            end_line = j
                            break
                    
                    section_content = '\n'.join(lines[i+1:end_line])
                    
                    sections.append({
                        'name': section_title,
                        'content': section_content,
                        'level': level,
                        'line_start': start_line,
                        'line_end': end_line,
                    })
            
            return sections
        
        @staticmethod
        def extract_by_level(content: str, level: int) -> List[Dict[str, any]]:
            """Extract sections at specific heading level"""
            all_sections = SectionOperations.Extractor.extract_all(content)
            return [s for s in all_sections if s['level'] == level]
        
        @staticmethod
        def find_by_name(content: str, name: str) -> Optional[Dict[str, any]]:
            """Find section by name"""
            sections = SectionOperations.Extractor.extract_all(content)
            for section in sections:
                if section['name'] == name:
                    return section
            return None
    
    class Analyzer:
        """Analyze section content"""
        
        @staticmethod
        def count_sections(content: str) -> int:
            """Count total sections"""
            return len(SectionOperations.Extractor.extract_all(content))
        
        @staticmethod
        def get_section_line_counts(content: str) -> List[Tuple[str, int]]:
            """Get line count for each section"""
            sections = SectionOperations.Extractor.extract_all(content)
            return [
                (s['name'], s['line_end'] - s['line_start'] + 1)
                for s in sections
            ]
        
        @staticmethod
        def has_prose(content: str) -> bool:
            """Check if content contains prose"""
            for pattern in MPPatterns.PROSE:
                if pattern.search(content):
                    return True
            return False


class FlowOperations:
    """Flow diagram operations"""
    
    class Detector:
        """Detect flow diagrams"""
        
        @staticmethod
        def has_flow_diagram(content: str) -> bool:
            """Check if content contains flow diagram indicators"""
            return any(indicator in content for indicator in MPPatterns.FLOW_INDICATORS)
        
        @staticmethod
        def extract_flow_sections(content: str) -> List[Dict[str, any]]:
            """Extract sections that contain flow diagrams"""
            sections = SectionOperations.Extractor.extract_all(content)
            flow_sections = []
            
            for section in sections:
                if FlowOperations.Detector.has_flow_diagram(section['content']):
                    flow_sections.append(section)
            
            return flow_sections


class PathOperations:
    """Path and file name operations"""
    
    class Parser:
        """Parse MP file paths and names"""
        
        @staticmethod
        def extract_mp_number(file_path: Path) -> Optional[int]:
            """Extract MP number from filename"""
            match = re.search(r'MP-(\d+)-flow', str(file_path.name))
            if match:
                return int(match.group(1))
            return None
        
        @staticmethod
        def extract_extension_number(file_path: Path) -> Optional[int]:
            """Extract extension number from filename"""
            match = re.search(r'ext(\d+)', str(file_path.name))
            if match:
                return int(match.group(1))
            return None
    
    class Generator:
        """Generate MP file paths"""
        
        @staticmethod
        def create_mp_filename(mp_number: int) -> str:
            """Generate MP filename"""
            return f"MP-{mp_number}-flow.md"
        
        @staticmethod
        def create_extension_filename(mp_number: int, ext_number: int) -> str:
            """Generate extension filename"""
            return f"MP-{mp_number}-flow-ext{ext_number}.md"


class MPFileUtils:
    """Legacy compatibility - delegates to FileOperations"""
    read_file_content = FileOperations.Reader.read
    count_lines = FileOperations.Reader.count_lines
    write_file_content = FileOperations.Writer.write
    is_mp_file = FileOperations.Validator.is_mp_file
    extract_lines = FileOperations.Reader.extract_lines


class MetadataUtils:
    """Legacy compatibility - delegates to MetadataOperations"""
    extract_all_metadata = MetadataOperations.Extractor.extract_all
    extract_current_line = MetadataOperations.Extractor.extract_current_line
    extract_purpose = MetadataOperations.Extractor.extract_purpose
    extract_scope = MetadataOperations.Extractor.extract_scope
    update_current_line = MetadataOperations.Updater.update_current_line
    validate_required_metadata = MetadataOperations.Validator.validate_required


class SectionUtils:
    """Legacy compatibility - delegates to SectionOperations"""
    extract_sections = SectionOperations.Extractor.extract_all
