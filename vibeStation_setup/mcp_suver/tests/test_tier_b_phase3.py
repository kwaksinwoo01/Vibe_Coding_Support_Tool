"""
Unit tests for Tier B Phase 3 enhancements.

Tests the enhanced phase parsing, WPD-grade-based selection, and PRD generation.
"""

import sys
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from B_Performing_Tasks import TaskExecutionEngine
from models.core import TaskContext, AgentState


class TestEnhancedPhaseParsing:
    """Test enhanced phase parsing with hierarchical support"""
    
    def test_parse_flat_phases_l1(self):
        """Test parsing flat phases for L1 documents"""
        wpd_content = """
# Test WPD L1

## 🔧 Execution Plan

### Phase 1: Setup
- [ ] Install dependencies
- [ ] Configure environment

### Phase 2: Implementation
- [ ] Write code
- [ ] Add tests

## References
None
"""
        context = TaskContext(user_input="execute plan", workspace_root="/tmp")
        engine = TaskExecutionEngine(context)
        
        phases = engine.parse_phases(wpd_content, "L1")
        
        assert len(phases) == 2
        assert phases[0]['phase_number'] == '1'
        assert phases[0]['phase_title'] == 'Setup'
        assert len(phases[0]['checklist']) == 2
        assert len(phases[0]['subphases']) == 0  # L1 has no subphases
        
        assert phases[1]['phase_number'] == '2'
        assert phases[1]['phase_title'] == 'Implementation'
    
    def test_parse_nested_phases_l2(self):
        """Test parsing nested phases for L2 documents"""
        wpd_content = """
# Test WPD L2

## 🔧 Execution Plan

### Phase 1: Main Phase
- [ ] Main task

### Phase 1.1: Subphase 1
- [ ] Subtask 1
- [ ] Subtask 2

### Phase 1.2: Subphase 2
- [ ] Subtask 3

### Phase 2: Another Main Phase
- [ ] Another main task

## References
None
"""
        context = TaskContext(user_input="execute plan", workspace_root="/tmp")
        engine = TaskExecutionEngine(context)
        
        phases = engine.parse_phases(wpd_content, "L2")
        
        # Should have 2 top-level phases
        assert len(phases) == 2
        
        # First phase should have 2 subphases
        assert phases[0]['phase_number'] == '1'
        assert len(phases[0]['subphases']) == 2
        assert phases[0]['subphases'][0]['phase_number'] == '1.1'
        assert phases[0]['subphases'][0]['phase_title'] == 'Subphase 1'
        assert len(phases[0]['subphases'][0]['checklist']) == 2
        
        # Second phase should have no subphases
        assert phases[1]['phase_number'] == '2'
        assert len(phases[1]['subphases']) == 0
    
    def test_parse_deep_nested_phases_l3(self):
        """Test parsing deeply nested phases for L3 documents"""
        wpd_content = """
# Test WPD L3

## 🔧 Execution Plan

### Phase 1: Top Level
- [ ] Top task

### Phase 1.1: Second Level
- [ ] Second level task

### Phase 1.1.1: Third Level
- [ ] Third level task
- [ ] Another third level task

### Phase 1.1.2: Another Third Level
- [ ] More tasks

## References
None
"""
        context = TaskContext(user_input="execute plan", workspace_root="/tmp")
        engine = TaskExecutionEngine(context)
        
        phases = engine.parse_phases(wpd_content, "L3")
        
        # Should have 1 top-level phase
        assert len(phases) == 1
        assert phases[0]['phase_number'] == '1'
        
        # Should have 1 second-level subphase
        assert len(phases[0]['subphases']) == 1
        assert phases[0]['subphases'][0]['phase_number'] == '1.1'
        
        # Should have 2 third-level subphases
        assert len(phases[0]['subphases'][0]['subphases']) == 2
        assert phases[0]['subphases'][0]['subphases'][0]['phase_number'] == '1.1.1'
        assert phases[0]['subphases'][0]['subphases'][1]['phase_number'] == '1.1.2'
    
    def test_backward_compatibility_milestone_format(self):
        """Test backward compatibility with legacy Milestone format"""
        wpd_content = """
# Legacy WPD

## 🎯 Milestones

- [ ] Milestone 1
- [x] Milestone 2
- [ ] Milestone 3

## References
None
"""
        context = TaskContext(user_input="execute plan", workspace_root="/tmp")
        engine = TaskExecutionEngine(context)
        
        phases = engine.parse_phases(wpd_content, "L1")
        
        # Should parse as milestones
        assert len(phases) == 3
        assert "Milestone 1" in phases[0]['title']
        assert phases[1]['completed'] == True  # Milestone 2 is checked


class TestWPDGradePriority:
    """Test WPD-grade-based selection priority"""
    
    def test_select_highest_grade_l3(self):
        """Test selection of L3 over L2 and L1"""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create L1, L2, L3 documents
            (workspace / "docs_2").mkdir(parents=True)
            
            l1_doc = workspace / "docs_2" / "P5-L1.md"
            l1_doc.write_text("# L1\n\n**WPD_grade**: L1\n", encoding='utf-8')
            
            l2_doc = workspace / "docs_2" / "P5-L2.md"
            l2_doc.write_text("# L2\n\n**WPD_grade**: L2\n", encoding='utf-8')
            
            l3_doc = workspace / "docs_2" / "P5-L3.md"
            l3_doc.write_text("# L3\n\n**WPD_grade**: L3\n", encoding='utf-8')
            
            created_docs = ["docs_2/P5-L1.md", "docs_2/P5-L2.md", "docs_2/P5-L3.md"]
            
            context = TaskContext(user_input="execute", workspace_root=str(workspace))
            engine = TaskExecutionEngine(context)
            
            selected = engine._select_wpd_by_grade_priority(created_docs)
            
            assert selected == "docs_2/P5-L3.md"  # Should select L3
    
    def test_select_l2_when_no_l3(self):
        """Test selection of L2 when L3 doesn't exist"""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create only L1 and L2 documents
            (workspace / "docs_2").mkdir(parents=True)
            
            l1_doc = workspace / "docs_2" / "P5-L1.md"
            l1_doc.write_text("# L1\n\n**WPD_grade**: L1\n", encoding='utf-8')
            
            l2_doc = workspace / "docs_2" / "P5-L2.md"
            l2_doc.write_text("# L2\n\n**WPD_grade**: L2\n", encoding='utf-8')
            
            created_docs = ["docs_2/P5-L1.md", "docs_2/P5-L2.md"]
            
            context = TaskContext(user_input="execute", workspace_root=str(workspace))
            engine = TaskExecutionEngine(context)
            
            selected = engine._select_wpd_by_grade_priority(created_docs)
            
            assert selected == "docs_2/P5-L2.md"  # Should select L2


class TestPRDGeneration:
    """Test PRD template-based report generation"""
    
    def test_generate_prd_basic(self):
        """Test basic PRD generation"""
        context = TaskContext(user_input="execute", workspace_root="/tmp")
        engine = TaskExecutionEngine(context)
        
        phases = [
            {"title": "Phase 1: Setup", "phase_number": "1", "order": 1, "checklist": []},
            {"title": "Phase 2: Execute", "phase_number": "2", "order": 2, "checklist": []},
        ]
        
        results = [
            {
                "phase": "Phase 1: Setup",
                "phase_number": "1",
                "status": "COMPLETED",
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "output": "Setup completed",
                "errors": [],
                "checklist_results": [],
                "subphase_results": []
            },
            {
                "phase": "Phase 2: Execute",
                "phase_number": "2",
                "status": "COMPLETED",
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "output": "Execution completed",
                "errors": [],
                "checklist_results": [],
                "subphase_results": []
            },
        ]
        
        prd_content = engine.generate_prd_report(phases, results, "docs_2/P5/P5-Test.md", "5")
        
        # Verify PRD structure
        assert "# PRD-P5: Execution Results Report" in prd_content
        assert "**Document Type**: PRD" in prd_content
        assert "**Total Phases** | 2" in prd_content
        assert "**Completed** | 2" in prd_content
        assert "Phase 1: Setup" in prd_content
        assert "Phase 2: Execute" in prd_content
        assert "docs_2/P5/P5-Test.md" in prd_content
    
    def test_prd_with_failures(self):
        """Test PRD generation with failed phases"""
        context = TaskContext(user_input="execute", workspace_root="/tmp")
        engine = TaskExecutionEngine(context)
        
        phases = [{"title": "Phase 1", "phase_number": "1", "order": 1, "checklist": []}]
        
        results = [
            {
                "phase": "Phase 1",
                "phase_number": "1",
                "status": "FAILED",
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "output": "",
                "errors": ["Test error"],
                "checklist_results": [],
                "subphase_results": []
            },
        ]
        
        prd_content = engine.generate_prd_report(phases, results, "docs_2/P5/P5-Test.md", "5")
        
        assert "**Status**: ❌ FAILED" in prd_content
        assert "**Failed** | 1" in prd_content
        assert "Test error" in prd_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
