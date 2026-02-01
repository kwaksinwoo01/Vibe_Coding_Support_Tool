"""
Unit tests for TierStateConverter - Tier C to Tier A integration

Tests the multiverse-composite operation node functionality where
Tier C can invoke Tier A for document creation.
"""

import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.core.tier_states import (
    TierAState,
    TierCState,
    TierStateConverter,
)
from models.core.tier_models import DocumentCreationContext


class TestTierCToAConversion:
    """Test suite for TierC → TierA state conversion"""
    
    def test_c_to_a_basic_conversion(self):
        """Test basic TierC to TierA state conversion"""
        # Create a TierC state with document creation request
        creation_context = DocumentCreationContext(
            documents_to_create=["New Phase Document", "Another Document"],
            parent_document_path="docs_2/NextTask-2.md",
            creation_parameters={
                "Part_N": "5",
                "phase_number": "2"
            }
        )
        
        tier_c = TierCState(
            target_document="docs_2/P5/P5-Feature.md",
            modification_type="add_phase",
            creation_context=creation_context
        )
        
        # Convert to TierA state
        tier_a = TierStateConverter.c_to_a(tier_c)
        
        # Verify conversion
        assert isinstance(tier_a, TierAState)
        assert tier_a.hierarchy.parent_document == "docs_2/P5/P5-Feature.md"
        assert tier_a.main_document_path == "docs_2/NextTask-2.md"
        assert tier_a.metadata.document_title == "New Phase Document"
        assert tier_a.metadata.Part_N == "5"
        assert tier_a.current_step == "5"
        # Note: wpd_grade is set in AgentState, not TierAState (per AGENT_STATE_OPTIMIZATION.md)
        assert not hasattr(tier_a, "wpd_grade"), "wpd_grade should be in AgentState, not TierAState"
        assert tier_a.metadata.document_type == "WPD"
    
    def test_c_to_a_with_empty_documents(self):
        """Test TierC to TierA conversion with no documents to create"""
        creation_context = DocumentCreationContext(
            documents_to_create=[],
            parent_document_path="docs_2/NextTask-2.md"
        )
        
        tier_c = TierCState(
            target_document="docs_2/P3/P3-Task.md",
            creation_context=creation_context
        )
        
        tier_a = TierStateConverter.c_to_a(tier_c)
        
        # Should still create valid TierA state with default title
        assert isinstance(tier_a, TierAState)
        assert tier_a.metadata.document_title == "New-Document"
    
    def test_c_to_a_preserves_context(self):
        """Test that creation context is preserved in conversion"""
        creation_context = DocumentCreationContext(
            documents_to_create=["Integration Phase 1"],
            parent_document_path="docs_2/NextTask-2.md",
            creation_parameters={
                "Part_N": "7",
                "source": "automatic_trigger",
                "timestamp": "2025-01-01T12:00:00"
            }
        )
        
        tier_c = TierCState(
            target_document="docs_2/P7/P7-Integration.md",
            creation_context=creation_context
        )
        
        tier_a = TierStateConverter.c_to_a(tier_c)
        
        assert tier_a.metadata.Part_N == "7"
        assert tier_a.current_step == "7"
    
    def test_a_to_c_result_merge(self):
        """Test merging TierA results back into TierC state"""
        # Original TierC state
        original_tier_c = TierCState(
            target_document="docs_2/P5/P5-Feature.md",
            modification_type="add_phase",
            creation_context=DocumentCreationContext(
                documents_to_create=["New Phase"]
            ),
            affected_sections=["Phase 1", "Phase 2"],
            changes_made=[{"type": "update", "description": "Initial changes"}]
        )
        
        # Simulated TierA result after document creation
        tier_a = TierAState(
            created_documents=[
                "docs_2/P5/P5.1-New-Phase.md",
                "docs_2/P5/P5.2-Another-Phase.md"
            ],
            validation_results={
                "docs_2/P5/P5.1-New-Phase.md": True,
                "docs_2/P5/P5.2-Another-Phase.md": True
            }
        )
        
        # Merge results back
        updated_tier_c = TierStateConverter.a_to_c(tier_a, original_tier_c)
        
        # Verify merge
        assert isinstance(updated_tier_c, TierCState)
        assert updated_tier_c.target_document == original_tier_c.target_document
        assert updated_tier_c.modification_type == original_tier_c.modification_type
        assert len(updated_tier_c.changes_made) == 2  # Original + new creation record
        assert updated_tier_c.creation_context.documents_to_create == []  # Should be cleared
        
        # Check that document creation was recorded
        creation_record = updated_tier_c.changes_made[-1]
        assert creation_record["type"] == "document_creation"
        assert len(creation_record["created_documents"]) == 2
        
    def test_a_to_c_validation_propagation(self):
        """Test that validation results from TierA propagate to TierC"""
        original_tier_c = TierCState(
            target_document="docs_2/P3/P3-Task.md",
            validation_passed=True
        )
        
        # TierA with failed validation
        tier_a_failed = TierAState(
            created_documents=["docs_2/P3/P3.1-Phase.md"],
            validation_results={
                "docs_2/P3/P3.1-Phase.md": False
            }
        )
        
        updated_tier_c = TierStateConverter.a_to_c(tier_a_failed, original_tier_c)
        
        # Validation should fail if TierA had validation failures
        assert updated_tier_c.validation_passed == False
    
    def test_chain_to_tier_c_to_a(self):
        """Test using chain_to_tier for C→A transition"""
        creation_context = DocumentCreationContext(
            documents_to_create=["New Module Phase"],
            parent_document_path="docs_2/NextTask-2.md",
            creation_parameters={"Part_N": "8"}
        )
        
        tier_c = TierCState(
            target_document="docs_2/P8/P8-Module.md",
            creation_context=creation_context
        )
        
        # Use chain_to_tier method
        tier_a = TierStateConverter.chain_to_tier(tier_c, "A")
        
        assert isinstance(tier_a, TierAState)
        assert tier_a.hierarchy.parent_document == "docs_2/P8/P8-Module.md"
        assert tier_a.metadata.Part_N == "8"
    
    def test_chain_to_tier_unsupported_transition(self):
        """Test that unsupported transitions raise ValueError"""
        tier_a = TierAState()
        
        # A→C is not a supported transition
        with pytest.raises(ValueError) as excinfo:
            TierStateConverter.chain_to_tier(tier_a, "C")
        
        assert "Unsupported tier transition" in str(excinfo.value)
        assert "A → C" in str(excinfo.value)


class TestTierCStateFields:
    """Test TierCState enhancements for document creation"""
    
    def test_tier_c_creation_fields(self):
        """Test that TierCState has document creation fields"""
        tier_c = TierCState()
        
        # Verify new fields exist
        assert hasattr(tier_c, 'creation_context')
        
        # Verify defaults - creation_context is DocumentCreationContext
        assert isinstance(tier_c.creation_context, DocumentCreationContext)
        assert tier_c.creation_context.documents_to_create == []
        assert tier_c.creation_context.parent_document_path is None
        assert tier_c.creation_context.creation_parameters == {}
    
    def test_tier_c_to_payload_includes_creation_fields(self):
        """Test that to_payload includes creation fields"""
        creation_context = DocumentCreationContext(
            documents_to_create=["doc1", "doc2"],
            parent_document_path="parent.md",
            creation_parameters={"key": "value"}
        )
        
        tier_c = TierCState(
            target_document="test.md",
            creation_context=creation_context
        )
        
        payload = tier_c.to_payload()
        
        assert "documents_to_create" in payload
        assert "parent_document_path" in payload
        assert "creation_context" in payload
        assert payload["documents_to_create"] == ["doc1", "doc2"]
        assert payload["parent_document_path"] == "parent.md"
        # creation_context should be the serialized DocumentCreationContext, not just parameters
        assert payload["creation_context"]["creation_parameters"] == {"key": "value"}
        assert payload["creation_context"]["documents_to_create"] == ["doc1", "doc2"]
        assert payload["creation_context"]["parent_document_path"] == "parent.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
