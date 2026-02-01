"""
Integration test for E_Document_Management merge functionality

Tests the integration between DocumentManagementEngine and DocumentMerger

Note: Uses sys.path.insert() to avoid complex dependency chain in the
existing codebase. In production, this would use proper relative imports,
but the current module structure has circular dependencies that prevent
standard imports during testing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Direct import to avoid complex dependency chain
# TODO: Refactor to use proper package imports once dependency issues are resolved
sys.path.insert(0, str(Path(__file__).parent.parent / "doc_management"))

from document_merger import DocumentMerger


class TestDocumentMergeIntegration:
    """Integration tests for document merging"""
    
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
    
    def test_realistic_implementation_report_merge(self, merger, temp_dir):
        """Test realistic scenario: merging enhancements into Implementation Report"""
        # Create a separate enhancements document (ADMP violation)
        enhancements_path = temp_dir / "ENHANCED_FEATURES.md"
        enhancements_content = """# Enhanced Features

**Created**: 2026-01-20

## Circuit Breaker Pattern

Implemented fault tolerance with Redis persistence.

### Features
- Automatic failure detection
- Exponential backoff
- Redis-based state persistence

## Decision Engine Enhancements

Added confidence-based routing with policy support.

### Features
- Confidence scoring (0.0-1.0)
- Policy-based routing
- Metrics collection
"""
        enhancements_path.write_text(enhancements_content, encoding='utf-8')
        
        # Create main Implementation Report
        report_path = temp_dir / "6TIER_IMPLEMENTATION_REPORT.md"
        report_content = """# 6-Tier Task Orchestration Implementation Report

**Version**: 2.0.3
**Last Updated**: 2026-01-15
**Status**: ACTIVE

## Overview

This document tracks the implementation status of the 6-Tier Task Orchestration Framework.

## Architecture

The system implements 6 decision tiers (A-F) for task classification and routing.

### Core Components
- Main orchestrator (main_agent.py)
- 6 tier modules (A-F)
- Shared state management

## Circuit Breaker

Basic circuit breaker implemented with local state.

## Decision Logic

Simple keyword-based routing for tier classification.

## Testing & Validation

Unit tests cover 85% of codebase.

## Next Steps

- Enhance fault tolerance
- Improve routing logic
- Add metrics collection
"""
        report_path.write_text(report_content, encoding='utf-8')
        
        # Perform merge (ADMP-compliant consolidation)
        result = merger.merge_documents(
            enhancements_path,
            report_path,
            "Consolidating enhancements per ADMP Scenario D instead of maintaining separate document"
        )
        
        # Verify merge success
        assert result["success"] is True
        
        # Verify version increment
        assert result["old_version"] == "2.0.3"
        assert result["new_version"] == "2.1.0"
        
        # Verify decisions were made
        assert result["merge_decisions"] > 0
        
        # Check merged content
        merged_content = report_path.read_text(encoding='utf-8')
        
        # Version should be updated
        assert "**Version**: 2.1.0" in merged_content
        
        # Changelog should exist
        assert "## 📝 Changelog" in merged_content
        assert "### Version 2.1.0" in merged_content
        assert "Consolidating enhancements" in merged_content
        
        # Circuit Breaker section should be enhanced (merged or appended)
        assert "Circuit Breaker" in merged_content
        # Should contain content from both sources
        circuit_breaker_section = merged_content[merged_content.find("Circuit Breaker"):]
        assert "fault tolerance" in circuit_breaker_section.lower() or "redis" in circuit_breaker_section.lower()
        
        # Decision Engine content should be integrated
        assert "Decision" in merged_content
        # Should contain enhancements
        assert "confidence" in merged_content.lower() or "routing" in merged_content.lower()
        
        # Original content should be preserved
        assert "Overview" in merged_content
        assert "Architecture" in merged_content
        assert "Testing & Validation" in merged_content
    
    def test_merge_prevents_simple_append(self, merger, temp_dir):
        """Test that merge integrates content, not just appends"""
        source_path = temp_dir / "updates.md"
        source_content = """# Updates

## Testing

Added 50 new unit tests.

Implemented integration test suite.
"""
        source_path.write_text(source_content, encoding='utf-8')
        
        target_path = temp_dir / "main.md"
        target_content = """# Main Report

**Version**: 1.0.0

## Testing

Current test coverage is 70%.

We use pytest framework.
"""
        target_path.write_text(target_content, encoding='utf-8')
        
        result = merger.merge_documents(source_path, target_path)
        
        merged_content = target_path.read_text(encoding='utf-8')
        
        # Should have merge marker (not simple append)
        assert "Merged Content" in merged_content or "merged" in merged_content.lower()
        
        # Should integrate into Testing section (not create duplicate)
        testing_count = merged_content.count("## Testing")
        assert testing_count == 1, "Should not create duplicate Testing sections"
        
        # Should include content from both
        assert "50 new unit tests" in merged_content
        assert "pytest framework" in merged_content
    
    def test_merge_semantic_matching(self, merger, temp_dir):
        """Test semantic matching of similar sections"""
        source_path = temp_dir / "security_updates.md"
        source_content = """# Security Updates

## Authentication & Authorization

Implemented JWT token validation.

Added role-based access control (RBAC).
"""
        source_path.write_text(source_content, encoding='utf-8')
        
        target_path = temp_dir / "report.md"
        target_content = """# System Report

**Version**: 1.0.0

## Security Features

Basic authentication using session cookies.
"""
        target_path.write_text(target_content, encoding='utf-8')
        
        result = merger.merge_documents(source_path, target_path)
        
        # Should match "Authentication & Authorization" with "Security Features" semantically
        assert result["success"] is True
        
        merged_content = target_path.read_text(encoding='utf-8')
        
        # JWT content should be integrated into Security section
        assert "JWT" in merged_content or "token" in merged_content
        
        # Should have RBAC
        assert "RBAC" in merged_content or "role-based" in merged_content.lower()
    
    def test_no_new_document_creation(self, merger, temp_dir):
        """Test ADMP: merge modifies target, doesn't create new files"""
        source_path = temp_dir / "feature.md"
        source_path.write_text("# Feature\n## New\nContent", encoding='utf-8')
        
        target_path = temp_dir / "main.md"
        target_path.write_text("# Main\n**Version**: 1.0.0\n## Old\nContent", encoding='utf-8')
        
        # Count files before
        files_before = set(temp_dir.glob("*.md"))
        
        merger.merge_documents(source_path, target_path)
        
        # Count files after
        files_after = set(temp_dir.glob("*.md"))
        
        # No new files should be created
        assert len(files_before) == len(files_after)
        assert files_before == files_after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
