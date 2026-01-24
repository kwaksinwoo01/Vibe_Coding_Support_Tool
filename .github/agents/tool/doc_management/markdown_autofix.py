"""
Markdown Autofix Manager

Automatically fixes common markdownlint warnings in markdown documents.
Follows Single Responsibility Principle with nested classes for functionality separation.

**Handles**:
- MD022: Blank lines around headings
- MD024: Duplicate heading content (contextual suffixing)
- MD029: Ordered list prefixes
- MD031: Blank lines around fenced code blocks
- MD032: Blank lines around lists
- MD034: Bare URLs
- MD012: Multiple blank lines

**Architecture**: Nested classes for rule-specific fixes
**Integration**: Called from E_Document_Management.py for document formatting
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FixResult:
    """Result of applying markdown fixes to a file"""
    changed: bool
    rules_applied: List[str] = field(default_factory=list)
    changes_count: int = 0
    
    def add_change(self, rule: str, count: int) -> None:
        """Add a change to the result"""
        if count > 0:
            self.rules_applied.append(f"{rule}: {count} changes")
            self.changes_count += count
            self.changed = True


@dataclass
class MarkdownDocument:
    """Represents a markdown document"""
    path: Path
    lines: List[str]
    
    @classmethod
    def load(cls, path: Path) -> 'MarkdownDocument':
        """Load markdown document from file"""
        content = path.read_text(encoding='utf-8')
        lines = content.split('\n')
        # Preserve line endings
        lines = [line + '\n' if i < len(lines) - 1 or content.endswith('\n') else line
                 for i, line in enumerate(lines)]
        return cls(path=path, lines=lines)
    
    def save(self, create_backup: bool = True) -> None:
        """Save document to file with optional backup"""
        if create_backup:
            backup_path = self.path.with_suffix(self.path.suffix + '.bak')
            if not backup_path.exists():
                backup_path.write_text(self.get_content(), encoding='utf-8')
        
        self.path.write_text(self.get_content(), encoding='utf-8')
    
    def get_content(self) -> str:
        """Get document content as string"""
        return ''.join(self.lines)


# ============================================================================
# Pattern Constants
# ============================================================================

class Patterns:
    """Compiled regex patterns for markdown elements"""
    HEADING = re.compile(r'^(#{1,6})\s+(.*)\s*$')
    ORDERED_ITEM = re.compile(r'^(\s*)(\d+)\.(\s+.*)$')
    FENCE = re.compile(r'^(`{3,}|~{3,})(.*)$')
    LIST_ITEM = re.compile(r'^(\s*)[-*+](\s+.*)$')
    BARE_URL = re.compile(r'(?<![<\[\(])https?://[^\s<>\[\]()]+(?![>\]\)])')


# ============================================================================
# Rule Fixers (Nested Classes)
# ============================================================================

class MarkdownRules:
    """Collection of markdown rule fixers"""
    
    class MD029:
        """Fix ordered list prefixes - normalize to '1.' consistently"""
        
        @staticmethod
        def fix(lines: List[str]) -> Tuple[List[str], int]:
            """Convert all ordered list items to use '1.' prefix"""
            changed = 0
            out = []
            for ln in lines:
                m = Patterns.ORDERED_ITEM.match(ln)
                if m:
                    leading, num, rest = m.groups()
                    if num != '1':
                        out.append(f"{leading}1.{rest}\n")
                        changed += 1
                        continue
                out.append(ln)
            return out, changed
    
    class MD031:
        """Ensure blank lines around fenced code blocks"""
        
        @staticmethod
        def fix(lines: List[str]) -> Tuple[List[str], int]:
            """Add blank lines before/after code fences if missing"""
            out = []
            changed = 0
            i = 0
            n = len(lines)
            in_fence = False
            fence_marker = None
            
            while i < n:
                ln = lines[i]
                m = Patterns.FENCE.match(ln.rstrip('\n'))
                
                if m and not in_fence:
                    # Opening fence
                    fence_marker = m.group(1)
                    # Ensure previous line is blank
                    if out and out[-1].strip() != '':
                        out.append('\n')
                        changed += 1
                    out.append(ln)
                    in_fence = True
                    i += 1
                    
                elif m and in_fence and m.group(1).startswith(fence_marker[:1]):
                    # Closing fence
                    out.append(ln)
                    in_fence = False
                    # Ensure next line is blank
                    if i + 1 < n and lines[i + 1].strip() != '':
                        out.append('\n')
                        changed += 1
                    i += 1
                    
                else:
                    out.append(ln)
                    i += 1
            
            return out, changed
    
    class MD012:
        """Collapse multiple consecutive blank lines to single blank line"""
        
        @staticmethod
        def fix(lines: List[str]) -> Tuple[List[str], int]:
            """Remove excessive blank lines"""
            out = []
            changed = 0
            blank_run = 0
            
            for ln in lines:
                if ln.strip() == '':
                    blank_run += 1
                    if blank_run == 1:
                        out.append(ln)
                    else:
                        changed += 1
                else:
                    blank_run = 0
                    out.append(ln)
            
            return out, changed
    
    class MD022:
        """Ensure blank lines around headings"""
        
        @staticmethod
        def fix(lines: List[str]) -> Tuple[List[str], int]:
            """Add a blank line before and after headings where missing"""
            out = []
            changed = 0
            i = 0
            n = len(lines)

            while i < n:
                ln = lines[i]
                m = Patterns.HEADING.match(ln.rstrip('\n'))
                if m:
                    # Ensure blank line before
                    if out and out[-1].strip() != '':
                        out.append('\n')
                        changed += 1
                    out.append(ln)
                    # Ensure blank line after
                    if i + 1 < n and lines[i + 1].strip() != '':
                        out.append('\n')
                        changed += 1
                    i += 1
                else:
                    out.append(ln)
                    i += 1

            return out, changed

    class MD024:
        """Fix duplicate heading content by appending contextual suffix"""
        
        @staticmethod
        def fix(lines: List[str]) -> Tuple[List[str], int]:
            """Make duplicate headings unique by appending a short contextual suffix.

            Strategy:
            - If a heading text repeats, attempt to find the nearest previous heading
              (above the current line) whose text differs; use that as context.
            - If no context is found, fall back to numeric suffix as an escape.
            - Keep context short (truncate to 40 chars) and strip problematic chars.
            """
            heading_counts: Dict[str, int] = {}
            out = []
            changed = 0
            
            for i, ln in enumerate(lines):
                m = Patterns.HEADING.match(ln.rstrip('\n'))
                if m:
                    level, text = m.groups()
                    key = text.strip().lower()

                    if key in heading_counts:
                        heading_counts[key] += 1
                        # find nearest previous heading with different text
                        parent_text = None
                        for j in range(i - 1, -1, -1):
                            pm = Patterns.HEADING.match(lines[j].rstrip('\n'))
                            if pm:
                                _, p_text = pm.groups()
                                p_text_str = p_text.strip()
                                if p_text_str and p_text_str.lower() != key:
                                    parent_text = p_text_str
                                    break

                        if parent_text:
                            # prefer the part after ':' if present, otherwise the whole parent
                            if ':' in parent_text:
                                parts = parent_text.split(':', 1)
                                context = parts[1].strip() or parts[0].strip()
                            else:
                                context = parent_text

                            # sanitize and truncate
                            context = re.sub(r"[\r\n()]","", context).strip()
                            if len(context) > 40:
                                context = context[:37] + '...'

                            suffix_text = f"{text} ({context})"
                        else:
                            # fallback to numeric suffix
                            suffix_text = f"{text} ({heading_counts[key]})"

                        out.append(f"{level} {suffix_text}\n")
                        changed += 1
                    else:
                        heading_counts[key] = 1
                        out.append(ln)
                else:
                    out.append(ln)
            
            return out, changed
    
    class MD032:
        """Ensure lists are surrounded by blank lines"""
        
        @staticmethod
        def fix(lines: List[str]) -> Tuple[List[str], int]:
            """Add blank lines before/after lists"""
            out = []
            changed = 0
            i = 0
            n = len(lines)
            
            while i < n:
                ln = lines[i]
                is_list = (Patterns.LIST_ITEM.match(ln) is not None or 
                          Patterns.ORDERED_ITEM.match(ln) is not None)
                
                if is_list:
                    # Check if we need blank line before
                    if out and out[-1].strip() != '':
                        out.append('\n')
                        changed += 1
                    
                    # Add all consecutive list items
                    while i < n and (Patterns.LIST_ITEM.match(lines[i]) or 
                                    Patterns.ORDERED_ITEM.match(lines[i])):
                        out.append(lines[i])
                        i += 1
                    
                    # Check if we need blank line after
                    if i < n and lines[i].strip() != '':
                        out.append('\n')
                        changed += 1
                else:
                    out.append(ln)
                    i += 1
            
            return out, changed
    
    class MD034:
        """Wrap bare URLs in angle brackets"""
        
        @staticmethod
        def fix(lines: List[str]) -> Tuple[List[str], int]:
            """Wrap unformatted URLs with <> brackets"""
            changed = 0
            out = []
            
            for ln in lines:
                original = ln
                # Replace all bare URLs with <URL>
                ln = Patterns.BARE_URL.sub(lambda m: f'<{m.group(0)}>', ln)
                if ln != original:
                    changed += 1
                out.append(ln)
            
            return out, changed


# ============================================================================
# Main Processor
# ============================================================================

class MarkdownAutofix:
    """
    Markdown autofix processor.
    
    Applies fixes for common markdownlint warnings following SRP.
    Each rule has its own nested class with a single fix method.
    """
    
    # Maximum passes for MD012 stabilization
    MAX_STABILIZATION_PASSES = 5
    
    def __init__(self, workspace_root: Path):
        """Initialize with workspace root"""
        self.workspace_root = workspace_root
    
    def process_file(self, file_path: Path, apply: bool = False) -> FixResult:
        """
        Process a single markdown file.
        
        Args:
            file_path: Path to markdown file
            apply: If True, write changes to file; if False, dry-run
            
        Returns:
            FixResult with details of changes made
        """
        # Load document
        doc = MarkdownDocument.load(file_path)
        lines = doc.lines
        
        result = FixResult(changed=False)
        
        # Apply MD012 initial pass
        lines, count = MarkdownRules.MD012.fix(lines)
        if count > 0:
            result.add_change("MD012_initial", count)
        
        # Apply MD029 (ordered lists)
        lines, count = MarkdownRules.MD029.fix(lines)
        if count > 0:
            result.add_change("MD029", count)
        
        # Apply MD031 (blank lines around fences)
        lines, count = MarkdownRules.MD031.fix(lines)
        if count > 0:
            result.add_change("MD031", count)
        
        # Apply MD022 (blank lines around headings)
        lines, count = MarkdownRules.MD022.fix(lines)
        if count > 0:
            result.add_change("MD022", count)
        
        # Apply MD032 (blank lines around lists)
        lines, count = MarkdownRules.MD032.fix(lines)
        if count > 0:
            result.add_change("MD032", count)
        
        # Apply MD034 (bare URLs)
        lines, count = MarkdownRules.MD034.fix(lines)
        if count > 0:
            result.add_change("MD034", count)
        
        # Apply MD024 (duplicate headings)
        lines, count = MarkdownRules.MD024.fix(lines)
        if count > 0:
            result.add_change("MD024", count)
        
        # Stabilization passes for MD012
        for pass_num in range(self.MAX_STABILIZATION_PASSES):
            lines, count = MarkdownRules.MD012.fix(lines)
            if count > 0:
                result.add_change(f"MD012_pass{pass_num + 1}", count)
            else:
                break
        
        # Apply changes if requested
        if result.changed and apply:
            doc.lines = lines
            doc.save(create_backup=True)
        
        return result
    
    def process_directory(self, dir_path: Path, apply: bool = False) -> Dict[str, FixResult]:
        """
        Process all markdown files in a directory recursively.
        
        Args:
            dir_path: Directory to process
            apply: If True, write changes; if False, dry-run
            
        Returns:
            Dict mapping file paths to FixResult
        """
        results = {}
        
        for md_file in self._find_markdown_files(dir_path):
            result = self.process_file(md_file, apply=apply)
            if result.changed:
                results[str(md_file)] = result
        
        return results
    
    def _find_markdown_files(self, root: Path) -> List[Path]:
        """Find all markdown files in directory, excluding common generated paths"""
        files = []
        
        if root.is_file():
            if root.suffix.lower() in ('.md', '.markdown'):
                files.append(root)
            return files
        
        for p in root.rglob('*.md'):
            # Skip virtual environments and other generated content
            path_str = str(p)
            if any(skip in path_str for skip in ['/.venv/', '\\.venv\\', '/node_modules/', '\\node_modules\\']):
                continue
            files.append(p)
        
        return files


# ============================================================================
# Facade for E_Document_Management Integration
# ============================================================================

class MarkdownAutofixManager:
    """
    Facade for markdown autofix operations.
    
    Integrates with E_Document_Management.py following the same pattern
    as other document managers (LinkManager, VersionManager, etc.)
    """
    
    def __init__(self, workspace_root: Path):
        """Initialize manager"""
        self.workspace_root = workspace_root
        self.processor = MarkdownAutofix(workspace_root)
    
    def fix_document(self, doc_path: Path, apply: bool = False) -> Dict[str, Any]:
        """
        Fix markdown issues in a document.
        
        Args:
            doc_path: Path to markdown document
            apply: Whether to apply changes (True) or dry-run (False)
            
        Returns:
            Dict with fix results
        """
        if not doc_path.exists():
            return {
                "success": False,
                "error": f"File not found: {doc_path}"
            }
        
        result = self.processor.process_file(doc_path, apply=apply)
        
        return {
            "success": True,
            "changed": result.changed,
            "rules_applied": result.rules_applied,
            "changes_count": result.changes_count,
            "file": str(doc_path),
            "applied": apply
        }
    
    def fix_directory(self, dir_path: Path, apply: bool = False) -> Dict[str, Any]:
        """
        Fix markdown issues in all files in a directory.
        
        Args:
            dir_path: Directory path
            apply: Whether to apply changes
            
        Returns:
            Dict with fix results for all files
        """
        if not dir_path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {dir_path}"
            }
        
        results = self.processor.process_directory(dir_path, apply=apply)
        
        total_files = len(results)
        total_changes = sum(r.changes_count for r in results.values())
        
        return {
            "success": True,
            "files_processed": total_files,
            "total_changes": total_changes,
            "files": {path: {
                "rules_applied": result.rules_applied,
                "changes_count": result.changes_count
            } for path, result in results.items()},
            "applied": apply
        }


__all__ = [
    'MarkdownAutofixManager',
    'MarkdownAutofix',
    'MarkdownRules',
    'FixResult',
    'MarkdownDocument',
]
