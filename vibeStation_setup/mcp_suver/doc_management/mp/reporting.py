"""
MP Reporting Module - Refactored

Report generation and formatting for MP tools.
Clean architecture with nested classes for formatters.

DESTRUCTIVE REFACTOR: Dataclasses moved to models.core.reporting_models
- ValidationIssue, SyncResult, FileMetadata now imported from canonical models
- This module now only contains formatters and reporter logic

TODO(refactor-dataclasses): Verify all consumers import from canonical models
TODO(refactor-dataclasses): Remove this module if only used for backward compatibility
PR: copilot/refactor-dataclasses-centralization
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import sys
from pathlib import Path

# Import canonical dataclasses from models
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models.core.reporting_models import ValidationIssue, SyncResult, FileMetadata


# ============================================================================
# Report Format Enumeration
# ============================================================================

class ReportFormat(Enum):
    """Output format types"""
    JSON = "json"
    MARKDOWN = "markdown"
    CONSOLE = "console"
    GITHUB_COMMENT = "github_comment"


# ============================================================================
# Formatters
# ============================================================================

class Formatters:
    """Collection of output formatters"""
    
    class Markdown:
        """Markdown formatting"""
        
        @staticmethod
        def validation_table(issues: List[ValidationIssue]) -> str:
            """Format validation issues as markdown table"""
            if not issues:
                return "*No issues found*"
            
            lines = [
                "| File | Line | Severity | Message |",
                "| ------ | ------ | ------ | ------ |",
            ]
            
            for issue in issues:
                line_num = issue.line_number if issue.line_number else '-'
                severity_icon = {
                    'error': '❌',
                    'warning': '⚠️',
                    'info': 'ℹ️',
                }.get(issue.severity, '•')
                
                message = issue.message[:60] + '...' if len(issue.message) > 60 else issue.message
                
                lines.append(
                    f"| {issue.file_path} | {line_num} | "
                    f"{severity_icon} {issue.severity} | {message} |"
                )
            
            return "\n".join(lines)
        
        @staticmethod
        def section_list(sections: List[Dict[str, Any]]) -> str:
            """Format sections as markdown list"""
            if not sections:
                return "*No sections found*"
            
            lines = []
            for section in sections:
                indent = "  " * (section.get('level', 1) - 1)
                line_count = section.get('line_end', 0) - section.get('line_start', 0) + 1
                lines.append(f"{indent}- {section['name']} ({line_count} lines)")
            
            return "\n".join(lines)
        
        @staticmethod
        def metadata_summary(metadata: FileMetadata) -> str:
            """Format metadata as markdown"""
            lines = [
                f"**File**: {metadata.file_path}",
                f"**Purpose**: {metadata.purpose}",
                f"**Scope**: {metadata.scope}",
                f"**Lines**: {metadata.current_line}",
            ]
            
            if metadata.related_project:
                lines.append(f"**Related Project**: {metadata.related_project}")
            
            if metadata.is_oversized():
                lines.append("\n⚠️ **Warning**: File exceeds 500 line limit")
            
            return "\n".join(lines)
        
        @staticmethod
        def github_comment(
            summary: Dict[str, int],
            issues_by_file: Dict[str, List[ValidationIssue]],
            passed: bool
        ) -> str:
            """Format GitHub PR comment"""
            lines = []
            
            # Header
            icon = "✅" if passed else "❌"
            lines.append(f"## {icon} MP File Validation Report")
            lines.append("")
            
            # Summary
            lines.append("### Summary")
            lines.append(f"- **Total Issues**: {summary.get('total_issues', 0)}")
            lines.append(f"- **Errors**: {summary.get('error_count', 0)}")
            lines.append(f"- **Warnings**: {summary.get('warning_count', 0)}")
            lines.append(f"- **Files Checked**: {summary.get('files_checked', 0)}")
            lines.append("")
            
            # Issues by file
            if issues_by_file:
                lines.append("### Issues by File")
                for file_path, issues in issues_by_file.items():
                    lines.append(f"\n#### {file_path}")
                    lines.append(Formatters.Markdown.validation_table(issues))
            
            return "\n".join(lines)
    
    class Console:
        """Console formatting"""
        
        @staticmethod
        def validation_summary(issues: List[ValidationIssue]) -> str:
            """Format validation summary for console"""
            if not issues:
                return "✅ No issues found"
            
            errors = sum(1 for i in issues if i.is_error())
            warnings = sum(1 for i in issues if i.is_warning())
            
            lines = [
                "=" * 80,
                "VALIDATION SUMMARY",
                "=" * 80,
                f"Total Issues: {len(issues)}",
                f"Errors: {errors}",
                f"Warnings: {warnings}",
                "=" * 80,
            ]
            
            # Group by file
            by_file: Dict[str, List[ValidationIssue]] = {}
            for issue in issues:
                if issue.file_path not in by_file:
                    by_file[issue.file_path] = []
                by_file[issue.file_path].append(issue)
            
            for file_path, file_issues in by_file.items():
                lines.append(f"\n{file_path}:")
                for issue in file_issues:
                    icon = "❌" if issue.is_error() else "⚠️"
                    line_info = f":{issue.line_number}" if issue.line_number else ""
                    lines.append(f"  {icon} {issue.severity.upper()}{line_info}: {issue.message}")
            
            return "\n".join(lines)
    
    class JSON:
        """JSON formatting"""
        
        @staticmethod
        def validation_report(
            issues: List[ValidationIssue],
            summary: Dict[str, int],
            timestamp: datetime
        ) -> str:
            """Format validation report as JSON"""
            import json
            
            report = {
                'timestamp': timestamp.isoformat(),
                'summary': summary,
                'issues': [
                    {
                        'file_path': i.file_path,
                        'severity': i.severity,
                        'message': i.message,
                        'line_number': i.line_number,
                    }
                    for i in issues
                ],
            }
            
            return json.dumps(report, indent=2)


# ============================================================================
# Reporter
# ============================================================================

class Reporter:
    """
    Main reporting interface.
    Aggregates validation issues, sync results, and metadata.
    """
    
    def __init__(self, format: ReportFormat = ReportFormat.CONSOLE):
        """Initialize reporter"""
        self.format = format
        self.validation_issues: List[ValidationIssue] = []
        self.sync_results: List[SyncResult] = []
        self.metadata_list: List[FileMetadata] = []
        self.timestamp = datetime.now()
        self.context: Dict[str, Any] = {}
    
    def add_validation_issue(
        self,
        file_path: str,
        severity: str,
        message: str,
        line_number: Optional[int] = None
    ) -> None:
        """Add validation issue"""
        issue = ValidationIssue(
            file_path=file_path,
            severity=severity,
            message=message,
            line_number=line_number
        )
        self.validation_issues.append(issue)
    
    def add_sync_result(
        self,
        file_path: str,
        status: str,
        details: str = "",
        changes_count: int = 0
    ) -> None:
        """Add sync result"""
        result = SyncResult(
            file_path=file_path,
            status=status,
            details=details,
            changes_count=changes_count
        )
        self.sync_results.append(result)
    
    def add_metadata(
        self,
        file_path: str,
        purpose: str,
        scope: str,
        current_line: int,
        related_project: str = ""
    ) -> None:
        """Add file metadata"""
        metadata = FileMetadata(
            file_path=file_path,
            purpose=purpose,
            scope=scope,
            current_line=current_line,
            related_project=related_project
        )
        self.metadata_list.append(metadata)
    
    def set_context(self, key: str, value: Any) -> None:
        """Set context information"""
        self.context[key] = value
    
    def get_summary_stats(self) -> Dict[str, int]:
        """Calculate summary statistics"""
        return {
            'total_issues': len(self.validation_issues),
            'error_count': sum(1 for i in self.validation_issues if i.is_error()),
            'warning_count': sum(1 for i in self.validation_issues if i.is_warning()),
            'info_count': sum(1 for i in self.validation_issues if not i.is_error() and not i.is_warning()),
            'blocking_count': sum(1 for i in self.validation_issues if i.is_blocking()),
            'files_checked': len(set(i.file_path for i in self.validation_issues)),
            'sync_results_count': len(self.sync_results),
        }
    
    def has_blocking_issues(self) -> bool:
        """Check if there are blocking issues"""
        return any(i.is_blocking() for i in self.validation_issues)
    
    def generate_report(self) -> str:
        """Generate report in configured format"""
        summary = self.get_summary_stats()
        
        if self.format == ReportFormat.CONSOLE:
            return Formatters.Console.validation_summary(self.validation_issues)
        
        elif self.format == ReportFormat.MARKDOWN:
            issues_by_file: Dict[str, List[ValidationIssue]] = {}
            for issue in self.validation_issues:
                if issue.file_path not in issues_by_file:
                    issues_by_file[issue.file_path] = []
                issues_by_file[issue.file_path].append(issue)
            
            return Formatters.Markdown.github_comment(
                summary,
                issues_by_file,
                not self.has_blocking_issues()
            )
        
        elif self.format == ReportFormat.JSON:
            return Formatters.JSON.validation_report(
                self.validation_issues,
                summary,
                self.timestamp
            )
        
        else:
            return "Unsupported format"


# Legacy compatibility
MPReporter = Reporter
MarkdownFormatter = Formatters.Markdown
ConsoleFormatter = Formatters.Console
JSONFormatter = Formatters.JSON
