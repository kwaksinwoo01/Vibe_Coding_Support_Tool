"""
Comprehensive tests for nested dataclass integration in tier states.

Tests the new DocumentMetadata, DocumentHierarchy, DocumentSources, and
DocumentCreationContext nested dataclasses and their integration with
WPDDocument service-layer models.
"""

import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.core.tier_states import (
    TierAState,
    TierBState,
    TierCState,
    TierEState,
    TierStateConverter
)
from models.core.tier_models import (
    DocumentMetadata,
    DocumentHierarchy,
    DocumentSources,
    DocumentCreationContext
)
from models.core.documents import WPDDocument


class TestNestedDataclasses:
    """Test nested dataclass functionality"""
    
    def test_document_metadata_creation(self):
        """Test DocumentMetadata creation and serialization"""
        metadata = DocumentMetadata(
            document_type="WPD",
            Part_N="5",
            document_title="Test Feature",
            version="1.0.0",
            status="📋 PENDING",
            timestamp="2025-01-07T00:00:00Z"
        )
        
        # Test to_dict
        data = metadata.to_dict()
        assert data["document_type"] == "WPD"
        assert data["Part_N"] == "5"
        assert data["document_title"] == "Test Feature"
        
        # Test from_dict
        metadata2 = DocumentMetadata.from_dict(data)
        assert metadata2.document_type == metadata.document_type
        assert metadata2.Part_N == metadata.Part_N
    
    def test_document_hierarchy_creation(self):
        """Test DocumentHierarchy creation and serialization"""
        hierarchy = DocumentHierarchy(
            parent_document="docs_2/NextTask-2.md",
            child_documents=["docs_2/P5/P5.1.md", "docs_2/P5/P5.2.md"],
            reference_documents=["docs_2/guidelines/workflow-2.md"]
        )
        
        # Test to_dict
        data = hierarchy.to_dict()
        assert data["parent_document"] == "docs_2/NextTask-2.md"
        assert len(data["child_documents"]) == 2
        
        # Test from_dict
        hierarchy2 = DocumentHierarchy.from_dict(data)
        assert hierarchy2.parent_document == hierarchy.parent_document
        assert hierarchy2.child_documents == hierarchy.child_documents
    
    def test_document_sources_creation(self):
        """Test DocumentSources creation and serialization"""
        sources = DocumentSources(
            wpd_sources=["docs_2/P5/P5-Feature.md"],
            prd_path="docs_2/prd/PRD-P5.md",
            execution_report_path="docs_2/reports/P5-exec.md"
        )
        
        # Test to_dict
        data = sources.to_dict()
        assert data["wpd_sources"] == ["docs_2/P5/P5-Feature.md"]
        assert data["prd_path"] == "docs_2/prd/PRD-P5.md"
        
        # Test from_dict
        sources2 = DocumentSources.from_dict(data)
        assert sources2.wpd_sources == sources.wpd_sources
        assert sources2.prd_path == sources.prd_path
    
    def test_document_creation_context_creation(self):
        """Test DocumentCreationContext creation and serialization"""
        context = DocumentCreationContext(
            documents_to_create=["New Phase 1", "New Phase 2"],
            parent_document_path="docs_2/P5/P5-Feature.md",
            creation_parameters={"Part_N": "5.3", "type": "phase"}
        )
        
        # Test to_dict
        data = context.to_dict()
        assert len(data["documents_to_create"]) == 2
        assert data["parent_document_path"] == "docs_2/P5/P5-Feature.md"
        assert data["creation_parameters"]["Part_N"] == "5.3"
        
        # Test from_dict
        context2 = DocumentCreationContext.from_dict(data)
        assert context2.documents_to_create == context.documents_to_create
        assert context2.creation_parameters == context.creation_parameters


class TestWPDDocumentIntegration:
    """Test integration between tier states and WPDDocument"""
    
    def test_metadata_from_wpd_document(self):
        """Test DocumentMetadata.from_wpd_document()"""
        wpd_doc = WPDDocument(
            Part_N="5",
            wpd_grade="L1",
            title="Test Feature",
            version="1.0.0",
            status="📋 PENDING",
            document_type="WPD",
            timestamp="2025-01-07T00:00:00Z"
        )
        
        metadata = DocumentMetadata.from_wpd_document(wpd_doc)
        assert metadata.Part_N == "5"
        assert metadata.document_title == "Test Feature"
        assert metadata.version == "1.0.0"
        assert metadata.document_type == "WPD"
    
    def test_hierarchy_from_wpd_document(self):
        """Test DocumentHierarchy.from_wpd_document()"""
        wpd_doc = WPDDocument(
            Part_N="5",
            wpd_grade="L1",
            title="Test Feature",
            parent_document="docs_2/NextTask-2.md",
            child_documents=["docs_2/P5/P5.1.md"],
            reference_documents=["docs_2/guidelines/workflow-2.md"]
        )
        
        hierarchy = DocumentHierarchy.from_wpd_document(wpd_doc)
        assert hierarchy.parent_document == "docs_2/NextTask-2.md"
        assert len(hierarchy.child_documents) == 1
        assert len(hierarchy.reference_documents) == 1
    
    def test_sources_from_wpd_document(self):
        """Test DocumentSources.from_wpd_document()"""
        wpd_doc = WPDDocument(
            Part_N="5",
            wpd_grade="L1",
            title="Test Feature",
            parent_document="docs_2/P5/P5-Feature.md",
            prd_path="docs_2/prd/PRD-P5.md",
            results_report="docs_2/reports/P5-exec.md"
        )
        
        sources = DocumentSources.from_wpd_document(wpd_doc)
        assert sources.wpd_sources == ["docs_2/P5/P5-Feature.md"]
        assert sources.prd_path == "docs_2/prd/PRD-P5.md"
        assert sources.execution_report_path == "docs_2/reports/P5-exec.md"
    
    def test_tier_a_from_wpd_document(self):
        """Test TierAState.from_wpd_document()"""
        wpd_doc = WPDDocument(
            Part_N="5",
            wpd_grade="L1",
            title="Test Feature",
            version="1.0.0",
            status="📋 PENDING",
            document_type="WPD",
            timestamp="2025-01-07T00:00:00Z",
            parent_document="docs_2/NextTask-2.md",
            child_documents=["docs_2/P5/P5.1.md"]
        )
        
        tier_a = TierAState.from_wpd_document(wpd_doc)
        # Note: wpd_grade is in AgentState, not TierAState (per AGENT_STATE_OPTIMIZATION.md)
        assert not hasattr(tier_a, "wpd_grade"), "wpd_grade should be in AgentState, not TierAState"
        assert tier_a.metadata.Part_N == "5"
        assert tier_a.metadata.document_title == "Test Feature"
        assert tier_a.hierarchy.parent_document == "docs_2/NextTask-2.md"
        assert len(tier_a.hierarchy.child_documents) == 1
    
    def test_tier_a_to_wpd_document(self):
        """Test TierAState.to_wpd_document() - wpd_grade should be passed as parameter"""
        metadata = DocumentMetadata(
            document_type="WPD",
            Part_N="5",
            document_title="Test Feature",
            version="1.0.0",
            status="📋 PENDING",
            timestamp="2025-01-07T00:00:00Z"
        )
        
        hierarchy = DocumentHierarchy(
            parent_document="docs_2/NextTask-2.md",
            child_documents=["docs_2/P5/P5.1.md"]
        )
        
        tier_a = TierAState(
            metadata=metadata,
            hierarchy=hierarchy
        )
        
        # wpd_grade is passed as parameter (comes from AgentState.wpd_grade)
        wpd_doc = tier_a.to_wpd_document(wpd_grade="L1")
        assert wpd_doc.wpd_grade == "L1"
        assert wpd_doc.Part_N == "5"
        assert wpd_doc.title == "Test Feature"
        assert wpd_doc.parent_document == "docs_2/NextTask-2.md"
        assert len(wpd_doc.child_documents) == 1


class TestCleanDataclassAccess:
    """Test clean nested dataclass access patterns (no backwards compatibility)"""
    
    def test_tier_a_nested_access(self):
        """Test TierAState nested dataclass access"""
        metadata = DocumentMetadata(
            document_type="WPD",
            Part_N="5",
            document_title="Test",
            version="1.0.0"
        )
        
        hierarchy = DocumentHierarchy(
            parent_document="docs_2/NextTask-2.md",
            child_documents=["docs_2/P5/P5.1.md"]
        )
        
        tier_a = TierAState(
            metadata=metadata,
            hierarchy=hierarchy
        )
        
        # Test access via nested structures
        assert tier_a.metadata.Part_N == "5"
        assert tier_a.metadata.document_title == "Test"
        assert tier_a.hierarchy.parent_document == "docs_2/NextTask-2.md"
        assert len(tier_a.hierarchy.child_documents) == 1
    
    def test_tier_b_nested_access(self):
        """Test TierBState nested dataclass access"""
        sources = DocumentSources(
            wpd_sources=["docs_2/P5/P5-Feature.md"],
            prd_path="docs_2/prd/PRD-P5.md"
        )
        
        tier_b = TierBState(
            sources=sources
        )
        
        # Test access via nested structures
        assert tier_b.sources.prd_path == "docs_2/prd/PRD-P5.md"
        assert tier_b.sources.wpd_sources == ["docs_2/P5/P5-Feature.md"]
    
    def test_tier_c_nested_access(self):
        """Test TierCState nested dataclass access"""
        creation_context = DocumentCreationContext(
            documents_to_create=["New Phase"],
            parent_document_path="docs_2/P5/P5-Feature.md"
        )
        
        tier_c = TierCState(
            creation_context=creation_context
        )
        
        # Test access via nested structures
        assert tier_c.creation_context.documents_to_create == ["New Phase"]
        assert tier_c.creation_context.parent_document_path == "docs_2/P5/P5-Feature.md"
    
    def test_tier_e_nested_access(self):
        """Test TierEState nested dataclass access"""
        sources = DocumentSources(
            wpd_sources=["docs_2/P5/P5-Feature.md"],
            prd_path="docs_2/prd/PRD-P5.md"
        )
        
        tier_e = TierEState(
            sources=sources
        )
        
        # Test access via nested structures
        assert tier_e.sources.prd_path == "docs_2/prd/PRD-P5.md"
        assert tier_e.sources.wpd_sources == ["docs_2/P5/P5-Feature.md"]


class TestPayloadSerialization:
    """Test to_payload and from_payload with nested structures"""
    
    def test_tier_a_payload_roundtrip(self):
        """Test TierAState payload serialization roundtrip"""
        metadata = DocumentMetadata(
            document_type="WPD",
            Part_N="5",
            document_title="Test Feature",
            version="1.0.0",
            status="📋 PENDING"
        )
        
        hierarchy = DocumentHierarchy(
            parent_document="docs_2/NextTask-2.md",
            child_documents=["docs_2/P5/P5.1.md"]
        )
        
        tier_a = TierAState(
            metadata=metadata,
            hierarchy=hierarchy,
            created_documents=["docs_2/P5/P5-Feature.md"]
        )
        
        # Serialize to payload
        payload = tier_a.to_payload()
        # Note: wpd_grade is NOT in TierAState payload (it's in AgentState)
        assert "Part_N" in payload  # Backward-compatible key
        assert payload["Part_N"] == "5"
        assert payload["parent_document"] == "docs_2/NextTask-2.md"
        
        # Deserialize from payload
        tier_a2 = TierAState.from_payload(payload)
        # wpd_grade is NOT in TierAState
        assert not hasattr(tier_a2, "wpd_grade")
        assert tier_a2.metadata.Part_N == "5"
        assert tier_a2.hierarchy.parent_document == "docs_2/NextTask-2.md"
        assert len(tier_a2.created_documents) == 1
    
    def test_tier_b_payload_roundtrip(self):
        """Test TierBState payload serialization roundtrip"""
        sources = DocumentSources(
            wpd_sources=["docs_2/P5/P5-Feature.md"],
            prd_path="docs_2/prd/PRD-P5.md"
        )
        
        tier_b = TierBState(
            sources=sources,
            total_phases=3,
            completed_phases=2
        )
        
        # Serialize to payload
        payload = tier_b.to_payload()
        # Note: wpd_source_path is NOT in TierBState (it's in AgentState)
        assert payload["prd_path"] == "docs_2/prd/PRD-P5.md"
        assert payload["total_phases"] == 3
        
        # Deserialize from payload
        tier_b2 = TierBState.from_payload(payload)
        # Note: wpd_source_path is NOT in TierBState (it's in AgentState)
        assert not hasattr(tier_b2, "wpd_source_path")
        assert tier_b2.sources.prd_path == "docs_2/prd/PRD-P5.md"
        assert tier_b2.total_phases == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
