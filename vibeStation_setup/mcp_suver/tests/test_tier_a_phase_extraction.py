"""
Unit tests for Tier A phase extraction and multi-document creation.

Tests the new PhaseExtractor class and multi-L2/L3 document creation workflow.
"""

import sys
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from A_Working_Document_Progress import WorkPlanCreationEngine


class TestPhaseExtractor:
    """Test PhaseExtractor class methods"""
    
    def test_extract_phases_from_l1_empty(self):
        """Test extracting phases from L1 with no phases"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create L1 document with no phases
            l1_doc = workspace_root / "P1-Test.md"
            l1_doc.write_text("""
# Test Document

## Executive Summary
Test summary

## References
None
""", encoding='utf-8')
            
            phases = WorkPlanCreationEngine.PhaseExtractor.extract_phases_from_l1(l1_doc)
            
            assert phases == []
    
    def test_extract_phases_from_l1_single_phase(self):
        """Test extracting single phase from L1"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create L1 document with one phase
            l1_doc = workspace_root / "P1-Test.md"
            l1_doc.write_text("""
# Test Document

## Execution Plan

### Phase 1.1: Setup Environment

**Action**: Install dependencies
**Files to Update**: requirements.txt
**Checklist**:
- [ ] Task 1
- [ ] Task 2

## References
None
""", encoding='utf-8')
            
            phases = WorkPlanCreationEngine.PhaseExtractor.extract_phases_from_l1(l1_doc)
            
            assert len(phases) == 1
            assert phases[0]['phase_n'] == '1'
            assert phases[0]['phase_title'] == 'Setup Environment'
            assert 'Install dependencies' in phases[0]['content']
    
    def test_extract_phases_from_l1_multiple_phases(self):
        """Test extracting multiple phases from L1"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create L1 document with multiple phases
            l1_doc = workspace_root / "P5-Feature.md"
            l1_doc.write_text("""
# Feature Implementation

## Execution Plan

### Phase 5.1: Setup
Setup content here

### Phase 5.2: Implementation
Implementation content here

### Phase 5.3: Testing
Testing content here

## References
None
""", encoding='utf-8')
            
            phases = WorkPlanCreationEngine.PhaseExtractor.extract_phases_from_l1(l1_doc)
            
            assert len(phases) == 3
            assert phases[0]['phase_n'] == '1'
            assert phases[0]['phase_title'] == 'Setup'
            assert phases[1]['phase_n'] == '2'
            assert phases[1]['phase_title'] == 'Implementation'
            assert phases[2]['phase_n'] == '3'
            assert phases[2]['phase_title'] == 'Testing'
    
    def test_extract_subphases_from_l2_empty(self):
        """Test extracting subphases from L2 with no subphases"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create L2 document with no subphases
            l2_doc = workspace_root / "P1.1-Phase.md"
            l2_doc.write_text("""
# Phase Document

## Overview
Phase overview

## References
None
""", encoding='utf-8')
            
            subphases = WorkPlanCreationEngine.PhaseExtractor.extract_subphases_from_l2(l2_doc)
            
            assert subphases == []
    
    def test_extract_subphases_from_l2_with_subphases(self):
        """Test extracting subphases from L2"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create L2 document with subphases
            l2_doc = workspace_root / "P5.1-Setup.md"
            l2_doc.write_text("""
# Setup Phase

## Implementation Plan

### Subphase 5.1.1: Install Tools

Action content here with some lines
Line 2
Line 3
Line 4
Line 5

### Subphase 5.1.2: Configure Settings

Configuration content here
More lines
Even more lines

## References
None
""", encoding='utf-8')
            
            subphases = WorkPlanCreationEngine.PhaseExtractor.extract_subphases_from_l2(l2_doc)
            
            assert len(subphases) == 2
            assert subphases[0]['subphase_n'] == '1'
            assert subphases[0]['subphase_title'] == 'Install Tools'
            assert subphases[0]['line_count'] > 0
            assert subphases[1]['subphase_n'] == '2'
            assert subphases[1]['subphase_title'] == 'Configure Settings'
    
    def test_check_300_line_threshold_none_exceeding(self):
        """Test 300-line threshold check with no exceeding subphases"""
        subphases = [
            {'subphase_n': '1', 'subphase_title': 'Small', 'content': 'content', 'line_count': 50},
            {'subphase_n': '2', 'subphase_title': 'Medium', 'content': 'content', 'line_count': 200},
        ]
        
        exceeding = WorkPlanCreationEngine.PhaseExtractor.check_300_line_threshold(subphases)
        
        assert exceeding == []
    
    def test_check_300_line_threshold_some_exceeding(self):
        """Test 300-line threshold check with exceeding subphases"""
        subphases = [
            {'subphase_n': '1', 'subphase_title': 'Small', 'content': 'content', 'line_count': 50},
            {'subphase_n': '2', 'subphase_title': 'Large', 'content': 'content', 'line_count': 350},
            {'subphase_n': '3', 'subphase_title': 'Huge', 'content': 'content', 'line_count': 500},
        ]
        
        exceeding = WorkPlanCreationEngine.PhaseExtractor.check_300_line_threshold(subphases)
        
        assert len(exceeding) == 2
        assert exceeding[0]['subphase_n'] == '2'
        assert exceeding[1]['subphase_n'] == '3'
    
    def test_check_300_line_threshold_exact_boundary(self):
        """Test 300-line threshold check at exact boundary"""
        subphases = [
            {'subphase_n': '1', 'subphase_title': 'Exact', 'content': 'content', 'line_count': 300},
            {'subphase_n': '2', 'subphase_title': 'Over', 'content': 'content', 'line_count': 301},
        ]
        
        exceeding = WorkPlanCreationEngine.PhaseExtractor.check_300_line_threshold(subphases)
        
        # 300 exactly should NOT exceed (threshold is >300)
        assert len(exceeding) == 1
        assert exceeding[0]['subphase_n'] == '2'


class TestL2CreatorFromPhase:
    """Test L2Creator.create_from_phase method"""
    
    def test_create_from_phase_basic(self):
        """Test creating L2 from phase info"""
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create parent L1 document
            l1_dir = workspace_root / "docs_2" / "P5"
            l1_dir.mkdir(parents=True, exist_ok=True)
            l1_doc = l1_dir / "P5-Feature.md"
            l1_doc.write_text("# Feature\n\n**WPD_grade**: L1\n", encoding='utf-8')
            
            # Phase info to create L2 from
            phase_info = {
                'phase_n': '1',
                'phase_title': 'Setup',
                'content': 'Setup phase content here'
            }
            
            # Create engine and states
            engine = WorkPlanCreationEngine(str(workspace_root))
            
            # Create L2 from phase
            l2_path = engine.Creator.L2Creator.create_from_phase(
                engine.state,
                engine.tier_state,
                workspace_root,
                l1_doc,
                phase_info
            )
            
            assert l2_path is not None
            assert l2_path.exists()
            assert l2_path.name == "P5.1-Setup.md"
            
            # Verify content
            content = l2_path.read_text(encoding='utf-8')
            assert "Setup" in content
            assert "Setup phase content here" in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
