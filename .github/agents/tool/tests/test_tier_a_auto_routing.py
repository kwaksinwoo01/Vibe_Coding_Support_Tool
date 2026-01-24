"""
Unit tests for AutoRoutingEngine in A_Working_Document_Progress.py

Tests the automatic document conflict detection and merging functionality
to prevent duplicate document creation.
"""

import sys
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from A_Working_Document_Progress import (
    WorkPlanCreationEngine,
    ConflictResolution,
)


class TestConflictResolution:
    """Test ConflictResolution dataclass"""
    
    def test_conflict_resolution_no_conflict(self):
        """Test ConflictResolution with no conflict"""
        resolution = ConflictResolution()
        
        assert resolution.has_conflict is False
        assert resolution.target_document is None
        assert resolution.merge_strategy == "append"
    
    def test_conflict_resolution_with_conflict(self):
        """Test ConflictResolution with conflict detected"""
        target_path = Path("/tmp/test.md")
        resolution = ConflictResolution(
            has_conflict=True,
            target_document=target_path,
            merge_strategy="insert"
        )
        
        assert resolution.has_conflict is True
        assert resolution.target_document == target_path
        assert resolution.merge_strategy == "insert"
    
    def test_conflict_resolution_immutable(self):
        """Test that ConflictResolution is immutable (frozen)"""
        resolution = ConflictResolution()
        
        with pytest.raises(AttributeError):
            resolution.has_conflict = True


class TestAutoRoutingEngineScanDocuments:
    """Test AutoRoutingEngine.scan_existing_documents"""
    
    def test_scan_empty_directory(self):
        """Test scanning when docs_2 directory doesn't exist"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            
            results = engine.scan_existing_documents(["test"])
            
            assert results == []
    
    def test_scan_no_matches(self):
        """Test scanning when no documents match keywords"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            docs_dir = workspace_root / "docs_2"
            docs_dir.mkdir(parents=True)
            
            # Create a document with no matching keywords
            test_doc = docs_dir / "test.md"
            test_doc.write_text("# Unrelated Document\n\nSome content", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            results = engine.scan_existing_documents(["event polling"])
            
            assert results == []
    
    def test_scan_single_match(self):
        """Test scanning finds a matching document"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            docs_dir = workspace_root / "docs_2" / "P2"
            docs_dir.mkdir(parents=True)
            
            # Create a document with matching keywords
            test_doc = docs_dir / "P2.1.01-Client-Event-Polling.md"
            test_doc.write_text(
                "# Client Dropbox Event Polling\n\nThis handles event polling",
                encoding="utf-8"
            )
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            results = engine.scan_existing_documents(["Client Dropbox Event Polling"])
            
            assert len(results) == 1
            assert results[0].name == "P2.1.01-Client-Event-Polling.md"
    
    def test_scan_multiple_matches(self):
        """Test scanning finds multiple matching documents"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            docs_dir = workspace_root / "docs_2" / "P2"
            docs_dir.mkdir(parents=True)
            
            # Create multiple documents with matching keywords
            doc1 = docs_dir / "P2.1.01-Client-Event-Polling.md"
            doc1.write_text("Event polling system", encoding="utf-8")
            
            doc2 = docs_dir / "P2-Remaining-User-Requirements.md"
            doc2.write_text("Event polling requirements", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            results = engine.scan_existing_documents(["event polling"])
            
            assert len(results) == 2
    
    def test_scan_case_insensitive(self):
        """Test that keyword matching is case-insensitive"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            docs_dir = workspace_root / "docs_2"
            docs_dir.mkdir(parents=True)
            
            test_doc = docs_dir / "test.md"
            test_doc.write_text("CLIENT DROPBOX EVENT POLLING", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            results = engine.scan_existing_documents(["client dropbox event polling"])
            
            assert len(results) == 1


class TestAutoRoutingEngineDetectConflicts:
    """Test AutoRoutingEngine.detect_conflicts"""
    
    def test_detect_no_conflict_empty_directory(self):
        """Test detect_conflicts when no existing documents"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            
            resolution = engine.detect_conflicts("Create event polling system")
            
            assert resolution.has_conflict is False
            assert resolution.target_document is None
    
    def test_detect_conflict_with_event_polling_document(self):
        """Test conflict detection for EVENT_POLLING_SRP_REFACTORING_ANALYSIS.md scenario"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            docs_dir = workspace_root / "docs_2" / "P2"
            docs_dir.mkdir(parents=True)
            
            # Create the exact scenario from the problem statement
            existing_doc = docs_dir / "P2.1.01-Client-Event-Polling.md"
            existing_doc.write_text(
                "# Client Dropbox Event Polling\n\nExisting content",
                encoding="utf-8"
            )
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            resolution = engine.detect_conflicts(
                "Create a work plan for Client Dropbox Event Polling refactoring"
            )
            
            assert resolution.has_conflict is True
            assert resolution.target_document is not None
            assert "Client-Event-Polling" in resolution.target_document.name
    
    def test_detect_conflict_prioritizes_p2_documents(self):
        """Test that P2 documents are prioritized for conflict resolution"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create multiple matching documents in different locations
            p1_dir = workspace_root / "docs_2" / "P1"
            p1_dir.mkdir(parents=True)
            p1_doc = p1_dir / "P1-Event.md"
            p1_doc.write_text("event polling", encoding="utf-8")
            
            p2_dir = workspace_root / "docs_2" / "P2"
            p2_dir.mkdir(parents=True)
            p2_doc = p2_dir / "P2-Event-Polling.md"
            p2_doc.write_text("event polling", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            resolution = engine.detect_conflicts("event polling system")
            
            # Should prioritize P2 document
            assert resolution.has_conflict is True
            assert "P2" in resolution.target_document.name
    
    def test_detect_conflict_prefers_specific_client_event_polling_doc(self):
        """Test that P2.1.01-Client-Event-Polling.md is preferred"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            p2_dir = workspace_root / "docs_2" / "P2"
            p2_dir.mkdir(parents=True)
            
            # Create multiple P2 documents
            doc1 = p2_dir / "P2-General.md"
            doc1.write_text("event polling", encoding="utf-8")
            
            doc2 = p2_dir / "P2.1.01-Client-Event-Polling.md"
            doc2.write_text("Client Dropbox Event Polling", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            resolution = engine.detect_conflicts("event polling refactoring")
            
            # Should prefer the specific Client-Event-Polling document
            assert resolution.has_conflict is True
            assert "Client-Event-Polling" in resolution.target_document.name
    
    def test_merge_strategy_append_by_default(self):
        """Test that default merge strategy is 'append'"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            docs_dir = workspace_root / "docs_2" / "P2"
            docs_dir.mkdir(parents=True)
            
            # Use a more specific document name that will score above threshold
            existing_doc = docs_dir / "P2.1-Event-Polling.md"
            existing_doc.write_text("event polling", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            resolution = engine.detect_conflicts("event polling")
            
            assert resolution.merge_strategy == "append"
    
    def test_merge_strategy_append_when_add_keyword(self):
        """Test merge strategy is 'append' when user input contains 'add'"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            docs_dir = workspace_root / "docs_2" / "P2"
            docs_dir.mkdir(parents=True)
            
            # Use a more specific document name that will score above threshold
            existing_doc = docs_dir / "P2.1-Event-Polling.md"
            existing_doc.write_text("event polling", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            resolution = engine.detect_conflicts("add event polling feature")
            
            assert resolution.merge_strategy == "append"
    
    def test_merge_strategy_insert_when_insert_keyword(self):
        """Test merge strategy is 'insert' when user input contains 'insert'"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            docs_dir = workspace_root / "docs_2" / "P2"
            docs_dir.mkdir(parents=True)
            
            # Use a more specific document name that will score above threshold
            existing_doc = docs_dir / "P2.1-Event-Polling.md"
            existing_doc.write_text("event polling", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            resolution = engine.detect_conflicts("insert event polling section")
            
            assert resolution.merge_strategy == "insert"


class TestAutoRoutingEngineMergeContent:
    """Test AutoRoutingEngine.merge_content"""
    
    def test_merge_content_append_strategy(self):
        """Test merging content with append strategy"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            target_doc = Path(tmpdir) / "test.md"
            target_doc.write_text("# Original Content\n\nLine 1", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            new_content = "## New Section\n\nLine 2"
            
            success = engine.merge_content(target_doc, new_content)
            
            assert success is True
            merged = target_doc.read_text(encoding="utf-8")
            assert "Original Content" in merged
            assert "New Section" in merged
            assert merged.endswith("Line 2")
    
    def test_merge_content_preserves_original(self):
        """Test that merging preserves original content"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            target_doc = Path(tmpdir) / "test.md"
            original_content = "# Title\n\n## Section 1\n\nContent 1"
            target_doc.write_text(original_content, encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            new_content = "## Section 2\n\nContent 2"
            
            success = engine.merge_content(target_doc, new_content)
            
            assert success is True
            merged = target_doc.read_text(encoding="utf-8")
            assert original_content in merged
    
    def test_merge_content_adds_separator(self):
        """Test that merged content has proper separation"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            target_doc = Path(tmpdir) / "test.md"
            target_doc.write_text("Line 1", encoding="utf-8")
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            success = engine.merge_content(target_doc, "Line 2")
            
            assert success is True
            merged = target_doc.read_text(encoding="utf-8")
            # Should have double newline separator
            assert "\n\n" in merged
    
    def test_merge_content_handles_nonexistent_file(self):
        """Test that merging fails gracefully for non-existent file"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            target_doc = Path(tmpdir) / "nonexistent.md"
            
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            success = engine.merge_content(target_doc, "New content")
            
            assert success is False


class TestAutoRoutingEngineKeywordExtraction:
    """Test AutoRoutingEngine._extract_keywords (internal method)"""
    
    def test_extract_keywords_client_event_polling(self):
        """Test keyword extraction for Client Event Polling"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            
            keywords = engine._extract_keywords(
                "Create a work plan for Client Dropbox Event Polling"
            )
            
            assert "Client Dropbox Event Polling" in keywords
    
    def test_extract_keywords_multiple_matches(self):
        """Test keyword extraction with multiple keyword matches"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            
            keywords = engine._extract_keywords(
                "Work on P2.1 event polling for dropbox polling system"
            )
            
            # Should extract multiple relevant keywords
            assert len(keywords) > 0
            assert any("event polling" in kw.lower() for kw in keywords)
    
    def test_extract_keywords_case_insensitive(self):
        """Test that keyword extraction is case-insensitive"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            
            keywords = engine._extract_keywords("CLIENT EVENT POLLING")
            
            assert len(keywords) > 0


class TestAutoRoutingEngineIntegration:
    """Integration tests for AutoRoutingEngine with WorkPlanCreationEngine"""
    
    def test_prevent_duplicate_event_polling_document(self):
        """
        Test the exact scenario from EVENT_POLLING_SRP_REFACTORING_ANALYSIS.md
        
        This test ensures that when a user tries to create a document about
        "Client Dropbox Event Polling", it should detect the existing
        P2.1.01-Client-Event-Polling.md and merge instead of creating duplicate.
        """
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Setup: Create existing document structure
            p2_dir = workspace_root / "docs_2" / "P2"
            p2_dir.mkdir(parents=True)
            
            # Create existing P2.1.01-Client-Event-Polling.md
            existing_doc = p2_dir / "P2.1.01-Client-Event-Polling.md"
            existing_doc.write_text(
                "# Client Dropbox Event Polling\n\n"
                "## Overview\n\n"
                "Existing event polling implementation.\n",
                encoding="utf-8"
            )
            
            # Create P2-Remaining-User-Requirements.md (parent document)
            parent_doc = p2_dir / "P2-Remaining-User-Requirements.md"
            parent_doc.write_text(
                "# Remaining User Requirements\n\n"
                "Client event polling tasks.\n",
                encoding="utf-8"
            )
            
            # Test: Try to create a plan for event polling refactoring
            engine = WorkPlanCreationEngine.AutoRoutingEngine(workspace_root)
            resolution = engine.detect_conflicts(
                "Create a work plan for Client Dropbox Event Polling SRP refactoring"
            )
            
            # Verify: Should detect conflict with existing document
            assert resolution.has_conflict is True
            assert resolution.target_document is not None
            assert "P2.1.01-Client-Event-Polling.md" in str(resolution.target_document)
            
            # Test: Merge content instead of creating new document
            new_content = (
                "## SRP Refactoring Analysis\n\n"
                "Refactoring event polling system to follow SRP.\n"
            )
            success = engine.merge_content(resolution.target_document, new_content)
            
            assert success is True
            
            # Verify: Original content preserved and new content added
            merged_content = resolution.target_document.read_text(encoding="utf-8")
            assert "Existing event polling implementation" in merged_content
            assert "SRP Refactoring Analysis" in merged_content
            
            # Verify: No duplicate document created
            all_docs = list(p2_dir.glob("*.md"))
            doc_names = [doc.name for doc in all_docs]
            
            # Should only have the 2 original documents, no duplicates
            assert len(all_docs) == 2
            assert "P2.1.01-Client-Event-Polling.md" in doc_names
            assert "P2-Remaining-User-Requirements.md" in doc_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
