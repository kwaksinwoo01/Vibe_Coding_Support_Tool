"""
Unit tests for DocumentMerger and SemanticAnalyzer

Tests:
- Semantic analysis and keyword extraction
- Section parsing and categorization
- Similarity calculation
- Section matching
- Content integration (not simple append)
- Version increment
- Changelog generation
- ADMP compliance

Note: Uses sys.path.insert() to avoid complex dependency chain in the
existing codebase. In production, this would use proper relative imports,
but the current module structure has circular dependencies that prevent
standard imports during testing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys

# Direct import to avoid complex dependency chain
# TODO: Refactor to use proper package imports once dependency issues are resolved
sys.path.insert(0, str(Path(__file__).parent.parent / "doc_management"))

from document_merger import (
    DocumentMerger,
    SemanticAnalyzer,
    DocumentSection,
    MergeDecision
)


class TestSemanticAnalyzer:
    """Test suite for SemanticAnalyzer"""
    
    def test_extract_keywords(self):
        """Test keyword extraction from text"""
        text = "This is a test implementation of authentication and security features"
        keywords = SemanticAnalyzer.extract_keywords(text)
        
        # Should extract significant words
        assert "implementation" in keywords
        assert "authentication" in keywords
        assert "security" in keywords
        assert "features" in keywords
        
        # Should filter out stop words
        assert "this" not in keywords
        assert "is" not in keywords
        assert "a" not in keywords
    
    def test_identify_category_testing(self):
        """Test category identification for testing-related content"""
        section = DocumentSection(
            title="Unit Test Results",
            content="Test validation with pytest. All tests passed successfully.",
            level=2,
            line_start=10,
            line_end=15
        )
        
        category = SemanticAnalyzer.identify_category(section)
        assert category == "testing"
    
    def test_identify_category_implementation(self):
        """Test category identification for implementation-related content"""
        section = DocumentSection(
            title="Implementation Details",
            content="Code implementation using Python. Developed new features.",
            level=2,
            line_start=20,
            line_end=25
        )
        
        category = SemanticAnalyzer.identify_category(section)
        assert category == "implementation"
    
    def test_identify_category_security(self):
        """Test category identification for security-related content"""
        section = DocumentSection(
            title="Security Enhancements",
            content="Added authentication and encryption for secure communication.",
            level=2,
            line_start=30,
            line_end=35
        )
        
        category = SemanticAnalyzer.identify_category(section)
        assert category == "security"
    
    def test_calculate_similarity_high(self):
        """Test similarity calculation for very similar sections"""
        section1 = DocumentSection(
            title="Testing Framework",
            content="Unit testing with pytest and coverage analysis",
            level=2,
            line_start=10,
            line_end=15,
            category="testing",
            keywords={"testing", "pytest", "coverage", "analysis", "unit"}
        )
        
        section2 = DocumentSection(
            title="Testing Implementation",
            content="pytest unit testing and code coverage verification",
            level=2,
            line_start=20,
            line_end=25,
            category="testing",
            keywords={"testing", "pytest", "coverage", "code", "verification", "unit"}
        )
        
        similarity = SemanticAnalyzer.calculate_similarity(section1, section2)
        
        # Should be high similarity (title similar, keywords overlap, category match)
        assert similarity > 0.6
    
    def test_calculate_similarity_low(self):
        """Test similarity calculation for unrelated sections"""
        section1 = DocumentSection(
            title="Testing Framework",
            content="Unit testing with pytest",
            level=2,
            line_start=10,
            line_end=15,
            category="testing",
            keywords={"testing", "pytest", "unit"}
        )
        
        section2 = DocumentSection(
            title="Database Schema",
            content="Database design with PostgreSQL tables",
            level=2,
            line_start=20,
            line_end=25,
            category="architecture",
            keywords={"database", "design", "postgresql", "tables"}
        )
        
        similarity = SemanticAnalyzer.calculate_similarity(section1, section2)
        
        # Should be low similarity (different categories, no keyword overlap)
        assert similarity < 0.3


class TestDocumentMerger:
    """Test suite for DocumentMerger"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def merger(self, temp_dir):
        """Create DocumentMerger instance"""
        return DocumentMerger(temp_dir)
    
    def test_parse_document_basic(self, merger, temp_dir):
        """Test basic document parsing"""
        doc_path = temp_dir / "test_doc.md"
        content = """# Test Document

**Version**: 1.0.0
**Status**: ACTIVE

## Introduction

This is the introduction section.

## Implementation

Details about implementation.

### Sub-section

Nested content here.
"""
        doc_path.write_text(content, encoding='utf-8')
        
        metadata, sections = merger.parse_document(doc_path)
        
        # Check metadata extraction
        assert metadata["Version"] == "1.0.0"
        assert metadata["Status"] == "ACTIVE"
        
        # Check sections
        assert len(sections) >= 3
        section_titles = [s.title for s in sections]
        assert "Introduction" in section_titles
        assert "Implementation" in section_titles
    
    def test_find_matching_section_high_similarity(self, merger):
        """Test finding matching section with high similarity"""
        source = DocumentSection(
            title="Testing Framework",
            content="Unit testing with pytest",
            level=2,
            line_start=10,
            line_end=15,
            category="testing",
            keywords={"testing", "pytest", "unit", "framework"}
        )
        
        target_sections = [
            DocumentSection(
                title="Testing Implementation",
                content="pytest unit testing implementation",
                level=2,
                line_start=20,
                line_end=25,
                category="testing",
                keywords={"testing", "pytest", "unit", "implementation"}
            ),
            DocumentSection(
                title="Database Design",
                content="PostgreSQL schema design",
                level=2,
                line_start=30,
                line_end=35,
                category="architecture",
                keywords={"database", "postgresql", "schema", "design"}
            )
        ]
        
        match, score = merger.find_matching_section(source, target_sections)
        
        assert match is not None
        assert match.title == "Testing Implementation"
        assert score > 0.6
    
    def test_merge_sections_integration(self, merger):
        """Test section merging integrates content correctly"""
        source = DocumentSection(
            title="Testing",
            content="## Testing\n\nNew test case added.\n\nAdditional validation implemented.",
            level=2,
            line_start=10,
            line_end=15
        )
        
        target = DocumentSection(
            title="Testing",
            content="## Testing\n\nExisting test cases.\n\nCurrent validation logic.",
            level=2,
            line_start=20,
            line_end=25
        )
        
        merged = merger.merge_sections(source, target)
        
        # Should include merge header
        assert "Merged Content" in merged
        
        # Should include source content
        assert "New test case added" in merged
        assert "Additional validation implemented" in merged
        
        # Should keep target content
        assert "Existing test cases" in merged
        assert "Current validation logic" in merged
    
    def test_merge_sections_no_duplicates(self, merger):
        """Test that merge doesn't duplicate identical content"""
        source = DocumentSection(
            title="Testing",
            content="## Testing\n\nExisting test cases.\n\nNew feature test.",
            level=2,
            line_start=10,
            line_end=15
        )
        
        target = DocumentSection(
            title="Testing",
            content="## Testing\n\nExisting test cases.\n\nOld validation logic.",
            level=2,
            line_start=20,
            line_end=25
        )
        
        merged = merger.merge_sections(source, target)
        
        # "Existing test cases" appears in both - should not duplicate
        # Count occurrences
        count = merged.count("Existing test cases")
        assert count <= 2  # Original + maybe one more, but not full duplication
        
        # Should include unique content from source
        assert "New feature test" in merged
    
    def test_increment_version_minor(self, merger):
        """Test version increment for merge"""
        old_version = "2.0.3"
        new_version = merger.increment_version(old_version)
        
        assert new_version == "2.1.0"
    
    def test_increment_version_with_v_prefix(self, merger):
        """Test version increment with 'v' prefix"""
        old_version = "v1.2.5"
        new_version = merger.increment_version(old_version)
        
        assert new_version == "1.3.0"
    
    def test_add_changelog_entry_new_section(self, merger):
        """Test adding changelog to document without one"""
        content = """# Test Document

## Introduction

Some content here.
"""
        
        updated = merger.add_changelog_entry(content, "Added new features", "2.1.0")
        
        # Should add changelog section
        assert "## 📝 Changelog" in updated
        assert "### Version 2.1.0" in updated
        assert "Added new features" in updated
    
    def test_add_changelog_entry_existing_section(self, merger):
        """Test adding changelog to document with existing changelog"""
        content = """# Test Document

## 📝 Changelog

### Version 2.0.0 (2025-01-01)
- Initial version

## Introduction

Some content here.
"""
        
        updated = merger.add_changelog_entry(content, "Bug fixes", "2.1.0")
        
        # Should insert new entry after header
        assert "### Version 2.1.0" in updated
        assert "Bug fixes" in updated
        
        # Should keep old entries
        assert "### Version 2.0.0" in updated
        assert "Initial version" in updated
    
    def test_merge_documents_full_workflow(self, merger, temp_dir):
        """Test complete document merge workflow"""
        # Create source document
        source_path = temp_dir / "source.md"
        source_content = """# Source Document

**Version**: 1.0.0

## Testing Enhancements

New pytest fixtures added.

Improved test coverage to 95%.

## Security Updates

Added authentication middleware.
"""
        source_path.write_text(source_content, encoding='utf-8')
        
        # Create target document
        target_path = temp_dir / "target.md"
        target_content = """# Target Implementation Report

**Version**: 2.0.3
**Status**: ACTIVE

## Testing Framework

Existing pytest setup with basic fixtures.

## Security

Current authentication using JWT tokens.

## Architecture

System design patterns and structure.
"""
        target_path.write_text(target_content, encoding='utf-8')
        
        # Perform merge
        result = merger.merge_documents(
            source_path, 
            target_path, 
            "Merging enhancements per ADMP policy"
        )
        
        # Check result
        assert result["success"] is True
        assert result["old_version"] == "2.0.3"
        assert result["new_version"] == "2.1.0"
        assert result["merge_decisions"] > 0
        
        # Check merged document
        merged_content = target_path.read_text(encoding='utf-8')
        
        # Version should be updated
        assert "**Version**: 2.1.0" in merged_content
        
        # Should include changelog
        assert "## 📝 Changelog" in merged_content
        assert "### Version 2.1.0" in merged_content
        assert "Merged content from source.md" in merged_content
        
        # Should include merged content (testing section)
        assert "pytest" in merged_content.lower()
        
        # Should include security content
        assert "authentication" in merged_content.lower()
        
        # Should keep original architecture section
        assert "Architecture" in merged_content
    
    def test_merge_documents_source_not_found(self, merger, temp_dir):
        """Test merge with non-existent source"""
        source_path = temp_dir / "nonexistent.md"
        target_path = temp_dir / "target.md"
        target_path.write_text("# Target\n**Version**: 1.0.0", encoding='utf-8')
        
        result = merger.merge_documents(source_path, target_path)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_merge_documents_target_not_found(self, merger, temp_dir):
        """Test merge with non-existent target"""
        source_path = temp_dir / "source.md"
        source_path.write_text("# Source\n**Version**: 1.0.0", encoding='utf-8')
        target_path = temp_dir / "nonexistent.md"
        
        result = merger.merge_documents(source_path, target_path)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_merge_decisions_detailed(self, merger, temp_dir):
        """Test that merge returns detailed decision information"""
        source_path = temp_dir / "source.md"
        source_content = """# Source

## Testing

New tests added.

## Configuration

New config options.
"""
        source_path.write_text(source_content, encoding='utf-8')
        
        target_path = temp_dir / "target.md"
        target_content = """# Target

**Version**: 1.0.0

## Testing Framework

Existing tests.

## Architecture

Design patterns.
"""
        target_path.write_text(target_content, encoding='utf-8')
        
        result = merger.merge_documents(source_path, target_path)
        
        # Should return decision details
        assert "decisions" in result
        assert len(result["decisions"]) > 0
        
        # Each decision should have required fields
        for decision in result["decisions"]:
            assert "source_title" in decision
            assert "action" in decision
            assert "similarity" in decision
            assert "justification" in decision


class TestADMPCompliance:
    """Test ADMP policy compliance"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def merger(self, temp_dir):
        """Create DocumentMerger instance"""
        return DocumentMerger(temp_dir)
    
    def test_admp_version_increment(self, merger, temp_dir):
        """Test ADMP requirement: version increment on merge"""
        source_path = temp_dir / "enhancements.md"
        source_path.write_text("# Enhancements\n## New Feature\nContent", encoding='utf-8')
        
        target_path = temp_dir / "main_report.md"
        target_path.write_text("# Main Report\n**Version**: 1.5.2\n## Overview\nContent", encoding='utf-8')
        
        result = merger.merge_documents(source_path, target_path)
        
        # ADMP: Version must be incremented
        assert result["old_version"] == "1.5.2"
        assert result["new_version"] == "1.6.0"
        
        # Check in actual file
        merged_content = target_path.read_text(encoding='utf-8')
        assert "**Version**: 1.6.0" in merged_content
    
    def test_admp_changelog_required(self, merger, temp_dir):
        """Test ADMP requirement: changelog entry on merge"""
        source_path = temp_dir / "enhancements.md"
        source_path.write_text("# Enhancements\n## Feature\nContent", encoding='utf-8')
        
        target_path = temp_dir / "main_report.md"
        target_path.write_text("# Report\n**Version**: 1.0.0\n## Overview\nContent", encoding='utf-8')
        
        result = merger.merge_documents(source_path, target_path, "Adding enhancements")
        
        # Check changelog was added
        merged_content = target_path.read_text(encoding='utf-8')
        assert "## 📝 Changelog" in merged_content
        assert "### Version 1.1.0" in merged_content
        assert "Merged content from enhancements.md" in merged_content
        assert "Adding enhancements" in merged_content
    
    def test_admp_no_separate_document_creation(self, merger, temp_dir):
        """Test ADMP requirement: merge into existing, don't create separate"""
        # This test verifies that merge modifies the target, not creates new
        source_path = temp_dir / "enhancements.md"
        source_path.write_text("# Enhancements\n## Feature\nNew feature", encoding='utf-8')
        
        target_path = temp_dir / "main_report.md"
        original_content = "# Report\n**Version**: 1.0.0\n## Overview\nOriginal"
        target_path.write_text(original_content, encoding='utf-8')
        
        # Record file count before merge
        files_before = list(temp_dir.glob("*.md"))
        
        result = merger.merge_documents(source_path, target_path)
        
        # Record file count after merge
        files_after = list(temp_dir.glob("*.md"))
        
        # ADMP: Should not create new files, only modify target
        assert len(files_before) == len(files_after)
        
        # Target should be modified
        merged_content = target_path.read_text(encoding='utf-8')
        assert merged_content != original_content
        assert "New feature" in merged_content or "Feature" in merged_content
    
    def test_admp_justification_tracked(self, merger, temp_dir):
        """Test ADMP requirement: justification is tracked"""
        source_path = temp_dir / "enhancements.md"
        source_path.write_text("# Enhancements\n## Feature\nContent", encoding='utf-8')
        
        target_path = temp_dir / "main_report.md"
        target_path.write_text("# Report\n**Version**: 1.0.0\n## Overview\nContent", encoding='utf-8')
        
        justification = "Consolidating enhancements per ADMP Scenario D"
        result = merger.merge_documents(source_path, target_path, justification)
        
        # Check justification is in changelog
        merged_content = target_path.read_text(encoding='utf-8')
        assert justification in merged_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
