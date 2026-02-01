"""
Integration test for Tier C invoking Tier A for document creation.

Tests the multiverse-composite operation where Tier C delegates
document creation to Tier A and merges results back.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from C_Edit_working_document import PlanModificationEngine
from models.core.states import AgentState
from models.core.tier_states import TierAState, TierCState


class TestTierCInvokesTierA:
    """Integration tests for Tier C invoking Tier A"""
    
    @patch('A_Working_Document_Progress.WorkPlanCreationEngine')
    def test_invoke_tier_a_success(self, mock_tier_a_class):
        """Test successful invocation of Tier A from Tier C"""
        # Setup mock Tier A engine
        mock_engine = MagicMock()
        mock_tier_a_class.return_value = mock_engine
        
        # Mock successful Tier A execution
        mock_result = AgentState.create_success(
            tier="A",
            logic_summary="Documents created successfully",
            payload={
                "created_documents": [
                    "docs_2/P5/P5.1-New-Phase.md",
                    "docs_2/P5/P5.2-Another-Phase.md"
                ],
                "validation_results": {
                    "docs_2/P5/P5.1-New-Phase.md": True,
                    "docs_2/P5/P5.2-Another-Phase.md": True
                },
                "wpd_grade": "L1",
                "main_document_path": "docs_2/NextTask-2.md",
                "Part_N": "5"
            }
        )
        mock_engine.execute.return_value = mock_result
        
        # Create Tier C engine
        tier_c_engine = PlanModificationEngine(workspace_root="/tmp")
        
        # Invoke Tier A for document creation
        success, created_docs = tier_c_engine.invoke_tier_a_for_document_creation(
            documents=["New Phase", "Another Phase"],
            parent_doc="docs_2/P5/P5-Feature.md"
        )
        
        # Verify success
        assert success is True
        assert len(created_docs) == 2
        assert "docs_2/P5/P5.1-New-Phase.md" in created_docs
        assert "docs_2/P5/P5.2-Another-Phase.md" in created_docs
        
        # Verify Tier A was called with correct arguments
        mock_tier_a_class.assert_called_once_with("/tmp")
        mock_engine.execute.assert_called_once()
    
    @patch('A_Working_Document_Progress.WorkPlanCreationEngine')
    def test_invoke_tier_a_failure(self, mock_tier_a_class):
        """Test Tier A invocation failure handling"""
        # Setup mock Tier A engine
        mock_engine = MagicMock()
        mock_tier_a_class.return_value = mock_engine
        
        # Mock failed Tier A execution
        mock_result = AgentState.create_failure(
            tier="A",
            error_msg="Document creation failed",
            logic_summary="Validation error"
        )
        mock_engine.execute.return_value = mock_result
        
        # Create Tier C engine
        tier_c_engine = PlanModificationEngine(workspace_root="/tmp")
        
        # Invoke Tier A for document creation
        success, created_docs = tier_c_engine.invoke_tier_a_for_document_creation(
            documents=["Failed Document"],
            parent_doc="docs_2/P5/P5-Feature.md"
        )
        
        # Verify failure
        assert success is False
        assert len(created_docs) == 0
    
    @patch('A_Working_Document_Progress.WorkPlanCreationEngine')
    def test_state_conversion_during_invocation(self, mock_tier_a_class):
        """Test that TierC state is properly converted to TierA state"""
        # Setup mock Tier A engine
        mock_engine = MagicMock()
        mock_tier_a_class.return_value = mock_engine
        
        # Mock successful result
        mock_result = AgentState.create_success(
            tier="A",
            logic_summary="Created",
            payload={
                "created_documents": ["docs_2/P7/P7.1-Test.md"],
                "validation_results": {"docs_2/P7/P7.1-Test.md": True},
                "wpd_grade": "L1",
                "Part_N": "7"
            }
        )
        mock_engine.execute.return_value = mock_result
        
        # Create Tier C engine with specific state
        tier_c_engine = PlanModificationEngine(workspace_root="/tmp")
        # Set tier-specific fields on tier_state, not state
        tier_c_engine.tier_state.creation_context.documents_to_create = ["Test Document"]
        tier_c_engine.tier_state.creation_context.parent_document_path = "docs_2/NextTask-2.md"
        tier_c_engine.tier_state.creation_context.creation_parameters = {
            "Part_N": "7",
            "source": "tier_c_modification"
        }
        
        # Invoke Tier A
        success, created_docs = tier_c_engine.invoke_tier_a_for_document_creation(
            documents=["Test Document"],
            parent_doc="docs_2/P7/P7-Module.md"
        )
        
        # Verify state was updated
        assert success is True
        assert tier_c_engine.tier_state.creation_context.documents_to_create == []  # Should be cleared
        # Verify documents were added to modified_documents list
        assert len(tier_c_engine.tier_state.modified_documents) > 0
        assert "docs_2/P7/P7.1-Test.md" in tier_c_engine.tier_state.modified_documents
    
    @patch('A_Working_Document_Progress.WorkPlanCreationEngine')
    def test_create_new_documents_uses_tier_a(self, mock_tier_a_class):
        """Test that create_new_documents() actually invokes Tier A"""
        # Setup mock
        mock_engine = MagicMock()
        mock_tier_a_class.return_value = mock_engine
        
        mock_result = AgentState.create_success(
            tier="A",
            logic_summary="Created",
            payload={
                "created_documents": ["docs_2/P5/P5.1-New.md"],
                "validation_results": {"docs_2/P5/P5.1-New.md": True},
                "wpd_grade": "L1",
                "Part_N": "5"
            }
        )
        mock_engine.execute.return_value = mock_result
        
        # Create Tier C engine with documents to add
        tier_c_engine = PlanModificationEngine(workspace_root="/tmp")
        # Set documents on tier_state, not add_doc
        tier_c_engine.tier_state.creation_context.documents_to_create = ["New Document", "Another Document"]
        tier_c_engine.tier_state.target_document = "docs_2/P5/P5-Feature.md"
        
        # Call create_new_documents
        result = tier_c_engine.create_new_documents()
        
        # Verify Tier A was invoked
        assert result is True
        assert len(tier_c_engine.tier_state.creation_context.documents_to_create) == 0  # Should be cleared
        mock_tier_a_class.assert_called()
    
    def test_extract_Part_Number_from_path(self):
        """Test step number extraction from document path"""
        tier_c_engine = PlanModificationEngine(workspace_root="/tmp")
        
        # Test various path formats
        assert tier_c_engine._extract_Part_Number_from_path("docs_2/P5/P5-Feature.md") == "5"
        assert tier_c_engine._extract_Part_Number_from_path("docs_2/P12/P12-Task.md") == "12"
        assert tier_c_engine._extract_Part_Number_from_path("docs_2/P5/P5.2-Phase.md") == "5"
        assert tier_c_engine._extract_Part_Number_from_path("P7-Module.md") == "7"
        assert tier_c_engine._extract_Part_Number_from_path("no-number.md") == "1"  # Default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
