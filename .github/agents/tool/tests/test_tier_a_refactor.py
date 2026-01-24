"""
Unit tests for A_Working_Document_Progress.py - Tier A Work Plan Creation

Tests the refactored Creator classes with clean SRP-following signatures.
"""

import sys
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from A_Working_Document_Progress import (
    WorkPlanCreationEngine,
    GradeInfo,
    detect_grade_from_path
)
from models.core import AgentState, TierAState, DocumentMetadata, DocumentHierarchy


class TestGradeInfo:
    """Test GradeInfo dataclass"""
    
    def test_grade_info_creation(self):
        """Test GradeInfo initialization"""
        grade_info = GradeInfo(
            grade="L1",
            path="docs_2/P5/P5-Feature.md",
            exists=True,
            has_grade_field=True
        )
        
        assert grade_info.grade == "L1"
        assert grade_info.path == "docs_2/P5/P5-Feature.md"
        assert grade_info.exists is True
        assert grade_info.has_grade_field is True
    
    def test_grade_info_defaults(self):
        """Test GradeInfo default values"""
        grade_info = GradeInfo()
        
        assert grade_info.grade == "L0"
        assert grade_info.path == ""
        assert grade_info.exists is False
        assert grade_info.has_grade_field is False


class TestDetectGradeFromPath:
    """Test detect_grade_from_path function"""
    
    def test_detect_l0_nexttask(self):
        """Test L0 detection for NextTask documents"""
        assert detect_grade_from_path("docs_2/NextTask-2.md") == "L0"
        assert detect_grade_from_path("NextTask.md") == "L0"
    
    def test_detect_l1(self):
        """Test L1 detection for P[N] documents"""
        assert detect_grade_from_path("docs_2/P5/P5-Feature.md") == "L1"
        assert detect_grade_from_path("P10/P10-Task.md") == "L1"
    
    def test_detect_l2(self):
        """Test L2 detection for P[N].[Phase] documents"""
        assert detect_grade_from_path("docs_2/P5/P5.1-Phase1.md") == "L2"
        assert detect_grade_from_path("P7/P7.2-Implementation.md") == "L2"
    
    def test_detect_l3(self):
        """Test L3 detection for P[N].[Phase].[Sub] documents"""
        assert detect_grade_from_path("docs_2/P5/P5.1.1-Subphase.md") == "L3"
        assert detect_grade_from_path("P8/P8.2.3-Detail.md") == "L3"
    
    def test_detect_default_l0(self):
        """Test default L0 for unrecognized patterns"""
        assert detect_grade_from_path("random.md") == "L0"
        assert detect_grade_from_path("docs/notes.txt") == "L0"


class TestValidatorValidateMainDocument:
    """Test Validator.validate_main_document with TierAState"""
    
    def test_validate_returns_grade_info(self):
        """Test that validate_main_document returns GradeInfo"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create a test main document
            docs_dir = workspace_root / "docs_2"
            docs_dir.mkdir(parents=True, exist_ok=True)
            main_doc = docs_dir / "NextTask-2.md"
            main_doc.write_text("# NextTask\n\n**WPD_grade**: L1\n", encoding="utf-8")
            
            # Create TierAState
            tier_state = TierAState()
            tier_state.main_document_path = "docs_2/NextTask-2.md"
            
            # Validate
            is_valid, grade_info = WorkPlanCreationEngine.Validator.validate_main_document(
                tier_state, workspace_root
            )
            
            # Verify result type
            assert is_valid is True
            assert isinstance(grade_info, GradeInfo)
            assert grade_info.exists is True
            assert grade_info.has_grade_field is True
            assert grade_info.grade == "L1"
    
    def test_validate_missing_document_fallback(self):
        """Test fallback to default when document doesn't exist"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create default main document
            docs_dir = workspace_root / "docs_2"
            docs_dir.mkdir(parents=True, exist_ok=True)
            default_doc = docs_dir / "NextTask-2.md"
            default_doc.write_text("# NextTask\n", encoding="utf-8")
            
            # Create TierAState with non-existent path
            tier_state = TierAState()
            tier_state.main_document_path = "docs_2/NonExistent.md"
            
            # Validate - should fall back to default
            is_valid, grade_info = WorkPlanCreationEngine.Validator.validate_main_document(
                tier_state, workspace_root
            )
            
            # Verify fallback occurred
            assert is_valid is True
            assert tier_state.main_document_path == "docs_2/NextTask-2.md"
            assert grade_info.exists is True


class TestCreatorClasses:
    """Test Creator classes with refactored signatures"""
    
    def test_l1_creator_no_duplicated_params(self):
        """Test L1Creator.create uses tier_state, not separate Doc_meta"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create parent document
            docs_dir = workspace_root / "docs_2"
            docs_dir.mkdir(parents=True, exist_ok=True)
            parent_doc = docs_dir / "NextTask-2.md"
            parent_doc.write_text("# NextTask\n", encoding="utf-8")
            
            # Create states
            state = AgentState(tier="A", status="PENDING")
            tier_state = TierAState()
            
            # Call L1Creator.create - NO Doc_meta parameter
            result = WorkPlanCreationEngine.Creator.L1Creator.create(
                state=state,
                tier_state=tier_state,
                workspace_root=workspace_root,
                Part_N="5",
                task_title="Test-Feature",
                parent_doc=parent_doc,
                description="Test description"
            )
            
            # Verify result
            assert result is not None
            assert result.exists()
            assert result.name == "P5-Test-Feature.md"
            
            # Verify metadata was set on tier_state, not via separate parameter
            assert tier_state.metadata.Part_N == "5"
            assert tier_state.metadata.document_title == "Test-Feature"
            assert tier_state.metadata.document_type == "WPD"
            
            # Verify wpd_grade was set on AgentState, not TierAState
            assert state.wpd_grade == "L1"
            assert not hasattr(tier_state, "wpd_grade")  # Should NOT be on tier_state
    
    def test_l2_creator_no_duplicated_params(self):
        """Test L2Creator.create uses tier_state, not separate Doc_meta/wpd"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create parent L1 document
            docs_dir = workspace_root / "docs_2" / "P5"
            docs_dir.mkdir(parents=True, exist_ok=True)
            parent_l1 = docs_dir / "P5-Feature.md"
            parent_l1.write_text("# P5 Feature\n", encoding="utf-8")
            
            # Create states
            state = AgentState(tier="A", status="PENDING")
            tier_state = TierAState()
            
            # Call L2Creator.create - NO Doc_meta or wpd parameters
            result = WorkPlanCreationEngine.Creator.L2Creator.create(
                state=state,
                tier_state=tier_state,
                workspace_root=workspace_root,
                parent_wpd_path=parent_l1
            )
            
            # Verify result
            assert result is not None
            assert result.exists()
            assert "P5.1" in result.name  # Should have phase number
            
            # Verify metadata was set on tier_state
            assert tier_state.metadata.Part_N == "5"
            assert tier_state.metadata.document_type == "WPD"
            assert tier_state.hierarchy.parent_document == "docs_2/P5/P5-Feature.md"
            
            # Verify wpd_grade on AgentState
            assert state.wpd_grade == "L2"
    
    def test_l3_creator_consistent_pattern(self):
        """Test L3Creator.create follows same pattern as L2Creator"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create parent L2 document
            docs_dir = workspace_root / "docs_2" / "P5"
            docs_dir.mkdir(parents=True, exist_ok=True)
            parent_l2 = docs_dir / "P5.1-Phase1.md"
            parent_l2.write_text("# P5.1 Phase 1\n", encoding="utf-8")
            
            # Create states
            state = AgentState(tier="A", status="PENDING")
            tier_state = TierAState()
            
            # Call L3Creator.create - same pattern as L2Creator
            result = WorkPlanCreationEngine.Creator.L3Creator.create(
                state=state,
                tier_state=tier_state,
                workspace_root=workspace_root,
                parent_wpd_path=parent_l2
            )
            
            # Verify result
            assert result is not None
            assert result.exists()
            assert "P5.1.1" in result.name  # Should have subphase number
            
            # Verify wpd_grade on AgentState
            assert state.wpd_grade == "L3"


class TestWorkPlanCreationEngine:
    """Test main WorkPlanCreationEngine class"""
    
    def test_engine_initialization(self):
        """Test WorkPlanCreationEngine initializes with correct state separation"""
        with TemporaryDirectory() as tmpdir:
            engine = WorkPlanCreationEngine(workspace_root=str(tmpdir))
            
            # Verify state separation
            assert isinstance(engine.state, AgentState)
            assert isinstance(engine.tier_state, TierAState)
            
            # Verify AgentState has common fields
            assert engine.state.tier == "A"
            assert engine.state.status == "PENDING"
            assert hasattr(engine.state, "wpd_grade")
            assert hasattr(engine.state, "execution_log")
            
            # Verify TierAState has tier-specific fields
            assert isinstance(engine.tier_state.metadata, DocumentMetadata)
            assert isinstance(engine.tier_state.hierarchy, DocumentHierarchy)
            assert not hasattr(engine.tier_state, "wpd_grade")  # Should NOT be here
    
    def test_delegate_methods_pass_correct_params(self):
        """Test delegate methods pass state and tier_state correctly"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            engine = WorkPlanCreationEngine(workspace_root=str(tmpdir))
            
            # Create parent document
            docs_dir = workspace_root / "docs_2"
            docs_dir.mkdir(parents=True, exist_ok=True)
            parent_doc = docs_dir / "NextTask-2.md"
            parent_doc.write_text("# NextTask\n", encoding="utf-8")
            
            # Call delegate method
            result = engine.create_wpd_l1_document(
                Part_N="7",
                task_title="Integration",
                parent_doc=parent_doc,
                description=""
            )
            
            # Verify both states were updated
            assert engine.state.wpd_grade == "L1"  # Common field in AgentState
            assert engine.tier_state.metadata.Part_N == "7"  # Tier-specific in TierAState
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
